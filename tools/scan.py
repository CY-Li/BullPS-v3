"""
BPS 交易推薦器 (BPS Trade Recommender)
=====================================
用途：
1. 掃描清單中符合技術面標準的強勢標的。
2. 自動呼叫 BPSOptimizer 建議 Short/Long Put 履約價。
3. 獲取即時選擇權權利金並計算 ROI，提供具體的交易策略建議。

模式 (Modes):
- standard (預設): Score > 75, Conf > 70
- relaxed: Score > 50, IV Rank > 15
- strict (Iron Shield): Score > 75, Conf > 70, IV Rank > 20
"""

import sys
import os
import json
import argparse
import warnings
from datetime import datetime
warnings.filterwarnings('ignore')

# Add current directory and core directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
core_dir = os.path.join(project_root, "core")

if project_root not in sys.path: sys.path.append(project_root)
if core_dir not in sys.path: sys.path.append(core_dir)

from core.integrated_stock_analyzer import IntegratedStockAnalyzer
from core.bps_optimizer import BPSOptimizer
from core.options_helper import get_real_premium

# 核心清單 (Fallback)
CORE_WATCHLIST = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX", "AMD", 
    "DIS", "BA", "JPM", "WMT", "V", "MA", "KO", "PEP", "COST", "INTC", "PYPL",
    "CRM", "ADBE", "QCOM", "TXN", "HON", "UNH", "PG", "XOM", "CVX", "MRK", "IWM", "SPY", "QQQ"
]

def parse_args():
    parser = argparse.ArgumentParser(description='BPS Scan Tool')
    parser.add_argument('--mode', choices=['standard', 'relaxed', 'strict'], default='standard', help='Scan mode stringency')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of stocks to scan (0 for all)')
    return parser.parse_args()

def main():
    args = parse_args()
    print(f"🚀 開始 BPS 掃描 (Mode: {args.mode}) ... [Date: {datetime.now().strftime('%Y-%m-%d')}]")
    
    analyzer = IntegratedStockAnalyzer()
    optimizer = BPSOptimizer()
    
    # 設定閾值
    min_score = 75
    min_conf = 70
    min_iv_rank = 0
    
    if args.mode == 'relaxed':
        min_score = 50
        min_conf = 0 # 不強制要求 confidence
        min_iv_rank = 15
        print(f"ℹ️ Relaxed Mode: Score > {min_score}, IV Rank > {min_iv_rank}")
    elif args.mode == 'strict':
        min_score = 75
        min_conf = 70
        min_iv_rank = 20
        print(f"ℹ️ Strict Mode (Iron Shield): Score > {min_score}, Conf > {min_conf}, IV Rank > {min_iv_rank}")
    else:
        print(f"ℹ️ Standard Mode: Score > {min_score}, Conf > {min_conf}")

    # 1. 讀取清單
    watchlist_path = os.path.join(project_root, "stock_watchlist.json")
    try:
        with open(watchlist_path, 'r', encoding='utf-8') as f:
            full_list = json.load(f).get('stocks', [])
        scan_list = full_list if full_list else CORE_WATCHLIST
        print(f"📊 正在從 {watchlist_path} 讀取清單，共 {len(scan_list)} 支股票...")
    except Exception as e:
        print(f"⚠️ 無法讀取清單檔案，改用核心清單: {e}")
        scan_list = CORE_WATCHLIST
    
    if args.limit > 0:
        scan_list = scan_list[:args.limit]
        print(f"⚠️ 限制掃描前 {args.limit} 支股票")

    candidates = []
    
    for i, symbol in enumerate(scan_list):
        try:
            print(f"[{i+1}/{len(scan_list)}] Analyzing {symbol}...", end='\r')
            
            # 1. 技術分析
            analysis_result = analyzer.analyze_stock(symbol)
            if not analysis_result: continue
            
            score = analysis_result.get('composite_score', 0)
            confidence = analysis_result.get('confidence_level', 0)
            
            # 初步過濾
            if score < min_score: continue
            if confidence < min_conf: continue
            
            # 2. BPS 優化 (獲取 IV Rank)
            bps_setup = optimizer.suggest_bps_strikes(symbol, days_to_expiry=35)
            if not bps_setup: continue
            
            iv_rank = bps_setup.get('iv_rank', 0)
            if iv_rank < min_iv_rank: continue
            
            # 3. 獲取權利金
            premium_data, err = get_real_premium(
                symbol, 
                bps_setup['short_put_strike'], 
                bps_setup['long_put_strike'], 
                bps_setup['suggested_expiry']
            )
            
            if premium_data:
                width = premium_data['short_strike'] - premium_data['long_strike']
                credit = premium_data['credit']
                
                # 簡單過濾垃圾權利金
                if credit > 0.05 and width > 0:
                    risk = width - credit
                    roi = (credit / risk) * 100
                    
                    # 記錄結果
                    candidates.append({
                        'symbol': symbol,
                        'price': analysis_result.get('current_price'),
                        'score': score,
                        'confidence': confidence,
                        'iv_rank': iv_rank,
                        'expiry': premium_data['expiry'],
                        'short_strike': premium_data['short_strike'],
                        'long_strike': premium_data['long_strike'],
                        'credit': round(credit, 2),
                        'roi': round(roi, 1),
                        'reasons': analysis_result.get('confidence_factors', [])
                    })
                    print(f"  ✨ {symbol} 符合標準! (Score: {score:.1f}, IVR: {iv_rank:.1f}, ROI: {roi:.1f}%)")
        except Exception as e:
            continue

    # 排序
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    print("\n\n🏆 Top Recommendations:")
    print(f"{'Symbol':<8} {'Score':<6} {'Conf%':<6} {'IVR':<5} {'Price':<10} {'Credit':<8} {'ROI%':<6} {'Expiry'}")
    print("-" * 80)
    
    top_candidates = candidates[:10]
    for res in top_candidates:
        print(f"{res['symbol']:<8} {res['score']:<6.1f} {res['confidence']:<6} {res['iv_rank']:<5.1f} ${res['price']:<10.2f} ${res['credit']:<8.2f} {res['roi']:<6.1f} {res['expiry']}")

    print("\n" + "="*50)
    print("FINAL_RECOMMENDATIONS_START")
    print(json.dumps(top_candidates, indent=2))
    print("FINAL_RECOMMENDATIONS_END")
    print("="*50 + "\n")
    
    # 寫入 Memory (如果沒有被其他流程調用)
    try:
        memory_file = os.path.join(project_root, "memory", datetime.now().strftime("%Y-%m-%d") + ".md")
        # 這裡不實作寫入，避免權限問題或與 Agent 邏輯衝突，由 Agent 解析輸出後寫入
    except:
        pass

if __name__ == "__main__":
    main()
