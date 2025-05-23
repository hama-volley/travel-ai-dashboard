# travel_planner_app.py

import streamlit as st
import requests
import json
import streamlit.components.v1 as components
from openai import OpenAI
from streamlit_lottie import st_lottie
import re

# --- ページ設定 ---
st.set_page_config(page_title="旅行プランナーAI", layout="wide")

# --- CSS（Delancy風） ---
delancy_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700&display=swap');
body, html, .stApp {
  font-family: 'Zen Maru Gothic', sans-serif;
  background-color: #FAF3E0;
  color: #333;
}
.stSidebar {
  background-color: #FAF3E0 !important;
  border-right: 2px solid #A8C1A1;
}
.stButton>button {
  background-color: #A8C1A1;
  color: #FFFFFF;
  border: none;
  border-radius: 8px;
  padding: 0.5em 1em;
  font-weight: bold;
  transition: 0.3s;
}
.stButton>button:hover {
  background-color: #8DAE90;
}
.stTextInput>div>input {
  background-color: #FFFFFF;
  border: 1px solid #A8C1A1;
  border-radius: 4px;
}
</style>
"""
st.markdown(delancy_css, unsafe_allow_html=True)

# --- Lottie ---
def load_lottieurl(url):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

animation = load_lottieurl("https://assets9.lottiefiles.com/private_files/lf30_m6j5igxb.json")

# --- API設定 ---
client = OpenAI(api_key=st.secrets['OPENAI_API_KEY'])
google_key = st.secrets['GOOGLE_API_KEY']
youtube_key = st.secrets.get('YOUTUBE_API_KEY', '')

# --- セッション初期化 ---
if 'itinerary' not in st.session_state:
    st.session_state.itinerary = []
if 'selected' not in st.session_state:
    st.session_state.selected = None

# --- JSON抽出 ---
def extract_json_block(text):
    match = re.search(r"```(?:json)?\\s*(\[.*?\])\\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    match = re.search(r"(\[\s*{.*?}\s*\])", text, re.DOTALL)
    return match.group(1) if match else text

# --- 行程生成 ---
def generate_itinerary(query):
    prompt = (
        "あなたはプロの旅行プランナーです。"
        "以下の要件に基づき、1泊2日の旅行行程をJSON配列形式で出力してください。"
        "出力は次の形式に従ってください: [{\"day\": 1, \"time\": \"9:00\", \"spot\": \"大阪城\"}, ...]"
    )
    try:
        response = client.chat.completions.create(
            model='gpt-4',
            messages=[
                {'role': 'system', 'content': prompt},
                {'role': 'user', 'content': query}
            ],
            temperature=0.7
        )
        content = response.choices[0].message.content.strip()
        if not content:
            st.warning('OpenAIの応答が空でした。')
            return []

        cleaned = extract_json_block(content)
        return json.loads(cleaned)
    except json.JSONDecodeError as je:
        st.error(f"JSON読み込みエラー: {je}")
        st.text(content)
        return []
    except Exception as e:
        st.error(f"行程生成中にエラー: {e}")
        return []

# --- 場所情報取得 ---
def get_place_info(name):
    try:
        # 明示的に "日本" をつけて曖昧さを回避
        search_name = name + " 日本"

        find = requests.get(
            'https://maps.googleapis.com/maps/api/place/findplacefromtext/json',
            params={'input': search_name, 'inputtype': 'textquery', 'fields': 'place_id', 'key': google_key}
        ).json().get('candidates', [])

        pid = find[0]['place_id'] if find else None

        desc = ''
        photo_url = None
        addr, lat, lng = '住所情報なし', None, None

        if pid:
            det = requests.get(
                'https://maps.googleapis.com/maps/api/place/details/json',
                params={
                    'place_id': pid,
                    'fields': 'editorial_summary,photos,geometry,formatted_address,name',
                    'key': google_key
                }
            ).json().get('result', {})

            desc = det.get('editorial_summary', {}).get('overview', '')
            addr = det.get('formatted_address', '住所情報なし')
            loc = det.get('geometry', {}).get('location', {})
            lat, lng = loc.get('lat'), loc.get('lng')

            phs = det.get('photos', [])
            if phs:
                ref = phs[0]['photo_reference']
                photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={ref}&key={google_key}"

        if not desc:
            ai = client.chat.completions.create(
                model='gpt-4',
                messages=[
                    {'role': 'system', 'content': '以下のスポットを100字以内で説明してください。'},
                    {'role': 'user', 'content': name}
                ],
                temperature=0.7
            )
            desc = ai.choices[0].message.content

        return desc, addr, photo_url, (lat, lng), pid
    except Exception as e:
        st.error(f"情報取得エラー: {e}")
        return '', '住所情報なし', None, (None, None), None

# --- YouTube取得 ---
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
if animation:
    st_lottie(animation, height=250, key="header_anim")

sel = st.session_state.selected
if sel:
    spot = sel['spot']
    st.header(f"📍 {spot} ({sel['time']})")
    with st.spinner('情報取得中...'):
        desc, addr, img, (lat, lng), pid = get_place_info(spot)
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

    if pid:
        map_url = f"https://www.google.com/maps/embed/v1/place?key={google_key}&q=place_id:{pid}"
        components.iframe(map_url, height=300, allowfullscreen=True)
    elif lat and lng:
        map_url = f"https://www.google.com/maps/embed/v1/place?key={google_key}&q={lat},{lng}"
        components.iframe(map_url, height=300, allowfullscreen=True)
    else:
        st.info('地図情報が見つかりませんでした')
else:
    st.info('サイドバーで旅程を生成し、行程を選択してください。')
