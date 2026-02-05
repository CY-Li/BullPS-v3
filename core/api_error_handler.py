#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API錯誤處理器
處理Yahoo Finance API錯誤和數據問題
"""

import yfinance as yf
import pandas as pd
import time
import warnings
from datetime import datetime, timedelta
import requests

warnings.filterwarnings('ignore')

class APIErrorHandler:
    def __init__(self):
        self.failed_symbols = set()
        self.retry_count = {}
        self.max_retries = 3
        self.delay_between_requests = 0.1  # 100ms延遲
        
    def safe_download_data(self, symbol, period='2y', interval='1d', max_retries=3):
        """
        安全下載股票數據，包含錯誤處理和重試機制
        """
        if symbol in self.failed_symbols:
            return None
            
        for attempt in range(max_retries):
            try:
                # 添加延遲避免API限制
                time.sleep(self.delay_between_requests)
                
                ticker = yf.Ticker(symbol)
                data = ticker.history(period=period, interval=interval)
                
                if data.empty:
                    print(f"  ⚠️  {symbol}: 無數據返回")
                    if attempt == max_retries - 1:
                        self.failed_symbols.add(symbol)
                    continue
                
                # 檢查數據質量
                if len(data) < 30:  # 至少需要30天數據
                    print(f"  ⚠️  {symbol}: 數據不足 ({len(data)}天)")
                    if attempt == max_retries - 1:
                        self.failed_symbols.add(symbol)
                    continue
                
                # 檢查是否有有效的價格數據
                if data['Close'].isna().all():
                    print(f"  ⚠️  {symbol}: 價格數據全部為空")
                    if attempt == max_retries - 1:
                        self.failed_symbols.add(symbol)
                    continue
                
                return data
                
            except Exception as e:
                error_msg = str(e)
                
                # 處理不同類型的錯誤
                if "404" in error_msg or "delisted" in error_msg.lower():
                    print(f"  ❌ {symbol}: 股票可能已下市或代號錯誤")
                    self.failed_symbols.add(symbol)
                    break
                elif "429" in error_msg or "rate limit" in error_msg.lower():
                    print(f"  ⏳ {symbol}: API限制，等待重試...")
                    time.sleep(5)  # 等待5秒後重試
                elif "timeout" in error_msg.lower():
                    print(f"  ⏳ {symbol}: 請求超時，重試中...")
                    time.sleep(2)
                else:
                    print(f"  ❌ {symbol}: 未知錯誤 - {error_msg}")
                
                if attempt == max_retries - 1:
                    print(f"  ❌ {symbol}: 達到最大重試次數，跳過")
                    self.failed_symbols.add(symbol)
                else:
                    print(f"  🔄 {symbol}: 重試 {attempt + 1}/{max_retries}")
                    time.sleep(1)
        
        return None
    
    def validate_symbol(self, symbol):
        """
        驗證股票代號是否有效
        """
        try:
            # 簡單的代號格式檢查
            if not symbol or len(symbol) < 1 or len(symbol) > 10:
                return False
            
            # 檢查是否包含無效字符
            invalid_chars = ['$', ' ', '\n', '\t']
            if any(char in symbol for char in invalid_chars):
                return False
            
            return True
            
        except Exception:
            return False
    
    def clean_symbol_list(self, symbols):
        """
        清理股票代號列表，移除無效代號
        """
        cleaned_symbols = []
        
        for symbol in symbols:
            if isinstance(symbol, str):
                # 清理代號
                cleaned_symbol = symbol.strip().upper()
                
                # 移除特殊前綴
                if cleaned_symbol.startswith('$'):
                    cleaned_symbol = cleaned_symbol[1:]
                
                # 驗證代號
                if self.validate_symbol(cleaned_symbol):
                    cleaned_symbols.append(cleaned_symbol)
                else:
                    print(f"  ❌ 無效股票代號: {symbol}")
            else:
                print(f"  ❌ 非字符串股票代號: {symbol}")
        
        return cleaned_symbols
    
    def batch_download_with_progress(self, symbols, period='2y', interval='1d'):
        """
        批量下載股票數據，顯示進度
        """
        print(f"開始下載 {len(symbols)} 支股票的數據...")
        
        # 清理股票代號
        cleaned_symbols = self.clean_symbol_list(symbols)
        print(f"有效股票代號: {len(cleaned_symbols)}")
        
        successful_data = {}
        failed_count = 0
        
        for i, symbol in enumerate(cleaned_symbols):
            print(f"[{i+1}/{len(cleaned_symbols)}] 下載 {symbol}...")
            
            data = self.safe_download_data(symbol, period, interval)
            
            if data is not None:
                successful_data[symbol] = data
                print(f"  ✅ {symbol}: 成功 ({len(data)}天數據)")
            else:
                failed_count += 1
        
        print(f"\n下載完成:")
        print(f"  ✅ 成功: {len(successful_data)} 支股票")
        print(f"  ❌ 失敗: {failed_count} 支股票")
        
        if self.failed_symbols:
            print(f"\n失敗的股票代號:")
            for symbol in sorted(self.failed_symbols):
                print(f"  - {symbol}")
        
        return successful_data
    
    def get_market_status(self):
        """
        檢查市場狀態
        """
        try:
            # 使用SPY作為市場指標
            spy = yf.Ticker("SPY")
            data = spy.history(period="1d")
            
            if not data.empty:
                return {
                    'status': 'active',
                    'last_price': data['Close'].iloc[-1],
                    'last_update': data.index[-1]
                }
            else:
                return {'status': 'unknown', 'message': '無法獲取市場數據'}
                
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def suggest_alternative_symbols(self, failed_symbol):
        """
        為失敗的股票代號建議替代方案
        """
        suggestions = []
        
        # 常見的代號變化
        if failed_symbol.endswith('.'):
            suggestions.append(failed_symbol[:-1])
        
        if not failed_symbol.endswith('.TO') and len(failed_symbol) <= 5:
            suggestions.append(failed_symbol + '.TO')  # 多倫多交易所
        
        if not failed_symbol.endswith('.L') and len(failed_symbol) <= 5:
            suggestions.append(failed_symbol + '.L')   # 倫敦交易所
        
        return suggestions

def test_api_handler():
    """
    測試API錯誤處理器
    """
    print("=== API錯誤處理器測試 ===")
    
    handler = APIErrorHandler()
    
    # 測試股票代號
    test_symbols = ['AAPL', 'INVALID_SYMBOL', 'TSLA', '$UNKNOWN', 'MSFT']
    
    print("1. 測試股票代號清理:")
    cleaned = handler.clean_symbol_list(test_symbols)
    print(f"原始: {test_symbols}")
    print(f"清理後: {cleaned}")
    
    print("\n2. 測試市場狀態:")
    market_status = handler.get_market_status()
    print(f"市場狀態: {market_status}")
    
    print("\n3. 測試單一股票下載:")
    data = handler.safe_download_data('AAPL', period='30d')
    if data is not None:
        print(f"AAPL數據: {len(data)}天")
    else:
        print("AAPL下載失敗")
    
    print("\n4. 測試無效股票:")
    invalid_data = handler.safe_download_data('INVALID_SYMBOL')
    print(f"無效股票結果: {invalid_data}")
    
    print(f"\n失敗的股票: {handler.failed_symbols}")

if __name__ == "__main__":
    test_api_handler()
