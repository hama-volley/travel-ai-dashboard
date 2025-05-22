# travel_planner_app.py

import streamlit as st
import requests
import urllib.parse
import streamlit.components.v1 as components
from openai import OpenAI

# --- ページ設定：最初に必ず ---
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

# --- APIクライアント設定 ---
client = OpenAI(api_key=st.secrets['OPENAI_API_KEY'])
google_key = st.secrets['GOOGLE_API_KEY']
pixabay_key = st.secrets.get('PIXABAY_API_KEY', '')
youtube_key = st.secrets.get('YOUTUBE_API_KEY', '')

# --- セッション初期化 ---
if 'itinerary' not in st.session_state:
    st.session_state.itinerary = ''
if 'spots' not in st.session_state:
    st.session_state.spots = []
if 'selected_spot' not in st.session_state:
    st.session_state.selected_spot = None

# --- 行程抽出 ---
def extract_spots(plan_text: str) -> list:
    resp = client.chat.completions.create(
        model='gpt-4',
        messages=[
            {'role':'system','content':'行程表から訪問すべき観光地名のみを順番にリストアップしてください。時間・ホテル・食事は除外。'},
            {'role':'user','content': plan_text}
        ],
        temperature=0
    )
    text = resp.choices[0].message.content
    return [line.strip('・-：: ') for line in text.split('\n') if line.strip()]

# --- フォールバック：ジオコーディング ---
def fallback_geocode(name: str):
    r = requests.get(
        'https://maps.googleapis.com/maps/api/geocode/json',
        params={'address': name, 'key': google_key}
    ).json()
    results = r.get('results', [])
    if not results:
        return '住所情報なし', (None, None)
    fm = results[0].get('formatted_address', '住所情報なし')
    loc = results[0].get('geometry', {}).get('location', {})
    return fm, (loc.get('lat'), loc.get('lng'))

# --- 場所情報取得 ---
def get_place_info(name: str):
    # Places APIで検索
    r = requests.get(
        'https://maps.googleapis.com/maps/api/place/findplacefromtext/json',
        params={
            'input': name + ' 観光地',
            'inputtype': 'textquery',
            'fields': 'place_id',
            'key': google_key
        }
    ).json()
    cand = r.get('candidates', [])
    if cand:
        pid = cand[0].get('place_id')
        d = requests.get(
            'https://maps.googleapis.com/maps/api/place/details/json',
            params={
                'place_id': pid,
                'fields': 'formatted_address,photo,editorial_summary,geometry',
                'key': google_key
            }
        ).json().get('result', {})
        # 説明
        desc = d.get('editorial_summary', {}).get('overview', '')
        if not desc:
            # AIでフォールバック生成
            ai = client.chat.completions.create(
                model='gpt-4',
                messages=[
                    {'role':'system','content':'この観光地について200字以内で簡潔に説明してください。'},
                    {'role':'user','content': name}
                ],
                temperature=0.7
            )
            desc = ai.choices[0].message.content
        # アクセス
        access = d.get('formatted_address', '')
        if not access:
            access, _ = fallback_geocode(name)
        # 画像
        photo_url = None
        photos = d.get('photos', [])
        if photos:
            ref = photos[0].get('photo_reference')
            photo_url = f'https://maps.googleapis.com/maps/api/place/photo?maxwidth=600&photoreference={ref}&key={google_key}'
        # 座標
        loc = d.get('geometry', {}).get('location', {})
        lat, lng = loc.get('lat'), loc.get('lng')
    else:
        # フォールバック：ジオコーディング
        desc = ''
        access, (lat, lng) = fallback_geocode(name)
        # 画像フォールバック：Pixabay
        photo_url = None
        if pixabay_key:
            p = requests.get(
                'https://pixabay.com/api/',
                params={'key': pixabay_key, 'q': name + ' 風景', 'image_type': 'photo', 'per_page': 3}
            ).json().get('hits', [])
            if p:
                photo_url = p[0].get('webformatURL')
        # 説明フォールバック：AI
        if not desc:
            ai = client.chat.completions.create(
                model='gpt-4',
                messages=[
                    {'role':'system','content':'この観光地について200字以内で簡潔に説明してください。'},
                    {'role':'user','content': name}
                ],
                temperature=0.7
            )
            desc = ai.choices[0].message.content
    return desc, access, photo_url, (lat, lng)

# --- YouTube動画検索 ---
def get_youtube_video(name: str):
    if not youtube_key:
        return None
    r = requests.get(
        'https://www.googleapis.com/youtube/v3/search',
        params={'part':'snippet','q': name + ' 観光','maxResults':1,'type':'video','key': youtube_key}
    ).json().get('items', [])
    if not r:
        return None
    vid = r[0]['id']['videoId']
    return f'https://www.youtube.com/watch?v={vid}'

# --- UI: サイドバー ---
st.sidebar.title('🗒️ 旅行プランAI')
user_input = st.sidebar.text_input('旅行プランを入力：', '大阪で1泊2日旅行したい')
if st.sidebar.button('✈️ 行程生成'):
    plan = client.chat.completions.create(
        model='gpt-4',
        messages=[
            {'role':'system','content':'あなたはプロの旅行プランナーです。1泊2日の時間付き行程表を作成してください。'},
            {'role':'user','content': user_input}
        ],
        temperature=0.7
    ).choices[0].message.content
    st.session_state.itinerary = plan
    st.session_state.spots = extract_spots(plan)
    st.session_state.selected_spot = None

if st.session_state.spots:
    st.sidebar.markdown('---')
    for i, spot in enumerate(st.session_state.spots):
        if st.sidebar.button(f'• {spot}', key=i):
            st.session_state.selected_spot = spot

# --- UI: メイン ---
st.title('🖋️ 手書き風 旅行プランナーAI')
if st.session_state.selected_spot:
    spot = st.session_state.selected_spot
    st.header(f'📍 {spot}')
    with st.spinner('情報取得中...'):
        desc, access, img, (lat, lng) = get_place_info(spot)
        yt = get_youtube_video(spot)
    left, right = st.columns([2,3])
    with left:
        st.subheader('📖 説明')
        st.write(desc)
        st.subheader('🚉 アクセス')
        st.write(access)
        if yt:
            st.markdown(f'[▶️ YouTubeで観光動画を見る]({yt})')
    with right:
        if img:
            st.image(img, caption=spot, use_column_width=True)
        else:
            st.warning('画像が見つかりませんでした')
    if lat and lng:
        url = f'https://www.google.com/maps/embed/v1/place?key={google_key}&q={lat},{lng}'
        components.iframe(url, height=300)
    else:
        st.info('地図情報が見つかりませんでした')
else:
    st.info('サイドバーで行程生成し、スポットを選択してください。')
