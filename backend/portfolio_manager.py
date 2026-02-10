import json
import os
import sys
from datetime import datetime
from pathlib import Path
import numpy as np

# 將專案根目錄添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrated_stock_analyzer import IntegratedStockAnalyzer

# --- 常數定義 ---
from backend.path_manager import path_manager

# 使用統一路徑
PORTFOLIO_FILE = path_manager.get_monitored_stocks_path()
ANALYSIS_RESULT_FILE = path_manager.get_analysis_path()
TRADE_HISTORY_FILE = path_manager.get_trade_history_path()

print(f"Using unified monitored stocks file path: {PORTFOLIO_FILE}")
print(f"Using unified analysis result file path: {ANALYSIS_RESULT_FILE}")
print(f"Using unified trade history file path: {TRADE_HISTORY_FILE}")

# --- 數據讀寫輔助函式 ---

def load_json_file(file_path):
    """通用 JSON 檔案讀取函式"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 如果是 monitored_stocks.json，檢查並填充 initial_analysis_snapshot
            if file_path == PORTFOLIO_FILE and isinstance(data, list):
                analysis_data = load_json_file(ANALYSIS_RESULT_FILE) # 載入最新的分析結果
                updated_data = []
                for trade in data:
                    if 'initial_analysis_snapshot' not in trade or not trade['initial_analysis_snapshot'].get('confidence_factors'):
                        symbol = trade.get('symbol')
                        if symbol:
                            latest_analysis = None
                            for stock_analysis in analysis_data.get('result', []):
                                if stock_analysis.get('symbol') == symbol:
                                    latest_analysis = stock_analysis
                                    break
                            if latest_analysis:
                                trade['initial_analysis_snapshot'] = latest_analysis
                                print(f"填充 {symbol} 的 initial_analysis_snapshot。")
                            else:
                                print(f"警告: 無法為 {symbol} 找到最新的分析數據來填充 initial_analysis_snapshot。")
                        else:
                            print("警告: 監控股票條目缺少 'symbol' 字段。")
                    updated_data.append(trade)
                return updated_data
            return data
        return []
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"讀取 {file_path} 時發生錯誤: {e}")
        return []

def save_json_file(data, file_path):
    """通用 JSON 檔案儲存函式"""
    class NpEncoder(json.JSONEncoder):
        def default(self, obj):
            import pandas as pd
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, pd.Timestamp):
                return obj.isoformat()
            return super(NpEncoder, self).default(obj)

    # 處理 NaN 值，將其轉換為 None
    def clean_nan_values(obj):
        if isinstance(obj, float) and (obj != obj): # 檢查是否為 NaN
            return None
        elif isinstance(obj, dict):
            return {k: clean_nan_values(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_nan_values(elem) for elem in obj]
        else:
            return obj

    cleaned_data = clean_nan_values(data)

    # 嘗試保存到主要位置
    try:
        # 確保目錄存在
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)



        # 寫入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, indent=2, ensure_ascii=False, cls=NpEncoder)

        return True  # 保存成功
    except (PermissionError, OSError) as e:
        print(f"❌ 儲存至 {file_path} 時發生錯誤: {e}")
        return False  # 保存失敗
    except Exception as e:
        print(f"❌ 儲存至 {file_path} 時發生未知錯誤: {e}")
        return False  # 保存失敗

def get_latest_analysis(symbol):
    """從 analysis_result.json 讀取指定股票的最新分析數據"""
    analysis_data = load_json_file(ANALYSIS_RESULT_FILE)
    if not analysis_data or 'result' not in analysis_data:
        return None
        
    for stock_analysis in analysis_data.get('result', []):
        if stock_analysis.get('symbol') == symbol:
            return stock_analysis
    return None

# --- 核心出場評估邏輯 ---

def evaluate_smart_sar_exit(trade, current_analysis, current_dt=None):
    """
    智能SAR停損評估
    結合多重確認機制，避免假突破
    """
    from datetime import datetime
    if current_dt is None:
        current_dt = datetime.now()
    current_price = current_analysis.get('current_price')
    current_sar = current_analysis.get('sar')
    entry_price = trade.get('entry_price')
    entry_date = trade.get('entry_date')

    # 檢查數據有效性
    if current_price is None or current_sar is None:
        return {
            'should_exit': False,
            'reason': 'SAR數據不完整',
            'confirmation_score': 0,
            'max_confirmation_score': 0,
            'confirmation_factors': ['數據缺失']
        }

    # 確保數據類型正確
    try:
        current_price = float(current_price)
        current_sar = float(current_sar)
    except (ValueError, TypeError):
        return {
            'should_exit': False,
            'reason': 'SAR數據格式錯誤',
            'confirmation_score': 0,
            'max_confirmation_score': 0,
            'confirmation_factors': ['數據格式錯誤']
        }

    # 檢查數據是否為有效數值
    if not (np.isfinite(current_price) and np.isfinite(current_sar)):
        return {
            'should_exit': False,
            'reason': 'SAR數據包含無效值',
            'confirmation_score': 0,
            'max_confirmation_score': 0,
            'confirmation_factors': ['無效數值']
        }

    # 基本SAR信號
    basic_sar_triggered = current_price < current_sar

    if not basic_sar_triggered:
        return {
            'should_exit': False,
            'reason': 'SAR未觸發',
            'confirmation_score': 0,
            'max_confirmation_score': 0,
            'confirmation_factors': []
        }

    # 計算持倉天數
    try:
        entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
        holding_days = (current_dt - entry_dt).days
    except:
        holding_days = 0

    # 計算獲利幅度
    profit_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price else 0

    # 確認機制評分
    confirmation_score = 0
    confirmation_factors = []
    max_score = 8

    # 1. 獲利保護機制（獲利越多，停損越寬鬆）
    if profit_pct > 20:
        # 大幅獲利時，需要更強確認
        required_confirmation = 6
    elif profit_pct > 10:
        # 中等獲利時，中等確認
        required_confirmation = 4
    elif profit_pct > 0:
        # 小幅獲利時，較少確認
        required_confirmation = 3
    else:
        # 虧損時，較嚴格停損
        required_confirmation = 2

    # 2. 持倉時間考量
    if holding_days < 3:
        # 短期持倉，避免過早停損
        required_confirmation += 1
        confirmation_factors.append("短期持倉保護")
    elif holding_days > 30:
        # 長期持倉，適度放寬
        required_confirmation = max(required_confirmation - 1, 2)

    # 3. 技術指標確認
    # [Fix] 對於短期持倉（<3天），忽略 "RSI超買" 和 "放量" 作為負面信號
    # 因為這些通常是強勢突破的特徵
    ignore_breakout_signals = (holding_days < 3)

    current_rsi = current_analysis.get('rsi', 50)
    current_macd = current_analysis.get('macd', 0)
    current_volume_ratio = current_analysis.get('volume_ratio', 1)

    # RSI確認
    if not ignore_breakout_signals:
        if current_rsi > 70:
            confirmation_score += 2
            confirmation_factors.append("RSI超買")
        elif current_rsi > 60:
            confirmation_score += 1
            confirmation_factors.append("RSI偏高")

    # MACD確認 (MACD轉負通常是真跌勢，保留)
    if current_macd < 0:
        confirmation_score += 2
        confirmation_factors.append("MACD轉負")

    # 成交量確認
    if not ignore_breakout_signals:
        if current_volume_ratio > 1.5:
            confirmation_score += 1
            confirmation_factors.append("放量下跌")
        
    # [Fix] Day 0 特別保護：除非大跌，否則不輕易因盤中波動出場
    if holding_days == 0 and profit_pct > -2.0:
         # 如果虧損在 2% 以內，且是第一天，強制要求更高的確認分數 (幾乎是不出場)
        required_confirmation += 5
        confirmation_factors.append("Day0波動保護")

    # 4. 價格結構確認
    sar_penetration = ((current_sar - current_price) / current_price) * 100
    if sar_penetration > 2:
        confirmation_score += 2
        confirmation_factors.append("深度跌破SAR")
    elif sar_penetration > 1:
        confirmation_score += 1
        confirmation_factors.append("明顯跌破SAR")

    # 5. 趨勢強度確認
    confidence_factors = current_analysis.get('confidence_factors', [])
    negative_factors = [
        "RSI超買風險", "MACD死叉", "價格跌破20日均線",
        "均線排列不佳", "動量減速", "趨勢反轉確認"
    ]

    negative_count = sum(1 for factor in confidence_factors if any(neg in factor for neg in negative_factors))
    if negative_count >= 3:
        confirmation_score += 2
        confirmation_factors.append("多重負面信號")
    elif negative_count >= 2:
        confirmation_score += 1
        confirmation_factors.append("部分負面信號")

    # 決策邏輯
    should_exit = confirmation_score >= required_confirmation

    reason = f"SAR移動停損 (價格: {current_price:.2f} < SAR: {current_sar:.2f}, 獲利: {profit_pct:.1f}%, 持倉: {holding_days}天)"

    return {
        'should_exit': should_exit,
        'reason': reason,
        'confirmation_score': confirmation_score,
        'max_confirmation_score': max_score,
        'required_confirmation': required_confirmation,
        'confirmation_factors': confirmation_factors,
        'profit_pct': profit_pct,
        'holding_days': holding_days,
        'sar_penetration': sar_penetration
    }

def evaluate_exit_confidence(trade, latest_analysis):
    """
    評估單一持倉的出場信心度
    :param trade: 一筆來自 monitored_stocks.json 的持倉紀錄
    :param latest_analysis: 該股票的最新分析數據
    :return: 一個包含信心度分數和原因的字典
    """
    symbol = trade.get('symbol')

    # 獲取進場時的分析快照和當前分析快照
    initial_snapshot = trade.get('initial_analysis_snapshot', {})
    current_snapshot = latest_analysis # latest_analysis 就是最新的分析快照

    # 從快照中獲取進場理由和當前信心因素
    entry_reasons_list = initial_snapshot.get('confidence_factors', [])
    entry_reasons = set(entry_reasons_list)

    current_factors_raw = current_snapshot.get('confidence_factors', [])
    if isinstance(current_factors_raw, list):
        current_factors = set(current_factors_raw)
    else:
        current_factors = set() # 處理 NaN 或其他非列表類型

    # 獲取買入價格和當前價格
    entry_price = trade.get('entry_price', 0) # 確保有預設值
    current_price = current_snapshot.get('current_price', 0)

    if not entry_reasons:
        return {
            "symbol": symbol,
            "exit_confidence": 0.0,
            "erosion_score": 0.0,
            "penalty_score": 0.0,
            "details": {
                "disappeared_reasons": [],
                "triggered_penalties": [],
                "notes": "缺少進場理由 (initial_analysis_snapshot 或 confidence_factors 為空)，無法評估。"
            }
        }

    # 1. 計算理由侵蝕分數 (Erosion Score)
    disappeared_reasons = [reason for reason in entry_reasons if reason not in current_factors]
    erosion_score = len(disappeared_reasons) / len(entry_reasons) if entry_reasons else 0
    
    # 2. 定義危險信號並計算懲罰分數 (Penalty Score)
    DANGER_SIGNALS = {
        "MACD死叉": 0.60, 
        "RSI超買風險": 0.50, 
        "價格跌破20日均線": 0.50,
        "均線排列不佳": 0.50,
        "RSI偏高": 0.40,
        "動量減速": 0.50,
        "價格跌破5日均線": 0.40,
        "趨勢反轉確認": -0.50, # 反轉確認在出場時是負面因素
        "反轉強度強勁": -0.50,
        "反轉可信度高": -0.50,
        "短期動能轉折": -0.50,
        "價格結構反轉": -0.50,
        "波動率過高": 0.30,
        "支撐位薄弱": 0.30,
        "相對強度為負": 0.50,
        "上漲動能不足": 0.50,
        "指標斜率向下": 0.50,
        "動量減速": 0.50,
        "價格通道向下": 0.50,
        "成交量配合不佳": 0.30
    }
    
    penalty_score = 0.0
    triggered_penalties = []
    for signal, penalty in DANGER_SIGNALS.items():
        if signal in current_factors:
            penalty_score += penalty
            triggered_penalties.append(signal)

    # 3. 計算綜合信心度 (Composite Exit Confidence Score)
    # 基礎分數，考慮理由侵蝕和風險懲罰
    base_exit_score = (erosion_score * 1) + (min(penalty_score, 1.0) * 1)

    # 引入更多出場相關指標的影響
    # 這些指標從 current_snapshot 中獲取，增加對 None 值的處理
    current_rsi = current_snapshot.get('rsi') or 50
    current_macd = current_snapshot.get('macd') or 0
    current_macd_hist = current_snapshot.get('macd_histogram') or 0
    current_volume_ratio = current_snapshot.get('volume_ratio') or 1
    current_ma20 = current_snapshot.get('ma20') or current_price
    current_ma5 = current_snapshot.get('ma5') or current_price

    # RSI惡化
    if current_rsi > 70: # 超買區
        base_exit_score += 0.2
    elif current_rsi < 30: # 超賣區，可能反彈，降低出場信心
        base_exit_score -= 0.1

    # MACD死叉或柱狀圖轉負
    if current_macd < 0 and current_macd_hist < 0: # 假設有macd_histogram
        base_exit_score += 0.2

    # 價格跌破均線
    if current_price < current_ma5: # 跌破5日均線
        base_exit_score += 0.1
    if current_price < current_ma20: # 跌破20日均線
        base_exit_score += 0.2

    # 成交量異常放大（下跌時）
    if current_price < entry_price and current_volume_ratio > 1.5: # 價格下跌且成交量放大
        base_exit_score += 0.15

    # 趨勢反轉指標惡化 (從 integrated_stock_analyzer.py 獲取)
    trend_reversal_confirmation = current_snapshot.get('trend_reversal_confirmation') or 0
    reversal_strength = current_snapshot.get('reversal_strength') or 0
    reversal_reliability = current_snapshot.get('reversal_reliability') or 0

    if trend_reversal_confirmation < 40: # 修正：低端反轉強度不足，視為持倉信心下降
        base_exit_score += 0.15
    if reversal_strength < 40:
        base_exit_score += 0.1
    if reversal_reliability < 40:
        base_exit_score += 0.1

    # 確保信心度在0到1之間
    exit_confidence = max(0.0, min(1.0, base_exit_score))

    return {
        "symbol": symbol,
        "exit_confidence": round(exit_confidence, 2),
        "erosion_score": round(erosion_score, 2),
        "penalty_score": round(penalty_score, 2),
        "details": {
            "disappeared_reasons": disappeared_reasons,
            "triggered_penalties": triggered_penalties,
            "notes": ""
        }
    }

# --- 投資組合管理函式 ---

def add_to_monitoring(symbol, purchase_price, quantity):
    """
    將新買入的股票加入監控列表（主要用於手動操作）。
    """
    latest_analysis = get_latest_analysis(symbol)
    if not latest_analysis:
        print(f"錯誤: 找不到 {symbol} 的分析數據，無法加入監控。")
        return

    # 手動加入時，我們使用更全面的 confidence_factors 作為理由
    entry_reasons = latest_analysis.get('confidence_factors', [])
    if not entry_reasons:
        print(f"警告: {symbol} 的進場理由為空，仍將加入監控。")

    new_trade = {
        "symbol": symbol,
        "entry_price": purchase_price,
        "quantity": quantity,
        "purchase_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "monitoring",
        "entry_signal_conditions": entry_reasons, # 寫入分析器使用的欄位名
        "initial_analysis_snapshot": latest_analysis # 新增：儲存完整的分析快照
    }

    monitored_stocks = load_json_file(PORTFOLIO_FILE)
    if any(t.get('symbol') == symbol for t in monitored_stocks):
        print(f"{symbol} 已經在監控列表中。")
        return
        
    monitored_stocks.append(new_trade)
    save_json_file(monitored_stocks, PORTFOLIO_FILE)
    print(f"已將 {symbol} 加入監控列表。")

def remove_from_monitoring(symbol, sell_price, exit_reasons: list = None):
    """
    從監控列表中移除股票，並記錄到交易歷史中。
    """
    if exit_reasons is None:
        exit_reasons = []
    monitored_stocks = load_json_file(PORTFOLIO_FILE)
    trade_to_close = next((trade for trade in monitored_stocks if trade.get('symbol') == symbol), None)

    if not trade_to_close:
        print(f"錯誤: 在監控列表中找不到 {symbol}。")
        return

    remaining_stocks = [t for t in monitored_stocks if t.get('symbol') != symbol]
    save_json_file(remaining_stocks, PORTFOLIO_FILE)

    # 正確地從 entry_price 計算盈虧
    purchase_price = trade_to_close.get('entry_price', 0)
    profit = (sell_price - purchase_price) * trade_to_close.get('quantity', 1) # 預設數量為1，避免為0導致盈虧計算錯誤
    
    profit_loss_percent = ((sell_price - purchase_price) / purchase_price) * 100 if purchase_price else 0

    # Use the passed exit_reasons, do not overwrite it
    # If no reasons were passed, it will be an empty list due to the default in the function signature

    closed_trade = {
        **trade_to_close,
        "status": "closed",
        "exit_price": sell_price,
        "exit_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "profit_loss_percent": profit_loss_percent,
        "exit_reasons": exit_reasons,
        "quantity": trade_to_close.get('quantity', 1)
    }
    
    trade_history = load_json_file(TRADE_HISTORY_FILE)
    trade_history.append(closed_trade)
    save_json_file(trade_history, TRADE_HISTORY_FILE)
    
    print(f"已將 {symbol} 從監控中移除，並記錄至交易歷史。盈虧: {profit:.2f}")

def compare_and_update_monitored_stocks():
    """
    比對監控中的股票與新的 analysis_result.json 是否有差異，並更新 monitored_stocks.json。
    """
    monitored_stocks = load_json_file(PORTFOLIO_FILE)
    analysis_data = load_json_file(ANALYSIS_RESULT_FILE)
    
    if not monitored_stocks:
        print("監控列表為空，無需比對更新。")
        return

    updated_monitored_stocks = []
    for trade in monitored_stocks:
        symbol = trade.get('symbol')
        if not symbol:
            updated_monitored_stocks.append(trade)
            continue

        latest_analysis = None
        for stock_analysis in analysis_data.get('result', []):
            if stock_analysis.get('symbol') == symbol:
                latest_analysis = stock_analysis
                break
        
        if not latest_analysis:
            # 如果找不到最新分析，觸發對該股票的單獨分析
            latest_analysis = re_analyze_missing_stock(symbol)

        if latest_analysis:
            trade['current_analysis_snapshot'] = latest_analysis
            # TODO: 在這裡可以加入更詳細的差異比對邏輯，並記錄差異
            # 例如：比較 confidence_factors, 各項評分等
            
            # 簡單的差異標記
            initial_factors_raw = trade.get('initial_analysis_snapshot', {}).get('confidence_factors', [])
            initial_factors = set(initial_factors_raw) if isinstance(initial_factors_raw, list) else set()
            
            current_factors_raw = latest_analysis.get('confidence_factors', [])
            current_factors = set(current_factors_raw) if isinstance(current_factors_raw, list) else set()
            
            disappeared_factors = list(initial_factors - current_factors)
            new_factors = list(current_factors - initial_factors)
            
            trade['analysis_diff'] = {
                'disappeared_factors': disappeared_factors,
                'new_factors': new_factors,
                'has_diff': bool(disappeared_factors or new_factors)
            }
        else:
            print(f"警告: 找不到 {symbol} 的最新分析數據，無法更新其快照。")
            trade['current_analysis_snapshot'] = trade.get('current_analysis_snapshot', {}) # 保持舊的或空
            trade['analysis_diff'] = {'has_diff': False, 'notes': '最新分析數據缺失'}

        updated_monitored_stocks.append(trade)
    
    save_json_file(updated_monitored_stocks, PORTFOLIO_FILE)
    print("已完成監控股票的分析數據比對與更新。")

def re_analyze_missing_stock(symbol):
    """
    對指定的股票執行單獨分析，並將結果更新回 analysis_result.json
    """
    print(f"🔍 監控中的股票 {symbol} 缺少最新分析，啟動單獨分析...")
    
    # 初始化分析器
    # 注意：這裡假設 integrated_stock_analyzer.py 在上一層目錄
    analyzer_path = os.path.join(os.path.dirname(__file__), '..', 'stock_watchlist.json')
    analyzer = IntegratedStockAnalyzer(watchlist_file=analyzer_path)
    
    # 執行單獨分析
    analysis_result = analyzer.analyze_stock(symbol)
    
    if not analysis_result:
        print(f"❌ 對 {symbol} 的單獨分析失敗，無法獲取數據。")
        return None

    # 讀取現有的 analysis_result.json
    analysis_data = load_json_file(ANALYSIS_RESULT_FILE)
    if not analysis_data or 'result' not in analysis_data:
        analysis_data = {'result': []}

    # 檢查是否已存在該股票的分析，如果存在則更新，否則新增
    updated = False
    for i, stock_analysis in enumerate(analysis_data['result']):
        if stock_analysis.get('symbol') == symbol:
            analysis_data['result'][i] = analysis_result
            updated = True
            break
    
    if not updated:
        analysis_data['result'].append(analysis_result)
        
    # 儲存更新後的 analysis_result.json
    save_json_file(analysis_data, ANALYSIS_RESULT_FILE)
    print(f"✅ 已將 {symbol} 的最新分析結果更新至 analysis_result.json")
    
    return analysis_result


def check_monitored_stocks_for_exit():
    """
    主函式：遍歷所有監控中的持倉，評估並執行出場。
    """
    monitored_stocks = load_json_file(PORTFOLIO_FILE)
    
    if not monitored_stocks:
        print("監控列表為空，無需評估。")
        return

    print(f"\n--- 開始評估 {len(monitored_stocks)} 筆監控中的持倉 ---")
    for trade in list(monitored_stocks):
        symbol = trade.get('symbol')
        if not symbol:
            continue

        latest_analysis = get_latest_analysis(symbol)
        if not latest_analysis:
            latest_analysis = re_analyze_missing_stock(symbol)

        if not latest_analysis:
            print(f"\n警告: 找不到 {symbol} 的最新分析數據，跳過評估。")
            continue

        purchase_price = trade.get('entry_price', 'N/A')
        print(f"\n股票: {symbol} (買入價: {purchase_price})")

        # --- 執行新的雙重出場邏輯 ---
        should_sell = False
        exit_reason = []

        # 1. 智能SAR移動停損檢查
        current_price = latest_analysis.get('current_price')
        current_sar = latest_analysis.get('sar')

        if current_price is not None and current_sar is not None:
            sar_decision = evaluate_smart_sar_exit(trade, latest_analysis)

            if sar_decision['should_exit']:
                should_sell = True
                reason = sar_decision['reason']
                exit_reason.append(reason)
                print(f"決策: {reason}")
                print(f"  - 確認分數: {sar_decision['confirmation_score']}/{sar_decision['max_confirmation_score']}")
                print(f"  - 確認因素: {', '.join(sar_decision['confirmation_factors'])}")
        else:
            print(f"  - 警告: {symbol} 的最新分析缺少價格或SAR數據，無法評估SAR停損。")

        # 2. 若未觸發SAR停損，才檢查綜合信心度
        if not should_sell:
            report = evaluate_exit_confidence(trade, latest_analysis)
            print(f"出場信心度: {report.get('exit_confidence', 0) * 100:.0f}%")
            print(f"  - 理由侵蝕: {report.get('erosion_score', 0):.2f}")
            print(f"  - 風險懲罰: {report.get('penalty_score', 0):.2f}")

            if report.get('exit_confidence', 0) >= 0.8:
                should_sell = True
                reason = f"出場信心度達到 {report.get('exit_confidence', 0) * 100:.0f}%"
                exit_reason.append(reason)
                exit_reason.extend(report.get('details', {}).get('triggered_penalties', []))
                print(f"決策: {reason}")

        # 3. 執行賣出操作
        if should_sell:
            if current_price is not None:
                print(f"執行賣出 {symbol} at ${current_price:.2f}")
                remove_from_monitoring(symbol, current_price, exit_reason)
            else:
                print(f"錯誤: {symbol} 缺少當前價格，無法執行賣出操作。")
        else:
            print("決策: 繼續持有。")

# --- 使用範例 ---
if __name__ == '__main__':
    check_monitored_stocks_for_exit()