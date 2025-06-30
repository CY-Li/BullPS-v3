#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試改進後的整合股票分析器
驗證多頭訊號偵測和信心度計算的改進效果
"""

import pandas as pd
import numpy as np
from integrated_stock_analyzer import IntegratedStockAnalyzer
import json

def test_improvements():
    """測試改進後的功能"""
    print("🧪 測試改進後的整合股票分析器")
    print("=" * 60)
    
    # 初始化分析器
    analyzer = IntegratedStockAnalyzer()
    
    # 測試股票
    test_symbols = ['AAPL', 'TSLA', 'NVDA']
    
    for symbol in test_symbols:
        print(f"\n📊 測試 {symbol}:")
        print("-" * 40)
        
        try:
            # 獲取數據
            df = analyzer.get_stock_data(symbol)
            if df is None or df.empty:
                print(f"❌ 無法獲取 {symbol} 數據")
                continue
            
            # 計算技術指標
            df = analyzer.calculate_technical_indicators(df)
            
            # 檢測多頭訊號
            signals = analyzer.detect_bullish_signals(df)
            print(f"多頭訊號數量: {len(signals)}")
            
            if signals:
                latest_signal = signals[-1]
                print(f"最新訊號日期: {latest_signal['date'].strftime('%Y-%m-%d')}")
                print(f"訊號條件: {latest_signal['conditions']}")
                print(f"訊號價格: ${latest_signal['price']:.2f}")
                
                # 直接用analyze_stock取得long_days等資訊
                stock_result = analyzer.analyze_stock(symbol)
                long_days = stock_result.get('long_days')
                print(f"Long Days: {long_days} 天")
                long_signal_price = stock_result.get('long_signal_price')
                print(f"Long Signal Price: ${long_signal_price:.2f}")
                entry_advice = stock_result.get('entry_opportunity')
                confidence_score = stock_result.get('confidence_score')
                confidence_level = stock_result.get('confidence_level')
                confidence_factors = stock_result.get('confidence_factors')
                print(f"進場建議: {entry_advice}")
                print(f"信心度: {confidence_score:.1f}/100 ({confidence_level})")
                print(f"主要因素: {confidence_factors[:3]}...")  # 只顯示前3個
                composite_score = stock_result.get('composite_score', 0)
                print(f"綜合評分: {composite_score:.1f}/100")
            
            else:
                print("❌ 未檢測到多頭訊號")
            
        except Exception as e:
            print(f"❌ 分析 {symbol} 時發生錯誤: {e}")
    
    print("\n✅ 改進測試完成！")

def test_signal_filtering():
    """測試訊號過濾機制"""
    print("\n🔍 測試訊號過濾機制:")
    print("-" * 40)
    
    analyzer = IntegratedStockAnalyzer()
    
    # 測試AAPL的訊號過濾
    df = analyzer.get_stock_data('AAPL')
    if df is not None and not df.empty:
        df = analyzer.calculate_technical_indicators(df)
        signals = analyzer.detect_bullish_signals(df)
        
        print(f"原始訊號數量: {len(signals)}")
        
        if len(signals) > 1:
            # 檢查時間過濾
            for i in range(1, len(signals)):
                days_diff = (signals[i]['date'] - signals[i-1]['date']).days
                print(f"訊號間隔: {days_diff} 天")
        
        # 檢查最近的趨勢過濾
        if len(df) >= 5:
            recent_trend = df['Close'].iloc[-5:].pct_change().mean()
            print(f"近5日趨勢: {recent_trend:.2%}")

if __name__ == "__main__":
    test_improvements()
    test_signal_filtering() 