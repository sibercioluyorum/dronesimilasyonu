"""
Test senaryosu ile algoritmaları kontrol et
"""

from datetime import time
from src.models import Drone, DeliveryPoint, NoFlyZone
from src.algorithms.genetic_algorithm import GeneticOptimizer
from src.algorithms.path_planning import PathPlanner

def run_test():
    """Basit test senaryosu"""
    # Tek bir drone
    drone = Drone(
        id=1,
        max_weight=10.0,
        battery=5000,
        speed=15.0,
        start_pos=(41.015137, 28.979530)  # İstanbul merkez
    )
    
    # İki teslimat noktası
    deliveries = [
        DeliveryPoint(
            id=1,
            pos=(41.055137, 29.009530),  # Beşiktaş
            weight=5.0,
            priority=3,
            time_window=(time(9, 0), time(12, 0))
        ),
        DeliveryPoint(
            id=2,
            pos=(41.085137, 29.039530),  # Sarıyer
            weight=3.0,
            priority=4,
            time_window=(time(10, 0), time(14, 0))
        )
    ]
    
    # Bir yasak bölge
    no_fly_zones = [
        NoFlyZone(
            id=1,
            coordinates=[
                (41.035137, 28.989530),
                (41.035137, 29.009530),
                (41.045137, 29.009530),
                (41.045137, 28.989530)
            ],
            active_time=(time(0, 0), time(23, 59))
        )
    ]
    
    print("\nTest senaryosu başlatılıyor...")
    print(f"Drone: {drone.id} (kapasite: {drone.max_weight} kg, batarya: {drone.battery} mAh)")
    print(f"Teslimat noktaları: {len(deliveries)}")
    print(f"Yasak bölgeler: {len(no_fly_zones)}")
    
    # Path planner test
    planner = PathPlanner(no_fly_zones)
    
    print("\nRota planlaması test ediliyor...")
    for delivery in deliveries:
        print(f"\nTeslimat {delivery.id} için rota aranıyor...")
        route = planner.find_path(
            drone.start_pos,
            delivery.pos,
            time(9, 0)
        )
        
        if route:
            print(f"Rota bulundu: {len(route)} nokta")
            for i, point in enumerate(route):
                print(f"Nokta {i+1}: ({point[0]:.6f}, {point[1]:.6f})")
        else:
            print("Rota bulunamadı!")
    
    # Genetik algoritma test
    print("\nGenetik algoritma test ediliyor...")
    optimizer = GeneticOptimizer(
        population_size=10,  # Test için küçük popülasyon
        generations=5,       # Test için az nesil
        mutation_rate=0.2,
        elitism_count=2
    )
    
    result = optimizer.optimize(
        drones=[drone],
        deliveries=deliveries,
        no_fly_zones=no_fly_zones,
        current_time=time(9, 0)
    )
    
    print("\nOptimizasyon sonuçları:")
    print(f"Tamamlanan teslimat: {len(result.assignments)}/{len(deliveries)}")
    print(f"Fitness değeri: {result.fitness:.2f}")
    
    for assignment in result.assignments:
        print(f"\nTeslimat {assignment.delivery.id}:")
        print(f"Drone: {assignment.drone.id}")
        print(f"Varış zamanı: {assignment.estimated_time.strftime('%H:%M')}")
        print(f"Enerji tüketimi: {assignment.energy_consumption:.1f} mAh")
        print(f"Rota uzunluğu: {len(assignment.route)} nokta")

if __name__ == "__main__":
    run_test()