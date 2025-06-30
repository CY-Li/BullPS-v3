from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, JSONResponse
import subprocess
import json
import math
import yfinance as yf
from pathlib import Path
from datetime import datetime
import os
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# 檔案路徑
WATCHLIST_PATH = Path(__file__).parent.parent / "stock_watchlist.json"
ANALYSIS_PATH = Path(__file__).parent.parent / "analysis_result.json"
STATIC_DIR = Path(__file__).parent.parent / "frontend" / "dist"

# 確保檔案存在
if not WATCHLIST_PATH.exists():
    logger.warning(f"Watchlist file not found at {WATCHLIST_PATH}, creating empty one")
    WATCHLIST_PATH.write_text(json.dumps({"stocks": [], "settings": {}}), encoding='utf-8')

if not ANALYSIS_PATH.exists():
    logger.warning(f"Analysis file not found at {ANALYSIS_PATH}, creating empty one")
    ANALYSIS_PATH.write_text(json.dumps({"result": []}), encoding='utf-8')

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def clean_nans(obj):
    if isinstance(obj, float) and math.isnan(obj):
        return None
    elif isinstance(obj, dict):
        return {k: clean_nans(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nans(x) for x in obj]
    else:
        return obj

def get_stock_price(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        price = info.get('regularMarketPrice')
        if price and not math.isnan(price):
            return price
        return None
    except Exception as e:
        logger.error(f"Error getting price for {symbol}: {e}")
        return None

def run_tracker_and_analyze():
    try:
        subprocess.run(["python", "options_volume_tracker_v2.py"], check=True)
        subprocess.run(["python", "integrated_stock_analyzer.py"], check=True)
    except Exception as e:
        logger.error(f"Error running analysis: {e}")
        raise

@app.on_event("startup")
def schedule_daily_task():
    import threading, time
    def daily_job():
        while True:
            try:
                now = datetime.now()
                if now.hour == 1 and now.minute == 0:
                    run_tracker_and_analyze()
                    time.sleep(60)
                time.sleep(30)
            except Exception as e:
                logger.error(f"Error in daily job: {e}")
                time.sleep(300)  # 錯誤後等待5分鐘再試
    threading.Thread(target=daily_job, daemon=True).start()

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "static_dir_exists": STATIC_DIR.exists(),
        "static_dir_path": str(STATIC_DIR),
        "files_in_static": os.listdir(STATIC_DIR) if STATIC_DIR.exists() else []
    }

@app.post("/api/run-now")
def run_now(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_tracker_and_analyze)
    return {"status": "started"}

@app.get("/api/watchlist")
def get_watchlist():
    try:
        if WATCHLIST_PATH.exists():
            return json.loads(WATCHLIST_PATH.read_text(encoding='utf-8'))
        return {"stocks": [], "settings": {}}
    except Exception as e:
        logger.error(f"Error reading watchlist: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to read watchlist"}
        )

@app.get("/api/analysis")
def get_analysis():
    try:
        if ANALYSIS_PATH.exists():
            data = json.loads(ANALYSIS_PATH.read_text(encoding='utf-8'))
            cleaned_data = clean_nans(data)
            return cleaned_data
        else:
            return {"result": None, "error": "Analysis file not found"}
    except Exception as e:
        logger.error(f"Error reading analysis: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to read analysis"}
        )

@app.get("/api/stock-prices")
def get_stock_prices():
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
        logger.error(f"Error getting stock prices: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to get stock prices"}
        )

@app.get("/api/stock-price/{symbol}")
def get_single_stock_price(symbol: str):
    try:
        price = get_stock_price(symbol)
        return {"symbol": symbol, "price": price}
    except Exception as e:
        logger.error(f"Error getting price for {symbol}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get price for {symbol}"}
        )

# 靜態檔案 - 放在 API 路由之後
if STATIC_DIR.exists():
    logger.info(f"Mounting static files from {STATIC_DIR}")
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
else:
    logger.error(f"Static directory not found at {STATIC_DIR}")

# SPA fallback
@app.middleware("http")
async def spa_fallback(request: Request, call_next):
    if request.url.path.startswith("/api"):
        return await call_next(request)
    response = await call_next(request)
    if response.status_code == 404:
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            logger.info(f"Serving index.html for path: {request.url.path}")
            return FileResponse(index_path)
        else:
            logger.error(f"Index file not found at {index_path}")
            return JSONResponse(
                status_code=404,
                content={"error": "Frontend not built"}
            )
    return response 