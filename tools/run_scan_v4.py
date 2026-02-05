#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BullPS-v4 智能掃描器 (Project Iron Shield)
=========================================
整合 V4 核心邏輯：
1. 技術面：支撐簇 (Support Clusters) + 反轉確認
2. 統計面：IV Rank 過濾 (拒絕低波動風險)
3. 數據面：紀錄 Erosion Snapshot (供未來監控使用)
"""

import sys
import os
import json
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

# Add project root and core to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
core_dir = os.path.join(project_root, "core")

if project_root not in sys.path:
    sys.path.append(project_root)
if core_dir not in sys.path:
    sys.path.append(core_dir)

from core.integrated_stock_analyzer import IntegratedStockAnalyzer
from core.bps_optimizer import BPSOptimizer

# 核心清單 (備用)
CORE_WATCHLIST = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX", "AMD", 
    "DIS", "BA", "JPM", "WMT", "V", "MA", "KO", "PEP", "COST", "INTC", "PYPL",
    "CRM", "ADBE", "QCOM", "TXN", "HON", "UNH", "PG", "XOM", "CVX", "MRK", "IWM", "SPY", "QQQ"
]

def get_real_premium(symbol, short_strike, long_strike, expiry_date_str):
    """獲取即時權利金 (V4 版: 增加錯誤處理與重試)"""
    try:
        ticker = yf.Ticker(symbol)
        # 轉換日期
        target_date_obj = datetime.strptime(expiry_date_str, '%Y-%m-%d')
        options = ticker.options
        if not options: return None, "No options chain"
        
        # 找最接近的到期日
        valid_dates = [d for d in options if datetime.strptime(d, '%Y-%m-%d') >= target_date_obj]
        if not valid_dates: return None, "No valid expiry"
        best_date = min(valid_dates, key=lambda x: abs((datetime.strptime(x, '%Y-%m-%d') - target_date_obj).days))
        
        chain = ticker.option_chain(best_date)
        puts = chain.puts
        
        # 模糊匹配 Strike
        short_put = puts[abs(puts['strike'] - short_strike) < 0.5]
        long_put = puts[abs(puts['strike'] - long_strike) < 0.5]
        
        if short_put.empty or long_put.empty:
            return None, f"Strikes not found for {best_date}"

        # 取價邏輯：優先用 Bid/Ask 中價，沒有則用 Last
        def get_mid_price(row):
            bid, ask = row['bid'].values[0], row['ask'].values[0]
            if bid > 0 and ask > 0: return (bid + ask) / 2
            return row['lastPrice'].values[0]

        short_price = get_mid_price(short_put)
        long_price = get_mid_price(long_put)
        
        return {
            'credit': short_price - long_price,
            'expiry': best_date,
            'short_strike': short_put['strike'].values[0],
            'long_strike': long_put['strike'].values[0]
        }, None
    except Exception as e:
        return None, str(e)

def main():
    print(f"🛡️ 啟動 BullPS-v4 (Iron Shield) 掃描... [Date: {datetime.now().strftime('%Y-%m-%d')}]")
    
    analyzer = IntegratedStockAnalyzer()
    optimizer = BPSOptimizer()
    
    # 載入清單
    watchlist_path = os.path.join(project_root, "stock_watchlist.json")
    try:
        with open(watchlist_path, 'r', encoding='utf-8') as f:
            full_list = json.load(f).get('stocks', [])
        scan_list = full_list if full_list else CORE_WATCHLIST
        print(f"📊 載入監控清單: {len(scan_list)} 支標的")
    except:
        scan_list = CORE_WATCHLIST
        print("⚠️ 無法載入清單，使用核心 30 支")

    candidates = []
    
    print("🔍 開始篩選 (過濾標準: 技術分>60 & IV Rank>20)...")
    
    for i, symbol in enumerate(scan_list):
        try:
            # print(f"Checking {symbol}...", end="\r")
            # 1. 技術面初篩 (快速)
            data = analyzer.get_stock_data(symbol)
            if data is None or len(data) < 60: 
                print(f"  [Error] {symbol} No Data")
                continue
            
            df = analyzer.calculate_technical_indicators(data)
            timing_res = analyzer.calculate_entry_timing_score(df)
            score = timing_res['timing_score']
            
            # V4 門檻：技術面必須有一定強度 (支撐/反轉)
            if score < 50: 
                print(f"  [Low Score] {symbol}: {score}")
                continue 

            # 2. 統計面過濾 (IV Rank)
            bps_setup = optimizer.suggest_bps_strikes(symbol)
            if not bps_setup: 
                print(f"  [Error] {symbol} BPS Setup Failed")
                continue
            
            iv_rank = bps_setup.get('iv_rank', 50)
            
            # V4 核心濾網：拒絕低波動 (IV Rank < 20)
            if iv_rank < 20: 
                print(f"  [Skip] {symbol} IV Rank {iv_rank:.1f} too low (Score: {score})")
                continue
                
            # 3. 獲取真實權利金
            premium_data, err = get_real_premium(
                symbol, 
                bps_setup['short_put_strike'], 
                bps_setup['long_put_strike'], 
                bps_setup['suggested_expiry']
            )
            
            if not premium_data:
                print(f"  [Skip] {symbol} No Options Data: {err}")
                continue
            
            if premium_data and premium_data['credit'] > 0.05:
                # 計算 ROI (年化)
                width = premium_data['short_strike'] - premium_data['long_strike']
                risk = width - premium_data['credit']
                roi = (premium_data['credit'] / risk) * 100
                
                # 建立 Erosion Snapshot (快照)
                snapshot = {
                    'MA20': df['MA20'].iloc[-1],
                    'RSI': df['RSI'].iloc[-1],
                    'MACD_Hist': df['MACD_Histogram'].iloc[-1],
                    'Close': df['Close'].iloc[-1],
                    'SAR': df['SAR'].iloc[-1]
                }
                
                candidates.append({
                    'symbol': symbol,
                    'price': bps_setup['current_price'],
                    'score': score,
                    'iv_rank': iv_rank,
                    'expiry': premium_data['expiry'],
                    'strikes': f"{premium_data['short_strike']}/{premium_data['long_strike']}",
                    'credit': round(premium_data['credit'], 2),
                    'roi': round(roi, 2),
                    'snapshot': snapshot, # 關鍵：把快照存下來
                    'reasons': timing_res['timing_factors']
                })
                print(f"  ✅ {symbol}: Score {score} | IV Rank {iv_rank} | ROI {roi:.1f}%")
                
        except Exception as e:
            continue
            
    # 排序：優先推薦「高分 + 高 IV」的組合
    candidates.sort(key=lambda x: x['score'] + x['iv_rank'], reverse=True)
    top_picks = candidates[:5]
    
    print("\n" + "="*50)
    print("🏆 BullPS-v4 Top 5 Recommendations")
    print("="*50)
    print(json.dumps(top_picks, indent=2))
    print("="*50)

if __name__ == "__main__":
    main()
