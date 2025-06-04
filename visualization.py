# src/visualization.py

from typing import List, Tuple, Dict
import folium
from folium import plugins
import logging # Eksik import eklendi

# Proje içindeki diğer modüllerden doğru ve standart göreceli importlar
# Bu yollar, dosya yapınızın `src` altında `models.py` ve `algorithms/genetic_algorithm.py`
# şeklinde olduğunu varsayar.
try:
    from .models import Drone, DeliveryPoint, NoFlyZone
    from .algorithms.genetic_algorithm import DeliveryAssignment
except ImportError as e:
    logging.error(f"visualization.py: Kritik modül import hatası: {e}. "
                  "Lütfen proje yapınızı ve Python PATH'inizi kontrol edin. "
                  "VS Code'da çalışma alanınızın kök dizinini doğru ayarladığınızdan emin olun.")
    # Bu aşamada programın düzgün çalışması beklenmez, ancak Pylance'a yol göstermek için
    # tipleri `Any` olarak tanımlayabilir veya hata verip çıkmasını sağlayabiliriz.
    # En iyi çözüm, importların doğru çalışmasını sağlamaktır.
    # Bu satırları kaldırıyoruz çünkü Pylance'ı yanıltıyorlar:
    # Drone, DeliveryPoint, NoFlyZone, DeliveryAssignment = object, object, object, object
    # Bunun yerine, eğer importlar gerçekten başarısız olursa, programın daha erken bir aşamada
    # hata vermesi daha sağlıklıdır. Şimdilik, yukarıdaki try-except yapısı
    # sadece bir loglama ve olası bir geliştirme notu olarak kalabilir.
    # Asıl çözüm, Pylance'ın ve Python'ın importları doğru yapmasını sağlamaktır.
    # Eğer yukarıdaki importlar çalışmıyorsa, aşağıdaki kodlar da tip hataları verecektir.
    pass


class RouteVisualizer:
    """Rota görselleştirme sınıfı"""
    
    def __init__(self, center: Tuple[float, float] = (41.015137, 28.979530), zoom: int = 11):
        self.map = folium.Map(
            location=center,
            zoom_start=zoom,
            control_scale=True,
            tiles="OpenStreetMap"
        )
        
        self.colors = [
            '#E6194B', '#3CB44B', '#FFE119', '#4363D8', '#F58231', 
            '#911EB4', '#46F0F0', '#F032E6', '#BCF60C', '#FABEBE',
            '#008080', '#E6BEFF', '#9A6324', '#FFFAC8', '#800000',
            '#AAFFC3', '#808000', '#FFD8B1', '#000075', '#A9A9A9',
            '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF' 
        ]
    
    def add_delivery_points(self, points: List[DeliveryPoint]):
        for point in points:
            popup_html = (f'<b>Teslimat ID: {point.id}</b><br>'
                          f'Ağırlık: {point.weight:.2f} kg<br>'
                          f'Öncelik: {point.priority}<br>'
                          f'Zaman Aralığı: {point.time_window[0].strftime("%H:%M")}-{point.time_window[1].strftime("%H:%M")}')
            folium.CircleMarker(
                location=point.pos,
                radius=7,
                color='#2E8B57', 
                fill=True,
                fill_color='#32CD32', 
                fill_opacity=0.8,
                tooltip=f'Teslimat {point.id}',
                popup=folium.Popup(popup_html, max_width=300)
            ).add_to(self.map)
    
    def add_no_fly_zones(self, zones: List[NoFlyZone]):
        """ID'si olan NFZ'leri ekler"""
        for zone in zones:
            popup_html = (f'<b>Yasak Bölge ID: {getattr(zone, "id", "N/A")}</b><br>'
                          f'Aktif: {zone.active_time[0].strftime("%H:%M")}-{zone.active_time[1].strftime("%H:%M")}')
            folium.Polygon(
                locations=zone.coordinates,
                color='darkred',
                fill=True,
                fill_color='red',
                fill_opacity=0.3,
                tooltip=f'Yasak Bölge {getattr(zone, "id", "")}',
                popup=folium.Popup(popup_html, max_width=300)
            ).add_to(self.map)

    def add_no_fly_zones_without_id(self, zones: List[NoFlyZone]):
        """ID'si olmayan veya önemsiz olan NFZ'leri ekler"""
        for zone_idx, zone in enumerate(zones):
            popup_html = (f'<b>Yasak Bölge (No: {zone_idx + 1})</b><br>'
                          f'Aktif: {zone.active_time[0].strftime("%H:%M")}-{zone.active_time[1].strftime("%H:%M")}')
            folium.Polygon(
                locations=zone.coordinates,
                color='darkred',
                fill=True,
                fill_color='red',
                fill_opacity=0.3,
                tooltip=f'Yasak Bölge (No: {zone_idx + 1})',
                popup=folium.Popup(popup_html, max_width=300)
            ).add_to(self.map)
    
    def add_routes(self, assignments: List[DeliveryAssignment], drones_info: List[Drone]):
        drone_colors: Dict[int, str] = {} 
        color_idx = 0

        if drones_info:
            base_pos = drones_info[0].start_pos
            folium.Marker(
                location=base_pos,
                popup="<b>Drone Üssü</b>",
                icon=folium.Icon(color='black', icon='industry', prefix='fa')
            ).add_to(self.map)
        
        for assignment in assignments:
            drone_id_val = assignment.drone.id
            if drone_id_val is None: # Pratikta olmamalı ama kontrol ekleyelim
                logging.warning("Atamada drone ID bulunamadı, rota çizilemiyor.")
                continue

            if drone_id_val not in drone_colors:
                drone_colors[drone_id_val] = self.colors[color_idx % len(self.colors)]
                color_idx += 1
            
            color = drone_colors[drone_id_val]
            
            if assignment.route and len(assignment.route) > 1:
                popup_html_route = (f'<b>Drone ID: {drone_id_val}</b><br>'
                                    f'Teslimat ID: {assignment.delivery.id}<br>'
                                    f'Varış: {assignment.estimated_time.strftime("%H:%M")}<br>'
                                    f'Enerji: {assignment.energy_consumption:.1f} mAh')
                folium.PolyLine(
                    locations=assignment.route,
                    color=color,
                    weight=3,
                    opacity=0.7,
                    tooltip=f'Drone {drone_id_val} -> Teslimat {assignment.delivery.id}',
                    popup=folium.Popup(popup_html_route, max_width=300)
                ).add_to(self.map)
                
                folium.CircleMarker(
                    location=assignment.route[0],
                    radius=4,
                    color=color,
                    fill=True,
                    fill_color='white',
                    fill_opacity=0.9,
                    tooltip=f'Drone {drone_id_val} Rota Başlangıcı'
                ).add_to(self.map)
    
    def add_heatmap(self, points: List[DeliveryPoint]):
        if not points:
            return
        # hasattr ile kontrol, DeliveryPoint tipinin doğru import edildiğini varsayar
        data = [[p.pos[0], p.pos[1]] for p in points if hasattr(p, 'pos') and p.pos] 
        if not data: return

        try:
            plugins.HeatMap(data, radius=15).add_to(self.map)
        except Exception as e:
            logging.error(f"Heatmap eklenirken hata: {e}")

    def save(self, filename: str):
        try:
            self.map.save(filename)
            logging.info(f"Harita '{filename}' olarak başarıyla kaydedildi.")
        except Exception as e:
            logging.error(f"Harita kaydedilirken hata oluştu: {e}")