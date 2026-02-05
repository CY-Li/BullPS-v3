#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BullPS-v3 停利警示系統 (OpenClaw 工具版)
修正了 CLI 呼叫問題，改用 OpenClaw 內建機制發送通知。
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
import yfinance as yf
import pandas as pd
import numpy as np

# Add backend to path for portfolio_manager
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
try:
    import portfolio_manager
except ImportError as e:
    print(f"Warning: Could not import portfolio_manager: {e}")
    portfolio_manager = None

# 設定
LINE_TARGET = 'U0aae8e070107ce5b7cf7f02cf67ea911'
PROFIT_TARGET_PCT = 0.50 # 50% 獲利目標
EXIT_CONFIDENCE_THRESHOLD = 0.70 # 信心度 > 70% 建議出場 (Thesis Breach)

def get_monitored_stocks():
    file_path = Path("BullPS-v3/monitored_stocks.json")
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def check_and_report():
    print(f"--- BullPS-v3 獲利掃描 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
    stocks = get_monitored_stocks()
    if not stocks:
        print("沒有監控中的標的。")
        return []

    alerts = []
    for stock in stocks:
        symbol = stock['symbol']
        print(f"Checking {symbol}...")
        
        # 1. 執行技術面與論點檢測 (Thesis Check)
        thesis_alert = None
        if portfolio_manager:
            try:
                # 獲取最新分析 (若無則即時分析)
                latest_analysis = portfolio_manager.get_latest_analysis(symbol)
                if not latest_analysis:
                    print(f"  - Re-analyzing {symbol} for thesis check...")
                    latest_analysis = portfolio_manager.re_analyze_missing_stock(symbol)
                
                if latest_analysis:
                    # 評估出場信心
                    conf_result = portfolio_manager.evaluate_exit_confidence(stock, latest_analysis)
                    exit_conf = conf_result.get('exit_confidence', 0.0)
                    
                    if exit_conf >= EXIT_CONFIDENCE_THRESHOLD:
                        reasons = conf_result.get('details', {}).get('triggered_penalties', [])
                        notes = conf_result.get('details', {}).get('notes', '')
                        print(f"  🚨 Thesis Breach Detected! Confidence: {exit_conf*100:.0f}%")
                        thesis_alert = {
                            'type': 'thesis_breach',
                            'exit_confidence': exit_conf,
                            'reasons': reasons,
                            'notes': notes
                        }
            except Exception as e:
                print(f"  - Thesis check failed: {e}")

        # 2. 執行 BPS 獲利檢測 (Profit Check)
        profit_alert = None
        # Skip if not an active option position (missing strike info)
        if 'short_strike' in stock and 'long_strike' in stock:
            short_strike = stock['short_strike']
            long_strike = stock['long_strike']
            expiry = stock['expiry']
            entry_premium = stock.get('entry_premium', 1.0)
            
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='1d')
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                    
                    options = ticker.option_chain(expiry)
                    puts = options.puts
                    
                    def get_interpolated_price(target_strike):
                        if target_strike in puts['strike'].values:
                            row = puts[puts['strike'] == target_strike].iloc[0]
                            if row['bid'] > 0 and row['ask'] > 0:
                                spread = row['ask'] - row['bid']
                                if spread > (row['bid'] + row['ask']) / 2 * 0.5: 
                                    return None
                                return (row['bid'] + row['ask']) / 2
                            return None
                        
                        sorted_puts = puts.sort_values('strike')
                        lower = sorted_puts[sorted_puts['strike'] < target_strike].tail(1)
                        upper = sorted_puts[sorted_puts['strike'] > target_strike].head(1)
                        
                        if not lower.empty and not upper.empty:
                            l_row, u_row = lower.iloc[0], upper.iloc[0]
                            if l_row['bid'] > 0 and l_row['ask'] > 0 and u_row['bid'] > 0 and u_row['ask'] > 0:
                                l_p = (l_row['bid'] + l_row['ask'])/2
                                u_p = (u_row['bid'] + u_row['ask'])/2
                                ratio = (target_strike - l_row['strike']) / (u_row['strike'] - l_row['strike'])
                                return l_p + ratio * (u_p - l_p)
                        return None

                    s_price = get_interpolated_price(short_strike)
                    l_price = get_interpolated_price(long_strike)
                    
                    if s_price is not None and l_price is not None:
                        current_spread_value = max(0.01, s_price - l_price)
                        profit_pct = (entry_premium - current_spread_value) / entry_premium
                        
                        print(f"  - Profit: {profit_pct*100:.1f}% (Price: {current_price:.2f})")
                        
                        if profit_pct >= PROFIT_TARGET_PCT:
                            profit_alert = {
                                'type': 'profit_target',
                                'profit_pct': profit_pct,
                                'current_price': current_price
                            }
                    else:
                        # Fallback if options data fails but we have price
                        print(f"  - Options data unavailable, using price only.")
                        
            except Exception as e:
                print(f"  - Profit check error: {e}")
        
        # Combine alerts
        if profit_alert:
            alerts.append({
                'symbol': symbol,
                'reason': 'profit_target',
                'data': profit_alert
            })
        elif thesis_alert: # Thesis breach is prioritized if profit not met
            alerts.append({
                'symbol': symbol,
                'reason': 'thesis_breach',
                'data': thesis_alert,
                'current_price': stock.get('current_analysis_snapshot', {}).get('current_price', 0)
            })
    
    return alerts
    
    return alerts

if __name__ == "__main__":
    results = check_and_report()
    if results:
        # 輸出 JSON 供外部擷取
        print("ALERTS_START")
        print(json.dumps(results))
        print("ALERTS_END")
