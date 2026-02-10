
import yfinance as yf
import json
from pathlib import Path

def check_profit():
    with open('BullPS-v3/monitored_stocks.json', 'r') as f:
        stocks = json.load(f)
    
    for stock in stocks:
        symbol = stock['symbol']
        ticker = yf.Ticker(symbol)
        price = ticker.fast_info['last_price']
        
        entry_price = stock.get('entry_price')
        short_strike = stock.get('short_strike')
        long_strike = stock.get('long_strike')
        entry_premium = stock.get('entry_premium')
        expiry = stock.get('expiry')
        
        print(f"Symbol: {symbol}")
        print(f"  Current Price: {price:.2f} | Short Strike: {short_strike}")
        
        try:
            chain = ticker.option_chain(expiry)
            puts = chain.puts
            short_put = puts[puts.strike == short_strike]
            long_put = puts[puts.strike == long_strike]
            
            if not short_put.empty and not long_put.empty:
                # Current mid price of spread
                curr_short = (short_put.iloc[0].bid + short_put.iloc[0].ask) / 2
                curr_long = (long_put.iloc[0].bid + long_put.iloc[0].ask) / 2
                curr_premium = curr_short - curr_long
                
                # Profit = Entry Premium - Current Premium
                profit = entry_premium - curr_premium
                profit_pct = profit / entry_premium
                
                print(f"  Entry Premium: {entry_premium:.2f}")
                print(f"  Current Premium: {curr_premium:.2f}")
                print(f"  Profit: {profit:.2f} ({profit_pct*100:.1f}%)")
            else:
                print("  [Error] Could not find specific strikes in option chain.")
        except Exception as e:
            print(f"  [Error] Failed to fetch options: {e}")
        print("-" * 20)

check_profit()
