import streamlit as st
import shioaji as sj
import pandas as pd

st.set_page_config(page_title="三維定位法分析器", layout="centered")

st.title("📈 三維定位法 - 自動抓取分析器")

# 自動從 Streamlit Secrets 讀取 API Key (若無設定則退回手動輸入模式)
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
# 使用 Streamlit 快取機制，防止 Shioaji API 重複初始化與連線衝突
# =========================================================
@st.cache_resource(show_spinner=False)
def get_shioaji_api(key, secret):
    """初始化 API 並載入全台股合約清單（全域僅執行一次）"""
    api = sj.Shioaji(simulation=True)
    api.login(api_key=key, secret_key=secret)
    api.fetch_contracts(contract_type=['Stock'])
    return api

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

# 主要區域：輸入股票代碼或中文公司名稱
stock_input = st.text_input("請輸入股票代碼或公司名稱", value="3042")

if st.button("🚀 抓取數據並分析", type="primary"):
    if not api_key or not secret_key:
        st.error("請在左側選單填寫 API Key 與 Secret Key，或設定 Streamlit Secrets！")
    else:
        with st.spinner("正在讀取股票數據..."):
            try:
                # 取得已快取的 API 物件 (避開多線程獨佔衝突)
                api = get_shioaji_api(api_key, secret_key)
                
                target_input = stock_input.strip()
                contract = None
                
                # 1. 優先嘗試當作股票代碼直接取得合約
                contract = api.Contracts.Stocks.get(target_input)
                
                # 2. 若找不到代碼，走訪上市與上櫃搜尋中文名稱
                if not contract:
                    for market in [api.Contracts.Stocks.TSE, api.Contracts.Stocks.OTC]:
                        for code, stock in market.items():
                            stock_name = getattr(stock, 'name', '')
                            if target_input == stock_name or (stock_name and target_input in stock_name):
                                contract = stock
                                break
                        if contract:
                            break

                if not contract:
                    st.error(f"找不到股票代碼或公司名稱：『{stock_input}』，請確認名稱是否正確（例：晶技、台積電 或 3042）。")
                else:
                    snapshots = api.snapshots([contract])
                    if not snapshots:
                        st.error("無法取得即時行情（可能非開盤時間或權限不足）。")
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

                        # 顯示結果
                        st.success(f"【{contract.code} {contract.name}】數據讀取成功！")
                        
                        col1, col2, col3 = st.columns(3)
                        col1.metric("1️⃣ 成本乖離率", f"{bias_rate:+.2f}%")
                        col2.metric("2️⃣ 動能係數", f"{momentum_coef:.2f}")
                        col3.metric("3️⃣ 多空平衡點", f"{balance_point:.2f}元")

                        st.subheader("📋 綜合判定診斷表")
                        df = pd.DataFrame({
                            "維度": ["第一維度（成本乖離率）", "第二維度（動能係數）", "第三維度（多空平衡點）"],
                            "數值": [f"{bias_rate:+.2f}%", f"{momentum_coef:.2f}", f"{balance_point:.2f}元"],
                            "系統判定": [bias_eval, momentum_eval, balance_eval]
                        })
                        st.table(df)

            except Exception as e:
                st.error(f"連線失敗或發生錯誤: {str(e)}")
