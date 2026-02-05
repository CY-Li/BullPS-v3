#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BullPS-v3 建倉記錄工具
用於在使用者確認建倉後，將部位加入監控並自動保存當下的分析快照。
"""

import sys
import os
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add core and backend to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core"))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from integrated_stock_analyzer import IntegratedStockAnalyzer
import portfolio_manager

def add_new_position(symbol, entry_price, short_strike, long_strike, expiry, quantity=1, premium=0.0):
    print(f"🚀 正在記錄新倉位: {symbol}...")
    
    # 1. 執行即時分析以獲取快照 (Snapshot)
    print(f"📊 執行 {symbol} 進場前分析 (Snapshot)...")
    analyzer = IntegratedStockAnalyzer()
    analysis_result = analyzer.analyze_stock(symbol)
    
    if not analysis_result:
        print(f"❌ 分析失敗，無法獲取進場快照。建倉終止。")
        return False
        
    # 2. 建構交易記錄
    new_trade = {
        "symbol": symbol,
        "entry_date": datetime.now().strftime("%Y-%m-%d"),
        "entry_price": float(entry_price),
        "quantity": int(quantity),
        "short_strike": float(short_strike),
        "long_strike": float(long_strike),
        "expiry": expiry,
        "entry_premium": float(premium),
        "status": "monitoring",
        # 這裡保存完整的分析快照，包含 confidence_factors (進場理由)
        "initial_analysis_snapshot": analysis_result
    }
    
    # 3. 讀取並更新 monitored_stocks.json
    file_path = Path("BullPS-v3/monitored_stocks.json")
    stocks = []
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            stocks = json.load(f)
            
    # 檢查是否重複
    # 簡單檢查：同 Symbol 且同 Strike 視為加碼 (但在這裡我們簡單處理，視為新的一筆或更新)
    stocks.append(new_trade)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(stocks, f, indent=2, ensure_ascii=False)
        
    print(f"✅ 成功將 {symbol} 加入監控列表。")
    print(f"📝 進場理由 (Snapshot): {', '.join(analysis_result.get('confidence_factors', []))}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Record a new BPS position')
    parser.add_argument('symbol', type=str, help='Stock Symbol (e.g. AAPL)')
    parser.add_argument('price', type=float, help='Entry Price (Underlying)')
    parser.add_argument('short', type=float, help='Short Strike')
    parser.add_argument('long', type=float, help='Long Strike')
    parser.add_argument('expiry', type=str, help='Expiry Date (YYYY-MM-DD)')
    parser.add_argument('--qty', type=int, default=1, help='Quantity')
    parser.add_argument('--premium', type=float, default=0.0, help='Net Credit Premium')

    args = parser.parse_args()
    
    add_new_position(
        args.symbol, 
        args.price, 
        args.short, 
        args.long, 
        args.expiry, 
        args.qty, 
        args.premium
    )
