"""
Test senaryoları ve performans metrikleri için testler
"""

import pytest
from datetime import time
from typing import List, Tuple

from ..models import Drone, DeliveryPoint, NoFlyZone
from ..data_generator import DataGenerator

class TestMetrics:
    """Test metrikleri için yardımcı sınıf"""
    
    @staticmethod
    def calculate_completion_rate(completed_deliveries: int, total_deliveries: int) -> float:
        """Tamamlanan teslimat yüzdesini hesaplar"""
        return (completed_deliveries / total_deliveries) * 100 if total_deliveries > 0 else 0
    
    @staticmethod
    def calculate_average_energy(drones: List[Drone], initial_batteries: List[int]) -> float:
        """Ortalama enerji tüketimini hesaplar"""
        total_consumption = sum(initial - drone.current_battery 
                              for drone, initial in zip(drones, initial_batteries)
                              if drone.current_battery is not None)
        return total_consumption / len(drones) if drones else 0

def test_scenario_1_data_generation():
    """Senaryo 1 için veri üretimini test eder"""
    generator = DataGenerator()
    
    # Senaryo 1: 5 drone, 20 teslimat, 2 no-fly zone
    drones, deliveries, zones = generator.generate_test_scenario(
        drone_count=5,
        delivery_count=20,
        no_fly_zone_count=2
    )
    
    # Veri miktarları
    assert len(drones) == 5
    assert len(deliveries) == 20
    assert len(zones) == 2
    
    # Drone özellikleri
    for drone in drones:
        assert 1.0 <= drone.max_weight <= 5.0  # 1-5 kg arası taşıma kapasitesi
        assert 5000 <= drone.battery <= 10000  # 5000-10000 mAh arası batarya
        assert 10.0 <= drone.speed <= 20.0     # 10-20 m/s arası hız
    
    # Teslimat noktası özellikleri
    for delivery in deliveries:
        assert 0.1 <= delivery.weight <= 4.0    # 0.1-4.0 kg arası paket ağırlığı
        assert 1 <= delivery.priority <= 5      # 1-5 arası öncelik
        assert delivery.time_window[0] <= delivery.time_window[1]  # Geçerli zaman penceresi
    
    # Uçuş yasağı bölgeleri
    for zone in zones:
        assert len(zone.coordinates) >= 3  # En az 3 köşe noktası (üçgen)
        assert zone.active_time[0] <= zone.active_time[1]  # Geçerli zaman aralığı

def test_scenario_2_data_generation():
    """Senaryo 2 için veri üretimini test eder"""
    generator = DataGenerator()
    
    # Senaryo 2: 10 drone, 50 teslimat, 5 no-fly zone
    drones, deliveries, zones = generator.generate_test_scenario(
        drone_count=10,
        delivery_count=50,
        no_fly_zone_count=5
    )
    
    # Veri miktarları
    assert len(drones) == 10
    assert len(deliveries) == 50
    assert len(zones) == 5
    
    # ID'lerin benzersiz olduğunu kontrol et
    drone_ids = [d.id for d in drones]
    delivery_ids = [d.id for d in deliveries]
    zone_ids = [z.id for z in zones]
    
    assert len(set(drone_ids)) == len(drone_ids)
    assert len(set(delivery_ids)) == len(delivery_ids)
    assert len(set(zone_ids)) == len(zone_ids)

def test_scenario_time_constraints():
    """Zaman kısıtlarını test eder"""
    generator = DataGenerator()
    # Test senaryosu oluştur
    drones, deliveries, zones = generator.generate_test_scenario(5, 20, 2)
    # Teslimat zamanları çalışma saatleri içinde olmalı
    for delivery in deliveries:
        assert time(9, 0) <= delivery.time_window[0] <= time(18, 0)
        assert time(9, 0) <= delivery.time_window[1] <= time(18, 0)
    # Uçuş yasağı bölgeleri çalışma saatleri içinde olmalı
    for zone in zones:
        assert time(0, 0) <= zone.active_time[0] <= time(23, 59)
        assert time(0, 0) <= zone.active_time[1] <= time(23, 59)

def test_drone_capacity_constraints():
    """Drone kapasite kısıtlarını test eder"""
    generator = DataGenerator()
    
    # Test senaryosu oluştur
    drones, deliveries, zones = generator.generate_test_scenario(5, 20, 2)
    
    # Her teslimat en az bir drone tarafından taşınabilmeli
    for delivery in deliveries:
        capable_drones = [d for d in drones if d.can_carry(delivery.weight)]
        assert len(capable_drones) > 0, f"Teslimat {delivery.id} için uygun drone yok"

def test_performance_metrics():
    """Performans metriklerini test eder"""
    generator = DataGenerator()
    
    # Test senaryosu oluştur
    drones, deliveries, zones = generator.generate_test_scenario(5, 20, 2)
    
    # Başlangıç batarya değerlerini kaydet
    initial_batteries = [d.battery for d in drones]
    
    # Örnek tamamlanmış teslimatlar (gerçek implementasyonda bu değerler algoritma tarafından belirlenecek)
    completed_deliveries = 15
    
    # Metrikleri hesapla
    completion_rate = TestMetrics.calculate_completion_rate(completed_deliveries, len(deliveries))
    assert 0 <= completion_rate <= 100
    
    # Her drone için rastgele enerji tüketimi simüle et
    import random
    for drone in drones:
        drone.update_battery(random.randint(0, 5000))
    
    avg_energy = TestMetrics.calculate_average_energy(drones, initial_batteries)
    assert 0 <= avg_energy <= max(initial_batteries)

def test_no_fly_zone_intersection():
    """Uçuş yasağı bölgeleri kesişim kontrolünü test eder"""
    generator = DataGenerator()
    
    # Test senaryosu oluştur
    drones, deliveries, zones = generator.generate_test_scenario(5, 20, 2)
    
    # Test noktaları
    test_routes = [
        ((0.0, 0.0), (100.0, 100.0)),
        ((50.0, 50.0), (150.0, 150.0)),
        ((0.0, 100.0), (100.0, 0.0))
    ]
    
    for zone in zones:
        for start, end in test_routes:
            # Yol kesişim kontrolü çalışmalı
            result = zone.intersects_path(start, end)
            assert isinstance(result, bool)