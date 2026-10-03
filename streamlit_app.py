import streamlit as st
import shioaji as sj
import pandas as pd
import twstock
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

st.set_page_config(page_title="三維定位法與5分K當沖轉折雷達", layout="centered")

st.title("📈 三維定位法 & 5分K當沖轉折監控雷達")

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
st.sidebar.subheader("⏱️ 盤中盯盤與聲響警示")
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

# 教學與戰法指南區塊
with st.expander("📚 5分K當沖轉折核心觀察點與實戰戰法指南"):
    st.markdown("""
    ### 🎯 5分K當沖四大轉折觸發條件
    1. **爆量長影線**：5分K急衝/急跌，成交量創高且留長上影線（轉折向下空）或長下影線（轉折向上多）。
    2. **5MA 乖離修正**：股價連續拉離 5分K 5MA，出現反向吞噬K棒時引發均線靠攏修正。
    3. **布林通道逆勢狙擊**：觸及布林上軌+收黑K（空點）或觸及下軌+站回軌道內（多點）。
    4. **吞噬訊號與 KD 配合**：
       * **多頭轉折**：陽線吞噬 + KD < 20 低檔黃金交叉（停損設轉折K最低點）。
       * **空頭轉折**：陰線吞噬 + KD > 80 高檔死亡交叉（停損設轉折K最高點）。
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

# 表單輸入區
with st.form(key="search_form"):
    col_input, col_add_btn = st.columns([3, 1])
    with col_input:
        stock_input = st.text_input("請輸入股票代碼或公司名稱（按下 Enter 即可分析）", value=st.session_state["selected_stock"])
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

                            # 三維度計算
                            bias_rate = ((curr_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
                            momentum_coef = (outer_vol / inner_vol) if inner_vol > 0 else 0
                            balance_point = (high_price + low_price + curr_price) / 3

                            st.success(f"【{contract.code} {contract.name}】當前最新價：{curr_price} 元")
                            
                            col1, col2, col3 = st.columns(3)
                            col1.metric("1️⃣ 成本乖離率", f"{bias_rate:+.2f}%")
                            col2.metric("2️⃣ 動能係數", f"{momentum_coef:.2f}")
                            col3.metric("3️⃣ 多空平衡點", f"{balance_point:.2f}元")

                            # 抓取近 3 日的 5 分 K 線
                            start_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
                            end_date = datetime.now().strftime("%Y-%m-%d")
                            
                            kbars = api.kbars(contract=contract, start=start_date, end=end_date)
                            
                            df_raw = pd.DataFrame({
                                "ts": kbars.ts, "Open": kbars.Open, "High": kbars.High,
                                "Low": kbars.Low, "Close": kbars.Close, "Volume": kbars.Volume
                            })
                            
                            if len(df_raw) > 0:
                                df_raw["DateTime"] = pd.to_datetime(df_raw["ts"] / 1000000000, unit='s', errors='coerce')
                                df_5m = df_raw.set_index("DateTime").resample("5min").agg({
                                    "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
                                }).dropna().reset_index()
                            else:
                                df_5m = pd.DataFrame(columns=["DateTime", "Open", "High", "Low", "Close", "Volume"])

                            # 計算 5分K 的 5MA、布林通道 (20MA, 2倍標準差)、KD 指標
                            df_5m["5MA"] = df_5m["Close"].rolling(5).mean()
                            df_5m["20MA"] = df_5m["Close"].rolling(20).mean()
                            df_5m["Std"] = df_5m["Close"].rolling(20).std()
                            df_5m["UpperBand"] = df_5m["20MA"] + (df_5m["Std"] * 2)
                            df_5m["LowerBand"] = df_5m["20MA"] - (df_5m["Std"] * 2)
                            df_5m = calculate_kd(df_5m)

                            # =========================================================
                            # 🎯 5 分 K 線當沖轉折核心條件偵測與聲音警示
                            # =========================================================
                            st.subheader("⚡ 5分K 當沖轉折雷達與即時警示")
                            
                            if len(df_5m) >= 2:
                                curr_k = df_5m.iloc[-1]
                                prev_k = df_5m.iloc[-2]
                                max_vol = df_5m["Volume"].tail(10).max()
                                
                                # K棒特徵計算
                                k_body = abs(curr_k["Close"] - curr_k["Open"])
                                upper_shadow = curr_k["High"] - max(curr_k["Close"], curr_k["Open"])
                                lower_shadow = min(curr_k["Close"], curr_k["Open"]) - curr_k["Low"]
                                
                                bull_turn_signals = []
                                bear_turn_signals = []
                                
                                # 1. 爆量長影線
                                if curr_k["Volume"] >= max_vol and lower_shadow > (k_body * 1.5):
                                    bull_turn_signals.append("🔥 **爆量長下影線**：低檔支撐強勁，短線多頭超跌 V 轉 Signal！")
                                if curr_k["Volume"] >= max_vol and upper_shadow > (k_body * 1.5):
                                    bear_turn_signals.append("⚠️ **爆量長上影線**：高檔主力出貨，短線空頭 A 轉 Signal！")
                                
                                # 2. 布林通道觸軌
                                if curr_k["High"] >= curr_k["UpperBand"] and curr_k["Close"] < curr_k["Open"]:
                                    bear_turn_signals.append("⚠️ **觸及布林上軌+收黑**：多頭受阻於軌道頂部，短線轉折向下！")
                                if curr_k["Low"] <= curr_k["LowerBand"] and curr_k["Close"] > curr_k["Open"]:
                                    bull_turn_signals.append("🔥 **觸及布林下軌+站回**：超跌破軌後收紅，V 轉買點發起！")
                                
                                # 3. 吞噬訊號與 KD 高低檔交叉
                                # 陽線吞噬 + KD 低檔黃金交叉
                                if (prev_k["Close"] < prev_k["Open"]) and (curr_k["Close"] > curr_k["Open"]) and \
                                   (curr_k["Close"] > prev_k["Open"]) and (curr_k["Open"] < prev_k["Close"]) and \
                                   (curr_k["K"] < 30 and curr_k["K"] > curr_k["D"]):
                                    bull_turn_signals.append(f"🔥 **陽線吞噬 + KD低檔金叉**：極佳多單進場點！建議停損設前低 `{curr_k['Low']:.2f}` 元。")
                                
                                # 陰線吞噬 + KD 高檔死亡交叉
                                if (prev_k["Close"] > prev_k["Open"]) and (curr_k["Close"] < curr_k["Open"]) and \
                                   (curr_k["Close"] < prev_k["Open"]) and (curr_k["Open"] > prev_k["Close"]) and \
                                   (curr_k["K"] > 70 and curr_k["K"] < curr_k["D"]):
                                    bear_turn_signals.append(f"⚠️ **陰線吞噬 + KD高檔死叉**：極佳空單進場點！建議停損設前高 `{curr_k['High']:.2f}` 元。")

                                # 4. 時間變盤點提醒 (09:30, 10:00, 10:30, 12:00)
                                now_time_str = datetime.now().strftime("%H:%M")
                                if now_time_str in ["09:30", "10:00", "10:30", "12:00"]:
                                    st.warning(f"🕒 **關鍵時間變盤點 ({now_time_str})**：主力常在此時發動收割或V轉/A轉，密切注意五檔量價變化！")

                                # 顯示警示與播放警示音效
                                if bull_turn_signals:
                                    play_sound(freq=1000, duration=0.8) # 高音警示多頭
                                    for b_sig in bull_turn_signals:
                                        st.success(b_sig)
                                
                                if bear_turn_signals:
                                    play_sound(freq=400, duration=0.8) # 低音警示空頭
                                    for r_sig in bear_turn_signals:
                                        st.error(r_sig)
                                
                                if not bull_turn_signals and not bear_turn_signals:
                                    st.info("ℹ️ 5分K 當前趨勢正常，未觸發極端轉折訊號（持續即時盯盤中...）。")

                            # 展示 5 分 K 線與布林通道圖表
                            st.subheader("📊 近 30 根 5分K 線與布林通道 (20MA, 2倍標準差)")
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
