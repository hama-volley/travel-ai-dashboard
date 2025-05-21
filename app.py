import streamlit as st
import requests
import urllib.parse
import streamlit.components.v1 as components

# 🔑 APIキー（あなたの環境ではst.secretsで管理してね）
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

# 📍 スポット一覧（仮データ）
spots = [
    {"name": "大阪城", "place_id": "ChIJ0WGkg4Z3ZTURwOZ1LI1D2Pk"},
    {"name": "通天閣", "place_id": "ChIJUe_bA3hQZTURHhTVUDh1n1k"},
    {"name": "あべのハルカス", "place_id": "ChIJfwfpKBBRZTURMiUdjQ2LMRk"}
]

# 🔗 Google Maps用URL生成
def get_embed_url(place_id):
    return f"https://www.google.com/maps/embed/v1/place?key={GOOGLE_API_KEY}&q=place_id:{place_id}"

def get_overview_url(spots):
    query = urllib.parse.quote(" ".join([s["name"] for s in spots]))
    return f"https://www.google.com/maps/embed/v1/search?key={GOOGLE_API_KEY}&q={query}"

# 🚀 UI構成
st.set_page_config(layout="wide")
st.title("🗺️ AI旅行プランナー：地図切り替え機能付き")

# 🧾 行程表（中央）
st.markdown("### 📅 行程表")
st.info("9:00 大阪城 → 10:30 通天閣 → 12:00 あべのハルカス")

# 🔁 切替（全体マップ or 詳細スポット選択）
map_mode = st.radio("🧭 地図モード", ["全体マップ", "詳細マップ"], horizontal=True)

# 🧩 レイアウト
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### 🖼️ 写真")
    st.image("https://upload.wikimedia.org/wikipedia/commons/0/0d/Osaka_Castle_02bs3200.jpg", caption="大阪城")

    st.markdown("#### 🏨 宿泊候補")
    st.info("※楽天トラベルAPIで宿を表示予定")

with col_right:
    st.markdown("#### 🗺️ 地図")

    if map_mode == "全体マップ":
        map_url = get_overview_url(spots)
    else:
        selected = st.selectbox("地図で見るスポットを選んでね", [s["name"] for s in spots])
        place_id = next((s["place_id"] for s in spots if s["name"] == selected), None)
        map_url = get_embed_url(place_id)

    components.iframe(map_url, height=360)

    st.markdown("#### 💬 AI質問欄")
    q = st.text_input("気になることを聞いてみよう：")
    if q:
        st.success("※ChatGPTで回答予定（未実装）")
