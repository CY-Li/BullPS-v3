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

# 動態檢測文件路徑
def get_file_path(filename):
    """動態檢測文件的實際位置"""
    # 可能的路徑列表（按優先級排序）
    possible_paths = [
        Path("/app/data") / filename,  # 容器數據目錄
        Path("/app") / filename,       # 容器根目錄
        BASE_DIR / filename,           # 本地根目錄
        BASE_DIR / "backend" / filename  # 本地backend目錄
    ]

    for path in possible_paths:
        if path.exists():
            logger.info(f"Found {filename} at: {path}")
            return path

    # 如果都不存在，使用默認路徑
    if os.path.exists("/app/data"):
        default_path = Path("/app/data") / filename
    else:
        default_path = BASE_DIR / "backend" / filename if filename != "analysis_result.json" else BASE_DIR / filename

    logger.warning(f"File {filename} not found, using default path: {default_path}")
    return default_path

# 設置文件路徑
ANALYSIS_PATH = get_file_path("analysis_result.json")
MONITORED_STOCKS_PATH = get_file_path("monitored_stocks.json")
TRADE_HISTORY_PATH = get_file_path("trade_history.json")

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

# 確保檔案存在並格式正確
def ensure_json_file_exists(file_path, default_content):
    """確保 JSON 文件存在且格式正確"""
    try:
        if not file_path.exists():
            logger.warning(f"File not found at {file_path}, creating with default content")
            file_path.write_text(json.dumps(default_content), encoding='utf-8')
        else:
            # 檢查文件是否為有效 JSON
            content = file_path.read_text(encoding='utf-8').strip()
            if not content:
                logger.warning(f"File {file_path} is empty, initializing with default content")
                file_path.write_text(json.dumps(default_content), encoding='utf-8')
            else:
                try:
                    json.loads(content)
                except json.JSONDecodeError:
                    logger.warning(f"File {file_path} contains invalid JSON, reinitializing")
                    file_path.write_text(json.dumps(default_content), encoding='utf-8')
    except Exception as e:
        logger.error(f"Error ensuring file {file_path}: {e}")
        file_path.write_text(json.dumps(default_content), encoding='utf-8')

# 初始化所有必要的 JSON 文件
ensure_json_file_exists(ANALYSIS_PATH, {"result": []})
ensure_json_file_exists(MONITORED_STOCKS_PATH, [])
ensure_json_file_exists(TRADE_HISTORY_PATH, [])

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
        "environment": "container" if os.path.exists("/app/data") else "local",
        "file_paths": {
            "analysis_path": str(ANALYSIS_PATH),
            "monitored_stocks_path": str(MONITORED_STOCKS_PATH),
            "trade_history_path": str(TRADE_HISTORY_PATH)
        },
        "file_exists": {
            "analysis_file": ANALYSIS_PATH.exists(),
            "monitored_stocks_file": MONITORED_STOCKS_PATH.exists(),
            "trade_history_file": TRADE_HISTORY_PATH.exists()
        },
        "data_dir_exists": os.path.exists("/app/data"),
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

    logger.info("Manual analysis triggered via API")
    background_tasks.add_task(run_stock_analysis)
    return {"status": "started", "message": "分析已開始"}

@app.get("/api/trigger-analysis")
def trigger_analysis_get(background_tasks: BackgroundTasks):
    """GET方式觸發分析（用於測試）"""
    if analysis_status["is_running"]:
        return {"status": "already_running", "message": "分析正在進行中"}

    logger.info("Analysis triggered via GET endpoint")
    background_tasks.add_task(run_stock_analysis)
    return {"status": "started", "message": "分析已開始"}



@app.get("/api/analysis")
def get_analysis():
    try:
        logger.info(f"Checking analysis file at: {ANALYSIS_PATH}")
        logger.info(f"File exists: {ANALYSIS_PATH.exists()}")

        if ANALYSIS_PATH.exists():
            content = ANALYSIS_PATH.read_text(encoding='utf-8').strip()
            if not content:
                logger.warning("Analysis file is empty")
                return {"result": [], "error": "Analysis file is empty"}

            data = json.loads(content)
            cleaned_data = clean_nans(data)
            logger.info(f"Analysis data loaded successfully, result count: {len(cleaned_data.get('result', []))}")
            return cleaned_data
        else:
            logger.warning(f"Analysis file not found at: {ANALYSIS_PATH}")
            # 嘗試創建空的分析結果文件
            try:
                ANALYSIS_PATH.parent.mkdir(parents=True, exist_ok=True)
                empty_result = {"result": [], "timestamp": "", "analysis_date": "", "total_stocks": 0, "analyzed_stocks": 0}
                ANALYSIS_PATH.write_text(json.dumps(empty_result), encoding='utf-8')
                logger.info(f"Created empty analysis file at: {ANALYSIS_PATH}")
                return empty_result
            except Exception as create_error:
                logger.error(f"Failed to create analysis file: {create_error}")
                return {"result": [], "error": "Analysis file not found and could not be created"}
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in analysis file: {e}")
        return {"result": [], "error": "Invalid JSON in analysis file"}
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
            content = MONITORED_STOCKS_PATH.read_text(encoding='utf-8').strip()
            if not content:
                # 文件為空，創建空數組
                logger.warning("monitored_stocks.json is empty, initializing with empty array")
                MONITORED_STOCKS_PATH.write_text("[]", encoding='utf-8')
                return []

            data = json.loads(content)
            return data
        else:
            # 文件不存在，創建空數組
            logger.warning("monitored_stocks.json does not exist, creating with empty array")
            MONITORED_STOCKS_PATH.write_text("[]", encoding='utf-8')
            return []
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in monitored stocks: {e}")
        # JSON 格式錯誤，重新初始化為空數組
        MONITORED_STOCKS_PATH.write_text("[]", encoding='utf-8')
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
