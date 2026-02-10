import yfinance as yf
import json

symbols = ["DIS", "IWM", "AMZN"]
data = yf.download(symbols, period="1d", interval="1m")
current_prices = {}

for sym in symbols:
    try:
        # Get the last valid price (iloc[-1])
        # yf.download returns a MultiIndex DataFrame if multiple symbols
        if len(symbols) > 1:
            price = data['Close'][sym].iloc[-1]
        else:
            price = data['Close'].iloc[-1]
        current_prices[sym] = float(price)
    except Exception as e:
        print(f"Error fetching {sym}: {e}")

print(json.dumps(current_prices))
