import yfinance as yf
from datetime import datetime
import pandas as pd

def get_real_premium(symbol, short_strike, long_strike, expiry_date_str):
    """
    獲取即時(或延遲)權利金
    """
    try:
        ticker = yf.Ticker(symbol)
        options = ticker.options
        if not options:
            return None, "No options"
        
        # 轉換日期格式
        target_date_obj = datetime.strptime(expiry_date_str, '%Y-%m-%d')
        
        # 尋找最接近的到期日 (必須 >= target_date_obj)
        valid_dates = [d for d in options if datetime.strptime(d, '%Y-%m-%d') >= target_date_obj]
        if not valid_dates:
             # 如果沒有未來的，找最後一個
             valid_dates = options[-1:]
        
        # 找最接近的一週
        best_date = min(valid_dates, key=lambda x: abs((datetime.strptime(x, '%Y-%m-%d') - target_date_obj).days))
        
        chain = ticker.option_chain(best_date)
        puts = chain.puts
        
        if puts.empty:
            return None, f"No puts for {best_date}"

        # 尋找 Strike
        # 允許 0.5 的誤差
        short_put = puts[abs(puts['strike'] - short_strike) < 0.5]
        long_put = puts[abs(puts['strike'] - long_strike) < 0.5]
        
        # 如果找不到精確的，找最接近的
        if short_put.empty:
            short_strike_real = puts.iloc[(puts['strike'] - short_strike).abs().argsort()[:1]]['strike'].values[0]
            short_put = puts[puts['strike'] == short_strike_real]
        else:
            short_strike_real = short_put['strike'].values[0]
            
        if long_put.empty:
            long_strike_real = puts.iloc[(puts['strike'] - long_strike).abs().argsort()[:1]]['strike'].values[0]
            long_put = puts[puts['strike'] == long_strike_real]
        else:
            long_strike_real = long_put['strike'].values[0]

        # 獲取價格
        def get_price(row):
            if row.empty: return 0.0
            bid = row['bid'].values[0]
            ask = row['ask'].values[0]
            last = row['lastPrice'].values[0]
            if bid > 0 and ask > 0:
                return (bid + ask) / 2
            return last

        short_price = get_price(short_put)
        long_price = get_price(long_put)
        net_credit = short_price - long_price
        
        return {
            'credit': net_credit,
            'expiry': best_date,
            'short_strike': short_strike_real,
            'long_strike': long_strike_real,
            'short_price': short_price,
            'long_price': long_price
        }, None

    except Exception as e:
        return None, str(e)
