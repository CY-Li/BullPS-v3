"""
BPS 交易推薦器 (BPS Trade Recommender)
=====================================
用途：
1. 掃描清單中技術面評分 > 75 且信心度 > 70 的強勢標的。
2. 自動呼叫 BPSOptimizer 建議 Short/Long Put 履約價。
3. 獲取即時選擇權權利金並計算 ROI，提供具體的交易策略建議。
"""

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
        short_put = puts[abs(puts['strike'] - short_strike) < 0.1]
        long_put = puts[abs(puts['strike'] - long_strike) < 0.1]
        
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
    
    # 1. 掃描
    watchlist_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stock_watchlist.json")
    try:
        with open(watchlist_path, 'r', encoding='utf-8') as f:
            full_list = json.load(f).get('stocks', [])
        scan_list = full_list if full_list else CORE_WATCHLIST
        print(f"📊 正在從 {watchlist_path} 讀取清單，共 {len(scan_list)} 支股票...")
    except Exception as e:
        print(f"⚠️ 無法讀取清單檔案，改用核心 30 支股票: {e}")
        scan_list = CORE_WATCHLIST
    
    all_results = []
    for symbol in scan_list:
        try:
            print(f"[{len(all_results)+1}/{len(scan_list)}] Analyzing {symbol}...", end='\r')
            analysis_result = analyzer.analyze_stock(symbol)
            if not analysis_result:
                continue
            
            # 建立標準化字典
            res_dict = {
                'symbol': symbol,
                'score': analysis_result.get('composite_score', 0),
                'confidence': analysis_result.get('confidence_level', 0),
                'price': analysis_result.get('current_price'),
                'timing_factors': analysis_result.get('confidence_factors', [])
            }
            all_results.append(res_dict)
            
            # 即時標註符合進場門檻的標的
            is_mega_cap = symbol in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
            threshold_score = 70 if is_mega_cap else 75
            threshold_conf = 65 if is_mega_cap else 70
            
            if res_dict['score'] >= threshold_score and res_dict['confidence'] >= threshold_conf:
                print(f"  ✨ {symbol} 符合進場標準! (Score: {res_dict['score']}, Conf: {res_dict['confidence']}%)")
                
        except Exception as e:
            continue

    # 排序所有結果 (分數高到低)
    all_results.sort(key=lambda x: x['score'], reverse=True)
    
    # 輸出前 10 名技術面排名 (與 IntegratedStockAnalyzer 一致)
    print("\n\n🏆 Top 10 Technical Rankings:")
    print(f"{'Symbol':<8} {'Score':<6} {'Conf%':<6} {'Price':<10} {'Factors'}")
    print("-" * 60)
    
    for res in all_results[:10]:
        factors = ", ".join(res['timing_factors'][:2])
        print(f"{res['symbol']:<8} {res['score']:<6.1f} {res['confidence']:<6} ${res['price']:<10.2f} {factors}")

    # 篩選出真正符合進場標準的候選名單進行 BPS 優化
    candidates = []
    for res in all_results:
        symbol = res['symbol']
        is_mega_cap = symbol in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
        threshold_score = 70 if is_mega_cap else 75
        threshold_conf = 65 if is_mega_cap else 70
        
        if res['score'] >= threshold_score and res['confidence'] >= threshold_conf:
            candidates.append(res)
    
    top_candidates = candidates[:10] # 取前 10 名符合標準的標的進行期權優化
    
    print(f"\n🔍 發現 {len(candidates)} 個符合進場標準的機會，精選前 {len(top_candidates)} 名進行 BPS 優化:\n")
    
    recommendations = []
    for cand in top_candidates:
        symbol = cand['symbol']
        print(f"👉 分析 {symbol} (Score: {cand['score']:.1f})...")
        
        # 2. 優化 BPS 點位 (預設 35 天到期)
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
                if credit > 0.05:
                    risk = width - credit
                    roi = (credit / risk) * 100
                    
                    rec = {
                        'symbol': symbol,
                        'price': cand['price'],
                        'expiry': premium_data['expiry'],
                        'short_strike': premium_data['short_strike'],
                        'long_strike': premium_data['long_strike'],
                        'credit': credit,
                        'roi': roi,
                        'reasons': cand['timing_factors']
                    }
                    recommendations.append(rec)
                    print(f"   ✅ 推薦: Short {premium_data['short_strike']} / Long {premium_data['long_strike']}")
                    print(f"      到期: {premium_data['expiry']} | 權利金: ${credit:.2f} | ROI: {roi:.1f}%")
                else:
                    print(f"   ⚠️ 權利金過低 (${credit:.2f})，跳過。")
            else:
                print(f"   ⚠️ 無法獲取期權數據: {err}")
        else:
            print(f"   ⚠️ 無法生成 BPS 建議")

    # 輸出最終結果 JSON 格式
    print("\n" + "="*50)
    print("FINAL_RECOMMENDATIONS_START")
    print(json.dumps(recommendations, indent=2))
    print("FINAL_RECOMMENDATIONS_END")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
