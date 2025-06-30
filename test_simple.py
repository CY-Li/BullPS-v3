#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試簡化版股票分析系統
"""

from stock_analyzer import StockAnalyzer
import json

def test_simple_config():
    """測試簡化配置"""
    print("🧪 測試簡化配置...")
    
    # 建立分析器
    analyzer = StockAnalyzer()
    
    print(f"✅ 成功載入 {len(analyzer.stocks)} 支股票")
    print("股票列表：")
    for i, symbol in enumerate(analyzer.stocks, 1):
        print(f"  {i}. {symbol}")
    
    print(f"\n設定：{analyzer.settings}")

def test_single_stock():
    """測試單一股票分析"""
    print("\n🧪 測試單一股票分析...")
    
    analyzer = StockAnalyzer()
    
    # 測試第一支股票
    if analyzer.stocks:
        symbol = analyzer.stocks[0]
        print(f"測試股票：{symbol}")
        
        result = analyzer.calculate_long_days(symbol)
        
        if result:
            print(f"✅ 成功分析 {result['symbol']}")
            print(f"   股票名稱: {result.get('name', 'N/A')}")
            print(f"   市場: {result.get('market', 'N/A')}")
            print(f"   Long Days: {result.get('long_days', 'N/A')}")
            print(f"   進場建議: {result.get('entry_opportunity', 'N/A')}")
        else:
            print("❌ 分析失敗")

def main():
    """主測試函數"""
    print("🚀 開始測試簡化版股票分析系統...")
    
    # 檢查必要檔案
    try:
        with open('stock_watchlist.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            print("✅ 成功載入 stock_watchlist.json")
    except FileNotFoundError:
        print("❌ 找不到 stock_watchlist.json 檔案")
        return
    except json.JSONDecodeError:
        print("❌ stock_watchlist.json 格式錯誤")
        return
    
    # 執行測試
    test_simple_config()
    test_single_stock()
    
    print("\n✅ 測試完成！")

if __name__ == "__main__":
    main() 