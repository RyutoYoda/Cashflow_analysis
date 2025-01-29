import streamlit as st
from bs4 import BeautifulSoup
import requests
import plotly.graph_objects as go
import openai
import pandas as pd
import yfinance as yf
import re

# Streamlit の設定
st.set_page_config(page_title="Cash Flow and Stock Analysis", page_icon="💰")
st.title("日経企業金融AI分析")

# サイドバーで設定
st.sidebar.title("設定")
openai_api_key = st.sidebar.text_input("OpenAI APIキーを入力してください", type="password")

# 株価データの期間選択
stock_period = st.sidebar.selectbox(
    "株価データの期間を選択してください",
    options=["1mo", "6mo", "1y", "2y"],
    index=2  # デフォルトは6ヶ月
)

# **GPTを使って企業名から証券コードを取得**
def get_security_code(company_name, api_key):
    if not api_key:
        return None
    prompt = f"日本の上場企業である {company_name} の証券コード（4桁の番号）を教えてください。番号のみを出力してください。"
    try:
        openai.api_key = api_key
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        code = response.choices[0].message.content.strip()
        if re.match(r"^\d{4}$", code):
            return code
    except Exception as e:
        st.error(f"証券コード取得エラー: {e}")
    return None

# **GPTを使ってキャッシュフロー診断を実行**
def generate_gpt_analysis(prompt, api_key):
    if not api_key:
        return "エラー: APIキーが未入力です。"
    try:
        openai.api_key = api_key
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"エラー: {e}"

# **企業名入力**
company_name = st.text_input("企業名を入力してください", "トヨタ自動車")

# **証券コードの取得**
security_code = get_security_code(company_name, openai_api_key) if company_name and openai_api_key else None

# **IRBANK の URL と Yahoo Finance のティッカーシンボルを自動設定**
url, stock_ticker = "", ""
if security_code:
    url = f"https://irbank.net/{security_code}/cf"
    stock_ticker = f"{security_code}.T"  # 日本株は ".T" を付与

# **URLとティッカーシンボルを表示**
if security_code:
    st.write(f"**IRBANK URL:** [{url}]({url})")
    st.write(f"**Yahoo Finance ティッカー:** {stock_ticker}")
else:
    st.warning("証券コードが取得できませんでした。企業名を変更してみてください。")

# **株価データの取得**
def fetch_stock_data_yf(ticker, period):
    try:
        stock_data = yf.download(ticker, period=period, interval="1d")
        stock_data.reset_index(inplace=True)
        stock_data["SMA_7"] = stock_data["Close"].rolling(window=7).mean()  # 7日移動平均
        return stock_data[["Date", "Open", "High", "Low", "Close", "SMA_7"]]
    except Exception as e:
        st.error(f"Yahoo Financeからの株価データ取得中にエラーが発生しました: {e}")
        return None

# **株価データ取得ボタン**
if st.button("📈 株価データを取得") and stock_ticker:
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

        # 7日移動平均線
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

# **キャッシュフロー診断を実行**
if st.button("📝 診断を実行") and security_code:
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # **企業名を取得**
    company_name_tag = soup.find('title')
    company_name_fetched = company_name_tag.text.split(' | ')[0] if company_name_tag else company_name

    # **キャッシュフロー取得**
    table = soup.find('table', class_='cs')
    if table is None:
        st.error("キャッシュフローのデータテーブルが見つかりませんでした。")
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

    # **キャッシュフローのグラフ（株価の下に配置）**
    fig_cf = go.Figure()
    fig_cf.add_trace(go.Scatter(x=[entry['期間'] for entry in data_with_labels], 
                                y=[int(entry['営業CF'].replace(',', '').replace('−', '-')) for entry in data_with_labels], 
                                mode='lines', name='営業CF', line=dict(color='blue')))
    fig_cf.add_trace(go.Scatter(x=[entry['期間'] for entry in data_with_labels], 
                                y=[int(entry['投資CF'].replace(',', '').replace('−', '-')) for entry in data_with_labels], 
                                mode='lines', name='投資CF', line=dict(color='red')))
    fig_cf.add_trace(go.Scatter(x=[entry['期間'] for entry in data_with_labels], 
                                y=[int(entry['財務CF'].replace(',', '').replace('−', '-')) for entry in data_with_labels], 
                                mode='lines', name='財務CF', line=dict(color='green')))

    fig_cf.update_layout(title=f'{company_name_fetched} キャッシュフローの推移')
    st.plotly_chart(fig_cf)

    # **GPT診断**
    st.write(f"### {company_name_fetched} の診断結果")
    prompt = f"{company_name_fetched} のキャッシュフロー情報を診断し、投資の観点からの意見を述べてください。"
    analysis = generate_gpt_analysis(prompt, openai_api_key)
    st.write(f"診断結果: {analysis}")
