# 日経企業金融AI分析

日本の上場企業のキャッシュフローと株価を可視化し、LLMによる財務診断を行うStreamlitアプリです。

## アプリURL

https://cashflowanalysis-deepseek.streamlit.app/

## 機能

### 企業分析
- **企業名から自動で証券コードを取得** — 企業名を入力するだけで、LLMが証券コード（4桁）を特定します
- **株価チャート** — Yahoo Financeからローソク足チャートと7日移動平均線を表示します。期間は1ヶ月〜2年から選択可能です
- **キャッシュフロー可視化** — 営業CF・投資CF・財務CF・フリーCFの推移を棒グラフで表示します
- **AI財務診断** — キャッシュフローの実データをもとに、LLMが財務状況の診断と投資観点からのコメントを生成します

### 分析履歴
- 診断結果はSupabase（PostgreSQL）に自動保存され、過去の分析をいつでも振り返れます
- 不要な履歴は個別に削除できます

## 使用技術

| 技術 | 用途 |
|------|------|
| Streamlit | Webアプリフレームワーク |
| yfinance | 株価・キャッシュフローデータの取得 |
| Plotly | ローソク足チャート・棒グラフの描画 |
| Groq + Llama 3.3 70B | 証券コード取得・財務診断 |
| Supabase (PostgreSQL) | 分析履歴の永続保存 |

## ローカルでの実行方法

```bash
pip install -r requirements.txt
streamlit run app.py
```

`.streamlit/secrets.toml` に以下を設定してください：

```toml
SUPABASE_URL = "your-supabase-url"
SUPABASE_KEY = "your-supabase-anon-key"
GROQ_API_KEY = "your-groq-api-key"
```
