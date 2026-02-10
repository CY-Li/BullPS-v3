import yfinance as yf
import json

def get_pre_market_data(symbols):
    data = {}
    for symbol in symbols:
        ticker = yf.Ticker(symbol)
        # Getting pre-market info usually involves fast_info or looking at the last trading day's after-hours
        # yfinance info can be slow or inconsistent. Let's try basic info first.
        info = ticker.info
        data[symbol] = {
            "current_price": info.get("regularMarketPrice"),
            "pre_market_price": info.get("preMarketPrice"),
            "bid": info.get("bid"),
            "ask": info.get("ask"),
            "volume": info.get("regularMarketVolume"),
            "pre_market_volume": info.get("preMarketVolume")
        }
    return data

symbols = ["AAPL", "AMZN", "MSFT", "^VIX"]
results = get_pre_market_data(symbols)
print(json.dumps(results, indent=2))
