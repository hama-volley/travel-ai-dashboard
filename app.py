import streamlit as st
import requests
import urllib.parse
import streamlit.components.v1 as components
from openai import OpenAI

# --- APIキー初期化 ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
google_key = st.secrets["GOOGLE_API_KEY"]
youtube_key = st.secrets["YOUTUBE_API_KEY"]
rakuten_app_id = st.secrets["RAKUTEN_APP_ID"]

# --- セッション ---
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

# --- Google Maps：place_id, 緯度経度, 写真, 地図URL ---
def get_place_info(spot):
    base = f"https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    place_res = requests.get(base, params={
        "input": spot,
        "inputtype": "textquery",
        "fields": "place_id",
        "key": google_key
    }).json()
    place_id = place_res.get("candidates", [{}])[0].get("place_id")

    lat, lng = None, None
    if place_id:
        detail_url = f"https://maps.googleapis.com/maps/api/place/details/json"
        detail_res = requests.get(detail_url, params={
            "place_id": place_id,
            "fields": "geometry,photo",
            "key": google_key
        }).json()
        geometry = detail_res.get("result", {}).get("geometry", {}).get("location", {})
        lat = geometry.get("lat")
        lng = geometry.get("lng")

        photo_ref = None
        photos = detail_res.get("result", {}).get("photos", [])
        if photos:
            photo_ref = photos[0].get("photo_reference")
            photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo_ref}&key={google_key}"
        else:
            photo_url = None

        map_url = f"https://www.google.com/maps/embed/v1/place?key={google_key}&q=place_id:{place_id}"
        return place_id, lat, lng, photo_url, map_url

    return None, None, None, None, None

# --- YouTube検索リンクだけ表示 ---
def get_youtube_link(spot):
    return f"https://www.youtube.com/results?search_query={urllib.parse.quote(spot + ' 観光')}"

# --- 楽天トラベル：緯度・経度でホテル検索 ---
def get_hotels_by_location(lat, lng):
    url = "https://app.rakuten.co.jp/services/api/Travel/SimpleHotelSearch/20170426"
    params = {
        "applicationId": rakuten_app_id,
        "format": "json",
        "latitude": lat,
        "longitude": lng,
        "datumType": 1,
        "hits": 5,
        "searchRadius": 3  # 半径3km以内
    }
    r = requests.get(url, params=params).json()
    return r.get("hotels", [])

# --- メイン構成 ---
st.set_page_config(layout="wide")
st.title("🌍 AI旅行プランナー")

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

    # スポット名
    spot = next((s for s in st.session_state["spots"] if s in selected_step), st.session_state["spots"][0])
    st.markdown(f"### 📍 {spot}")

    # Googleからplace情報取得
    place_id, lat, lng, photo_url, map_url = get_place_info(spot)

    # 地図と写真
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🖼 写真")
        if photo_url:
            st.image(photo_url, caption=spot)
        else:
            st.warning("画像が見つかりません")

    with col2:
        st.markdown("#### 🗺 地図")
        if map_url:
            components.iframe(map_url, height=300)
        else:
            st.warning("地図情報なし")

    # YouTubeリンク
    st.markdown("#### 🎥 YouTube検索リンク")
    st.markdown(f"[🔗 {spot} 観光の動画を見る]({get_youtube_link(spot)})")

    # 楽天トラベルホテル表示
    st.markdown("#### 🏨 宿泊候補（楽天トラベル）")
    if lat and lng:
        hotels = get_hotels_by_location(lat, lng)
        if hotels:
            for h in hotels:
                info = h["hotel"][0]["hotelBasicInfo"]
                st.markdown(f"**[{info['hotelName']}]({info['hotelInformationUrl']})**")
                st.image(info["hotelImageUrl"], width=200)
                st.markdown(f"最安料金: {info.get('hotelMinCharge', '不明')} 円")
                st.markdown(f"アクセス: {info.get('access', '情報なし')}")
                st.markdown("---")
        else:
            st.info("周辺の宿泊情報が見つかりませんでした。")
    else:
        st.warning("位置情報が取得できなかったため、ホテル情報を表示できません。")

    # 質問
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
