#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BullPS-v3 完整分析器執行腳本
用於手動執行全市場掃描，直接輸出 IntegratedStockAnalyzer 的分析結果。
"""

import sys
import os
import json
import time
from datetime import datetime

# Add core to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "core"))

from integrated_stock_analyzer import IntegratedStockAnalyzer

# 核心清單 (同 run_scan_now.py)
CORE_WATCHLIST = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX", "AMD", 
    "DIS", "BA", "JPM", "WMT", "V", "MA", "KO", "PEP", "COST", "INTC", "PYPL",
    "CRM", "ADBE", "QCOM", "TXN", "HON", "UNH", "PG", "XOM", "CVX", "MRK"
]

def main():
    print(f"🚀 開始執行 IntegratedStockAnalyzer 完整掃描... [Date: {datetime.now().strftime('%Y-%m-%d')}]")
    
    analyzer = IntegratedStockAnalyzer()
    
    # 讀取完整的監控清單
    try:
        watchlist_path = "BullPS-v3/stock_watchlist.json"
        with open(watchlist_path, 'r', encoding='utf-8') as f:
            full_list = json.load(f).get('stocks', [])
        scan_list = full_list if full_list else CORE_WATCHLIST
        print(f"📊 掃描清單: {len(scan_list)} 支股票")
    except Exception as e:
        print(f"⚠️ 無法讀取清單，使用核心清單: {e}")
        scan_list = CORE_WATCHLIST

    candidates = []
    
    for i, symbol in enumerate(scan_list):
        # 顯示進度
        print(f"[{i+1}/{len(scan_list)}] Analyzing {symbol}...", end='\r')
        
        result = analyzer.analyze_stock(symbol)
        if result:
            # 儲存重要結果
            candidates.append(result)
            
            # 即時顯示高分股
            if result['composite_score'] >= 80:
                 print(f"  ✨ {symbol} Found! Score: {result['composite_score']}, Conf: {result['confidence_level']}%")

    # 排序
    candidates.sort(key=lambda x: x['composite_score'], reverse=True)
    
    # 輸出前 10 名
    print("\n\n🏆 Top 10 Integrated Analyzer Results:")
    print(f"{'Symbol':<8} {'Score':<6} {'Conf%':<6} {'Price':<10} {'Factors'}")
    print("-" * 60)
    
    top_candidates = candidates[:10]
    for cand in top_candidates:
        factors = ", ".join(cand['confidence_factors'][:2]) # 只顯示前兩個理由
        print(f"{cand['symbol']:<8} {cand['composite_score']:<6.1f} {cand['confidence_level']:<6} ${cand['current_price']:<9.2f} {factors}")

    # 輸出 JSON 供比對
    print("\nANALYZER_RESULTS_START")
    print(json.dumps([{
        'symbol': c['symbol'],
        'score': c['composite_score'],
        'confidence': c['confidence_level'],
        'price': c['current_price'],
        'reasons': c['confidence_factors']
    } for c in top_candidates], indent=2))
    print("ANALYZER_RESULTS_END")

if __name__ == "__main__":
    main()
