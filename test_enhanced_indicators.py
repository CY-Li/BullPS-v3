#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試增強版技術指標
驗證新增的趨勢持續性、動能和風險管理指標
"""

import pandas as pd
import numpy as np
from integrated_stock_analyzer import IntegratedStockAnalyzer

def test_enhanced_indicators():
    """測試增強版指標"""
    print("🧪 測試增強版技術指標")
    print("=" * 60)
    
    # 初始化分析器
    analyzer = IntegratedStockAnalyzer()
    
    # 測試股票
    test_symbols = ['AAPL', 'NVDA', 'SPY']
    
    for symbol in test_symbols:
        print(f"\n📊 測試 {symbol} 增強版指標:")
        print("-" * 50)
        
        try:
            # 獲取數據
            df = analyzer.get_stock_data(symbol)
            if df is None or df.empty:
                print(f"❌ 無法獲取 {symbol} 數據")
                continue
            
            # 計算技術指標
            df = analyzer.calculate_technical_indicators(df)
            
            # 顯示新增指標
            print(f"ADX趨勢強度: {df['ADX'].iloc[-1]:.1f}")
            print(f"均線多頭排列強度: {df['MA_Bullish_Strength'].iloc[-1]:.0f}%")
            print(f"價格通道斜率: {df['Price_Channel_Slope'].iloc[-1]:.2f}%")
            print(f"成交量趨勢配合度: {df['Volume_Trend_Alignment'].iloc[-1]:.0f}分")
            print(f"動量加速度: {df['Momentum_Acceleration'].iloc[-1]:.4f}")
            print(f"RSI斜率: {df['RSI_Slope'].iloc[-1]:.2f}")
            print(f"MACD斜率: {df['MACD_Slope'].iloc[-1]:.2f}")
            print(f"相對強度: {df['Relative_Strength'].iloc[-1]:.2f}%")
            print(f"上漲動能延續性: {df['Uptrend_Continuity'].iloc[-1]:.0f}分")
            print(f"波動率比率: {df['Volatility_Ratio'].iloc[-1]:.4f}")
            print(f"支撐位可靠性: {df['Support_Reliability'].iloc[-1]:.0f}%")
            print(f"風險報酬比: {df['Risk_Reward_Ratio'].iloc[-1]:.2f}")
            
            # 檢測多頭訊號
            signals = analyzer.detect_bullish_signals(df)
            print(f"多頭訊號數量: {len(signals)}")
            
            if signals:
                latest_signal = signals[-1]
                print(f"最新訊號條件: {latest_signal['conditions']}")
                print(f"訊號ADX: {latest_signal.get('adx', 'N/A')}")
                print(f"訊號均線強度: {latest_signal.get('ma_bullish_strength', 'N/A')}")
                print(f"訊號動能延續性: {latest_signal.get('uptrend_continuity', 'N/A')}")
                print(f"訊號風險報酬比: {latest_signal.get('risk_reward_ratio', 'N/A')}")
            
        except Exception as e:
            print(f"❌ 分析 {symbol} 時發生錯誤: {e}")
    
    print("\n✅ 增強版指標測試完成！")

def test_risk_management():
    """測試風險管理功能"""
    print("\n🛡️ 測試風險管理功能:")
    print("-" * 40)
    
    analyzer = IntegratedStockAnalyzer()
    
    # 測試AAPL的風險管理
    df = analyzer.get_stock_data('AAPL')
    if df is not None and not df.empty:
        df = analyzer.calculate_technical_indicators(df)
        
        current_price = df['Close'].iloc[-1]
        stop_loss = df['Dynamic_Stop_Loss'].iloc[-1]
        target_price = df['BB_Upper'].iloc[-1]
        
        print(f"當前價格: ${current_price:.2f}")
        print(f"動態停損: ${stop_loss:.2f}")
        print(f"目標價位: ${target_price:.2f}")
        print(f"潛在損失: {((current_price - stop_loss) / current_price * 100):.1f}%")
        print(f"潛在獲利: {((target_price - current_price) / current_price * 100):.1f}%")
        print(f"風險報酬比: {df['Risk_Reward_Ratio'].iloc[-1]:.2f}")
        print(f"支撐位可靠性: {df['Support_Reliability'].iloc[-1]:.0f}%")

if __name__ == "__main__":
    test_enhanced_indicators()
    test_risk_management() 