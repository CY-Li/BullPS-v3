import json
import os
import sys
from datetime import datetime
from pathlib import Path
import numpy as np

# 加入路徑以便導入同級模組
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from integrated_stock_analyzer import IntegratedStockAnalyzer
from path_manager import path_manager

# --- 配置 ---
EXIT_CONFIDENCE_THRESHOLD = 0.6 # [V4 Optimized] 波段模式門檻由 0.8 調降至 0.6

PORTFOLIO_FILE = path_manager.get_monitored_stocks_path()
ANALYSIS_RESULT_FILE = path_manager.get_analysis_path()
TRADE_HISTORY_FILE = path_manager.get_trade_history_path()

def load_json_file(file_path):
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except:
        return []

def save_json_file(data, file_path):
    class NpEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.integer, np.floating)): return float(obj)
            if isinstance(obj, np.ndarray): return obj.tolist()
            return super(NpEncoder, self).default(obj)
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, cls=NpEncoder)
        return True
    except:
        return False

def evaluate_exit_confidence(trade, latest_analysis):
    """
    [V4 Core] 理由侵蝕模型
    比對進場快照與當前數據，量化「理由消失」程度。
    """
    symbol = trade.get('symbol')
    initial_snapshot = trade.get('initial_analysis_snapshot', {})
    
    # 取得進場理由清單
    entry_reasons = initial_snapshot.get('confidence_factors', [])
    if not entry_reasons:
        # 如果沒有快照，嘗試尋找舊格式的理由
        entry_reasons = trade.get('entry_signal_conditions', [])
        
    current_factors = set(latest_analysis.get('confidence_factors', []))
    
    if not entry_reasons:
        return {
            "exit_confidence": 0.0, 
            "erosion_score": 0.0, 
            "reason": "缺少初始快照",
            "should_exit": False,
            "disappeared": []
        }

    # 1. 理由侵蝕 (Erosion) - 長週期保護短週期
    TIMEFRAME_WEIGHTS = {"月線": 3.0, "週線": 2.0, "日線": 1.0, "default": 1.0}
    total_weight = 0.0
    eroded_weight = 0.0
    disappeared = []

    for reason in entry_reasons:
        weight = TIMEFRAME_WEIGHTS['default']
        for tf, w in TIMEFRAME_WEIGHTS.items():
            if tf in reason: weight = w; break
        
        total_weight += weight
        if reason not in current_factors:
            eroded_weight += weight
            disappeared.append(reason)

    erosion_score = eroded_weight / total_weight if total_weight > 0 else 0
    
    # 2. 新增危險 (Penalties)
    penalty_score = 0.0
    DANGER_SIGNALS = {
        "MACD死叉": 0.6, "價格跌破20日均線": 0.5, "RSI超買風險": 0.4,
        "動量減速": 0.4, "跌破布林下軌": 0.6
    }
    for signal, penalty in DANGER_SIGNALS.items():
        if any(signal in f for f in current_factors):
            penalty_score += penalty

    # 3. 綜合得分
    exit_confidence = (erosion_score * 0.7) + (min(penalty_score, 1.0) * 0.3)
    
    return {
        "symbol": symbol,
        "exit_confidence": round(exit_confidence, 2),
        "erosion_score": round(erosion_score, 2),
        "disappeared": disappeared,
        "should_exit": exit_confidence >= EXIT_CONFIDENCE_THRESHOLD
    }

def check_monitored_stocks_for_exit_v4():
    """V4 版本的持倉檢查邏輯"""
    stocks = load_json_file(PORTFOLIO_FILE)
    if not stocks: return []
    
    analyzer = IntegratedStockAnalyzer()
    results = []
    
    for trade in stocks:
        symbol = trade['symbol']
        data = analyzer.get_stock_data(symbol)
        if data is None: continue
        
        df = analyzer.calculate_technical_indicators(data)
        latest_analysis = analyzer.analyze_stock(symbol)
        
        report = evaluate_exit_confidence(trade, latest_analysis)
        results.append(report)
        
    return results

if __name__ == '__main__':
    res = check_monitored_stocks_for_exit_v4()
    print(json.dumps(res, indent=2))
