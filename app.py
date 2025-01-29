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

# **企業名から証券コードを取得する関数**
def get_security_code(company_name, api_key):
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
        else:
            return None
    except Exception as e:
        st.error(f"証券コードの取得中にエラーが発生しました: {e}")
        return None

# **企業名を入力**
company_name = st.text_input("企業名を入力してください", "")

# **証券コードをGPTで取得**
security_code = None
if company_name and openai_api_key:
    security_code = get_security_code(company_name, openai_api_key)

# **証券コードが取得できたら自動設定し、入力欄は非表示**
if security_code:
    stock_ticker = f"{security_code}.T"
    url = f"https://irbank.net/{security_code}/cf"
    st.success(f"取得した証券コード: {security_code} / Yahoo Finance ティッカー: {stock_ticker}")
else:
    url = st.text_input("企業のキャッシュフローURLを入力してください", "https://irbank.net/7203/cf")
    stock_ticker = st.text_input("Yahoo Financeのティッカーシンボル", "")

# **ボタンの状態管理**
if "show_stock" not in st.session_state:
    st.session_state.show_stock = False
if "show_diagnosis" not in st.session_state:
    st.session_state.show_diagnosis = False

# **株価データ取得ボタン**
if st.button("📈 株価データを取得"):
    st.session_state.show_stock = True

# **株価グラフの表示**
if st.session_state.show_stock:
    if not stock_ticker:
        st.error("ティッカーシンボルを入力してください。")
        st.stop()

    stock_data = yf.download(stock_ticker, period=stock_period, interval="1d")
    stock_data.reset_index(inplace=True)
    stock_data["SMA_7"] = stock_data["Close"].rolling(window=7).mean()  # 7日移動平均

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

    # 7日移動平均線を追加
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

# **診断ボタン**
if st.session_state.show_stock and st.button("📝 診断を実行"):
    st.session_state.show_diagnosis = True

# **キャッシュフロー診断（グラフを復活）**
if st.session_state.show_diagnosis:
    if not openai_api_key:
        st.error("OpenAI APIキーを入力してください。")
        st.stop()

    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # **企業名を取得**
    company_name_tag = soup.find('title')
    company_name = company_name_tag.text.split(' | ')[0] if company_name_tag else "不明な企業"

    # **キャッシュフロー取得**
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

    # **キャッシュフローのグラフ**
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

    # **GPT診断**
    prompt = (
        f"以下は {company_name} のキャッシュフロー情報です:\n"
        f"営業CF: {operating_cfs[0]}\n"
        f"投資CF: {investing_cfs[0]}\n"
        f"財務CF: {financing_cfs[0]}\n"
        f"この企業の健康状態を診断し、その後投資の観点からの意見も簡潔に述べてください。"
    )
    analysis = generate_gpt_analysis(prompt, openai_api_key)
    st.write(f"### {company_name} の診断結果")
    st.write(f"診断結果: {analysis}")
