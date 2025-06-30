from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import json
import math
import yfinance as yf
from pathlib import Path
from datetime import datetime

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 修正檔案路徑 - 檔案在 backend 目錄中
WATCHLIST_PATH = Path("stock_watchlist.json")
ANALYSIS_PATH = Path("analysis_result.json")


def clean_nans(obj):
    """遞迴清理物件中的 NaN 值，轉換為 None"""
    if isinstance(obj, float) and math.isnan(obj):
        return None
    elif isinstance(obj, dict):
        return {k: clean_nans(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nans(x) for x in obj]
    else:
        return obj


def get_stock_price(symbol: str):
    """使用 yfinance 取得股票現價"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        price = info.get('regularMarketPrice')
        if price and not math.isnan(price):
            return price
        return None
    except Exception as e:
        print(f"Error getting price for {symbol}: {e}")
        return None


def run_tracker_and_analyze():
    # 1. 執行 options_volume_tracker_v2.py（在根目錄）
    subprocess.run(["python", "../options_volume_tracker_v2.py"], check=True)
    # 2. 執行 integrated_stock_analyzer.py（在根目錄）
    subprocess.run(["python", "../integrated_stock_analyzer.py"], check=True)

@app.on_event("startup")
def schedule_daily_task():
    import threading, time
    def daily_job():
        while True:
            now = datetime.now()
            # 每天凌晨1點自動執行
            if now.hour == 1 and now.minute == 0:
                run_tracker_and_analyze()
                time.sleep(60)
            time.sleep(30)
    threading.Thread(target=daily_job, daemon=True).start()

@app.post("/api/run-now")
def run_now(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_tracker_and_analyze)
    return {"status": "started"}

@app.get("/api/watchlist")
def get_watchlist():
    if WATCHLIST_PATH.exists():
        return json.loads(WATCHLIST_PATH.read_text(encoding='utf-8'))
    return {"stocks": [], "settings": {}}

@app.get("/api/analysis")
def get_analysis():
    try:
        if ANALYSIS_PATH.exists():
            data = json.loads(ANALYSIS_PATH.read_text(encoding='utf-8'))
            # 清理 NaN 值
            cleaned_data = clean_nans(data)
            print(f"Analysis data loaded: {len(cleaned_data.get('result', []))} stocks")  # 調試用
            return cleaned_data
        else:
            print(f"Analysis file not found at: {ANALYSIS_PATH.absolute()}")  # 調試用
            return {"result": None, "error": "Analysis file not found"}
    except Exception as e:
        print(f"Error loading analysis: {e}")  # 調試用
        return {"result": None, "error": str(e)}

@app.get("/api/stock-prices")
def get_stock_prices():
    """取得所有股票的現價"""
    try:
        if WATCHLIST_PATH.exists():
            watchlist_data = json.loads(WATCHLIST_PATH.read_text(encoding='utf-8'))
            stocks = watchlist_data.get('stocks', [])
            
            prices = {}
            for symbol in stocks:
                price = get_stock_price(symbol)
                prices[symbol] = price
            
            return {"prices": prices}
        else:
            return {"prices": {}}
    except Exception as e:
        print(f"Error getting stock prices: {e}")
        return {"prices": {}, "error": str(e)}

@app.get("/api/stock-price/{symbol}")
def get_single_stock_price(symbol: str):
    """取得單一股票的現價"""
    try:
        price = get_stock_price(symbol)
        return {"symbol": symbol, "price": price}
    except Exception as e:
        print(f"Error getting price for {symbol}: {e}")
        return {"symbol": symbol, "price": None, "error": str(e)} 