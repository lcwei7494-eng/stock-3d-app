import numpy as np
import pandas as pd

def calculate_three_lines_strategy_advanced(df):
    """
    張宇明「三線多空 + 防誘多假突破」進階量化篩選模組
    輸入 DataFrame 必需欄位: ['close', 'open', 'high', 'low', 'volume', 'institutional_net_buy'][cite: 1]
    """
    data = df.copy()

    # 1. 趨勢線 (Trend Line) & 線型長度/力道強度[cite: 1]
    data['ema_20'] = data['close'].ewm(span=20, adjust=False).mean()
    data['ema_60'] = data['close'].ewm(span=60, adjust=False).mean()
    
    # 趨勢線斜率（力道長度判定）[cite: 1]
    data['ema20_slope'] = data['ema_20'].diff(3)
    data['trend_line'] = np.where(
        (data['ema_20'] > data['ema_60']) & (data['close'] > data['ema_20']) & (data['ema20_slope'] > 0),
        1, -1
    ) #

    # 2. 籌碼線 (Chip Line) & 主力真吃貨驗證 (防散戶追價偽利多)
    if 'institutional_net_buy' not in data.columns:
        # 若缺乏法人數據，以 K 線實體量價評估主力資金進出
        data['institutional_net_buy'] = (data['close'] - data['open']) / (data['high'] - data['low'] + 1e-6) * data['volume']

    data['chip_cum_10'] = data['institutional_net_buy'].rolling(window=10).sum()
    data['chip_ma_10'] = data['chip_cum_10'].rolling(window=10).mean()
    data['chip_line'] = np.where(
        (data['chip_cum_10'] > data['chip_ma_10']) & (data['chip_cum_10'] > 0),
        1, -1
    ) #

    # 3. 動能線 (Momentum Line)：RSI 14[cite: 1]
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    data['rsi_14'] = 100 - (100 / (1 + rs))
    data['rsi_14'] = data['rsi_14'].fillna(50)
    data['momentum_line'] = np.where(data['rsi_14'] > 50, 1, -1) #[cite: 1, 2]

    # 4. K 線突破型態：帶量長紅或跳空缺口[cite: 1]
    data['vol_ma5'] = data['volume'].rolling(5).mean()
    data['is_volume_breakout'] = data['volume'] >= (data['vol_ma5'] * 1.5) # 量增 1.5 倍以上[cite: 1]
    data['is_red_candle'] = (data['close'] - data['open']) / data['open'] >= 0.025 # 實體漲幅 >= 2.5%[cite: 1]
    data['is_gap_up'] = data['open'] > data['high'].shift(1) # 跳空缺口[cite: 1]
    data['kline_breakout'] = data['is_volume_breakout'] & (data['is_red_candle'] | data['is_gap_up']) #[cite: 1]

    # 5. 均線糾結判定 (5MA, 10MA, 20MA, 60MA 集中度 < 3.5%)[cite: 3]
    data['ma_5'] = data['close'].rolling(5).mean()
    data['ma_10'] = data['close'].rolling(10).mean()
    data['ma_20'] = data['close'].rolling(20).mean()
    data['ma_60'] = data['close'].rolling(60).mean()
    
    ma_max = data[['ma_5', 'ma_10', 'ma_20', 'ma_60']].max(axis=1)
    ma_min = data[['ma_5', 'ma_10', 'ma_20', 'ma_60']].min(axis=1)
    data['ma_tangle_ratio'] = (ma_max - ma_min) / (ma_min + 1e-9) * 100
    data['is_tangled'] = data['ma_tangle_ratio'] <= 3.5 #[cite: 3]

    # 6. 三線總分與精確訊號判斷[cite: 1, 2]
    data['total_score'] = data['trend_line'] + data['chip_line'] + data['momentum_line'] #[cite: 1]

    # 具體條件匹配
    conditions = [
        # (1) 真突破起漲：三線全多 + 帶量長紅/跳空 + 均線先前有糾結[cite: 1, 2, 3]
        (data['total_score'] == 3) & data['kline_breakout'] & (data['is_tangled'].shift(1) | data['is_tangled'].shift(2)),
        
        # (2) 偽利多/誘多警訊：股價衝高突破，但籌碼線未同步（主力倒貨）[cite: 1, 2]
        (data['total_score'] == 1) & (data['trend_line'] == 1) & (data['momentum_line'] == 1) & (data['chip_line'] == -1),
        
        # (3) 標準三線翻多[cite: 1, 2]
        (data['total_score'] == 3),
        
        # (4) 三線翻空/出場[cite: 1, 2, 3]
        (data['total_score'] == -3) | ((data['total_score'] < 0) & (data['close'] < data['ma_20']))
    ]
    
    choices = [
        "🔥 真突破起漲 (均線糾結+帶量長紅+三線共振)",
        "⚠️ 偽利多誘多警訊 (股價突破但籌碼未跟進/主力倒貨)",
        "🟢 三線翻多 (強勢多頭架構)",
        "🔴 三線轉空 (架構破壞/果斷離場)"
    ]
    
    data['signal'] = np.select(conditions, choices, default="🟡 盤整觀望/多空拉鋸")

    return data
