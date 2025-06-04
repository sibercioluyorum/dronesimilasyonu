"""
Test senaryoları için veri üreteci
"""

import random
from datetime import time
from typing import List, Tuple

try:
    from .models import Drone, DeliveryPoint, NoFlyZone
except ImportError:
    from models import Drone, DeliveryPoint, NoFlyZone

class DataGenerator:
    """Test verileri üreteci"""
    
    @staticmethod
    def generate_scenario_1():
        """Senaryo 1: 5 drone, 20 teslimat, 2 no-fly zone"""
        
        # İstanbul merkezi koordinatları
        center_lat, center_lon = 41.015137, 28.979530
        
        # 5 drone oluştur
        drones = [
            Drone(id=1, max_weight=round(random.uniform(1.0, 5.0), 1), battery=random.randint(5000, 10000), speed=15.0, 
                 start_pos=(center_lat, center_lon)),
            Drone(id=2, max_weight=round(random.uniform(1.0, 5.0), 1), battery=random.randint(5000, 10000), speed=12.0,
                 start_pos=(center_lat, center_lon)),
            Drone(id=3, max_weight=round(random.uniform(1.0, 5.0), 1), battery=random.randint(5000, 10000), speed=10.0,
                 start_pos=(center_lat, center_lon)),
            Drone(id=4, max_weight=round(random.uniform(1.0, 5.0), 1), battery=random.randint(5000, 10000), speed=13.0,
                 start_pos=(center_lat, center_lon)),
            Drone(id=5, max_weight=round(random.uniform(1.0, 5.0), 1), battery=random.randint(5000, 10000), speed=14.0,
                 start_pos=(center_lat, center_lon))
        ]
        
        # 20 teslimat noktası oluştur
        deliveries = []
        for i in range(20):
            lat = center_lat + random.uniform(-0.1, 0.1)
            lon = center_lon + random.uniform(-0.1, 0.1)
            # Sadece senaryo 1 için: 0.1–4.0 kg aralığı
            weight = round(random.uniform(0.1, 4.0), 1)
            priority = random.randint(1, 5)
            start_hour = random.randint(9, 16)
            start_minute = random.choice([0, 15, 30, 45])
            # Zaman penceresi bitişi 18:00'ı aşmasın
            end_hour = min(start_hour + random.randint(2, 4), 18)
            end_minute = 0 if end_hour == 18 else random.choice([0, 15, 30, 45])
            delivery = DeliveryPoint(
                id=i+1,
                pos=(lat, lon),
                weight=weight,
                priority=priority,
                time_window=(time(start_hour, start_minute), time(end_hour, end_minute))
            )
            deliveries.append(delivery)
        
        # 2 yasak bölge oluştur (Havalimanları ve önemli binalar)
        no_fly_zones = [
            # Sabiha Gökçen Havalimanı
            NoFlyZone(
                id=1,
                coordinates=[
                    (40.898652, 29.309155),
                    (40.898652, 29.319155),
                    (40.908652, 29.319155),
                    (40.908652, 29.309155)
                ],
                active_time=(time(0, 0), time(23, 59))
            ),
            # Sultanahmet bölgesi
            NoFlyZone(
                id=2,
                coordinates=[
                    (41.005137, 28.969530),
                    (41.005137, 28.989530),
                    (41.015137, 28.989530),
                    (41.015137, 28.969530)
                ],
                active_time=(time(10, 0), time(16, 0))
            )
        ]
        
        return drones, deliveries, no_fly_zones
    
    @staticmethod
    def generate_scenario_2():
        """Senaryo 2: 10 drone, 50 teslimat, 5 dinamik no-fly zone"""
        
        # İstanbul merkezi koordinatları
        center_lat, center_lon = 41.015137, 28.979530
        
        # 10 drone oluştur
        drones = []
        for i in range(10):
            max_weight = round(random.uniform(1.0, 5.0), 1)
            battery = random.randint(3000, 8000)
            speed = round(random.uniform(10.0, 18.0), 1)
            
            drone = Drone(
                id=i+1,
                max_weight=max_weight,
                battery=battery,
                speed=speed,
                start_pos=(center_lat, center_lon)
            )
            drones.append(drone)
        
        # 50 teslimat noktası oluştur
        deliveries = []
        for i in range(50):
            # Rastgele konum (İstanbul sınırları içinde)
            lat = center_lat + random.uniform(-0.2, 0.2)  # ±22 km
            lon = center_lon + random.uniform(-0.2, 0.2)  # ±22 km
            
            # Rastgele ağırlık (2-18 kg)
            weight = round(random.uniform(2.0, 18.0), 1)
            
            # Rastgele öncelik (1-5)
            priority = random.randint(1, 5)
            
            # Rastgele zaman penceresi (09:00-18:00 arası, en az 1.5 saat fark)
            start_hour = random.randint(9, 16)
            start_minute = random.choice([0, 15, 30, 45])
            # Bitiş saatini ve dakikasını 18:00'ı aşmayacak şekilde ayarla
            max_end_hour = 18
            possible_end_hours = [h for h in range(start_hour + 1, max_end_hour + 1)]
            if not possible_end_hours:
                end_hour = max_end_hour
                end_minute = 0
            else:
                end_hour = min(start_hour + random.randint(1, 3), max_end_hour)
                if end_hour == max_end_hour:
                    end_minute = 0
                else:
                    end_minute = random.choice([0, 15, 30, 45])
            
            delivery = DeliveryPoint(
                id=i+1,
                pos=(lat, lon),
                weight=weight,
                priority=priority,
                time_window=(
                    time(start_hour, start_minute),
                    time(end_hour, end_minute)
                )
            )
            deliveries.append(delivery)
        
        # 5 dinamik yasak bölge oluştur
        no_fly_zones = []
        zone_id = 1
        
        # Havalimanları (sürekli aktif)
        airports = [
            # Sabiha Gökçen
            (40.898652, 29.309155, 0.02),
            # İstanbul Havalimanı
            (41.275278, 28.751944, 0.03)
        ]
        
        for center_lat, center_lon, radius in airports:
            coordinates = [
                (center_lat - radius, center_lon - radius),
                (center_lat - radius, center_lon + radius),
                (center_lat + radius, center_lon + radius),
                (center_lat + radius, center_lon - radius)
            ]
            
            zone = NoFlyZone(
                id=zone_id,
                coordinates=coordinates,
                active_time=(time(0, 0), time(23, 59))
            )
            no_fly_zones.append(zone)
            zone_id += 1
        
        # Dinamik yasak bölgeler (belirli saatlerde aktif)
        dynamic_zones = [
            # Sultanahmet
            (41.005137, 28.979530, 0.01, (10, 0), (16, 0)),
            # Taksim
            (41.036944, 28.985, 0.01, (12, 0), (18, 0)),
            # Kadıköy
            (40.990278, 29.029167, 0.01, (11, 0), (15, 0))
        ]
        
        for center_lat, center_lon, radius, (start_h, start_m), (end_h, end_m) in dynamic_zones:
            coordinates = [
                (center_lat - radius, center_lon - radius),
                (center_lat - radius, center_lon + radius),
                (center_lat + radius, center_lon + radius),
                (center_lat + radius, center_lon - radius)
            ]
            
            zone = NoFlyZone(
                id=zone_id,
                coordinates=coordinates,
                active_time=(time(start_h, start_m), time(end_h, end_m))
            )
            no_fly_zones.append(zone)
            zone_id += 1
        
        return drones, deliveries, no_fly_zones
    
    @staticmethod
    def save_scenario(filename: str,
                     drones: List[Drone],
                     deliveries: List[DeliveryPoint],
                     no_fly_zones: List[NoFlyZone]):
        """Senaryo verilerini dosyaya kaydet"""
        with open(filename, 'w', encoding='utf-8') as f:
            # Dronelar
            f.write("DRONES\n")
            for drone in drones:
                f.write(f"{drone.id},{drone.max_weight},{drone.battery},"
                       f"{drone.speed},{drone.start_pos[0]},{drone.start_pos[1]}\n")
            
            # Teslimat noktaları
            f.write("\nDELIVERIES\n")
            for delivery in deliveries:
                f.write(f"{delivery.id},{delivery.pos[0]},{delivery.pos[1]},"
                       f"{delivery.weight},{delivery.priority},"
                       f"{delivery.time_window[0].strftime('%H:%M')},"
                       f"{delivery.time_window[1].strftime('%H:%M')}\n")
            
            # Yasak bölgeler
            f.write("\nNO_FLY_ZONES\n")
            for zone in no_fly_zones:
                coords = ";".join(f"{lat},{lon}" for lat, lon in zone.coordinates)
                f.write(f"{zone.id},{coords},"
                       f"{zone.active_time[0].strftime('%H:%M')},"
                       f"{zone.active_time[1].strftime('%H:%M')}\n")
    
    @staticmethod
    def load_scenario(filename: str) -> Tuple[List[Drone], List[DeliveryPoint], List[NoFlyZone]]:
        """Senaryo verilerini dosyadan yükle"""
        drones = []
        deliveries = []
        no_fly_zones = []
        
        current_section = None
        
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                if line in ["DRONES", "DELIVERIES", "NO_FLY_ZONES"]:
                    current_section = line
                    continue
                
                if current_section == "DRONES":
                    id_, max_weight, battery, speed, lat, lon = line.split(',')
                    drone = Drone(
                        id=int(id_),
                        max_weight=float(max_weight),
                        battery=int(battery),
                        speed=float(speed),
                        start_pos=(float(lat), float(lon))
                    )
                    drones.append(drone)
                
                elif current_section == "DELIVERIES":
                    (id_, lat, lon, weight, priority,
                     start_time, end_time) = line.split(',')
                    
                    start_h, start_m = map(int, start_time.split(':'))
                    end_h, end_m = map(int, end_time.split(':'))
                    
                    delivery = DeliveryPoint(
                        id=int(id_),
                        pos=(float(lat), float(lon)),
                        weight=float(weight),
                        priority=int(priority),
                        time_window=(
                            time(start_h, start_m),
                            time(end_h, end_m)
                        )
                    )
                    deliveries.append(delivery)
                
                elif current_section == "NO_FLY_ZONES":
                    parts = line.split(',')
                    id_ = int(parts[0])
                    
                    # Koordinatları parse et
                    coord_str = ','.join(parts[1:-2])
                    coord_pairs = coord_str.split(';')
                    coordinates = []
                    for pair in coord_pairs:
                        lat, lon = map(float, pair.split(','))
                        coordinates.append((lat, lon))
                    
                    # Zaman aralığını parse et
                    start_time = parts[-2]
                    end_time = parts[-1]
                    
                    start_h, start_m = map(int, start_time.split(':'))
                    end_h, end_m = map(int, end_time.split(':'))
                    
                    zone = NoFlyZone(
                        id=id_,
                        coordinates=coordinates,
                        active_time=(
                            time(start_h, start_m),
                            time(end_h, end_m)
                        )
                    )
                    no_fly_zones.append(zone)
        
        return drones, deliveries, no_fly_zones
    
    @staticmethod
    def generate_test_scenario(drone_count=5, delivery_count=20, no_fly_zone_count=2):
        """Testler için jenerik senaryo üretici (senaryo 1 veya 2)"""
        if drone_count == 5 and delivery_count == 20 and no_fly_zone_count == 2:
            return DataGenerator.generate_scenario_1()
        elif drone_count == 10 and delivery_count == 50 and no_fly_zone_count == 5:
            return DataGenerator.generate_scenario_2()
        else:
            center_lat, center_lon = 41.015137, 28.979530
            drones = [
                Drone(id=i+1, max_weight=random.uniform(7.0, 20.0), battery=random.randint(3000, 8000), speed=random.uniform(10.0, 18.0), start_pos=(center_lat, center_lon))
                for i in range(drone_count)
            ]
            max_drone_weight = max(d.max_weight for d in drones)
            deliveries = []
            for i in range(delivery_count):
                lat = center_lat + random.uniform(-0.2, 0.2)
                lon = center_lon + random.uniform(-0.2, 0.2)
                # Teslimat ağırlığı, drone'ların max_weight değerini aşmayacak
                weight = round(random.uniform(2.0, max_drone_weight), 1)
                priority = random.randint(1, 5)
                start_hour = random.randint(9, 16)
                start_minute = random.choice([0, 15, 30, 45])
                # Zaman penceresi bitişi 18:00'ı aşmasın
                end_hour = min(start_hour + random.randint(1, 3), 18)
                end_minute = 0 if end_hour == 18 else random.choice([0, 15, 30, 45])
                delivery = DeliveryPoint(
                    id=i+1,
                    pos=(lat, lon),
                    weight=weight,
                    priority=priority,
                    time_window=(time(start_hour, start_minute), time(end_hour, end_minute))
                )
                deliveries.append(delivery)
            no_fly_zones = []
            for i in range(no_fly_zone_count):
                base_lat = center_lat + random.uniform(-0.1, 0.1)
                base_lon = center_lon + random.uniform(-0.1, 0.1)
                radius = 0.01
                coordinates = [
                    (base_lat - radius, base_lon - radius),
                    (base_lat - radius, base_lon + radius),
                    (base_lat + radius, base_lon + radius),
                    (base_lat + radius, base_lon - radius)
                ]
                zone = NoFlyZone(
                    id=i+1,
                    coordinates=coordinates,
                    active_time=(time(9, 0), time(18, 0))
                )
                no_fly_zones.append(zone)
            return drones, deliveries, no_fly_zones
    
    @staticmethod
    def generate_drones(count: int):
        """Testler için 1-5 kg arası kapasiteyle drone üretir"""
        center_lat, center_lon = 41.015137, 28.979530
        drones = [
            Drone(id=i+1, max_weight=random.uniform(1.0, 5.0), battery=random.randint(2000, 5000), speed=random.uniform(10.0, 18.0), start_pos=(center_lat, center_lon))
            for i in range(count)
        ]
        return drones
    
    @staticmethod
    def generate_delivery_points(count: int):
        """Testler için 1-5 kg arası ağırlık ve 09:00-18:00 arası zaman penceresiyle teslimat üretir"""
        center_lat, center_lon = 41.015137, 28.979530
        deliveries = []
        for i in range(count):
            lat = center_lat + random.uniform(-0.1, 0.1)
            lon = center_lon + random.uniform(-0.1, 0.1)
            weight = round(random.uniform(1.0, 5.0), 1)
            priority = random.randint(1, 5)
            start_hour = random.randint(9, 16)
            start_minute = random.choice([0, 15, 30, 45])
            max_end_hour = 18
            possible_end_hours = [h for h in range(start_hour + 1, max_end_hour + 1)]
            if not possible_end_hours:
                end_hour = max_end_hour
                end_minute = 0
            else:
                end_hour = min(start_hour + random.randint(1, 3), max_end_hour)
                end_minute = 0 if end_hour == max_end_hour else random.choice([0, 15, 30, 45])
            delivery = DeliveryPoint(
                id=i+1,
                pos=(lat, lon),
                weight=weight,
                priority=priority,
                time_window=(time(start_hour, start_minute), time(end_hour, end_minute))
            )
            deliveries.append(delivery)
        return deliveries
    
    @staticmethod
    def generate_no_fly_zones(count: int):
        """Testler için 09:00-18:00 arası aktif, küçük kutu şeklinde no-fly zone üretir"""
        center_lat, center_lon = 41.015137, 28.979530
        zones = []
        for i in range(count):
            base_lat = center_lat + random.uniform(-0.1, 0.1)
            base_lon = center_lon + random.uniform(-0.1, 0.1)
            radius = 0.01
            coordinates = [
                (base_lat - radius, base_lon - radius),
                (base_lat - radius, base_lon + radius),
                (base_lat + radius, base_lon + radius),
                (base_lat + radius, base_lon - radius)
            ]
            zone = NoFlyZone(
                id=i+1,
                coordinates=coordinates,
                active_time=(time(9, 0), time(18, 0))
            )
            zones.append(zone)
        return zones

if __name__ == "__main__":
    # Script olarak çalıştırıldığında absolute import kullan
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from models import Drone, DeliveryPoint, NoFlyZone
    # Senaryo 1'i üret ve kaydet
    drones1, deliveries1, zones1 = DataGenerator.generate_scenario_1()
    DataGenerator.save_scenario("scenario_1.txt", drones1, deliveries1, zones1)
    # Senaryo 2'yi üret ve kaydet
    drones2, deliveries2, zones2 = DataGenerator.generate_scenario_2()
    DataGenerator.save_scenario("scenario_2.txt", drones2, deliveries2, zones2)