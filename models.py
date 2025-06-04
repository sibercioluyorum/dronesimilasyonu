# src/models.py

from dataclasses import dataclass, field
from typing import Tuple, List, Optional
from datetime import time, timedelta
import math

# matplotlib kütüphanesini ekleyin (pip install matplotlib)
try:
    from matplotlib.path import Path
    MPL_AVAILABLE = True
except ImportError:
    MPL_AVAILABLE = False
    # Fallback (Basit Ray Casting)
    def point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
        x, y = point
        n = len(polygon)
        inside = False
        p1x, p1y = polygon[0]
        for i in range(n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside

@dataclass
class DroneConfig:
    """Drone yapılandırma sabitleri"""
    BASE_WEIGHT: float = 2.0  # kg
    ENERGY_FACTOR: float = 0.01  # mAh/m/kg 

    def calculate_energy(self, distance: float, payload: float) -> float:
        total_weight = self.BASE_WEIGHT + payload
        return distance * total_weight * self.ENERGY_FACTOR

@dataclass(frozen=True)
class DeliveryPoint:
    """Teslimat noktası özellikleri"""
    id: int 
    pos: Tuple[float, float]  # (enlem, boylam)
    weight: float             # kg
    priority: int             # 1: düşük, 5: yüksek
    time_window: Tuple[time, time]  # (başlangıç, bitiş)

    def is_time_valid(self, current_time: time) -> bool:
        return self.time_window[0] <= current_time <= self.time_window[1]

    def __hash__(self) -> int:
        return hash(self.id)
    
    def __eq__(self, other):
        if not isinstance(other, DeliveryPoint):
            return NotImplemented
        return self.id == other.id

@dataclass
class Drone:
    """Drone özellikleri"""
    id: int 
    max_weight: float  # kg
    battery: int      # mAh
    speed: float      # m/s
    start_pos: Tuple[float, float]  # (enlem, boylam)
    _current_battery: Optional[int] = None
    _config: DroneConfig = field(default_factory=DroneConfig)

    def __post_init__(self):
        if self._current_battery is None:
            self._current_battery = self.battery

    @property
    def current_battery(self) -> int:
        return self._current_battery if self._current_battery is not None else 0

    def update_battery(self, energy_consumption: float):
        if self._current_battery is not None:
            self._current_battery = max(0, int(self._current_battery - energy_consumption))

    def charge_battery(self):
        """Bataryayı tam şarj eder."""
        self._current_battery = self.battery

    def can_carry(self, weight: float) -> bool:
        return weight <= self.max_weight

    def calculate_energy_consumption(self, distance: float, weight: float) -> float:
        return self._config.calculate_energy(distance, weight)

    def has_enough_battery(self, required_energy: float) -> bool:
        return self.current_battery >= required_energy

    def copy(self):
        from copy import deepcopy
        return deepcopy(self)

@dataclass(frozen=True)
class NoFlyZone:
    """Uçuş yasağı bölgesi özellikleri"""
    id: int 
    coordinates: List[Tuple[float, float]] #
    active_time: Tuple[time, time] #
    _polygon_path: Optional['Path'] = field(init=False, repr=False, default=None)

    def __post_init__(self):
        if not self.coordinates or len(self.coordinates) < 3:
            raise ValueError("Bir NoFlyZone en az 3 koordinata sahip olmalıdır.")
        if MPL_AVAILABLE:
            object.__setattr__(self, '_polygon_path', Path(self.coordinates))

    def is_active(self, current_time: time) -> bool:
        start = self.active_time[0]
        end = self.active_time[1]
        if start <= end: # Aynı gün içinde
            return start <= current_time <= end
        else: # Ertesi güne sarkan zaman aralığı (örn: 22:00 - 06:00)
            return current_time >= start or current_time <= end

    def contains_point(self, point: Tuple[float, float]) -> bool:
        if MPL_AVAILABLE and self._polygon_path:
            return self._polygon_path.contains_point(point)
        else:
            return point_in_polygon(point, self.coordinates) # Fallback

    def intersects_path(self, start: Tuple[float, float], end: Tuple[float, float]) -> bool:
        """İki nokta arasındaki doğru parçasının bölgeyi kesip kesmediğini kontrol eder."""
        # Basit örnekleme tabanlı kontrol. Daha kesin sonuçlar için
        # geometrik kesişim algoritmaları (örn: Shapely kütüphanesi) kullanılabilir.
        steps = 30  # Kontrol edilecek ara nokta sayısı
        for i in range(1, steps + 1): # Başlangıç ve bitiş noktaları dahil değil
            t = i / float(steps)
            # Doğru parçası üzerindeki ara noktayı hesapla
            inter_lat = start[0] + t * (end[0] - start[0])
            inter_lon = start[1] + t * (end[1] - start[1])
            if self.contains_point((inter_lat, inter_lon)):
                return True
        return False

def add_minutes_to_time(t: time, minutes_to_add: int) -> time:
    """Verilen zamana dakika ekler ve yeni time nesnesi döndürür."""
    current_total_minutes = t.hour * 60 + t.minute
    new_total_minutes = current_total_minutes + int(minutes_to_add)
    
    # Saati ve dakikayı 24 saat formatına göre ayarla
    day_offset = new_total_minutes // (24 * 60) # Kaç gün geçtiği (kullanılmıyor ama hesaplanabilir)
    new_hour = (new_total_minutes // 60) % 24 
    new_minute = new_total_minutes % 60
    
    return time(new_hour, new_minute)