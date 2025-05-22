import streamlit as st
import openai
import requests
import urllib.parse
import streamlit.components.v1 as components

# --- APIキー ---
openai.api_key = st.secrets["OPENAI_API_KEY"]
google_key = st.secrets["GOOGLE_API_KEY"]

# --- セッション状態管理 ---
if "itinerary" not in st.session_state:
    st.session_state["itinerary"] = ""
if "spots" not in st.session_state:
    st.session_state["spots"] = []
if "selected_index" not in st.session_state:
    st.session_state["selected_index"] = 0
if "steps" not in st.session_state:
    st.session_state["steps"] = []

# --- GPT：観光地抽出 ---
def extract_spots(text):
    res = openai.ChatCompletion.create(
        model="gpt-4",
        temperature=0.0,
        messages=[
            {"role": "system", "content": "以下の旅行行程から、観光名所、観光施設、ホテル、レストラン、カフェなどのスポット名のみを1行ずつ抽出してください。時間帯・食事・移動・日付・『2日目』などの表記は除外してください。リスト形式で出力してください。"},
            {"role": "user", "content": text}
        ]
    )
    return [line.strip("・-:：") for line in res.choices[0].message["content"].split("\n") if line.strip()]

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

# --- Swiper UI生成（JS埋込＋index検出） ---
def render_swiper_and_listen(slides):
    cards = "".join([f"<div class='swiper-slide'>{s}</div>" for s in slides])
    html_code = f"""
    <link rel="stylesheet" href="https://unpkg.com/swiper/swiper-bundle.min.css" />
    <style>
      .swiper-slide {{
        background: #f9f9f9;
        border-radius: 12px;
        padding: 20px;
        font-size: 17px;
        height: 170px;
        width: 75%;
        margin: auto;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
      }}
      .swiper-slide:hover {{
        transform: scale(1.03);
      }}
    </style>
    <div class="swiper mySwiper">
      <div class="swiper-wrapper">{cards}</div>
      <div class="swiper-pagination"></div>
    </div>
    <script src="https://unpkg.com/swiper/swiper-bundle.min.js"></script>
    <script>
      const swiper = new Swiper(".mySwiper", {{
        slidesPerView: "auto",
        centeredSlides: true,
        spaceBetween: 30,
        speed: 400,
        pagination: {{
          el: ".swiper-pagination",
          clickable: true,
        }},
        on: {{
          slideChange: function () {{
            const index = swiper.realIndex;
            window.parent.postMessage({{type: 'swiper-index', index}}, "*");
          }},
        }},
      }});
    </script>
    """
    components.html(html_code, height=310)

# --- ページ構成 ---
st.set_page_config(layout="wide")
st.title("🌍 行程 × 地図 × 写真 同期ダッシュボード")

user_input = st.text_input("旅行プランを入力：", "大阪で1泊2日旅行したい")

if st.button("AIで行程作成！"):
    res = openai.ChatCompletion.create(
        model="gpt-4",
        temperature=0.7,
        messages=[
            {"role": "system", "content": "あなたは旅行プランナーです。指定された旅程に対して、時間付きの行程表を1泊2日で作成してください。"},
            {"role": "user", "content": user_input}
        ]
    )
    itinerary = res.choices[0].message["content"]
    st.session_state["itinerary"] = itinerary
    st.session_state["steps"] = [line for line in itinerary.split("\n") if line.strip()]
    st.session_state["spots"] = extract_spots(itinerary)
    st.session_state["selected_index"] = 0

# --- 表示部：行程スライド・写真・地図 ---
if st.session_state["steps"]:
    st.subheader("📅 行程表（スライド選択）")
    render_swiper_and_listen(st.session_state["steps"])

    # JSイベント → Pythonでインデックス更新
    js_code = """
    <script>
    window.addEventListener("message", (event) => {
      if (event.data.type === "swiper-index") {
        const index = event.data.index;
        const form = new FormData();
        form.append("index", index);
        fetch("/_stcore/update_index", {
          method: "POST",
          body: form
        }).then(() => window.location.reload());
      }
    });
    </script>
    """
    components.html(js_code, height=0)

    # 選択中スポット
    idx = st.session_state["selected_index"]
    if idx >= len(st.session_state["spots"]):
        idx = 0
    spot = st.session_state["spots"][idx]
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
            ans = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"{spot} に関する観光案内を丁寧にお願いします。"},
                    {"role": "user", "content": q}
                ]
            )
            response_text = ans.choices[0].message["content"]
            answer_placeholder.text_area("🧠 回答はこちら", response_text, height=150)

# --- index更新エンドポイント定義 ---
from streamlit.web.server.websocket_headers import _get_websocket_headers
from streamlit.runtime.scriptrunner import get_script_run_ctx
from streamlit.runtime.runtime import Runtime
from streamlit.runtime.state import session_state

@st.cache_resource
def _register_update_index_handler():
    from fastapi import Request
    from starlette.responses import Response

    async def update_index(request: Request):
        form = await request.form()
        new_index = int(form["index"])
        session_id = _get_websocket_headers().get("X-Streamlit-Session-ID")
        ctx = get_script_run_ctx()
        if ctx and session_id:
            session = Runtime.instance()._session_mgr.get_session_info(session_id).session
            session.session_state["selected_index"] = new_index
        return Response(content="OK", status_code=200)

    from streamlit.web.server import Server
    server = Server.get_current()
    if server:
        server._app.add_api_route("/_stcore/update_index", update_index, methods=["POST"])

_register_update_index_handler()
