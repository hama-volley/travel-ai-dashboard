import openai
import streamlit as st
import requests
import urllib.parse
import streamlit.components.v1 as components

# 🔑 Secrets取得
openai.api_key = st.secrets["OPENAI_API_KEY"]
pixabay_key = st.secrets["PIXABAY_API_KEY"]
youtube_key = st.secrets["YOUTUBE_API_KEY"]
google_maps_key = st.secrets["GOOGLE_MAPS_API_KEY"]

st.set_page_config(layout="wide")
st.title("✈️ AI旅行プランナー ダッシュボード")

# 🔍 クエリ補完
def refine_keywords(base, mode):
    extras = ["観光", "名所", "建物"] if mode == "image" else ["観光", "旅行", "Vlog"]
    return [f"{base} {x}" for x in extras]

# 🖼️ Pixabay画像取得
def fetch_pixabay(spot):
    for q in refine_keywords(spot, "image"):
        url = f"https://pixabay.com/api/?key={pixabay_key}&q={urllib.parse.quote(q)}&image_type=photo&per_page=3"
        r = requests.get(url)
        if r.status_code == 200 and r.json().get("hits"):
            return r.json()["hits"][0]["webformatURL"]
    return None

# ▶️ YouTube動画取得
def fetch_youtube_embed(spot):
    for q in refine_keywords(spot, "video"):
        search_url = f"https://www.googleapis.com/youtube/v3/search?key={youtube_key}&part=snippet&q={urllib.parse.quote(q)}&type=video&maxResults=1"
        r = requests.get(search_url)
        items = r.json().get("items")
        if items:
            video_id = items[0]["id"]["videoId"]
            return f"https://www.youtube.com/embed/{video_id}"
    return None

# ✨ スポット名を抽出（長文からシンプルな地名だけを抽出）
def extract_spot_name(description):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "以下の文章から観光地や施設名を1つだけ抽出してください。検索キーワードとして最適な短く明確な名称を返してください。"},
                {"role": "user", "content": description}
            ],
            temperature=0.2,
            max_tokens=20
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        st.warning(f"スポット名の抽出に失敗しました: {e}")
        return None


# 📍 GoogleマップURL
def get_map_embed_url(spot):
    query = urllib.parse.quote(spot)
    return f"https://www.google.com/maps/embed/v1/place?key={google_maps_key}&q={query}"

# ✈️ 入力エリア
destination = st.text_input("旅行プランを作りたい内容を入力してね", "大阪で1泊2日旅行したい")

if st.button("行程表を作成！"):
    with st.spinner("AIが旅行プランを考え中やで〜..."):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "あなたはプロの旅行プランナーです。日程ごとの旅行プランを時間順で提案してください。"},
                    {"role": "user", "content": destination}
                ]
            )
            itinerary = response.choices[0].message["content"]
            st.markdown("### 📅 行程表（AI生成）")
            st.markdown(itinerary)

            raw_lines = [line.strip("・-：:") for line in itinerary.split("\n") if line.strip()]
            spots = []
            for line in raw_lines:
                spot = extract_spot_name(line)
                if spot and spot not in spots:
                    spots.append(spot)

            for spot in spots:
                st.markdown(f"---\n\n### 📍 {spot}")
                col1, col2, col3 = st.columns([1.5, 2, 2])

                with col1:
                    st.markdown("#### 🎥 YouTube動画")
                    yt_url = fetch_youtube_embed(spot)
                    if yt_url:
                        components.iframe(yt_url, height=250)
                    else:
                        st.warning(f"{spot} の動画が見つかりませんでした")

                with col2:
                    st.markdown("#### 🖼️ 写真（Pixabay）")
                    img_url = fetch_pixabay(spot)
                    if img_url:
                        st.image(img_url, caption=f"{spot}のイメージ（Pixabay）")
                    else:
                        st.warning(f"{spot} の画像が見つかりませんでした（Pixabay）")

                with col3:
                    st.markdown("#### 🗺️ Googleマップ")
                    map_url = get_map_embed_url(spot)
                    components.iframe(map_url, height=250)

        except Exception as e:
            st.error(f"旅程の取得エラー: {e}")
