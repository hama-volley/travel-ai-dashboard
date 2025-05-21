import openai
import streamlit as st
import requests
import urllib.parse
import streamlit.components.v1 as components

# 🔐 Secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]
google_api_key = st.secrets["GOOGLE_API_KEY"]

st.set_page_config(layout="wide")
st.title("🗺️ AI旅行プランナー：地図切り替え機能付き")

# 🎯 入力
destination = st.text_input("旅行したい内容を入力してね", "大阪で1泊2日旅行したい")

# 📍 モード切り替え（地図表示）
st.markdown("### 🧭 地図モード")
map_mode = st.radio("地図を切り替える", ["🟥 全体マップ", "🔘 詳細マップ"])

# 📜 行程表生成
if st.button("行程表を作成！"):
    with st.spinner("AIが行程表を作成中やで..."):
        try:
            gpt_res = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "あなたは旅行プランナーです。1泊2日の旅行プランを、時間順に作成してください。"},
                    {"role": "user", "content": destination}
                ]
            )
            itinerary = gpt_res.choices[0].message["content"]
            st.markdown("### 🗓️ 行程表")
            st.info(itinerary)

            # 行単位でスポット候補抽出
            lines = [line for line in itinerary.split("\n") if line.strip()]
            extracted_spots = []
            for line in lines:
                spot_res = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "以下の行から観光地名のみを1つ抽出してください。"},
                        {"role": "user", "content": line}
                    ],
                    temperature=0.2,
                    max_tokens=20
                )
                spot = spot_res.choices[0].message["content"].strip()
                if spot and spot not in extracted_spots:
                    extracted_spots.append(spot)

            # 🗺 全体マップ生成（Static）
            if map_mode == "🟥 全体マップ":
                st.markdown("### 🌐 全体マップ")
                map_urls = []
                for spot in extracted_spots:
                    map_urls.append(urllib.parse.quote(spot))
                joined = " ➔ ".join(extracted_spots)
                map_query = urllib.parse.quote(" ".join(extracted_spots))
                map_url = f"https://www.google.com/maps/embed/v1/directions?key={google_api_key}&origin={map_urls[0]}&destination={map_urls[-1]}&waypoints={'|'.join(map_urls[1:-1])}" if len(map_urls) >= 3 else f"https://www.google.com/maps/embed/v1/place?key={google_api_key}&q={map_urls[0]}"
                components.iframe(map_url, height=300)

            for spot in extracted_spots:
                st.markdown(f"---\n\n### 📍 {spot}")

                left, right = st.columns([1, 2])

                with left:
                    st.markdown("### 🖼️ 写真")
                    place_id_url = f"https://maps.googleapis.com/maps/api/place/findplacefromtext/json?input={urllib.parse.quote(spot)}&inputtype=textquery&fields=place_id&key={google_api_key}"
                    place_id_res = requests.get(place_id_url).json()
                    place_id = place_id_res["candidates"][0]["place_id"] if place_id_res.get("candidates") else None

                    if place_id:
                        detail_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=photo&key={google_api_key}"
                        photo_res = requests.get(detail_url).json()
                        if "photos" in photo_res.get("result", {}):
                            photo_ref = photo_res["result"]["photos"][0]["photo_reference"]
                            photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo_ref}&key={google_api_key}"
                            st.image(photo_url, caption=f"{spot}の写真")
                        else:
                            st.warning("写真が見つかりませんでした")
                    else:
                        st.warning("写真が見つかりませんでした")

                    st.markdown("### 🏨 宿泊候補（準備中）")
                    st.info("※楽天トラベルAPIで宿を表示予定です")

                with right:
                    if map_mode == "🔘 詳細マップ" and place_id:
                        st.markdown("### 🗺️ 地図")
                        embed_url = f"https://www.google.com/maps/embed/v1/place?key={google_api_key}&q=place_id:{place_id}"
                        components.iframe(embed_url, height=300)

                    st.markdown("### 💬 AI質問欄")
                    user_q = st.text_input(f"{spot} に関する質問：", key=f"q_{spot}")
                    if user_q:
                        answer = openai.ChatCompletion.create(
                            model="gpt-4",
                            messages=[
                                {"role": "system", "content": f"{spot}に関する質問です。観光案内として丁寧に答えてください。"},
                                {"role": "user", "content": user_q}
                            ]
                        )
                        st.success(answer.choices[0].message["content"])

        except Exception as e:
            st.error(f"エラー発生: {e}")
