"""
Drone teslimat sistemini çalıştıran ve HTML raporu oluşturan ana program
"""

from datetime import time
import json
import os
from typing import List, Dict
import folium
from folium import plugins
import webbrowser

from src.models import Drone, DeliveryPoint, NoFlyZone
from src.algorithms.path_planning import PathPlanner

def create_sample_data():
    """Örnek test verileri oluşturur"""
    
    # Dronelar
    drones = [
        Drone(id=1, max_weight=10.0, battery=5000, speed=15.0, start_pos=(41.015137, 28.979530)),  # İstanbul
        Drone(id=2, max_weight=8.0, battery=4000, speed=12.0, start_pos=(41.015137, 28.979530)),
        Drone(id=3, max_weight=12.0, battery=6000, speed=10.0, start_pos=(41.015137, 28.979530))
    ]
    
    # Teslimat noktaları (İstanbul'un farklı semtleri)
    deliveries = [
        DeliveryPoint(id=1, pos=(41.055137, 29.009530), weight=5.0, priority=3,  # Beşiktaş
                     time_window=(time(9, 0), time(12, 0))),
        DeliveryPoint(id=2, pos=(41.085137, 29.039530), weight=3.0, priority=4,  # Sarıyer
                     time_window=(time(10, 0), time(14, 0))),
        DeliveryPoint(id=3, pos=(41.025137, 28.919530), weight=8.0, priority=5,  # Bakırköy
                     time_window=(time(11, 0), time(15, 0))),
        DeliveryPoint(id=4, pos=(41.045137, 28.999530), weight=4.0, priority=2,  # Şişli
                     time_window=(time(13, 0), time(17, 0))),
        DeliveryPoint(id=5, pos=(40.985137, 28.939530), weight=6.0, priority=4,  # Zeytinburnu
                     time_window=(time(14, 0), time(18, 0)))
    ]
    
    # Uçuş yasağı bölgeleri (Havalimanları ve önemli binalar)
    no_fly_zones = [
        NoFlyZone(id=1,
                 coordinates=[
                     (41.015137, 28.959530),
                     (41.015137, 28.999530),
                     (41.035137, 28.999530),
                     (41.035137, 28.959530)
                 ],
                 active_time=(time(0, 0), time(23, 59))),
        NoFlyZone(id=2,
                 coordinates=[
                     (41.065137, 29.019530),
                     (41.065137, 29.039530),
                     (41.075137, 29.039530),
                     (41.075137, 29.019530)
                 ],
                 active_time=(time(12, 0), time(18, 0)))
    ]
    
    return drones, deliveries, no_fly_zones

def create_html_report(drones: List[Drone],
                      deliveries: List[DeliveryPoint],
                      no_fly_zones: List[NoFlyZone],
                      assignments: List,
                      output_file: str = "drone_report.html"):
    """Sonuçları HTML raporuna dönüştürür"""
    
    # Harita merkezi (İstanbul)
    center_lat, center_lon = 41.015137, 28.979530
    
    # Harita oluştur
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
    
    # Renk paleti
    drone_colors = {
        1: "#FF0000",  # Kırmızı
        2: "#00FF00",  # Yeşil
        3: "#0000FF"   # Mavi
    }
    
    # Her drone için toplam mesafe ve enerji tüketimi
    drone_stats = {d.id: {"distance": 0.0, "energy": 0.0} for d in drones}
    
    # Droneların başlangıç noktasını işaretle
    folium.Marker(
        [center_lat, center_lon],
        popup="Drone Üssü",
        icon=folium.Icon(color='black', icon='home')
    ).add_to(m)
    
    # Teslimat noktalarını ve rotaları ekle
    assigned_deliveries = set()
    for assignment in assignments:
        drone = assignment.drone
        delivery = assignment.delivery
        assigned_deliveries.add(delivery.id)
        
        # Koordinatları ters çevir (folium için lat, lon olarak)
        lat, lon = delivery.pos
        
        # Teslimat noktasını ekle
        folium.Marker(
            [lat, lon],
            popup=f"Teslimat {delivery.id}<br>"
                  f"Ağırlık: {delivery.weight} kg<br>"
                  f"Öncelik: {delivery.priority}<br>"
                  f"Zaman: {delivery.time_window[0].strftime('%H:%M')}-{delivery.time_window[1].strftime('%H:%M')}<br>"
                  f"Varış: {assignment.estimated_time.strftime('%H:%M')}",
            icon=folium.Icon(color='green', icon='info-sign')
        ).add_to(m)
        
        # Rotayı ekle
        route_points = []
        for i in range(len(assignment.route)-1):
            start = assignment.route[i]
            end = assignment.route[i+1]
            # Koordinatları ters çevir
            route_points.extend([[start[0], start[1]], [end[0], end[1]]])
            
            # Mesafe hesapla
            distance = PathPlanner.calculate_distance(start, end)
            drone_stats[drone.id]["distance"] += distance
            
        # Rotayı çiz
        folium.PolyLine(
            route_points,
            weight=2,
            color=drone_colors[drone.id],
            popup=f"Drone {drone.id} - Teslimat {delivery.id}"
        ).add_to(m)
        
        # Enerji tüketimini kaydet
        drone_stats[drone.id]["energy"] += assignment.energy_consumption
    
    # Atanmamış teslimatları ekle
    for delivery in deliveries:
        if delivery.id not in assigned_deliveries:
            # Koordinatları ters çevir
            lat, lon = delivery.pos
            folium.Marker(
                [lat, lon],
                popup=f"Atanmamış Teslimat {delivery.id}<br>"
                      f"Ağırlık: {delivery.weight} kg<br>"
                      f"Öncelik: {delivery.priority}<br>"
                      f"Zaman: {delivery.time_window[0].strftime('%H:%M')}-{delivery.time_window[1].strftime('%H:%M')}",
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(m)
    
    # Yasak bölgeleri ekle
    for zone in no_fly_zones:
        folium.Polygon(
            locations=zone.coordinates,
            popup=f"Yasak Bölge {zone.id}<br>"
                  f"Aktif: {zone.active_time[0].strftime('%H:%M')}-{zone.active_time[1].strftime('%H:%M')}",
            color='red',
            fill=True,
            fill_opacity=0.2
        ).add_to(m)
    
    # Isı haritası ekle (drone yoğunluğunu göstermek için)
    heat_data = []
    for assignment in assignments:
        for point in assignment.route:
            heat_data.append([point[0], point[1], 0.5])
    plugins.HeatMap(heat_data).add_to(m)
    
    # HTML içeriği oluştur
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Drone Teslimat Sistemi Raporu</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .container {{ display: flex; flex-direction: column; }}
            .info-panel {{ margin-bottom: 20px; }}
            .map-panel {{ height: 600px; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
            .stat-box {{ 
                border: 1px solid #ddd;
                padding: 10px;
                border-radius: 5px;
                text-align: center;
                flex: 1;
                margin: 0 10px;
            }}
        </style>
    </head>
    <body>
        <h1>Drone Teslimat Sistemi Raporu</h1>
        <div class="container">
            <div class="info-panel">
                <div class="stats">
                    <div class="stat-box">
                        <h3>Toplam Teslimat</h3>
                        <p>{len(deliveries)}</p>
                    </div>
                    <div class="stat-box">
                        <h3>Tamamlanan</h3>
                        <p>{len(assignments)}</p>
                    </div>
                    <div class="stat-box">
                        <h3>Başarı Oranı</h3>
                        <p>{(len(assignments) / len(deliveries) * 100):.1f}%</p>
                    </div>
                </div>

                <h2>Drone İstatistikleri</h2>
                <table>
                    <tr>
                        <th>ID</th>
                        <th>Maks. Ağırlık</th>
                        <th>Batarya</th>
                        <th>Hız</th>
                        <th>Toplam Mesafe</th>
                        <th>Enerji Tüketimi</th>
                        <th>Kalan Batarya</th>
                    </tr>
    """
    
    # Drone bilgileri
    for drone in drones:
        stats = drone_stats[drone.id]
        remaining_battery = drone.battery - stats["energy"]
        html_content += f"""
                    <tr>
                        <td>{drone.id}</td>
                        <td>{drone.max_weight} kg</td>
                        <td>{drone.battery} mAh</td>
                        <td>{drone.speed} m/s</td>
                        <td>{stats['distance']:.1f} m</td>
                        <td>{stats['energy']:.1f} mAh</td>
                        <td>{remaining_battery:.1f} mAh</td>
                    </tr>
        """
    
    html_content += """
                </table>
                
                <h2>Teslimat Detayları</h2>
                <table>
                    <tr>
                        <th>ID</th>
                        <th>Konum</th>
                        <th>Ağırlık</th>
                        <th>Öncelik</th>
                        <th>Zaman Aralığı</th>
                        <th>Drone</th>
                        <th>Tahmini Varış</th>
                        <th>Mesafe</th>
                        <th>Enerji</th>
                    </tr>
    """
    
    # Teslimat bilgileri
    for delivery in deliveries:
        # Bu teslimat için atamayı bul
        assignment = next(
            (a for a in assignments if a.delivery.id == delivery.id),
            None
        )
        
        drone_id = assignment.drone.id if assignment else "Atanmadı"
        arrival = assignment.estimated_time if assignment else "-"
        
        # Mesafe hesapla
        if assignment:
            distance = sum(
                PathPlanner.calculate_distance(assignment.route[i], assignment.route[i+1])
                for i in range(len(assignment.route)-1)
            )
            energy = assignment.energy_consumption
        else:
            distance = "-"
            energy = "-"
        
        lat, lon = delivery.pos
        location = f"({lat:.6f}, {lon:.6f})"
        
        html_content += f"""
                    <tr>
                        <td>{delivery.id}</td>
                        <td>{location}</td>
                        <td>{delivery.weight} kg</td>
                        <td>{delivery.priority}</td>
                        <td>{delivery.time_window[0].strftime('%H:%M')}-{delivery.time_window[1].strftime('%H:%M')}</td>
                        <td>{drone_id}</td>
                        <td>{arrival.strftime('%H:%M') if arrival != '-' else '-'}</td>
                        <td>{f'{distance:.1f} m' if distance != '-' else '-'}</td>
                        <td>{f'{energy:.1f} mAh' if energy != '-' else '-'}</td>
                    </tr>
        """
    
    html_content += """
                </table>
            </div>
            
            <div class="map-panel">
                <h2>Rota Haritası</h2>
    """
    
    # Haritayı HTML'e ekle
    html_content += m._repr_html_()
    
    html_content += """
            </div>
        </div>
    </body>
    </html>
    """
    
    # HTML dosyasını kaydet
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return output_file

def main():
    """Ana program"""
    # Örnek verileri oluştur
    drones, deliveries, no_fly_zones = create_sample_data()
    
    # Genetik algoritmayı başlat
    optimizer = GeneticOptimizer()
    
    # Optimizasyonu çalıştır
    result = optimizer.optimize(
        drones=drones,
        deliveries=deliveries,
        no_fly_zones=no_fly_zones,
        current_time=time(9, 0)  # Başlangıç zamanı: 09:00
    )
    
    # HTML raporu oluştur
    output_file = create_html_report(
        drones=drones,
        deliveries=deliveries,
        no_fly_zones=no_fly_zones,
        assignments=result.assignments
    )
    
    print(f"Rapor oluşturuldu: {output_file}")
    print("\nÖzet:")
    print(f"Toplam teslimat: {len(deliveries)}")
    print(f"Tamamlanan teslimat: {len(result.assignments)}")
    print(f"Fitness değeri: {result.fitness:.2f}")
    
    # Raporu varsayılan tarayıcıda aç
    webbrowser.open(output_file)

if __name__ == "__main__":
    main()