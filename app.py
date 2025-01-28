import streamlit as st
from bs4 import BeautifulSoup
import requests
import plotly.graph_objects as go
import openai
import pandas as pd
import yfinance as yf

# Streamlit の設定
st.set_page_config(page_title="Cash Flow and Stock Analysis", page_icon="📊")
st.title("キャッシュフローと株価分析")

# サイドバーで設定
st.sidebar.title("設定")
openai_api_key = st.sidebar.text_input("OpenAI APIキーを入力してください", type="password")

# 株価データの期間選択
stock_period = st.sidebar.selectbox(
    "株価データの期間を選択してください",
    options=["1wk", "1mo", "6mo", "1y", "2y"],
    index=2  # デフォルトは6ヶ月
)

# OpenAI APIの設定
def generate_gpt_analysis(prompt, api_key):
    try:
        openai.api_key = api_key
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"エラー: {e}"

# 株価データの取得 (yfinance)
def fetch_stock_data_yf(ticker, period):
    try:
        stock_data = yf.download(ticker, period=period, interval="1d")
        stock_data.reset_index(inplace=True)
        return stock_data[["Date", "Close"]]
    except Exception as e:
        st.error(f"Yahoo Financeからの株価データ取得中にエラーが発生しました: {e}")
        return None

# URL入力とティッカーシンボル
url = st.text_input("企業のキャッシュフローURLを入力してください", "https://irbank.net/E05080/cf")
stock_ticker = st.text_input("Yahoo Financeのティッカーシンボルを入力してください", "7203.T")  # 例: トヨタのティッカーシンボルは "7203.T"

# キャッシュフロー診断
if st.button("キャッシュフロー診断"):
    if not openai_api_key:
        st.error("OpenAI APIキーを入力してください。")
        st.stop()

    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # 企業名を取得
    company_name_tag = soup.find('title')
    company_name = company_name_tag.text.split(' | ')[0] if company_name_tag else "不明な企業"

    # キャッシュフロー取得
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

    # キャッシュフローのグラフ
    fig_cf = go.Figure()
    fig_cf.add_trace(go.Scatter(x=periods, y=operating_cfs, mode='lines+markers', name='営業CF', line=dict(color='blue')))
    fig_cf.add_trace(go.Scatter(x=periods, y=investing_cfs, mode='lines+markers', name='投資CF', line=dict(color='red')))
    fig_cf.add_trace(go.Scatter(x=periods, y=financing_cfs, mode='lines+markers', name='財務CF', line=dict(color='green')))

    fig_cf.update_layout(
        title=f'{company_name} キャッシュフローの推移',
        xaxis_title='期間',
        yaxis_title='キャッシュフロー (百万円)',
        xaxis=dict(tickangle=-45),
        legend=dict(x=0, y=1),
        template='plotly_white'
    )
    st.plotly_chart(fig_cf)

    # GPT診断
    st.write(f"### {company_name} の診断結果")
    sorted_data = sorted(data_with_labels, key=lambda x: x['期間'], reverse=True)

    for entry in sorted_data:
        prompt = (
            f"以下は {company_name} のキャッシュフロー情報です:\n"
            f"期間: {entry['期間']} / 四半期: {entry['四半期']}\n"
            f"営業CF: {entry['営業CF']}\n"
            f"投資CF: {entry['投資CF']}\n"
            f"財務CF: {entry['財務CF']}\n"
            f"この企業の健康状態を診断し、投資の観点からの意見を述べてください。"
        )
        analysis = generate_gpt_analysis(prompt, openai_api_key)
        st.write(f"期間: {entry['期間']} / 四半期: {entry['四半期']}")
        st.write(f"診断結果: {analysis}")
        st.write("-------------------------------------------------")

# 株価インサイト
if st.button("株価インサイト"):
    if not stock_ticker:
        st.error("ティッカーシンボルを入力してください。")
        st.stop()

    stock_data = fetch_stock_data_yf(stock_ticker, stock_period)
    if stock_data is not None:
        fig_stock = go.Figure()
        fig_stock.add_trace(go.Scatter(x=stock_data["Date"], y=stock_data["Close"], mode='lines+markers', name='株価'))
        fig_stock.update_layout(
            title=f'{stock_ticker} 株価の推移',
            xaxis_title='日付',
            yaxis_title='株価 (JPY)',
            template='plotly_white'
        )
        st.plotly_chart(fig_stock)
    else:
        st.error("株価データの取得に失敗しました。")
