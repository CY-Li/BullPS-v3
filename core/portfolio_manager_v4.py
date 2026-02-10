import json
import os
import sys
import numpy as np
from datetime import datetime
from pathlib import Path

def evaluate_exit_confidence(trade, latest_analysis):
    """
    評估單一持倉的出場信心度 (V4 精簡版)
    :param trade: 一筆來自 monitored_stocks.json 的持倉紀錄
    :param latest_analysis: 該股票的最新分析數據
    :return: 一個包含信心度分數和原因的字典
    """
    symbol = trade.get('symbol')

    # 獲取進場時的分析快照和當前分析快照
    initial_snapshot = trade.get('initial_analysis_snapshot', {})
    current_snapshot = latest_analysis # latest_analysis 就是最新的分析快照

    # 從快照或直接從 trade 獲取進場理由
    entry_reasons_list = initial_snapshot.get('confidence_factors', [])
    
    # 兼容 V3 格式
    if not entry_reasons_list:
        entry_reasons_list = trade.get('entry_signal_conditions', [])
        
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
            "should_exit": False,
            "disappeared": [],
            "details": {
                "disappeared_reasons": [],
                "triggered_penalties": [],
                "notes": "缺少進場理由，無法評估。"
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
        "趨勢反轉確認": -0.50, 
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
    base_exit_score = (erosion_score * 0.5) + (min(penalty_score, 1.0) * 0.5)

    # 引入更多出場相關指標的影響
    current_rsi = current_snapshot.get('rsi') or 50
    current_macd = current_snapshot.get('macd') or 0
    current_volume_ratio = current_snapshot.get('volume_ratio') or 1

    # RSI惡化
    if current_rsi > 70: base_exit_score += 0.1
    
    # MACD 轉負
    if current_macd < 0: base_exit_score += 0.1

    # 確保信心度在0到1之間
    exit_confidence = max(0.0, min(1.0, base_exit_score))

    return {
        "symbol": symbol,
        "exit_confidence": round(exit_confidence, 2),
        "erosion_score": round(erosion_score, 2),
        "penalty_score": round(penalty_score, 2),
        "should_exit": exit_confidence >= 0.6,
        "disappeared": disappeared_reasons,
        "details": {
            "disappeared_reasons": disappeared_reasons,
            "triggered_penalties": triggered_penalties
        }
    }
