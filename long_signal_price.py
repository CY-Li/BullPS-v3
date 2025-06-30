#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Long Signal Price 分析程式
資深股票交易員設計：計算每檔股票30天內不易跌破的抄底價位
"""

import json
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import warnings
import time
warnings.filterwarnings('ignore')

# 觀察池檔案
WATCHLIST_FILE = 'stock_watchlist.json'

class LongSignalPriceAnalyzer:
    def __init__(self, watchlist_file=WATCHLIST_FILE):
        self.watchlist_file = watchlist_file
        self.watchlist = self.load_watchlist()
        self.stocks = self.watchlist.get('stocks', [])
        self.period = 30  # 分析區間天數

    def load_watchlist(self):
        try:
            with open(self.watchlist_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ 找不到 {self.watchlist_file}")
            return {"stocks": []}

    def get_stock_info(self, symbol):
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            name = info.get('longName', info.get('shortName', symbol))
            if '.TW' in symbol:
                market = 'TWSE'
            elif '.HK' in symbol:
                market = 'HKEX'
            else:
                market = 'US'
            return {'symbol': symbol, 'name': name, 'market': market}
        except Exception as e:
            print(f"⚠️ 無法獲取 {symbol} 資訊: {e}")
            return {'symbol': symbol, 'name': symbol, 'market': 'Unknown'}

    def get_stock_data(self, symbol, period_days=30, max_retries=3):
        for attempt in range(max_retries):
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period=f'{period_days}d', timeout=60)
                if data.empty:
                    print(f"  警告：{symbol} 沒有數據")
                    return None
                return data
            except Exception as e:
                print(f"  ❌ 第 {attempt+1} 次嘗試失敗：{e}")
                time.sleep(2)
        print(f"  ❌ 無法獲取 {symbol} 的數據")
        return None

    def calculate_long_signal_price(self, df):
        # 1. 近30日最低價
        min_low = df['Low'].min()
        # 2. 30日布林下軌
        ma = df['Close'].rolling(window=20).mean()
        std = df['Close'].rolling(window=20).std()
        bb_lower = (ma - 2 * std).iloc[-1]
        # 3. 30日均線
        ma30 = df['Close'].rolling(window=30).mean().iloc[-1]
        # 4. 30日內多頭訊號日的收盤價（黃金交叉、RSI反轉、MACD柱轉正）
        signals = []
        for i in range(1, len(df)):
            # 黃金交叉
            ma5 = df['Close'].rolling(window=5).mean()
            ma20 = df['Close'].rolling(window=20).mean()
            if ma5.iloc[i] > ma20.iloc[i] and ma5.iloc[i-1] <= ma20.iloc[i-1]:
                signals.append(df['Close'].iloc[i])
            # RSI反轉
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            if rsi.iloc[i] > 30 and rsi.iloc[i-1] <= 30:
                signals.append(df['Close'].iloc[i])
            # MACD柱狀圖轉正
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            macd_signal = macd.ewm(span=9, adjust=False).mean()
            macd_hist = macd - macd_signal
            if macd_hist.iloc[i] > 0 and macd_hist.iloc[i-1] <= 0:
                signals.append(df['Close'].iloc[i])
        if signals:
            signal_price = min(signals)
        else:
            signal_price = min_low
        # 5. 近30日最大成交量K棒的最低價
        max_vol_idx = df['Volume'].idxmax()
        max_vol_low = df.loc[max_vol_idx, 'Low'] if max_vol_idx in df.index else min_low
        # 6. RSI<30時的最低價
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_oversold_lows = df['Low'][rsi < 30]
        rsi_oversold_low = rsi_oversold_lows.min() if not rsi_oversold_lows.empty else min_low
        # 綜合多重支撐，取最高值
        candidates = [min_low, bb_lower, ma30, signal_price, max_vol_low, rsi_oversold_low]
        long_signal_price = max([v for v in candidates if not pd.isna(v)])
        # 信心度：有幾條支撐同時接近long_signal_price
        close_count = sum([abs(long_signal_price-v)/long_signal_price < 0.03 for v in candidates])
        confidence = min(100, 40 + close_count*15)  # 最多100分
        return long_signal_price, candidates, confidence

    def analyze(self):
        results = []
        for symbol in self.stocks:
            print(f"分析 {symbol}...")
            info = self.get_stock_info(symbol)
            df = self.get_stock_data(symbol, self.period)
            if df is None or len(df) < 20:
                print(f"  ❌ {symbol} 無法分析")
                continue
            price, candidates, confidence = self.calculate_long_signal_price(df)
            results.append({
                'symbol': symbol,
                'name': info['name'],
                'market': info['market'],
                'long_signal_price': round(price, 2),
                'min_low': round(candidates[0], 2),
                'bb_lower': round(candidates[1], 2),
                'ma30': round(candidates[2], 2),
                'signal_price': round(candidates[3], 2),
                'max_vol_low': round(candidates[4], 2),
                'rsi_oversold_low': round(candidates[5], 2),
                'confidence': confidence
            })
            time.sleep(1)
        return pd.DataFrame(results)

    def report(self, df):
        print("\n" + "="*80)
        print("📉 Long Signal Price 分析報告")
        print("="*80)
        print(f"分析時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"觀察池股票數量：{len(self.stocks)}")
        print("="*80)
        if df.empty:
            print("❌ 無法獲取任何股票數據")
            return
        print(f"\n🎯 30天內不易跌破的抄底價位（Long Signal Price）：")
        print("-" * 80)
        for _, row in df.iterrows():
            print(f"{row['symbol']} ({row['name']})")
            print(f"   Long Signal Price: ${row['long_signal_price']}")
            print(f"   信心度: {row['confidence']}/100")
            print(f"   依據：近30日最低 {row['min_low']}、布林下軌 {row['bb_lower']}、MA30 {row['ma30']}、多頭訊號價 {row['signal_price']}、最大量K低 {row['max_vol_low']}、RSI超賣低 {row['rsi_oversold_low']}")
            print()
        print("="*80)

    def save_csv(self, df, filename='long_signal_price_results.csv'):
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"💾 分析結果已儲存至 {filename}")

if __name__ == "__main__":
    analyzer = LongSignalPriceAnalyzer()
    results = analyzer.analyze()
    analyzer.report(results)
    if not results.empty:
        analyzer.save_csv(results)
    print("\n✅ 分析完成！") 