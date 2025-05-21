import openai
import streamlit as st
import requests
import urllib.parse
import streamlit.components.v1 as components

openai.api_key = st.secrets["OPENAI_API_KEY"]
google_places_key = st.secrets["GOOGLE_PLACES_API_KEY"]

st.set_page_config(layout="wide")
st.title("✈️ AI旅行プランナー ダッシュボード")
# Place ID を取得
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

# 写真URLを取得
def get_place_photo_url(place_id, api_key):
    detail_url = (
        f"https://maps.googleapis.com/maps/api/place/details/json"
        f"?place_id={place_id}&fields=photo&key={api_key}"
    )
    res = requests.get(detail_url)
    data = res.json()
    if "photos" in data.get("result", {}):
        photo_ref = data["result"]["photos"][0]["photo_reference"]
        return (
            f"https://maps.googleapis.com/maps/api/place/photo"
            f"?maxwidth=800&photoreference={photo_ref}&key={api_key}"
        )
    return None

# GoogleマップEmbed URL取得
def get_map_embed_url_from_place_id(place_id, api_key):
    return f"https://www.google.com/maps/embed/v1/place?key={api_key}&q=place_id:{place_id}"
# 例：AIで行程表を取得済みの部分からスポット処理

spots = ["大阪城", "通天閣", "あべのハルカス"]  # 仮に手動。抽出ロジックはあとで追加

for spot in spots:
    st.markdown(f"---\n\n### 📍 {spot}")
    col1, col2 = st.columns([2, 2])

    # Google PlacesでPlace ID取得
    place_id = get_place_id(spot, google_places_key)

    with col1:
        st.markdown("#### 🖼️ 写真（Google）")
        if place_id:
            photo_url = get_place_photo_url(place_id, google_places_key)
            if photo_url:
                st.image(photo_url, caption=f"{spot} の写真（Google提供）")
            else:
                st.warning("写真が見つかりませんでした")
        else:
            st.warning("Place ID が見つかりませんでした")

    with col2:
        st.markdown("#### 🗺️ Googleマップ")
        if place_id:
            map_url = get_map_embed_url_from_place_id(place_id, google_places_key)
            components.iframe(map_url, height=300)
        else:
            st.warning("マップが表示できませんでした")
