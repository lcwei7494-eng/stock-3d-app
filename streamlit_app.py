import streamlit as st
import shioaji as sj
import pandas as pd
import twstock
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import json
import os
import math
import requests
import asyncio
import threading
from websockets.server import serve
from datetime import datetime, timedelta

st.set_page_config(page_title="三維定位法 & 6層量化選股與當沖盯盤全功能系統", layout="wide")

# =========================================================
# 🎨 UI 主題（專業券商級戰情室 Terminal 主題 — 高亮高清版）
# =========================================================
_CSS = """
<style>
:root {
  --bg:#0B0E14; --panel:#121721; --panel2:#1A2130; --line:#253042;
  --text:#FFFFFF; --muted:#D1D8E0; --up:#F6465D; --down:#1FC98B; --accent:#4C8DFF;
  --gold:#FFD166;
}
.stApp { background:var(--bg); color:var(--text); }
html, body, [class*="css"] { font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif; }

p, label, span, div, .stMarkdown { color: #F0F4F8 !important; }
h1, h2, h3, h4 { font-weight:700 !important; color:#FFFFFF !important; }
.block
