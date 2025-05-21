import openai
import streamlit as st
import requests
import urllib.parse
import streamlit.components.v1 as components

# 🔑 APIキー読み込み
openai.api_key = st.secrets["OPENAI_API_KEY"]
google_api_key = st.secrets["GOOGLE_API_KEY"]

st.set_page_config(layout="wide")
st.title("🗺️ AI旅行プランナー：観光地クリックで情報切替")

# 🌟 ユーザー入力欄
destination = st.text_input("どんな旅行がしたい？（例：大阪で1泊2日旅行したい）", "大阪で1泊2日旅行したい")

if st.button("行程表を作成！"):

    with st.spinner("AIが旅行プランを作成中やで..."):

        # 🧠 行程生成
        res = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたはプロの旅行プランナーです。時間付きの行程表を1泊2日で作成してください。"},
                {"role": "user", "content": destination}
            ]
        )

        itinerary_text = res.choices[0].message['content']
        st.markdown("### 📅 行程表")
        st.info(itinerary_text)

        # ⛳ 観光地名だけ抽出
        lines = [line for line in itinerary_text.split("\n") if line.strip()]
        spots = []
        for line in lines:
            try:
                spot_res = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "以下の行から観光地名だけを抽出してください（地名1つのみ）。"},
                        {"role": "user", "content": line}
                    ],
                    temperature=0.2,
                    max_tokens=10
                )
                spot = spot_res.choices[0].message["content"].strip()
                if spot and spot not in spots:
                    spots.append(spot)
            except:
                continue

        # 🔽 選択式
        selected = st.radio("🔍 行程内の観光地を選んでね", spots)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🖼 写真")
            map_url = f"https://www.google.com/maps/embed/v1/place?key={google_api_key}&q={urllib.parse.quote(selected)}"
            image_url = f"https://source.unsplash.com/600x400/?{urllib.parse.quote(selected)}"
            st.image(image_url, caption=selected)

        with col2:
            st.markdown("### 🗺 地図")
            components.iframe(map_url, height=300)

        st.markdown("---")
        st.markdown("### 🏨 宿泊候補（全体表示）")
        st.info("※ここに楽天トラベルAPI連携により、近隣のホテル一覧を今後表示予定です。")

        st.markdown("### 💬 AI質問欄")
        user_question = st.text_input("観光地についてAIに聞きたいことは？")
        if user_question:
            qres = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"{selected} についてガイドとして丁寧に回答してください。"},
                    {"role": "user", "content": user_question}
                ]
            )
            st.success(qres.choices[0].message['content'])
