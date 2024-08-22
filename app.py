import streamlit as st
from bs4 import BeautifulSoup
import requests
import matplotlib.pyplot as plt
import japanize_matplotlib

# タイトル
st.title("キャッシュフロー分析アプリ")

# トグルでアプリの説明を表示
with st.expander("アプリの説明を見る"):
    st.write("""
    このアプリは、企業のキャッシュフローを分析し、8つの分類に基づいてその特徴を評価します。  
    以下の手順でご利用ください:
    
    1. IRBANKのキャッシュ・フローの状況ページのURLを入力してください。
    2. 「分析する」ボタンを押すと、データが取得され、キャッシュフローの推移がグラフとして表示されます。
    3. さらに、企業のキャッシュフローがどのパターンに分類されるかも表示されます。

    URLの例: `https://irbank.net/E05080/cf`
    """)

# URL入力
url = st.text_input("キャッシュフローを取得する企業のURLを入力してください", "https://irbank.net/E05080/cf")

if st.button("分析する") and url:
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

    # 折れ線グラフを描画する関数
    def plot_cash_flows(data_with_labels):
        periods = [entry['期間'] for entry in data_with_labels]
        operating_cfs = [int(entry['営業CF'].replace(',', '').replace('−', '-')) for entry in data_with_labels]
        investing_cfs = [int(entry['投資CF'].replace(',', '').replace('−', '-')) for entry in data_with_labels]
        financing_cfs = [int(entry['財務CF'].replace(',', '').replace('−', '-')) for entry in data_with_labels]

        # 折れ線グラフの作成
        plt.figure(figsize=(10, 6))
        plt.plot(periods, operating_cfs, marker='o', label='営業CF', color='blue')
        plt.plot(periods, investing_cfs, marker='o', label='投資CF', color='red')
        plt.plot(periods, financing_cfs, marker='o', label='財務CF', color='green')

        # グラフの設定
        plt.title('キャッシュフローの推移')
        plt.xlabel('期間')
        plt.ylabel('キャッシュフロー (百万円)')
        plt.xticks(rotation=45)
        plt.legend()
        plt.grid(True)

        # グラフの表示
        st.pyplot(plt)

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

    # 折れ線グラフを表示
    plot_cash_flows(data_with_labels)

    # 取得したデータに基づいて分類を実行
    for entry in data_with_labels:
        classification, description = classify_cash_flow(entry)
        st.write(f"{entry['期間']} {entry['四半期']} => {classification}")
        st.write(f"特徴: {description}")
        st.write("-------------------------------------------------")

