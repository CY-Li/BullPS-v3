import sys
from pathlib import Path

# 將專案根目錄添加到 Python 路徑
# 確保即使直接運行 main.py 也能找到 backend 模組
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import subprocess
import json
import math

from pathlib import Path
from datetime import datetime
import os
import logging
import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時執行
    # 每天早上6點（Asia/Taipei）執行
    scheduler.add_job(scheduled_task, CronTrigger(hour=6, minute=0))
    scheduler.start()
    logger.info("Scheduler started")

    yield

    # 關閉時執行
    scheduler.shutdown()
    logger.info("Scheduler shutdown")

app = FastAPI(lifespan=lifespan)

# 檔案路徑
BASE_DIR = Path(__file__).parent.parent
ANALYSIS_PATH = BASE_DIR / "analysis_result.json"
MONITORED_STOCKS_PATH = BASE_DIR / "backend" / "monitored_stocks.json"
TRADE_HISTORY_PATH = BASE_DIR / "backend" / "trade_history.json"
STATIC_DIR = BASE_DIR / "frontend" / "dist"


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



def run_stock_analysis():
    """執行股票分析器，並回報詳細狀態"""
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
        
        # 調整工作目錄到專案根目錄
        os.chdir(BASE_DIR)
        
        # 階段1: 數據獲取與分析
        update_status("正在分析股票...", 30, "數據分析中")
        subprocess.run(["python", "integrated_stock_analyzer.py"], check=True, cwd=BASE_DIR)
        
        # 階段2.5: 比對並更新監控中的股票分析快照
        update_status("正在比對並更新監控股票分析快照...", 65, "數據比對中")
        # 直接調用 portfolio_manager 中的函數，而不是作為獨立進程
        from backend.portfolio_manager import compare_and_update_monitored_stocks
        compare_and_update_monitored_stocks()
        
        # 階段3: 投資組合管理
        update_status("正在檢查持倉與更新交易紀錄...", 80, "投資組合管理中")
        subprocess.run(["python", "backend/portfolio_manager.py"], check=True, cwd=BASE_DIR)
        
        # 階段4: 報告生成中
        update_status("正在生成最終報告...", 95, "報告生成中")
        time.sleep(1)
        
        # 完成
        analysis_status.update({
            "is_running": False,
            "current_stage": "完成",
            "progress": 100,
            "message": "分析與管理完成",
            "end_time": datetime.now(TZ_TAIPEI).isoformat()
        })
        
        logger.info("Analysis and portfolio management completed successfully")
        
    except Exception as e:
        analysis_status.update({
            "is_running": False,
            "current_stage": "錯誤",
            "progress": 0,
            "message": f"執行失敗: {str(e)}",
            "end_time": datetime.now(TZ_TAIPEI).isoformat(),
            "error": str(e)
        })
        logger.error(f"Error during execution: {e}")
        raise

scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Taipei'))

def scheduled_task():
    try:
        run_stock_analysis()
    except Exception as e:
        logger.error(f"Error in scheduled task: {e}")



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
    
    background_tasks.add_task(run_stock_analysis)
    return {"status": "started", "message": "分析已開始"}



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

@app.get("/api/monitored-stocks")
def get_monitored_stocks():
    try:
        if MONITORED_STOCKS_PATH.exists():
            data = json.loads(MONITORED_STOCKS_PATH.read_text(encoding='utf-8'))
            return data
        return []
    except Exception as e:
        logger.error(f"Error reading monitored stocks: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to read monitored stocks"}
        )

@app.get("/api/trade-history")
def get_trade_history():
    try:
        if TRADE_HISTORY_PATH.exists():
            data = json.loads(TRADE_HISTORY_PATH.read_text(encoding='utf-8'))
            return data
        return []
    except Exception as e:
        logger.error(f"Error reading trade history: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to read trade history"}
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

if __name__ == "__main__":
    try:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8080)
    except ImportError:
        logger.error("Uvicorn is not installed. Please run 'pip install uvicorn' to start the server.")
