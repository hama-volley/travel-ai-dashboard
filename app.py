# YouTubeなし＆新しいUIレイアウトに基づく旅行AIダッシュボードのフルコード（Streamlit用 app.py）

app_code = '''
import openai
import streamlit as st
import requests
import urllib.parse
import streamlit.components.v1 as components

# 🔐 APIキーの読み込み
openai.api_key = st.secrets["OPENAI_API_KEY"]
google_places_key = st.secrets["GOOGLE_PLACES_API_KEY"]

st.set_page_config(layout="wide")
st.title("✈️ AI旅行プランナー ダッシュボード")

# --- Google Places API ---
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

# --- スポット名抽出（OpenAIで正規化） ---
def extract_spot_name(description):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "以下の文章から観光地名や施設名を1つだけ抽出して、検索キーワードとして最適な短い名称を返してください。"},
                {"role": "user", "content": description}
            ],
            temperature=0.2,
            max_tokens=20
        )
        return response.choices[0].message['content'].strip()
    except:
        return None

# --- メイン ---
destination = st.text_input("旅行したい内容を入力してね", "大阪で1泊2日旅行したい")

if st.button("行程表を作成！"):
    with st.spinner("AIが旅行プランを作成中やで..."):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "あなたはプロの旅行プランナーです。入力に基づいて1泊2日の行程表を作成してください。"},
                    {"role": "user", "content": destination}
                ]
            )
            itinerary = response.choices[0].message["content"]
            st.markdown("### 📅 行程表")
            st.markdown(itinerary)

            lines = [line for line in itinerary.split("\\n") if line.strip()]
            extracted_spots = []

            for line in lines:
                spot = extract_spot_name(line)
                if not spot or spot in extracted_spots:
                    continue
                extracted_spots.append(spot)

                place_id = get_place_id(spot, google_places_key)
                photo_url = get_place_photo_url(place_id, google_places_key) if place_id else None
                map_url = get_map_embed_url_from_place_id(place_id, google_places_key) if place_id else None

                st.markdown(f"---\\n\\n### 📍 {spot}")

                left_col, right_col = st.columns([3, 2])
                with left_col:
                    upper, lower = st.columns(2)
                    with upper:
                        st.markdown("#### 🖼 写真")
                        if photo_url:
                            st.image(photo_url, caption=spot)
                        else:
                            st.warning("写真が見つかりませんでした")

                    with lower:
                        st.markdown("#### 🗺 地図")
                        if map_url:
                            components.iframe(map_url, height=250)
                        else:
                            st.warning("地図が見つかりませんでした")

                with right_col:
                    st.markdown("#### 🏨 宿泊候補（準備中）")
                    st.info("ここに楽天トラベルAPIで周辺ホテル一覧を表示予定です。")

                    st.markdown("#### 💬 AI質問欄")
                    user_question = st.text_input(f"{spot} に関する質問をどうぞ：", key=f"q_{spot}")
                    if user_question:
                        answer = openai.ChatCompletion.create(
                            model="gpt-4",
                            messages=[
                                {"role": "system", "content": f"以下は {spot} に関する質問です。ガイドとして丁寧に答えてください。"},
                                {"role": "user", "content": user_question}
                            ]
                        )
                        st.success(answer.choices[0].message["content"])

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
'''
