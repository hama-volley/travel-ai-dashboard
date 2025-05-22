import streamlit as st
import streamlit.components.v1 as components

# --- Google Maps APIキー ---
google_key = st.secrets["GOOGLE_API_KEY"]

# --- ダミー座標（大阪駅あたり） ---
coords = [(34.702485, 135.495951), (34.705512, 135.498302)]

# --- 関数定義 ---
def generate_map_html(coords, color="#FF0000"):
    points = ",\n".join([f"{{lat: {lat}, lng: {lng}}}" for lat, lng in coords])
    html = f"""
    <html>
      <head>
        <script src="https://maps.googleapis.com/maps/api/js?key={google_key}"></script>
        <script>
          function initMap() {{
            var map = new google.maps.Map(document.getElementById('map'), {{
              zoom: 14,
              center: {{lat: {coords[0][0]}, lng: {coords[0][1]}}}
            }});
            var route = new google.maps.Polyline({{
              path: [{points}],
              geodesic: true,
              strokeColor: '{color}',
              strokeOpacity: 1.0,
              strokeWeight: 4
            }});
            route.setMap(map);
            [{points}].forEach(loc => {{
              new google.maps.Marker({{
                position: loc,
                map: map
              }});
            }});
          }}
        </script>
        <style>html, body, #map {{ height: 100%; margin: 0; padding: 0; }}</style>
      </head>
      <body onload="initMap()"><div id="map"></div></body>
    </html>
    """
    return html

# --- 表示 ---
st.title("🗾 マップ表示テスト")
components.html(generate_map_html(coords), height=500)
