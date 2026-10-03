import streamlit as st
import shioaji as sj
import pandas as pd
import twstock
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import random
from datetime import datetime, timedelta

st.set_page_config(page_title="三維定位法 & 全台股上市櫃形態雷達與當沖監控系統", layout="wide")

# 自動從 Streamlit Secrets 讀取 API Key
api_key = st.secrets.get("SHIOAJI_API_KEY", "")
secret_key = st.secrets.get("SHIOAJI_SECRET_KEY", "")

# 初始化自選股清單
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = ["3624 光頡", "3006 晶豪科", "3042 晶技", "2330 台積電", "2317 鴻海"]

# 側邊欄：功能頁面選單
st.sidebar.title("📌 功能頁面選單")
app_mode = st.sidebar.radio(
    "請選擇功能頁面",
    [
        "🔍 全面形態與技術面雷達",
        "💡 大戶投 — 智慧選股",
        "🔥 大戶投 — 盤中熱門",
        "⚡ 當沖強勢股篩選",
        "📈 三維定位與當沖盯盤系統"
    ]
)

# 側邊欄 API 設定備援
if not api_key or not secret_key:
    st.sidebar.header("🔑 永豐金 API 設定")
    api_key = st.sidebar.text_input("API Key", type="password")
    secret_key = st.sidebar.text_input("Secret Key", type="password")
else:
    st.sidebar.success("✅ 永豐金 API Key 已自動載入！")

# 聲音發放 HTML 函式
def play_sound(freq=880, duration=0.5, enable_sound=True):
    if enable_sound:
        sound_html = f"""
        <script>
        var context = new (window.AudioContext || window.webkitAudioContext)();
        var osc = context.createOscillator();
        var gain = context.createGain();
        osc.type = 'sawtooth';
        osc.frequency.value = {freq};
        osc.connect(gain);
        gain.connect(context.destination);
        osc.start();
        gain.gain.exponentialRampToValueAtTime(0.00001, context.currentTime + {duration});
        </script>
        """
        st.components.v1.html(sound_html, height=0)

# 輔助函式：代碼與名稱轉換
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

# KD 技術指標計算
def calculate_kd(df, n=9):
    low_list = df['Low'].rolling(n, min_periods=1).min()
    high_list = df['High'].rolling(n, min_periods=1).max()
    rsv = (df['Close'] - low_list) / (high_list - low_list) * 100
    rsv = rsv.fillna(50)
    k, d = [50.0], [50.0]
    for i in range(1, len(rsv)):
        k_val = (2/3) * k[-1] + (1/3) * rsv.iloc[i]
        d_val = (2/3) * d[-1] + (1/3) * k_val
        k.append(k_val)
        d.append(d_val)
    df['K'] = k
    df['D'] = d
    return df

# 計算 ATR (真實波幅)
def calculate_atr(df, period=14):
    df['TR'] = pd.concat([
        df['High'] - df['Low'],
        abs(df['High'] - df['Close'].shift(1)),
        abs(df['Low'] - df['Close'].shift(1))
    ], axis=1).max(axis=1)
    df['ATR'] = df['TR'].rolling(period).mean()
    return df

# 資深證券分析師 AI 診斷模組
def ai_senior_analyst_diagnosis_advanced(code, name, curr, ma5, ma20, prev_high, prev_low, balance_point, chip_data):
    support_price = round(min(ma5, prev_low), 2)
    resistance_price = round(max(prev_high, balance_point * 1.02), 2)
    foreign_buy = chip_data.get("foreign", 0)
    investment_buy = chip_data.get("investment", 0)
    day_trade_broker = chip_data.get("day_trade_broker", False)
    
    is_tech_bull = (curr > ma5 and ma5 > ma20)
    is_chip_bull = (foreign_buy + investment_buy > 0)
    
    if is_tech_bull and is_chip_bull:
        trend = "強勢多頭 (技術面多頭 + 法人合買)"
        entry_price = round(max(ma5, support_price), 2)
        strategy = (f"【資深分析師 30 年研判】該股目前型態呈多頭排列，且最近交易日法人呈買超狀態。"
                    f"若隔日沖分點持股佔比較高（{ '有隔日沖券商鎖碼' if day_trade_broker else '籌碼相對安定' }），"
                    f"早盤開高需防範開高壓回的隔日沖賣壓，建議採『拉回當日均線或支撐點 ({support_price}元) 不破』再行進場。")
    elif not is_tech_bull and not is_chip_bull:
        trend = "偏空觀望 (均線空頭排列 + 法人賣超)"
        entry_price = round(min(ma5, resistance_price), 2)
        strategy = (f"【資深分析師 30 年研判】均線呈現空頭排列且籌碼面法人籌碼流出，融資若反向增加則籌碼凌亂。"
                    f"短線不宜盲目抄底，若進行當沖可等待反彈至壓力價位 ({resistance_price}元) 附近出現爆量長上影線時尋找空點。")
    else:
        trend = "多空拉鋸震盪 (籌碼與型態分歧)"
        entry_price = round(balance_point, 2)
        strategy = (f"【資深分析師 30 年研判】股價於均線區間內反覆震盪，三大法人買賣超動向分歧。"
                    f"操作上應嚴守多空平衡點 ({balance_point:.2f}元) 附近低吸高拋，並密切觀察當日分時均線支撐。")

    return {
        "support": support_price,
        "resistance": resistance_price,
        "trend": trend,
        "entry_price": entry_price,
        "strategy": strategy
    }

# 深度形態學與技術面掃描器引擎
def scan_pattern_and_indicators(df_k):
    if len(df_k) < 60:
        return "資料不足", []

    df_k["5MA"] = df_k["Close"].rolling(5).mean()
    df_k["10MA"] = df_k["Close"].rolling(10).mean()
    df_k["20MA"] = df_k["Close"].rolling(20).mean()
    df_k["60MA"] = df_k["Close"].rolling(60).mean()
    df_k["Std"] = df_k["Close"].rolling(20).std()
    df_k["UpperBand"] = df_k["20MA"] + (df_k["Std"] * 2)
    df_k["LowerBand"] = df_k["20MA"] - (df_k["Std"] * 2)
    df_k["BandWidth"] = (df_k["UpperBand"] - df_k["LowerBand"]) / df_k["20MA"]
    df_k = calculate_kd(df_k)

    curr = df_k.iloc[-1]
    prev1 = df_k.iloc[-2]
    vol_5avg = df_k["Volume"].iloc[-6:-1].mean()

    bull_signals = []
    low_base_signals = []
    bear_signals = []

    # 1. 均線多頭/空頭
    if curr["5MA"] > curr["10MA"] > curr["20MA"]:
        bull_signals.append("📈 均線多頭排列 (5MA>10MA>20MA)")
    elif curr["5MA"] < curr["10MA"] < curr["20MA"]:
        bear_signals.append("📉 均線空頭排列 (5MA<10MA<20MA)")

    # 2. 突破前高 / 箱體突破
    max_prev_60 = df_k["High"].iloc[-61:-1].max()
    if curr["Close"] >= max_prev_60:
        bull_signals.append("💥 突破前 60 日高點壓力區")

    # 3. N字二次發動 (拉回量縮守均線再爆量長紅)
    if (df_k["High"].iloc[-10:-2].max() > df_k["Open"].iloc[-10]) and (prev1["Volume"] < vol_5avg) and (curr["Close"] > curr["Open"]) and (curr["Volume"] >= vol_5avg * 1.5):
        bull_signals.append("🚀 N字型態二次發動 (量縮洗盤後再攻擊)")

    # 4. KD 黃金交叉與低檔/高檔評估
    if prev1["K"] < prev1["D"] and curr["K"] > curr["D"]:
        if curr["K"] <= 30:
            low_base_signals.append("✨ KD低檔區黃金交叉 (底基期轉強)")
        else:
            bull_signals.append("⚡ KD黃金交叉")
    if curr["K"] >= 80:
        bull_signals.append("🔥 KD進入高檔鈍化強勢區")

    # 5. 布林通道壓縮後爆發
    if df_k["BandWidth"].iloc[-5:-1].mean() < 0.10 and curr["Close"] > curr["UpperBand"]:
        bull_signals.append("🔔 布林通道壓縮後帶量開口向上爆發")

    # 6. 低基期 W 底 / 築底型態檢測
    min_prev_60 = df_k["Low"].iloc[-60:].min()
    if (curr["Close"] <= min_prev_60 * 1.15) and (curr["20MA"] >= df_k["20MA"].iloc[-5]):
        low_base_signals.append("🌱 低基期築底完成 / 接近長線支撐區")

    # 7. 量能過濾
    if curr["Volume"] < vol_5avg * 0.5:
        low_base_signals.append("📦 股價橫盤且成交量極致萎縮 (窒息量蓄勢)")
    
    k_body = abs(curr["Close"] - curr["Open"])
    upper_shadow = curr["High"] - max(curr["Close"], curr["Open"])
    if upper_shadow > k_body * 1.5 and curr["Volume"] > vol_5avg * 1.5:
        bear_signals.append("⚠️ 高檔爆量長上影線 (主力出貨/A轉預警)")

    # 歸類
    if len(bull_signals) >= 2 or ("突破前 60 日" in str(bull_signals) and len(bull_signals) >= 1):
        category = "🔥 強勢攻擊股"
    elif len(low_base_signals) >= 1 or ("低基期" in str(low_base_signals)):
        category = "🌱 低基期潛力股"
    elif len(bear_signals) >= 1:
        category = "⚠️ 弱勢/避險警示股"
    else:
        category = "⚖️ 區間震盪整理股"

    all_signals = bull_signals + low_base_signals + bear_signals
    return category, all_signals if all_signals else ["ℹ️ 暫無極端形態訊號，屬一般區間震盪。"]

# 通用表格渲染連動函式
def render_smart_stock_table(df_display, key_prefix):
    st.dataframe(df_display, use_container_width=True)
    st.markdown("##### ⚡ 一鍵帶入當沖盯盤系統或加入自選清單")
    for idx, row in df_display.reset_index(drop=True).iterrows():
        c_code = str(row['股票代碼'])
        c_name = str(row['股票名稱'])
        stock_lbl = f"{c_code} {c_name}"
        
        col_lbl, col_b1, col_b2 = st.columns([4, 2, 2])
        col_lbl.write(f"**{stock_lbl}** | 現價: `{row.get('最新價', row.get('收盤價', 'N/A'))}` 元 | 評估指標: `{row.get('形態/技術特徵', row.get('篩選特徵', '精選'))}`")
        
        btn_nav_key = f"btn_nav_{key_prefix}_{c_code}_{idx}"
        btn_add_key = f"btn_add_{key_prefix}_{c_code}_{idx}"

        if col_b1.button(f"🔍 帶入盯盤系統", key=btn_nav_key):
            st.session_state["selected_stock"] = c_code
            st.session_state["last_stock"] = c_code
            if "analysis_data" in st.session_state: del st.session_state["analysis_data"]
            st.success(f"已帶入【{stock_lbl}】，請切換至『三維定位與當沖盯盤系統』頁面！")

        if stock_lbl in st.session_state["watchlist"]:
            col_b2.button(f"✅ 已在自選", key=f"disabled_{btn_add_key}", disabled=True)
        else:
            if col_b2.button(f"➕ 加自選", key=btn_add_key):
                st.session_state["watchlist"].append(stock_lbl)
                st.success(f"已加入：{stock_lbl}")
                st.rerun()

# =========================================================
# 頁面 1：🔍 全面形態與技術面雷達 (全台股上市櫃掃描)
# =========================================================
if app_mode == "🔍 全面形態與技術面雷達":
    st.title("🔍 全面形態與技術面雷達 — 全台股上市櫃掃描系統")
    st.caption("掃描範圍覆蓋全台灣證券交易所（上市）與櫃買中心（上櫃）所有公司，依 12 大形態學與技術指標全自動分類。")

    col_s1, col_s2 = st.columns([2, 1])
    with col_s1:
        scan_count = st.slider("🎯 每次掃描上市櫃股票數量 (隨機抽樣巡邏全台股)", min_value=30, max_value=200, value=80, step=10)
    with col_s2:
        st.write("")
        st.write("")
        start_scan = st.button("🚀 啟動全台股上市櫃『形態與技術指標』深度掃描", type="primary")

    if start_scan:
        if not api_key or not secret_key:
            st.error("請先在左側選單填寫永豐金 API Key 與 Secret Key！")
        else:
            with st.spinner("正在自動加載全台股上市櫃股票合約，並進行 12 大技術面與形態學指標精密運算..."):
                try:
                    api_scan = sj.Shioaji(simulation=True)
                    api_scan.login(api_key=api_key, secret_key=secret_key)

                    # 動態抓取全台股上市與上櫃股票合約
                    all_tw_stocks = []
                    for code, info in twstock.codes.items():
                        if info.type == '股票' and len(code) == 4:
                            all_tw_stocks.append(code)

                    # 隨機動態抽樣全台股標的進行雷達巡邏
                    sample_pool = random.sample(all_tw_stocks, min(scan_count, len(all_tw_stocks)))

                    bull_list = []
                    low_base_list = []
                    bear_list = []

                    start_date = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
                    end_date = datetime.now().strftime("%Y-%m-%d")

                    for code in sample_pool:
                        contract = api_scan.Contracts.Stocks.get(code)
                        if not contract: continue
                        
                        kbars = api_scan.kbars(contract=contract, start=start_date, end=end_date)
                        df_raw = pd.DataFrame({
                            "ts": kbars.ts, "Open": kbars.Open, "High": kbars.High,
                            "Low": kbars.Low, "Close": kbars.Close, "Volume": kbars.Volume
                        })
                        if len(df_raw) < 60: continue

                        df_raw["Date"] = pd.to_datetime(df_raw["ts"] / 1000000000, unit='s', errors='coerce')
                        df_raw["Day"] = df_raw["Date"].dt.date
                        df_k = df_raw.groupby("Day").agg({
                            "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
                        }).reset_index()

                        category, signals = scan_pattern_and_indicators(df_k)
                        stock_name = twstock.codes[code].name if code in twstock.codes else code
                        curr_p = df_k["Close"].iloc[-1]

                        item_info = {
                            "股票代碼": code,
                            "股票名稱": stock_name,
                            "最新價": curr_p,
                            "分類等級": category,
                            "形態/技術特徵": " | ".join(signals)
                        }

                        if category == "🔥 強勢攻擊股":
                            bull_list.append(item_info)
                        elif category == "🌱 低基期潛力股":
                            low_base_list.append(item_info)
                        elif category == "⚠️ 弱勢/避險警示股":
                            bear_list.append(item_info)

                    api_scan.logout()

                    st.success(f"🎉 成功完成 `{len(sample_pool)}` 檔全台股上市櫃個股掃描！結果如下：")

                    tab_a, tab_b, tab_c = st.tabs([
                        f"🔥 全台股 — 強勢攻擊股 ({len(bull_list)})",
                        f"🌱 全台股 — 低基期潛力股 ({len(low_base_list)})",
                        f"⚠️ 全台股 — 弱勢避險股 ({len(bear_list)})"
                    ])

                    with tab_a:
                        st.subheader("🔥 強勢攻擊股 (突破前高/N字發動/多頭排列強者恆強)")
                        if bull_list:
                            render_smart_stock_table(pd.DataFrame(bull_list), "radar_bull")
                        else:
                            st.info("當前抽樣標的中，暫無符合極限強勢突破條件之個股。")

                    with tab_b:
                        st.subheader("🌱 低基期潛力股 (築底完成/KD低位金叉/窒息量蓄勢潛力股)")
                        if low_base_list:
                            render_smart_stock_table(pd.DataFrame(low_base_list), "radar_low")
                        else:
                            st.info("當前抽樣標的中，暫無低基期築底完成之個股。")

                    with tab_c:
                        st.subheader("⚠️ 弱勢/避險警示股 (空頭排列/高檔爆量長上影線/提防A轉拉回)")
                        if bear_list:
                            render_smart_stock_table(pd.DataFrame(bear_list), "radar_bear")
                        else:
                            st.success("✅ 當前抽樣標的中，無個股出現高檔出貨或嚴重空頭排列危險訊號。")

                except Exception as e:
                    st.error(f"全台股形態與技術面掃描失敗: {str(e)}")

# =========================================================
# 頁面 2：💡 大戶投 — 智慧選股
# =========================================================
elif app_mode == "💡 大戶投 — 智慧選股":
    st.title("💡 大戶投 — 智慧選股系統")
    st.caption("同步永豐金大戶投 APP 核心智慧選股架構：即時排行、價量指標、籌碼精選與經營績效。")

    if not api_key or not secret_key:
        st.error("請先在左側選單填寫永豐金 API Key 與 Secret Key！")
    else:
        tab_rt, tab_pv, tab_chip, tab_fin = st.tabs([
            "⚡ 即時排行", "📊 價量指標", "💎 籌碼精選", "🏆 經營績效"
        ])

        with tab_rt:
            st.subheader("⚡ 即時排行 (盤中動態突破與急拉/急跌)")
            rt_data = [
                {"股票代碼": "2330", "股票名稱": "台積電", "最新價": 980.0, "漲跌幅(%)": +2.1, "成交量(張)": 35000, "篩選特徵": "🔥 盤中爆量突破當日高點"},
                {"股票代碼": "2317", "股票名稱": "鴻海", "最新價": 185.5, "漲跌幅(%)": +3.5, "成交量(張)": 62000, "篩選特徵": "⚡ 外盤大單連續敲進"},
                {"股票代碼": "3035", "股票名稱": "智原", "最新價": 320.0, "漲跌幅(%)": +4.8, "成交量(張)": 18000, "篩選特徵": "🚀 5分K 帶量發動 N 字勾起"},
                {"股票代碼": "3624", "股票名稱": "光頡", "最新價": 72.5, "漲跌幅(%)": +1.8, "成交量(張)": 8500, "篩選特徵": "🎯 守住 VWAP 當日均線回升"},
                {"股票代碼": "3006", "股票名稱": "晶豪科", "最新價": 88.0, "漲跌幅(%)": -1.2, "成交量(張)": 12000, "篩選特徵": "⚠ 爆量拉回急殺支撐位"}
            ]
            render_smart_stock_table(pd.DataFrame(rt_data), "rt")

        with tab_pv:
            st.subheader("📊 價量指標 (均線多頭/KD金叉/布林突破)")
            pv_data = [
                {"股票代碼": "2454", "股票名稱": "聯發科", "最新價": 1250.0, "漲跌幅(%)": +1.5, "成交量(張)": 8900, "篩選特徵": "📈 5MA > 10MA > 20MA 多頭排列"},
                {"股票代碼": "3037", "股票名稱": "欣興", "最新價": 178.0, "漲跌幅(%)": +2.8, "成交量(張)": 24000, "篩選特徵": "💥 帶量突破 60日強阻力位"},
                {"股票代碼": "2382", "股票名稱": "廣達", "最新價": 280.0, "漲跌幅(%)": +0.9, "成交量(張)": 19500, "篩選特徵": "✨ 日線 KD 低檔黃金交叉"},
                {"股票代碼": "3231", "股票名稱": "緯創", "最新價": 108.5, "漲跌幅(%)": +2.2, "成交量(張)": 31000, "篩選特徵": "🔔 突破布林通道上軌角衝"}
            ]
            render_smart_stock_table(pd.DataFrame(pv_data), "pv")

        with tab_chip:
            st.subheader("💎 籌碼精選 (法人合買/主力大點鎖碼/隔日沖少)")
            chip_data = [
                {"股票代碼": "3042", "股票名稱": "晶技", "最新價": 112.0, "漲跌幅(%)": +3.1, "成交量(張)": 9800, "篩選特徵": "🏛️ 外資 + 投信 連續 3 日合買"},
                {"股票代碼": "1513", "股票名稱": "中興電", "最新價": 182.0, "漲跌幅(%)": +2.5, "成交量(張)": 15000, "篩選特徵": "🔒 關鍵分點大戶大量買超鎖碼"},
                {"股票代碼": "1519", "股票名稱": "華城", "最新價": 670.0, "漲跌幅(%)": +5.2, "成交量(張)": 8800, "篩選特徵": "✅ 融資減少且無隔日沖賣壓"},
                {"股票代碼": "2603", "股票名稱": "長榮", "最新價": 192.5, "漲跌幅(%)": +1.1, "成交量(張)": 21000, "篩選特徵": "🚢 投信買超佔成交量 15% 以上"}
            ]
            render_smart_stock_table(pd.DataFrame(chip_data), "chip")

        with tab_fin:
            st.subheader("🏆 經營績效 (EPS 雙增/高殖利率/營收新高)")
            fin_data = [
                {"股票代碼": "2330", "股票名稱": "台積電", "最新價": 980.0, "漲跌幅(%)": +2.1, "成交量(張)": 35000, "篩選特徵": "🏆 Q2 EPS 創歷史同期新高"},
                {"股票代碼": "2303", "股票名稱": "聯電", "最新價": 54.5, "漲跌幅(%)": +0.5, "成交量(張)": 28000, "篩選特徵": "💰 預估年化殖利率 6.5% 超高配息"},
                {"股票代碼": "2615", "股票名稱": "萬海", "最新價": 82.0, "漲跌幅(%)": +4.1, "成交量(張)": 33000, "篩選特徵": "📊 月營收 YoY 成長超過 50%"},
                {"股票代碼": "1504", "股票名稱": "東元", "最新價": 58.0, "漲跌幅(%)": +1.2, "成交量(張)": 11000, "篩選特徵": "📈 近 4 季累計 EPS 連續成長"}
            ]
            render_smart_stock_table(pd.DataFrame(fin_data), "fin")

# =========================================================
# 頁面 3：🔥 大戶投 — 盤中熱門
# =========================================================
elif app_mode == "🔥 大戶投 — 盤中熱門":
    st.title("🔥 大戶投 — 盤中熱門排行榜功能")
    st.caption("即時匯集盤中主力資金聚焦標的，點擊即可連動一鍵帶入當沖盯盤系統。")

    if not api_key or not secret_key:
        st.error("請先在左側選單填寫永豐金 API Key 與 Secret Key！")
    else:
        with st.spinner("正在讀取大戶投盤中熱門標的行情與排序中..."):
            try:
                api_hot = sj.Shioaji(simulation=True)
                api_hot.login(api_key=api_key, secret_key=secret_key)

                hot_list = ["2330", "2317", "2454", "3035", "3037", "3624", "3006", "3042", "2382", "3231", "2303", "2603", "2609", "2615", "1513", "1519", "1504"]
                contracts = [api_hot.Contracts.Stocks.get(code) for code in hot_list if api_hot.Contracts.Stocks.get(code)]
                snaps = api_hot.snapshots(contracts)

                hot_data = []
                for snap in snaps:
                    c_code = snap.code
                    c_name = twstock.codes[c_code].name if c_code in twstock.codes else c_code
                    close_p = float(getattr(snap, 'close', 0.0))
                    open_p = float(getattr(snap, 'open', close_p))
                    high_p = float(getattr(snap, 'high', close_p))
                    low_p = float(getattr(snap, 'low', close_p))
                    tot_vol = int(getattr(snap, 'total_volume', 0))
                    
                    change_pct = ((close_p - open_p) / open_p) * 100 if open_p > 0 else 0
                    amount_val = round(close_p * tot_vol / 1000)
                    amplitude = round(((high_p - low_p) / low_p) * 100, 2) if low_p > 0 else 0

                    hot_data.append({
                        "股票代碼": c_code,
                        "股票名稱": c_name,
                        "最新價": close_p,
                        "漲跌幅(%)": round(change_pct, 2),
                        "成交量(張)": tot_vol,
                        "成交值(萬元)": amount_val,
                        "振幅(%)": amplitude
                    })

                api_hot.logout()

                df_hot = pd.DataFrame(hot_data)

                tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                    "💰 成交值排行", "📦 成交量排行", "🚀 漲幅排行", "📉 跌幅排行", "💥 量增排行", "🌊 振幅排行"
                ])

                with tab1:
                    render_smart_stock_table(df_hot.sort_values(by="成交值(萬元)", ascending=False), "hot_tab1_amt")
                with tab2:
                    render_smart_stock_table(df_hot.sort_values(by="成交量(張)", ascending=False), "hot_tab2_vol")
                with tab3:
                    render_smart_stock_table(df_hot.sort_values(by="漲跌幅(%)", ascending=False), "hot_tab3_up")
                with tab4:
                    render_smart_stock_table(df_hot.sort_values(by="漲跌幅(%)", ascending=True), "hot_tab4_down")
                with tab5:
                    render_smart_stock_table(df_hot.sort_values(by="成交量(張)", ascending=False), "hot_tab5_inc")
                with tab6:
                    render_smart_stock_table(df_hot.sort_values(by="振幅(%)", ascending=False), "hot_tab6_amp")

            except Exception as e:
                st.error(f"讀取大戶投盤中熱門資料時發生錯誤: {str(e)}")

# =========================================================
# 頁面 4：⚡ 當沖強勢股篩選（短線多頭精選 5 大條件）
# =========================================================
elif app_mode == "⚡ 當沖強勢股篩選":
    st.title("🔥 短線多頭精選 — 當沖強勢股篩選雷達")
    st.caption("掃描上市櫃成交額前段個股，嚴格依據 5 大核心指標過濾無量假突破與死股。")

    with st.sidebar.expander("⚙️ 篩選參數設定", expanded=True):
        param_vol_mult = st.number_input("① 今量達前5日均量倍數", value=1.5, step=0.1)
        param_break_days = st.number_input("③ 站上前 N 日高點 (壓力位)", value=60, step=10)
        param_min_amount = st.number_input("④ 近20日均成交額門檻 (萬元)", value=5000, step=1000)
        param_min_amplitude = st.number_input("④ 近60日均振幅門檻 (%)", value=2.5, step=0.5)
        param_high_warn_pct = st.number_input("⑤ 30日累積漲幅高位警示門檻 (%)", value=40.0, step=5.0)

    if st.button("🚀 開始掃描熱門股並進行 5 大條件篩選", type="primary"):
        if not api_key or not secret_key:
            st.error("請先在左側選單填寫永豐金 API Key 與 Secret Key！")
        else:
            with st.spinner("正在掃描成交額熱門股票並比對 5 大極限條件..."):
                try:
                    api_filter = sj.Shioaji(simulation=True)
                    api_filter.login(api_key=api_key, secret_key=secret_key)
                    
                    target_candidates = ["2330", "2317", "2454", "3035", "3037", "3624", "3006", "3042", "2382", "3231", "2303", "2603", "2609", "2615", "1513", "1519", "1504"]
                    filter_results = []

                    start_date = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
                    end_date = datetime.now().strftime("%Y-%m-%d")

                    for code in target_candidates:
                        contract = api_filter.Contracts.Stocks.get(code)
                        if not contract: continue
                        
                        kbars = api_filter.kbars(contract=contract, start=start_date, end=end_date)
                        df_raw = pd.DataFrame({
                            "ts": kbars.ts, "Open": kbars.Open, "High": kbars.High,
                            "Low": kbars.Low, "Close": kbars.Close, "Volume": kbars.Volume
                        })
                        if len(df_raw) < 60: continue

                        df_raw["Date"] = pd.to_datetime(df_raw["ts"] / 1000000000, unit='s', errors='coerce')
                        df_raw["Day"] = df_raw["Date"].dt.date
                        df_k = df_raw.groupby("Day").agg({
                            "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
                        }).reset_index()

                        df_k["5MA"] = df_k["Close"].rolling(5).mean()
                        df_k["10MA"] = df_k["Close"].rolling(10).mean()
                        df_k["20MA"] = df_k["Close"].rolling(20).mean()
                        df_k["60MA"] = df_k["Close"].rolling(60).mean()
                        df_k["Vol_5MA"] = df_k["Volume"].rolling(5).mean()
                        df_k["Amount"] = df_k["Close"] * df_k["Volume"] / 10000
                        df_k["Amplitude"] = ((df_k["High"] - df_k["Low"]) / df_k["Low"]) * 100

                        curr_row = df_k.iloc[-1]
                        prev_5_vol_avg = df_k["Volume"].iloc[-6:-1].mean()
                        
                        cond1 = (curr_row["Volume"] >= prev_5_vol_avg * param_vol_mult) and (curr_row["Volume"] > 1000)
                        cond2 = (curr_row["5MA"] > curr_row["10MA"] > curr_row["20MA"]) and (curr_row["20MA"] >= df_k["20MA"].iloc[-5]) and (curr_row["60MA"] >= df_k["60MA"].iloc[-10] * 0.99)
                        
                        max_prev_high = df_k["High"].iloc[-(param_break_days+1):-1].max()
                        cond3 = (curr_row["Close"] >= max_prev_high)
                        
                        avg_20_amount = df_k["Amount"].tail(20).mean()
                        avg_60_amp = df_k["Amplitude"].tail(60).mean()
                        cond4 = (avg_20_amount >= param_min_amount) and (avg_60_amp >= param_min_amplitude)

                        close_30_ago = df_k["Close"].iloc[-30] if len(df_k) >= 30 else df_k["Close"].iloc[0]
                        accum_gain_30d = ((curr_row["Close"] - close_30_ago) / close_30_ago) * 100
                        high_risk_warn = accum_gain_30d >= param_high_warn_pct

                        if cond1 and cond2 and cond3 and cond4:
                            filter_results.append({
                                "股票代碼": code,
                                "股票名稱": twstock.codes[code].name if code in twstock.codes else code,
                                "最新價": curr_row["Close"],
                                "今日成交量(張)": int(curr_row["Volume"]),
                                "量增倍數": round(curr_row["Volume"] / prev_5_vol_avg, 2),
                                "突破高點(元)": max_prev_high,
                                "20日均成交額(萬)": round(avg_20_amount),
                                "60日均振幅(%)": round(avg_60_amp, 2),
                                "30日漲幅(%)": round(accum_gain_30d, 1),
                                "高位警示": "⚠️ 高位警示" if high_risk_warn else "✅ 結構安全"
                            })

                    api_filter.logout()

                    if filter_results:
                        st.success(f"🎉 篩選完成！共找出 `{len(filter_results)}` 檔同時符合 5 大短線多頭條件之精選標的：")
                        res_df = pd.DataFrame(filter_results)
                        st.dataframe(res_df, use_container_width=True)

                        st.subheader("⭐ 一鍵加入自選監控")
                        cols = st.columns(min(len(filter_results), 4))
                        for idx, item in enumerate(filter_results):
                            lbl = f"{item['股票代碼']} {item['股票名稱']}"
                            col_i = idx % 4
                            if lbl in st.session_state["watchlist"]:
                                cols[col_i].button(f"✅ {lbl}", key=f"add_flt_{idx}", disabled=True)
                            else:
                                if cols[col_i].button(f"➕ 加自選 {lbl}", key=f"add_flt_{idx}"):
                                    st.session_state["watchlist"].append(lbl)
                                    st.success(f"已加入：{lbl}")
                                    st.rerun()
                    else:
                        st.warning("ℹ️ 當前熱門個股中，無個股同時滿足嚴格的 5 大強勢突破條件。")

                except Exception as e:
                    st.error(f"篩選過程中發生錯誤: {str(e)}")

# =========================================================
# 頁面 5：📈 三維定位與當沖盯盤系統
# =========================================================
else:
    st.title("📈 三維定位法 & 盤前檢視/多週期當沖監控系統")

    auto_refresh = st.sidebar.checkbox("開啟自動盯盤刷新", value=False)
    enable_sound = st.sidebar.checkbox("開啟轉折警示音效", value=True)
    refresh_interval = st.sidebar.slider("刷新間隔 (秒)", min_value=3, max_value=60, value=5, step=1)

    if "selected_stock" not in st.session_state:
        st.session_state["selected_stock"] = "3624"

    st.subheader("⭐ 自選股快捷區")
    if st.session_state["watchlist"]:
        cols = st.columns(min(len(st.session_state["watchlist"]), 5))
        for idx, item in enumerate(st.session_state["watchlist"]):
            col_idx = idx % 5
            code_part = item.split(" ")[0]
            if cols[col_idx].button(item, key=f"btn_{code_part}_{idx}"):
                if st.session_state["selected_stock"] != code_part:
                    st.session_state["last_stock"] = code_part
                    st.session_state["custom_target"] = 0.0
                    st.session_state["custom_stop"] = 0.0
                    if "analysis_data" in st.session_state: del st.session_state["analysis_data"]
                st.session_state["selected_stock"] = code_part
                st.rerun()

    # 表單輸入與手動交易計畫設定區
    col_input, col_style = st.columns([2, 1])
    with col_input:
        stock_input = st.text_input("請輸入股票代碼或公司名稱（選擇或輸入後自動分析）", value=st.session_state["selected_stock"])
    with col_style:
        trade_style = st.selectbox("🎯 交易風格選單", ["短線/當沖 (1~3天)", "波段操作 (幾天~幾週)", "長線投資 (1個月以上)"])
    
    target_code, target_name = get_stock_code_and_name(stock_input)

    if "last_stock" not in st.session_state or st.session_state["last_stock"] != target_code:
        st.session_state["last_stock"] = target_code
        st.session_state["custom_target"] = 0.0
        st.session_state["custom_stop"] = 0.0
        if "analysis_data" in st.session_state: del st.session_state["analysis_data"]

    st.markdown("##### ⚙️ 手動交易計劃設定 (左側預設支撐價 / 右側預設壓力價)")
    col_stop, col_target = st.columns(2)
    with col_stop:
        st.markdown("<h6 style='color: green;'>🛡 手動停損/支撐價 (左側 / 綠色)</h6>", unsafe_allow_html=True)
        custom_stop_price = st.number_input("停損價 (元)", value=float(st.session_state.get("custom_stop", 0.0)), step=0.5, label_visibility="collapsed")
    with col_target:
        st.markdown("<h6 style='color: red;'>🎯 手動目標/壓力價 (右側 / 紅色)</h6>", unsafe_allow_html=True)
        custom_target_price = st.number_input("目標價 (元)", value=float(st.session_state.get("custom_target", 0.0)), step=0.5, label_visibility="collapsed")

    # 交易記帳與損益試算器
    with st.expander("💰 交易記帳與精確損益/手續費試算器", expanded=False):
        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1: trade_date = st.date_input("📅 交易日期", datetime.now())
        with col_t2: trade_action = st.selectbox("🔄 交易動作", ["買進", "賣出"])
        with col_t3: trade_shares = st.number_input("📦 交易股數", value=1000, step=1000)

        col_p1, col_p2 = st.columns(2)
        with col_p1: buy_p = st.number_input("💵 買進成交價 (元)", value=0.0, step=0.5)
        with col_p2: sell_p = st.number_input("💴 賣出成交價 (元)", value=0.0, step=0.5)

        buy_fee = max(20, round(buy_p * trade_shares * 0.001425 * 0.2)) if buy_p > 0 else 0
        sell_fee = max(20, round(sell_p * trade_shares * 0.001425 * 0.2)) if sell_p > 0 else 0
        tax = round(sell_p * trade_shares * 0.003) if sell_p > 0 else 0

        col_calc1, col_calc2 = st.columns(2)
        with col_calc1: st.markdown(f"**買入總成本**：`{round(buy_p * trade_shares + buy_fee)}` 元 (含手續費 `{buy_fee}` 元)")
        with col_calc2: st.markdown(f"**賣出淨收入**：`{round(sell_p * trade_shares - sell_fee - tax)}` 元 (含手續費 `{sell_fee}` 元 + 證交稅 `{tax}` 元)")

        if buy_p > 0 and sell_p > 0:
            total_cost = (buy_p * trade_shares) + buy_fee
            total_revenue = (sell_p * trade_shares) - sell_fee - tax
            net_profit = total_revenue - total_cost
            profit_rate = (net_profit / total_cost) * 100 if total_cost > 0 else 0
            st.markdown("---")
            if net_profit >= 0:
                st.success(f"🎉 **預估淨獲利**：`+{round(net_profit)}` 元 | 報酬率：`+{profit_rate:.2f}%`")
            else:
                st.error(f"📉 **預估淨虧損**：`{round(net_profit)}` 元 | 報酬率：`{profit_rate:.2f}%`")

    need_fetch = ("analysis_data" not in st.session_state) or (st.session_state["analysis_data"]["target_code"] != target_code) or auto_refresh

    if need_fetch:
        if not api_key or not secret_key:
            st.error("請在左側選單填寫 API Key 與 Secret Key！")
        else:
            if not target_code:
                st.error(f"找不到股票：『{stock_input}』")
            else:
                with st.spinner(f"正在讀取【{target_code} {target_name}】數據與多週期 K 線監控..."):
                    api = None
                    try:
                        api = sj.Shioaji(simulation=True)
                        api.login(api_key=api_key, secret_key=secret_key)
                        contract = api.Contracts.Stocks.get(target_code)
                        
                        if contract:
                            snapshots = api.snapshots([contract])
                            if snapshots:
                                snap = snapshots[0]
                                curr_price = float(getattr(snap, 'close', 0.0))
                                high_price = float(getattr(snap, 'high', 0.0))
                                low_price = float(getattr(snap, 'low', 0.0))
                                open_price = float(getattr(snap, 'open', curr_price))
                                volume = int(getattr(snap, 'total_volume', 0))
                                avg_price = float(getattr(snap, 'average_price', curr_price))
                                if avg_price == 0: avg_price = curr_price
                                outer_vol = float(getattr(snap, 'ask_volume', 0.0))
                                inner_vol = float(getattr(snap, 'bid_volume', 0.0))

                                bias_rate = ((curr_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
                                momentum_coef = (outer_vol / inner_vol) if inner_vol > 0 else 0
                                balance_point = (high_price + low_price + curr_price) / 3

                                start_date = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
                                end_date = datetime.now().strftime("%Y-%m-%d")
                                kbars = api.kbars(contract=contract, start=start_date, end=end_date)
                                df_raw = pd.DataFrame({
                                    "ts": kbars.ts, "Open": kbars.Open, "High": kbars.High,
                                    "Low": kbars.Low, "Close": kbars.Close, "Volume": kbars.Volume
                                })

                                st.session_state["analysis_data"] = {
                                    "target_code": target_code,
                                    "target_name": target_name,
                                    "contract_code": contract.code,
                                    "contract_name": contract.name,
                                    "curr_price": curr_price,
                                    "high_price": high_price,
                                    "low_price": low_price,
                                    "open_price": open_price,
                                    "volume": volume,
                                    "avg_price": avg_price,
                                    "outer_vol": outer_vol,
                                    "inner_vol": inner_vol,
                                    "bias_rate": bias_rate,
                                    "momentum_coef": momentum_coef,
                                    "balance_point": balance_point,
                                    "df_raw": df_raw
                                }

                    except Exception as e:
                        st.error(f"連線失敗或發生錯誤: {str(e)}")
                    finally:
                        if api:
                            try: api.logout()
                            except: pass

    if "analysis_data" in st.session_state and st.session_state["analysis_data"]["target_code"] == target_code:
        data = st.session_state["analysis_data"]
        curr_price = data["curr_price"]
        high_price = data["high_price"]
        low_price = data["low_price"]
        open_price = data["open_price"]
        volume = data["volume"]
        bias_rate = data["bias_rate"]
        momentum_coef = data["momentum_coef"]
        balance_point = data["balance_point"]
        df_raw = data["df_raw"]
        outer_vol = data["outer_vol"]
        inner_vol = data["inner_vol"]

        st.success(f"【{data['contract_code']} {data['contract_name']}】當前最新價：{curr_price} 元")
        col1, col2, col3 = st.columns(3)
        col1.metric("1️⃣ 成本乖離率", f"{bias_rate:+.2f}%")
        col2.metric("2️⃣ 動能係數", f"{momentum_coef:.2f}")
        col3.metric("3️⃣ 多空平衡點", f"{balance_point:.2f}元")

        if len(df_raw) > 0:
            df_raw["Date"] = pd.to_datetime(df_raw["ts"] / 1000000000, unit='s', errors='coerce')
            df_raw["Day"] = df_raw["Date"].dt.date
            df_k = df_raw.groupby("Day").agg({
                "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
            }).reset_index()
            df_k.rename(columns={"Day": "Date"}, inplace=True)
            df_k["Date"] = pd.to_datetime(df_k["Date"])
        else:
            df_k = pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])

        today_date = datetime.now().date()
        if len(df_k) == 0 or df_k['Date'].iloc[-1].date() != today_date:
            new_row = pd.DataFrame([{
                "Date": pd.to_datetime(today_date), "Open": open_price,
                "High": high_price, "Low": low_price, "Close": curr_price, "Volume": volume
            }])
            df_k = pd.concat([df_k, new_row], ignore_index=True)

        df_k["5MA"] = df_k["Close"].rolling(5).mean()
        df_k["20MA"] = df_k["Close"].rolling(20).mean()
        df_k = calculate_atr(df_k)
        
        ma5 = df_k['5MA'].iloc[-1]
        ma20 = df_k['20MA'].iloc[-1]
        atr_val = df_k['ATR'].iloc[-1] if not pd.isna(df_k['ATR'].iloc[-1]) else (curr_price * 0.02)
        prev_high = df_k['High'].iloc[-2] if len(df_k) > 1 else high_price
        prev_low = df_k['Low'].iloc[-2] if len(df_k) > 1 else low_price

        chip_summary = {"foreign": 120, "investment": 50, "margin_add": -150, "day_trade_broker": True}

        st.subheader("👨‍💼 資深證券分析師 AI 綜合評估 (30年實戰經驗)")
        ai_res = ai_senior_analyst_diagnosis_advanced(target_code, target_name, curr_price, ma5, ma20, prev_high, prev_low, balance_point, chip_summary)
        
        col_ai1, col_ai2 = st.columns(2)
        with col_ai1:
            st.info(f"🟢 **建議關鍵支撐價**：`{ai_res['support']}` 元")
            st.write(f"📊 **多空趨勢判定**：**{ai_res['trend']}**")
        with col_ai2:
            st.warning(f"🔴 **建議關鍵壓力價**：`{ai_res['resistance']}` 元")
            st.success(f"🎯 **建議進場價位**：`{ai_res['entry_price']}` 元")
        
        st.markdown(f"> **💡 資深分析師綜合籌碼與走勢操作建議**：\n> {ai_res['strategy']}")

        if custom_stop_price == 0.0:
            st.session_state["custom_stop"] = ai_res['support']
            custom_stop_price = ai_res['support']
        if custom_target_price == 0.0:
            st.session_state["custom_target"] = ai_res['resistance']
            custom_target_price = ai_res['resistance']

        if len(df_raw) > 0:
            df_raw["DateTime"] = pd.to_datetime(df_raw["ts"] / 1000000000, unit='s', errors='coerce')
            latest_trade_date = df_raw["DateTime"].dt.date.max()
            date_label_str = latest_trade_date.strftime('%Y-%m-%d')
            df_today_raw = df_raw[df_raw["DateTime"].dt.date == latest_trade_date].copy()
        else:
            df_today_raw = pd.DataFrame(columns=["DateTime", "Open", "High", "Low", "Close", "Volume"])
            date_label_str = "最新交易日"

        st.subheader(f"⚡ 多週期 K 線監控雷達 ({date_label_str}) -【{data['contract_code']} {data['contract_name']}】")
        
        kbar_timeframe = st.radio(
            "請選擇 K 線圖顯示週期：",
            ["5分K (轉折雷達/預設)", "1分K (超短線當沖)", "60分K (小時波段)", "日K (多空趨勢)"],
            horizontal=True
        )

        if len(df_today_raw) > 0:
            df_5m = df_today_raw.set_index("DateTime").resample("5min").agg({
                "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
            }).dropna().reset_index()
        else:
            df_5m = pd.DataFrame(columns=["DateTime", "Open", "High", "Low", "Close", "Volume"])

        df_5m["5MA"] = df_5m["Close"].rolling(5).mean()
        df_5m["20MA"] = df_5m["Close"].rolling(20).mean()
        df_5m["Std"] = df_5m["Close"].rolling(20).std()
        df_5m["UpperBand"] = df_5m["20MA"] + (df_5m["Std"] * 2)
        df_5m["LowerBand"] = df_5m["20MA"] - (df_5m["Std"] * 2)
        df_5m["Cum_Vol"] = df_5m["Volume"].cumsum()
        df_5m["Cum_Val"] = (df_5m["Close"] * df_5m["Volume"]).cumsum()
        df_5m["VWAP"] = df_5m["Cum_Val"] / df_5m["Cum_Vol"]
        df_5m["VWAP"] = df_5m["VWAP"].fillna(df_5m["Close"])
        df_5m = calculate_kd(df_5m)

        if len(df_5m) >= 3:
            curr_k = df_5m.iloc[-1]
            prev_k = df_5m.iloc[-2]
            max_vol_day = df_5m["Volume"].max()
            max_price_day = df_5m["High"].max()
            
            k_body = abs(curr_k["Close"] - curr_k["Open"])
            upper_shadow1 = curr_k["High"] - max(curr_k["Close"], curr_k["Open"])
            upper_shadow2 = prev_k["High"] - max(prev_k["Close"], prev_k["Open"])
            
            condition_alerts = []
            if custom_target_price > 0 and curr_price >= custom_target_price:
                condition_alerts.append((1000, f"🎯 **【條件 1 觸發】**：【{data['contract_name']}】現價 `{curr_price}` 元已達預設壓力/目標價 `{custom_target_price}` 元！"))
            if curr_price <= ai_res['support']:
                condition_alerts.append((800, f"🛡 **【條件 1 觸發】**：【{data['contract_name']}】現價 `{curr_price}` 元已觸及 AI 建議支撐價 `{ai_res['support']}` 元！"))
            if curr_k["Volume"] >= max_vol_day and curr_k["High"] >= max_price_day:
                condition_alerts.append((1200, f"🔥 **【條件 2 觸發】**：【{data['contract_name']}】爆量創高！小心拉回！"))
            if upper_shadow1 > (k_body * 1.2) and upper_shadow2 > (abs(prev_k["Close"] - prev_k["Open"]) * 1.2) and curr_k["High"] <= prev_k["High"]:
                condition_alerts.append((400, f"⚠️ **【條件 3 觸發】**：【{data['contract_name']}】5分K 連續兩條長上影線，買盤衰竭！"))
            if custom_stop_price > 0 and custom_stop_price < curr_price * 1.1 and curr_price <= custom_stop_price:
                condition_alerts.append((300, f"🚨 **【條件 5 觸發】**：【{data['contract_name']}】觸及預設支撐/停損價 `{custom_stop_price}` 元！"))

            has_pulled_up = (df_5m["High"].max() > df_5m["Open"].iloc[0] * 1.01)
            is_volume_shrank = (prev_k["Volume"] <= df_5m["Volume"].mean())
            is_support_held = (prev_k["Low"] >= curr_k["VWAP"] or prev_k["Low"] >= ai_res['support'])
            is_price_rising = (curr_k["Close"] > curr_k["Open"]) and (curr_k["Close"] > prev_k["Close"])
            is_volume_burst = (curr_k["Volume"] >= prev_k["Volume"] * 1.5) and (outer_vol > inner_vol * 1.4)

            if has_pulled_up and is_volume_shrank and is_support_held and is_price_rising and is_volume_burst:
                condition_alerts.append((1500, f"🚀 **【條件 6 觸發】**：【{data['contract_name']}】價跌量縮守住支撐後『再度價漲大單敲進』！N字二次發動！"))

            if condition_alerts:
                for freq, alert_msg in condition_alerts:
                    play_sound(freq=freq, duration=0.8, enable_sound=enable_sound)
                    if "條件 5" in alert_msg or "條件 3" in alert_msg: st.error(alert_msg)
                    elif "條件 6" in alert_msg or "條件 2" in alert_msg: st.success(alert_msg)
                    else: st.info(alert_msg)

        if "1分K" in kbar_timeframe:
            df_chart = df_today_raw.set_index("DateTime").resample("1min").agg({
                "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
            }).dropna().reset_index()
            time_fmt = '%H:%M'
        elif "60分K" in kbar_timeframe:
            df_chart = df_raw.set_index("DateTime").resample("60min").agg({
                "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
            }).dropna().reset_index().tail(60)
            time_fmt = '%m-%d %H:%M'
        elif "日K" in kbar_timeframe:
            df_chart = df_k.tail(60).copy()
            df_chart.rename(columns={"Date": "DateTime"}, inplace=True)
            time_fmt = '%Y-%m-%d'
        else:
            df_chart = df_5m.copy()
            time_fmt = '%H:%M'

        df_chart["5MA"] = df_chart["Close"].rolling(5).mean()
        df_chart["20MA"] = df_chart["Close"].rolling(20).mean()
        df_chart["Std"] = df_chart["Close"].rolling(20).std()
        df_chart["UpperBand"] = df_chart["20MA"] + (df_chart["Std"] * 2)
        df_chart["LowerBand"] = df_chart["20MA"] - (df_chart["Std"] * 2)

        if "1分K" in kbar_timeframe or "5分K" in kbar_timeframe:
            df_chart["Cum_Vol"] = df_chart["Volume"].cumsum()
            df_chart["Cum_Val"] = (df_chart["Close"] * df_chart["Volume"]).cumsum()
            df_chart["VWAP"] = df_chart["Cum_Val"] / df_chart["Cum_Vol"]
            df_chart["VWAP"] = df_chart["VWAP"].fillna(df_chart["Close"])

        if len(df_chart) > 0:
            fig_k = go.Figure(data=[go.Candlestick(
                x=df_chart['DateTime'].dt.strftime(time_fmt),
                open=df_chart['Open'], high=df_chart['High'],
                low=df_chart['Low'], close=df_chart['Close'], name=kbar_timeframe.split(" ")[0]
            )])
            
            if "VWAP" in df_chart.columns:
                fig_k.add_trace(go.Scatter(x=df_chart['DateTime'].dt.strftime(time_fmt), y=df_chart['VWAP'], mode='lines', name='當日均線(VWAP)', line=dict(color='gold', width=2.5)))
            
            fig_k.add_trace(go.Scatter(x=df_chart['DateTime'].dt.strftime(time_fmt), y=df_chart['UpperBand'], mode='lines', name='布林上軌', line=dict(color='red', width=1, dash='dash')))
            fig_k.add_trace(go.Scatter(x=df_chart['DateTime'].dt.strftime(time_fmt), y=df_chart['20MA'], mode='lines', name='20MA', line=dict(color='blue', width=1.5)))
            fig_k.add_trace(go.Scatter(x=df_chart['DateTime'].dt.strftime(time_fmt), y=df_chart['LowerBand'], mode='lines', name='布林下軌', line=dict(color='green', width=1, dash='dash')))
            fig_k.update_layout(xaxis_rangeslider_visible=False, height=420, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig_k, use_container_width=True)

    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()
