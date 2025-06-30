#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試短期趨勢反轉識別功能
驗證「被低估、可抄底，並確定短期趨勢正要反轉或已反轉」的需求
"""

import pandas as pd
import numpy as np
from integrated_stock_analyzer import IntegratedStockAnalyzer

def test_trend_reversal_detection():
    """測試趨勢反轉識別功能"""
    print("🔄 測試短期趨勢反轉識別功能")
    print("=" * 60)
    
    # 初始化分析器
    analyzer = IntegratedStockAnalyzer()
    
    # 測試股票
    test_symbols = ['AAPL', 'NVDA', 'SPY', 'TSLA']
    
    for symbol in test_symbols:
        print(f"\n📊 測試 {symbol} 趨勢反轉識別:")
        print("-" * 50)
        
        try:
            # 獲取數據
            df = analyzer.get_stock_data(symbol)
            if df is None or df.empty:
                print(f"❌ 無法獲取 {symbol} 數據")
                continue
            
            # 計算技術指標
            df = analyzer.calculate_technical_indicators(df)
            
            # 顯示趨勢反轉指標
            print(f"趨勢反轉確認: {df['Trend_Reversal_Confirmation'].iloc[-1]:.0f}分")
            print(f"反轉強度: {df['Reversal_Strength'].iloc[-1]:.0f}分")
            print(f"反轉可信度: {df['Reversal_Reliability'].iloc[-1]:.0f}分")
            print(f"短期動能轉折: {df['Short_Term_Momentum_Turn'].iloc[-1]:.0f}分")
            print(f"價格結構反轉: {df['Price_Structure_Reversal'].iloc[-1]:.0f}分")
            
            # 檢測多頭訊號
            signals = analyzer.detect_bullish_signals(df)
            print(f"多頭訊號數量: {len(signals)}")
            
            if signals:
                latest_signal = signals[-1]
                print(f"最新訊號日期: {latest_signal['date'].strftime('%Y-%m-%d')}")
                print(f"訊號條件: {latest_signal['conditions']}")
                
                # 檢查是否包含趨勢反轉條件
                reversal_conditions = [
                    "趨勢反轉確認", "反轉強度強勁", "反轉可信度高", 
                    "短期動能轉折", "價格結構反轉"
                ]
                
                has_reversal = any(cond in latest_signal['conditions'] for cond in reversal_conditions)
                if has_reversal:
                    print("✅ 包含趨勢反轉條件")
                else:
                    print("❌ 未包含趨勢反轉條件")
                
                # 顯示反轉相關數值
                if 'trend_reversal_confirmation' in latest_signal:
                    print(f"訊號趨勢反轉確認: {latest_signal['trend_reversal_confirmation']:.0f}分")
                if 'reversal_strength' in latest_signal:
                    print(f"訊號反轉強度: {latest_signal['reversal_strength']:.0f}分")
                if 'reversal_reliability' in latest_signal:
                    print(f"訊號反轉可信度: {latest_signal['reversal_reliability']:.0f}分")
            
            # 評估進場機會
            entry_advice, confidence_score, confidence_level, confidence_factors = analyzer.assess_entry_opportunity(df)
            print(f"進場建議: {entry_advice}")
            print(f"信心度: {confidence_score:.0f}/100 ({confidence_level})")
            
            # 顯示趨勢反轉相關的信心度因素
            reversal_factors = [f for f in confidence_factors if "反轉" in f or "轉折" in f]
            if reversal_factors:
                print(f"趨勢反轉因素: {', '.join(reversal_factors)}")
            
        except Exception as e:
            print(f"❌ 分析 {symbol} 時發生錯誤: {e}")
    
    print("\n✅ 趨勢反轉識別測試完成！")

def test_undervalued_reversal_stocks():
    """測試被低估且趨勢反轉的股票"""
    print("\n🎯 測試被低估且趨勢反轉的股票:")
    print("-" * 50)
    
    analyzer = IntegratedStockAnalyzer()
    
    # 分析所有股票
    results = analyzer.analyze_watchlist()
    
    # 篩選被低估且趨勢反轉的股票
    undervalued_reversal = []
    
    for _, row in results.iterrows():
        if pd.notna(row['long_days']):
            # 檢查是否被低估（RSI < 50 或接近布林下軌）
            is_undervalued = (row['rsi'] < 50 or 
                            row.get('distance_to_signal', 0) > 0)  # 距離抄底價有空間
            
            # 檢查是否有趨勢反轉跡象
            has_reversal = False
            confidence_factors = row.get('confidence_factors', [])
            reversal_keywords = ["反轉", "轉折", "確認"]
            has_reversal = any(keyword in str(factor) for factor in confidence_factors for keyword in reversal_keywords)
            
            if is_undervalued and has_reversal:
                undervalued_reversal.append(row)
    
    print(f"找到 {len(undervalued_reversal)} 檔被低估且趨勢反轉的股票:")
    
    for stock in undervalued_reversal:
        print(f"\n🏆 {stock['symbol']} ({stock['name']})")
        print(f"   RSI: {stock['rsi']:.1f}")
        print(f"   進場建議: {stock['entry_opportunity']}")
        print(f"   信心度: {stock['confidence_score']:.0f}/100")
        print(f"   Long Days: {stock['long_days']} 天")
        
        # 顯示趨勢反轉因素
        confidence_factors = stock.get('confidence_factors', [])
        reversal_factors = [f for f in confidence_factors if "反轉" in f or "轉折" in f]
        if reversal_factors:
            print(f"   趨勢反轉因素: {', '.join(reversal_factors)}")

if __name__ == "__main__":
    test_trend_reversal_detection()
    test_undervalued_reversal_stocks() 