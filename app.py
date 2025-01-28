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
def generate_gpt_classification(prompt, api_key):
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

# 分析実行
if st.button("分析開始"):
    if not openai_api_key:
        st.error("OpenAI APIキーを入力してください。")
        st.stop()

    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

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
        title='キャッシュフローの推移',
        xaxis_title='期間',
        yaxis_title='キャッシュフロー (百万円)',
        xaxis=dict(tickangle=-45),
        legend=dict(x=0, y=1),
        template='plotly_white'
    )
    st.plotly_chart(fig)

    # GPTで分類結果を生成
    st.write("### キャッシュフロー分類結果")
    sorted_data = sorted(data_with_labels, key=lambda x: x['期間'], reverse=True)

    for entry in sorted_data:
        prompt = (
            f"以下は企業のキャッシュフロー情報です:\n"
            f"期間: {entry['期間']} / 四半期: {entry['四半期']}\n"
            f"営業CF: {entry['営業CF']}\n"
            f"投資CF: {entry['投資CF']}\n"
            f"財務CF: {entry['財務CF']}\n"
            f"この企業の健康状態を診断し、簡潔に説明してください。"
        )
        classification = generate_gpt_classification(prompt, openai_api_key)
        st.write(f"期間: {entry['期間']} / 四半期: {entry['四半期']}")
        st.write(f"診断結果: {classification}")
        st.write("-------------------------------------------------")



# import streamlit as st
# from bs4 import BeautifulSoup
# import requests
# import plotly.graph_objects as go

# st.set_page_config(page_title="Cash Flow Analysis", page_icon="💰")

# st.title("キャッシュフロー分析")


# with st.expander("アプリの説明と使用方法"):
#     st.write("""
#         このアプリは、指定した企業のキャッシュフローを分析し、キャッシュフローのタイプを分類します。
#         URLを入力して実行ボタンを押すと、最新のデータを取得して、キャッシュフローのグラフと分類結果を表示します。
#         分類結果は最新の期間が赤色で表示されます。

#         **使い方:**
#         1. IRBANKのキャッシュ・フローの状況ページのURLを入力します。
#            - 例: `https://irbank.net/企業ID/cf` のように、`企業ID` 部分を対象企業のIDに置き換えてください。
#         2. URLを入力したら、「実行」ボタンを押してください。
#         3. 分析結果が表示されます。
#     """)

# # URL i
# url = st.text_input("企業のキャッシュフローURLを入力してください", "https://irbank.net/E05080/cf")

# if st.button("分析開始"):
#     response = requests.get(url)
#     soup = BeautifulSoup(response.content, 'html.parser')

#     # テーブルからキャッシュフローのデータを抽出
#     table = soup.find('table', class_='cs')

#     # エラーチェック：テーブルが見つからない場合
#     if table is None:
#         st.error("キャッシュフローのデータテーブルが見つかりませんでした。URLを確認してください。")
#         st.stop()

#     rows = table.find_all('tr')

#     # データを格納するリスト
#     data = []
#     for row in rows[1:]:
#         cols = row.find_all('td')
#         cols = [ele.text.strip() for ele in cols]
#         if len(cols) == 8:  # 8列あることを確認
#             data.append(cols)

#     # ラベルを定義
#     labels = ['期間', '四半期', '営業CF', '投資CF', '財務CF', 'フリーCF', '設備投資', '現金等']

#     # データを辞書形式に変換
#     data_with_labels = [dict(zip(labels, row)) for row in data]

#     # データが正しく取得されたか確認
#     if len(data_with_labels) == 0:
#         st.error("データの解析に失敗しました。ページ構造が変わった可能性があります。")
#         st.stop()

#     # 期間ごとにCFデータを抽出
#     try:
#         periods = [entry['期間'] for entry in data_with_labels]
#         operating_cfs = [int(entry['営業CF'].replace(',', '').replace('−', '-')) for entry in data_with_labels]
#         investing_cfs = [int(entry['投資CF'].replace(',', '').replace('−', '-')) for entry in data_with_labels]
#         financing_cfs = [int(entry['財務CF'].replace(',', '').replace('−', '-')) for entry in data_with_labels]
#     except KeyError as e:
#         st.error(f"データ解析中にエラーが発生しました: {e}")
#         st.stop()

#     # 折れ線グラフの作成 (Plotly)
#     fig = go.Figure()

#     fig.add_trace(go.Scatter(x=periods, y=operating_cfs, mode='lines+markers', name='営業CF', line=dict(color='blue')))
#     fig.add_trace(go.Scatter(x=periods, y=investing_cfs, mode='lines+markers', name='投資CF', line=dict(color='red')))
#     fig.add_trace(go.Scatter(x=periods, y=financing_cfs, mode='lines+markers', name='財務CF', line=dict(color='green')))

#     # グラフの設定
#     fig.update_layout(
#         title='キャッシュフローの推移',
#         xaxis_title='期間',
#         yaxis_title='キャッシュフロー (百万円)',
#         xaxis=dict(tickangle=-45),
#         legend=dict(x=0, y=1),
#         template='plotly_white'
#     )

#     st.plotly_chart(fig)

#     # キャッシュフローの分類関数
#     def classify_cash_flow(entry):
#         operating_cf = int(entry['営業CF'].replace(',', '').replace('−', '-'))
#         investing_cf = int(entry['投資CF'].replace(',', '').replace('−', '-'))
#         financing_cf = int(entry['財務CF'].replace(',', '').replace('−', '-'))

#         if operating_cf > 0 and investing_cf < 0 and financing_cf < 0:
#             return "優良企業", "営業CFが黒字、投資CFが赤字、財務CFが赤字。健全な事業運営を行っており、投資を積極的に行いつつ、借入金返済も進んでいる。長期的な安定成長が見込まれるため、低リスクの投資先と見なされる。"
#         elif operating_cf > 0 and investing_cf < 0 and financing_cf > 0:
#             return "積極投資企業", "営業CFが黒字、投資CFが赤字、財務CFが黒字。積極的に資金調達を行い、成長のための投資を進めている。リスクはあるが、高成長が期待できる。"
#         elif operating_cf > 0 and investing_cf > 0 and financing_cf < 0:
#             return "過剰CF企業", "営業CFが黒字、投資CFが黒字、財務CFが赤字。現金の保有量が多く、投資機会が少ないため、株主還元やM&Aの可能性がある。"
#         elif operating_cf > 0 and investing_cf < 0 and financing_cf < 0:
#             return "債務返済企業/成熟・衰退企業", "営業CFが黒字、投資CFが赤字、財務CFが赤字。債務返済を進めており、成長は見込まれにくいが、安定したキャッシュフローがある。"
#         elif operating_cf < 0 and investing_cf > 0 and financing_cf < 0:
#             return "リストラ企業", "営業CFが赤字、投資CFが黒字、財務CFが赤字。事業再編やリストラを進めている可能性があり、リスクが高い。"
#         elif operating_cf < 0 and investing_cf < 0 and financing_cf > 0:
#             return "新興企業", "営業CFが赤字、投資CFが赤字、財務CFが黒字。成長のために資金調達を行い、積極的な投資をしている。成長の可能性があるが、リスクも大きい。"
#         elif operating_cf < 0 and investing_cf > 0 and financing_cf > 0:
#             return "危険信号企業", "営業CFが赤字、投資CFが黒字、財務CFが黒字。営業活動が低迷しており、危険信号が出ている。"
#         elif operating_cf < 0 and investing_cf < 0 and financing_cf < 0:
#             return "倒産危機企業", "営業CFが赤字、投資CFが赤字、財務CFが赤字。経営が危機的状況にあり、倒産のリスクが高い。"
#         else:
#             return "分類不明", "データの形式が正しくないか、該当する分類がありません。"

#     # 取得したデータを降順でソートして分類を実行
#     st.write("### キャッシュフロー分類結果")
#     sorted_data = sorted(data_with_labels, key=lambda x: x['期間'], reverse=True)

#     for entry in sorted_data:
#         classification, description = classify_cash_flow(entry)
#         if entry == sorted_data[0]:  # 最新の期間を赤字で表示
#             st.markdown(f"<span style='color:red'>[直近のデータ] {entry['期間']} {entry['四半期']} => **{classification}**</span>", unsafe_allow_html=True)
#         else:
#             st.write(f"{entry['期間']} {entry['四半期']} => **{classification}**")
#         st.write(f"特徴: {description}")
#         st.write("-------------------------------------------------")
