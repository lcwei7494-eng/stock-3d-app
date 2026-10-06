import streamlit as st
import shioaji as sj
import pandas as pd
import twstock
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time, json, os, math, requests, asyncio, threading
from websockets.server import serve
from datetime import datetime, timedelta

st.set_page_config(page_title="三維定位法 & 6層量化選股與當沖盯盤全功能系統", layout="wide")

# =========================================================
# 🎨 1. 單行 CSS 主題 (徹底防止多行三引號截斷語法錯誤)
# =========================================================
st.markdown("<style>:root{--bg:#0B0E14;--panel:#121721;--panel2:#1A2130;--line:#253042;--text:#FFFFFF;--muted:#D1D8E0;--up:#F6465D;--down:#1FC98B;--accent:#4C8DFF;--gold:#FFD166;}.stApp{background:var(--bg);color:var(--text);}html,body,[class*='css']{font-family:'Noto Sans TC','Microsoft JhengHei',sans-serif;}p,label,span,div,.stMarkdown{color:#F0F4F8 !important;}h1,h2,h3,h4{font-weight:700 !important;color:#FFFFFF !important;}.block-container{padding-top:1.2rem;max-width:1400px;}#MainMenu,footer{visibility:hidden;}[data-testid='stSidebar']{background:var(--panel) !important;border-right:1px solid var(--line);}[data-testid='stSidebar'] *{color:#F0F4F8 !important;}.stTabs [data-baseweb='tab-list']{gap:6px;flex-wrap:wrap;}.stTabs [data-baseweb='tab']{background:var(--panel);border:1px solid var(--line);border-radius:999px;padding:6px 16px;}.stTabs [aria-selected='true']{background:var(--accent);border-color:var(--accent);}.stTabs [aria-selected='true'] *{color:#FFFFFF !important;font-weight:700;}.stButton>button{min-height:38px;border-radius:8px;border:1px solid var(--line);background:var(--panel2);color:#FFFFFF !important;font-weight:600;}.stButton>button:hover{border-color:var(--accent);background:var(--accent);color:#fff !important;}input,[data-baseweb='select'] > div{background:var(--panel2) !important;color:#FFFFFF !important;border-radius:8px !important;}.up,.text-red{color:var(--up) !important;font-weight:700;}.down,.text-green{color:var(--down) !important;font-weight:700;}.muted{color:#D1D8E0 !important;font-size:.9rem;}.navy-card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin-bottom:10px;}.lv{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 16px;height:100%;}.lv h5{margin:0 0 8px;font-size:.95rem;}.lv .it{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px dashed var(--line);}.level-container{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;}.level-head{display:flex;justify-content:space-between;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid var(--line);}.level-box{background:var(--panel2);border:1.5px solid var(--gold);border-radius:8px;padding:8px 12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;}.level-box.normal{border-color:var(--line);}.level-box .lbl{font-size:.9rem;color:#FFFFFF !important;font-weight:600;}.level-box .val{font-size:1.15rem;font-weight:800;}.row{display:flex;justify-content:space-between;align-items:center;background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--muted);border-radius:10px;padding:10px 14px;margin:6px 0;}.row.up-bar{border-left-color:var(--up);}.row.down-bar{border-left-color:var(--down);}.row .name{font-size:1rem;font-weight:700;color:#FFFFFF;}.row .code{color:var(--muted);font-size:.82rem;margin-left:6px;}.row .px{font-size:1.15rem;font-weight:800;text-align:right;}</style>", unsafe_allow_html=True)

# =========================================================
# 🧮 2. 核心運算與工具函式
# =========================================================
def safe_float(val, default=0.0):
    try: return float(val) if val is not None else default
    except (ValueError, TypeError): return default

def tone(pct):
    pct = safe_float(pct)
    return "up" if pct > 0 else ("down" if pct < 0 else "flat")

def stock_row_html(code, name, price, pct, tag="", prev_close=0.0):
    t = tone(pct); bar = {"up": "up-bar", "down": "down-bar"}.get(t, "")
    tag_html = f'<span style="background:var(--panel2); padding:2px 8px; border-radius:12px; font-size:.75rem; color:var(--muted);">{tag}</span>' if tag else ""
    close_info = f'<span style="color:var(--gold); font-size:.8rem;
