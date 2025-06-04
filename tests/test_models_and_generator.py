"""
Veri yapıları ve veri üreteci için test dosyası
"""

import pytest
from datetime import time

from ..models import Drone, DeliveryPoint, NoFlyZone
from ..data_generator import DataGenerator

def test_drone_initialization():
    """Drone sınıfının doğru şekilde başlatıldığını test eder"""
    drone = Drone(
        id=1,
        max_weight=5.0,
        battery=10000,
        speed=15.0,
        start_pos=(0.0, 0.0)
    )
    
    assert drone.id == 1
    assert drone.max_weight == 5.0
    assert drone.battery == 10000
    assert drone.speed == 15.0
    assert drone.start_pos == (0.0, 0.0)
    assert drone.current_battery == 10000  # Başlangıçta batarya dolu olmalı

def test_drone_energy_calculation():
    """Drone'un enerji hesaplamalarını test eder"""
    drone = Drone(
        id=1,
        max_weight=5.0,
        battery=10000,
        speed=15.0,
        start_pos=(0.0, 0.0)
    )
    
    # 100m mesafe, 1kg yük için enerji hesaplaması
    energy = drone.calculate_energy_consumption(distance=100, weight=1.0)
    assert energy > 0  # Enerji pozitif olmalı
    assert drone.has_enough_battery(energy)  # Yeterli şarj olmalı
    
    # Batarya kapasitesinden fazla enerji gerektiğinde
    assert not drone.has_enough_battery(20000)

def test_delivery_point_time_window():
    """Teslimat noktası zaman penceresi kontrollerini test eder"""
    delivery = DeliveryPoint(
        id=1,
        pos=(100.0, 100.0),
        weight=2.0,
        priority=3,
        time_window=(time(10, 0), time(11, 0))
    )
    
    # Zaman penceresi içinde
    assert delivery.is_time_valid(time(10, 30))
    
    # Zaman penceresi dışında
    assert not delivery.is_time_valid(time(9, 59))
    assert not delivery.is_time_valid(time(11, 1))

def test_no_fly_zone_point_containment():
    """Uçuş yasağı bölgesinin nokta içerme kontrolünü test eder"""
    zone = NoFlyZone(
        id=1,
        coordinates=[(0.0, 0.0), (0.0, 10.0), (10.0, 10.0), (10.0, 0.0)],
        active_time=(time(9, 0), time(17, 0))
    )
    
    # Bölge içindeki nokta
    assert zone.contains_point((5.0, 5.0))
    
    # Bölge dışındaki noktalar
    assert not zone.contains_point((-1.0, -1.0))
    assert not zone.contains_point((11.0, 11.0))

def test_data_generator():
    """Veri üretecinin temel fonksiyonlarını test eder"""
    generator = DataGenerator()
    
    # Drone üretimi testi
    drones = generator.generate_drones(5)
    assert len(drones) == 5
    assert all(isinstance(d, Drone) for d in drones)
    assert len(set(d.id for d in drones)) == 5  # ID'ler benzersiz olmalı
    
    # Teslimat noktası üretimi testi
    deliveries = generator.generate_delivery_points(10)
    assert len(deliveries) == 10
    assert all(isinstance(d, DeliveryPoint) for d in deliveries)
    assert len(set(d.id for d in deliveries)) == 10  # ID'ler benzersiz olmalı
    
    # Uçuş yasağı bölgesi üretimi testi
    zones = generator.generate_no_fly_zones(3)
    assert len(zones) == 3
    assert all(isinstance(z, NoFlyZone) for z in zones)
    assert len(set(z.id for z in zones)) == 3  # ID'ler benzersiz olmalı

def test_full_scenario_generation():
    """Tam senaryo üretimini test eder"""
    generator = DataGenerator()
    
    # Senaryo 1 test
    drones, deliveries, zones = generator.generate_test_scenario(
        drone_count=5,
        delivery_count=20,
        no_fly_zone_count=2
    )
    
    assert len(drones) == 5
    assert len(deliveries) == 20
    assert len(zones) == 2
    
    # Tüm nesnelerin doğru tipte olduğunu kontrol et
    assert all(isinstance(d, Drone) for d in drones)
    assert all(isinstance(d, DeliveryPoint) for d in deliveries)
    assert all(isinstance(z, NoFlyZone) for z in zones)