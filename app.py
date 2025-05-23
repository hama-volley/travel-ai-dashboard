# travel_planner_app.py

import streamlit as st
import requests
import json
import streamlit.components.v1 as components
import openai

# --- ページ設定（最初に必ず） ---
st.set_page_config(page_title="旅行プランナーAI", layout="wide")

# --- 手書き風CSS ---
handwritten_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700&display=swap');
body, html, .stApp {
  font-family: 'Zen Maru Gothic', cursive;
  background-color: #fdf6e3;
  color: #333;
}
.stSidebar {
  background-color: #fdf6e3 !important;
  border-right: 2px dashed #ccc;
}
.stButton>button {
  background-color: #fff8dc;
  border: 2px dashed #999;
  border-radius: 8px;
  padding: 0.5em 1em;
  font-weight: bold;
}
.stTextInput>div>input {
  background-color: #fff8dc;
  border: 1px dashed #aaa;
  border-radius: 4px;
}
</style>
"""
st.markdown(handwritten_css, unsafe_allow_html=True)

# --- API キー設定 ---
openai.api_key = st.secrets['OPENAI_API_KEY']
google_key = st.secrets['GOOGLE_API_KEY']
youtube_key = st.secrets.get('YOUTUBE_API_KEY', '')

# --- セッション初期化 ---
if 'itinerary' not in st.session_state:
    st.session_state.itinerary = []
if 'selected' not in st.session_state:
    st.session_state.selected = None

# --- 行程生成 ---
def generate_itinerary(query):
    prompt = (
        "あなたはプロの旅行プランナーです。"
        "以下の要件に基づき、1泊2日の時間付き行程表をJSON配列で返してください。"
        "各要素は {day:int, time:str, spot:str} という辞書形式にしてください。"
    )
    try:
        response = openai.ChatCompletion.create(
            model='gpt-4',
            messages=[
                {'role': 'system', 'content': prompt},
                {'role': 'user', 'content': query}
            ],
            temperature=0.7
        )
        return json.loads(response['choices'][0]['message']['content'])
    except Exception as e:
        st.error(f"行程生成中にエラー: {e}")
        return []

# --- 地図・住所・画像・説明 ---
def get_place_info(name):
    try:
        g = requests.get(
            'https://maps.googleapis.com/maps/api/geocode/json',
            params={'address': name, 'key': google_key}
        ).json().get('results', [])
        addr, lat, lng = ('住所情報なし', None, None)
        if g:
            addr = g[0].get('formatted_address', '')
            loc = g[0]['geometry']['location']
            lat, lng = loc['lat'], loc['lng']

        find = requests.get(
            'https://maps.googleapis.com/maps/api/place/findplacefromtext/json',
            params={'input': name, 'inputtype': 'textquery', 'fields': 'place_id', 'key': google_key}
        ).json().get('candidates', [])

        desc = ''
        photo_url = None
        if find:
            pid = find[0]['place_id']
            det = requests.get(
                'https://maps.googleapis.com/maps/api/place/details/json',
                params={'place_id': pid, 'fields': 'editorial_summary,photos', 'key': google_key}
            ).json().get('result', {})
            desc = det.get('editorial_summary', {}).get('overview', '')
            phs = det.get('photos', [])
            if phs:
                ref = phs[0]['photo_reference']
                photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={ref}&key={google_key}"

        if not desc:
            ai = openai.ChatCompletion.create(
                model='gpt-4',
                messages=[
                    {'role': 'system', 'content': '以下のスポットを100字以内で説明してください。'},
                    {'role': 'user', 'content': name}
                ],
                temperature=0.7
            )
            desc = ai['choices'][0]['message']['content']

        return desc, addr, photo_url, (lat, lng)
    except Exception as e:
        st.error(f"情報取得エラー: {e}")
        return '', '住所情報なし', None, (None, None)

# --- YouTubeリンク ---
def get_youtube(name):
    if not youtube_key:
        return None
    try:
        items = requests.get(
            'https://www.googleapis.com/youtube/v3/search',
            params={'part': 'snippet', 'q': name + ' 観光', 'maxResults': 1, 'type': 'video', 'key': youtube_key}
        ).json().get('items', [])
        if items:
            return f"https://www.youtube.com/watch?v={items[0]['id']['videoId']}"
        return None
    except:
        return None

# --- UI ---
st.sidebar.header('🗒️ 旅行プランAI')
req = st.sidebar.text_input('旅程の要望：', '大阪で1泊2日旅行したい')
if st.sidebar.button('生成'):
    st.session_state.itinerary = generate_itinerary(req)
    st.session_state.selected = None

if st.session_state.itinerary:
    st.sidebar.markdown('---')
    for i, item in enumerate(st.session_state.itinerary):
        day, time, spot = item.get('day', ''), item.get('time', ''), item.get('spot', '')
        label = f"【{day}日目】{time} - {spot}" if day else spot
        if st.sidebar.button(label, key=i):
            st.session_state.selected = {'day': day, 'time': time, 'spot': spot}

st.title('🖋️ 手書き風 旅行プランナーAI')
sel = st.session_state.selected
if sel:
    spot = sel['spot']
    st.header(f"📍 {spot} ({sel['time']})")
    with st.spinner('情報取得中...'):
        desc, addr, img, (lat, lng) = get_place_info(spot)
        yt = get_youtube(spot)
    col1, col2 = st.columns([2, 3])
    with col1:
        st.subheader('📖 説明')
        st.write(desc)
        st.subheader('🚉 アクセス')
        st.write(addr)
        if yt:
            st.markdown(f"[▶️ YouTube動画を見る]({yt})")
    with col2:
        if img:
            st.image(img, caption=spot, use_container_width=True)
        else:
            st.warning('画像が見つかりませんでした')
    if lat and lng:
        map_url = f"https://www.google.com/maps/embed/v1/place?key={google_key}&q={lat},{lng}"
        components.iframe(map_url, height=300, allowfullscreen=True)
    else:
        st.info('地図情報が見つかりませんでした')
else:
    st.info('サイドバーで旅程を生成し、行程を選択してください。')
