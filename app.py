import streamlit as st
import requests
import urllib.parse
import streamlit.components.v1 as components
from openai import OpenAI

# --- 初期化 ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
google_key = st.secrets["GOOGLE_API_KEY"]

# --- セッション管理 ---
if "itinerary" not in st.session_state:
    st.session_state["itinerary"] = ""
if "spots" not in st.session_state:
    st.session_state["spots"] = []
if "selected_step" not in st.session_state:
    st.session_state["selected_step"] = ""

# --- GPT：スポット抽出 ---
def extract_spots(text):
    res = client.chat.completions.create(
        model="gpt-4",
        temperature=0.0,
        messages=[
            {"role": "system", "content": "以下の旅行行程から、観光名所、観光施設、ホテル、レストラン、カフェなどのスポット名のみを1行ずつ抽出してください。時間帯・食事・移動・日付・『2日目』などの表記は除外してください。リスト形式で出力してください。"},
            {"role": "user", "content": text}
        ]
    )
    return [line.strip("・-:：") for line in res.choices[0].message.content.split("\n") if line.strip()]

# --- Google Maps連携 ---
def get_place_id(spot):
    url = f"https://maps.googleapis.com/maps/api/place/findplacefromtext/json?input={urllib.parse.quote(spot)}&inputtype=textquery&fields=place_id&key={google_key}"
    r = requests.get(url).json()
    return r.get("candidates", [{}])[0].get("place_id")

def get_photo_url(place_id):
    url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=photo&key={google_key}"
    r = requests.get(url).json()
    photos = r.get("result", {}).get("photos", [])
    if photos:
        ref = photos[0]["photo_reference"]
        return f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={ref}&key={google_key}"
    return None

def get_map_embed_url(place_id):
    return f"https://www.google.com/maps/embed/v1/place?key={google_key}&q=place_id:{place_id}"

# --- メイン構成 ---
st.set_page_config(layout="wide")
st.title("🌍 行程 × 地図 × 写真 同期ダッシュボード（安定版）")

user_input = st.text_input("旅行プランを入力：", "大阪で1泊2日旅行したい")

if st.button("AIで行程作成！"):
    res = client.chat.completions.create(
        model="gpt-4",
        temperature=0.7,
        messages=[
            {"role": "system", "content": "あなたは旅行プランナーです。指定された旅程に対して、時間付きの行程表を1泊2日で作成してください。"},
            {"role": "user", "content": user_input}
        ]
    )
    itinerary = res.choices[0].message.content
    st.session_state["itinerary"] = itinerary
    st.session_state["steps"] = [line for line in itinerary.split("\n") if line.strip()]
    st.session_state["spots"] = extract_spots(itinerary)
    st.session_state["selected_step"] = st.session_state["steps"][0] if st.session_state["steps"] else ""

# --- 表示 ---
if "steps" in st.session_state and st.session_state["steps"]:
    st.subheader("📅 行程を選択")
    selected_step = st.selectbox("行程：", st.session_state["steps"])
    st.session_state["selected_step"] = selected_step

    # ステップから該当スポットを自動抽出
    spot = None
    for s in st.session_state["spots"]:
        if s in selected_step:
            spot = s
            break
    if not spot:
        spot = st.session_state["spots"][0] if st.session_state["spots"] else "スポット未定"

    st.markdown(f"### 📍 {spot}")

    col1, col2 = st.columns(2)
    place_id = get_place_id(spot)

    with col1:
        st.markdown("#### 🖼 写真")
        img = get_photo_url(place_id) if place_id else None
        if img:
            st.image(img, caption=spot)
        else:
            st.warning("画像が見つかりません")

    with col2:
        st.markdown("#### 🗺 地図")
        if place_id:
            map_url = get_map_embed_url(place_id)
            components.iframe(map_url, height=300)
        else:
            st.warning("地図情報なし")

    # --- 質問欄と回答表示 ---
    st.markdown("#### 💬 質問してみよう")
    q = st.text_input(f"{spot} についての質問は？", key="ask")
    answer_placeholder = st.empty()

    if q:
        with st.spinner("AIが考え中やで..."):
            ans = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"{spot} に関する観光案内を丁寧にお願いします。"},
                    {"role": "user", "content": q}
                ]
            )
            response_text = ans.choices[0].message.content
            answer_placeholder.text_area("🧠 回答はこちら", response_text, height=150)
