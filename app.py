import streamlit as st

# ← ここでページ設定
st.set_page_config(layout="wide")

import openai
import requests
...

import urllib.parse
import streamlit.components.v1 as components

# --- カスタムCSS（手書き風） ---
handwritten_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700&display=swap');
body, html, .stApp {
  font-family: 'Zen Maru Gothic', cursive;
  background-color: #fdf6e3;
  color: #333;
}
.stButton>button {
  background-color: #fff8dc;
  color: #333;
  border: 2px dashed #999;
  border-radius: 8px;
  padding: 0.5em 1em;
  font-weight: bold;
}
.stTextInput>div>input {
  background-color: #fff8dc;
  border: 1px dashed #aaa;
}
.stSidebar, .css-1d391kg, .css-1cpxqw2 {
  background-color: #fdf6e3 !important;
  border-right: 2px dashed #ccc;
}
</style>
"""

st.markdown(handwritten_css, unsafe_allow_html=True)

# --- APIキー読み込み ---
openai.api_key = st.secrets["OPENAI_API_KEY"]
google_key = st.secrets["GOOGLE_API_KEY"]

# --- セッション初期化 ---
for key in ["itinerary", "spots", "details"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key != "itinerary" else ""

# --- 観光地抽出 ---
def extract_spots(text):
    res = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "行程表から観光地名だけを順番にリストアップしてください（1行ずつ）。時間・ホテル・食事は除外。"},
            {"role": "user", "content": text},
        ]
    )
    return [s.strip("・-:：") for s in res.choices[0].message['content'].split("\n") if s.strip()]

# --- 地図・画像・説明の取得 ---
def get_place_info(spot):
    find_url = f"https://maps.googleapis.com/maps/api/place/findplacefromtext/json?input={urllib.parse.quote(spot)}&inputtype=textquery&fields=place_id&key={google_key}"
    r = requests.get(find_url).json()
    place_id = r.get("candidates", [{}])[0].get("place_id")
    if not place_id:
        return None, None, None, None

    detail_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=name,formatted_address,photo,editorial_summary&key={google_key}"
    d = requests.get(detail_url).json().get("result", {})

    lat_lng_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=geometry&key={google_key}"
    geo = requests.get(lat_lng_url).json().get("result", {}).get("geometry", {}).get("location", {})
    
    photo_ref = d.get("photos", [{}])[0].get("photo_reference") if d.get("photos") else None
    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=600&photoreference={photo_ref}&key={google_key}" if photo_ref else None

    summary = d.get("editorial_summary", {}).get("overview", "説明が見つかりませんでした")
    access = d.get("formatted_address", "住所不明")
    
    return summary, access, photo_url, geo

# --- UI構築 ---
st.set_page_config(layout="wide")
st.title("🖋️ 手書き風 旅行プランナーAI")

user_input = st.text_input("旅行プランを入力：", "大阪で1泊2日旅行したい")
if st.button("✈️ AIで行程表を生成"):
    res = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "あなたは旅行プランナーです。時間付きの行程表を1泊2日で出力してください。"},
            {"role": "user", "content": user_input}
        ]
    )
    itinerary = res.choices[0].message["content"]
    st.session_state["itinerary"] = itinerary
    st.session_state["spots"] = extract_spots(itinerary)

# --- レイアウト ---
col1, col2 = st.columns([1, 3])

with col1:
    st.sidebar.header("📋 行程表を選択")
    day = 1
    for i, spot in enumerate(st.session_state["spots"]):
        if "2日目" in spot:
            day = 2
        if st.sidebar.button(f"{spot}", key=f"btn_{i}"):
            st.session_state["selected_spot"] = spot

with col2:
    spot = st.session_state.get("selected_spot")
    if spot:
        st.header(f"📍 {spot}")
        with st.spinner("情報を取得中..."):
            desc, access, img, geo = get_place_info(spot)
        
        left, right = st.columns(2)
        with left:
            st.markdown(f"#### 📖 説明（AIで自動生成）")
            st.write(desc)
            st.markdown(f"#### 🚉 アクセス")
            st.write(access)
            st.markdown(f"[YouTubeで観光動画を検索](https://www.youtube.com/results?search_query={urllib.parse.quote(spot + ' 観光')})")
        with right:
            if img:
                st.image(img, caption=spot)
            else:
                st.warning("画像が見つかりませんでした")
        if geo:
            map_url = f"https://www.google.com/maps/embed/v1/place?key={google_key}&q={geo['lat']},{geo['lng']}"
            components.iframe(map_url, height=300)
        else:
            st.info("地図情報が見つかりませんでした")
