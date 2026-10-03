import streamlit as st
import shioaji as sj
import pandas as pd
import twstock
import plotly.graph_objects as go
import time

st.set_page_config(page_title="三維定位法分析器 - 專業旗艦版", layout="centered")

st.title("📈 三維定位法 - 自動抓取分析器")

# 自動從 Streamlit Secrets 讀取 API Key
api_key = st.secrets.get("SHIOAJI_API_KEY", "")
secret_key = st.secrets.get("SHIOAJI_SECRET_KEY", "")

# 側邊欄：僅在沒有設定 Secrets 時顯示手動輸入框作為備援
if not api_key or not secret_key:
    st.sidebar.header("🔑 永豐金 API 設定")
    api_key = st.sidebar.text_input("API Key", type="password")
    secret_key = st.sidebar.text_input("Secret Key", type="password")
else:
    st.sidebar.success("✅ 永豐金 API Key 已自動載入！")

# =========================================================
# 盤中自動刷新設定（側邊欄）
# =========================================================
st.sidebar.subheader("⏱️ 盤中自動刷新設定")
auto_refresh = st.sidebar.checkbox("開啟自動定時刷新", value=False)
refresh_interval = st.sidebar.slider("刷新間隔 (秒)", min_value=5, max_value=60, value=10, step=5)

# =========================================================
# 輔助函式：將中文公司名稱或代碼統一轉為股票代碼與名稱
# =========================================================
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
# 三維定位法完整教學與說明區塊
# =========================================================
with st.expander("📚 點此查看【三維定位法】三個維度的核心含義與實戰判讀"):
    st.markdown("""
    ### 1️⃣ 第一維度：成本乖離率
    * **算式**：$\\text{成本乖離率} = \\frac{\\text{目前價格} - \\text{今日分時均價}}{\\text{今日分時均價}} \\times 100\\%$
    * **核心含義**：衡量當前股價與今日市場平均交易成本的差距。
    * **實戰判讀**：
      * **正乖離率（> 0%）**：當前股價高於均價，多數買方獲利，買盤意願較強。
      * **健康偏強（+1% ~ +2%）**：主力穩健拉升且籌碼經充分換手，結構健康。
      * **短線過熱（> +3% ~ +5%）**：拉離均價過遠，容易引發獲利了結賣壓，不宜盲目追高。
      * **負乖離率（< 0%）**：股價跌破均價，買方多數套牢，短線結構轉弱。

    ---

    ### 2️⃣ 第二維度：動能係數
    * **算式**：$\\text{動能係數} = \\frac{\\text{外盤張數}}{\\text{內盤張數}}$
    * **核心含義**：衡量買方主動吃貨（敲外盤）與賣方主動拋售（砍內盤）的力道對比。
    * **實戰判讀**：
      * **強勢攻擊（≥ 1.4）**：外盤遠大於內盤，代表主動買盤強勁，主力吃貨拉抬意願高。
      * **買氣平平（1.0 ~ 1.4）**：多空對峙均衡，屬溫和推升或整理。
      * **賣壓偏強（< 1.0）**：內盤大於外盤，代表主動拋售賣壓重，拉升不易。

    ---

    ### 3️⃣ 第三維度：多空平衡點
    * **算式**：$\\text{多空平衡點} = \\frac{\\text{今日最高價} + \\text{今日最低價} + \\text{目前價}}{3}$
    * **核心含義**：當天多空激烈交戰後的中心價位，亦為隔天多空決戰的關鍵支撐/壓力關卡。
    * **實戰判讀**：
      * **多頭領先（收盤價 > 平衡點）**：當天拉升有效，結構穩固，隔天守住平衡點可續抱。
      * **多頭防守/轉弱（收盤價 < 平衡點）**：當天衝高回落或誘多，若隔天開低跌破平衡點應提防回測。
    """)

# =========================================================
# 可動態自訂管理（新增/刪除）的自選股清單
# =========================================================
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = ["3042 晶技", "2330 台積電", "2317 鴻海"]

if "selected_stock" not in st.session_state:
    st.session_state["selected_stock"] = "3042"

st.subheader("⭐ 自選股快捷區")

# 顯示自選股按鈕
if st.session_state["watchlist"]:
    cols = st.columns(min(len(st.session_state["watchlist"]), 5))
    for idx, item in enumerate(st.session_state["watchlist"]):
        col_idx = idx % 5
        code_part = item.split(" ")[0]
        if cols[col_idx].button(item, key=f"btn_{code_part}_{idx}"):
            st.session_state["selected_stock"] = code_part
            st.rerun()

# 股票輸入框與快速新增按鈕
col_input, col_add_btn = st.columns([3, 1])
with col_input:
    stock_input = st.text_input("請輸入股票代碼或公司名稱", value=st.session_state["selected_stock"])

# 自動解析當前輸入的股票資訊
target_code, target_name = get_stock_code_and_name(stock_input)

with col_add_btn:
    st.write("&#160;")  # 垂直對齊調高
    if target_code and target_name:
        current_label = f"{target_code} {target_name}"
        if current_label in st.session_state["watchlist"]:
            st.button("✅ 已加入", disabled=True, key="add_watchlist_disabled")
        else:
            if st.button("➕ 加自選", key="add_watchlist_btn"):
                st.session_state["watchlist"].append(current_label)
                st.success(f"已加入：{current_label}")
                st.rerun()

# 自選股管理選單（可手動刪除）
with st.expander("⚙️ 管理/刪除自選股清單"):
    remove_item = st.selectbox("選擇要刪除的自選股", ["（請選擇）"] + st.session_state["watchlist"])
    if st.button("❌ 刪除選取的自選股"):
        if remove_item != "（請選擇）":
            st.session_state["watchlist"].remove(remove_item)
            st.success(f"已從自選股移除：{remove_item}")
            st.rerun()

# 分析執行區
if st.button("🚀 抓取數據並分析", type="primary") or auto_refresh:
    if not api_key or not secret_key:
        st.error("請在左側選單填寫 API Key 與 Secret Key，或設定 Streamlit Secrets！")
    else:
        if not target_code:
            st.error(f"找不到股票：『{stock_input}』，請確認公司名稱或直接輸入 4 位數代碼。")
        else:
            with st.spinner(f"已識別股票代碼【{target_code}】，正在讀取即時與日線數據..."):
                api = None
                try:
                    api = sj.Shioaji(simulation=True)
                    api.login(api_key=api_key, secret_key=secret_key)
                    
                    contract = api.Contracts.Stocks.get(target_code)
                    
                    if not contract:
                        st.error(f"無法在 Shioaji 取得代碼【{target_code}】的合約。")
                    else:
                        snapshots = api.snapshots([contract])
                        if not snapshots:
                            st.error("無法取得即時行情（可能非開盤時間或 API 權限問題）。")
                        else:
                            snap = snapshots[0]
                            curr_price = float(getattr(snap, 'close', 0.0))
                            high_price = float(getattr(snap, 'high', 0.0))
                            low_price = float(getattr(snap, 'low', 0.0))
                            
                            # 取得均價
                            avg_price = float(getattr(snap, 'average_price', curr_price))
                            if avg_price == 0:
                                avg_price = curr_price
                            
                            # 外盤與內盤量
                            outer_vol = float(getattr(snap, 'ask_volume', 0.0))
                            inner_vol = float(getattr(snap, 'bid_volume', 0.0))

                            # 三維度計算
                            bias_rate = ((curr_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
                            momentum_coef = (outer_vol / inner_vol) if inner_vol > 0 else 0
                            balance_point = (high_price + low_price + curr_price) / 3

                            # 評估邏輯
                            bias_eval = "健康偏強 (+1%~+2%)" if 1 <= bias_rate <= 2 else ("短線過熱 (>+2%)" if bias_rate > 2 else "結構偏弱/回落")
                            momentum_eval = "買氣主動攻擊意願強 (≥1.4)" if momentum_coef >= 1.4 else ("買氣平平 (1.0~1.4)" if momentum_coef >= 1.0 else "賣壓偏強 (<1.0)")
                            balance_eval = f"多頭領先 ({curr_price} > 平衡點 {balance_point:.2f})" if curr_price >= balance_point else f"多頭防守 ({curr_price} < 平衡點 {balance_point:.2f})"

                            # 綜合強弱度評價與訊號燈判定
                            st.success(f"【{contract.code} {contract.name}】數據讀取成功！")
                            
                            if bias_rate >= 1.0 and bias_rate <= 2.5 and momentum_coef >= 1.4 and curr_price >= balance_point:
                                st.balloons()
                                st.success("🔥 **【黃金攻擊訊號】**：成本乖離健康、買氣攻擊強勁且站穩多空平衡點，短線多頭結構完美！")
                            elif bias_rate > 3.0:
                                st.warning("⚠️ **【警示：短線過熱】**：成本乖離率已高於 +3%，小心追高獲利回吐賣壓！")
                            elif curr_price < balance_point and momentum_coef < 1.0:
                                st.error("🚨 **【警示：空頭壓制】**：跌破多空平衡點且主動賣壓偏重，建議觀望或停損防守。")
                            else:
                                st.info("ℹ️ **【盤整/觀望訊號】**：指標表現平平，屬區間震盪整理格局。")

                            # 核心三維度指標卡片
                            col1, col2, col3 = st.columns(3)
                            col1.metric("1️⃣ 成本乖離率", f"{bias_rate:+.2f}%")
                            col2.metric("2️⃣ 動能係數", f"{momentum_coef:.2f}")
                            col3.metric("3️⃣ 多空平衡點", f"{balance_point:.2f}元")

                            # 診斷表
                            st.subheader("📋 綜合判定診斷表")
                            df = pd.DataFrame({
                                "維度": ["第一維度（成本乖離率）", "第二維度（動能係數）", "第三維度（多空平衡點）"],
                                "數值": [f"{bias_rate:+.2f}%", f"{momentum_coef:.2f}", f"{balance_point:.2f}元"],
                                "系統判定": [bias_eval, momentum_eval, balance_eval]
                            })
                            st.table(df)

                            # 即時五檔買賣價量視覺化
                            st.subheader("📊 五檔買賣委託柱狀視覺化")
                            bids = getattr(snap, 'bids', [])
                            asks = getattr(snap, 'asks', [])
                            
                            if bids and asks:
                                bid_prices = [f"買{i+1}: {b.price}" for i, b in enumerate(bids[:5])]
                                bid_vols = [b.volume for b in bids[:5]]
                                ask_prices = [f"賣{i+1}: {a.price}" for i, a in enumerate(asks[:5])]
                                ask_vols = [a.volume for a in asks[:5]]

                                fig_depth = go.Figure()
                                fig_depth.add_trace(go.Bar(y=bid_prices[::-1], x=bid_vols[::-1], orientation='h', name='買盤掛單', marker_color='red'))
                                fig_depth.add_trace(go.Bar(y=ask_prices[::-1], x=ask_vols[::-1], orientation='h', name='賣盤掛單', marker_color='green'))
                                fig_depth.update_layout(title="最佳五檔掛單量對比", barmode='relative', height=300, margin=dict(l=10, r=10, t=40, b=10))
                                st.plotly_chart(fig_depth, use_container_width=True)

                            # 近 15 日 K 線圖與日層級均線對比
                            st.subheader("📜 近 15 日 K 線與日均線對比")
                            try:
                                kbars = api.kbars(contract, start="2026-09-01")
                                df_k = pd.DataFrame({
                                    "Date": kbars.ts,
                                    "Open": kbars.Open,
                                    "High": kbars.High,
                                    "Low": kbars.Low,
                                    "Close": kbars.Close,
                                    "Volume": kbars.Volume
                                })
                                df_k["Date"] = pd.to_datetime(df_k["Date"])
                                df_k["5MA"] = df_k["Close"].rolling(5).mean()
                                df_k["20MA"] = df_k["Close"].rolling(20).mean()
                                df_k = df_k.tail(15)

                                fig_k = go.Figure(data=[go.Candlestick(
                                    x=df_k['Date'].dt.strftime('%Y-%m-%d'),
                                    open=df_k['Open'], high=df_k['High'],
                                    low=df_k['Low'], close=df_k['Close'],
                                    name="日K"
                                )])
                                fig_k.add_trace(go.Scatter(x=df_k['Date'].dt.strftime('%Y-%m-%d'), y=df_k['5MA'], mode='lines', name='5日均線(5MA)', line=dict(color='orange', width=1.5)))
                                fig_k.add_trace(go.Scatter(x=df_k['Date'].dt.strftime('%Y-%m-%d'), y=df_k['20MA'], mode='lines', name='20日均線(20MA)', line=dict(color='purple', width=1.5)))
                                fig_k.update_layout(xaxis_rangeslider_visible=False, height=350, margin=dict(l=10, r=10, t=30, b=10))
                                st.plotly_chart(fig_k, use_container_width=True)

                                last_close = df_k['Close'].iloc[-1]
                                ma5 = df_k['5MA'].iloc[-1]
                                ma20 = df_k['20MA'].iloc[-1]
                                ma_trend = "多頭排列 (股價 > 5MA > 20MA)" if last_close >= ma5 >= ma20 else ("空頭排列" if last_close < ma5 < ma20 else "均線糾結震盪")
                                st.info(f"📈 **日線趨勢對照**：當前收盤價 {last_close} 元 | 5MA: {ma5:.2f}元 | 20MA: {ma20:.2f}元（系統判定：**{ma_trend}**）")

                            except Exception as e_k:
                                st.caption("（未能取得日 K 線圖，僅顯示即時三維數據）")

                except Exception as e:
                    st.error(f"連線失敗或發生錯誤: {str(e)}")
                finally:
                    if api:
                        try:
                            api.logout()
                        except:
                            pass

# 處理盤中自動刷新延遲
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
