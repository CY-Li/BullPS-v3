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
import warnings
warnings.filterwarnings('ignore')

# 加入路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
core_dir = os.path.join(project_root, "core")
if project_root not in sys.path: sys.path.append(project_root)
if core_dir not in sys.path: sys.path.append(core_dir)

from core.integrated_stock_analyzer import IntegratedStockAnalyzer
from core.portfolio_manager_v4 import evaluate_exit_confidence
from core.options_helper import get_real_premium

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
    if not stocks: 
        print("沒有監控中的持倉。")
        return

    analyzer = IntegratedStockAnalyzer()
    alerts = []
    
    # 檢查是否在交易時間 (簡單判斷: 週一至週五 9:30-16:00 ET 轉換為本地時間)
    # 這裡不做嚴格限制，允許隨時檢查

    for stock in stocks:
        symbol = stock.get('symbol')
        print(f"Checking {symbol}...", end='\r')
        
        try:
            # 1. 執行最新分析 (用於 Erosion)
            latest_analysis = analyzer.analyze_stock(symbol)
            if not latest_analysis: continue
            
            # 2. 獲利監控 (Theta Decay / Price Action)
            profit_alert = False
            current_profit_pct = 0.0
            
            # 必須要有期權資訊才能檢查獲利
            if all(k in stock for k in ('short_strike', 'long_strike', 'expiry', 'entry_credit')):
                try:
                    # 獲取當前平倉成本
                    premium_data, err = get_real_premium(
                        symbol, 
                        stock['short_strike'], 
                        stock['long_strike'], 
                        stock['expiry']
                    )
                    
                    if premium_data:
                        # 當前平倉成本 (Debit to Close) = Credit (Short - Long)
                        # 如果 current_credit 變小，代表獲利
                        current_credit = premium_data['credit']
                        entry_credit = stock['entry_credit']
                        
                        if entry_credit > 0:
                            profit = entry_credit - current_credit
                            current_profit_pct = profit / entry_credit
                            
                            if current_profit_pct >= PROFIT_TARGET_PCT:
                                profit_alert = True
                                alerts.append({
                                    'type': 'PROFIT',
                                    'symbol': symbol,
                                    'profit_pct': current_profit_pct,
                                    'message': f"獲利達標 ({current_profit_pct*100:.1f}%)"
                                })
                            
                            print(f"  {symbol} 獲利狀態: {current_profit_pct*100:.1f}% (目標 50%)", end='')
                except Exception as e:
                    print(f"  [Profit Check Error] {e}", end='')

            # 3. [V4 Core] 信心侵蝕監控 (理由消失)
            erosion_report = evaluate_exit_confidence(stock, latest_analysis)
            
            # 如果獲利已經達標，Erosion 就不那麼重要了，但還是可以顯示
            if erosion_report['should_exit'] and not profit_alert:
                alerts.append({
                    'type': 'EROSION',
                    'symbol': symbol,
                    'confidence': erosion_report['exit_confidence'],
                    'disappeared': erosion_report['disappeared'],
                    'message': f"信心崩潰 (剩餘 {erosion_report['exit_confidence']*100:.0f}%)"
                })

            print(f" | 信心度: {erosion_report['exit_confidence']*100:.0f}%")

        except Exception as e:
            print(f"\n  [Error] {symbol}: {e}")

    if alerts:
        print("\n🚨 【V4 警報列表】")
        for a in alerts:
            if a['type'] == 'PROFIT':
                print(f"💰 {a['symbol']} | {a['message']} | 建議: 獲利了結")
            elif a['type'] == 'EROSION':
                msg = f"⚠️ {a['symbol']} | {a['message']} | 建議: 停損/出場"
                if a.get('disappeared'):
                    msg += f"\n   消失理由: {', '.join(a['disappeared'][:2])}"
                print(msg)
    else:
        print("\n✅ 目前持倉狀況穩定 (未達停利點且理由穩固)。")

if __name__ == "__main__":
    run_v4_watchdog()
