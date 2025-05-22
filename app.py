# travel_planner_app.py

import streamlit as st
import requests
import urllib.parse
import json
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
youtube_key = st.secrets.get('YOUTUBE_API_KEY', '')

# --- セッションデータ ---
if 'itinerary' not in st.session_state:
    st.session_state.itinerary = []  # list of dict
if 'selected' not in st.session_state:
    st.session_state.selected = None

# --- AI行程生成：JSONフォーマット ---
def generate_itinerary(query: str):
    prompt = (
        "あなたはプロの旅行プランナーです。以下の要件に基づき、1泊2日の時間付き行程表を"
        "JSON形式で返してください。配列要素は{day:int, time:str, spot:str}としてください。"
    )
    resp = client.chat.completions.create(
        model='gpt-4',
        messages=[
            {'role':'system','content':prompt},
            {'role':'user','content':query}
        ],
        temperature=0.7
    )
    return json.loads(resp.choices[0].message.content)

# --- 状況に応じて情報取得 ---
def get_place_info(name: str):
    # 1. ジオコーディングで住所と座標
    geo = requests.get(
        'https://maps.googleapis.com/maps/api/geocode/json',
        params={'address': name, 'key': google_key}
    ).json().get('results', [])
    if geo:
        addr = geo[0].get('formatted_address', '')
        loc = geo[0]['geometry']['location']
        lat, lng = loc['lat'], loc['lng']
    else:
        addr, lat, lng = '住所情報なし', None, None
    # 2. Places API で詳細取得
    find = requests.get(
        'https://maps.googleapis.com/maps/api/place/findplacefromtext/json',
        params={
            'input': name,
            'inputtype': 'textquery',
            'fields': 'place_id',
            'key': google_key
        }
    ).json().get('candidates', [])
    photo_url, desc = None, ''
    if find:
        pid = find[0]['place_id']
        details = requests.get(
            'https://maps.googleapis.com/maps/api/place/details/json',
            params={
                'place_id': pid,
                'fields': 'photo,editorial_summary',
                'key': google_key
            }
        ).json().get('result', {})
        # 説明
        desc = details.get('editorial_summary', {}).get('overview','')
        # 写真
        photos = details.get('photos', [])
        if photos:
            ref = photos[0]['photo_reference']
            photo_url = (
                f'https://maps.googleapis.com/maps/api/place/photo'
                f'?maxwidth=800&photoreference={ref}&key={google_key}'
            )
    # フォールバック：説明がない場合はAI生成
    if not desc:
        ai = client.chat.completions.create(
            model='gpt-4',
            messages=[
                {'role':'system','content':'以下の観光地について100字以内で簡潔に説明してください。'},
                {'role':'user','content':name}
            ],
            temperature=0.7
        )
        desc = ai.choices[0].message.content
    return desc, addr, photo_url, (lat, lng)

# --- YouTube検索 ---
def get_youtube(name: str):
    if not youtube_key:
        return None
    res = requests.get(
        'https://www.googleapis.com/youtube/v3/search',
        params={
            'part': 'snippet',
            'q': name + ' 観光',
            'type': 'video',
            'maxResults': 1,
            'key': youtube_key
        }
    ).json().get('items', [])
    if res:
        return f"https://www.youtube.com/watch?v={res[0]['id']['videoId']}"
    return None

# --- UI: サイドバー入力 & 生成 ---
st.sidebar.header('🗒️ 旅行プランAI')
query = st.sidebar.text_input('旅程の要望：', '大阪で1泊2日旅行したい')
if st.sidebar.button('生成'):
    st.session_state.itinerary = generate_itinerary(query)
    st.session_state.selected = None

# --- UI: サイドバー行程一覧 ---
if st.session_state.itinerary:
    st.sidebar.markdown('---')
    for idx, item in enumerate(st.session_state.itinerary):
        label = f"【{item['day']}日目】{item['time']} - {item['spot']}"
        if st.sidebar.button(label, key=idx):
            st.session_state.selected = item

# --- UI: メイン表示 ---
st.title('🖋️ 手書き風 旅行プランナーAI')
if st.session_state.selected:
    spot = st.session_state.selected['spot']
    st.header(f"📍 {spot}  ({st.session_state.selected['time']})")
    with st.spinner('情報取得中...'):
        desc, addr, img, (lat, lng) = get_place_info(spot)
        yt = get_youtube(spot)
    left, right = st.columns([2,3])
    with left:
        st.subheader('📖 説明')
        st.write(desc)
        st.subheader('🚉 アクセス')
        st.write(addr)
        if yt:
            st.markdown(f"[▶️ YouTube動画を見る]({yt})")
    with right:
        if img:
            st.image(img, caption=spot, use_container_width=True)
        else:
            st.warning('画像が見つかりませんでした')
    if lat and lng:
        map_url = (
            f'https://www.google.com/maps/embed/v1/place?key={google_key}&q={lat},{lng}'
        )
        components.iframe(map_url, height=300)
    else:
        st.info('地図情報が見つかりませんでした')
else:
    st.info('サイドバーで旅程を生成し、行程を選択してください。')
