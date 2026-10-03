import streamlit as st
import shioaji as sj
import pandas as pd
import twstock
import plotly.graph_objects as go
import time

st.set_page_config(page_title="三維定位法與進出場策略分析器", layout="centered")

st.title("📈 三維定位法 & 進出場戰術分析器")

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

# 盤中自動刷新設定
st.sidebar.subheader("⏱️ 盤中自動刷新設定")
auto_refresh = st.sidebar.checkbox("開啟自動定時刷新", value=False)
refresh_interval = st.sidebar.slider("刷新間隔 (秒)", min_value=5, max_value=60, value=10, step=5)

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

# =========================================================
# 教學與策略指南區塊 (包含三張圖的文字解讀)
# =========================================================
with st.expander("📚 實戰戰法指南（三維定位法 + 進場 / 停損停利 / 轉弱判讀）"):
    st.markdown("""
    ### 🎯 第一部分：三維定位法
    * **第一維度：成本乖離率**：衡量當前價與分時均價距離。+1%~+2% 健康偏強；>+3% 過熱不追[cite: 1]。
    * **第二維度：動能係數**：外盤/內盤比值。≥1.4 代表主動買盤強勁[cite: 2, 3]。
    * **第三維度：多空平衡點**：(高+低+收)/3。收盤價高於平衡點代表多頭領先。

    ---
    ### 🎯 第二部分：怎麼找進場點？（6種常見方式）[cite: 1]
    1. **回踩支撐**：上漲趨勢中回測支撐再上攻[cite: 1]。
    2. **突破壓力**：突破前高或整理區，伴隨成交量放大[cite: 1]。
    3. **整理區間**：靠近區間下緣支撐買進，突破上緣加碼[cite: 1]。
    4. **均線進場**：股價站上重要均線（如 5日、10日線）且均線轉多[cite: 1]。
    5. **突破下降趨勢線**：跌勢結束突破下降趨勢線[cite: 1]。
    6. **缺口進場**：跳空突破缺口且有量[cite: 1]。

    ---
    ### 🎯 第三部分：停損、停利怎麼設？[cite: 2]
    * **停損法**：支撐停損、均線停損、固定比例停損（3%~7%）[cite: 2]。
    * **停利法**：壓力停利（前高壓力區）、移動停利（沿5日線）、分批停利（+5%、+10%、+15%）[cite: 2]。
    * **短線/當沖建議**：停損設 3%~5%，停利設 5%~10%[cite: 2]。

    ---
    ### 🎯 第四部分：怎麼判斷股票轉弱？（6大訊號）[cite: 3]
    1. **跌破重要均線**：均線由多頭轉空頭排列[cite: 3]。
    2. **爆量長黑 K**：高檔賣壓湧現，主力出貨[cite: 3]。
    3. **高檔長上影線**：衝高回落，上方賣壓重[cite: 3]。
    4. **重要支撐跌破**：跌破前低或整理區下緣[cite: 3]。
    5. **量價背離**：股價創新高但成交量萎縮[cite: 3]。
    6. **頭部形態**：形成 M頭、頭肩頂並跌破頸線[cite: 3]。
    """)

# 自選股快捷區
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = ["3042 晶技", "2330 台積電", "2317 鴻海"]
if "selected_stock" not in st.session_state:
    st.session_state["selected_stock"] = "3042"

st.subheader("⭐ 自選股快捷區")
if st.session_state["watchlist"]:
    cols = st.columns(min(len(st.session_state["watchlist"]), 5))
    for idx, item in enumerate(st.session_state["watchlist"]):
        col_idx = idx % 5
        code_part = item.split(" ")[0]
        if cols[col_idx].button(item, key=f"btn_{code_part}_{idx}"):
            st.session_state["selected_stock"] = code_part
            st.rerun()

# 輸入框與快速新增
col_input, col_add_btn = st.columns([3, 1])
with col_input:
    stock_input = st.text_input("請輸入股票代碼或公司名稱", value=st.session_state["selected_stock"])

target_code, target_name = get_stock_code_and_name(stock_input)

with col_add_btn:
    st.write("&#160;")
    if target_code and target_name:
        current_label = f"{target_code} {target_name}"
        if current_label in st.session_state["watchlist"]:
            st.button("✅ 已在自選", disabled=True, key="add_watchlist_disabled")
        else:
            if st.button("➕ 加自選", key="add_watchlist_btn"):
                st.session_state["watchlist"].append(current_label)
                st.success(f"已加入：{current_label}")
                st.rerun()

# 刪除自選股
with st.expander("⚙️ 管理/刪除自選股清單"):
    remove_item = st.selectbox("選擇要刪除的自選股", ["（請選擇）"] + st.session_state["watchlist"])
    if st.button("❌ 刪除選取的自選股"):
        if remove_item != "（請選擇）":
            st.session_state["watchlist"].remove(remove_item)
            st.success(f"已移除：{remove_item}")
            st.rerun()

# 分析執行區
if st.button("🚀 抓取數據並分析", type="primary") or auto_refresh:
    if not api_key or not secret_key:
        st.error("請在左側選單填寫 API Key 與 Secret Key！")
    else:
        if not target_code:
            st.error(f"找不到股票：『{stock_input}』")
        else:
            with st.spinner(f"正在讀取【{target_code}】數據..."):
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
                            curr_price = float(getattr(snap, 'close', 0.0))[cite: 1]
                            high_price = float(getattr(snap, 'high', 0.0))
                            low_price = float(getattr(snap, 'low', 0.0))
                            avg_price = float(getattr(snap, 'average_price', curr_price))[cite: 1]
                            if avg_price == 0: avg_price = curr_price
                            outer_vol = float(getattr(snap, 'ask_volume', 0.0))
                            inner_vol = float(getattr(snap, 'bid_volume', 0.0))

                            # 核心三維度
                            bias_rate = ((curr_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0[cite: 1]
                            momentum_coef = (outer_vol / inner_vol) if inner_vol > 0 else 0
                            balance_point = (high_price + low_price + curr_price) / 3

                            st.success(f"【{contract.code} {contract.name}】最新成交價：{curr_price} 元")
                            
                            col1, col2, col3 = st.columns(3)
                            col1.metric("1️⃣ 成本乖離率", f"{bias_rate:+.2f}%")[cite: 1]
                            col2.metric("2️⃣ 動能係數", f"{momentum_coef:.2f}")
                            col3.metric("3️⃣ 多空平衡點", f"{balance_point:.2f}元")

                            # 取得歷史 K 線計算 5MA / 20MA
                            kbars = api.kbars(contract, start="2026-09-01")
                            df_k = pd.DataFrame({
                                "Date": kbars.ts, "Open": kbars.Open, "High": kbars.High,
                                "Low": kbars.Low, "Close": kbars.Close, "Volume": kbars.Volume
                            })
                            df_k["Date"] = pd.to_datetime(df_k["Date"])
                            df_k["5MA"] = df_k["Close"].rolling(5).mean()
                            df_k["20MA"] = df_k["Close"].rolling(20).mean()
                            
                            last_close = df_k['Close'].iloc[-1]
                            ma5 = df_k['5MA'].iloc[-1]
                            ma20 = df_k['20MA'].iloc[-1]
                            prev_high = df_k['High'].iloc[-2]

                            # =========================================================
                            # 新增功能：圖片戰略綜合診斷區 (一鍵診斷)
                            # =========================================================
                            st.subheader("🛠️ 圖解戰法實戰診斷")

                            # 1. 進場點診斷 (圖一)
                            st.markdown("#### 🟢 1. 進場型態評估 (圖一對照)")[cite: 1]
                            entry_signals = []
                            if curr_price > ma5 and ma5 > ma20:
                                entry_signals.append("✅ **均線進場**：股價站上 5日/20日線，均線多頭排列[cite: 1]。")
                            if curr_price > prev_high:
                                entry_signals.append("✅ **突破壓力進場**：股價已突破前一日高點壓力[cite: 1]。")
                            if 1.0 <= bias_rate <= 2.0:
                                entry_signals.append("✅ **回踩/健康拉升**：成本乖離率介於 +1%~+2%，籌碼結構健康[cite: 1]。")
                            
                            if entry_signals:
                                for sig in entry_signals: st.write(sig)
                            else:
                                st.write("ℹ️ 當前暫無明顯突破或帶量進場型態，建議等待回測支撐或帶量突破[cite: 1]。")

                            # 2. 停損停利試算 (圖二)
                            st.markdown("#### 🎯 2. 戰術停損與停利參考試算 (圖二對照)")[cite: 2]
                            col_sl, col_tp = st.columns(2)
                            with col_sl:
                                st.error("🛡️ **建議停損點**")
                                st.write(f"* **短線固定停損 (5%)**：`{curr_price * 0.95:.2f}` 元[cite: 2]")
                                st.write(f"* **均線停損 (跌破 5MA)**：`{ma5:.2f}` 元[cite: 2]")
                                st.write(f"* **平衡點停損**：`{balance_point:.2f}` 元[cite: 2]")
                            with col_tp:
                                st.success("🎯 **建議停利點**")
                                st.write(f"* **第一目標 (+5%)**：`{curr_price * 1.05:.2f}` 元[cite: 2]")
                                st.write(f"* **第二目標 (+10%)**：`{curr_price * 1.10:.2f}` 元[cite: 2]")
                                st.write(f"* **前高壓力區停利**：`{prev_high:.2f}` 元[cite: 2]")

                            # 3. 轉弱風險警示 (圖三)
                            st.markdown("#### 🚨 3. 轉弱訊號偵測 (圖三對照)")[cite: 3]
                            weak_signals = []
                            if curr_price < ma5:
                                weak_signals.append("❌ **跌破重要均線**：股價已跌破 5 日均線[cite: 3]。")
                            if bias_rate > 3.0:
                                weak_signals.append("❌ **短線過熱/遠離均價**：乖離率 > +3%，提防高檔拉回[cite: 1, 3]。")
                            if curr_price < balance_point:
                                weak_signals.append("❌ **失去平衡點支撐**：收盤價低於多空平衡點，多頭結構轉弱[cite: 3]。")

                            if weak_signals:
                                for w_sig in weak_signals: st.warning(w_sig)
                            else:
                                st.success("✅ 目前未偵測到明顯轉弱訊號，多頭結構正常[cite: 3]。")

                            # 展示近 15 日 K 線圖
                            st.subheader("📜 近 15 日 K 線與均線")
                            df_k_tail = df_k.tail(15)
                            fig_k = go.Figure(data=[go.Candlestick(
                                x=df_k_tail['Date'].dt.strftime('%Y-%m-%d'),
                                open=df_k_tail['Open'], high=df_k_tail['High'],
                                low=df_k_tail['Low'], close=df_k_tail['Close'], name="日K"
                            )])
                            fig_k.add_trace(go.Scatter(x=df_k_tail['Date'].dt.strftime('%Y-%m-%d'), y=df_k_tail['5MA'], mode='lines', name='5MA', line=dict(color='orange', width=1.5)))
                            fig_k.add_trace(go.Scatter(x=df_k_tail['Date'].dt.strftime('%Y-%m-%d'), y=df_k_tail['20MA'], mode='lines', name='20MA', line=dict(color='purple', width=1.5)))
                            fig_k.update_layout(xaxis_rangeslider_visible=False, height=350, margin=dict(l=10, r=10, t=30, b=10))
                            st.plotly_chart(fig_k, use_container_width=True)

                except Exception as e:
                    st.error(f"連線失敗或發生錯誤: {str(e)}")
                finally:
                    if api:
                        try: api.logout()
                        except: pass

if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
