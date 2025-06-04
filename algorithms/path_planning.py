# src/algorithms/path_planning.py

from typing import List, Tuple, Dict, Set, Optional, Callable
from dataclasses import dataclass
import math
import heapq
from datetime import time
import logging
import random

try:
    from src.models import NoFlyZone
except ImportError:
    from models import NoFlyZone

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

@dataclass
class Node:
    pos: Tuple[float, float]
    g_cost: float = 0
    h_cost: float = 0
    parent: Optional['Node'] = None
    priority: float = 1.0 # Teslimat önceliği ile ilişkilendirilebilir
    speed: float = 10.0
    
    @property
    def f_cost(self) -> float:
        return self.g_cost + self.h_cost
    
    def __lt__(self, other: 'Node') -> bool:
        return self.f_cost < other.f_cost
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return False
        return haversine_distance(self.pos[0], self.pos[1], other.pos[0], other.pos[1]) < 10 # 10m tolerans

    def __hash__(self) -> int:
        # Konumları belirli bir hassasiyete yuvarlayarak hash_value oluştur
        # Bu, A* algoritmasında open_set_dict ve closed_set için önemlidir
        return hash((round(self.pos[0], 5), round(self.pos[1], 5)))


class PathPlanner:
    _instance = None
    _initialized = False
    
    def __new__(cls, no_fly_zones: List[NoFlyZone], *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, no_fly_zones: List[NoFlyZone], adaptive_sampling: bool = True, safety_margin: float = 0.0001): # derece cinsinden ~10m
        if self._initialized:
            self.no_fly_zones = no_fly_zones # Güncel NFZ listesini al
            return
        
        self.no_fly_zones = no_fly_zones
        self.safety_margin = safety_margin
        self.adaptive_sampling = adaptive_sampling
        self.max_iterations = 10000 
        self.heuristic_weight = 1.1 # 1.0'a yakın daha optimal, >1.0 daha hızlı ama suboptimal olabilir
        
        # PRM Parametreleri (kullanılmıyorsa bile tanımlı kalabilir)
        self.prm_samples = 300
        self.prm_neighbors = 15
        self.prm_max_dist = 0.015 # ~1.5 km (derece cinsinden)
        
        # Adaptif Adım Boyutları
        self.min_step_size = 0.0002  # ~20 metre
        self.max_step_size = 0.002   # ~200 metre
        self.default_step_size = 0.0005 # ~50 metre
        
        self._initialized = True

    @staticmethod
    def calculate_distance(pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        return haversine_distance(pos1[0], pos1[1], pos2[0], pos2[1])
    
    def is_valid_position(self, pos: Tuple[float, float], active_zones: List[NoFlyZone]) -> bool:
        """Verilen pozisyonun aktif yasak bölgeler içinde olup olmadığını kontrol eder."""
        return not any(zone.contains_point(pos) for zone in active_zones)
    
    def _get_step_size(self, pos: Tuple[float, float], end_pos: Tuple[float, float], 
                       active_zones: List[NoFlyZone]) -> float:
        if not self.adaptive_sampling:
            return self.default_step_size
        
        dist_to_target_deg = math.sqrt((pos[0] - end_pos[0])**2 + (pos[1] - end_pos[1])**2)
        
        min_dist_to_obstacle_deg = float('inf')
        if active_zones:
            for zone in active_zones:
                # Basit bir yaklaşım: Yasak bölgenin köşe noktalarına olan en kısa mesafe
                for vertex in zone.coordinates:
                    dist = math.sqrt((pos[0] - vertex[0])**2 + (pos[1] - vertex[1])**2)
                    min_dist_to_obstacle_deg = min(min_dist_to_obstacle_deg, dist)
        
        if min_dist_to_obstacle_deg == float('inf'): # Engel yoksa
            return self.max_step_size
        
        # En yakın özelliğe (hedef veya engel) olan mesafeye göre adım boyutu belirle
        closest_feature_deg = min(dist_to_target_deg, min_dist_to_obstacle_deg)
        
        # Adım boyutunu, en yakın özelliğe olan mesafenin bir oranı olarak ayarla
        step_size_factor = 0.3 # Bu faktör ayarlanabilir
        step_size = closest_feature_deg * step_size_factor
        
        return max(self.min_step_size, min(step_size, self.max_step_size))

    def _is_edge_valid(self, pos1: Tuple[float, float], pos2: Tuple[float, float], 
                       active_zones: List[NoFlyZone]) -> bool:
        """İki nokta arasındaki doğru parçasının yasak bölgeyle kesişip kesişmediğini kontrol eder."""
        for zone in active_zones:
            if zone.intersects_path(pos1, pos2):
                return False
        return True

    def _is_direct_path_possible(self, start: Tuple[float, float], 
                                 end: Tuple[float, float], 
                                 active_zones: List[NoFlyZone]) -> bool:
        """İki nokta arasında engelsiz direkt bir yol olup olmadığını kontrol eder."""
        return self._is_edge_valid(start, end, active_zones)

    def get_neighbors(self,
                      pos: Tuple[float, float],
                      end_pos: Tuple[float, float],
                      active_zones: List[NoFlyZone]) -> List[Tuple[float, float]]:
        step_size = self._get_step_size(pos, end_pos, active_zones)
        neighbors = []
        
        # 8 ana yön + 8 ara yön (daha hassas keşif için)
        directions = [
            (1, 0), (-1, 0), (0, 1), (0, -1),         # N, S, E, W
            (1, 1), (1, -1), (-1, 1), (-1, -1),       # NE, NW, SE, SW
            (0.5, 1), (1, 0.5), (-0.5, 1), (-1, 0.5), # Ara yönler
            (0.5, -1), (1, -0.5), (-0.5, -1), (-1, -0.5)
        ]
        
        for dx_dir, dy_dir in directions:
            magnitude = math.sqrt(dx_dir**2 + dy_dir**2)
            # Normalize edilmiş yönü adım boyutuyla çarp
            nx = (dx_dir / magnitude) * step_size 
            ny = (dy_dir / magnitude) * step_size
            
            new_pos = (pos[0] + nx, pos[1] + ny)
            if self.is_valid_position(new_pos, active_zones):
                neighbors.append(new_pos)
        
        # Hedef noktası da geçerli bir komşu olabilir (özellikle yakınsa)
        if self._is_edge_valid(pos, end_pos, active_zones):
             neighbors.append(end_pos)
             
        return list(set(neighbors)) # Tekrarları önle

    def find_path(self,
                  start: Tuple[float, float],
                  end: Tuple[float, float],
                  current_time: time,
                  priority: float = 1.0, # PDF'e göre maliyet fonksiyonunda kullanılabilir
                  drone_speed: float = 10.0) -> List[Tuple[float, float]]:
        
        active_zones = [zone for zone in self.no_fly_zones if zone.is_active(current_time)]
        
        if not (self.is_valid_position(start, active_zones) and self.is_valid_position(end, active_zones)):
            logging.warning(f"Rota Planlama: Başlangıç ({start}) veya hedef ({end}) geçersiz (yasak bölge içinde).")
            return []
            
        if self._is_direct_path_possible(start, end, active_zones):
            return [start, end]
        
        start_node = Node(start, priority=priority, speed=drone_speed)
        # PDF'teki A* heuristic: distance + nofly_zone_penalty.
        # Mevcut implementasyon no-fly zone'lardan kaçınıyor, bu yüzden penalty direkt heuristic'e eklenmiyor.
        # Heuristic olarak sadece mesafeyi kullanıyoruz.
        start_node.h_cost = self.calculate_distance(start, end) * self.heuristic_weight
        
        open_set = [start_node] # Min-heap
        open_set_dict: Dict[Tuple[float, float], Node] = {start_node.pos: start_node} # Hızlı erişim için
        closed_set: Set[Tuple[float, float]] = set() # Ziyaret edilen düğümlerin pozisyonları
        
        iterations = 0
        while open_set:
            iterations += 1
            if iterations > self.max_iterations:
                logging.warning(f"A* Maksimum iterasyon ({self.max_iterations}) aşıldı. Rota bulunamadı.")
                return [] # PRM fallback'i daha sonra eklenebilir.
            
            current_node = heapq.heappop(open_set)
            
            # Eğer bu düğüm zaten daha iyi bir yolla open_set_dict'ten çıkarılmışsa atla
            if current_node.pos not in open_set_dict or open_set_dict[current_node.pos].f_cost < current_node.f_cost:
                continue
            
            open_set_dict.pop(current_node.pos, None) # open_set_dict'ten de kaldır
            closed_set.add(current_node.pos)
            
            # Hedefe ulaşıldı mı? (Belirli bir toleransla)
            if self.calculate_distance(current_node.pos, end) <= 50: # 50 metre tolerans
                path = self._reconstruct_path(current_node)
                return self._smooth_path(path, active_zones)
            
            neighbors_pos = self.get_neighbors(current_node.pos, end, active_zones)
            for neighbor_pos_tuple in neighbors_pos:
                if neighbor_pos_tuple in closed_set:
                    continue
                
                # PDF'teki A* kenar maliyeti: distance * weight + (priority * 100)
                # Mevcut A* kenar maliyeti sadece mesafe. Ağırlık ve öncelik GA'da ele alınıyor.
                # Basitlik adına A*'da sadece mesafeyi kullanmaya devam edelim.
                movement_cost = self.calculate_distance(current_node.pos, neighbor_pos_tuple)
                new_g_cost = current_node.g_cost + movement_cost
                
                # Yeni komşu düğüm
                neighbor_node = Node(
                    pos=neighbor_pos_tuple,
                    g_cost=new_g_cost,
                    h_cost=self.calculate_distance(neighbor_pos_tuple, end) * self.heuristic_weight,
                    parent=current_node,
                    priority=current_node.priority, # Öncelik ebeveynden gelebilir
                    speed=current_node.speed
                )
                
                if neighbor_pos_tuple not in open_set_dict or new_g_cost < open_set_dict[neighbor_pos_tuple].g_cost:
                    heapq.heappush(open_set, neighbor_node)
                    open_set_dict[neighbor_pos_tuple] = neighbor_node
                    
        logging.info(f"A* ile {start} -> {end} için yol bulunamadı.")
        return [] # PRM fallback'i buraya eklenebilir.

    def _reconstruct_path(self, end_node: Node) -> List[Tuple[float, float]]:
        path = []
        current = end_node
        while current:
            path.append(current.pos)
            current = current.parent
        return list(reversed(path))
    
    def _smooth_path(self, path: List[Tuple[float, float]], 
                     active_zones: List[NoFlyZone]) -> List[Tuple[float, float]]:
        if len(path) <= 2:
            return path
            
        smoothed_path = [path[0]]
        i = 0
        while i < len(path) - 1:
            furthest_valid_idx = i + 1
            for j in range(i + 2, len(path)):
                if self._is_edge_valid(path[i], path[j], active_zones):
                    furthest_valid_idx = j
                else:
                    break # Daha fazla ilerleyemeyiz, arada engel var
            smoothed_path.append(path[furthest_valid_idx])
            i = furthest_valid_idx
            
        return smoothed_path