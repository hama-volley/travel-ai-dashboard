# travel_planner_app.py

import streamlit as st
# --- ページ設定は最初に必ず ---
st.set_page_config(page_title="旅行プランナーAI", layout="wide")

# --- 手書き風カスタムCSS ---
handwritten_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700&display=swap');
body, html, .stApp {
  font-family: 'Zen Maru Gothic', cursive;
  background-color: #fdf6e3;
  color: #333;
}
.stSidebar, .css-1d391kg, .css-1cpxqw2 {
  background-color: #fdf6e3 !important;
  border-right: 2px dashed #ccc;
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
  border-radius: 4px;
}
</style>
"""
st.markdown(handwritten_css, unsafe_allow_html=True)

# --- ライブラリ読み込み ---
import openai
import requests
import urllib.parse
import streamlit.components.v1 as components

# --- APIキー設定 ---
openai.api_key = st.secrets['OPENAI_API_KEY']
google_key      = st.secrets['GOOGLE_API_KEY']

# --- セッション初期化 ---
if 'itinerary' not in st.session_state:
    st.session_state.itinerary = ''
if 'spots' not in st.session_state:
    st.session_state.spots = []
if 'selected_spot' not in st.session_state:
    st.session_state.selected_spot = None

# --- 観光地抽出 ---
def extract_spots(text: str) -> list:
    resp = openai.ChatCompletion.create(
        model='gpt-4',
        messages=[
            {'role':'system','content':'行程表から訪問すべき観光地名のみを順番に1行ずつ抽出してください。時間・ホテル・食事は除外。'},
            {'role':'user','content': text}
        ],
        temperature=0
    )
    lines = resp.choices[0].message['content'].split('\n')
    return [l.strip('・-：: ') for l in lines if l.strip()]

# --- 地図・画像・説明取得 ---
def get_place_info(spot: str):
    # プレースID取得
    find = requests.get(
        'https://maps.googleapis.com/maps/api/place/findplacefromtext/json',
        params={
            'input': spot + ' 大阪 観光地',
            'inputtype': 'textquery',
            'fields': 'place_id',
            'key': google_key
        }
    ).json()
    pid = find.get('candidates', [{}])[0].get('place_id')
    if not pid:
        return '説明なし','アクセスなし', None, None
    # 詳細取得
    det = requests.get(
        'https://maps.googleapis.com/maps/api/place/details/json',
        params={ 'place_id': pid, 'fields':'formatted_address,photo,editorial_summary,geometry', 'key': google_key }
    ).json().get('result', {})
    # 説明
    desc   = det.get('editorial_summary', {}).get('overview','説明が見つかりませんでした')
    # 住所
    access = det.get('formatted_address','住所不明')
    # 画像URL
    photos = det.get('photos', [])
    img    = None
    if photos:
        ref = photos[0].get('photo_reference')
        img = f'https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={ref}&key={google_key}'
    # 座標
    loc    = det.get('geometry', {}).get('location', {})
    latlng = (loc.get('lat'), loc.get('lng')) if loc else (None, None)
    return desc, access, img, latlng

# --- UI: サイドバー ---
st.sidebar.title('🗒️ 旅行プランAI')
user_input = st.sidebar.text_input('旅行プランを入力：', '大阪で1泊2日旅行したい')
if st.sidebar.button('✈️ 行程生成'):
    # AIで行程生成
    plan = openai.ChatCompletion.create(
        model='gpt-4',
        messages=[
            {'role':'system','content':'あなたはプロの旅行プランナーです。1泊2日、時間付き行程表を作成してください。'},
            {'role':'user','content': user_input}
        ],
        temperature=0.7
    ).choices[0].message['content']
    st.session_state.itinerary = plan
    st.session_state.spots = extract_spots(plan)
    st.session_state.selected_spot = None

if st.session_state.spots:
    st.sidebar.markdown('---')
    st.sidebar.subheader('🔖 スポット一覧')
    for i, spot in enumerate(st.session_state.spots):
        if st.sidebar.button(f'• {spot}', key=i):
            st.session_state.selected_spot = spot

# --- UI: メイン ---
st.title('🖋️ 手書き風 旅行プランナーAI')
if st.session_state.selected_spot:
    spot = st.session_state.selected_spot
    st.header(f'📍 {spot}')
    # 情報取得
    with st.spinner('情報取得中...'):
        desc, access, img, (lat, lng) = get_place_info(spot)
    cols = st.columns([2,3])
    with cols[0]:
        st.subheader('📖 説明')
        st.write(desc)
        st.subheader('🚉 アクセス')
        st.write(access)
        yt = urllib.parse.quote(spot + ' 観光')
        st.markdown(f'[▶️ YouTube動画を検索](https://www.youtube.com/results?search_query={yt})')
    with cols[1]:
        if img:
            st.image(img, caption=spot, use_column_width=True)
        else:
            st.warning('画像なし')
    if lat and lng:
        url = f'https://www.google.com/maps/embed/v1/place?key={google_key}&q={lat},{lng}'
        components.iframe(url, height=300)
    else:
        st.info('地図情報なし')
else:
    st.info('左のサイドバーから行程生成とスポット選択をしてください。')
