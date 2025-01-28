import streamlit as st
from bs4 import BeautifulSoup
import requests
import plotly.graph_objects as go
import openai
import pandas as pd

# Streamlit の設定
st.set_page_config(page_title="Cash Flow and Stock Analysis", page_icon="📈")
st.title("キャッシュフロー・株価分析")

# サイドバーでAPIキーを入力
st.sidebar.title("設定")
openai_api_key = st.sidebar.text_input("OpenAI APIキーサイドバーから入力してください", type="password")

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

# 株価データの取得
def get_stock_data(company_url):
    base_url = company_url.split("/cf")[0]
    stock_url = f"{base_url}/stock"
    response = requests.get(stock_url)
    soup = BeautifulSoup(response.content, 'html.parser')

    stock_table = soup.find('table', class_='stock-data')
    if stock_table:
        rows = stock_table.find_all('tr')
        dates, prices = [], []
        for row in rows[1:]:
            cols = row.find_all('td')
            if len(cols) >= 2:
                dates.append(cols[0].text.strip())
                prices.append(float(cols[1].text.strip().replace(',', '')))
        return dates[::-1], prices[::-1]  # 日付と価格を逆順に
    return [], []

# 日経平均株価データの取得
def get_nikkei_data():
    url = "https://www.nikkei.com/markets/kabu/nidxprice/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    table = soup.find('table', class_='stock-table')
    if table:
        rows = table.find_all('tr')
        dates, nikkei_prices = [], []
        for row in rows[1:]:
            cols = row.find_all('td')
            if len(cols) >= 2:
                dates.append(cols[0].text.strip())
                nikkei_prices.append(float(cols[1].text.strip().replace(',', '')))
        return dates[::-1], nikkei_prices[::-1]  # 日付と価格を逆順に
    return [], []

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

    # 株価データの取得
    stock_dates, stock_prices = get_stock_data(url)
    if stock_dates and stock_prices:
        fig_stock = go.Figure()
        fig_stock.add_trace(go.Scatter(x=stock_dates, y=stock_prices, mode='lines+markers', name='株価', line=dict(color='orange')))

        fig_stock.update_layout(
            title=f'{company_name} 株価推移',
            xaxis_title='日付',
            yaxis_title='株価 (円)',
            xaxis=dict(tickangle=-45),
            template='plotly_white'
        )
        st.plotly_chart(fig_stock)
    else:
        st.warning(f"{company_name} の株価データを取得できませんでした。")

    # 日経平均株価の取得と表示
    nikkei_dates, nikkei_prices = get_nikkei_data()
    if nikkei_dates and nikkei_prices:
        fig_nikkei = go.Figure()
        fig_nikkei.add_trace(go.Scatter(x=nikkei_dates, y=nikkei_prices, mode='lines+markers', name='日経平均', line=dict(color='purple')))

        fig_nikkei.update_layout(
            title='日経平均株価推移',
            xaxis_title='日付',
            yaxis_title='株価 (円)',
            xaxis=dict(tickangle=-45),
            template='plotly_white'
        )
        st.plotly_chart(fig_nikkei)
    else:
        st.warning("日経平均株価データを取得できませんでした。")
