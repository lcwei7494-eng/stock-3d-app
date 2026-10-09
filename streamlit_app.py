import streamlit as st
import shioaji as sj
import pandas as pd
import numpy as np
import twstock
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time, json, os, math, requests, asyncio, threading
from websockets.server import serve
from datetime import datetime, timedelta

st.set_page_config(page_title="三維定位法 & 6層量化選股與智慧下單當沖盯盤系統", layout="wide")

# =========================================================
# 🎨 1. 極致高對比 UI 主題 (修復表格 Hover 白底白字問題)
# =========================================================
_CSS = """
<style>
:root {
    --bg: #0B0E14;
    --panel: #121721;
    --panel2: #1E2638;
    --line: #2A364F;
    --text: #FFFFFF;
    --muted: #CBD5E1;
    --up: #F6465D;
    --down: #1FC98B;
    --accent: #4C8DFF;
    --gold: #FFD166;
}

.stApp {
    background: var(--bg);
    color: var(--text);
}

html, body, p, span, label, div {
    font-family: 'Noto Sans TC', 'Microsoft JhengHei', sans-serif;
}

h1, h2, h3, h4, h5, h6 {
    color: #FFFFFF !important;
    font-weight: 700 !important;
}

.block-container {
    padding-top: 1.2rem;
    max-width: 1400px;
}

#MainMenu, footer { visibility: hidden; }

/* 側邊欄樣式 */
[data-testid='stSidebar'] {
    background: var(--panel) !important;
    border-right: 1px solid var(--line);
}
[data-testid='stSidebar'] * {
    color: #FFFFFF !important;
}

/* 標籤頁 Tabs 樣式 */
.stTabs [data-baseweb='tab-list'] {
    gap: 6px;
    flex-wrap: wrap;
}
.stTabs [data-baseweb='tab'] {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 999px;
    padding: 6px 16px;
}
.stTabs [aria-selected='true'] {
    background: var(--accent);
    border-color: var(--accent);
}
.stTabs [aria-selected='true'] * {
    color: #FFFFFF !important;
    font-weight: 700;
}

/* 按鈕樣式 */
.stButton>button {
    min-height: 38px;
    border-radius: 8px;
    border: 1px solid var(--line);
    background: var(--panel2);
    color: #FFFFFF !important;
    font-weight: 600;
}
.stButton>button:hover {
    border-color: var(--accent);
    background: var(--accent);
    color: #FFFFFF !important;
}

/* 輸入框樣式 */
input, select, textarea, [data-baseweb='select'] > div {
    background: var(--panel2) !important;
    color: #FFFFFF !important;
    border-radius: 8px !important;
    border: 1.5px solid var(--line) !important;
}
[data-baseweb='popover'] * {
    background: #1E2638 !important;
    color: #FFFFFF !important;
}
[data-baseweb='calendar'] * {
    color: #FFFFFF !important;
}

/* Dataframe 表格修復 */
[data-testid='stDataFrame'] {
    background: var(--panel) !important;
    border-radius: 8px;
    padding: 4px;
    border: 1px solid var(--line);
}

[data-testid='stDataFrame'] * {
    color: #FFFFFF !important;
}

[data-testid='stDataFrame'] [role='grid'] [role='row']:hover,
[data-testid='stDataFrame'] [role='grid'] [role='row']:hover * {
    background-color: #2A364F !important;
    color: #FFFFFF !important;
}

[data-testid='stDataFrame'] [role='columnheader'],
[data-testid='stDataFrame'] [role='columnheader'] * {
    background-color: #1A2130 !important;
    color: var(--gold) !important;
    font-weight: 700 !important;
}

/* 狀態顏色類別 */
.up, .text-red { color: var(--up) !important; font-weight: 700; }
.down, .text-green { color: var(--down) !important; font-weight: 700; }
.muted { color: var(--muted) !important; font-size: .9rem; }

.navy-card {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 10px;
}
.lv {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 12px 16px;
    height: 100%;
}
.lv h5 { margin: 0 0 8px; font-size: .95rem; }
.lv .it {
    display: flex;
    justify-content: space-between;
    padding: 5px 0;
    border-bottom: 1px dashed var(--line);
}
.level-container {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 14px;
}
.level-head {
    display: flex;
    justify-content: space-between;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--line);
}
.level-box {
    background: var(--panel2);
    border: 1.5px solid var(--gold);
    border-radius: 8px;
    padding: 8px 12px;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.level-box.normal { border-color: var(--line); }
.level-box .lbl { font-size: .9rem; color: #FFFFFF !important; font-weight: 600; }
.level-box .val { font-size: 1.15rem; font-weight: 800; }

.row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--panel);
    border: 1px solid var(--line);
    border-left: 4px solid var(--muted);
    border-radius: 10px;
    padding: 10px 14px;
    margin: 6px 0;
}
.row.up-bar { border-left-color: var(--up); }
.row.down-bar { border-left-color: var(--down); }
.row .name { font-size: 1rem; font-weight: 700; color: #FFFFFF; }
.row .code { color: var(--muted); font-size: .82rem; margin-left: 6px; }
.row .px { font-size: 1.15rem; font-weight: 800; text-align: right; }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

# =========================================================
# 💾 2. 自選股與持股資料安全無損讀寫模組
# =========================================================
WATCHLIST_FILE = "watchlist.json"
HOLDINGS_FILE = "holdings.json"
STOCKIFY_JOURNAL_FILE = "stockify_journal.json"

def load_saved_watchlist():
    default_list = ["3624 光頡", "2360 致茂", "8111 立碁", "4971 IET-KY", "4991 環宇-KY", "2330 台積電", "3374 精材", "1785 光洋科", "3081 聯亞", "3088 艾訊", "3219 倚強科", "3228 金麗科"]
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    combined = list(data)
                    for item in default_list:
                        if item not in combined: combined.append(item)
                    return combined
        except Exception: pass
    return default_list

def save_watchlist_to_file(watchlist):
    try:
        unique_list = []
        for item in watchlist:
            if item not in unique_list: unique_list.append(item)
        with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(unique_list, f, ensure_ascii=False, indent=2)
    except Exception as e: st.error("寫入自選股失敗: " + str(e))

def load_saved_holdings():
    if os.path.exists(HOLDINGS_FILE):
        try:
            with open(HOLDINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict): return data
        except Exception: pass
    return {}

def save_stock_holding_multi(code, trades_list, custom_stop, custom_target):
    holdings = load_saved_holdings()
    holdings[str(code)] = {"trades": trades_list, "custom_stop": float(custom_stop), "custom_target": float(custom_target)}
    try:
        with open(HOLDINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(holdings, f, ensure_ascii=False, indent=2)
    except Exception as e: st.error("儲存持股失敗: " + str(e))

def load_saved_stockify_journal():
    if os.path.exists(STOCKIFY_JOURNAL_FILE):
        try:
            with open(STOCKIFY_JOURNAL_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list): return data
        except Exception: pass
    return [
        {"account": "主帳戶", "date": "2025-05-28", "code": "3015", "name": "全漢", "type": "買進", "price": 61.9, "shares": 1000, "fee_discount": 0.2, "note": "存股建倉"},
        {"account": "主帳戶", "date": "2026-06-04", "code": "3015", "name": "全漢", "type": "賣出", "price": 62.7, "shares": 1000, "fee_discount": 0.2, "note": "獲利平倉"},
        {"account": "主帳戶", "date": "2026-10-02", "code": "3624", "name": "光頡", "type": "買進", "price": 148.5, "shares": 1000, "fee_discount": 0.2, "note": "突破買進"},
        {"account": "主帳戶", "date": "2026-10-05", "code": "3624", "name": "光頡", "type": "買進", "price": 152.0, "shares": 1000, "fee_discount": 0.2, "note": "加碼進場"}
    ]

def save_stockify_journal_to_file(journal_data):
    try:
        with open(STOCKIFY_JOURNAL_FILE, "w", encoding="utf-8") as f:
            json.dump(journal_data, f, ensure_ascii=False, indent=2)
    except Exception as e: st.error("儲存 Stockify 交易日記失敗: " + str(e))

if "watchlist" not in st.session_state: st.session_state["watchlist"] = load_saved_watchlist()
if "holdings" not in st.session_state: st.session_state["holdings"] = load_saved_holdings()
if "stockify_journal" not in st.session_state: st.session_state["stockify_journal"] = load_saved_stockify_journal()

def add_to_watchlist_safe(stock_lbl):
    if stock_lbl not in st.session_state["watchlist"]:
        st.session_state["watchlist"].append(stock_lbl)
        save_watchlist_to_file(st.session_state["watchlist"])

# =========================================================
# 🧮 3. 核心工具與張宇明三線多空演算法模組
# =========================================================
def safe_float(val, default=0.0):
    try: return float(val) if val is not None else default
    except (ValueError, TypeError): return default

def tone(pct):
    pct = safe_float(pct)
    return "up" if pct > 0 else ("down" if pct < 0 else "flat")

def get_stock_code_and_name(user_input):
    target = user_input.strip()
    if target.isdigit():
        if target in twstock.codes: return target, twstock.codes[target].name
        return target, target
    for code, info in twstock.codes.items():
        if info.type == '股票' and (target == info.name or target in info.name): return code, info.name
    return None, None

def calculate_atr(df, period=14):
    df['TR'] = pd.concat([df['High'] - df['Low'], abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))], axis=1).max(axis=1)
    df['ATR'] = df['TR'].rolling(period).mean()
    return df

def calculate_three_lines_strategy(df):
    data = df.copy()

    # 1. 趨勢線 (Trend Line)：20 EMA 與 60 EMA
    data["ema_20"] = data["close"].ewm(span=20, adjust=False).mean()
    data["ema_60"] = data["close"].ewm(span=60, adjust=False).mean()
    data["trend_line"] = np.where(
        (data["ema_20"] > data["ema_60"]) & (data["close"] > data["ema_20"]), 1, -1
    )

    # 2. 籌碼線 (Chip Line)：10 日三大法人累積買賣超
    if "institutional_net_buy" not in data.columns:
        data["institutional_net_buy"] = data.get("volume", 1000) * 0.15

    data["chip_cum_10"] = data["institutional_net_buy"].rolling(window=10).sum()
    data["chip_ma_10"] = data["chip_cum_10"].rolling(window=10).mean()
    data["chip_line"] = np.where(
        (data["chip_cum_10"] > data["chip_ma_10"]) & (data["chip_cum_10"] > 0), 1, -1
    )

    # 3. 動能線 (Momentum Line)：RSI (14)
    delta = data["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data["rsi_14"] = 100 - (100 / (1 + rs))
    data["rsi_14"] = data["rsi_14"].fillna(50)
    data["momentum_line"] = np.where(data["rsi_14"] > 50, 1, -1)

    # 4. 三線共振綜合判斷
    data["total_score"] = (
        data["trend_line"] + data["chip_line"] + data["momentum_line"]
    )

    conditions = [
        data["total_score"] == 3,
        data["total_score"] == -3,
    ]
    choices = ["三線突破 (買進/強勢多頭)", "三線跌破 (賣出/強勢空頭)"]
    data["signal"] = np.select(conditions, choices, default="盤整/觀望")

    return data

def check_fundamental_6layer(code):
    fund_db = {
        "3624": {"eps": 1.8, "yoy": 35.2, "roe": 14.5, "pe": 20.5, "peg": 0.58, "catalyst": "車用與工業被動元件急單拉貨，10/07攻上漲停159.5元"},
        "2360": {"eps": 12.15, "yoy": 110.2, "roe": 28.5, "pe": 41.2, "peg": 0.75, "catalyst": "AI 2500W+ SLT水冷溫控/CPO光測試/HVDC高壓架構"},
        "8111": {"eps": 1.5, "yoy": 38.5, "roe": 13.2, "pe": 22.0, "peg": 0.60, "catalyst": "光電模組與半導體封測成長"},
        "4971": {"eps": 1.3, "yoy": 42.0, "roe": 11.5, "pe": 24.0, "peg": 0.57, "catalyst": "高頻磊晶片訂單升溫"},
        "4991": {"eps": 1.2, "yoy": 120.5, "roe": 15.2, "pe": 28.5, "peg": 0.55, "catalyst": "化合物半導體/CPO光通訊急單"},
        "4908": {"eps": 2.5, "yoy": 85.0, "roe": 18.2, "pe": 22.0, "peg": 0.48, "catalyst": "CPO光收發模組強勁拉貨"},
        "2330": {"eps": 9.5, "yoy": 32.5, "roe": 26.5, "pe": 24.5, "peg": 0.70, "catalyst": "CoWoS產能擴充/AI晶片需求"},
        "3374": {"eps": 3.2, "yoy": 45.0, "roe": 18.5, "pe": 28.0, "peg": 0.62, "catalyst": "台積電 CoWoS 封裝晶圓測試急單"},
        "1785": {"eps": 2.1, "yoy": 28.5, "roe": 16.0, "pe": 22.5, "peg": 0.65, "catalyst": "貴金屬回收與半導體靶材需求爆發"},
        "3081": {"eps": 4.5, "yoy": 65.0, "roe": 21.0, "pe": 35.0, "peg": 0.52, "catalyst": "矽光子 CPO 800G 光收發模組拉貨"},
        "3088": {"eps": 6.2, "yoy": 38.0, "roe": 19.5, "pe": 18.5, "peg": 0.58, "catalyst": "工業電腦與 AI 邊緣運算設備訂單爆滿"},
        "3219": {"eps": 3.8, "yoy": 52.0, "roe": 17.5, "pe": 24.0, "peg": 0.55, "catalyst": "半導體測試介面與探針卡需求強勁"},
        "3228": {"eps": 4.1, "yoy": 41.5, "roe": 16.2, "pe": 31.0, "peg": 0.60, "catalyst": "自研 AI 晶片架構與高效能運算授權"}
    }
    return fund_db.get(code, {"eps": 1.2, "yoy": 25.0, "roe": 12.0, "pe": 18.0, "peg": 0.70, "catalyst": "產業復甦成長"})

def stock_row_html(code, name, price, pct, tag="", prev_close=0.0):
    t = tone(pct)
    bar = "up-bar" if t == "up" else ("down-bar" if t == "down" else "")
    tag_html = '<span style="background:var(--panel2); padding:2px 8px; border-radius:12px; font-size:.75rem; color:var(--muted);">' + str(tag) + '</span>' if tag else ""
    close_info = '<span style="color:var(--gold); font-size:.8rem; margin-left:8px;">[最近日收盤: ' + f"{prev_close:.2f}" + ']</span>' if prev_close > 0 else ""
    return '<div class="row ' + bar + '"><div><span class="name">' + str(name) + '</span><span class="code">' + str(code) + '</span>' + close_info + '<br>' + tag_html + '</div><div class="px ' + t + '">' + f"{safe_float(price):.2f}" + '<small style="display:block; font-size:.8rem;">' + f"{safe_float(pct):+.2f}" + '%</small></div></div>'

def level_card_html(title, items, color_class):
    rows = "".join('<div class="it"><span class="muted">' + str(k) + '</span><b class="' + str(color_class) + '">' + f"{safe_float(v):.2f}" + '</b></div>' for k, v in items)
    return '<div class="lv"><h5 class="' + str(color_class) + '">' + str(title) + '</h5>' + rows + '</div>'

@st.cache_data(ttl=86400)
def get_all_taiwan_stock_codes():
    all_codes = []
    try:
        for code, info in twstock.codes.items():
            if info.type == '股票' and len(code) == 4 and code.isdigit():
                all_codes.append(code)
    except Exception:
        all_codes = ["2330", "2317", "2454", "3374", "1785", "3081", "3088", "3219", "3228", "2308", "2382", "3231", "2356", "6669", "3017", "2360", "3624", "8111", "4971", "4991", "4908"]
    return all_codes

def calculate_breakeven_price(trades_list, discount=0.2, tax_rate=0.003):
    if not trades_list: return 0.0, 0.0, 0.0, 0, 0.0
    total_shares = 0; total_buy_cost = 0.0; total_fee = 0.0; weighted_price_sum = 0.0
    for t in trades_list:
        p = safe_float(t.get("price", 0.0))
        q = int(safe_float(t.get("shares", safe_float(t.get("sheets", 0)) * 1000)))
        if p > 0 and q > 0:
            amt = p * q
            fee = math.floor(amt * 0.001425 * discount); fee = 20 if fee < 20 else fee
            total_shares += q; total_buy_cost += (amt + fee); total_fee += fee; weighted_price_sum += (p * q)
    if total_shares == 0: return 0.0, 0.0, 0.0, 0, 0.0
    avg_price = weighted_price_sum / total_shares
    factor = 1.0 - (0.001425 * discount) - tax_rate
    raw_breakeven = total_buy_cost / (total_shares * factor)
    def get_tick_size(price):
        if price < 10: return 0.01
        elif price < 50: return 0.05
        elif price < 100: return 0.1
        elif price < 500: return 0.5
        elif price < 1000: return 1.0
        else: return 5.0
    tick = get_tick_size(raw_breakeven)
    breakeven_price = math.ceil(raw_breakeven / tick) * tick
    return breakeven_price, total_buy_cost, total_fee, total_shares, avg_price

def calculate_pnl_and_roi(curr_price, trades_list, discount=0.2, tax_rate=0.003):
    breakeven_price, total_buy_cost, total_fee, total_shares, avg_price = calculate_breakeven_price(trades_list, discount, tax_rate)
    if curr_price <= 0 or total_buy_cost <= 0 or total_shares <= 0: return 0.0, 0.0
    sell_amt = curr_price * total_shares
    sell_fee = math.floor(sell_amt * 0.001425 * discount); sell_fee = 20 if sell_fee < 20 else sell_fee
    sell_tax = math.floor(sell_amt * tax_rate); net_sell = sell_amt - sell_fee - sell_tax
    pnl = net_sell - total_buy_cost; roi = (pnl / total_buy_cost) * 100.0 if total_buy_cost > 0 else 0.0
    return pnl, roi

# 讀取 Secrets
api_key = st.secrets.get("SHIOAJI_API_KEY", "")
secret_key = st.secrets.get("SHIOAJI_SECRET_KEY", "")
gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")
finmind_token = st.secrets.get("FINMIND_API_TOKEN", "")

st.sidebar.title("📌 全功能頁面選單")
app_mode = st.sidebar.radio("請選擇功能頁面", [
    "📐 張宇明三線多空戰略",
    "🔍 FinMind 全市場掃描器",
    "🚀 6層量化戰略選股",
    "💡 大戶投 — 智慧選股",
    "🔥 大戶投 — 盤中熱門",
    "⚡ 當沖強勢股篩選",
    "📈 三維定位與當沖盯盤系統",
    "📊 簡單台股記帳 (Stockify)"
])

if not api_key or not secret_key:
    st.sidebar.header("🔑 永豐金 API 設定")
    api_key = st.sidebar.text_input("API Key", type="password"); secret_key = st.sidebar.text_input("Secret Key", type="password")
else: st.sidebar.success("✅ 永豐金 API Key 已載入！")

if not gemini_api_key: gemini_api_key = st.sidebar.text_input("🔑 Gemini API Key (AI 評估用)", type="password")
if not finmind_token: finmind_token = st.sidebar.text_input("🔑 FinMind API Token (籌碼資料用)", type="password")
else: st.sidebar.success("✅ FinMind Token 已載入！")

st.sidebar.markdown("---")
if st.sidebar.button("🔄 一鍵重置 API 連線與清理 Session", use_container_width=True):
    if "shioaji_api_instance" in st.session_state and st.session_state["shioaji_api_instance"]:
        try: st.session_state["shioaji_api_instance"].logout()
        except Exception: pass
        st.session_state["shioaji_api_instance"] = None
    st.cache_resource.clear()
    st.sidebar.success("✅ 已主動發送 api.logout() 並清理 Session！")
    time.sleep(1); st.rerun()

# =========================================================
# 🛒 4. Shioaji API 全自動智慧下單與微秒級洗價引擎
# =========================================================
@st.cache_resource(ttl=3600, show_spinner=False)
def get_shioaji_api(k_key, s_key):
    if not k_key or not s_key: return None
    if "shioaji_api_instance" in st.session_state and st.session_state["shioaji_api_instance"]:
        try: return st.session_state["shioaji_api_instance"]
        except Exception: pass
    try:
        api = sj.Shioaji(simulation=True)
        accounts = api.login(api_key=k_key, secret_key=s_key)
        if accounts:
            st.session_state["shioaji_api_instance"] = api
            return api
    except Exception as e:
        err_str = str(e)
        if "451" in err_str or "Too Many Connections" in err_str:
            st.error("⚠️ 永豐金伺服器連線數過多 (Code 451)。請點擊左側『🔄 一鍵重置 API 連線』。")
        else: st.error("永豐金 API 登入失敗: " + err_str)
        return None

# 🛒 整合 SmartTrader 自動下單管理器
class SmartOrderManager:
    def __init__(self, api):
        self.api = api

    def place_buy_order(self, stock_code: str, price: float, sheets: int = 1):
        contract = self.api.Contracts.Stocks.get(stock_code)
        if not contract: return False, "找不到股票合約"
        order = self.api.Order(
            price=price,
            quantity=sheets,
            action=sj.constant.Action.Buy,
            price_type=sj.constant.StockPriceType.LMT,
            order_type=sj.constant.TFTOrderType.ROD,
            account=self.api.stock_account
        )
        try:
            trade = self.api.place_order(contract, order)
            return True, trade
        except Exception as e:
            return False, str(e)

    def place_emergency_sell_order(self, stock_code: str, sheets: int = 1, reason: str = ""):
        contract = self.api.Contracts.Stocks.get(