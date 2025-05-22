import streamlit as st
import requests
import urllib.parse
from openai import OpenAI

# --- APIキー ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
google_key = st.secrets["GOOGLE_API_KEY"]
rakuten_key = st.secrets["RAKUTEN_APP_ID"]

# --- セッション初期化 ---
if "itinerary" not in st.session_state:
    st.session_state["itinerary"] = ""
if "day1_spots" not in st.session_state:
    st.session_state["day1_spots"] = []
if "day2_spots" not in st.session_state:
    st.session_state["day2_spots"] = []

# --- Google API: place_id, lat/lng, photo ---
def get_place_info(spot):
    base_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = {
        "input": spot,
        "inputtype": "textquery",
        "fields": "place_id",
        "key": google_key
    }
    res = requests.get(base_url, params=params).json()
    place_id = res.get("candidates", [{}])[0].get("place_id")
    if not place_id:
        return None, None, None, None

    detail_url = "https://maps.googleapis.com/maps/api/place/details/json"
    res = requests.get(detail_url, params={
        "place_id": place_id,
        "fields": "geometry,photo",
        "key": google_key
    }).json()
    result = res.get("result", {})
    loc = result.get("geometry", {}).get("location", {})
    lat, lng = loc.get("lat"), loc.get("lng")
    photos = result.get("photos", [])
    photo_url = None
    if photos:
        ref = photos[0]["photo_reference"]
        photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={ref}&key={google_key}"
    return place_id, lat, lng, photo_url

# --- Google Map Embed with Polyline (JS) ---
def generate_map_html(coords, color):
    points = ",\n".join([f"{{lat: {lat}, lng: {lng}}}" for lat, lng in coords])
    html = f"""
    <html>
      <head>
        <script src="https://maps.googleapis.com/maps/api/js?key={google_key}"></script>
        <script>
          function initMap() {{
            var map = new google.maps.Map(document.getElementById('map'), {{
              zoom: 13,
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
        <style>
          html, body, #map {{ height: 100%; margin: 0; padding: 0; }}
        </style>
      </head>
      <body onload="initMap()">
        <div id="map"></div>
      </body>
    </html>
    """
    return html
# --- 楽天トラベルAPIで宿泊候補取得 ---
def get_hotels(lat, lng):
    url = "https://app.rakuten.co.jp/services/api/Travel/SimpleHotelSearch/20170426"
    params = {
        "applicationId": rakuten_key,
        "format": "json",
        "latitude": lat,
        "longitude": lng,
        "datumType": 1,
        "hits": 3,
        "searchRadius": 3
    }
    r = requests.get(url, params=params).json()
    return r.get("hotels", [])

# --- YouTube検索リンク ---
def get_youtube_link(spot):
    return f"https://www.youtube.com/results?search_query={urllib.parse.quote(spot + ' 観光')}"

# --- 行程入力と分類 ---
st.set_page_config(layout="wide")
st.title("🌍 超統合 旅行プランナーAI")

user_input = st.text_area("旅行プランを入力", "大阪で1泊2日観光したい")
if st.button("AIで行程生成！"):
    res = client.chat.completions.create(
        model="gpt-4",
        temperature=0.7,
        messages=[
            {"role": "system", "content": "1泊2日の旅行プランを時間帯付きで日本語で作成してください。"},
            {"role": "user", "content": user_input}
        ]
    )
    itinerary = res.choices[0].message.content
    st.session_state["itinerary"] = itinerary

    # 日別分類
    day1, day2 = [], []
    current = None
    for line in itinerary.splitlines():
        if "1日目" in line:
            current = "day1"
        elif "2日目" in line:
            current = "day2"
        elif line.strip():
            if current == "day1":
                day1.append(line.strip("・-:： "))
            elif current == "day2":
                day2.append(line.strip("・-:： "))
    st.session_state["day1_spots"] = day1
    st.session_state["day2_spots"] = day2

# --- 表示 ---
if st.session_state["itinerary"]:
    st.subheader("📝 行程表")
    st.markdown(f"```\n{st.session_state['itinerary']}\n```")

    tab1, tab2 = st.tabs(["🟥 1日目", "🟦 2日目"])
    for label, spots, tab, color in [("1日目", st.session_state["day1_spots"], tab1, "#FF0000"),
                                     ("2日目", st.session_state["day2_spots"], tab2, "#0000FF")]:
        with tab:
            st.markdown(f"### 📍 {label}のスポット")
            coords, infos = [], []
            for spot in spots:
                place_id, lat, lng, photo_url = get_place_info(spot)
                if lat and lng:
                    coords.append((lat, lng))
                infos.append({
                    "spot": spot,
                    "lat": lat,
                    "lng": lng,
                    "photo": photo_url,
                    "youtube": get_youtube_link(spot),
                    "hotels": get_hotels(lat, lng) if lat and lng else []
                })

            if coords:
                html = generate_map_html(coords, color)
                st.components.v1.html(html, height=500)

            for info in infos:
                st.markdown(f"#### {info['spot']}")
                col1, col2 = st.columns([1, 3])
                with col1:
                    if info["photo"]:
                        st.image(info["photo"], width=120)
                with col2:
                    st.markdown(f"[🎥 YouTubeで観光動画を見る]({info['youtube']})")

                if info["hotels"]:
                    with st.expander("🏨 宿泊候補を表示"):
                        for h in info["hotels"]:
                            b = h["hotel"][0]["hotelBasicInfo"]
                            st.markdown(f"**[{b['hotelName']}]({b['hotelInformationUrl']})**")
                            st.image(b["hotelImageUrl"], width=200)
                            st.markdown(f"最安: {b.get('hotelMinCharge', '不明')} 円")
                            st.markdown(f"アクセス: {b.get('access', '情報なし')}")
                            st.markdown("---")

                # 質問欄
                st.markdown("#### 💬 質問してみよう")
                q = st.text_input(f"{info['spot']} について質問：", key=info["spot"])
                if q:
                    ans = client.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": f"{info['spot']} に関する観光案内を丁寧にお願いします。"},
                            {"role": "user", "content": q}
                        ]
                    )
                    st.success(ans.choices[0].message.content)
