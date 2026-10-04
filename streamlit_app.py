# 🤖 真正呼叫 Gemini API 的高盛資深分析師診斷函式 (已完全修復 404 模型名稱與 SDK 相容性)
def run_goldman_sachs_ai_evaluation(row, user_gemini_key=""):
    c_code = str(row['股票代碼'])
    c_name = str(row['股票名稱'])
    price = row.get('最新真實價', row.get('最新價', 100.0))
    pct = row.get('漲跌幅(%)', 0.0)
    eps = row.get('季EPS', 1.5)
    yoy = row.get('營收YoY', '+20.0%')
    roe = row.get('ROE', '15.0%')
    peg = row.get('PEG', 0.8)
    score = row.get('綜合評分', 75)
    catalyst = row.get('催化劑', '產業景氣回溫/庫存回補')
    status = row.get('狀態', '強勢突破')

    key_to_use = user_gemini_key if user_gemini_key else gemini_api_key

    if not key_to_use:
        return "⚠️ 請先在左側選單輸入 **Gemini API Key**，或於 Secrets 設定 `GEMINI_API_KEY` 以啟動 AI 實時診斷！"

    prompt = f"""
你是高盛（Goldman Sachs）資深台股證券分析師，具備 30 年機構法人操盤經驗。
請針對以下台股個股數據進行專業且實質的深度評估，切勿使用公版套話：

【個股即時數據】
* 股票代碼與名稱：{c_code} {c_name}
* 最新成交價：{price} 元 (漲跌幅: {pct:+.2f}%)
* 量化戰略評分：{score} 分 (戰略狀態: {status})
* 基本面數據：季 EPS {eps} 元 | 營收 YoY {yoy} | ROE {roe} | PEG 估值 {peg}
* 產業催化劑題材：{catalyst}

【請嚴格依據下列 3 大點輸出深度評估】
1. **🎯 核心操作策略與進場指引**：分析該股營收成長是否真正轉化為獲利，評估其目前股價位置，給出最佳買進點位與短中線操作戰戰法（是否宜追高，或是應等待拉回關鍵均線）。
2. **📊 買進勝率與勝率結構評估**：請給出具體的短線/波段買進勝率預估（例如 75%），並列出勝率支撐的主要理由與技術/基本面優勢。
3. **⚠️ 風險提示與嚴格停損位**：指出該股當前最大的風險因子（如本益比過高、獲利未跟上營收、高檔獲利吐回等），並給出精確的**停損參考價格**。
"""

    # 1. 優先嘗試 Google GenAI SDK (google.genai)
    try:
        from google import genai
        client = genai.Client(api_key=key_to_use)
        # 嘗試標準別名
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e1:
        # 2. 次要嘗試 Google Generative AI SDK (google.generativeai)
        try:
            import google.generativeai as old_genai
            old_genai.configure(api_key=key_to_use)
            model = old_genai.GenerativeModel('gemini-1.5-flash')
            res = model.generate_content(prompt)
            return res.text
        except Exception as e2:
            # 3. 備援嘗試：使用無版本別名 gemini-flash-latest
            try:
                from google import genai
                client = genai.Client(api_key=key_to_use)
                response = client.models.generate_content(
                    model='gemini-flash-latest',
                    contents=prompt,
                )
                return response.text
            except Exception as e3:
                return f"❌ 呼叫 Gemini API 分析時發生錯誤: {str(e1)}"
