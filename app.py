import streamlit as st
from bs4 import BeautifulSoup
import requests
import plotly.graph_objects as go
import pandas as pd
import yfinance as yf
import re
from supabase import create_client
from groq import Groq

# Streamlit の設定
st.set_page_config(page_title="Cash Flow and Stock Analysis", page_icon="💰")
st.title("日経企業金融AI分析")

# --- Supabase 接続 ---
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"],
)

# --- Groq 接続 ---
groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
MODEL = "llama-3.3-70b-versatile"

# サイドバーで設定
st.sidebar.title("設定")
st.sidebar.info("本アプリはオープンソースLLM（Llama 3.3 70B）を使用しており、APIキーの入力は不要です。")

# 株価データの期間選択
stock_period = st.sidebar.selectbox(
    "株価データの期間を選択してください",
    options=["1mo", "6mo", "1y", "2y"],
    index=2
)

# **LLMを使って企業名から証券コードを取得**
def get_security_code(company_name):
    prompt = f"日本の上場企業である {company_name} の証券コード（4桁の番号）を教えてください。番号のみを出力してください。"
    try:
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=10,
        )
        code = response.choices[0].message.content.strip()
        if re.match(r"^\d{4}$", code):
            return code
    except Exception as e:
        st.error(f"証券コード取得エラー: {e}")
    return None

# **LLMを使ってキャッシュフロー診断を実行**
def generate_analysis(prompt):
    try:
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1024,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"エラー: {e}"

# --- タブ切り替え ---
tab1, tab2 = st.tabs(["📊 企業分析", "📋 分析履歴"])

# ============================================================
# タブ1: 企業分析
# ============================================================
with tab1:
    company_name = st.text_input("企業名を入力してください", "トヨタ自動車")

    security_code = get_security_code(company_name) if company_name else None

    url, stock_ticker = "", ""
    if security_code:
        url = f"https://irbank.net/{security_code}/cf"
        stock_ticker = f"{security_code}.T"

    if security_code:
        st.write(f"**IRBANK URL:** [{url}]({url})")
        st.write(f"**Yahoo Finance ティッカー:** {stock_ticker}")
    else:
        st.warning("証券コードが取得できませんでした。企業名を変更してみてください。")

    def fetch_stock_data_yf(ticker, period):
        try:
            stock_data = yf.download(ticker, period=period, interval="1d")
            stock_data.reset_index(inplace=True)
            stock_data["SMA_7"] = stock_data["Close"].rolling(window=7).mean()
            return stock_data[["Date", "Open", "High", "Low", "Close", "SMA_7"]]
        except Exception as e:
            st.error(f"Yahoo Financeからの株価データ取得中にエラーが発生しました: {e}")
            return None

    if st.button("📈 株価データを取得") and stock_ticker:
        stock_data = fetch_stock_data_yf(stock_ticker, stock_period)
        if stock_data is not None:
            fig_stock = go.Figure()
            fig_stock.add_trace(go.Candlestick(
                x=stock_data["Date"],
                open=stock_data["Open"],
                high=stock_data["High"],
                low=stock_data["Low"],
                close=stock_data["Close"],
                name="株価"
            ))
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

    if st.button("📝 キャッシュフローの診断を実行") and security_code:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        company_name_tag = soup.find('title')
        company_name_fetched = company_name_tag.text.split(' | ')[0] if company_name_tag else company_name

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

        st.write(f"### {company_name_fetched} の診断結果")
        prompt = f"{company_name_fetched} のキャッシュフロー情報を診断し、その後投資の観点からの意見も簡潔に述べてください。"
        analysis = generate_analysis(prompt)
        st.write(f"診断結果: {analysis}")

        # Supabaseに分析履歴を保存
        supabase.table("analysis_history").insert({
            "company_name": company_name_fetched,
            "security_code": security_code,
            "analysis_result": analysis,
        }).execute()
        st.success("分析結果を履歴に保存しました")

# ============================================================
# タブ2: 分析履歴
# ============================================================
with tab2:
    st.subheader("過去の分析履歴")

    history = supabase.table("analysis_history").select("*").order("created_at", desc=True).execute()

    if not history.data:
        st.info("まだ分析履歴がありません。「企業分析」タブで診断を実行すると、ここに履歴が保存されます。")
    else:
        st.caption(f"全 {len(history.data)} 件")
        for record in history.data:
            with st.expander(f"{record['company_name']}（{record['security_code']}）— {record['created_at'][:10]}"):
                st.write(record["analysis_result"])
                if st.button("削除", key=f"del_{record['id']}"):
                    supabase.table("analysis_history").delete().eq("id", record["id"]).execute()
                    st.rerun()
