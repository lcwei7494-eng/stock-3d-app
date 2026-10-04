# 🇹🇼 臺灣證券交易所標準升降單位 (Tick Size) 規範
def get_tw_tick_size(price):
    if price < 10: return 0.01
    elif price < 50: return 0.05
    elif price < 100: return 0.1
    elif price < 500: return 0.5
    elif price < 1000: return 1.0  # 500~1000元檔位為 1元
    else: return 5.0

def calculate_tw_limit_prices(ref_price):
    if ref_price <= 0: return 0, 0
    
    # 1. 漲停價：昨收 * 1.10，向下對齊 Tick
    raw_up = ref_price * 1.10
    tick_up = get_tw_tick_size(raw_up)
    limit_up = int(raw_up / tick_up) * tick_up
    
    # 2. 跌停價：昨收 * 0.90，向上對齊 Tick
    raw_down = ref_price * 0.90
    tick_down = get_tw_tick_size(raw_down)
    limit_down = int(raw_down / tick_down + 0.9999) * tick_down
    
    # 格式化顯示（小於500元顯示小數點，500元以上顯示整數）
    fmt_up = f"{limit_up:.2f}".rstrip('0').rstrip('.') if limit_up < 500 else f"{int(limit_up)}"
    fmt_down = f"{limit_down:.2f}".rstrip('0').rstrip('.') if limit_down < 500 else f"{int(limit_down)}"
    
    return fmt_up, fmt_down
