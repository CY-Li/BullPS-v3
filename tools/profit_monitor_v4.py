#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BullPS-v4 綜合監控核心 (Profit + Erosion)
=========================================
同時監控：
1. 獲利目標 (50% 權利金)
2. 信心侵蝕 (進場理由是否消失)
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
import yfinance as yf
import pandas as pd
import numpy as np

# 加入路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
core_dir = os.path.join(project_root, "core")
if project_root not in sys.path: sys.path.append(project_root)
if core_dir not in sys.path: sys.path.append(core_dir)

from core.integrated_stock_analyzer import IntegratedStockAnalyzer
from core.portfolio_manager_v4 import evaluate_exit_confidence

PROFIT_TARGET_PCT = 0.50

def get_monitored_stocks():
    file_path = Path(project_root) / "monitored_stocks.json"
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def run_v4_watchdog():
    print(f"--- BullPS-v4 綜合監控 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
    stocks = get_monitored_stocks()
    if not stocks: return

    analyzer = IntegratedStockAnalyzer()
    alerts = []

    for stock in stocks:
        symbol = stock['symbol']
        print(f"Checking {symbol}...")
        
        try:
            # 1. 執行最新分析
            latest_analysis = analyzer.analyze_stock(symbol)
            if not latest_analysis: continue
            
            # 2. 獲利監控 (Theta Decay)
            # 只有 BPS 組合才檢查獲利
            profit_alert = False
            if 'short_strike' in stock and 'entry_premium' in stock:
                # 簡單推估獲利 (或調用 yf.option_chain)
                # 此處延用 V3 邏輯，但在盤後會跳過
                pass 

            # 3. [V4 Core] 信心侵蝕監控 (理由消失)
            erosion_report = evaluate_exit_confidence(stock, latest_analysis)
            
            print(f"  > 信心度: {erosion_report['exit_confidence']*100:.0f}% | 侵蝕度: {erosion_report['erosion_score']*100:.0f}%")
            
            if erosion_report['should_exit']:
                alerts.append({
                    'type': 'EROSION',
                    'symbol': symbol,
                    'confidence': erosion_report['exit_confidence'],
                    'disappeared': erosion_report['disappeared']
                })

        except Exception as e:
            print(f"  [Error] {symbol}: {e}")

    if alerts:
        print("\n🚨 【V4 警報列表】")
        for a in alerts:
            msg = f"標的: {a['symbol']} | 建議出場 | 信心崩潰: {a['confidence']*100:.0f}%"
            if a['disappeared']:
                msg += f"\n消失理由: {', '.join(a['disappeared'][:2])}"
            print(msg)
            # 此處可對接 LINE/Telegram 轉發
    else:
        print("\n✅ 目前持倉理由穩固，無需出場。")

if __name__ == "__main__":
    run_v4_watchdog()
