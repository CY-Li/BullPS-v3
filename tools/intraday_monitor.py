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
STRIKE_WARNING_THRESHOLD = 0.03 # 距離 Short Strike 小於 3% 觸發警示

def send_line_message(message):
    """將警示記錄到日誌檔案，不再主動發送 LINE 訊息"""
    try:
        log_path = Path("memory/intraday_alerts.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] ALERT:\n{message}\n{'-'*40}\n")
        print(f"📍 警示已記錄至 {log_path}", flush=True)
    except Exception as e:
        print(f"Error logging alert: {e}", flush=True)

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

def get_realtime_liquidity(symbol):
    """
    [Optimization 1] 取得即時 Bid/Ask 報價以過濾滑價陷阱 (Liquidity Trap)
    """
    try:
        ticker = yf.Ticker(symbol)
        # 嘗試獲取盤中即時數據
        info = ticker.info 
        bid = info.get('bid', 0)
        ask = info.get('ask', 0)
        last = info.get('currentPrice', 0)
        
        if bid and ask and last and bid > 0:
            spread = ask - bid
            spread_pct = spread / last
            return {
                'bid': bid,
                'ask': ask,
                'last': last,
                'spread_pct': spread_pct,
                'is_valid': True
            }
    except Exception as e:
        print(f"Liquidity check failed for {symbol}: {e}")
    
    return {'is_valid': False}

def calculate_rsi(series, period=14):
    """計算 RSI (Relative Strength Index)"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0))
    loss = (-delta.where(delta < 0, 0))

    # 使用 Wilder's Smoothing (EMA)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

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
            
            # 獲取 5 天歷史數據以計算平均成交量 (5m K線)
            data = yf.download(symbols, period='5d', interval='5m', progress=False)
            
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
                    # 提取 Series 數據
                    if isinstance(data['Close'], pd.DataFrame):
                        if symbol in data['Close'].columns:
                            close_series = data['Close'][symbol].dropna()
                            volume_series = data['Volume'][symbol].dropna() if 'Volume' in data else pd.Series()
                        else:
                            continue
                    else:
                        close_series = data['Close'].dropna()
                        volume_series = data['Volume'].dropna() if 'Volume' in data else pd.Series()
                    
                    if close_series.empty: continue
                    current_price = close_series.iloc[-1]
                    
                except Exception as e:
                    print(f"Error getting data for {symbol}: {e}", flush=True)
                    continue

                if pd.isna(current_price): continue
                
                entry_price = stock.get('entry_price')
                if not entry_price: continue
                
                # 計算相對於進場價的跌幅
                change_pct = (current_price - entry_price) / entry_price
                
                # --- 新增過濾邏輯 ---
                # 1. 計算 RSI
                rsi_val = 50 # 預設值
                if len(close_series) > 14:
                    rsi_series = calculate_rsi(close_series)
                    rsi_val = rsi_series.iloc[-1]
                
                # 2. 計算成交量條件 (Volume > 1.5x 5-day Avg)
                vol_condition = False
                avg_vol = 0
                current_vol = 0
                if not volume_series.empty:
                    current_vol = volume_series.iloc[-1]
                    avg_vol = volume_series.mean() # 5天內所有5m K線的平均成交量
                    if avg_vol > 0 and current_vol > 1.5 * avg_vol:
                        vol_condition = True
                
                # 3. 組合過濾條件: (RSI < 35 OR Volume > 1.5x Avg)
                technical_filter = (rsi_val < 35) or vol_condition
                
                # BPS 專屬警示：Short Strike 防禦檢測
                short_strike = stock.get('short_strike')
                strike_msg = ""
                if short_strike:
                    distance_pct = (current_price - short_strike) / short_strike
                    if 0 < distance_pct < STRIKE_WARNING_THRESHOLD:
                        strike_msg = (
                            f"⚠️ **危險接近履約價！**\n"
                            f"距離 Short Strike ({short_strike}): 僅剩 {distance_pct*100:.2f}%\n"
                        )
                    elif current_price < short_strike:
                         strike_msg = (
                            f"🚨 **已跌破履約價 (ITM)！**\n"
                            f"Short Strike: {short_strike}\n"
                            f"目前為價內: {(short_strike-current_price)/short_strike*100:.2f}%\n"
                        )

                # 觸發警示邏輯:
                # 舊邏輯: if change_pct <= DROP_THRESHOLD or strike_msg:
                # 新邏輯: (跌幅達標 AND 技術指標符合) OR (Strike 警示)
                
                drop_alert_triggered = (change_pct <= DROP_THRESHOLD) and technical_filter
                
                if drop_alert_triggered or strike_msg:
                    # [Optimization 1] 滑價過濾機制 (Liquidity Trap Filter)
                    # 只有在準備發送警示時才檢查，節省 API 資源
                    is_liquidity_trap = False
                    liq_data = get_realtime_liquidity(symbol)
                    
                    if liq_data['is_valid']:
                        # 1. 檢查價差是否過大 (Spread > 0.3% 視為異常擴大)
                        if liq_data['spread_pct'] > 0.003:
                            is_liquidity_trap = True
                            print(f"⚠️ {symbol} 偵測到流動性陷阱 (Spread: {liq_data['spread_pct']*100:.2f}%)，抑制警示。", flush=True)
                        
                        # 2. 檢查報價是否偏離買賣價過遠 (Bad Tick)
                        # 如果 Current Price 比 Ask 還高 1% 或 比 Bid 還低 1%
                        elif current_price > liq_data['ask'] * 1.01 or current_price < liq_data['bid'] * 0.99:
                            is_liquidity_trap = True
                            print(f"⚠️ {symbol} 偵測到異常報價 (Price: {current_price} vs Bid/Ask: {liq_data['bid']}/{liq_data['ask']})，抑制警示。", flush=True)

                    if is_liquidity_trap:
                        continue # 跳過本次警示，不發送

                    # 避免重複發送警示（這裡可以記錄最後警示時間，暫時簡化）
                    alert_content = (
                        f"🚨 【BullPS 盤中警示】\n"
                        f"股票: {symbol}\n"
                        f"現價: ${current_price:.2f}\n"
                        f"較進場價跌幅: {change_pct*100:.2f}%\n"
                    )
                    
                    if drop_alert_triggered:
                        alert_content += f"📉 觸發條件: 跌幅 > 2% 且 (RSI={rsi_val:.1f} 或 Vol爆量)\n"
                        if vol_condition:
                            alert_content += f"📊 成交量異常: {current_vol} (均量 {avg_vol:.0f})\n"
                        if rsi_val < 30:
                            alert_content += f"📉 RSI 過低: {rsi_val:.1f}\n"

                    if strike_msg:
                        alert_content += strike_msg
                    elif not drop_alert_triggered:
                         # 僅 strike msg
                         pass
                    else:
                        alert_content += f"⚠️ 請檢查 BPS 組合風險，考慮執行止損或調整。"

                    print(f"!!! ALERT !!! {symbol} price: {current_price}, drop: {change_pct*100:.2f}%, RSI: {rsi_val:.1f}, VolRatio: {current_vol/avg_vol if avg_vol else 0:.1f}", flush=True)
                    send_line_message(alert_content)
            
            time.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            print(f"Monitor loop error: {e}", flush=True)
            time.sleep(60)

if __name__ == "__main__":
    monitor_loop()
