import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def check_live_premiums():
    # 推薦的標的
    recommendations = [
        {'symbol': 'JPM', 'short': 290, 'long': 285, 'target_expiry': '2026-03-13'},
        {'symbol': 'V', 'short': 310, 'long': 305, 'target_expiry': '2026-03-13'},
        {'symbol': 'MSFT', 'short': 380, 'long': 375, 'target_expiry': '2026-03-13'}
    ]
    
    print(f"--- 實時權利金獲取 (Time: {datetime.now().strftime('%H:%M:%S')}) ---")
    
    for rec in recommendations:
        symbol = rec['symbol']
        try:
            ticker = yf.Ticker(symbol)
            # 獲取到期日
            options = ticker.options
            if not options:
                print(f"{symbol}: 無法獲取到期日")
                continue
            
            # 找到最接近的到期日
            target = rec['target_expiry']
            best_date = min(options, key=lambda x: abs((datetime.strptime(x, '%Y-%m-%d') - datetime.strptime(target, '%Y-%m-%d')).days))
            
            chain = ticker.option_chain(best_date)
            puts = chain.puts
            
            # 獲取具體 Strike 的價格
            short_put = puts[abs(puts['strike'] - rec['short']) < 0.1]
            long_put = puts[abs(puts['strike'] - rec['long']) < 0.1]
            
            if short_put.empty or long_put.empty:
                # 找最接近的
                short_s = puts.iloc[(puts['strike'] - rec['short']).abs().argsort()[:1]]
                long_s = puts.iloc[(puts['strike'] - rec['long']).abs().argsort()[:1]]
            else:
                short_s = short_put
                long_s = long_put
                
            def get_mid(row):
                bid = row['bid'].values[0]
                ask = row['ask'].values[0]
                last = row['lastPrice'].values[0]
                # 如果買賣盤都在，取中間價；否則取最後成交價
                if bid > 0 and ask > 0:
                    return (bid + ask) / 2
                return last

            short_price = get_mid(short_s)
            long_price = get_mid(long_s)
            net_credit = short_price - long_price
            
            print(f"{symbol} ({best_date}):")
            print(f"  Strike: {short_s['strike'].values[0]} / {long_s['strike'].values[0]}")
            print(f"  Short Put Mid: ${short_price:.2f} (Bid: {short_s['bid'].values[0]} / Ask: {short_s['ask'].values[0]})")
            print(f"  Long Put Mid: ${long_price:.2f}")
            print(f"  Net Credit: ${net_credit:.2f}")
            print("-" * 30)
            
        except Exception as e:
            print(f"{symbol}: 錯誤 - {str(e)}")

if __name__ == "__main__":
    check_live_premiums()
