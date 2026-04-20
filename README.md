# Calorie Tracker / カロリートラッカー

個人用カロリー・栄養素管理アプリ（ローカル動作）  
A personal calorie and nutrition tracking app that runs locally.

---

## 概要 / Overview

**日本語**  
USDA FoodData Central API を使った食材検索、食事ロギング、BMR/TDEE に基づいたカロリー目標管理を行うデスクトップ向け Web アプリです。

**English**  
A Streamlit-based desktop web app for food search via the USDA FoodData Central API, meal logging, and calorie goal management based on BMR/TDEE calculations.

---

## 機能 / Features

| Phase | 機能 / Feature |
|-------|---------------|
| 1 | プロフィール管理（性別・年齢・身長・体重・体脂肪率・活動レベル・目標） |
| 1 | Profile management (gender, age, height, weight, body fat %, activity level, goal) |
| 1 | USDA FoodData Central による食材検索 / Food search via USDA FoodData Central |
| 1 | 食事ロギング（食事区分・グラム数・栄養素） / Meal logging (meal type, grams, nutrients) |
| 1 | 日次ダッシュボード（カロリー・マクロ） / Daily dashboard (calories & macros) |

---

## 技術スタック / Tech Stack

- **Python** 3.11+
- **Streamlit** — UI フレームワーク / UI framework
- **SQLite + SQLAlchemy 2.0** — ローカルDB / Local database
- **pandas / plotly** — データ処理・可視化 / Data processing & visualization
- **pydantic** — バリデーション / Validation
- **uv** — パッケージ管理 / Package management
- **Ruff** — リンター / Linter (line-length: 100)

---

## セットアップ / Setup

```bash
# 1. リポジトリをクローン / Clone the repository
git clone https://github.com/HarukiU06/calorie-tracker.git
cd calorie-tracker

# 2. 依存をインストール / Install dependencies
uv sync

# 3. 環境変数を設定 / Configure environment variables
cp .env.example .env
# .env を編集して USDA_API_KEY を設定 / Edit .env and set USDA_API_KEY

# 4. アプリを起動 / Run the app
uv run streamlit run app.py
```

USDA API キーは [https://fdc.nal.usda.gov/api-guide.html](https://fdc.nal.usda.gov/api-guide.html) から無料取得できます。  
Get a free USDA API key at [https://fdc.nal.usda.gov/api-guide.html](https://fdc.nal.usda.gov/api-guide.html).

---

## 計算ロジック / Calculation Logic

| 項目 | 方式 |
|------|------|
| BMR | Mifflin-St Jeor（体脂肪率あれば Katch-McArdle に自動切替） |
| TDEE | BMR × 活動係数（sedentary 1.2 〜 very_active 1.9） |
| カロリー目標 | 減量: TDEE−500 / 維持: TDEE / 増量: TDEE+300 |

---

## プロジェクト構造 / Project Structure

```
calorie-tracker/
├── app.py              # Streamlit エントリーポイント / entry point
├── pages/
│   ├── 1_Profile.py    # プロフィール設定 / Profile settings
│   ├── 2_Log_Meal.py   # 食事ロギング / Meal logging
│   └── 3_Dashboard.py  # 日次ダッシュボード / Daily dashboard
├── src/
│   ├── db/
│   │   ├── database.py # DB セッション管理 / DB session management
│   │   └── models.py   # SQLAlchemy モデル / ORM models
│   ├── services/
│   │   ├── usda.py     # USDA API クライアント / API client
│   │   ├── bmr.py      # BMR/TDEE 計算 / calculations
│   │   └── dri.py      # 栄養素推奨量 / DRI lookup
│   └── data/
│       └── dri.json    # DRI 参照データ / reference data
├── pyproject.toml
└── .env.example
```

---

## ライセンス / License

MIT
