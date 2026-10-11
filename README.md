# Calorie Tracker

A personal calorie and nutrition tracking app that runs locally.

---

## Overview

A Streamlit-based desktop web app for food search via the USDA FoodData Central API, meal logging, and calorie goal management based on BMR/TDEE calculations.

---

## Features

Profile management (gender, age, height, weight, body fat %, activity level, goal)
Food search via USDA FoodData Central
Meal logging (meal type, grams, nutrients)
 Daily dashboard (calories & macros)

---

## Tech Stack

- **Python** 3.11+
- **Streamlit** — UI framework
- **SQLite + SQLAlchemy 2.0** — Local database
- **pandas / plotly** — Data processing & visualization
- **pydantic** — Validation
- **uv** — Package management
- **Ruff** — Linter (line-length: 100)

---

## Setup

```bash
# 1. Clone the repository
git clone https://github.com/HarukiU06/calorie-tracker.git
cd calorie-tracker

# 2. Install dependencies
uv sync

# 3. Configure environment variables
cp .env.example .env
# Edit .env and set USDA_API_KEY

# 4. Run the app
uv run streamlit run app.py
```

Get a free USDA API key at [https://fdc.nal.usda.gov/api-guide.html](https://fdc.nal.usda.gov/api-guide.html).

---

## Calculation Logic

| Item | Method |
|------|--------|
| BMR | Mifflin-St Jeor (auto-switches to Katch-McArdle if body fat % is provided) |
| TDEE | BMR × activity factor (sedentary 1.2 — very active 1.9) |
| Calorie target | Lose: TDEE−500 / Maintain: TDEE / Gain: TDEE+300 |

---

## Project Structure

```
calorie-tracker/
├── app.py              # Streamlit entry point
├── pages/
│   ├── 1_Profile.py    # Profile settings
│   ├── 2_Log_Meal.py   # Meal logging
│   └── 3_Dashboard.py  # Daily dashboard
├── src/
│   ├── db/
│   │   ├── database.py # DB session management
│   │   └── models.py   # SQLAlchemy ORM models
│   ├── services/
│   │   ├── usda.py     # USDA API client
│   │   ├── bmr.py      # BMR/TDEE calculations
│   │   └── dri.py      # DRI lookup
│   └── data/
│       └── dri.json    # DRI reference data
├── pyproject.toml
└── .env.example
```

---

## Security

- The app has **no authentication**. `.streamlit/config.toml` binds the server to
  `localhost` only — don't expose it to a network without an authenticating reverse proxy.
- Keep `USDA_API_KEY` in `.env` (git-ignored). The key is sent in the `X-Api-Key`
  header, never in URLs, and API errors shown in the UI don't include request details.
- `data.db` contains personal health data; it is git-ignored and created with `0600` permissions.
- Text from the USDA API and the database is HTML-escaped before it is rendered.
- Dependabot (`.github/dependabot.yml`) opens weekly dependency update PRs. To audit locally:

  ```bash
  uv export --format requirements-txt --no-hashes --all-groups > /tmp/req.txt
  uvx pip-audit -r /tmp/req.txt
  ```
