import streamlit as st
import requests

appid = st.secrets["RAKUTEN_APP_ID"]
keyword = st.text_input("検索キーワード", "大阪")

if st.button("宿泊検索"):
    url = "https://app.rakuten.co.jp/services/api/Travel/SimpleHotelSearch/20170426"
    params = {
        "applicationId": appid,
        "format": "json",
        "keyword": keyword,
        "hits": 3
    }
    res = requests.get(url, params=params).json()
    st.json(res)  # ← ここでレスポンス構造を表示

    hotels = res.get("hotels", [])
    if not hotels:
        st.warning("ホテル情報が見つかりませんでした。")
    else:
        for h in hotels:
            info = h["hotel"][0]["hotelBasicInfo"]
            st.markdown(f"### [{info['hotelName']}]({info['hotelInformationUrl']})")
            st.image(info["hotelImageUrl"], width=250)
            st.markdown(f"🚃 アクセス：{info['access']}")
            st.markdown(f"💴 最安料金：{info.get('hotelMinCharge', '不明')} 円")
            st.markdown("---")
