import openai
import streamlit as st
import streamlit.components.v1 as components
import urllib.parse

st.set_page_config(layout="wide")
st.title("✈️ AI旅行プランナー ダッシュボード")

openai.api_key = st.secrets["OPENAI_API_KEY"]

# 入力欄
destination = st.text_input("旅行プランを作成したい内容を入力してね", "大阪で1泊2日旅行したい")

if st.button("行程表を作成！"):
    with st.spinner("AIが旅行プランを考え中やで〜..."):
        try:
            # 1. 行程表を生成
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

            # 2. スポットを抽出
            with st.spinner("行程表からスポットを抽出中..."):
                try:
                    extract_response = openai.ChatCompletion.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "あなたは日本国内の旅行ガイド編集者です。以下の旅行スケジュールの中に含まれている主なスポット名（観光地や施設、商業地など）を5つ以内で抽出してください。地名のみをカンマ区切りで返してください。"},
                            {"role": "user", "content": itinerary}
                        ],
                        temperature=0.3
                    )
                    spot_list_text = extract_response.choices[0].message['content']
                    extracted_spots = [s.strip() for s in spot_list_text.split(",")]
                    st.success(f"抽出されたスポット：{', '.join(extracted_spots)}")
                except Exception as e:
                    st.error(f"スポット抽出エラー: {e}")
                    extracted_spots = []

            # 3. スポットごとに連動表示
            for spot in extracted_spots:
                st.markdown(f"## 📍 {spot}")

                col1, col2, col3 = st.columns([1.5, 2, 2])

                with col1:
                    st.markdown("#### 🎥 TikTok映像")
                    search_link = f"https://www.tiktok.com/search?q={urllib.parse.quote(spot)}&t=0"
                    st.markdown(f"[{spot} のTikTokを検索]({search_link})")

                with col2:
                    st.markdown("#### 🖼️ 写真")
                    image_url = f"https://source.unsplash.com/featured/?{urllib.parse.quote(spot)}"
                    st.image(image_url, caption=f"{spot}のイメージ")

                with col3:
                    st.markdown("#### 🗺️ Googleマップ")
                    map_url = f'https://www.google.com/maps/embed/v1/place?key={st.secrets["GOOGLE_MAPS_API_KEY"]}&q={urllib.parse.quote(spot)}'
                    components.iframe(map_url, height=300)

        except Exception as e:
            st.error(f"旅程の取得エラー: {e}")

