import streamlit as st

from src.ui.theme import ACCENT, BG, BG_ALT, INK, MUTED, RULE, RULE_STRONG


def inject_css() -> None:
    st.html(
        f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600&family=Inter:wght@400;500&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {{
  --bg:          {BG};
  --bg-alt:      {BG_ALT};
  --ink:         {INK};
  --muted:       {MUTED};
  --rule:        {RULE};
  --rule-strong: {RULE_STRONG};
  --accent:      {ACCENT};
}}

/* ── Base ── */
html, body, [data-testid="stAppViewContainer"] {{
  background: var(--bg);
  color: var(--ink);
  font-family: 'Inter', sans-serif;
}}

/* Remove default top padding */
[data-testid="stAppViewContainer"] > .main > .block-container {{
  padding-top: 2rem;
  max-width: 1100px;
}}

/* ── Headings ── */
h1, h2 {{
  font-family: 'Inter Tight', sans-serif;
  font-weight: 500;
  letter-spacing: -0.6px;
  color: var(--ink);
}}
h3 {{
  font-family: 'Inter Tight', sans-serif;
  font-weight: 500;
  color: var(--ink);
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
  background: var(--bg-alt) !important;
  border-right: 1px solid var(--rule-strong);
}}
[data-testid="stSidebar"] > div:first-child {{
  padding: 1.5rem 1.25rem;
}}
/* Nav links */
[data-testid="stSidebarNav"] a {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  letter-spacing: 0.4px;
  color: var(--muted) !important;
  text-transform: uppercase;
}}
[data-testid="stSidebarNav"] a[aria-current="page"] {{
  color: var(--ink) !important;
  font-weight: 500;
}}

/* ── Buttons ── */
div[data-testid="stButton"] > button {{
  font-family: 'Inter Tight', sans-serif;
  font-weight: 500;
  font-size: 14px;
  border-radius: 2px;
  transition: opacity 0.15s;
}}
div[data-testid="stButton"] > button[kind="primary"],
div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {{
  background: var(--accent) !important;
  color: #fff !important;
  border: none !important;
}}
div[data-testid="stButton"] > button[kind="secondary"],
div[data-testid="stButton"] > button[data-testid="baseButton-secondary"] {{
  background: transparent !important;
  color: var(--ink) !important;
  border: 1px solid var(--rule-strong) !important;
}}
div[data-testid="stButton"] > button:hover {{ opacity: 0.8; }}

/* ── Progress ── */
div[data-testid="stProgress"] > div {{
  background: var(--rule-strong) !important;
  height: 3px !important;
  border-radius: 0 !important;
}}
div[data-testid="stProgress"] > div > div {{
  background: var(--accent) !important;
  height: 3px !important;
  border-radius: 0 !important;
}}

/* ── Metrics ── */
div[data-testid="stMetric"] label {{
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 10px !important;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: var(--muted) !important;
}}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
  font-family: 'Inter Tight', sans-serif !important;
  font-size: 24px !important;
  font-weight: 500 !important;
  color: var(--ink) !important;
}}

/* ── Inputs ── */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {{
  font-family: 'Inter Tight', sans-serif;
  font-size: 18px;
  background: transparent !important;
  border: none !important;
  border-bottom: 2px solid var(--ink) !important;
  border-radius: 0 !important;
  color: var(--ink) !important;
  padding: 4px 0 !important;
}}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus {{
  border-bottom-color: var(--accent) !important;
  box-shadow: none !important;
}}

/* ── Selectbox ── */
div[data-testid="stSelectbox"] > div > div {{
  background: transparent !important;
  border: 1px solid var(--rule-strong) !important;
  border-radius: 2px !important;
  font-family: 'Inter', sans-serif;
}}

/* ── DataFrames ── */
div[data-testid="stDataFrame"] th {{
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 10px !important;
  text-transform: uppercase !important;
  letter-spacing: 0.6px !important;
  color: var(--muted) !important;
  background: var(--bg-alt) !important;
}}

/* ── Divider ── */
hr {{
  border: none;
  border-top: 1px solid var(--rule);
  margin: 1.5rem 0;
}}

/* ── Alerts ── */
div[data-testid="stAlert"] {{
  border-radius: 2px;
  font-family: 'Inter', sans-serif;
  font-size: 14px;
}}
</style>
"""
    )
