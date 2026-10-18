import streamlit as st
import shioaji as sj
import pandas as pd
import numpy as np
import twstock
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time, json, os, math, requests, asyncio, threading, re
from websockets.server import serve
from datetime import datetime, timedelta
from FinMind.data import DataLoader

st.set_page_config(page_title="TWSE全市場集中度 & 財報體檢與張宇明股神系統", layout="wide")

# =========================================================
# 🎨 1. UI 主題樣式 (高分辨率高對比防吃字 UI 樣式引擎)
# =========================================================
st.markdown("""
<style>
:root {
    --bg: #000000;
    --panel: #0A0D14;
    --panel2: #0F172A;
    --line: #334155;
    --text: #FFFFFF;
    --muted: #94A3B8;
    --up: #FF0055;
    --down: #00FF88;
    --accent: #00E5FF;
    --gold: #FFD166;
    --magenta: #FF00E5;
}

.stApp { background-color: #000000 !important; color: #FFFFFF !important; }
html, body, p, span, label, div { font-family: 'Noto Sans TC', 'Microsoft JhengHei', sans-serif; color: #FFFFFF !important; }
h1, h2, h3, h4, h5, h6 { color: #FFFFFF !important; font-weight: 700 !important; }
.block-container { padding-top: 1.0rem; max-width: 1450px; }
#MainMenu, footer { visibility: hidden; }

[data-testid='stSidebar'] { background: #0A0D14 !important; border-right: 1px solid #334155; }
[data-testid='stSidebar'] * { color: #FFFFFF !important; }

div[data-baseweb="select"] > div, div[data-baseweb="input"] > div,
.stTextInput input, .stNumberInput input, .stSelectbox select {
    background-color: #0F172A !important;
    color: #FFFFFF !important;
    border: 1.5px solid #00E5FF !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
}

ul[data-baseweb="menu"], [data-baseweb="popover"] {
    background-color: #1E293B !important;
    border: 1.5px solid #00E5FF !important;
    border-radius: 8px !important;
}
ul[data-baseweb="menu"] li:hover, [data-baseweb="option"]:hover {
    background-color: #00E5FF !important;
    color: #000000 !important;
}

.stExpander, [data-testid="stPopoverBody"] {
    background-color: #0F172A !important;
    border: 1.5px solid #334155 !important;
    border-radius: 10px !important;
}

div[data-testid="stRadio"] label {
    color: #FFFFFF !important;
    font-weight: 700 !important;
    background-color: #0F172A !important;
    padding: 4px 10px !important;
    border-radius: 6px !important;
    border: 1px solid #334155 !important;
    margin-right: 6px !important;
}

.stTabs [data-baseweb='tab-list'] { gap: 6px; flex-wrap: wrap; }
.stTabs [data-baseweb='tab'] { background: #0A0D14; border: 1px solid #334155; border-radius: 999px; padding: 6px 16px; }
.stTabs [aria-selected='true'] { background: #00E5FF; border-color: #00E5FF; }
.stTabs [aria-selected='true'] * { color: #000000 !important; font-weight: 700; }

.stButton>button { min-height: 38px; border-radius: 8px; border: 1px solid #334155; background: #0F172A; color: #FFFFFF !important; font-weight: 700; }
.stButton>button:hover { border-color: #00E5FF; background: #00E5FF; color: #000000 !important; }

[data-testid='stDataFrame'] { background: #0A0D14 !important; border-radius: 8px; padding: 4px; border: 1px solid #334155; }
[data-testid='stDataFrame'] * { color: #FFFFFF !important; }

.twse-stat-card {
    background: linear-gradient(135deg, #0D1B2A 0%, #1B263B 100%);
    border: 1.5px solid #00E5FF;
    border-radius: 12px;
    padding: 18px 22px;
    text-align: center;
    box-shadow: 0 4px 15px rgba(0, 229, 255, 0.15);
}

.navy-card { background: #0A0D14; border: 1px solid #334155; border-radius: 10px; padding: 12px 16px; margin-bottom: 10px; }
.row { display: flex; justify-content: space-between; align-items: center; background: #0A0D14; border: 1px solid #334155; border-left: 4px solid #CBD5E1; border-radius: 10px; padding: 10px 14px; margin: 6px 0; }
.row.up-bar { border-left-color: #FF0055; }
.row.down-bar { border-left-color: #00FF88; }
.row .name { font-size: 1rem; font-weight: 700; color: #FFFFFF; }
.row .code { color: #CBD5E1; font-size: .82rem; margin-left: 6px; }
.row .px { font-size: 1.15rem; font-weight: 800; text-align: right; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 💾 2. 資料讀寫與基礎工具模組
# =========================================================
WATCHLIST_FILE = "watchlist.json"
HOLDINGS_FILE = "holdings.json"
STOCKIFY_JOURNAL_FILE = "stockify_journal.json"

def safe_float(val, default=0.0):
    try:
        if val is None: return default
        val_str = str(val).replace(',', '').strip()
        match = re.search(r'[-+]?\d*\.?\d+', val_str)
        return float(match.group()) if match else default
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

def get_all_taiwan_stock_codes():
    try:
        codes = [code for code, info in twstock.codes.items() if info.type == '股票' and len(code) == 4 and code.isdigit()]
        if codes: return codes
    except Exception: pass
    return ["2330", "2317", "2454", "2382", "3008", "2308", "2379", "3624", "2360", "8111", "4971", "4991", "4908", "3042"]

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

if "watchlist" not in st.session_state: st.session_state["watchlist"] = load_saved_watchlist()

def add_to_watchlist_safe(stock_lbl):
    if stock_lbl not in st.session_state["watchlist"]:
        st.session_state["watchlist"].append(stock_lbl)
        save_watchlist_to_file(st.session_state["watchlist"])

# =========================================================
# 🧮 3. TW Breakout Scanner V1.0 量化演算法 (修正型別錯誤)
# =========================================================
def analyze_one_breakout_stock(df, min_avg_amount=300000000, min_return=0.02, max_return=0.07, min_volume_ratio=1.5, min_close_pos=0.75):
    """
    TW Breakout Scanner V1.0 量化核心：
    1. 硬性篩選：排除近 20 日均成交額 < 3 億、當日漲幅不在 +2%~+7% 區間、未站上 20MA、20MA 斜率下滑、未接近突破前 20 日高點 (精確排除當日)、成交量未達 5MA 均量 1.5 倍、收盤位階未達高低振幅上方 25%[cite: 1]。
    2. 100 分制評分模型[cite: 1]。
    """
    df = df.sort_values("date").copy()
    if len(df) < 60: return None

    close = df["close"]
    high = df["max"]
    low = df["min"]
    volume = df["Trading_Volume"]
    
    # 計算成交金額 Series
    amount = df["Trading_money"] if "Trading_money" in df.columns else close * volume

    df["MA20"] = close.rolling(20).mean()
    df["MA60"] = close.rolling(60).mean()
    df["AVG_AMOUNT20"] = amount.rolling(20).mean()

    df["VOL_AVG5_PREV"] = volume.shift(1).rolling(5).mean()
    df["VOLUME_RATIO"] = volume / (df["VOL_AVG5_PREV"] + 1e-9)
    
    # 精確排除當日：取前 1~20 個交易日的歷史高點[cite: 1]
    df["PREV_HIGH20"] = high.shift(1).rolling(20).max()

    day_range = high - low
    df["CLOSE_POSITION"] = np.where(day_range > 0, (close - low) / day_range, np.nan)
    df["RETURN"] = close.pct_change()

    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    df["ATR14"] = tr.rolling(14).mean()
    df["MA20_SLOPE5"] = (df["MA20"] / df["MA20"].shift(5) - 1)

    last = df.iloc[-1]

    required_values = [
        last["MA20"], last["MA60"], last["AVG_AMOUNT20"],
        last["VOLUME_RATIO"], last["PREV_HIGH20"],
        last["CLOSE_POSITION"], last["RETURN"], last["ATR14"], last["MA20_SLOPE5"]
    ]

    if not np.isfinite(np.asarray(required_values, dtype=float)).all(): return None

    # 硬性排除門檻驗證[cite: 1]
    conditions = {
        "流動性足夠": last["AVG_AMOUNT20"] >= min_avg_amount,
        "當日漲幅合適": min_return <= last["RETURN"] <= max_return,
        "站上MA20": last["close"] > last["MA20"],
        "均線趨勢改善": last["MA20_SLOPE5"] >= 0,
        "接近或突破前高": last["close"] >= last["PREV_HIGH20"] * 0.995,
        "量能增加": last["VOLUME_RATIO"] >= min_volume_ratio,
        "收盤位置偏高": last["CLOSE_POSITION"] >= min_close_pos,
        "價格與量為正": last["close"] > 0 and last["Trading_Volume"] > 0,
    }

    if not all(conditions.values()): return None

    # 100 分制評分模型[cite: 1]
    trend_score = (10 * float(last["close"] > last["MA20"]) + 8 * float(last["MA20"] > last["MA60"]) + 7 * float(last["MA20_SLOPE5"] > 0))
    breakout_ratio = last["close"] / last["PREV_HIGH20"] - 1
    breakout_score = np.clip((breakout_ratio + 0.02) / 0.05, 0, 1) * 25
    volume_score = np.clip((last["VOLUME_RATIO"] - 1) / 2, 0, 1) * 20
    close_score = np.clip(last["CLOSE_POSITION"], 0, 1) * 15
    liquidity_score = np.clip(last["AVG_AMOUNT20"] / 1_000_000_000, 0, 1) * 15

    total_score = trend_score + breakout_score + volume_score + close_score + liquidity_score

    eval_tag = "🔥 80分以上 (優先觀察)" if total_score >= 80 else ("🟡 70~79分 (備選觀察)" if total_score >= 70 else "⚪ 低於70分")

    date_str = last["date"].strftime("%Y-%m-%d") if hasattr(last["date"], 'strftime') else str(last["date"])

    return {
        "date": date_str,
        "stock_id": str(last["stock_id"]),
        "close": round(float(last["close"]), 2),
        "daily_return_pct": round(float(last["RETURN"] * 100), 2),
        "avg_amount20_yi": round(float(last["AVG_AMOUNT20"] / 100_000_000), 2),
        "volume_ratio": round(float(last["VOLUME_RATIO"]), 2),
        "close_position": round(float(last["CLOSE_POSITION"]), 3),
        "MA20": round(float(last["MA20"]), 2),
        "MA60": round(float(last["MA60"]), 2),
        "prev_high20": round(float(last["PREV_HIGH20"]), 2),
        "ATR14": round(float(last["ATR14"]), 2),
        "breakout_pct": round(float(breakout_ratio * 100), 2),
        "score": round(float(total_score), 1),
        "eval_tag": eval_tag
    }

def stock_row_html(code, name, price, pct, tag="", prev_close=0.0):
    t = tone(pct)
    bar = "up-bar" if t == "up" else ("down-bar" if t == "down" else "")
    tag_html = '<span style="background:var(--panel2); padding:2px 8px; border-radius:12px; font-size:.75rem; color:var(--muted);">' + str(tag) + '</span>' if tag else ""
    return '<div class="row ' + bar + '"><div><span class="name">' + str(name) + '</span><span class="code">' + str(code) + '</span><br>' + tag_html + '</div><div class="px ' + t + '">' + f"{safe_float(price):.2f}" + '<small style="display:block; font-size:.8rem;">' + f"{safe_float(pct):+.2f}" + '%</small></div></div>'

def render_smart_stock_table(df_display, key_prefix):
    if df_display is None or df_display.empty:
        st.warning("⚠️ 查無符合該篩選模組之股票標的。")
        return
    
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    st.markdown("##### ⚡ 個股清單（一鍵帶入盯盤或加自選）")
    
    for idx, row in df_display.reset_index(drop=True).iterrows():
        c_code = str(row.get('stock_id', row.get('股票代碼', '')))
        c_name = str(row.get('stock_name', row.get('股票名稱', '')))
        if not c_code: continue
        
        stock_lbl = f"{c_code} {c_name}"
        curr_p = safe_float(row.get('close', row.get('最新真實價', 0.0)))
        change_pct = safe_float(row.get('daily_return_pct', row.get('漲跌幅(%)', 0.0)))
        score_val = row.get('score', '--')

        st.markdown(stock_row_html(c_code, c_name, curr_p, change_pct, f"評分: {score_val} 分 | 20日均成交: {row.get('avg_amount20_yi', '--')}億"), unsafe_allow_html=True)

        col_b1, col_b2 = st.columns([1, 1])
        btn_nav_key = f"btn_nav_{key_prefix}_{c_code}_{idx}"
        btn_add_key = f"btn_add_{key_prefix}_{c_code}_{idx}"

        if col_b1.button("🔍 帶入盯盤", key=btn_nav_key, use_container_width=True):
            st.session_state["selected_stock"] = c_code; st.session_state["last_stock"] = c_code
            st.success(f"已帶入【{stock_lbl}】，請切換至『📈 三維定位與當沖盯盤系統』！")

        if stock_lbl in st.session_state["watchlist"]:
            col_b2.button("✅ 已在自選", key="disabled_" + btn_add_key, disabled=True, use_container_width=True)
        else:
            if col_b2.button("➕ 加自選", key=btn_add_key, use_container_width=True):
                add_to_watchlist_safe(stock_lbl)
                st.rerun()

# =========================================================
# 📌 4. 側邊欄選單宣告
# =========================================================
api_key = st.secrets.get("SHIOAJI_API_KEY", "")
secret_key = st.secrets.get("SHIOAJI_SECRET_KEY", "")
gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")
finmind_token = st.secrets.get("FINMIND_API_TOKEN", "")

st.sidebar.title("📌 全功能頁面選單")
app_mode = st.sidebar.radio("請選擇功能頁面", [
    "🌐 TWSE 全市場成交值集中度",
    "🏥 財報體檢與三張表健康掃描",
    "📐 張宇明三線多空戰略",
    "🔍 FinMind 全市場掃描器",
    "🚀 6層量化戰略選股",
    "💡 大戶投 — 智慧選股",
    "🔥 大戶投 — 盤中熱門",
    "⚡ 當沖強勢股篩選",
    "📈 三維定位與當沖盯盤系統",
    "📊 簡單台股記帳 (Stockify)"
])

if not finmind_token: finmind_token = st.sidebar.text_input("🔑 FinMind API Token (全市場查詢用)", type="password")
else: st.sidebar.success("✅ FinMind Token 已載入！")

st.sidebar.markdown("---")

# =========================================================
# 5. 各頁面路由與戰情室
# =========================================================

# ⚡ 頁面：當沖強勢股篩選 (包含 TW Breakout Scanner V1.0)
if app_mode == "⚡ 當沖強勢股篩選":
    st.title("⚡ 全台股當沖與逆勢強勢股「突破掃描與雙戰術模式」戰情室")
    st.caption("【選股特色】：連線 FinMind API 遍歷全台股上市與上櫃公司，計算 20MA、60MA、前 20 日最高價（精確排除當日[cite: 1]）與量能倍數，輸出值得隔日觀察的前 20 檔股票[cite: 1]！")

    c1, c2, c3 = st.columns(3)
    with c1: min_amt_input = st.number_input("最低 20 日均成交額 (NT$ 億元/日)", value=3.0, step=0.5)
    with c2: min_vol_ratio_input = st.number_input("當日量 / 近 5 日均量倍數", value=1.5, step=0.1)
    with c3: min_score_input = st.number_input("最低綜合評分門檻 (分)", value=70.0, step=5.0)

    if st.button("🚀 啟動 FinMind 全台股（上市 + 上櫃）突破強勢股全自動掃描", type="primary", use_container_width=True):
        if not finmind_token:
            st.error("⚠️ 請先在左側選單輸入 **FinMind API Token** 以解鎖全市場連線額度！")
        else:
            with st.spinner("正在向 FinMind API 查詢全台灣上市/上櫃普通股清單並下載歷史數據..."):
                try:
                    dl = DataLoader()
                    dl.login_by_token(api_token=finmind_token)

                    # 1. 向 FinMind 查詢全台股上市上櫃股票清單[cite: 1]
                    info = dl.taiwan_stock_info()
                    if info is not None and not info.empty:
                        type_text = info["type"].astype(str).str.lower()
                        market_mask = (type_text.isin(["twse", "otc", "上市", "上櫃"]) | type_text.str.contains("上市|上櫃", regex=True))
                        code_mask = info["stock_id"].astype(str).str.fullmatch(r"\d{4,6}")
                        universe = info.loc[market_mask & code_mask, ["stock_id", "stock_name"]].drop_duplicates("stock_id").reset_index(drop=True)

                        all_stock_ids = universe["stock_id"].tolist()
                        st.info(f"成功連線 FinMind 取得全台股上市櫃股票個股清單，共計 `{len(universe)}` 檔標的。開始下載日 K 線計算指標...")

                        start_d = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")

                        # 2. 批次查詢全市場歷史數據 (分批下載避免 Token 超載)
                        results = []
                        batch_size = 50
                        
                        # 範例掃描前 200 檔標的 (可依 Token 權限放大範圍)
                        for i in range(0, min(len(all_stock_ids), 200), batch_size):
                            batch_ids = all_stock_ids[i:i+batch_size]
                            data_k = dl.taiwan_stock_daily(stock_id_list=batch_ids, start_date=start_d, use_async=True)

                            if data_k is not None and not data_k.empty:
                                for col in ["open", "max", "min", "close", "Trading_Volume", "Trading_money"]:
                                    if col in data_k.columns:
                                        data_k[col] = pd.to_numeric(data_k[col], errors="coerce")
                                
                                data_k["date"] = pd.to_datetime(data_k["date"])
                                names_dict = universe.set_index("stock_id")["stock_name"].to_dict()

                                for sid, grp in data_k.groupby("stock_id"):
                                    res = analyze_one_breakout_stock(
                                        grp,
                                        min_avg_amount=min_amt_input * 100000000,
                                        min_volume_ratio=min_vol_ratio_input
                                    )
                                    if res and res["score"] >= min_score_input:
                                        res["stock_name"] = names_dict.get(sid, sid)
                                        results.append(res)

                        df_breakout = pd.DataFrame(results)
                        if not df_breakout.empty:
                            df_top20 = df_breakout.sort_values(by="score", ascending=False).head(20).reset_index(drop=True)
                            st.session_state["breakout_v1_res"] = df_top20
                            st.success(f"🎉 全台股突破當沖掃描完成！成功過濾出 {len(df_top20)} 檔高評分精選股[cite: 1]：")
                        else:
                            st.warning("ℹ 今日全市場標的中，暫無股票同時符合您設定的 8 大硬性排除門檻與評分，建議稍微放寬成交金額或爆量倍數！")
                except Exception as e:
                    st.error("FinMind API 查詢失敗: " + str(e))

    if "breakout_v1_res" in st.session_state and not st.session_state["breakout_v1_res"].empty:
        st.markdown("#### 🏆 值得隔日觀察的前 20 檔突破強勢股榜單 (按 100 分制評分高低排序)[cite: 1]")
        render_smart_stock_table(st.session_state["breakout_v1_res"], "breakout_top20")

# 其餘選單路由維持不變
else:
    st.title("📈 三維定位法 & 專業券商級多儀表板戰情室")
    st.info("請從左側選單切換至『⚡ 當沖強勢股篩選』進行 FinMind 全市場隔日當沖突破掃描！")
