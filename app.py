import streamlit as st
from bs4 import BeautifulSoup
import requests
import plotly.graph_objects as go
import openai
import pandas as pd
import yfinance as yf
import re

# ------------------------------------------------------------
# Streamlit の設定
# ------------------------------------------------------------
st.set_page_config(page_title="Cash Flow and Stock Analysis", page_icon="💰")
st.title("日経企業金融AI分析")

# サイドバーで設定
st.sidebar.title("設定")
openai_api_key = st.sidebar.text_input("OpenAI APIキーを入力してください", type="password")

# 株価データの期間選択
stock_period = st.sidebar.selectbox(
    "株価データの期間を選択してください",
    options=["1mo", "6mo", "1y", "2y"],
    index=2  # デフォルトは "1y"
)

# ------------------------------------------------------------
# GPT を使って企業名から証券コードを取得する関数
# ------------------------------------------------------------
def get_security_code(company_name, api_key):
    """
    GPT-3.5-turboを使って、企業名から4桁の証券コードを取得する。
    GPTの返答から4桁の数字を抽出し、最初に見つかった4桁を返す。
    """
    if not api_key:
        return None
    
    # GPTへ尋ねるプロンプトを作成
    prompt = (
        f"あなたは日本の上場企業を調べるアシスタントです。"
        f"日本の上場企業である「{company_name}」の証券コード（4桁の数字）だけを答えてください。"
    )

    try:
        openai.api_key = api_key
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0
        )
        # GPTからの返答
        content = response.choices[0].message.content.strip()
        
        # 4桁の数字を正規表現で抽出
        match = re.search(r"\b(\d{4})\b", content)
        if match:
            return match.group(1)
        else:
            return None
    except Exception as e:
        st.error(f"証券コード取得エラー: {e}")
        return None

# ------------------------------------------------------------
# GPT を使ってキャッシュフロー診断を実行する関数
# ------------------------------------------------------------
def generate_gpt_analysis(prompt, api_key):
    """
    GPT-3.5-turboを使ってキャッシュフロー診断を実行する。
    """
    if not api_key:
        return "エラー: APIキーが未入力です。"
    try:
        openai.api_key = api_key
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"エラー: {e}"

# ------------------------------------------------------------
# 企業名の入力
# ------------------------------------------------------------
company_name = st.text_input("企業名を入力してください", "トヨタ自動車")

# ------------------------------------------------------------
# 証券コードの取得
# ------------------------------------------------------------
security_code = None
if company_name and openai_api_key:
    security_code = get_security_code(company_name, openai_api_key)
elif not company_name:
    st.warning("企業名を入力してください。")
elif not openai_api_key:
    st.warning("OpenAI APIキーを入力してください。")

# ------------------------------------------------------------
# IRBANK の URL と Yahoo Finance のティッカーシンボル設定
# ------------------------------------------------------------
url, stock_ticker = "", ""
if security_code:
    url = f"https://irbank.net/{security_code}/cf"
    stock_ticker = f"{security_code}.T"  # 日本株は ".T" を付与

    st.write(f"**IRBANK URL:** [{url}]({url})")
    st.write(f"**Yahoo Finance ティッカー:** {stock_ticker}")
else:
    if company_name and openai_api_key:
        st.warning("証券コードが取得できませんでした。企業名を変更して再度お試しください。")

# ------------------------------------------------------------
# セッションステートの初期化
# ------------------------------------------------------------
if "show_stock" not in st.session_state:
    st.session_state["show_stock"] = False
if "show_diagnosis" not in st.session_state:
    st.session_state["show_diagnosis"] = False

# ------------------------------------------------------------
# 株価データ取得ボタン
# ------------------------------------------------------------
def fetch_stock_data_yf(ticker, period):
    """
    yfinanceを使って株価データを取得し、DataFrameを返す。
    """
    try:
        stock_data = yf.download(ticker, period=period, interval="1d")
        stock_data.reset_index(inplace=True)
        stock_data["SMA_7"] = stock_data["Close"].rolling(window=7).mean()  # 7日移動平均
        return stock_data[["Date", "Open", "High", "Low", "Close", "SMA_7"]]
    except Exception as e:
        st.error(f"Yahoo Financeからの株価データ取得中にエラーが発生しました: {e}")
        return None

if st.button("📈 株価データを取得"):
    if stock_ticker:
        st.session_state["show_stock"] = True
    else:
        st.error("有効な証券コードがありません。")

# ------------------------------------------------------------
# 株価グラフの表示
# ------------------------------------------------------------
if st.session_state["show_stock"] and stock_ticker:
    stock_data = fetch_stock_data_yf(stock_ticker, stock_period)
    if stock_data is not None and not stock_data.empty:
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
    else:
        st.error("株価データの取得に失敗、またはデータが存在しませんでした。")

# ------------------------------------------------------------
# 診断ボタン
# ------------------------------------------------------------
if st.session_state["show_stock"]:
    if st.button("📝 診断を実行"):
        st.session_state["show_diagnosis"] = True

# ------------------------------------------------------------
# キャッシュフロー診断
# ------------------------------------------------------------
if st.session_state["show_diagnosis"] and security_code:
    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        st.error(f"IRBANKページの取得に失敗しました: {e}")
        st.stop()

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # 企業名をIRBANKのtitleタグから取得
    company_name_tag = soup.find('title')
    company_name_fetched = company_name_tag.text.split(' | ')[0] if company_name_tag else company_name

    # キャッシュフロー情報が含まれるテーブルを取得
    table = soup.find('table', class_='cs')
    if table is None:
        st.error("キャッシュフローのデータテーブルが見つかりませんでした。")
        st.stop()

    rows = table.find_all('tr')
    if len(rows) < 2:
        st.error("キャッシュフローのデータが存在しないようです。")
        st.stop()

    # 各列を想定通り抽出（IRBANK側で構造が変わる可能性があるので注意）
    data = []
    for row in rows[1:]:
        cols = row.find_all('td')
        # 列数は会社により変動があるかもしれないので最低限の検査のみ
        # 今回は 8 列（期間, 四半期, 営業CF, 投資CF, 財務CF, フリーCF, 設備投資, 現金等）を想定
        if len(cols) >= 8:
            # 前半8列を取得
            extracted = [c.text.strip() for c in cols[:8]]
            data.append(extracted)

    if not data:
        st.error("キャッシュフローに関する必要な列が取得できませんでした。")
        st.stop()

    labels = ['期間', '四半期', '営業CF', '投資CF', '財務CF', 'フリーCF', '設備投資', '現金等']
    data_with_labels = [dict(zip(labels, row)) for row in data]

    # GPT診断の実行
    st.write(f"### {company_name_fetched} の診断結果")
    prompt = (
        f"以下は {company_name_fetched} のキャッシュフロー情報です:\n"
        f"{data_with_labels}\n"
        f"この企業の健康状態をキャッシュフローや投資観点から総合的に分析し、"
        f"わかりやすく説明してください。"
    )
    analysis = generate_gpt_analysis(prompt, openai_api_key)
    st.write(f"診断結果:\n\n{analysis}")
