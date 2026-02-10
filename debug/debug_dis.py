import yfinance as yf
from datetime import datetime

def check_dis():
    symbol = "DIS"
    expiry = "2026-03-06"
    short_strike = 100.0
    long_strike = 95.0
    
    t = yf.Ticker(symbol)
    try:
        current_price = t.history(period='1d')['Close'].iloc[-1]
        print(f"DIS Current Price: {current_price}")
        
        options = t.option_chain(expiry)
        puts = options.puts
        
        # 尋找 strikes
        s_row = puts[puts['strike'] == short_strike]
        l_row = puts[puts['strike'] == long_strike]
        
        print(f"Short Strike ({short_strike}) row:")
        print(s_row[['strike', 'bid', 'ask', 'lastPrice']])
        
        print(f"Long Strike ({long_strike}) row:")
        print(l_row[['strike', 'bid', 'ask', 'lastPrice']])
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    check_dis()
