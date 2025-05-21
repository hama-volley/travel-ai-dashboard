
import openai
import streamlit as st
import streamlit.components.v1 as components
import urllib.parse

openai.api_key = st.secrets["OPENAI_API_KEY"]

st.set_page_config(layout="wide")
st.title("✈️ AI旅行プランナー ダッシュボード")

destination = st.text_input("旅行プランを作成したい内容を入力してね", "大阪で1泊2日旅行したい")

if st.button("行程表を作成！"):
    with st.spinner("AIが旅行プランを考え中やで〜..."):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "あなたはプロの旅行プランナーです。ユーザーが入力した内容に基づいて、日程ごとの旅行プランを時間軸で提案してください。"},
                    {"role": "user", "content": destination}
                ],
                temperature=0.7
            )
            itinerary = response.choices[0].message['content']
            st.markdown("### 🗓️ 行程表（AI生成）")
            st.text(itinerary)

            spot = "Tsutenkaku Tower"

            col1, center, col2 = st.columns([2, 3, 2])

            with col1:
                st.markdown("#### 🎥 TikTok映像")
                video_url = "https://www.tiktok.com/@tsutenkaku_tower/video/7349129575198182663"
                video_id = video_url.split("/")[-1]
                embed_url = f"https://www.tiktok.com/embed/{video_id}"
                components.iframe(embed_url, height=300)

                st.markdown("#### 🖼️ 写真（Unsplash）")
                spot = spot.strip()
                image_url = f"https://source.unsplash.com/featured/?{urllib.parse.quote(spot)}"
                st.image(image_url, caption=f"{spot}のイメージ")

            with center:
                st.markdown("#### 📅 行程表再掲")
                st.text(itinerary)

            with col2:
                st.markdown("#### 🗺️ Googleマップ")
                map_query = urllib.parse.quote(spot)
                map_url = f'https://www.google.com/maps/embed/v1/place?key={st.secrets["GOOGLE_MAPS_API_KEY"]}&q={map_query}'
                components.iframe(map_url, height=300)

                st.markdown("#### 🏨 宿泊候補（楽天トラベルリンク）")
                st.markdown(f"[{spot}周辺の宿を探す（楽天）](https://search.travel.rakuten.co.jp/ds/search/kwd={urllib.parse.quote(spot)})")

        except Exception as e:
            st.error(f"旅程の取得エラー: {e}")
