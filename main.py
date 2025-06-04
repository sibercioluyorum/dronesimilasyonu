# src/main.py

from datetime import time
import json
import os
from typing import List, Dict, Tuple
import time as timer # `time` modülü ile karışmaması için `timer` olarak adlandırıldı
import webbrowser
import sys
from pathlib import Path
import logging

# Proje kök dizinini Python path'ine ekle
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# Gerekli Kütüphaneler
try:
    import folium
    from folium import plugins
    import matplotlib # models.py için gerekli olabilir
except ImportError:
    print("Lütfen gerekli kütüphaneleri kurun: pip install folium numpy matplotlib")
    sys.exit(1)

# Proje Modülleri
from src.models import Drone, DeliveryPoint, NoFlyZone
from src.algorithms.genetic_algorithm import GeneticAlgorithm
from src.algorithms.path_planning import PathPlanner # PathPlanner'ı import et
from src.data_generator import DataGenerator
from src.visualization import RouteVisualizer

def run_scenario(scenario_num: int,
                 drones: List[Drone],
                 deliveries: List[DeliveryPoint],
                 no_fly_zones: List[NoFlyZone],
                 output_file: str) -> Tuple[dict, float]:
    """Test senaryosunu çalıştırır ve sonuçları döndürür"""
    logging.info(f"Senaryo {scenario_num} başlatılıyor...")
    start_time_exec = timer.time() # `timer` modülünü kullan
    
    optimizer = GeneticAlgorithm(
        population_size=100,  
        generations=50, # PDF'e göre ayarlanabilir
        mutation_rate=0.25,   
        elitism_count=5,
        charging_time_per_mah=0.001 # PDF'te belirtilen şarj süresi faktörü
    )
    
    result = optimizer.optimize(
        drones=drones,
        deliveries=deliveries,
        no_fly_zones=no_fly_zones,
        current_time=time(9, 0) # Başlangıç zamanı
    )
    
    end_time_exec = timer.time() # `timer` modülünü kullan
    execution_time = end_time_exec - start_time_exec
    
    total_deliveries = len(deliveries)
    completed_deliveries = len(result.assignments)
    completion_rate = (completed_deliveries / total_deliveries) * 100 if total_deliveries > 0 else 0.0
    
    total_energy = sum(a.energy_consumption for a in result.assignments)
    
    # Toplam mesafe hesaplaması (PathPlanner.calculate_distance kullanarak)
    total_distance = 0.0
    for assignment in result.assignments:
        if assignment.route and len(assignment.route) > 1:
            for i in range(len(assignment.route) - 1):
                point1 = assignment.route[i]
                point2 = assignment.route[i+1]
                total_distance += PathPlanner.calculate_distance(point1, point2)
                
    rule_violations = sum(a.rule_violations for a in result.assignments)
    
    avg_energy = total_energy / completed_deliveries if completed_deliveries > 0 else 0.0
    
    metrics = {
        "scenario": scenario_num,
        "total_deliveries": total_deliveries,
        "completed_deliveries": completed_deliveries,
        "completion_rate": completion_rate, #
        "total_distance_meters": total_distance, #
        "total_energy_mah": total_energy, #
        "avg_energy_per_delivery_mah": avg_energy, #
        "rule_violations": rule_violations, #
        "execution_time_seconds": execution_time, #
        "fitness_score": result.fitness #
    }
    
    logging.info(f"Senaryo {scenario_num} tamamlandı. Süre: {execution_time:.2f} saniye.")
    
    # Görselleştirme
    logging.info(f"{output_file} için harita oluşturuluyor...")
    center_lat, center_lon = 41.015137, 28.979530 # İstanbul merkezi
    visualizer = RouteVisualizer(center=(center_lat, center_lon), zoom=11)
    
    # NoFlyZone ekleme:
    # Eğer NoFlyZone nesnelerinizde 'id' attribute'u varsa add_no_fly_zones kullanın.
    # Eğer yoksa veya DataGenerator ID atamıyorsa, add_no_fly_zones_without_id kullanın.
    # Bir önceki yanıtta add_no_fly_zones_without_id önerilmişti.
    if hasattr(no_fly_zones[0] if no_fly_zones else None, 'id'):
         visualizer.add_no_fly_zones(no_fly_zones)
    else:
         visualizer.add_no_fly_zones_without_id(no_fly_zones)
         
    visualizer.add_delivery_points(deliveries)
    # add_routes metoduna 'drones' listesini (drones_info olarak) gönder
    visualizer.add_routes(result.assignments, drones) 
    visualizer.add_heatmap(deliveries)
    visualizer.save(output_file)
    
    return metrics, execution_time

def main():
    """Ana program"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
    
    generator = DataGenerator() 
    
    # Senaryo 1
    logging.info("Senaryo 1 verileri üretiliyor...")
    drones1, deliveries1, zones1 = generator.generate_scenario_1()
    metrics1, time1 = run_scenario(1, drones1, deliveries1, zones1, "scenario_1_results.html")
    logging.info(f"Senaryo 1 Sonuçları: Tamamlanan Teslimat: {metrics1['completed_deliveries']}/{metrics1['total_deliveries']} ({metrics1['completion_rate']:.1f}%)")
    logging.info(f"Toplam Mesafe: {metrics1['total_distance_meters']/1000:.1f} km, Ortalama Enerji: {metrics1['avg_energy_per_delivery_mah']:.0f} mAh, Çalışma Süresi: {time1:.2f} sn")
    
    # Senaryo 2
    logging.info("Senaryo 2 verileri üretiliyor...")
    drones2, deliveries2, zones2 = generator.generate_scenario_2()
    metrics2, time2 = run_scenario(2, drones2, deliveries2, zones2, "scenario_2_results.html")
    logging.info(f"Senaryo 2 Sonuçları: Tamamlanan Teslimat: {metrics2['completed_deliveries']}/{metrics2['total_deliveries']} ({metrics2['completion_rate']:.1f}%)")
    logging.info(f"Toplam Mesafe: {metrics2['total_distance_meters']/1000:.1f} km, Ortalama Enerji: {metrics2['avg_energy_per_delivery_mah']:.0f} mAh, Çalışma Süresi: {time2:.2f} sn")
    
    results = {"scenario_1": metrics1, "scenario_2": metrics2}
    with open("results.json", "w", encoding='utf-8') as f: # encoding eklendi
        json.dump(results, f, indent=2, ensure_ascii=False) # ensure_ascii eklendi
    
    logging.info("Sonuçlar kaydedildi ve haritalar oluşturuldu.")
    
    try:
        # Mutlak yolları kullanarak tarayıcıda açmayı dene
        report1_path = os.path.abspath("scenario_1_results.html")
        report2_path = os.path.abspath("scenario_2_results.html")
        webbrowser.open(f"file://{report1_path}")
        webbrowser.open(f"file://{report2_path}")
    except Exception as e:
        logging.warning(f"Haritalar tarayıcıda otomatik açılamadı: {e}. Lütfen manuel olarak açın.")

# Kullanıcıdan gelen özel veri setiyle simülasyon
def run_custom_scenario():
    drones = [
        {"id": 1, "max_weight": 4.0, "battery": 12000, "speed": 8.0, "start_pos": (10, 10)},
        {"id": 2, "max_weight": 3.5, "battery": 10000, "speed": 10.0, "start_pos": (20, 30)},
        {"id": 3, "max_weight": 5.0, "battery": 15000, "speed": 7.0, "start_pos": (50, 50)},
        {"id": 4, "max_weight": 2.0, "battery": 8000, "speed": 12.0, "start_pos": (80, 20)},
        {"id": 5, "max_weight": 6.0, "battery": 20000, "speed": 5.0, "start_pos": (40, 70)}
    ]
    deliveries = [
        {"id": 1, "pos": (15, 25), "weight": 1.5, "priority": 3, "time_window": (0, 60)},
        {"id": 2, "pos": (30, 40), "weight": 2.0, "priority": 5, "time_window": (0, 30)},
        {"id": 3, "pos": (70, 80), "weight": 3.0, "priority": 2, "time_window": (20, 80)},
        {"id": 4, "pos": (90, 10), "weight": 1.0, "priority": 4, "time_window": (10, 40)},
        {"id": 5, "pos": (45, 60), "weight": 4.0, "priority": 1, "time_window": (30, 90)},
        {"id": 6, "pos": (25, 15), "weight": 2.5, "priority": 3, "time_window": (0, 50)},
        {"id": 7, "pos": (60, 30), "weight": 1.0, "priority": 5, "time_window": (5, 25)},
        {"id": 8, "pos": (85, 90), "weight": 3.5, "priority": 2, "time_window": (40, 100)},
        {"id": 9, "pos": (10, 80), "weight": 2.0, "priority": 4, "time_window": (15, 45)},
        {"id": 10, "pos": (95, 50), "weight": 1.5, "priority": 3, "time_window": (0, 60)},
        {"id": 11, "pos": (55, 20), "weight": 0.5, "priority": 5, "time_window": (0, 20)},
        {"id": 12, "pos": (35, 75), "weight": 2.0, "priority": 1, "time_window": (50, 120)},
        {"id": 13, "pos": (75, 40), "weight": 3.0, "priority": 3, "time_window": (10, 50)},
        {"id": 14, "pos": (20, 90), "weight": 1.5, "priority": 4, "time_window": (30, 70)},
        {"id": 15, "pos": (65, 65), "weight": 4.5, "priority": 2, "time_window": (25, 75)},
        {"id": 16, "pos": (40, 10), "weight": 2.0, "priority": 5, "time_window": (0, 30)},
        {"id": 17, "pos": (5, 50), "weight": 1.0, "priority": 3, "time_window": (15, 55)},
        {"id": 18, "pos": (50, 85), "weight": 3.0, "priority": 1, "time_window": (60, 100)},
        {"id": 19, "pos": (80, 70), "weight": 2.5, "priority": 4, "time_window": (20, 60)},
        {"id": 20, "pos": (30, 55), "weight": 1.5, "priority": 2, "time_window": (40, 80)}
    ]
    no_fly_zones = [
        {
            "id": 1,
            "coordinates": [(40, 30), (60, 30), (60, 50), (40, 50)],
            "active_time": (0, 120)
        },
        {
            "id": 2,
            "coordinates": [(70, 10), (90, 10), (90, 30), (70, 30)],
            "active_time": (30, 90)
        },
        {
            "id": 3,
            "coordinates": [(10, 60), (30, 60), (30, 80), (10, 80)],
            "active_time": (0, 60)
        }
    ]
    # Model nesnelerine dönüştür
    drone_objs = [Drone(**d) for d in drones]
    from datetime import time as dtime
    def convert_time_window(tw):
        # (başlangıç, bitiş) dakikadan -> (datetime.time, datetime.time)
        start = dtime(hour=tw[0] // 60, minute=tw[0] % 60)
        end = dtime(hour=tw[1] // 60, minute=tw[1] % 60)
        return (start, end)
    delivery_objs = []
    for dp in deliveries:
        dp = dict(dp)
        dp["time_window"] = convert_time_window(dp["time_window"])
        delivery_objs.append(DeliveryPoint(**dp))
    def convert_zone_time_window(tw):
        start = dtime(hour=tw[0] // 60, minute=tw[0] % 60)
        end = dtime(hour=tw[1] // 60, minute=tw[1] % 60)
        return (start, end)
    zone_objs = []
    for z in no_fly_zones:
        z = dict(z)
        z["active_time"] = convert_zone_time_window(z["active_time"])
        zone_objs.append(NoFlyZone(**z))
    metrics, exec_time = run_scenario(99, drone_objs, delivery_objs, zone_objs, "custom_scenario_results.html")
    print(f"Özel Senaryo Sonuçları: Tamamlanan Teslimat: {metrics['completed_deliveries']}/{metrics['total_deliveries']} ({metrics['completion_rate']:.1f}%)")
    print(f"Toplam Mesafe: {metrics['total_distance_meters']/1000:.1f} km, Ortalama Enerji: {metrics['avg_energy_per_delivery_mah']:.0f} mAh, Çalışma Süresi: {exec_time:.2f} sn")

if __name__ == "__main__":
    main()
    run_custom_scenario()