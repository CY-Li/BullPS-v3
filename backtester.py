#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化交易策略回測程式
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import json
import warnings
import time
from pathlib import Path
import pytz

# 複用現有的分析器
import sys
import os
# 將當前目錄和 core 目錄加入路徑
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'core')))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from core.integrated_stock_analyzer import IntegratedStockAnalyzer
# 複用出場評估邏輯
try:
    from backend.portfolio_manager import evaluate_exit_confidence, load_json_file
except ImportError:
    # 這裡可能需要根據實際 backend 資料夾結構調整
    pass

warnings.filterwarnings('ignore')

# --- 回測參數設定 ---
START_DATE = "2026-01-01"
END_DATE = datetime.now().strftime("%Y-%m-%d")
TRADE_AMOUNT_USD = 100.00  # 每次交易投入100美元
WATCHLIST_FILE = 'stock_watchlist.json'
OUTPUT_CSV = 'backtest_trade_log.csv'

# --- 輔助函式 ---

def load_watchlist(file_path):
    """載入觀察名單"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('stocks', [])
    except FileNotFoundError:
        print(f"[ERROR] 找不到觀察名單檔案: {file_path}")
        return []

def preload_data(symbols, start, end):
    """預先下載所有需要的歷史數據"""
    print(f"正在從 {start} 到 {end} 預先下載 {len(symbols)} 支股票的數據...")
    
    preload_start_date = (pd.to_datetime(start) - timedelta(days=90)).strftime('%Y-%m-%d')
    
    all_data = {}
    df_all = yf.download(symbols, start=preload_start_date, end=end, progress=True, auto_adjust=True)
    
    if df_all.empty:
        print("[ERROR] 下載數據失敗，請檢查網路連線或股票代號。")
        return None

    failed_symbols = []

    for symbol in symbols:
        try:
            # 跳過無效的股票代號
            if not symbol or symbol in ['UNKNOWN', '$UNKNOWN'] or symbol.startswith('$'):
                failed_symbols.append(symbol)
                continue

            df_symbol = None

            if isinstance(df_all.columns, pd.MultiIndex) and symbol in df_all.columns.get_level_values(1):
                df_symbol = df_all.xs(symbol, level=1, axis=1).copy()
            elif symbol in df_all.columns:
                df_symbol = df_all.copy()

            if df_symbol is not None:
                df_symbol.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)

                # 檢查數據質量
                if not df_symbol.empty and len(df_symbol) >= 30:
                    all_data[symbol] = df_symbol
                else:
                    failed_symbols.append(symbol)
                    if df_symbol.empty:
                        print(f"  ⚠️  {symbol}: 數據為空")
                    else:
                        print(f"  ⚠️  {symbol}: 數據不足 ({len(df_symbol)}天)")
            else:
                failed_symbols.append(symbol)
                print(f"  ❌ {symbol}: 未找到數據")

        except Exception as e:
            failed_symbols.append(symbol)
            print(f"  ❌ {symbol}: 處理失敗 - {str(e)}")

    if failed_symbols:
        print(f"\n{len(failed_symbols)} Failed downloads:")
        for i, symbol in enumerate(failed_symbols):
            if i < 10:  # 只顯示前10個失敗的
                print(f"['{symbol}']")
            elif i == 10:
                print(f"... and {len(failed_symbols) - 10} more")
                break

    print(f"[SUCCESS] 成功預載 {len(all_data)} 支股票的數據。")
    return all_data

# --- 回測核心類別 ---

class Backtester:
    def __init__(self, symbols, all_historical_data):
        self.analyzer = IntegratedStockAnalyzer()
        self.symbols = symbols
        self.all_data = all_historical_data
        self.portfolio = {}
        self.trade_log = []
        
        spy_data = yf.download('SPY', start=START_DATE, end=END_DATE, progress=False, auto_adjust=True)
        self.trading_days = spy_data.index

    def run(self):
        print(f"[INFO] 開始回測，期間: {START_DATE} to {END_DATE}")
        
        for i in range(len(self.trading_days) - 1):
            current_day = self.trading_days[i]
            next_day = self.trading_days[i+1]
            
            print(f"--- 模擬交易日: {current_day.strftime('%Y-%m-%d')} ---")

            self.check_and_execute_exits(current_day, next_day)
            self.check_and_execute_entries(current_day, next_day)

        print("[SUCCESS] 回測完成。")
        self.generate_report()

    def check_and_execute_exits(self, current_day, next_day):
        if not self.portfolio:
            return

        symbols_to_sell = []
        for symbol, trade_info in self.portfolio.items():
            if current_day <= trade_info['entry_date']:
                continue

            # 使用新版的分析方法
            analysis_result = self.analyze_at_date(symbol, current_day)
            if not analysis_result:
                continue

            current_price = analysis_result['current_price']
            
            # --- 出場邏輯 (信心侵蝕) ---
            # 1. 信心度過低
            if analysis_result['confidence_level'] < 40:
                print(f"   - [出場信號] {symbol}: 信心度低於 40% ({analysis_result['confidence_level']}%)")
                symbols_to_sell.append(symbol)
                continue

            # 2. 綜合評分轉弱
            if analysis_result['composite_score'] < 50:
                print(f"   - [出場信號] {symbol}: 綜合評分轉弱 ({analysis_result['composite_score']})")
                symbols_to_sell.append(symbol)
                continue
            
            # 3. 基礎移動停損 (跌破關鍵支撐)
            if current_price < analysis_result['sar'] * 0.98: # 寬鬆一點
                print(f"   - [出場信號] {symbol}: 跌破 SAR 支撐")
                symbols_to_sell.append(symbol)

        for symbol in symbols_to_sell:
            if next_day not in self.all_data[symbol].index:
                continue
            exit_price = self.all_data[symbol].loc[next_day]['Open']
            self.execute_sell(symbol, next_day, exit_price)

    def check_and_execute_entries(self, current_day, next_day):
        for symbol in self.symbols:
            if symbol in self.portfolio:
                continue
            
            analysis_result = self.analyze_at_date(symbol, current_day)
            if not analysis_result:
                continue

            composite_score = analysis_result['composite_score']
            confidence_level = analysis_result['confidence_level']
            
            # 進場條件：評分 >= 75 且 信心度 >= 70% (針對優化後的評分)
            if composite_score >= 75 and confidence_level >= 70:
                print(f"   - [進場信號] {symbol}: 綜合評分 {composite_score:.1f}, 信心度 {confidence_level}%")
                if next_day not in self.all_data[symbol].index:
                    continue
                entry_price = self.all_data[symbol].loc[next_day]['Open']
                self.execute_buy(symbol, next_day, entry_price, analysis_result)

    def analyze_at_date(self, symbol, target_date):
        """在特定日期模擬 analyze_stock 的行為"""
        if symbol not in self.all_data:
            return None
            
        full_df = self.all_data[symbol]
        data_slice = full_df.loc[:target_date]
        
        if len(data_slice) < 30:
            return None
            
        # 由於 IntegratedStockAnalyzer 的 analyze_stock 預設抓取 yfinance 資料
        # 我們需要稍微修改一下，讓它能處理我們傳入的 data_slice
        # 這裡我們手動模擬它的分析流程
        try:
            df_with_inds = self.analyzer.calculate_technical_indicators(data_slice)
            if df_with_inds is None: return None
            
            # 以下邏輯同步自 IntegratedStockAnalyzer.analyze_stock
            current_price = df_with_inds['Close'].iloc[-1]
            rsi = df_with_inds['RSI'].iloc[-1]
            macd_hist = df_with_inds['MACD_Histogram'].iloc[-1]
            ma20 = df_with_inds['MA20'].iloc[-1]
            sar = df_with_inds['SAR'].iloc[-1]
            
            # 使用已更新的 analyzer 方法
            timing_res = self.analyzer.calculate_entry_timing_score(df_with_inds)
            timing_score = timing_res['timing_score']
            timing_factors = timing_res['timing_factors']
            
            reversal_conf = self.analyzer.calculate_trend_reversal_confirmation(df_with_inds)
            support_reliability = df_with_inds['Support_Reliability'].iloc[-1]
            
            # 簡單加權平均
            composite_score = (timing_score * 0.4) + (reversal_conf * 0.3) + (min(100, support_reliability) * 0.3)
            
            # 計算信心度
            confidence_level = 50 
            if rsi < 40 and macd_hist > 0: confidence_level += 20
            if current_price > ma20: confidence_level += 15
            if reversal_conf > 40: confidence_level += 15
            
            return {
                'symbol': symbol,
                'current_price': current_price,
                'composite_score': composite_score,
                'confidence_level': min(100, confidence_level),
                'confidence_score': min(100, confidence_level),
                'sar': sar,
                'rsi': rsi,
                'macd_histogram': macd_hist,
                'ma20': ma20,
                'reversal_confirmation': reversal_conf,
                'trend_reversal_confirmation': reversal_conf,
                'reversal_strength': df_with_inds['Reversal_Strength'].iloc[-1],
                'reversal_reliability': df_with_inds['Reversal_Reliability'].iloc[-1],
                'short_term_momentum_turn': df_with_inds['Short_Term_Momentum_Turn'].iloc[-1],
                'initial_analysis_snapshot': {
                    'symbol': symbol,
                    'entry_price': current_price,
                    'confidence_factors': timing_factors
                }
            }
        except Exception as e:
            # print(f"Analysis error at date: {e}")
            return None

    def execute_buy(self, symbol, date, price, analysis_result):
        if pd.isna(price) or price == 0:
            print(f"   - [買入失敗] {symbol} 在 {date.strftime('%Y-%m-%d')} 無開盤價數據。")
            return
            
        shares = TRADE_AMOUNT_USD / price
        self.portfolio[symbol] = {
            'entry_date': date,
            'entry_price': price,
            'shares': shares,
            # 修正: 使用 portfolio_manager 期望的正確鍵名 'initial_analysis_snapshot'
            'initial_analysis_snapshot': analysis_result['initial_analysis_snapshot'],
            'composite_score': analysis_result['composite_score'],
            'confidence_score': analysis_result['confidence_score'],
            'trend_reversal_confirmation': analysis_result['trend_reversal_confirmation'],
            'reversal_strength': analysis_result['reversal_strength'],
            'reversal_reliability': analysis_result['reversal_reliability'],
            'short_term_momentum_turn': analysis_result['short_term_momentum_turn'],
        }
        print(f"   - [執行買入] {symbol} at ${price:.2f} on {date.strftime('%Y-%m-%d')}")

    def execute_sell(self, symbol, date, price):
        if pd.isna(price) or price == 0:
            print(f"   - [賣出失敗] {symbol} 在 {date.strftime('%Y-%m-%d')} 無開盤價數據。")
            if symbol in self.portfolio:
                del self.portfolio[symbol]
            return

        trade_info = self.portfolio.pop(symbol, None)
        if not trade_info:
            return

        profit_loss = (price - trade_info['entry_price']) * trade_info['shares']
        profit_loss_pct = (price / trade_info['entry_price'] - 1) * 100

        self.trade_log.append({
            'symbol': symbol,
            'entry_date': trade_info['entry_date'].strftime('%Y-%m-%d'),
            'entry_price': trade_info['entry_price'],
            'exit_date': date.strftime('%Y-%m-%d'),
            'exit_price': price,
            'holding_period_days': (date - trade_info['entry_date']).days,
            'profit_loss_usd': profit_loss,
            'profit_loss_pct': profit_loss_pct,
            'composite_score_at_entry': trade_info['composite_score'],
            'confidence_score_at_entry': trade_info['confidence_score'],
            'trend_reversal_confirmation': trade_info['trend_reversal_confirmation'],
            'reversal_strength': trade_info['reversal_strength'],
            'reversal_reliability': trade_info['reversal_reliability'],
            'short_term_momentum_turn': trade_info['short_term_momentum_turn'],
        })
        print(f"   - [執行賣出] {symbol} at ${price:.2f} on {date.strftime('%Y-%m-%d')}. P/L: ${profit_loss:.2f} ({profit_loss_pct:.2f}%)")

    def generate_report(self):
        if not self.trade_log:
            print("\n[回測報告]: 沒有完成任何交易。")
            return

        df_log = pd.DataFrame(self.trade_log)
        
        df_log.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
        print(f"\n[詳細交易日誌已儲存至]: {OUTPUT_CSV}")

        total_trades = len(df_log)
        winning_trades = df_log[df_log['profit_loss_usd'] > 0]
        losing_trades = df_log[df_log['profit_loss_usd'] <= 0]
        
        win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0
        total_pnl = df_log['profit_loss_usd'].sum()
        
        avg_profit = winning_trades['profit_loss_usd'].mean()
        avg_loss = losing_trades['profit_loss_usd'].mean()
        
        profit_factor = abs(winning_trades['profit_loss_usd'].sum() / losing_trades['profit_loss_usd'].sum()) if len(losing_trades) > 0 and losing_trades['profit_loss_usd'].sum() != 0 else float('inf')
        
        avg_holding_period = df_log['holding_period_days'].mean()

        print("\n" + "="*50)
        print("[回測績效報告]")
        print("="*50)
        print(f"  回測期間: {START_DATE} to {END_DATE}")
        print(f"  總交易次數: {total_trades}")
        print(f"  勝率: {win_rate:.2f}%")
        print(f"  總盈虧: ${total_pnl:.2f}")
        print("-" * 50)
        print(f"  平均盈利: ${avg_profit:.2f}")
        print(f"  平均虧損: ${avg_loss:.2f}")
        print(f"  盈虧比 (Profit Factor): {profit_factor:.2f}")
        print(f"  平均持倉天數: {avg_holding_period:.1f} 天")
        print("="*50)

def main():
    """主執行函式"""
    watchlist = load_watchlist(WATCHLIST_FILE)
    if not watchlist:
        return

    all_data = preload_data(watchlist, START_DATE, END_DATE)
    if not all_data:
        return

    backtester = Backtester(watchlist, all_data)
    backtester.run()

if __name__ == "__main__":
    main()
