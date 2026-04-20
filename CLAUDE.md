# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# アプリ起動
uv run streamlit run app.py

# Ruff lint
uv run ruff check .

# Ruff auto-fix
uv run ruff check --fix .

# 依存追加
uv add <package>
uv add --dev <package>
```

## Architecture

Streamlit マルチページアプリ。`app.py` がエントリーポイントで `init_db()` を呼びテーブルを作成する。`pages/` 以下の各ページが独立して動作する。

### データフロー

1. **USDA API** (`src/services/usda.py`) → per 100g の栄養素を取得
2. `scale_nutrients()` でグラム数にスケール済みの値を `MealEntry.nutrients`（JSON blob）に保存
3. **Dashboard** が `MealEntry` を集計し、`bmr.py` のカロリー目標・`dri.py` の推奨量と比較して表示

### DB

- SQLite (`data.db`、プロジェクトルート、`.gitignore` 済み)
- SQLAlchemy 2.0 `DeclarativeBase` + `Mapped` 型アノテーション
- `Profile` はシングルトン（`id=1` 固定）
- `MealEntry.nutrients` は `dict[str, float]` の JSON blob。スキーマ変更を避けるため栄養素カラムは追加しない

### 栄養素キー規則

`snake_case + 単位サフィックス` 形式で統一:
- `energy_kcal`, `protein_g`, `fat_g`, `carb_g`, `fiber_g`
- `sodium_mg`, `calcium_mg`, `iron_mg`, `vitamin_c_mg`
- `vitamin_d_ug`, `vitamin_b12_ug`, `folate_ug`, `vitamin_a_ug`

### BMR 計算ロジック

- `Profile.body_fat_pct` が `None` → Mifflin-St Jeor
- `body_fat_pct` が設定済み → Katch-McArdle（除脂肪体重ベース）
- TDEE = BMR × 活動係数（1.2〜1.9）
- カロリー目標: 減量 TDEE−500 / 維持 TDEE / 増量 TDEE+300

## 設定

- `.env` に `USDA_API_KEY` を設定（`.env.example` 参照）
- Ruff `line-length = 100`、`src` を first-party として isort 管理
- Python 3.11+、パッケージ管理は `uv`
