import streamlit as st
from bs4 import BeautifulSoup
import requests
import plotly.graph_objects as go
import openai
import pandas as pd
import yfinance as yf
import re

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
        return stock_data[["Date", "Open", "High", "Low", "Close"]]
    except Exception as e:
        st.error(f"Yahoo Financeからの株価データ取得中にエラーが発生しました: {e}")
        return None

# URL入力とティッカーシンボル
url = st.text_input("企業のキャッシュフローURLを入力してください", "https://irbank.net/7203/cf")

# IRBANKのURLから企業コードを自動取得
default_stock_ticker = ""
match = re.search(r"https://irbank.net/(\d+)/cf", url)
if match:
    default_stock_ticker = match.group(1) + ".T"  # 日本株は .T をつける

# ティッカーシンボルを手動修正できるように
stock_ticker = st.text_input("Yahoo Financeのティッカーシンボル", default_stock_ticker)

# ボタンの状態管理
if "show_cashflow" not in st.session_state:
    st.session_state.show_cashflow = False
if "show_stock" not in st.session_state:
    st.session_state.show_stock = True  # 常に株価グラフは表示

# キャッシュフロー診断
if st.button("キャッシュフロー診断"):
    st.session_state.show_cashflow = True  # ボタン状態を記録

if st.session_state.show_cashflow:
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
    fig_cf.add_trace(go.Scatter(x=periods, y=operating_cfs, mode='lines', name='営業CF', line=dict(color='blue')))
    fig_cf.add_trace(go.Scatter(x=periods, y=investing_cfs, mode='lines', name='投資CF', line=dict(color='red')))
    fig_cf.add_trace(go.Scatter(x=periods, y=financing_cfs, mode='lines', name='財務CF', line=dict(color='green')))

    fig_cf.update_layout(
        title=f'{company_name} キャッシュフローの推移',
        xaxis_title='期間',
        yaxis_title='キャッシュフロー (百万円)',
        xaxis=dict(tickangle=-45),
        legend=dict(x=0, y=1),
        template='plotly_white'
    )
    st.plotly_chart(fig_cf)

# 株価インサイト
if st.session_state.show_stock:
    if not stock_ticker:
        st.error("ティッカーシンボルを入力してください。")
        st.stop()

    stock_data = fetch_stock_data_yf(stock_ticker, stock_period)
    if stock_data is not None:
        fig_stock = go.Figure()

        # ローソク足チャート
        fig_stock.add_trace(go.Candlestick(
            x=stock_data["Date"],
            open=stock_data["Open"],
            high=stock_data["High"],
            low=stock_data["Low"],
            close=stock_data["Close"],
            name="株価"
        ))

        # 移動平均線を追加（7日移動平均）
        stock_data["SMA_7"] = stock_data["Close"].rolling(window=7).mean()
        fig_stock.add_trace(go.Scatter(
            x=stock_data["Date"], y=stock_data["SMA_7"],
            mode='lines', name="7日移動平均", line=dict(color='orange', width=2)
        ))

        fig_stock.update_layout(
            title=f'{stock_ticker} 株価の推移 ({stock_period})',
            xaxis_title='日付',
            yaxis_title='株価 (JPY)',
            template='plotly_white',
            xaxis_rangeslider_visible=True
        )
        st.plotly_chart(fig_stock)
    else:
        st.error("株価データの取得に失敗しました。")
