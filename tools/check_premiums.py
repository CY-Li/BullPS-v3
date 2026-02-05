import yfinance as yf
import pandas as pd
from datetime import datetime

# 目標：獲取 2026-03-06 (或最接近) 的期權報價
targets = [
    {'symbol': 'FXI', 'short': 36.5, 'long': 31.5, 'date': '2026-03-06'},
    {'symbol': 'AAPL', 'short': 235.5, 'long': 230.5, 'date': '2026-03-06'},
    {'symbol': 'DIS', 'short': 103.0, 'long': 98.0, 'date': '2026-03-06'},
    {'symbol': 'F', 'short': 12.5, 'long': 7.5, 'date': '2026-03-06'}
]

def get_premium(symbol, short_strike, long_strike, expiry_date):
    try:
        ticker = yf.Ticker(symbol)
        # 獲取到期日列表
        options = ticker.options
        if not options:
             return None, "No options found"
             
        # 找到最接近的到期日
        target_date = min(options, key=lambda x: abs(pd.Timestamp(x) - pd.Timestamp(expiry_date)))
        
        chain = ticker.option_chain(target_date)
        puts = chain.puts
        
        # 尋找最接近的 Strike
        if puts.empty:
             return None, f"No puts found for date {target_date}"

        short_strike_real = min(puts['strike'], key=lambda x: abs(x - short_strike))
        long_strike_real = min(puts['strike'], key=lambda x: abs(x - long_strike))

        short_put = puts[puts['strike'] == short_strike_real]
        long_put = puts[puts['strike'] == long_strike_real]
        
        if short_put.empty or long_put.empty:
            return None, f"Strike not found for date {target_date}"
            
        # 優先使用 bid/ask 中間價，如果沒有則使用 lastPrice
        short_bid = short_put['bid'].iloc[0]
        short_ask = short_put['ask'].iloc[0]
        short_last = short_put['lastPrice'].iloc[0]
        
        long_bid = long_put['bid'].iloc[0]
        long_ask = long_put['ask'].iloc[0]
        long_last = long_put['lastPrice'].iloc[0]

        short_price = (short_bid + short_ask) / 2 if short_bid > 0 and short_ask > 0 else short_last
        long_price = (long_bid + long_ask) / 2 if long_bid > 0 and long_ask > 0 else long_last
        
        net_credit = short_price - long_price
        return net_credit, target_date, short_strike_real, long_strike_real
    except Exception as e:
        return None, str(e), 0, 0

print("估算權利金 (基於上週五收盤價):\n")
for t in targets:
    result = get_premium(t['symbol'], t['short'], t['long'], t['date'])
    # 解包回傳值 (相容舊代碼)
    if result and result[0] is not None:
        credit = result[0]
        actual_date = result[1]
        real_short = result[2]
        real_long = result[3]
        
        width = real_short - real_long
        # 防止除以零或負數風險 (極端情況)
        risk = width - credit
        if risk <= 0: risk = width 
        
        roi = (credit / risk) * 100
        print(f"{t['symbol']} (到期日 {actual_date}):")
        print(f"  建議點位: Short {real_short} / Long {real_long}")
        print(f"  預估權利金: ${credit*100:.2f} (每口)")
        print(f"  最大風險 (保證金): ${risk*100:.2f}")
        print(f"  潛在回報率 (ROI): {roi:.2f}%\n")
    else:
        # 處理錯誤訊息
        err_msg = result[1] if result else "Unknown Error"
        print(f"{t['symbol']}: 無法獲取數據 - {err_msg}\n")
