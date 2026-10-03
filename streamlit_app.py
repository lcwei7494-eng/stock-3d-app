import streamlit as st
import shioaji as sj
import pandas as pd
import twstock
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

st.set_page_config(page_title="三維定位法與盤前掃描/5分K當沖雷達", layout="centered")

st.title("📈 三維定位法 & 盤前檢視/5分K當沖監控系統")

# 自動從 Streamlit Secrets 讀取 API Key
api_key = st.secrets.get("SHIOAJI_API_KEY", "")
secret_key = st.secrets.get("SHIOAJI_SECRET_KEY", "")

# 側邊欄 API 設定備援
if not api_key or not secret_key:
    st.sidebar.header("🔑 永豐金 API 設定")
    api_key = st.sidebar.text_input("API Key", type="password")
    secret_key = st.sidebar.text_input("Secret Key", type="password")
else:
    st.sidebar.success("✅ 永豐金 API Key 已自動載入！")

# 盤中自動刷新與聲響警示開關
st.sidebar.subheader("⏱️ 盤中自動盯盤與聲響警示")
auto_refresh = st.sidebar.checkbox("開啟自動盯盤刷新", value=False)
enable_sound = st.sidebar.checkbox("開啟轉折警示音效", value=True)
refresh_interval = st.sidebar.slider("刷新間隔 (秒)", min_value=5, max_value=60, value=10, step=5)

# 聲音發放 HTML 函式 (瀏覽器 Web Audio API)
def play_sound(freq=880, duration=0.5):
    if enable_sound:
        sound_html = f"""
        <script>
        var context = new (window.AudioContext || window.webkitAudioContext)();
        var osc = context.createOscillator();
        var gain = context.createGain();
        osc.type = 'sine';
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

# 5分K KD 技術指標計算
def calculate_kd(df, n=9):
    low_list = df['Low'].rolling(n, min_periods=1).min()
    high_list = df['High'].rolling(n, min_periods=1).max()
    rsv = (df['Close'] - low_list) / (high_list - low_list) * 100
    rsv = rsv.fillna(50)
    
    k = [50.0]
    d = [50.0]
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

# 教學與戰法指南區塊 (4張圖表精華)
with st.expander("📚 實戰戰法指南（進場點 / 停損停利 / 轉弱判讀 / 阿宇策略圖解）"):
    st.markdown("""
    ### 🎯 四大圖卡實戰判讀標準
    1. **圖一：6種進場點**：回踩支撐、突破壓力/整理區帶量、站上5/10日均線、突破下降趨勢線、缺口進場[cite: 10]。
    2. **圖二：停損停利法**：支撐停損、均線停損、固定比例停損，壓力停利與沿5日線移動停利[cite: 11]。
    3. **圖三：6大轉弱訊號**：跌破重要均線/支撐、爆量長黑K、高檔長上影線、量價背離、頭部型態[cite: 12]。
    4. **圖四：阿宇停損停利指南**：
       * **四大設定法**：百分比法、技術位法、K線法、ATR波幅法（1~2倍ATR停損，2~4倍ATR停利）[cite: 13]。
       * **風格定位**：短線當沖 (停損3~5%/停利5~8%)、波段 (停損5~10%/停利10~20%)、長線 (停損10~15%/停利20~50%)[cite: 13]。
    """)

# 自選股快捷區
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = ["3006 晶豪科", "3042 晶技", "2330 台積電", "2317 鴻海"]
if "selected_stock" not in st.session_state:
    st.session_state["selected_stock"] = "3006"

st.subheader("⭐ 自選股快捷區")
if st.session_state["watchlist"]:
    cols = st.columns(min(len(st.session_state["watchlist"]), 5))
    for idx, item in enumerate(st.session_state["watchlist"]):
        col_idx = idx % 5
        code_part = item.split(" ")[0]
        if cols[col_idx].button(item, key=f"btn_{code_part}_{idx}"):
            st.session_state["selected_stock"] = code_part
            st.rerun()

# 刪除自選股
with st.expander("⚙️ 管理/刪除自選股清單"):
    remove_item = st.selectbox("選擇要刪除的自選股", ["（請選擇）"] + st.session_state["watchlist"])
    if st.button("❌ 刪除選取的自選股"):
        if remove_item != "（請選擇）":
            st.session_state["watchlist"].remove(remove_item)
            st.success(f"已移除：{remove_item}")
            st.rerun()

# =========================================================
# 表單輸入區（支援 Enter 鍵直接觸發查詢）
# =========================================================
with st.form(key="search_form"):
    col_input, col_style = st.columns([2, 1])
    with col_input:
        stock_input = st.text_input("請輸入股票代碼或公司名稱（按下 Enter 即可分析）", value=st.session_state["selected_stock"])
    with col_style:
        trade_style = st.selectbox("🎯 交易風格選單 (圖四對照)", ["短線/當沖 (1~3天)", "波段操作 (幾天~幾週)", "長線投資 (1個月以上)"])
    
    target_code, target_name = get_stock_code_and_name(stock_input)
    submit_button = st.form_submit_button("🚀 抓取數據並分析 (Enter)", type="primary")

# 加自選按鈕
if target_code and target_name:
    current_label = f"{target_code} {target_name}"
    col_info, col_btn = st.columns([3, 1])
    with col_info:
        st.caption(f"當前目標：{current_label}")
    with col_btn:
        if current_label in st.session_state["watchlist"]:
            st.button("✅ 已在自選", disabled=True, key="add_watchlist_disabled")
        else:
            if st.button("➕ 加自選", key="add_watchlist_btn"):
                st.session_state["watchlist"].append(current_label)
                st.success(f"已加入：{current_label}")
                st.rerun()

# 分析執行區
if submit_button or auto_refresh:
    if not api_key or not secret_key:
        st.error("請在左側選單填寫 API Key 與 Secret Key！")
    else:
        if not target_code:
            st.error(f"找不到股票：『{stock_input}』")
        else:
            with st.spinner(f"正在讀取【{target_code}】數據與5分K即時監控..."):
                api = None
                try:
                    api = sj.Shioaji(simulation=True)
                    api.login(api_key=api_key, secret_key=secret_key)
                    contract = api.Contracts.Stocks.get(target_code)
                    
                    if not contract:
                        st.error(f"無法取得【{target_code}】合約。")
                    else:
                        snapshots = api.snapshots([contract])
                        if not snapshots:
                            st.error("無法取得即時行情。")
                        else:
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

                            # 核心三維度
                            bias_rate = ((curr_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
                            momentum_coef = (outer_vol / inner_vol) if inner_vol > 0 else 0
                            balance_point = (high_price + low_price + curr_price) / 3

                            st.success(f"【{contract.code} {contract.name}】當前最新價：{curr_price} 元")
                            
                            col1, col2, col3 = st.columns(3)
                            col1.metric("1️⃣ 成本乖離率", f"{bias_rate:+.2f}%")
                            col2.metric("2️⃣ 動能係數", f"{momentum_coef:.2f}")
                            col3.metric("3️⃣ 多空平衡點", f"{balance_point:.2f}元")

                            # 抓取歷史 K 線資料
                            start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
                            end_date = datetime.now().strftime("%Y-%m-%d")
                            
                            kbars = api.kbars(contract=contract, start=start_date, end=end_date)
                            df_raw = pd.DataFrame({
                                "ts": kbars.ts, "Open": kbars.Open, "High": kbars.High,
                                "Low": kbars.Low, "Close": kbars.Close, "Volume": kbars.Volume
                            })
                            
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
                            else:
                                df_k.loc[df_k.index[-1], "Close"] = curr_price
                                df_k.loc[df_k.index[-1], "High"] = max(df_k.loc[df_k.index[-1], "High"], high_price)
                                df_k.loc[df_k.index[-1], "Low"] = min(df_k.loc[df_k.index[-1], "Low"], low_price)

                            # 計算日均線與 ATR
                            df_k["5MA"] = df_k["Close"].rolling(5).mean()
                            df_k["20MA"] = df_k["Close"].rolling(20).mean()
                            df_k = calculate_atr(df_k)
                            
                            ma5 = df_k['5MA'].iloc[-1]
                            ma20 = df_k['20MA'].iloc[-1]
                            atr_val = df_k['ATR'].iloc[-1] if not pd.isna(df_k['ATR'].iloc[-1]) else (curr_price * 0.02)
                            prev_high = df_k['High'].iloc[-2] if len(df_k) > 1 else high_price
                            prev_low = df_k['Low'].iloc[-2] if len(df_k) > 1 else low_price

                            # =========================================================
                            # 🔍 盤前數據全表檢視 (四大圖卡檢驗標準)
                            # =========================================================
                            st.subheader("🔍 盤前數據全表檢視 (四大圖卡標準綜合診斷)")

                            # 1. 6種進場型態檢驗 (圖一)
                            st.markdown("#### 1️⃣ 6種進場型態評估 (圖一對照)")
                            entry_list = []
                            if curr_price > ma5 and ma5 > ma20:
                                entry_list.append("✅ **均線進場**：股價站上 5日/20日均線，多頭排列[cite: 10]。")
                            if curr_price > prev_high:
                                entry_list.append("✅ **突破壓力進場**：股價突破前一日高點壓力[cite: 10]。")
                            if 1.0 <= bias_rate <= 2.0:
                                entry_list.append("✅ **回踩/健康拉升**：成本乖離率介於 +1%~+2%，結構健康[cite: 10]。")
                            
                            if entry_list:
                                for entry in entry_list: st.write(entry)
                            else:
                                st.write("ℹ️ 當前暫無明顯突破型態，建議等待回測支撐或帶量突破[cite: 10]。")

                            # 2. 停損停利四大設定法 (圖二與圖四)
                            st.markdown("#### 2️⃣ 四大停損停利參考設定 (圖二、圖四對照)")
                            col_sl_box, col_tp_box = st.columns(2)
                            
                            # 風格參數判定
                            if "短線" in trade_style:
                                sl_pct, tp_pct = 0.04, 0.06
                            elif "波段" in trade_style:
                                sl_pct, tp_pct = 0.07, 0.15
                            else:
                                sl_pct, tp_pct = 0.12, 0.30

                            with col_sl_box:
                                st.error("🛡️ **多重停損試算 (阿宇圖卡)**")
                                st.write(f"* **百分比法 ({sl_pct*100:.0f}%)**：`{curr_price * (1 - sl_pct):.2f}` 元[cite: 13]")
                                st.write(f"* **ATR 波動法 (1.5xATR)**：`{curr_price - (1.5 * atr_val):.2f}` 元[cite: 13]")
                                st.write(f"* **均線/技術位法 (跌破5MA)**：`{ma5:.2f}` 元[cite: 11, 13]")
                                st.write(f"* **K線法 (前低支撐)**：`{prev_low:.2f}` 元[cite: 12, 13]")

                            with col_tp_box:
                                st.success("🎯 **多重停利試算 (阿宇圖卡)**")
                                st.write(f"* **百分比法 ({tp_pct*100:.0f}%)**：`{curr_price * (1 + tp_pct):.2f}` 元[cite: 13]")
                                st.write(f"* **ATR 波動法 (3xATR)**：`{curr_price + (3 * atr_val):.2f}` 元[cite: 13]")
                                st.write(f"* **移動停利線 (沿5MA)**：`{ma5:.2f}` 元[cite: 11, 13]")
                                st.write(f"* **前高壓力區停利**：`{prev_high:.2f}` 元[cite: 11, 13]")

                            # 3. 6大轉弱避險訊號 (圖三)
                            st.markdown("#### 3️⃣ 6大轉弱訊號防范 (圖三對照)")
                            if curr_price < ma5:
                                st.error("❌ **跌破重要均線**：股價已跌破 5 日均線[cite: 12]。")
                            if bias_rate > 3.0:
                                st.warning("⚠️ **短線過熱/遠離均價**：乖離率 > +3%，提防拉回[cite: 10, 12]。")
                            if curr_price < balance_point:
                                st.error("❌ **失去平衡點**：收盤價低於多空平衡點[cite: 12]。")

                            # =========================================================
                            # ⚡ 5 分 K 線當沖轉折即時盯盤與聲響警示
                            # =========================================================
                            st.subheader("⚡ 5分K 當沖轉折雷達與即時警示")
                            
                            if len(df_raw) > 0:
                                df_raw["DateTime"] = pd.to_datetime(df_raw["ts"] / 1000000000, unit='s', errors='coerce')
                                df_5m = df_raw.set_index("DateTime").resample("5min").agg({
                                    "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
                                }).dropna().reset_index()
                            else:
                                df_5m = pd.DataFrame(columns=["DateTime", "Open", "High", "Low", "Close", "Volume"])

                            df_5m["5MA"] = df_5m["Close"].rolling(5).mean()
                            df_5m["20MA"] = df_5m["Close"].rolling(20).mean()
                            df_5m["Std"] = df_5m["Close"].rolling(20).std()
                            df_5m["UpperBand"] = df_5m["20MA"] + (df_5m["Std"] * 2)
                            df_5m["LowerBand"] = df_5m["20MA"] - (df_5m["Std"] * 2)
                            df_5m = calculate_kd(df_5m)

                            if len(df_5m) >= 2:
                                curr_k = df_5m.iloc[-1]
                                prev_k = df_5m.iloc[-2]
                                max_vol = df_5m["Volume"].tail(10).max()
                                
                                k_body = abs(curr_k["Close"] - curr_k["Open"])
                                upper_shadow = curr_k["High"] - max(curr_k["Close"], curr_k["Open"])
                                lower_shadow = min(curr_k["Close"], curr_k["Open"]) - curr_k["Low"]
                                
                                bull_turn_signals = []
                                bear_turn_signals = []
                                
                                # 1. 爆量長影線
                                if curr_k["Volume"] >= max_vol and lower_shadow > (k_body * 1.5):
                                    bull_turn_signals.append("🔥 **爆量長下影線**：低檔強勁支撐，超跌 V 轉 Signal！")
                                if curr_k["Volume"] >= max_vol and upper_shadow > (k_body * 1.5):
                                    bear_turn_signals.append("⚠️ **爆量長上影線**：高檔主力出貨，空頭 A 轉 Signal！")
                                
                                # 2. 布林通道觸軌
                                if curr_k["High"] >= curr_k["UpperBand"] and curr_k["Close"] < curr_k["Open"]:
                                    bear_turn_signals.append("⚠️️ **觸及布林上軌+收黑**：多頭受阻於頂部，短線轉折向下！")
                                if curr_k["Low"] <= curr_k["LowerBand"] and curr_k["Close"] > curr_k["Open"]:
                                    bull_turn_signals.append("🔥 **觸及布林下軌+站回**：超跌破軌收紅，V 轉買點！")
                                
                                # 3. 吞噬訊號與 KD 高低檔交叉
                                if (prev_k["Close"] < prev_k["Open"]) and (curr_k["Close"] > curr_k["Open"]) and \
                                   (curr_k["Close"] > prev_k["Open"]) and (curr_k["Open"] < prev_k["Close"]) and \
                                   (curr_k["K"] < 30 and curr_k["K"] > curr_k["D"]):
                                    bull_turn_signals.append(f"🔥 **陽線吞噬 + KD低檔金叉**：極佳多單進場點！停損設 `{curr_k['Low']:.2f}` 元。")
                                
                                if (prev_k["Close"] > prev_k["Open"]) and (curr_k["Close"] < curr_k["Open"]) and \
                                   (curr_k["Close"] < prev_k["Open"]) and (curr_k["Open"] > prev_k["Close"]) and \
                                   (curr_k["K"] > 70 and curr_k["K"] < curr_k["D"]):
                                    bear_turn_signals.append(f"⚠️ **陰線吞噬 + KD高檔死叉**：極佳空單進場點！停損設 `{curr_k['High']:.2f}` 元。")

                                # 4. 時間變盤點提醒
                                now_time_str = datetime.now().strftime("%H:%M")
                                if now_time_str in ["09:30", "10:00", "10:30", "12:00"]:
                                    st.warning(f"🕒 **關鍵時間變盤點 ({now_time_str})**：主力發動收割或轉折時間，請注意量價！")

                                # 聲響與視窗警示
                                if bull_turn_signals:
                                    play_sound(freq=1000, duration=0.8)
                                    for b_sig in bull_turn_signals: st.success(b_sig)
                                
                                if bear_turn_signals:
                                    play_sound(freq=400, duration=0.8)
                                    for r_sig in bear_turn_signals: st.error(r_sig)
                                
                                if not bull_turn_signals and not bear_turn_signals:
                                    st.info("ℹ️ 5分K 趨勢正常，未觸發轉折訊號（持續即時盯盤中...）。")

                            # 展示近 30 根 5分K 與布林通道圖表
                            st.subheader("📊 近 30 根 5分K 線與布林通道")
                            df_5m_tail = df_5m.tail(30)
                            fig_5m = go.Figure(data=[go.Candlestick(
                                x=df_5m_tail['DateTime'].dt.strftime('%H:%M'),
                                open=df_5m_tail['Open'], high=df_5m_tail['High'],
                                low=df_5m_tail['Low'], close=df_5m_tail['Close'], name="5分K"
                            )])
                            fig_5m.add_trace(go.Scatter(x=df_5m_tail['DateTime'].dt.strftime('%H:%M'), y=df_5m_tail['UpperBand'], mode='lines', name='布林上軌', line=dict(color='red', width=1, dash='dash')))
                            fig_5m.add_trace(go.Scatter(x=df_5m_tail['DateTime'].dt.strftime('%H:%M'), y=df_5m_tail['20MA'], mode='lines', name='20MA(中軌)', line=dict(color='blue', width=1.5)))
                            fig_5m.add_trace(go.Scatter(x=df_5m_tail['DateTime'].dt.strftime('%Y-%m-%d %H:%M'), y=df_5m_tail['LowerBand'], mode='lines', name='布林下軌', line=dict(color='green', width=1, dash='dash')))
                            fig_5m.update_layout(xaxis_rangeslider_visible=False, height=380, margin=dict(l=10, r=10, t=30, b=10))
                            st.plotly_chart(fig_5m, use_container_width=True)

                except Exception as e:
                    st.error(f"連線失敗或發生錯誤: {str(e)}")
                finally:
                    if api:
                        try: api.logout()
                        except: pass

if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
