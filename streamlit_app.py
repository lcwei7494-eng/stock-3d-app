import streamlit as st
import shioaji as sj
import pandas as pd

st.set_page_config(page_title="三維定位法分析器", layout="centered")

st.title("📈 三維定位法 - 自動抓取分析器")

# 側邊欄：輸入 API 金鑰
st.sidebar.header("🔑 永豐金 API 設定")
api_key = st.sidebar.text_input("API Key", type="password")
secret_key = st.sidebar.text_input("Secret Key", type="password")

# 主要區域：輸入股票代碼
stock_code = st.text_input("請輸入股票代碼", value="3042")

if st.button("🚀 抓取數據並分析", type="primary"):
    if not api_key or not secret_key:
        st.error("請在左側選單填寫 API Key 與 Secret Key！")
    else:
        with st.spinner("正在連線永豐金 API 抓取資料..."):
            try:
                # 初始化 API
                api = sj.Shioaji(simulation=True)
                api.login(api_key=api_key, secret_key=secret_key)
                
                # 抓取股票資料
                contract = api.Contracts.Stocks.get(stock_code)
                if not contract:
                    st.error(f"找不到股票代碼：{stock_code}")
                else:
                    snapshots = api.snapshots([contract])
                    if not snapshots:
                        st.error("無法取得即時行情（可能非開盤時間或權限不足）。")
                    else:
                        snap = snapshots[0]
                        curr_price = float(getattr(snap, 'close', 0.0))
                        high_price = float(getattr(snap, 'high', 0.0))
                        low_price = float(getattr(snap, 'low', 0.0))
                        
                        # 取得均價 (若未提供則用當前價代替)
                        avg_price = float(getattr(snap, 'average_price', curr_price))
                        if avg_price == 0:
                            avg_price = curr_price
                        
                        # 修正屬性名稱：ask_volume 與 bid_volume
                        outer_vol = float(getattr(snap, 'ask_volume', 0.0))  # 外盤量
                        inner_vol = float(getattr(snap, 'bid_volume', 0.0))  # 內盤量

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
                        
                        # 關鍵指標展現
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