import yfinance as yf
import pandas as pd

targets = ['AAPL', 'AMZN']
print("--- 盤中即時狀態檢查 ---")
for sym in targets:
    ticker = yf.Ticker(sym)
    df = ticker.history(period='1d', interval='1m')
    if df.empty:
        print(f"{sym}: 無法獲取數據")
        continue
    
    current_price = df['Close'].iloc[-1]
    open_price = df['Open'].iloc[0]
    day_low = df['Low'].min()
    change_pct = (current_price / open_price - 1) * 100
    
    # 這裡對比用戶的 Short Strike
    short_strike = 255 if sym == 'AAPL' else 235
    distance_to_strike = (current_price - short_strike) / short_strike * 100
    
    print(f"{sym}:")
    print(f"  現價: ${current_price:.2f} ({change_pct:+.2f}%)")
    print(f"  Short Strike: ${short_strike}")
    print(f"  距離履約價: {distance_to_strike:.2f}%")
    print(f"  今日低點: ${day_low:.2f}")
