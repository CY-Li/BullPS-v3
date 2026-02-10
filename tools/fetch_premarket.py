import yfinance as yf
import json
from datetime import datetime

def get_premarket_info(tickers):
    results = {}
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        # Pre-market data is usually in 'info' or can be fetched via 'fast_info'
        info = stock.info
        results[ticker] = {
            "currentPrice": info.get("currentPrice") or info.get("regularMarketPrice"),
            "preMarketPrice": info.get("preMarketPrice"),
            "regularMarketPreviousClose": info.get("regularMarketPreviousClose"),
            "volume": info.get("volume"),
            "averageVolume": info.get("averageVolume")
        }
    return results

def get_vix():
    vix = yf.Ticker("^VIX")
    return vix.info.get("regularMarketPrice")

if __name__ == "__main__":
    stocks = ["AAPL", "AMZN", "MSFT"]
    data = {
        "stocks": get_premarket_info(stocks),
        "vix": get_vix(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    print(json.dumps(data, indent=2))
