import sys
from pathlib import Path

# 將專案根目錄添加到 Python 路徑
# 確保即使直接運行 main.py 也能找到 backend 模組
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, BackgroundTasks, Request, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, JSONResponse, Response
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
    if os.path.exists("/app"):
        ANALYSIS_PATH = Path("/app/analysis_result.json")
        MONITORED_STOCKS_PATH = Path("/app/monitored_stocks.json")
        TRADE_HISTORY_PATH = Path("/app/trade_history.json")
    else:
        ANALYSIS_PATH = BASE_DIR / "analysis_result.json"
        MONITORED_STOCKS_PATH = BASE_DIR / "monitored_stocks.json"
        TRADE_HISTORY_PATH = BASE_DIR / "trade_history.json"
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
        subprocess.run(["python", "core/integrated_stock_analyzer.py"], check=True, cwd=BASE_DIR)
        
        # 階段2.5: 比對並更新監控中的股票分析快照
        update_status("正在比對並更新監控股票分析快照...", 65, "數據比對中")
        # 直接調用 portfolio_manager 中的函數，而不是作為獨立進程
        from backend.portfolio_manager import compare_and_update_monitored_stocks
        compare_and_update_monitored_stocks()
        
        # 階段3: 投資組合管理
        update_status("正在檢查持倉與更新交易紀錄...", 80, "投資組合管理中")
        subprocess.run(["python", "backend/portfolio_manager.py"], check=True, cwd=BASE_DIR, env=os.environ)
        
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
        "/app/*.json",
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
            # If data is a dictionary, convert its values to a list
            if isinstance(data, dict):
                return list(data.values())
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

from collections import defaultdict

@app.get("/api/trade-history")
def get_trade_history():
    try:
        if not TRADE_HISTORY_PATH.exists():
            return {"trades": [], "yearly_summary": {}, "monthly_summary": {}}

        content = TRADE_HISTORY_PATH.read_text(encoding='utf-8').strip()
        if not content:
            return {"trades": [], "yearly_summary": {}, "monthly_summary": {}}

        trades = json.loads(content)

        yearly_summary = defaultdict(lambda: {
            "total_pnl_percent": 0,
            "trade_count": 0,
            "winning_trades": 0,
        })
        monthly_summary = defaultdict(lambda: defaultdict(float))

        for trade in trades:
            try:
                exit_date = datetime.fromisoformat(trade['exit_date'].replace('Z', '+00:00'))
                entry_date = datetime.fromisoformat(trade['entry_date'].replace('Z', '+00:00'))
                year = exit_date.year
                month = exit_date.month
                
                pnl_percent = trade.get('profit_loss_percent')

                if entry_date.date() == exit_date.date() and pnl_percent == 0:
                    continue

                if pnl_percent is None:
                    continue

                # Yearly summary
                yearly_summary[year]["total_pnl_percent"] += pnl_percent
                yearly_summary[year]["trade_count"] += 1
                if pnl_percent > 0:
                    yearly_summary[year]["winning_trades"] += 1
                
                # Monthly summary
                monthly_summary[year][month] += pnl_percent

            except (ValueError, KeyError) as e:
                logger.warning(f"Skipping trade due to invalid data: {trade}, error: {e}")
                continue

        # Finalize yearly summary
        final_yearly_summary = {}
        for year, data in yearly_summary.items():
            win_rate = (data["winning_trades"] / data["trade_count"]) * 100 if data["trade_count"] > 0 else 0
            final_yearly_summary[str(year)] = {
                "year": year,
                "total_pnl_percent": round(data["total_pnl_percent"], 2),
                "trade_count": data["trade_count"],
                "winning_trades": data["winning_trades"],
                "win_rate": round(win_rate, 2)
            }
        
        sorted_yearly_summary = dict(sorted(final_yearly_summary.items(), key=lambda item: item[0], reverse=True))

        # Finalize monthly summary
        final_monthly_summary = {
            str(year): {str(month): round(pnl, 2) for month, pnl in sorted(months.items())}
            for year, months in sorted(monthly_summary.items(), reverse=True)
        }

        return {"trades": trades, "yearly_summary": sorted_yearly_summary, "monthly_summary": final_monthly_summary}

    except Exception as e:
        logger.error(f"Error processing trade history: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to process trade history"}
        )





@app.get("/api/file-paths-status")
def get_file_paths_status():
    """獲取當前文件路徑狀態"""
    try:
        import os
        from pathlib import Path

        # 檢查路徑管理器狀態
        try:
            from backend.path_manager import path_manager
            path_info = path_manager.get_info()
        except ImportError:
            path_info = {"error": "路徑管理器不可用"}

        # 檢查實際使用的文件路徑
        actual_paths = {
            "analysis_path": str(ANALYSIS_PATH),
            "monitored_stocks_path": str(MONITORED_STOCKS_PATH),
            "trade_history_path": str(TRADE_HISTORY_PATH)
        }

        # 檢查文件狀態
        file_status = {}
        for name, path_str in actual_paths.items():
            path = Path(path_str)
            file_status[name] = {
                "path": path_str,
                "exists": path.exists(),
                "readable": False,
                "writable": False,
                "size": 0
            }

            if path.exists():
                try:
                    # 測試讀取
                    content = path.read_text(encoding='utf-8')
                    file_status[name]["readable"] = True
                    file_status[name]["size"] = len(content)

                    # 測試寫入
                    path.write_text(content, encoding='utf-8')
                    file_status[name]["writable"] = True
                except Exception as e:
                    file_status[name]["error"] = str(e)

        # 檢查備份目錄
        backup_dir = Path("/tmp/bullps_data")
        backup_status = {
            "exists": backup_dir.exists(),
            "writable": False,
            "files": {}
        }

        if backup_dir.exists():
            try:
                test_file = backup_dir / "test.tmp"
                test_file.write_text("test")
                test_file.unlink()
                backup_status["writable"] = True
            except Exception:
                pass

            # 檢查備份文件
            for filename in ["monitored_stocks.json", "trade_history.json", "analysis_result.json"]:
                backup_file = backup_dir / filename
                backup_status["files"][filename] = {
                    "exists": backup_file.exists(),
                    "size": backup_file.stat().st_size if backup_file.exists() else 0
                }

        return {
            "status": "success",
            "timestamp": datetime.now(TZ_TAIPEI).isoformat(),
            "path_manager_info": path_info,
            "actual_paths": actual_paths,
            "file_status": file_status,
            "backup_status": backup_status,
            "environment": {
                "container_env": os.environ.get("CONTAINER_ENV"),
                "zeabur": os.environ.get("ZEABUR"),
                "hostname": os.environ.get("HOSTNAME"),
                "backup_dir_env": os.environ.get("BULLPS_BACKUP_DIR")
            }
        }

    except Exception as e:
        logger.error(f"Error in get_file_paths_status: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"獲取文件路徑狀態失敗: {str(e)}"}
        )

@app.post("/api/import-monitored-stocks")
async def import_monitored_stocks(file: UploadFile = File(...)):
    """匯入監控股票數據"""
    try:
        # 驗證文件類型
        if not file.filename.endswith('.json'):
            return JSONResponse(
                status_code=400,
                content={"error": "只支援 JSON 文件格式"}
            )

        # 讀取文件內容
        content = await file.read()

        # 驗證 JSON 格式
        try:
            data = json.loads(content.decode('utf-8'))
        except json.JSONDecodeError as e:
            return JSONResponse(
                status_code=400,
                content={"error": f"JSON 格式錯誤: {str(e)}"}
            )

        # 驗證數據結構
        if not isinstance(data, list):
            return JSONResponse(
                status_code=400,
                content={"error": "數據格式錯誤：應為股票列表數組"}
            )

        # 驗證每個股票項目的必要字段
        required_fields = ['symbol', 'entry_price', 'entry_date']
        for i, stock in enumerate(data):
            if not isinstance(stock, dict):
                return JSONResponse(
                    status_code=400,
                    content={"error": f"第 {i+1} 項數據格式錯誤：應為對象"}
                )

            for field in required_fields:
                if field not in stock:
                    return JSONResponse(
                        status_code=400,
                        content={"error": f"第 {i+1} 項缺少必要字段: {field}"}
                    )

        # 備份原有數據
        try:
            original_data = []
            if MONITORED_STOCKS_PATH.exists():
                original_content = MONITORED_STOCKS_PATH.read_text(encoding='utf-8')
                if original_content.strip():
                    original_data = json.loads(original_content)
        except Exception as e:
            logger.warning(f"無法讀取原有數據進行備份: {e}")

        # 保存新數據
        try:
            MONITORED_STOCKS_PATH.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            logger.info(f"成功匯入 {len(data)} 筆監控股票數據")

            return {
                "status": "success",
                "message": f"成功匯入 {len(data)} 筆監控股票數據",
                "imported_count": len(data),
                "original_count": len(original_data),
                "timestamp": datetime.now(TZ_TAIPEI).isoformat()
            }

        except Exception as e:
            logger.error(f"保存匯入數據失敗: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": f"保存數據失敗: {str(e)}"}
            )

    except Exception as e:
        logger.error(f"匯入監控股票數據失敗: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"匯入失敗: {str(e)}"}
        )

@app.post("/api/import-trade-history")
async def import_trade_history(file: UploadFile = File(...)):
    """匯入交易歷史數據"""
    try:
        # 驗證文件類型
        if not file.filename.endswith('.json'):
            return JSONResponse(
                status_code=400,
                content={"error": "只支援 JSON 文件格式"}
            )

        # 讀取文件內容
        content = await file.read()

        # 驗證 JSON 格式
        try:
            data = json.loads(content.decode('utf-8'))
        except json.JSONDecodeError as e:
            return JSONResponse(
                status_code=400,
                content={"error": f"JSON 格式錯誤: {str(e)}"}
            )

        # 驗證數據結構
        if not isinstance(data, list):
            return JSONResponse(
                status_code=400,
                content={"error": "數據格式錯誤：應為交易記錄列表數組"}
            )

        # 驗證每個交易記錄的必要字段
        required_fields = ['symbol', 'entry_price', 'exit_price', 'entry_date', 'exit_date']
        for i, trade in enumerate(data):
            if not isinstance(trade, dict):
                return JSONResponse(
                    status_code=400,
                    content={"error": f"第 {i+1} 項數據格式錯誤：應為對象"}
                )

            for field in required_fields:
                if field not in trade:
                    return JSONResponse(
                        status_code=400,
                        content={"error": f"第 {i+1} 項缺少必要字段: {field}"}
                    )

        # 備份原有數據
        try:
            original_data = []
            if TRADE_HISTORY_PATH.exists():
                original_content = TRADE_HISTORY_PATH.read_text(encoding='utf-8')
                if original_content.strip():
                    original_data = json.loads(original_content)
        except Exception as e:
            logger.warning(f"無法讀取原有數據進行備份: {e}")

        # 保存新數據
        try:
            TRADE_HISTORY_PATH.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            logger.info(f"成功匯入 {len(data)} 筆交易歷史數據")

            return {
                "status": "success",
                "message": f"成功匯入 {len(data)} 筆交易歷史數據",
                "imported_count": len(data),
                "original_count": len(original_data),
                "timestamp": datetime.now(TZ_TAIPEI).isoformat()
            }

        except Exception as e:
            logger.error(f"保存匯入數據失敗: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": f"保存數據失敗: {str(e)}"}
            )

    except Exception as e:
        logger.error(f"匯入交易歷史數據失敗: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"匯入失敗: {str(e)}"}
        )

@app.get("/api/export-monitored-stocks")
def export_monitored_stocks():
    """匯出監控股票數據"""
    try:
        if MONITORED_STOCKS_PATH.exists():
            content = MONITORED_STOCKS_PATH.read_text(encoding='utf-8')
            data = json.loads(content) if content.strip() else []
        else:
            data = []

        # 生成文件名
        timestamp = datetime.now(TZ_TAIPEI).strftime('%Y%m%d_%H%M%S')
        filename = f"monitored_stocks_{timestamp}.json"

        # 返回文件下載
        return Response(
            content=json.dumps(data, indent=2, ensure_ascii=False),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/json; charset=utf-8"
            }
        )

    except Exception as e:
        logger.error(f"匯出監控股票數據失敗: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"匯出失敗: {str(e)}"}
        )

@app.get("/api/export-trade-history")
def export_trade_history():
    """匯出交易歷史數據"""
    try:
        if TRADE_HISTORY_PATH.exists():
            content = TRADE_HISTORY_PATH.read_text(encoding='utf-8')
            data = json.loads(content) if content.strip() else []
        else:
            data = []

        # 生成文件名
        timestamp = datetime.now(TZ_TAIPEI).strftime('%Y%m%d_%H%M%S')
        filename = f"trade_history_{timestamp}.json"

        # 返回文件下載
        return Response(
            content=json.dumps(data, indent=2, ensure_ascii=False),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/json; charset=utf-8"
            }
        )

    except Exception as e:
        logger.error(f"匯出交易歷史數據失敗: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"匯出失敗: {str(e)}"}
        )

# 回測狀態管理
backtest_status = {
    "is_running": False,
    "progress": 0,
    "message": "",
    "current_step": "",
    "logs": [],
    "result": None
}

@app.get("/api/fear-greed-index")
async def get_fear_greed_index_data():
    """
    獲取CNN恐懼貪婪指數的歷史數據
    """
    try:
        from backend.fear_greed_index import FearGreedIndex
        fgi = FearGreedIndex()
        # The fetch_data is called inside get_historical_data if data is not present
        df = fgi.get_historical_data()

        if df.empty:
            return JSONResponse(
                status_code=404,
                content={"error": "無法獲取恐懼貪婪指數數據，請稍後再試。"}
            )
        
        # Convert dataframe to a list of dicts for JSON response
        # The 'date' column is a datetime object, so convert it to ISO 8601 string format
        df['date'] = df['date'].dt.strftime('%Y-%m-%dT%H:%M:%S')
        historical_data = df.to_dict(orient='records')
        
        current_index = fgi.get_current_index()

        return {
            "current": current_index,
            "historical": historical_data
        }
        
    except Exception as e:
        logger.error(f"獲取恐懼貪婪指數時發生錯誤: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "伺服器在獲取恐懼貪婪指數時發生內部錯誤。"}
        )


def update_backtest_status(message: str, progress: int, step: str = "", log_message: str = ""):
    """更新回測狀態"""
    global backtest_status
    backtest_status["message"] = message
    backtest_status["progress"] = progress
    backtest_status["current_step"] = step

    if log_message:
        timestamp = datetime.now(TZ_TAIPEI).strftime('%H:%M:%S')
        backtest_status["logs"].append(f"[{timestamp}] {log_message}")
        # 保持最新的100條日誌
        if len(backtest_status["logs"]) > 100:
            backtest_status["logs"] = backtest_status["logs"][-100:]

@app.get("/api/backtest-status")
def get_backtest_status():
    """獲取回測狀態"""
    return backtest_status

@app.post("/api/run-backtest")
def run_backtest(request: dict):
    """執行回測"""
    global backtest_status

    if backtest_status["is_running"]:
        return {"status": "already_running", "message": "回測正在進行中"}

    # 驗證參數
    symbol = request.get("symbol", "").strip().upper()
    start_date = request.get("start_date", "")
    end_date = request.get("end_date", "")

    if not symbol:
        return JSONResponse(
            status_code=400,
            content={"error": "請輸入股票代號"}
        )

    if not start_date or not end_date:
        return JSONResponse(
            status_code=400,
            content={"error": "請輸入開始和結束日期"}
        )

    try:
        # 驗證日期格式
        from datetime import datetime
        datetime.strptime(start_date, '%Y-%m-%d')
        datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"error": "日期格式錯誤，請使用 YYYY-MM-DD 格式"}
        )

    # 重置狀態
    backtest_status = {
        "is_running": True,
        "progress": 0,
        "message": "準備開始回測...",
        "current_step": "初始化",
        "logs": [],
        "result": None
    }

    logger.info(f"開始回測: {symbol}, {start_date} to {end_date}")

    # 使用線程池執行回測任務，避免阻塞API
    import threading
    thread = threading.Thread(target=run_backtest_task, args=(symbol, start_date, end_date))
    thread.daemon = True
    thread.start()

    return {"status": "started", "message": "回測已開始"}

def run_backtest_task(symbol: str, start_date: str, end_date: str):
    """執行回測任務 - 改為同步函數在後台線程中執行"""
    global backtest_status

    try:
        update_backtest_status("正在初始化回測環境...", 5, "初始化", "開始回測程序")

        # 導入必要的模組
        import yfinance as yf
        import backtester
        import pandas as pd
        import time

        update_backtest_status("正在下載股票數據...", 15, "數據下載", f"正在下載 {symbol} 的歷史數據")

        # 驗證股票代號並下載數據
        try:
            stock_data = yf.download(symbol, start=start_date, end=end_date, progress=False, auto_adjust=True)
            if stock_data.empty:
                raise ValueError(f"無法獲取股票 {symbol} 的數據")

            update_backtest_status("數據下載完成", 25, "數據驗證", f"成功下載 {len(stock_data)} 天的數據")

        except Exception as e:
            update_backtest_status("數據下載失敗", 0, "錯誤", f"下載失敗: {str(e)}")
            backtest_status["is_running"] = False
            return

        update_backtest_status("正在準備回測程序...", 35, "程序準備", "設置回測參數")

        # 保存原始值
        original_start = backtester.START_DATE
        original_end = backtester.END_DATE

        try:
            # 修改全局變量
            backtester.START_DATE = start_date
            backtester.END_DATE = end_date

            update_backtest_status("載入股票數據...", 45, "數據載入", f"載入 {symbol} 的歷史數據")

            # 使用原始的preload_data和Backtester
            watchlist = [symbol]
            all_data = backtester.preload_data(watchlist, backtester.START_DATE, backtester.END_DATE)

            if not all_data:
                update_backtest_status("數據載入失敗", 0, "錯誤", "無法載入股票數據")
                backtest_status["is_running"] = False
                return

            # 創建自定義的Backtester來即時輸出日誌
            class RealTimeBacktester(backtester.Backtester):
                def __init__(self, symbols, all_historical_data):
                    super().__init__(symbols, all_historical_data)
                    self.total_days = len(self.trading_days)
                    self.current_day_index = 0

                def run(self):
                    update_backtest_status("開始逐日模擬交易...", 55, "模擬交易", f"共 {self.total_days} 個交易日")

                    for i in range(len(self.trading_days) - 1):
                        current_day = self.trading_days[i]
                        next_day = self.trading_days[i+1]
                        self.current_day_index = i

                        # 計算進度
                        progress = 55 + int((i / self.total_days) * 30)  # 55% 到 85%

                        # 即時更新日誌
                        date_str = current_day.strftime('%Y-%m-%d')

                        # 檢查出場
                        exit_count_before = len([t for t in self.trade_log if t.get('exit_date')])
                        self.check_and_execute_exits(current_day, next_day)
                        exit_count_after = len([t for t in self.trade_log if t.get('exit_date')])

                        if exit_count_after > exit_count_before:
                            for trade in self.trade_log[exit_count_before:exit_count_after]:
                                pnl = trade.get('profit_loss_usd', 0)
                                pnl_pct = trade.get('profit_loss_pct', 0)
                                result_text = "獲利" if pnl > 0 else "虧損"
                                update_backtest_status(f"出場信號", progress, "交易執行",
                                                     f"🔴 {trade['symbol']} 出場 @ ${trade.get('exit_price', 0):.2f} ({result_text}: ${pnl:.2f}, {pnl_pct:.1f}%)")

                        # 檢查進場
                        entry_count_before = len([t for t in self.trade_log if t.get('entry_date')])
                        self.check_and_execute_entries(current_day, next_day)
                        entry_count_after = len([t for t in self.trade_log if t.get('entry_date')])

                        if entry_count_after > entry_count_before:
                            for trade in self.trade_log[entry_count_before:entry_count_after]:
                                update_backtest_status(f"進場信號", progress, "交易執行",
                                                     f"🟢 {trade['symbol']} 進場 @ ${trade.get('entry_price', 0):.2f}")

                        # 更頻繁的進度更新
                        if i % 3 == 0 or i < 15:  # 前15天每天更新，之後每3天更新
                            current_trades = len(self.trade_log)
                            update_backtest_status(f"模擬交易日: {date_str}", progress, "模擬交易",
                                                 f"[{i+1}/{self.total_days}] 檢查 {date_str} 交易機會")

                        # 添加延遲讓前端有時間獲取更新
                        if i % 5 == 0:
                            time.sleep(0.05)  # 50毫秒延遲，讓前端有時間獲取狀態

                    update_backtest_status("模擬交易完成", 85, "計算結果", f"總共產生 {len(self.trade_log)} 筆交易")

            # 創建並運行回測器
            bt = RealTimeBacktester(watchlist, all_data)
            bt.run()

            # 處理結果
            if bt.trade_log:
                df_log = pd.DataFrame(bt.trade_log)

                total_trades = len(df_log)
                winning_trades = df_log[df_log['profit_loss_usd'] > 0]
                losing_trades = df_log[df_log['profit_loss_usd'] <= 0]

                win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0
                total_pnl = df_log['profit_loss_usd'].sum()

                avg_profit = winning_trades['profit_loss_usd'].mean() if len(winning_trades) > 0 else 0
                avg_loss = losing_trades['profit_loss_usd'].mean() if len(losing_trades) > 0 else 0

                profit_factor = abs(winning_trades['profit_loss_usd'].sum() / losing_trades['profit_loss_usd'].sum()) if len(losing_trades) > 0 and losing_trades['profit_loss_usd'].sum() != 0 else float('inf')

                avg_holding_period = df_log['holding_period_days'].mean()

                backtest_result = {
                    "symbol": symbol,
                    "start_date": start_date,
                    "end_date": end_date,
                    "total_trades": total_trades,
                    "win_rate": round(win_rate, 2),
                    "total_pnl": round(total_pnl, 2),
                    "avg_profit": round(avg_profit, 2),
                    "avg_loss": round(avg_loss, 2),
                    "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else "∞",
                    "avg_holding_period": round(avg_holding_period, 1),
                    "trades": df_log.to_dict('records')
                }

                backtest_status["result"] = backtest_result
                update_backtest_status("回測完成", 100, "完成",
                                     f"✅ 完成！{total_trades} 筆交易，勝率 {win_rate:.1f}%，總盈虧 ${total_pnl:.2f}")
            else:
                backtest_result = {
                    "symbol": symbol,
                    "start_date": start_date,
                    "end_date": end_date,
                    "total_trades": 0,
                    "win_rate": 0,
                    "total_pnl": 0,
                    "avg_profit": 0,
                    "avg_loss": 0,
                    "profit_factor": 0,
                    "avg_holding_period": 0,
                    "trades": []
                }
                backtest_status["result"] = backtest_result
                update_backtest_status("回測完成", 100, "完成", "✅ 回測完成，期間內未產生交易信號")

        finally:
            # 恢復原始值
            backtester.START_DATE = original_start
            backtester.END_DATE = original_end

    except Exception as e:
        logger.error(f"直接回測執行失敗: {e}")
        update_backtest_status("回測執行失敗", 0, "錯誤", f"執行錯誤: {str(e)}")
        backtest_status["is_running"] = False
        return

    except Exception as e:
        logger.error(f"回測任務失敗: {e}")
        update_backtest_status("回測失敗", 0, "錯誤", f"系統錯誤: {str(e)}")

    finally:
        backtest_status["is_running"] = False



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
