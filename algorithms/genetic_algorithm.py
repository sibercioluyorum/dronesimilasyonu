# src/algorithms/genetic_algorithm.py

from typing import List, Tuple, Optional
import random
from datetime import time
from dataclasses import dataclass, field
import math
import logging
import heapq # Min-Heap için heapq modülünü import et

try:
    from src.models import Drone, DeliveryPoint, NoFlyZone, add_minutes_to_time
    from .path_planning import PathPlanner
except ImportError:
    from models import Drone, DeliveryPoint, NoFlyZone, add_minutes_to_time
    from path_planning import PathPlanner

@dataclass
class DeliveryAssignment:
    drone: Drone 
    delivery: DeliveryPoint
    estimated_time: time
    route: List[Tuple[float, float]]
    energy_consumption: float
    rule_violations: int = 0
    time_added_for_charge_return: float = 0.0

@dataclass
class Individual:
    assignments: List[DeliveryAssignment]
    fitness: float = 0.0

    def calculate_fitness(self, total_deliveries: int) -> float:
        if not self.assignments:
            self.fitness = -float('inf') 
            return self.fitness
        
        completed_deliveries = len(self.assignments)
        total_energy = sum(a.energy_consumption for a in self.assignments)
        total_violations = sum(a.rule_violations for a in self.assignments)
        
        # PDF'teki Fitness Fonksiyonu
        self.fitness = (
            (completed_deliveries * 50) -
            (total_energy * 0.1) -
            (total_violations * 1000)
        )
        return self.fitness

class GeneticAlgorithm:
    def __init__(self,
                 population_size: int = 50,
                 generations: int = 20,
                 mutation_rate: float = 0.2,
                 elitism_count: int = 3,
                 charging_time_per_mah: float = 0.001):
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.elitism_count = elitism_count
        self.charging_time_per_mah = charging_time_per_mah

    def _ensure_path_planner(self, no_fly_zones: List[NoFlyZone]) -> PathPlanner:
        planner = PathPlanner(no_fly_zones)
        planner.no_fly_zones = no_fly_zones
        return planner

    def _create_individual_from_deliveries(self,
                                           potential_deliveries: List[DeliveryPoint], # Artık potansiyel teslimat havuzu
                                           drones: List[Drone],
                                           initial_current_time: time,
                                           no_fly_zones: List[NoFlyZone],
                                           planner: PathPlanner) -> Individual:
        assignments: List[DeliveryAssignment] = []
        used_delivery_ids = set()
        
        active_drones = [d.copy() for d in drones]
        drone_available_times = [initial_current_time] * len(active_drones)
        drone_current_positions = [d.start_pos for d in active_drones]
        base_pos = drones[0].start_pos if drones else (0.0, 0.0)

        # --- MIN-HEAP ENTEGRASYONU BAŞLANGICI ---
        delivery_heap = []
        for delivery in potential_deliveries: # GA operatörlerinden gelen teslimat havuzu
            if delivery.id not in used_delivery_ids: # Henüz bu bireyde atanmamışları heape ekle
                # Min-Heap önceliği: (-priority, time_window_start_minutes, delivery.id)
                # En yüksek priority (PDF'e göre 5) en önce çıkmalı, bu yüzden -priority.
                # Eşitlik durumunda zaman penceresi başlangıcı erken olan, o da eşitse ID'si küçük olan.
                priority_value = -delivery.priority # Yüksek öncelik = Küçük negatif değer
                start_window_minutes = delivery.time_window[0].hour * 60 + delivery.time_window[0].minute
                heapq.heappush(delivery_heap, (priority_value, start_window_minutes, delivery.id, delivery))
        # --- MIN-HEAP ENTEGRASYONU SONU ---

        processed_in_loop = 0 # Sonsuz döngüye karşı basit bir sayaç
        max_processing_attempts = len(potential_deliveries) * len(active_drones) + len(potential_deliveries)


        while delivery_heap and processed_in_loop < max_processing_attempts: # Heap boşalana kadar veya deneme limiti
            processed_in_loop += 1
            
            # Min-Heap'ten en öncelikli teslimatı çek
            _, _, _, delivery_to_assign = heapq.heappop(delivery_heap)

            if delivery_to_assign.id in used_delivery_ids: # Zaten atandıysa (çoklu ekleme durumu nadir)
                continue

            best_candidate_assignment: Optional[DeliveryAssignment] = None
            best_candidate_drone_idx: int = -1
            earliest_arrival_time_for_delivery = time(23, 59, 59)
            
            for drone_idx, current_drone in enumerate(active_drones):
                if not current_drone.can_carry(delivery_to_assign.weight):
                    continue

                temp_drone_state = current_drone.copy()
                current_drone_pos = drone_current_positions[drone_idx]
                current_drone_available_at = drone_available_times[drone_idx]
                time_added_for_current_path = 0.0

                route_to_delivery = planner.find_path(current_drone_pos, delivery_to_assign.pos, current_drone_available_at, delivery_to_assign.priority)
                if not route_to_delivery: continue
                
                dist_to_delivery = sum(PathPlanner.calculate_distance(route_to_delivery[j], route_to_delivery[j+1]) for j in range(len(route_to_delivery)-1))
                energy_for_delivery_trip = temp_drone_state.calculate_energy_consumption(dist_to_delivery, delivery_to_assign.weight)

                route_delivery_to_base = planner.find_path(delivery_to_assign.pos, base_pos, current_drone_available_at)
                if not route_delivery_to_base: continue
                dist_delivery_to_base = sum(PathPlanner.calculate_distance(route_delivery_to_base[j], route_delivery_to_base[j+1]) for j in range(len(route_delivery_to_base)-1))
                energy_for_return_trip = temp_drone_state.calculate_energy_consumption(dist_delivery_to_base, 0)

                total_energy_for_mission = energy_for_delivery_trip + energy_for_return_trip
                potential_available_at = current_drone_available_at

                if not temp_drone_state.has_enough_battery(total_energy_for_mission):
                    time_for_return_to_base_now = 0.0
                    if current_drone_pos != base_pos:
                        route_current_to_base = planner.find_path(current_drone_pos, base_pos, current_drone_available_at)
                        if not route_current_to_base: continue
                        dist_current_to_base = sum(PathPlanner.calculate_distance(route_current_to_base[j], route_current_to_base[j+1]) for j in range(len(route_current_to_base)-1))
                        energy_to_return_now = temp_drone_state.calculate_energy_consumption(dist_current_to_base, 0)
                        if not temp_drone_state.has_enough_battery(energy_to_return_now): continue
                        temp_drone_state.update_battery(energy_to_return_now)
                        time_for_return_to_base_now = (dist_current_to_base / temp_drone_state.speed) / 60 if temp_drone_state.speed > 0 else float('inf')
                    
                    energy_needed_for_full_charge = temp_drone_state.battery - temp_drone_state.current_battery
                    charging_duration_minutes = energy_needed_for_full_charge * self.charging_time_per_mah
                    temp_drone_state.charge_battery()
                    
                    time_added_for_current_path = time_for_return_to_base_now + charging_duration_minutes
                    potential_available_at = add_minutes_to_time(current_drone_available_at, int(time_added_for_current_path))
                    current_drone_pos = base_pos 
                    
                    route_to_delivery = planner.find_path(current_drone_pos, delivery_to_assign.pos, potential_available_at, delivery_to_assign.priority)
                    if not route_to_delivery: continue
                    dist_to_delivery = sum(PathPlanner.calculate_distance(route_to_delivery[j], route_to_delivery[j+1]) for j in range(len(route_to_delivery)-1))
                    energy_for_delivery_trip = temp_drone_state.calculate_energy_consumption(dist_to_delivery, delivery_to_assign.weight)
                    # Üsse dönüş enerjisi şarjdan sonra tekrar hesaplanmasına gerek yok, zaten batarya dolu.
                    # Sadece teslimat enerjisi yeterli mi diye bakılır.
                    if not temp_drone_state.has_enough_battery(energy_for_delivery_trip): continue


                flight_time_to_delivery_minutes = (dist_to_delivery / temp_drone_state.speed) / 60 if temp_drone_state.speed > 0 else float('inf')
                estimated_arrival = add_minutes_to_time(potential_available_at, int(flight_time_to_delivery_minutes))
                
                if estimated_arrival.hour < potential_available_at.hour:
                    if not (potential_available_at.hour > 20 and estimated_arrival.hour < 4): 
                        continue
                if not delivery_to_assign.is_time_valid(estimated_arrival): continue

                violations = sum(1 for k in range(len(route_to_delivery) - 1) 
                                 for zone in no_fly_zones 
                                 if zone.is_active(estimated_arrival) and 
                                    zone.intersects_path(route_to_delivery[k], route_to_delivery[k+1]))
                
                if violations == 0:
                    if best_candidate_assignment is None or estimated_arrival < earliest_arrival_time_for_delivery:
                        earliest_arrival_time_for_delivery = estimated_arrival
                        best_candidate_drone_idx = drone_idx
                        best_candidate_assignment = DeliveryAssignment(
                            drone=drones[drone_idx], 
                            delivery=delivery_to_assign,
                            estimated_time=estimated_arrival,
                            route=route_to_delivery,
                            energy_consumption=energy_for_delivery_trip,
                            rule_violations=violations,
                            time_added_for_charge_return=time_added_for_current_path
                        )
            
            if best_candidate_assignment and best_candidate_drone_idx != -1:
                assignments.append(best_candidate_assignment)
                used_delivery_ids.add(delivery_to_assign.id)
                
                drone_to_update = active_drones[best_candidate_drone_idx]
                time_increase_for_assignment = best_candidate_assignment.time_added_for_charge_return
                
                current_drone_original_available_time = drone_available_times[best_candidate_drone_idx]

                if time_increase_for_assignment > 0:
                    drone_available_times[best_candidate_drone_idx] = add_minutes_to_time(current_drone_original_available_time, int(time_increase_for_assignment))
                    drone_current_positions[best_candidate_drone_idx] = base_pos
                    drone_to_update.charge_battery()

                drone_to_update.update_battery(best_candidate_assignment.energy_consumption)
                drone_current_positions[best_candidate_drone_idx] = delivery_to_assign.pos
                drone_available_times[best_candidate_drone_idx] = best_candidate_assignment.estimated_time
            # Eğer atanamadıysa, bu teslimat bu birey için kaybolur (heap'ten çıkarıldığı için).
            # Bu, GA'nın farklı bireylerde farklı atamalar denemesine yol açar.

        if processed_in_loop >= max_processing_attempts and delivery_heap:
            logging.warning(f"Birey oluşturma: Max işlem denemesine ulaşıldı, {len(delivery_heap)} teslimat atanamadı.")
            
        return Individual(assignments)

    def optimize(self, drones, deliveries, current_time, no_fly_zones):
        planner = self._ensure_path_planner(no_fly_zones)
        population = []
        if not deliveries: return Individual([], fitness=-float('inf'))

        for _ in range(self.population_size):
            shuffled_deliveries = deliveries.copy()
            random.shuffle(shuffled_deliveries) # GA çeşitliliği için hala karıştır
            # _create_individual_from_deliveries Min-Heap kullanacak
            individual = self._create_individual_from_deliveries(shuffled_deliveries, drones, current_time, no_fly_zones, planner)
            population.append(individual)
        
        if not population:
             logging.error("Başlangıç popülasyonu oluşturulamadı!")
             return Individual([], fitness=-float('inf'))

        for gen in range(self.generations):
            for ind in population: ind.calculate_fitness(len(deliveries))
            population.sort(key=lambda ind: ind.fitness, reverse=True)
            
            logging.debug(f"Nesil {gen+1} Öncesi En İyi Fitness: {population[0].fitness if population else 'N/A'}")
            logging.debug(f"Nesil {gen+1} Öncesi En İyi Birey Atama Sayısı: {len(population[0].assignments) if population else 'N/A'}")

            new_population = population[:self.elitism_count]
            
            while len(new_population) < self.population_size:
                parent_pool = population[:max(self.elitism_count + 2, self.population_size // 2)]
                if len(parent_pool) < 2:
                   parent1, parent2 = random.choices(population, k=2) if len(population) >= 2 else (population[0] if population else Individual([]), population[0] if population else Individual([]))
                else:
                   parent1, parent2 = random.sample(parent_pool, 2)
                
                child = self.crossover(parent1, parent2, drones, current_time, no_fly_zones, planner, deliveries) # all_deliveries eklendi
                if random.random() < self.mutation_rate:
                    child = self.mutate(child, drones, deliveries, current_time, no_fly_zones, planner)
                new_population.append(child)

            population = new_population
            
            # Her nesilden sonraki en iyi durumu logla (opsiyonel)
            if population: # Kontrol eklendi
                current_best_fitness_in_gen = max(ind.fitness for ind in population) if population else -float('inf')
                logging.info(f"Nesil {gen+1}: En İyi Fitness = {current_best_fitness_in_gen}")


        for ind in population: ind.calculate_fitness(len(deliveries)) # Son kez fitness hesapla
        best_individual = max(population, key=lambda ind: ind.fitness, default=Individual([], -float('inf')))
        logging.info(f"Optimizasyon tamamlandı. En iyi fitness: {best_individual.fitness}, Atama Sayısı: {len(best_individual.assignments)}")
        return best_individual

    def crossover(self, parent1: Individual, parent2: Individual, 
                  drones: List[Drone], current_time: time, 
                  no_fly_zones: List[NoFlyZone], planner: PathPlanner,
                  all_possible_deliveries: List[DeliveryPoint]) -> Individual: # all_possible_deliveries eklendi
        
        # Ebeveynlerin atadığı teslimatları al (objeler olarak)
        p1_deliveries = [a.delivery for a in parent1.assignments]
        p2_deliveries = [a.delivery for a in parent2.assignments]

        # Eğer ebeveynlerden biri veya ikisi de boşsa, diğerini veya boş bir birey döndür
        if not p1_deliveries and not p2_deliveries:
            return self._create_individual_from_deliveries([], drones, current_time, no_fly_zones, planner)
        if not p1_deliveries:
            return self._create_individual_from_deliveries(p2_deliveries, drones, current_time, no_fly_zones, planner)
        if not p2_deliveries:
            return self._create_individual_from_deliveries(p1_deliveries, drones, current_time, no_fly_zones, planner)

        min_len = min(len(p1_deliveries), len(p2_deliveries))

        child_delivery_order: List[DeliveryPoint]
        if min_len < 2: # Tek noktalı çaprazlama için yetersiz
            # Daha iyi fitness'a sahip ebeveynin teslimat listesini kullan
            chosen_parent_deliveries = p1_deliveries if parent1.fitness >= parent2.fitness else p2_deliveries
            child_delivery_order = chosen_parent_deliveries
        else:
            split_point = random.randint(1, min_len - 1) # min_len-1 dahil
            
            # Çocuk için teslimat sırasını oluştur (Order Crossover (OX1) benzeri bir yaklaşım)
            child_delivery_order = p1_deliveries[:split_point]
            child_delivery_set = {d.id for d in child_delivery_order}

            # İkinci ebeveynden, çocukta henüz olmayan teslimatları sırayla ekle
            for delivery in p2_deliveries:
                if delivery.id not in child_delivery_set:
                    child_delivery_order.append(delivery)
                    child_delivery_set.add(delivery.id) # Eklendikten sonra sete de ekle

        # Çeşitliliği korumak için, `all_possible_deliveries` listesinden çocukta olmayanları da ekleyebiliriz.
        # Bu, GA'nın keşfetmediği teslimatları da denemesini sağlar.
        # Ancak bu, bireyin çok fazla teslimatla başlamasına neden olabilir.
        # Şimdilik ebeveynlerden gelenlerle yetinelim veya `all_possible_deliveries` parametresini
        # `_create_individual_from_deliveries` içinde kullanmak daha mantıklı olabilir.
        # Bu örnekte, çocuk sadece ebeveynlerden gelen genleri (teslimatları) miras alıyor.

        return self._create_individual_from_deliveries(child_delivery_order, drones, current_time, no_fly_zones, planner)


    def mutate(self, individual: Individual, 
               drones: List[Drone], 
               all_deliveries_list: List[DeliveryPoint], 
               current_time: time, 
               no_fly_zones: List[NoFlyZone], 
               planner: PathPlanner) -> Individual:
        
        current_delivery_order = [a.delivery for a in individual.assignments]
        
        if not all_deliveries_list and not current_delivery_order:
            return individual # Mutasyon için malzeme yok

        mutated_delivery_order = current_delivery_order.copy()
        
        # Olası mutasyon operasyonları (oranlar ayarlanabilir)
        action = random.random()

        if action < 0.6 and len(mutated_delivery_order) >= 2:
            # Swap Mutasyonu: İki teslimatın yerini değiştir
            idx1, idx2 = random.sample(range(len(mutated_delivery_order)), 2)
            mutated_delivery_order[idx1], mutated_delivery_order[idx2] = mutated_delivery_order[idx2], mutated_delivery_order[idx1]
        
        elif action < 0.85 and all_deliveries_list: # %25 ihtimalle ekleme dene
            # Teslimat Ekleme Mutasyonu: Atanmamış bir teslimatı rastgele bir yere ekle
            # Bireyin mevcut atamalarındaki teslimatların ID'lerini al
            assigned_ids = {d.id for d in mutated_delivery_order}
            unassigned_deliveries = [d for d in all_deliveries_list if d.id not in assigned_ids]
            
            if unassigned_deliveries:
                delivery_to_add = random.choice(unassigned_deliveries)
                insert_pos = random.randint(0, len(mutated_delivery_order))
                mutated_delivery_order.insert(insert_pos, delivery_to_add)
        
        elif mutated_delivery_order: # Kalan %15 ihtimalle çıkarma dene (eğer listede eleman varsa)
            # Teslimat Çıkarma Mutasyonu: Rastgele bir teslimatı çıkar
            mutated_delivery_order.pop(random.randrange(len(mutated_delivery_order)))
            
        # Mutasyona uğramış teslimat sırasına göre yeni bir birey oluştur (tamir et)
        return self._create_individual_from_deliveries(mutated_delivery_order, drones, current_time, no_fly_zones, planner)