#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BullPS-v3 精準獲利追蹤器 (V2)
使用真實進場權利金計算 ROI，並提供自動停利警示。
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
import yfinance as yf
import pandas as pd
import numpy as np

# 設定
LINE_TARGET = 'U0aae8e070107ce5b7cf7f02cf67ea911'
PROFIT_TARGET_PCT = 0.50 # 50% 獲利目標
# 使用絕對路徑確保背景執行時能找到 openclaw
OPENCLAW_BIN = "/home/jimmy161688/.npm-global/bin/openclaw"

def send_line_message(message):
    """透過 OpenClaw CLI 發送 LINE 訊息"""
    try:
        subprocess.run([
            OPENCLAW_BIN, "message", "send",
            "--channel", "line",
            "--target", LINE_TARGET,
            "--message", message
        ], check=True)
    except Exception as e:
        print(f"Error sending LINE message: {e}")

def get_monitored_stocks():
    file_path = Path("BullPS-v3/monitored_stocks.json")
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def run_profit_check():
    print(f"--- BullPS-v3 精準獲利追蹤 ({datetime.now().strftime('%H:%M:%S')}) ---")
    stocks = get_monitored_stocks()
    if not stocks:
        return

    for stock in stocks:
        symbol = stock['symbol']
        short_strike = stock['short_strike']
        long_strike = stock['long_strike']
        expiry = stock['expiry']
        entry_premium = stock.get('entry_premium', 1.0) # 預設值 1.0 防止報錯
        
        try:
            ticker = yf.Ticker(symbol)
            current_price = ticker.history(period='1d')['Close'].iloc[-1]
            
            options = ticker.option_chain(expiry)
            puts = options.puts
            
            # 尋找最接近的履約價 (插值估算)
            def get_interpolated_price(target_strike):
                if target_strike in puts['strike'].values:
                    row = puts[puts['strike'] == target_strike].iloc[0]
                    return (row['bid'] + row['ask']) / 2 if row['bid'] > 0 else row['lastPrice']
                
                # 線性插值
                sorted_puts = puts.sort_values('strike')
                lower = sorted_puts[sorted_puts['strike'] < target_strike].tail(1)
                upper = sorted_puts[sorted_puts['strike'] > target_strike].head(1)
                
                if not lower.empty and not upper.empty:
                    l_strike, l_p = lower.iloc[0]['strike'], (lower.iloc[0]['bid'] + lower.iloc[0]['ask'])/2
                    u_strike, u_p = upper.iloc[0]['strike'], (upper.iloc[0]['bid'] + upper.iloc[0]['ask'])/2
                    # 簡單加權平均
                    ratio = (target_strike - l_strike) / (u_strike - l_strike)
                    return l_p + ratio * (u_p - l_p)
                return None

            s_price = get_interpolated_price(short_strike)
            l_price = get_interpolated_price(long_strike)
            
            if s_price is not None and l_price is not None:
                current_spread_value = max(0.01, s_price - l_price)
                # 獲利計算：(原始權利金 - 當前價值) / 原始權利金
                profit_pct = (entry_premium - current_spread_value) / entry_premium
                
                print(f"{symbol}: 現價 ${current_price:.2f} | 價差價值 ${current_spread_value:.2f} | 獲利 {profit_pct*100:.1f}%")
                
                if profit_pct >= PROFIT_TARGET_PCT:
                    msg = (
                        f"💰 【BullPS 停利建議】\n"
                        f"股票: {symbol}\n"
                        f"當前獲利: {profit_pct*100:.1f}%\n"
                        f"已達到 {PROFIT_TARGET_PCT*100:.0f}% 獲利目標！\n"
                        f"建議執行 BTC (Buy to Close) 鎖定利潤。"
                    )
                    send_line_message(msg)
            
        except Exception as e:
            print(f"Error checking {symbol}: {e}")

if __name__ == "__main__":
    run_profit_check()
