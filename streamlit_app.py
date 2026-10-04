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
.block-container { padding-top:1.2rem; max-width:1400px; }
#MainMenu, footer { visibility:hidden; }

/* 側邊欄 */
[data-testid="stSidebar"] { background:var(--panel) !important; border-right:1px solid var(--line); }
[data-testid="stSidebar"] * { color: #F0F4F8 !important; }
[data-testid="stSidebar"] [role="radiogroup"] label { padding:8px 12px; border-radius:8px; margin-bottom:2px; width:100%; }
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background:var(--panel2); }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
  background:rgba(76,141,255,.2) !important; box-shadow:inset 3px 0 0 var(--accent);
}

/* 分頁：膠囊式 */
.stTabs [data-baseweb="tab-list"] { gap:6px; flex-wrap:wrap; }
.stTabs [data-baseweb="tab"] { background:var(--panel); border:1px solid var(--line); border-radius:999px; padding:6px 16px; height:auto; }
.stTabs [data-baseweb="tab"] * { color: #E6EBF3 !important; }
.stTabs [aria-selected="true"] { background:var(--accent); border-color:var(--accent); }
.stTabs [aria-selected="true"] * { color:#FFFFFF !important; font-weight:700; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display:none; }

/* 按鈕 */
.stButton>button { min-height:38px; border-radius:8px; border:1px solid var(--line); background:var(--panel2); color:#FFFFFF !important; font-weight:600; }
.stButton>button:hover { border-color:var(--accent); background:var(--accent); color:#fff !important; }
.stButton>button[kind="primary"] { background:var(--accent); border-color:var(--accent); color:#fff !important; }

/* 輸入框 */
input, [data-baseweb="select"] > div { background:var(--panel2) !important; color:#FFFFFF !important; border-radius:8px !important; }

/* 台股色彩與清晰標籤 */
.up, .text-red { color:var(--up) !important; font-weight:700; }
.down, .text-green { color:var(--down) !important; font-weight:700; }
.muted { color:#D1D8E0 !important; font-size:.9rem; font-weight:500; }

/* 通用卡片 */
.navy-card { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:12px 16px; margin-bottom:10px; }

/* 價位卡（停損/停利） */
.lv { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:12px 16px; height:100%; }
.lv h5 { margin:0 0 8px; font-size:.95rem; }
.lv .it { display:flex; justify-content:space-between; padding:5px 0; border-bottom:1px dashed var(--line); }
.lv .it:last-child { border-bottom:0; }

/* 專業右側關鍵價位看板（黃框樣式） */
.level-container { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px; }
.level-head { display:flex; justify-content:space-between; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid var(--line); }
.level-box {
  background:var(--panel2); border:1.5px solid var(--gold); border-radius:8px;
  padding:8px 12px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;
}
.level-box.normal { border-color:var(--line); }
.level-box .lbl { font-size:.9rem; color:#FFFFFF !important; font-weight:600; }
.level-box .val { font-size:1.15rem; font-weight:800; }

/* 個股列 */
.row { display:flex; justify-content:space-between; align-items:center; background:var(--panel);
  border:1px solid var(--line); border-left:4px solid var(--muted); border-radius:10px; padding:10px 14px; margin:6px 0; }
.row.up-bar { border-left-color:var(--up); } .row.down-bar { border-left-color:var(--down); }
.row .name { font-size:1rem; font-weight:700; color:#FFFFFF; }
.row .code { color:var(--muted); font-size:.82rem; margin-left:6px; }
.row .px { font-size:1.15rem; font-weight:800; text-align:right; }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)


def safe_float(val, default=0.0):
    try:
        if val is None:
            return default
        return float(val)
    except (ValueError, TypeError):
        return default


def tone(pct):
    pct = safe_float(pct)
    return "up" if pct > 0 else ("down" if pct < 0 else "flat")


def stock_row_html(code, name, price, pct, tag="", prev_close=0.0):
    t = tone(pct)
    bar = {"up": "up-bar", "down": "down-bar"}.get(t, "")
    tag_html = f'<span style="background:var(--panel2); padding:2px 8px; border-radius:12px; font-size:.75rem; color:var(--muted);">{tag}</span>' if tag else ""
    close_info = f'<span style="color:var(--gold); font-size:.8rem; margin-left:8px;">[最近日收盤: {prev_close:.2f}]</span>' if prev_close > 0 else ""
    return (
        f'<div class="row {bar}"><div>'
        f'<span class="name">{name}</span><span class="code">{code}</span>{close_info}<br>{tag_html}</div>'
        f'<div class="px {t}">{safe_float(price):.2f}<small style="display:block; font-size:.8rem;">{safe_float(pct):+.2f}%</small></div></div>'
    )


def level_card_html(title, items, color_class):
    rows = "".join(
        f'<div class="it"><span class="muted">{k}</span><b class="{color_class}">{safe_float(v):.2f}</b></div>'
        for k, v in items
    )
    return f'<div class="lv"><h5 class="{color_class}">{title}</h5>{rows}</div>'


# 🧮 計算買進總成本與損益兩平價（含 2 折手續費與 0.3% 證交稅）
def calculate_breakeven_price(buy_price, qty_sheets=1, discount=0.2, tax_rate=0.003):
    if buy_price <= 0 or qty_sheets <= 0:
        return 0.0, 0.0, 0.0
    
    shares = qty_sheets * 1000
    buy_amt = buy_price * shares
    buy_fee = math.floor(buy_amt * 0.001425 * discount)
    if buy_fee < 20: buy_fee = 20
    total_buy_cost = buy_amt + buy_fee

    factor = 1.0 - (0.001425 * discount) - tax_rate
    raw_breakeven = total_buy_cost / (shares * factor)

    def get_tick_size(price):
        if price < 10: return 0.01
        elif price < 50: return 0.05
        elif price < 100: return 0.1
        elif price < 500: return 0.5
        elif price < 1000: return 1.0
        else: return 5.0

    tick = get_tick_size(raw_breakeven)
    breakeven_price = math.ceil(raw_breakeven / tick) * tick

    return breakeven_price, total_buy_cost, buy_fee


# 🧮 計算給定現價下的未實現損益與報酬率
def calculate_pnl_and_roi(curr_price, buy_price, qty_sheets=1, discount=0.2, tax_rate=0.003):
    if curr_price <= 0 or buy_price <= 0 or qty_sheets <= 0:
        return 0.0, 0.0
    shares = qty_sheets * 1000
    buy_amt = buy_price * shares
    buy_fee = math.floor(buy_amt * 0.001425 * discount)
    if buy_fee < 20: buy_fee = 20
    total_buy_cost = buy_amt + buy_fee

    sell_amt = curr_price * shares
    sell_fee = math.floor(sell_amt * 0.001425 * discount)
    if sell_fee < 20: sell_fee = 20
    sell_tax = math.floor(sell_amt * tax_rate)
    net_sell = sell_amt - sell_fee - sell_tax

    pnl = net_sell - total_buy_cost
    roi = (pnl / total_buy_cost) * 100.0 if total_buy_cost > 0 else 0.0
    return pnl, roi


# 💾 1. 自選股 JSON 永久儲存與讀取
WATCHLIST_FILE = "watchlist.json"

def load_saved_watchlist():
    default_list = ["8111 立碁", "4971 IET-KY", "3624 光頡", "4991 環宇-KY", "4908 前鼎", "2330 台積電"]
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception:
            pass
    return default_list

def save_watchlist_to_file(watchlist):
    try:
        with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(watchlist, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"寫入自選股設定檔失敗: {str(e)}")


# 💾 2. 個人持股成本 (買進價 & 張數 & 停損目標價) 永久 JSON 儲存與讀取
HOLDINGS_FILE = "holdings.json"

def load_saved_holdings():
    if os.path.exists(HOLDINGS_FILE):
        try:
            with open(HOLDINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}

def save_stock_holding(code, buy_cost, buy_sheets, custom_stop, custom_target):
    holdings = load_saved_holdings()
    holdings[str(code)] = {
        "buy_cost": float(buy_cost),
        "buy_sheets": int(buy_sheets),
        "custom_stop": float(custom_stop),
        "custom_target": float(custom_target)
    }
    try:
        with open(HOLDINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(holdings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"儲存持股成本失敗: {str(e)}")


# 初始化資料結構
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = load_saved_watchlist()

if "holdings" not in st.session_state:
    st.session_state["holdings"] = load_saved_holdings()

# Secrets 讀取 API Keys
api_key = st.secrets.get("SHIOAJI_API_KEY", "")
secret_key = st.secrets.get("SHIOAJI_SECRET_KEY", "")
gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")
finmind_token = st.secrets.get("FINMIND_API_TOKEN", "")

# 側邊欄選單
st.sidebar.title("📌 全功能頁面選單")
app_mode = st.sidebar.radio(
    "請選擇功能頁面",
    [
        "🔍 FinMind 全市場掃描器",
        "🚀 6層量化戰略選股",
        "💡 大戶投 — 智慧選股",
        "🔥 大戶投 — 盤中熱門",
        "⚡ 當沖強勢股篩選",
        "📈 三維定位與當沖盯盤系統"
    ]
)

if not api_key or not secret_key:
    st.sidebar.header("🔑 永豐金 API 設定")
    api_key = st.sidebar.text_input("API Key", type="password")
    secret_key = st.sidebar.text_input("Secret Key", type="password")
else:
    st.sidebar.success("✅ 永豐金 API Key 已自動載入！")

if not gemini_api_key:
    gemini_api_key = st.sidebar.text_input("🔑 Gemini API Key (AI 評估用)", type="password")

if not finmind_token:
    finmind_token = st.sidebar.text_input("🔑 FinMind API Token (籌碼資料用)", type="password")
else:
    st.sidebar.success("✅ FinMind Token 已自動載入！")


# =========================================================
# 🔒 終極防護：Shioaji API Session 全域複用，徹底避免 Code 451 錯誤
# =========================================================
@st.cache_resource(ttl=3600, show_spinner=False)
def get_shioaji_api(k_key, s_key):
    if not k_key or not s_key:
        return None
    
    if "shioaji_api_instance" in st.session_state and st.session_state["shioaji_api_instance"]:
        try:
            return st.session_state["shioaji_api_instance"]
        except Exception:
            pass

    try:
        api = sj.Shioaji(simulation=True)
        accounts = api.login(api_key=k_key, secret_key=s_key)
        if accounts:
            st.session_state["shioaji_api_instance"] = api
            return api
    except Exception as e:
        err_str = str(e)
        if "451" in err_str or "Too Many Connections" in err_str:
            st.error("⚠️ 永豐金伺服器顯示連線數過多 (Code 451)。請關閉多餘分頁並靜置網頁 3~5 分鐘，等待伺服器自動釋放舊連線。")
        else:
            st.error(f"永豐金 API 登入失敗: {err_str}")
        return None


# 🌐 精準抓取「最近一個交易日真實收盤價」核心邏輯（含假日與非交易時間自動修復）
def get_latest_trade_close(api, contract, snapshot=None):
    try:
        if snapshot:
            close_p = safe_float(getattr(snapshot, 'close', 0.0))
            ref_p = safe_float(getattr(snapshot, 'reference_price', getattr(snapshot, 'yesterday_close', 0.0)))
            if close_p > 0:
                return close_p
            elif ref_p > 0:
                return ref_p

        start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        kbars = api.kbars(contract=contract, start=start_date, end=end_date)
        if kbars and len(kbars.Close) > 0:
            return safe_float(kbars.Close[-1])
    except Exception:
        pass
    return 0.0


# 🌐 通用函式：傳入股票代碼清單，透過 API 抓取最新真實撮合價與最近一日真實收盤價
def fetch_real_stock_snapshots(codes_list, tag_feature="精選"):
    api = get_shioaji_api(api_key, secret_key)
    if not api:
        return pd.DataFrame()
    try:
        contracts = [api.Contracts.Stocks.get(code) for code in codes_list if api.Contracts.Stocks.get(code)]
        if not contracts:
            return pd.DataFrame()
        snaps = api.snapshots(contracts)
        snap_dict = {s.code: s for s in snaps}

        results = []
        for contract in contracts:
            c_code = contract.code
            c_name = twstock.codes[c_code].name if c_code in twstock.codes else c_code
            s = snap_dict.get(c_code)
            
            real_close_p = get_latest_trade_close(api, contract, s)
            curr_p = safe_float(getattr(s, 'close', real_close_p), real_close_p)
            open_p = safe_float(getattr(s, 'open', real_close_p), real_close_p)
            tot_vol = int(safe_float(getattr(s, 'total_volume', 0))) if s else 0
            pct = round(((curr_p - open_p) / open_p) * 100, 2) if open_p > 0 else 0.0

            results.append({
                "股票代碼": c_code,
                "股票名稱": c_name,
                "最新真實價": curr_p,
                "最近日收盤價": real_close_p,
                "最新價": curr_p,
                "漲跌幅(%)": pct,
                "成交量(張)": tot_vol,
                "成交值(萬元)": round(curr_p * tot_vol / 1000),
                "篩選特徵": tag_feature,
                "狀態": "即時行情"
            })
        return pd.DataFrame(results)
    except Exception:
        return pd.DataFrame()


# =========================================================
# ⚡ 真正微秒級/毫秒級 WebSocket 推播廣播引擎
# =========================================================
CONNECTED_CLIENTS = set()

async def ws_handler(websocket):
    CONNECTED_CLIENTS.add(websocket)
    try:
        async for message in websocket:
            pass
    except Exception:
        pass
    finally:
        CONNECTED_CLIENTS.remove(websocket)

def start_websocket_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    async def run_server():
        async with serve(ws_handler, "0.0.0.0", 8765):
            await asyncio.Future()
    try:
        loop.run_until_complete(run_server())
    except Exception:
        pass

if "ws_thread_started" not in st.session_state:
    st.session_state["ws_thread_started"] = True
    t = threading.Thread(target=start_websocket_server, daemon=True)
    t.start()

def broadcast_tick_microsecond(tick_data):
    if CONNECTED_CLIENTS:
        msg = json.dumps(tick_data)
        async def _send():
            for ws in list(CONNECTED_CLIENTS):
                try:
                    await ws.send(msg)
                except Exception:
                    pass
        asyncio.run(_send())


# 🌐 FinMind API：真實抓取近 5 日三大法人買賣超數據
@st.cache_data(ttl=3600)
def fetch_finmind_chip_data(stock_code, token=""):
    start_date = (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d")
    url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInstitutionalInvestorsBuySell&data_id={stock_code}&start_date={start_date}"
    if token:
        url += f"&token={token}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            raw_data = res.json().get("data", [])
            if raw_data:
                df = pd.DataFrame(raw_data)
                df["net_vol"] = (df["buy"] - df["sell"]) / 1000
                name_map = {
                    "Foreign_Investor": "外資",
                    "Investment_Trust": "投信",
                    "Dealer_Self": "自營商",
                    "Dealer_Hedging": "自營商避險"
                }
                df["name_clean"] = df["name"].map(lambda x: name_map.get(x, x))
                pivot_df = df.pivot_table(index="date", columns="name_clean", values="net_vol", aggfunc="sum").fillna(0)
                
                if "自營商避險" in pivot_df.columns:
                    pivot_df["自營商"] = pivot_df.get("自營商", 0) + pivot_df["自營商避險"]
                
                for col in ["外資", "投信", "自營商"]:
                    if col not in pivot_df.columns:
                        pivot_df[col] = 0.0

                pivot_df["合計"] = pivot_df["外資"] + pivot_df["投信"] + pivot_df["自營商"]
                pivot_df = pivot_df.sort_index(ascending=False).head(5).reset_index()
                
                pivot_df["日期"] = pd.to_datetime(pivot_df["date"]).dt.strftime("%m/%d")
                for col in ["外資", "投信", "自營商", "合計"]:
                    pivot_df[col] = pivot_df[col].apply(lambda x: f"{x:+.0f}" if x != 0 else "0")
                
                return pivot_df[["日期", "外資", "投信", "自營商", "合計"]]
    except Exception:
        pass
    return pd.DataFrame()


def get_stock_code_and_name(user_input):
    target = user_input.strip()
    if target.isdigit():
        if target in twstock.codes:
            return target, twstock.codes[target].name
        return target, target
    for code, info in twstock.codes.items():
        if info.type == '股票' and (target == info.name or target in info.name):
            return code, info.name
    return None, None

def calculate_atr(df, period=14):
    df['TR'] = pd.concat([
        df['High'] - df['Low'],
        abs(df['High'] - df['Close'].shift(1)),
        abs(df['Low'] - df['Close'].shift(1))
    ], axis=1).max(axis=1)
    df['ATR'] = df['TR'].rolling(period).mean()
    return df

# 🤖 升級版：高盛機構級全方位 AI 診斷引擎 (修復 SyntaxError)
def run_goldman_sachs_ai_evaluation(data_dict, user_gemini_key=""):
    c_code = str(data_dict.get('股票代碼', data_dict.get('target_code', '')))
    c_name = str(data_dict.get('股票名稱', data_dict.get('target_name', '')))
    price = safe_float(data_dict.get('最新真實價', data_dict.get('curr_price', 0.0)))
    pct = safe_float(data_dict.get('漲跌幅(%)', 0.0))
    eps = data_dict.get('季EPS', '--')
    yoy = data_dict.get('營收YoY', '--')
    roe = data_dict.get('ROE', '--')
    peg = data_dict.get('PEG', '--')
    catalyst = data_dict.get('催化劑', '產業復甦/AI檢測需求')
    status = data_dict.get('狀態', '盤中監控')

    key_to_use = user_gemini_key.strip() if user_gemini_key else gemini_api_key.strip()

    if not key_to_use:
        return "⚠️ 請先在左側選單輸入 **Gemini API Key**，以啟動 AI 實時診斷！"

    prompt = f"""
你是高盛（Goldman Sachs）亞太區台股首席策略分析師。請針對台股標的【{c_code} {c_name}】進行深度、實質且具備機構風控視角的投資評估報告。

【即時市場與基本面數據】
* 股票代碼與名稱：{c_code} {c_name}
* 最新成交價：{price} 元 (今日漲跌幅: {pct:+.2f}%)
* 基本面數據：季 EPS {eps} 元 | 營收 YoY {yoy} | ROE {roe} | PEG 估值 {peg}
* 產業催化劑/狀態：{catalyst} ({status})

【請嚴格依據下列 4 大維度輸出詳盡專業報告，切勿使用公版套話】：

1. **🏢 產業趨勢與基本面實質檢視**：
   * 分析該公司於產業鏈（如 AI 伺服器、CPO 光通訊、半導體檢測、車用等）的核心競爭力與長線紅利。
   * 檢視營收成長（YoY {yoy}）是否能實質轉化為毛利率與 EPS 獲利跳升。

2. **🎯 投資人類型建議與分戰略操作策略**：
   * **空手 / 打算新建倉者**：給出明確的進場條件（例如等待拉回關鍵均線、本益比合理的甜甜價區間），切勿盲目追高。
   * **已有低價持股者**：提供續抱策略與移動停利點設定指引（如沿月線/季線移動防守）。

3. **📊 買進勝率與勝率結構剖析**：
   * 給出具體的短線/波段勝率預估（例如 72%）。
   * 詳細拆解勝率支撐理由（如法人籌碼鎖碼、技術面多頭排列、產業催化劑）與下檔限制。

4. **⚠️ 風險提示與精確停損位**：
   * 列出當前最大的風險因子（如估值過高、大盤回檔風險、法人調節賣壓等）。
   * 給出精確的**停損參考價格與紀律觸發條件**。
"""

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": prompt}]
        }]
    }

    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key_to_use}"
    available_endpoints = []
    try:
        res_list = requests.get(list_url, timeout=5)
        if res_list.status_code == 200:
            models_data = res_list.json().get("models", [])
            for m in models_data:
                m_name = m.get("name", "")
                methods = m.get("su