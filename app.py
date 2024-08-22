import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import plotly.graph_objects as go

# アプリの設定
st.set_page_config(page_title="Cash Flow Analysis", page_icon="💰")

# アプリの説明と使用方法をトグルで表示
with st.expander("アプリの説明と使用方法"):
    st.write("""
    ### このアプリについて
    このアプリは、指定されたURLからキャッシュフローのデータを取得し、企業のキャッシュフローを分析・分類します。
    
    ### 使用方法
    1. 初期URLが指定されていますが、必要に応じてURLを変更してください。
    2. 「実行」ボタンを押して、データを取得し、キャッシュフローの分析を行います。
    3. 分析結果は、分類された結果とキャッシュフローの推移グラフとして表示されます。
    """)

# URL入力欄
url = st.text_input("キャッシュフローのURLを入力してください", "https://irbank.net/E05080/cf")

# 実行ボタン
if st.button("実行"):
    # データ取得
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # テーブルからキャッシュフローのデータを抽出
    table = soup.find('table', class_='cs')
    rows = table.find_all('tr')

    # データを格納するリスト
    data = []
    for row in rows[1:]:
        cols = row.find_all('td')
        cols = [ele.text.strip() for ele in cols]
        data.append(cols)

    # ラベルを定義
    labels = ['期間', '四半期', '営業CF', '投資CF', '財務CF', 'フリーCF', '設備投資', '現金等']

    # データを辞書形式に変換
    data_with_labels = [dict(zip(labels, row)) for row in data]

    # 最新の期間のデータを赤で表示
    latest_period = data_with_labels[-1]['期間']

    # キャッシュフローの分類関数
    def classify_cash_flow(entry):
        operating_cf = int(entry['営業CF'].replace(',', '').replace('−', '-'))
        investing_cf = int(entry['投資CF'].replace(',', '').replace('−', '-'))
        financing_cf = int(entry['財務CF'].replace(',', '').replace('−', '-'))

        if operating_cf > 0 and investing_cf < 0 and financing_cf < 0:
            return "優良企業", "営業CFが黒字、投資CFが赤字、財務CFが赤字。健全な事業運営を行っており、投資を積極的に行いつつ、借入金返済も進んでいる。長期的な安定成長が見込まれるため、低リスクの投資先と見なされる。"
        elif operating_cf > 0 and investing_cf < 0 and financing_cf > 0:
            return "積極投資企業", "営業CFが黒字、投資CFが赤字、財務CFが黒字。積極的に資金調達を行い、成長のための投資を進めている。リスクはあるが、高成長が期待できる。"
        elif operating_cf > 0 and investing_cf > 0 and financing_cf < 0:
            return "過剰CF企業", "営業CFが黒字、投資CFが黒字、財務CFが赤字。現金の保有量が多く、投資機会が少ないため、株主還元やM&Aの可能性がある。"
        elif operating_cf > 0 and investing_cf < 0 and financing_cf < 0:
            return "債務返済企業/成熟・衰退企業", "営業CFが黒字、投資CFが赤字、財務CFが赤字。債務返済を進めており、成長は見込まれにくいが、安定したキャッシュフローがある。"
        elif operating_cf < 0 and investing_cf > 0 and financing_cf < 0:
            return "リストラ企業", "営業CFが赤字、投資CFが黒字、財務CFが赤字。事業再編やリストラを進めている可能性があり、リスクが高い。"
        elif operating_cf < 0 and investing_cf < 0 and financing_cf > 0:
            return "新興企業", "営業CFが赤字、投資CFが赤字、財務CFが黒字。成長のために資金調達を行い、積極的な投資をしている。成長の可能性があるが、リスクも大きい。"
        elif operating_cf < 0 and investing_cf > 0 and financing_cf > 0:
            return "危険信号企業", "営業CFが赤字、投資CFが黒字、財務CFが黒字。営業活動が低迷しており、危険信号が出ている。"
        elif operating_cf < 0 and investing_cf < 0 and financing_cf < 0:
            return "倒産危機企業", "営業CFが赤字、投資CFが赤字、財務CFが赤字。経営が危機的状況にあり、倒産のリスクが高い。"
        else:
            return "分類不明", "データの形式が正しくないか、該当する分類がありません。"

    # 取得したデータに基づいて分類を実行し、降順で表示
    data_with_labels.sort(key=lambda x: x['期間'], reverse=True)
    for entry in data_with_labels:
        classification, description = classify_cash_flow(entry)
        if entry['期間'] == latest_period:
            st.markdown(f"<span style='color:red;'>{entry['期間']} {entry['四半期']} => {classification}</span>", unsafe_allow_html=True)
        else:
            st.write(f"{entry['期間']} {entry['四半期']} => {classification}")
        st.write(f"特徴: {description}")
        st.write("-------------------------------------------------")

    # 期間ごとにCFデータを抽出
    periods = [entry['期間'] for entry in data_with_labels]
    operating_cfs = [int(entry['営業CF'].replace(',', '').replace('−', '-')) for entry in data_with_labels]
    investing_cfs = [int(entry['投資CF'].replace(',', '').replace('−', '-')) for entry in data_with_labels]
    financing_cfs = [int(entry['財務CF'].replace(',', '').replace('−', '-')) for entry in data_with_labels]

    # 折れ線グラフの作成 (Plotly)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=periods, y=operating_cfs, mode='lines+markers', name='営業CF', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=periods, y=investing_cfs, mode='lines+markers', name='投資CF', line=dict(color='red')))
    fig.add_trace(go.Scatter(x=periods, y=financing_cfs, mode='lines+markers', name='財務CF', line=dict(color='green')))

    # グラフの設定
    fig.update_layout(title='キャッシュフローの推移', xaxis_title='期間', yaxis_title='キャッシュフロー (百万円)', xaxis_tickangle=-45)

    # グラフの表示
    st.plotly_chart(fig)
