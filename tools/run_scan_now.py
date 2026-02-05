#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import time
import warnings
warnings.filterwarnings('ignore')

# Add current directory and core directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(os.path.dirname(current_dir), "core"))

from integrated_stock_analyzer import IntegratedStockAnalyzer
from bps_optimizer import BPSOptimizer

# 核心清單：優先掃描流動性好、權值高的股票
CORE_WATCHLIST = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX", "AMD", 
    "DIS", "BA", "JPM", "WMT", "V", "MA", "KO", "PEP", "COST", "INTC", "PYPL",
    "CRM", "ADBE", "QCOM", "TXN", "HON", "UNH", "PG", "XOM", "CVX", "MRK"
]

def get_real_premium(symbol, short_strike, long_strike, expiry_date_str):
    """
    獲取即時(或延遲)權利金
    """
    try:
        ticker = yf.Ticker(symbol)
        options = ticker.options
        if not options:
            return None, "No options"
        
        # 轉換日期格式
        target_date_obj = datetime.strptime(expiry_date_str, '%Y-%m-%d')
        
        # 尋找最接近的到期日 (必須 >= target_date_obj)
        valid_dates = [d for d in options if datetime.strptime(d, '%Y-%m-%d') >= target_date_obj]
        if not valid_dates:
             # 如果沒有未來的，找最後一個
             valid_dates = options[-1:]
        
        # 找最接近的一週
        best_date = min(valid_dates, key=lambda x: abs((datetime.strptime(x, '%Y-%m-%d') - target_date_obj).days))
        
        chain = ticker.option_chain(best_date)
        puts = chain.puts
        
        if puts.empty:
            return None, f"No puts for {best_date}"

        # 尋找 Strike
        # 這裡我們允許小數點誤差
        short_put = puts[abs(puts['strike'] - short_strike) < 0.1]
        long_put = puts[abs(puts['strike'] - long_strike) < 0.1]
        
        # 如果找不到精確 Strike，找最接近的
        if short_put.empty:
            short_strike = puts.iloc[(puts['strike'] - short_strike).abs().argsort()[:1]]['strike'].values[0]
            short_put = puts[puts['strike'] == short_strike]
            
        if long_put.empty:
            long_strike = puts.iloc[(puts['strike'] - long_strike).abs().argsort()[:1]]['strike'].values[0]
            long_put = puts[puts['strike'] == long_strike]

        # 獲取價格
        def get_price(row):
            bid = row['bid'].values[0]
            ask = row['ask'].values[0]
            last = row['lastPrice'].values[0]
            if bid > 0 and ask > 0:
                return (bid + ask) / 2
            return last

        short_price = get_price(short_put)
        long_price = get_price(long_put)
        
        net_credit = short_price - long_price
        
        return {
            'credit': net_credit,
            'expiry': best_date,
            'short_strike': short_strike,
            'long_strike': long_strike,
            'short_price': short_price,
            'long_price': long_price
        }, None

    except Exception as e:
        return None, str(e)

def main():
    print(f"🚀 開始 BPS 掃描與推薦... [Date: {datetime.now().strftime('%Y-%m-%d')}]")
    
    analyzer = IntegratedStockAnalyzer()
    optimizer = BPSOptimizer()
    
    candidates = []
    
    # 1. 掃描
    # 讀取完整的監控清單
    # 修正路徑：從 tools 目錄往上一層找到 stock_watchlist.json
    watchlist_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stock_watchlist.json")
    try:
        with open(watchlist_path, 'r', encoding='utf-8') as f:
            full_list = json.load(f).get('stocks', [])
        scan_list = full_list if full_list else CORE_WATCHLIST
        print(f"📊 正在從 {watchlist_path} 讀取清單，共 {len(scan_list)} 支股票...")
    except Exception as e:
        print(f"⚠️ 無法讀取清單檔案，改用核心 30 支股票: {e}")
        scan_list = CORE_WATCHLIST
    
    for symbol in scan_list:
        try:
            # print(f"  Checking {symbol}...", end='\r')
            data = analyzer.get_stock_data(symbol)
            if data is None or data.empty:
                continue
            
            # --- [Optimization] 升級為完整版分析邏輯 ---
            # 原本只跑 calculate_technical_indicators，現在改跑 analyze_stock 以獲得綜合評分
            # 注意：analyze_stock 內部會呼叫 multi_timeframe 和 confirmation_system
            
            analysis_result = analyzer.analyze_stock(symbol)
            if not analysis_result:
                continue

            # 獲取核心指標
            composite_score = analysis_result.get('composite_score', 0)
            confidence_level = analysis_result.get('confidence_level', 0)
            timing_score = analysis_result.get('timing_score', 0)
            
            # 嚴格篩選標準：
            # 1. 綜合評分 >= 85 (原定 90，稍微放寬以避免漏掉潛力股)
            # 2. 信心度 >= 75 (原定 80)
            # 3. 必須有 BPS 推薦理由 (timing_factors 不為空)
            
            # 特例：如果是大型權值股 (如 AAPL, MSFT)，評分標準可微調 (權值股通常分數較穩定)
            is_mega_cap = symbol in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
            threshold_score = 80 if is_mega_cap else 85
            threshold_conf = 70 if is_mega_cap else 75
            
            if composite_score >= threshold_score and confidence_level >= threshold_conf:
                # 這是候選名單
                candidates.append({
                    'symbol': symbol,
                    'score': composite_score,
                    'confidence': confidence_level,
                    'close': analysis_result.get('current_price'),
                    'rsi': analysis_result.get('rsi'),
                    'timing_factors': analysis_result.get('confidence_factors', []) # 使用完整的信心理由
                })
                print(f"  ✨ {symbol} 入選 (Score: {composite_score}, Conf: {confidence_level}%)")

                
        except Exception as e:
            # print(f"Error analyzing {symbol}: {e}")
            continue

    # 排序候選名單 (分數高到低)
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    top_candidates = candidates[:5] # 取前 5 名
    
    print(f"\n🔍 發現 {len(candidates)} 個潛在機會，精選前 {len(top_candidates)} 名進行 BPS 優化:\n")
    
    recommendations = []
    
    for cand in top_candidates:
        symbol = cand['symbol']
        print(f"👉 分析 {symbol} (Score: {cand['score']:.1f})...")
        
        # 2. 優化 BPS 點位
        # 預設 30-40 天到期
        bps_setup = optimizer.suggest_bps_strikes(symbol, days_to_expiry=35)
        
        if bps_setup:
            # 3. 獲取權利金
            premium_data, err = get_real_premium(
                symbol, 
                bps_setup['short_put_strike'], 
                bps_setup['long_put_strike'], 
                bps_setup['suggested_expiry']
            )
            
            if premium_data:
                # 計算 ROI
                width = premium_data['short_strike'] - premium_data['long_strike']
                credit = premium_data['credit']
                # 確保 credit 不為負 (Bid/Ask spread 大時可能發生，過濾掉)
                if credit > 0.05: # 至少有 $0.05
                    risk = width - credit
                    roi = (credit / risk) * 100
                    
                    rec = {
                        'symbol': symbol,
                        'price': cand['close'],
                        'expiry': premium_data['expiry'],
                        'short_strike': premium_data['short_strike'],
                        'long_strike': premium_data['long_strike'],
                        'credit': credit,
                        'roi': roi,
                        'reasons': cand['timing_factors']
                    }
                    recommendations.append(rec)
                    
                    print(f"   ✅ 推薦: Short {premium_data['short_strike']} / Long {premium_data['long_strike']}")
                    print(f"      到期: {premium_data['expiry']}")
                    print(f"      權利金: ${credit:.2f} | ROI: {roi:.1f}%")
                else:
                     print(f"   ⚠️ 權利金過低 (${credit:.2f})，跳過。")
            else:
                print(f"   ⚠️ 無法獲取期權數據: {err}")
        else:
            print(f"   ⚠️ 無法生成 BPS 建議")

    # 輸出最終結果 JSON 格式供 LLM 解析
    print("\n" + "="*50)
    print("FINAL_RECOMMENDATIONS_START")
    print(json.dumps(recommendations, indent=2))
    print("FINAL_RECOMMENDATIONS_END")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
