#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票觀察池分析程式
資深股票交易員設計的技術分析系統
用於找出被低估、抄底、有高機率上漲修正的股票
"""

import json
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
import time
import requests
warnings.filterwarnings('ignore')

class StockAnalyzer:
    def __init__(self, watchlist_file='stock_watchlist.json'):
        """
        初始化股票分析器
        
        Args:
            watchlist_file (str): 觀察池JSON檔案路徑
        """
        self.watchlist_file = watchlist_file
        self.watchlist = self.load_watchlist()
        self.settings = self.watchlist.get('settings', {})
        self.stocks = self.watchlist.get('stocks', [])
        
    def load_watchlist(self):
        """載入觀察池配置"""
        try:
            with open(self.watchlist_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"錯誤：找不到 {self.watchlist_file} 檔案")
            return {"stocks": [], "settings": {}}
    
    def get_stock_info(self, symbol):
        """
        獲取股票基本資訊
        
        Args:
            symbol (str): 股票代號
            
        Returns:
            dict: 股票資訊
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # 嘗試獲取股票資訊
            info = ticker.info
            
            # 嘗試獲取股票名稱
            name = info.get('longName', info.get('shortName', symbol))
            
            # 判斷市場
            if '.TW' in symbol:
                market = 'TWSE'
            elif '.HK' in symbol:
                market = 'HKEX'
            else:
                market = 'US'
            
            return {
                'symbol': symbol,
                'name': name,
                'market': market
            }
        except Exception as e:
            print(f"  ⚠️ 無法獲取 {symbol} 的詳細資訊：{str(e)}")
            # 如果無法獲取資訊，使用預設值
            if '.TW' in symbol:
                market = 'TWSE'
            elif '.HK' in symbol:
                market = 'HKEX'
            else:
                market = 'US'
                
            return {
                'symbol': symbol,
                'name': symbol,
                'market': market
            }
    
    def get_stock_data(self, symbol, period='60d', max_retries=3):
        """
        獲取股票歷史數據
        
        Args:
            symbol (str): 股票代號
            period (str): 分析期間
            max_retries (int): 最大重試次數
            
        Returns:
            pd.DataFrame: 股票歷史數據
        """
        for attempt in range(max_retries):
            try:
                print(f"  嘗試獲取 {symbol} 數據 (第 {attempt + 1} 次)...")
                
                # 建立ticker物件並設定連線參數
                ticker = yf.Ticker(symbol)
                
                # 嘗試獲取歷史數據，使用基本參數
                data = ticker.history(
                    period=period, 
                    timeout=60
                )
                
                if data.empty:
                    print(f"  警告：{symbol} 沒有數據")
                    return None
                
                print(f"  ✅ 成功獲取 {symbol} 數據，共 {len(data)} 筆記錄")
                print(f"     最新日期：{data.index[-1].strftime('%Y-%m-%d')}")
                print(f"     最新價格：${data['Close'].iloc[-1]:.2f}")
                return data
                
            except Exception as e:
                error_msg = str(e)
                print(f"  ❌ 第 {attempt + 1} 次嘗試失敗：{error_msg}")
                
                # 根據錯誤類型決定重試策略
                if "Expecting value" in error_msg or "JSON" in error_msg:
                    print(f"  🔄 JSON解析錯誤，可能是網路問題，等待 5 秒後重試...")
                    time.sleep(5)
                elif "timeout" in error_msg.lower():
                    print(f"  ⏳ 連線超時，等待 3 秒後重試...")
                    time.sleep(3)
                elif "rate limit" in error_msg.lower():
                    print(f"  🚫 API限制，等待 10 秒後重試...")
                    time.sleep(10)
                else:
                    print(f"  ⏳ 未知錯誤，等待 2 秒後重試...")
                    time.sleep(2)
                
                if attempt == max_retries - 1:
                    print(f"  ❌ 無法獲取 {symbol} 的數據，已重試 {max_retries} 次")
                    return None
        
        return None
    
    def calculate_technical_indicators(self, data):
        """
        計算技術分析指標
        
        Args:
            data (pd.DataFrame): 股票歷史數據
            
        Returns:
            pd.DataFrame: 包含技術指標的數據
        """
        if data is None or data.empty:
            return None
            
        df = data.copy()
        
        # 移動平均線
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA10'] = df['Close'].rolling(window=10).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        
        # RSI (相對強弱指標)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
        
        # 布林通道
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        
        # 成交量指標
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
        
        # 價格動量
        df['Price_Momentum'] = df['Close'].pct_change(periods=5)
        
        # 波動率
        df['Volatility'] = df['Close'].rolling(window=20).std()
        
        return df
    
    def detect_bullish_signals(self, df):
        """
        檢測多頭訊號
        
        Args:
            df (pd.DataFrame): 包含技術指標的數據
            
        Returns:
            list: 多頭訊號日期列表
        """
        if df is None or df.empty:
            return []
            
        signals = []
        
        for i in range(20, len(df)):
            current = df.iloc[i]
            prev = df.iloc[i-1]
            
            # 多頭訊號條件（資深交易員經驗法則）
            bullish_conditions = []
            
            # 1. 黃金交叉：短期MA穿越長期MA
            if (current['MA5'] > current['MA20'] and 
                prev['MA5'] <= prev['MA20']):
                bullish_conditions.append("黃金交叉")
            
            # 2. RSI從超賣區反轉
            if (current['RSI'] > 30 and prev['RSI'] <= 30):
                bullish_conditions.append("RSI超賣反轉")
            
            # 3. MACD柱狀圖由負轉正
            if (current['MACD_Histogram'] > 0 and 
                prev['MACD_Histogram'] <= 0):
                bullish_conditions.append("MACD柱狀圖轉正")
            
            # 4. 價格突破布林通道下軌
            if (current['Close'] > current['BB_Lower'] and 
                prev['Close'] <= prev['BB_Lower']):
                bullish_conditions.append("突破布林下軌")
            
            # 5. 成交量放大配合價格上漲
            if (current['Volume_Ratio'] > 1.5 and 
                current['Close'] > prev['Close']):
                bullish_conditions.append("放量上漲")
            
            # 6. 價格動量轉正
            if (current['Price_Momentum'] > 0 and 
                prev['Price_Momentum'] <= 0):
                bullish_conditions.append("動量轉正")
            
            # 如果滿足至少2個條件，視為多頭訊號
            if len(bullish_conditions) >= 2:
                signals.append({
                    'date': df.index[i],
                    'price': current['Close'],
                    'conditions': bullish_conditions,
                    'rsi': current['RSI'],
                    'macd': current['MACD'],
                    'volume_ratio': current['Volume_Ratio']
                })
        
        return signals
    
    def calculate_long_days(self, symbol):
        """
        計算Long Days（最近多頭訊號距離現在的天數）
        
        Args:
            symbol (str): 股票代號
            
        Returns:
            dict: 分析結果
        """
        print(f"分析 {symbol}...")
        
        # 獲取股票資訊
        stock_info = self.get_stock_info(symbol)
        
        # 獲取股票數據
        data = self.get_stock_data(symbol)
        if data is None:
            return None
        
        # 計算技術指標
        df = self.calculate_technical_indicators(data)
        if df is None:
            return None
        
        # 檢測多頭訊號
        signals = self.detect_bullish_signals(df)
        
        if not signals:
            return {
                'symbol': symbol,
                'name': stock_info['name'],
                'market': stock_info['market'],
                'long_days': None,
                'status': '無多頭訊號',
                'current_price': df['Close'].iloc[-1],
                'rsi': df['RSI'].iloc[-1],
                'macd': df['MACD'].iloc[-1],
                'volume_ratio': df['Volume_Ratio'].iloc[-1]
            }
        
        # 找到最近的多頭訊號
        latest_signal = signals[-1]
        current_date = df.index[-1]
        days_since_signal = (current_date - latest_signal['date']).days
        
        # 評估當前狀態
        current_rsi = df['RSI'].iloc[-1]
        current_macd = df['MACD'].iloc[-1]
        current_volume_ratio = df['Volume_Ratio'].iloc[-1]
        
        # 判斷是否適合進場
        entry_opportunity, confidence_score, confidence_level, confidence_factors = self.assess_entry_opportunity(
            df, current_rsi, current_macd, current_volume_ratio
        )
        
        return {
            'symbol': symbol,
            'name': stock_info['name'],
            'market': stock_info['market'],
            'long_days': days_since_signal,
            'latest_signal_date': latest_signal['date'].strftime('%Y-%m-%d'),
            'latest_signal_price': latest_signal['price'],
            'signal_conditions': latest_signal['conditions'],
            'current_price': df['Close'].iloc[-1],
            'current_date': current_date.strftime('%Y-%m-%d'),
            'rsi': current_rsi,
            'macd': current_macd,
            'volume_ratio': current_volume_ratio,
            'entry_opportunity': entry_opportunity,
            'price_change_since_signal': ((df['Close'].iloc[-1] - latest_signal['price']) / latest_signal['price']) * 100,
            'confidence_score': confidence_score,
            'confidence_level': confidence_level,
            'confidence_factors': confidence_factors
        }
    
    def assess_entry_opportunity(self, df, rsi, macd, volume_ratio):
        """
        評估進場機會和信心度
        
        Args:
            df (pd.DataFrame): 股票數據
            rsi (float): 當前RSI
            macd (float): 當前MACD
            volume_ratio (float): 當前成交量比率
            
        Returns:
            tuple: (進場建議, 信心度分數, 信心度等級)
        """
        score = 0
        confidence_factors = []
        
        # RSI評估
        if 30 <= rsi <= 50:  # 從超賣區反轉但未過熱
            score += 2
            confidence_factors.append("RSI從超賣區反轉")
        elif rsi < 30:  # 超賣區
            score += 3
            confidence_factors.append("RSI嚴重超賣")
        elif rsi > 70:  # 超買區
            score -= 2
            confidence_factors.append("RSI超買")
        
        # MACD評估
        macd_histogram = df['MACD_Histogram'].iloc[-1]
        if macd > 0:  # MACD為正
            score += 1
            confidence_factors.append("MACD為正")
        if macd_histogram > 0:  # MACD柱狀圖為正
            score += 1
            confidence_factors.append("MACD柱狀圖為正")
        
        # 成交量評估
        if volume_ratio > 1.2:  # 成交量放大
            score += 1
            confidence_factors.append("成交量放大")
        elif volume_ratio < 0.8:  # 成交量萎縮
            score -= 1
            confidence_factors.append("成交量萎縮")
        
        # 價格趨勢評估
        current_price = df['Close'].iloc[-1]
        ma20 = df['MA20'].iloc[-1]
        ma5 = df['MA5'].iloc[-1]
        
        if current_price > ma20:  # 價格在20日均線之上
            score += 1
            confidence_factors.append("價格在20日均線之上")
        if current_price > ma5:  # 價格在5日均線之上
            score += 1
            confidence_factors.append("價格在5日均線之上")
        
        # 布林通道評估
        bb_upper = df['BB_Upper'].iloc[-1]
        bb_lower = df['BB_Lower'].iloc[-1]
        bb_position = (current_price - bb_lower) / (bb_upper - bb_lower)
        
        if bb_position < 0.3:  # 接近布林通道下軌
            score += 1
            confidence_factors.append("接近布林通道下軌")
        elif bb_position > 0.7:  # 接近布林通道上軌
            score -= 1
            confidence_factors.append("接近布林通道上軌")
        
        # 價格動量評估
        momentum_5d = df['Price_Momentum'].iloc[-1]
        momentum_10d = df['Close'].pct_change(periods=10).iloc[-1]
        
        if momentum_5d > 0 and momentum_10d > 0:
            score += 1
            confidence_factors.append("短期和中期動量均為正")
        elif momentum_5d < 0 and momentum_10d < 0:
            score -= 1
            confidence_factors.append("短期和中期動量均為負")
        
        # 計算信心度分數 (0-100)
        confidence_score = max(0, min(100, (score + 5) * 10))  # 將-5到5的分數轉換為0-100
        
        # 根據分數判斷進場建議
        if score >= 4:
            entry_advice = "強烈推薦進場"
        elif score >= 2:
            entry_advice = "建議進場"
        elif score >= 0:
            entry_advice = "觀望"
        else:
            entry_advice = "不建議進場"
        
        # 信心度等級
        if confidence_score >= 80:
            confidence_level = "極高"
        elif confidence_score >= 60:
            confidence_level = "高"
        elif confidence_score >= 40:
            confidence_level = "中等"
        elif confidence_score >= 20:
            confidence_level = "低"
        else:
            confidence_level = "極低"
        
        return entry_advice, confidence_score, confidence_level, confidence_factors
    
    def analyze_watchlist(self):
        """
        分析整個觀察池
        
        Returns:
            pd.DataFrame: 分析結果
        """
        results = []
        
        for symbol in self.stocks:
            result = self.calculate_long_days(symbol)
            if result:
                results.append(result)
            
            # 在每個股票分析之間增加延遲，避免API限制
            time.sleep(1)
        
        # 轉換為DataFrame並排序
        df_results = pd.DataFrame(results)
        
        # 按Long Days排序（天數越短越優先）
        if not df_results.empty and 'long_days' in df_results.columns:
            df_results = df_results.sort_values('long_days', na_position='last')
        
        return df_results
    
    def generate_report(self, results_df):
        """
        生成分析報告
        
        Args:
            results_df (pd.DataFrame): 分析結果
        """
        print("\n" + "="*80)
        print("📈 股票觀察池分析報告")
        print("="*80)
        print(f"分析時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"觀察池股票數量：{len(self.stocks)}")
        print("="*80)
        
        if results_df.empty:
            print("❌ 無法獲取任何股票數據")
            return
        
        # 顯示最佳進場機會
        print("\n🎯 最佳進場機會（Long Days最短）：")
        print("-" * 80)
        
        for _, row in results_df.head(5).iterrows():
            if pd.notna(row['long_days']):
                print(f"🏆 {row['symbol']} ({row['name']})")
                print(f"   Long Days: {row['long_days']} 天")
                print(f"   最新訊號: {row['latest_signal_date']}")
                print(f"   當前價格: ${row['current_price']:.2f}")
                print(f"   進場建議: {row['entry_opportunity']}")
                print(f"   信心度: {row.get('confidence_score', 'N/A'):.0f}/100 ({row.get('confidence_level', 'N/A')})")
                print(f"   RSI: {row['rsi']:.1f}")
                print(f"   成交量比率: {row['volume_ratio']:.2f}")
                
                # 顯示信心度因素
                confidence_factors = row.get('confidence_factors', [])
                if confidence_factors:
                    print(f"   信心度因素: {', '.join(confidence_factors[:3])}")  # 只顯示前3個因素
                
                print()
        
        # 顯示無訊號的股票
        no_signals = results_df[results_df['long_days'].isna()]
        if not no_signals.empty:
            print("\n⚠️  無多頭訊號的股票：")
            print("-" * 40)
            for _, row in no_signals.iterrows():
                print(f"   {row['symbol']} ({row['name']}) - {row['status']}")
        
        # 統計摘要
        print("\n📊 統計摘要：")
        print("-" * 40)
        valid_signals = results_df[results_df['long_days'].notna()]
        if not valid_signals.empty:
            print(f"有訊號股票數量: {len(valid_signals)}")
            print(f"平均Long Days: {valid_signals['long_days'].mean():.1f} 天")
            print(f"最短Long Days: {valid_signals['long_days'].min()} 天")
            print(f"最長Long Days: {valid_signals['long_days'].max()} 天")
        
        print("\n" + "="*80)

def main():
    """主程式"""
    print("🚀 啟動股票觀察池分析系統...")
    
    # 建立分析器
    analyzer = StockAnalyzer()
    
    # 分析觀察池
    results = analyzer.analyze_watchlist()
    
    # 生成報告
    analyzer.generate_report(results)
    
    # 儲存結果到CSV
    if not results.empty:
        results.to_csv('stock_analysis_results.csv', index=False, encoding='utf-8-sig')
        print("💾 分析結果已儲存至 stock_analysis_results.csv")
    
    print("\n✅ 分析完成！")

if __name__ == "__main__":
    main() 