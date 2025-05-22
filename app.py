import streamlit as st

# Google APIキーの読み込み
google_key = st.secrets["GOOGLE_API_KEY"]

# デモ用の固定スポット座標（大阪市内）
coords = [
    (34.6937, 135.5023),  # 大阪駅
    (34.6995, 135.4938),  # 梅田スカイビル
    (34.7058, 135.5002)   # グランフロント
]

# --- デバッグログ：座標を表示 ---
st.write("✅ 現在のマップ座標リスト：", coords)

# --- HTML生成 ---
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

# --- 地図の描画 ---
st.markdown("## 🗺️ テスト：大阪の地図を表示")
html = generate_map_html(coords)
st.components.v1.html(html, height=500)
