import openai
import streamlit as st
import requests
import urllib.parse
import streamlit.components.v1 as components

# APIキー
openai.api_key = st.secrets["OPENAI_API_KEY"]
google_places_key = st.secrets["GOOGLE_PLACES_API_KEY"]
youtube_key = st.secrets["YOUTUBE_API_KEY"]

st.set_page_config(layout="wide")
st.title("✈️ AI旅行プランナー ダッシュボード")

# --- Places API関連 ---
def get_place_id(spot_name, api_key):
    url = (
        "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        f"?input={urllib.parse.quote(spot_name)}&inputtype=textquery&fields=place_id&key={api_key}"
    )
    res = requests.get(url)
    data = res.json()
    if data.get("candidates"):
        return data["candidates"][0]["place_id"]
    return None

def get_place_photo_url(place_id, api_key):
    detail_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=photo&key={api_key}"
    res = requests.get(detail_url)
    data = res.json()
    if "photos" in data.get("result", {}):
        photo_ref = data["result"]["photos"][0]["photo_reference"]
        return f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo_ref}&key={api_key}"
    return None

def get_map_embed_url_from_place_id(place_id, api_key):
    return f"https://www.google.com/maps/embed/v1/place?key={api_key}&q=place_id:{place_id}"

# --- YouTube動画埋め込み ---
def fetch_youtube_embed(spot, api_key):
    search_keywords = [spot, f"{spot} 観光", f"{spot} vlog", f"{spot} tour"]
    for keyword in search_keywords:
        search_url = (
            f"https://www.googleapis.com/youtube/v3/search?key={api_key}"
            f"&part=snippet&q={urllib.parse.quote(keyword)}&type=video&maxResults=1"
        )
        res = requests.get(search_url)
        if res.status_code == 200:
            items = res.json().get("items", [])
            if items:
                video_id = items[0]["id"]["videoId"]
                return f"https://www.youtube.com/embed/{video_id}"
    return None

# --- スポット名抽出 ---
def extract_spot_name(description):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "以下の文章から観光地や施設名を1つだけ抽出し、検索用に短く返答してください。"},
                {"role": "user", "content": description}
            ],
            temperature=0.2,
            max_tokens=20
        )
        return response.choices[0].message['content'].strip()
    except:
        return None

# --- メインUI ---
destination = st.text_input("行きたい場所・旅行内容を入力", "大阪で1泊2日旅行したい")

if st.button("行程表を作成！"):
    with st.spinner("AIが旅行プランを作成中やで〜..."):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "あなたはプロの旅行プランナーです。入力内容に基づいて、1泊2日の行程表を日付・時間順で作成してください。"},
                    {"role": "user", "content": destination}
                ]
            )
            itinerary = response.choices[0].message["content"]
            st.markdown("### 📅 AI生成の行程表")
            st.markdown(itinerary)

            st.markdown("### 📍 各スポットの詳細")
            lines = [line for line in itinerary.split("\n") if line.strip()]
            extracted_spots = []

            for line in lines:
                spot = extract_spot_name(line)
                if not spot or spot in extracted_spots:
                    continue
                extracted_spots.append(spot)

                place_id = get_place_id(spot, google_places_key)
                photo_url = get_place_photo_url(place_id, google_places_key) if place_id else None
                map_url = get_map_embed_url_from_place_id(place_id, google_places_key) if place_id else None
                yt_url = fetch_youtube_embed(spot, youtube_key)

                st.markdown(f"---\n\n#### 📌 {spot}")
                col1, col2, col3 = st.columns([1.2, 1.2, 2])

                with col1:
                    st.markdown("🎥 YouTube")
                    if yt_url:
                        components.iframe(yt_url, height=200)
                    else:
                        st.warning("動画が見つかりませんでした")

                with col2:
                    st.markdown("🖼 写真（Google）")
                    if photo_url:
                        st.image(photo_url, caption=spot)
                    else:
                        st.warning("写真が見つかりませんでした")

                with col3:
                    st.markdown("🗺 地図（Google）")
                    if map_url:
                        components.iframe(map_url, height=200)
                    else:
                        st.warning("地図が見つかりませんでした")

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")

