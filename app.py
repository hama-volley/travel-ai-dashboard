import streamlit as st
import streamlit.components.v1 as components
import requests
import urllib.parse

# --- セットアップ ---
st.set_page_config(layout="wide")
st.title("🌏 旅行プランナーAI - サイドバー式UI")

# --- 初期データ（大阪1泊2日） ---
itinerary = {
    "1日目": ["道頓堀", "通天閣", "なんばグランド花月"],
    "2日目": ["大阪城", "梅田スカイビル", "グランフロント大阪"]
}

# --- 選択管理 ---
if "selected_spot" not in st.session_state:
    st.session_state.selected_spot = None

# --- Google APIキー（secrets.toml に格納） ---
google_key = st.secrets["GOOGLE_API_KEY"]

# --- スポット情報取得関数 ---
def get_place_info(spot):
    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    res = requests.get(url, params={
        "input": spot,
        "inputtype": "textquery",
        "fields": "place_id",
        "key": google_key
    }).json()
    candidates = res.get("candidates", [])
    if not candidates:
        return None, None, None, None
    place_id = candidates[0].get("place_id")

    detail = requests.get("https://maps.googleapis.com/maps/api/place/details/json", params={
        "place_id": place_id,
        "fields": "geometry,photo,name,formatted_address",
        "key": google_key
    }).json().get("result", {})

    loc = detail.get("geometry", {}).get("location", {})
    lat, lng = loc.get("lat"), loc.get("lng")
    photos = detail.get("photos", [])
    photo_url = None
    if photos:
        ref = photos[0].get("photo_reference")
        photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={ref}&key={google_key}"
    return lat, lng, photo_url, detail.get("formatted_address", "")

# --- YouTubeリンク生成 ---
def get_youtube_link(spot):
    return f"https://www.youtube.com/results?search_query={urllib.parse.quote(spot + ' 観光')}"

# --- UI構成 ---
with st.sidebar:
    st.header("🗓 行程表を選択")
    for day, spots in itinerary.items():
        st.subheader(f"📅 {day}")
        for spot in spots:
            if st.button(f"🔸 {spot}"):
                st.session_state.selected_spot = spot

# --- 選択されたスポットを右側で表示 ---
if st.session_state.selected_spot:
    spot = st.session_state.selected_spot
    st.markdown(f"## 📍 {spot}")
    lat, lng, img, address = get_place_info(spot)
    
    col1, col2 = st.columns([2, 3])
    with col1:
        st.markdown("#### 📖 説明（AIで自動生成）")
        st.write(f"{spot}は大阪を代表する観光地のひとつです。歴史・文化・グルメなど、さまざまな魅力が詰まっています。")
        st.markdown(f"**🚃 アクセス：** {address}")
        st.markdown(f"[▶️ YouTubeで観光動画を検索]({get_youtube_link(spot)})")

    with col2:
        if img:
            st.image(img, use_column_width=True)
        else:
            st.warning("画像が見つかりませんでした")

    if lat and lng:
        map_url = f"https://www.google.com/maps/embed/v1/place?key={google_key}&q={lat},{lng}"
        components.iframe(map_url, height=300)

    st.markdown("---")
else:
    st.info("左のサイドバーからスポットを選んでください")

