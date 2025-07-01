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
import threading
import time
from typing import Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# 檔案路徑
WATCHLIST_PATH = Path(__file__).parent.parent / "stock_watchlist.json"
ANALYSIS_PATH = Path(__file__).parent.parent / "analysis_result.json"
STATIC_DIR = Path(__file__).parent.parent / "frontend" / "dist"

# 全局狀態變數
analysis_status = {
    "is_running": False,
    "current_stage": "",
    "progress": 0,
    "message": "",
    "start_time": None,
    "end_time": None,
    "error": None
}

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

# 設定台北時區
TZ_TAIPEI = pytz.timezone('Asia/Taipei')

def update_status(stage: str, progress: int, message: str):
    """更新分析狀態"""
    global analysis_status
    analysis_status.update({
        "current_stage": stage,
        "progress": progress,
        "message": message,
        "is_running": True
    })
    logger.info(f"Stage: {stage} - {message} ({progress}%)")

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
    """執行選擇權追蹤器和股票分析器，並回報詳細狀態"""
    global analysis_status
    
    try:
        # 初始化狀態
        analysis_status.update({
            "is_running": True,
            "current_stage": "",
            "progress": 0,
            "message": "",
            "start_time": datetime.now(TZ_TAIPEI).isoformat(),
            "end_time": None,
            "error": None
        })
        
        # 階段1: 數據收集中
        update_status("正在獲取股票列表...", 5, "數據收集中")
        time.sleep(1)
        
        # 執行選擇權追蹤器
        update_status("正在掃描選擇權交易量...", 10, "數據收集中")
        subprocess.run(["python", "options_volume_tracker_v2.py"], check=True)
        
        # 階段2: 排名篩選中
        update_status("正在篩選活躍股票...", 20, "排名篩選中")
        time.sleep(1)
        
        # 階段3: 監控清單更新中
        update_status("正在更新股票觀察池...", 30, "監控清單更新中")
        time.sleep(1)
        
        # 階段4: 數據獲取中
        update_status("正在獲取股票歷史數據...", 40, "數據獲取中")
        time.sleep(1)
        
        # 執行股票分析器
        update_status("正在計算技術指標...", 50, "技術指標計算中")
        subprocess.run(["python", "integrated_stock_analyzer.py"], check=True)
        
        # 階段5: 技術指標計算中
        update_status("正在計算技術指標...", 60, "技術指標計算中")
        time.sleep(1)
        
        # 階段6: 多頭訊號檢測中
        update_status("正在檢測多頭訊號...", 70, "多頭訊號檢測中")
        time.sleep(1)
        
        # 階段7: 趨勢反轉分析中
        update_status("正在分析趨勢反轉...", 80, "趨勢反轉分析中")
        time.sleep(1)
        
        # 階段8: 綜合評分中
        update_status("正在計算綜合評分...", 85, "綜合評分中")
        time.sleep(1)
        
        # 階段9: 信心度計算中
        update_status("正在計算信心度...", 90, "信心度計算中")
        time.sleep(1)
        
        # 階段10: 數據整合中
        update_status("正在整合分析結果...", 95, "數據整合中")
        time.sleep(1)
        
        # 階段11: 報告生成中
        update_status("正在生成分析報告...", 100, "報告生成中")
        time.sleep(1)
        
        # 完成
        analysis_status.update({
            "is_running": False,
            "current_stage": "完成",
            "progress": 100,
            "message": "分析完成",
            "end_time": datetime.now(TZ_TAIPEI).isoformat()
        })
        
        logger.info("Analysis completed successfully")
        
    except Exception as e:
        analysis_status.update({
            "is_running": False,
            "current_stage": "錯誤",
            "progress": 0,
            "message": f"分析失敗: {str(e)}",
            "end_time": datetime.now(TZ_TAIPEI).isoformat(),
            "error": str(e)
        })
        logger.error(f"Error running analysis: {e}")
        raise

scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Taipei'))

def scheduled_task():
    try:
        run_tracker_and_analyze()
    except Exception as e:
        logger.error(f"Error in scheduled task: {e}")

@app.on_event("startup")
def start_scheduler():
    # 每天早上6點（Asia/Taipei）執行
    scheduler.add_job(scheduled_task, CronTrigger(hour=6, minute=0))
    scheduler.start()

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(TZ_TAIPEI).isoformat(),
        "static_dir_exists": STATIC_DIR.exists(),
        "static_dir_path": str(STATIC_DIR),
        "files_in_static": os.listdir(STATIC_DIR) if STATIC_DIR.exists() else []
    }

@app.get("/api/analysis-status")
def get_analysis_status():
    """獲取當前分析狀態"""
    return analysis_status

@app.post("/api/run-now")
def run_now(background_tasks: BackgroundTasks):
    """觸發立即分析"""
    if analysis_status["is_running"]:
        return {"status": "already_running", "message": "分析正在進行中"}
    
    background_tasks.add_task(run_tracker_and_analyze)
    return {"status": "started", "message": "分析已開始"}

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