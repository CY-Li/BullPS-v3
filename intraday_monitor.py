#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
盤中即時監控警示系統 (OpenClaw 版)
監控持倉股票的盤中價格與波動，並透過 LINE 發送警示。
"""

import sys
import os
from pathlib import Path

# 將專案根目錄添加到 Python 路徑
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

try:
    import yfinance as yf
    import pandas as pd
    import json
    import time
    import subprocess
    from datetime import datetime
    import pytz
    from backend.path_manager import path_manager
except ImportError as e:
    print(f"❌ 啟動失敗，缺少模組: {e}")
    sys.exit(1)

# 設定
LINE_TARGET = 'U0aae8e070107ce5b7cf7f02cf67ea911' # 使用者的 LINE ID
CHECK_INTERVAL = 300 # 每 5 分鐘檢查一次
DROP_THRESHOLD = -0.02 # 跌幅超過 2% 觸發警示

def send_line_message(message):
    """透過 OpenClaw CLI 發送 LINE 訊息"""
    try:
        # 使用絕對路徑或確保 openclaw 在 PATH 中
        subprocess.run([
            "openclaw", "message", "send",
            "--channel", "line",
            "--target", LINE_TARGET,
            "--message", message
        ], check=True)
    except Exception as e:
        print(f"Error sending LINE message: {e}")

def get_monitored_stocks():
    """讀取當前持倉列表"""
    file_path = path_manager.get_monitored_stocks_path()
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"Error reading monitored stocks: {e}")
        return []

def monitor_loop():
    print(f"🚀 [BullPS-v3] 盤中監控系統已啟動", flush=True)
    print(f"📍 監控檔案: {path_manager.get_monitored_stocks_path()}", flush=True)
    print(f"⏱️ 檢查間隔: {CHECK_INTERVAL}s, 閾值: {DROP_THRESHOLD*100}%", flush=True)
    
    while True:
        try:
            stocks = get_monitored_stocks()
            if not stocks:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 尚無監控持倉，等待中...", flush=True)
                time.sleep(60)
                continue

            symbols = list(set([s['symbol'] for s in stocks if 'symbol' in s]))
            if not symbols:
                time.sleep(60)
                continue

            print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在檢查 {len(symbols)} 支股票: {', '.join(symbols)}", flush=True)
            
            # 獲取最新價格
            data = yf.download(symbols, period='1d', interval='5m', progress=False)
            
            if data.empty:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 市場似乎未開盤或無數據，跳過本次檢查。", flush=True)
                time.sleep(CHECK_INTERVAL)
                continue
            
            # 確保 Close 數據存在
            if 'Close' not in data:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 無法獲取收盤價數據。", flush=True)
                time.sleep(CHECK_INTERVAL)
                continue

            for stock in stocks:
                symbol = stock.get('symbol')
                if not symbol: continue
                
                try:
                    # 獲取該股票的最新價格
                    if isinstance(data['Close'], pd.DataFrame):
                        if symbol in data['Close'].columns:
                            current_price = data['Close'][symbol].iloc[-1]
                        else:
                            continue
                    else:
                        # 只有一支股票時，data['Close'] 可能是 Series
                        current_price = data['Close'].iloc[-1]
                except Exception as e:
                    print(f"Error getting price for {symbol}: {e}", flush=True)
                    continue

                if pd.isna(current_price): continue
                
                entry_price = stock.get('entry_price')
                if not entry_price: continue
                
                # 計算相對於進場價的跌幅
                change_pct = (current_price - entry_price) / entry_price
                
                # 觸發警示邏輯
                if change_pct <= DROP_THRESHOLD:
                    # 避免重複發送警示（這裡可以記錄最後警示時間，暫時簡化）
                    alert_msg = (
                        f"🚨 【BullPS 盤中警示】\n"
                        f"股票: {symbol}\n"
                        f"現價: ${current_price:.2f}\n"
                        f"較進場價跌幅: {change_pct*100:.2f}%\n"
                        f"⚠️ 請檢查 BPS 組合風險，考慮執行止損或調整。"
                    )
                    print(f"!!! ALERT !!! {symbol} dropped {change_pct*100:.2f}%", flush=True)
                    send_line_message(alert_msg)
            
            time.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            print(f"Monitor loop error: {e}", flush=True)
            time.sleep(60)

if __name__ == "__main__":
    monitor_loop()
