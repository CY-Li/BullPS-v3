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

# 使用統一的路徑管理器
try:
    from backend.path_manager import path_manager
    ANALYSIS_PATH = path_manager.get_analysis_path()
    MONITORED_STOCKS_PATH = path_manager.get_monitored_stocks_path()
    TRADE_HISTORY_PATH = path_manager.get_trade_history_path()
    logger.info(f"Using path_manager - Analysis: {ANALYSIS_PATH}, Monitored: {MONITORED_STOCKS_PATH}, Trade History: {TRADE_HISTORY_PATH}")
except ImportError as e:
    logger.warning(f"Failed to import path_manager: {e}, using fallback paths")
    # 回退到原始路徑邏輯
    if os.path.exists("/app/data"):
        ANALYSIS_PATH = Path("/app/data/analysis_result.json")
        MONITORED_STOCKS_PATH = Path("/app/data/monitored_stocks.json")
        TRADE_HISTORY_PATH = Path("/app/data/trade_history.json")
    else:
        ANALYSIS_PATH = BASE_DIR / "analysis_result.json"
        MONITORED_STOCKS_PATH = BASE_DIR / "backend" / "monitored_stocks.json"
        TRADE_HISTORY_PATH = BASE_DIR / "backend" / "trade_history.json"
    logger.info(f"Using fallback paths - Analysis: {ANALYSIS_PATH}, Monitored: {MONITORED_STOCKS_PATH}, Trade History: {TRADE_HISTORY_PATH}")

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
            try:
                file_path.write_text(json.dumps(default_content), encoding='utf-8')
            except (PermissionError, OSError) as e:
                logger.error(f"Cannot create file {file_path}: {e}")
                return
        else:
            # 檢查文件是否為有效 JSON
            content = file_path.read_text(encoding='utf-8').strip()
            if not content:
                logger.warning(f"File {file_path} is empty, initializing with default content")
                try:
                    file_path.write_text(json.dumps(default_content), encoding='utf-8')
                except (PermissionError, OSError) as e:
                    logger.error(f"Cannot write to file {file_path}: {e}")
                    return
            else:
                try:
                    json.loads(content)
                except json.JSONDecodeError:
                    logger.warning(f"File {file_path} contains invalid JSON, reinitializing")
                    try:
                        file_path.write_text(json.dumps(default_content), encoding='utf-8')
                    except (PermissionError, OSError) as e:
                        logger.error(f"Cannot write to file {file_path}: {e}")
                        return
    except Exception as e:
        logger.error(f"Error ensuring file {file_path}: {e}")
        try:
            file_path.write_text(json.dumps(default_content), encoding='utf-8')
        except (PermissionError, OSError) as write_error:
            logger.error(f"Cannot write to file {file_path}: {write_error}")

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
    try:
        from backend.path_manager import path_manager
        path_info = path_manager.get_info()
    except Exception as e:
        path_info = {
            "error": f"Path manager failed: {e}",
            "fallback_paths": {
                "analysis": str(ANALYSIS_PATH),
                "monitored_stocks": str(MONITORED_STOCKS_PATH),
                "trade_history": str(TRADE_HISTORY_PATH)
            },
            "fallback_exists": {
                "analysis": ANALYSIS_PATH.exists(),
                "monitored_stocks": MONITORED_STOCKS_PATH.exists(),
                "trade_history": TRADE_HISTORY_PATH.exists()
            }
        }

    return {
        "status": "healthy",
        "timestamp": datetime.now(TZ_TAIPEI).isoformat(),
        "path_manager_info": path_info,
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

@app.get("/api/debug-files")
def debug_files():
    """調試端點：檢查所有可能的文件位置"""
    import glob

    debug_info = {
        "current_paths": {
            "analysis": str(ANALYSIS_PATH),
            "monitored_stocks": str(MONITORED_STOCKS_PATH),
            "trade_history": str(TRADE_HISTORY_PATH)
        },
        "file_exists": {
            "analysis": ANALYSIS_PATH.exists(),
            "monitored_stocks": MONITORED_STOCKS_PATH.exists(),
            "trade_history": TRADE_HISTORY_PATH.exists()
        },
        "file_sizes": {},
        "all_json_files": []
    }

    # 檢查文件大小
    for name, path in [("analysis", ANALYSIS_PATH), ("monitored_stocks", MONITORED_STOCKS_PATH), ("trade_history", TRADE_HISTORY_PATH)]:
        try:
            debug_info["file_sizes"][name] = path.stat().st_size if path.exists() else 0
        except Exception as e:
            debug_info["file_sizes"][name] = f"Error: {e}"

    # 查找所有 JSON 文件
    search_patterns = [
        "/app/**/*.json",
        "/app/data/*.json",
        "/app/backend/*.json",
        "*.json",
        "backend/*.json"
    ]

    for pattern in search_patterns:
        try:
            files = glob.glob(pattern, recursive=True)
            for file in files:
                if file not in debug_info["all_json_files"]:
                    try:
                        size = os.path.getsize(file)
                        debug_info["all_json_files"].append(f"{file} ({size} bytes)")
                    except:
                        debug_info["all_json_files"].append(f"{file} (size unknown)")
        except Exception as e:
            debug_info["all_json_files"].append(f"Error searching {pattern}: {e}")

    return debug_info



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
            except (PermissionError, OSError) as create_error:
                logger.error(f"Permission denied creating analysis file: {create_error}")
                return {"result": [], "error": "Analysis file not found and permission denied to create"}
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
                try:
                    MONITORED_STOCKS_PATH.write_text("[]", encoding='utf-8')
                except (PermissionError, OSError) as e:
                    logger.error(f"Cannot write to monitored_stocks.json: {e}")
                return []

            data = json.loads(content)
            return data
        else:
            # 文件不存在，創建空數組
            logger.warning("monitored_stocks.json does not exist, creating with empty array")
            try:
                MONITORED_STOCKS_PATH.write_text("[]", encoding='utf-8')
            except (PermissionError, OSError) as e:
                logger.error(f"Cannot create monitored_stocks.json: {e}")
            return []
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in monitored stocks: {e}")
        # JSON 格式錯誤，重新初始化為空數組
        try:
            MONITORED_STOCKS_PATH.write_text("[]", encoding='utf-8')
        except (PermissionError, OSError) as write_error:
            logger.error(f"Cannot write to monitored_stocks.json: {write_error}")
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

@app.post("/api/fix-permissions")
def fix_permissions():
    """修復數據文件權限（用於 Zeabur 部署後的權限問題）"""
    try:
        import stat
        import subprocess

        results = []
        files_to_fix = [ANALYSIS_PATH, MONITORED_STOCKS_PATH, TRADE_HISTORY_PATH]

        # 首先嘗試修復目錄權限
        data_dir = ANALYSIS_PATH.parent
        try:
            # 使用 chmod 修復目錄權限
            subprocess.run(["chmod", "-R", "777", str(data_dir)], check=False)
            results.append(f"✅ 嘗試修復目錄權限: {data_dir}")
        except Exception as e:
            results.append(f"❌ 修復目錄權限失敗: {e}")

        for file_path in files_to_fix:
            if file_path.exists():
                try:
                    # 檢查當前權限
                    current_stat = file_path.stat()
                    current_mode = stat.filemode(current_stat.st_mode)

                    # 嘗試修復權限（設為可讀寫）
                    file_path.chmod(0o664)

                    results.append({
                        "file": str(file_path),
                        "status": "success",
                        "previous_mode": current_mode,
                        "new_mode": "rw-rw-r--",
                        "message": "權限修復成功"
                    })

                except PermissionError as e:
                    results.append({
                        "file": str(file_path),
                        "status": "permission_denied",
                        "error": str(e),
                        "message": "權限不足，無法修復"
                    })
                except Exception as e:
                    results.append({
                        "file": str(file_path),
                        "status": "error",
                        "error": str(e),
                        "message": "修復失敗"
                    })
            else:
                results.append({
                    "file": str(file_path),
                    "status": "not_found",
                    "message": "文件不存在"
                })

        # 測試寫入權限
        test_results = []
        for file_path in files_to_fix:
            if file_path.exists():
                try:
                    # 嘗試寫入測試
                    content = file_path.read_text(encoding='utf-8')
                    file_path.write_text(content, encoding='utf-8')
                    test_results.append({
                        "file": str(file_path),
                        "writable": True,
                        "message": "寫入測試成功"
                    })
                except Exception as e:
                    test_results.append({
                        "file": str(file_path),
                        "writable": False,
                        "error": str(e),
                        "message": "寫入測試失敗"
                    })

        return {
            "status": "completed",
            "timestamp": datetime.now(TZ_TAIPEI).isoformat(),
            "permission_fixes": results,
            "write_tests": test_results,
            "summary": {
                "total_files": len(files_to_fix),
                "fixed": len([r for r in results if r["status"] == "success"]),
                "failed": len([r for r in results if r["status"] != "success"]),
                "writable": len([t for t in test_results if t["writable"]])
            }
        }

    except Exception as e:
        logger.error(f"Error in fix_permissions: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"權限修復失敗: {str(e)}"}
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
