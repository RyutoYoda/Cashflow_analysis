import streamlit as st
from bs4 import BeautifulSoup
import requests
import plotly.graph_objects as go
import openai

# Streamlit の設定
st.set_page_config(page_title="Cash Flow Analysis", page_icon="💰")
st.title("キャッシュフロー分析")

# サイドバーでAPIキーを入力
st.sidebar.title("設定")
openai_api_key = st.sidebar.text_input("OpenAI APIキーを入力してください", type="password")

# OpenAI APIの設定
def generate_gpt_analysis(prompt, api_key):
    try:
        openai.api_key = api_key
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"エラー: {e}"

# URL入力
url = st.text_input("企業のキャッシュフローURLを入力してください", "https://irbank.net/E05080/cf")

if st.button("分析開始"):
    if not openai_api_key:
        st.error("OpenAI APIキーを入力してください。")
        st.stop()

    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # 企業名を取得
    company_name_tag = soup.find('title')
    company_name = company_name_tag.text.split(' | ')[0] if company_name_tag else "不明な企業"

    # キャッシュフローデータ取得
    table = soup.find('table', class_='cs')
    if table is None:
        st.error("キャッシュフローのデータテーブルが見つかりませんでした。URLを確認してください。")
        st.stop()

    rows = table.find_all('tr')
    data = []
    for row in rows[1:]:
        cols = row.find_all('td')
        cols = [ele.text.strip() for ele in cols]
        if len(cols) == 8:
            data.append(cols)

    labels = ['期間', '四半期', '営業CF', '投資CF', '財務CF', 'フリーCF', '設備投資', '現金等']
    data_with_labels = [dict(zip(labels, row)) for row in data]

    if len(data_with_labels) == 0:
        st.error("データの解析に失敗しました。")
        st.stop()

    periods = [entry['期間'] for entry in data_with_labels]
    operating_cfs = [int(entry['営業CF'].replace(',', '').replace('−', '-')) for entry in data_with_labels]
    investing_cfs = [int(entry['投資CF'].replace(',', '').replace('−', '-')) for entry in data_with_labels]
    financing_cfs = [int(entry['財務CF'].replace(',', '').replace('−', '-')) for entry in data_with_labels]

    # 折れ線グラフ
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=periods, y=operating_cfs, mode='lines+markers', name='営業CF', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=periods, y=investing_cfs, mode='lines+markers', name='投資CF', line=dict(color='red')))
    fig.add_trace(go.Scatter(x=periods, y=financing_cfs, mode='lines+markers', name='財務CF', line=dict(color='green')))

    fig.update_layout(
        title=f'{company_name} キャッシュフローの推移',
        xaxis_title='期間',
        yaxis_title='キャッシュフロー (百万円)',
        xaxis=dict(tickangle=-45),
        legend=dict(x=0, y=1),
        template='plotly_white'
    )
    st.plotly_chart(fig)

    # GPTで診断結果を生成
    st.write(f"### {company_name} の診断結果")
    sorted_data = sorted(data_with_labels, key=lambda x: x['期間'], reverse=True)

    for entry in sorted_data:
        prompt = (
            f"以下は {company_name} のキャッシュフロー情報です:\n"
            f"期間: {entry['期間']} / 四半期: {entry['四半期']}\n"
            f"営業CF: {entry['営業CF']}\n"
            f"投資CF: {entry['投資CF']}\n"
            f"財務CF: {entry['財務CF']}\n"
            f"この企業の健康状態を診断し、その後投資の観点からの意見も簡潔に述べてください。"
        )
        analysis = generate_gpt_analysis(prompt, openai_api_key)
        st.write(f"期間: {entry['期間']} / 四半期: {entry['四半期']}")
        st.write(f"診断結果: {analysis}")
        st.write("-------------------------------------------------")
