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
from integrated_stock_analyzer import IntegratedStockAnalyzer
# 複用出場評估邏輯
from backend.portfolio_manager import evaluate_exit_confidence, load_json_file, ANALYSIS_RESULT_FILE

warnings.filterwarnings('ignore')

# --- 回測參數設定 ---
START_DATE = "2024-01-01"
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
    df_all = yf.download(symbols, start=preload_start_date, end=end, progress=True)
    
    if df_all.empty:
        print("[ERROR] 下載數據失敗，請檢查網路連線或股票代號。")
        return None

    for symbol in symbols:
        if isinstance(df_all.columns, pd.MultiIndex) and symbol in df_all.columns.get_level_values(1):
            df_symbol = df_all.xs(symbol, level=1, axis=1).copy()
            df_symbol.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)
            if not df_symbol.empty:
                all_data[symbol] = df_symbol
        elif symbol in df_all.columns:
            df_symbol = df_all.copy()
            df_symbol.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)
            if not df_symbol.empty:
                all_data[symbol] = df_symbol

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
        
        spy_data = yf.download('SPY', start=START_DATE, end=END_DATE, progress=False)
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
            # 確保至少持有一個交易日
            if current_day <= trade_info['entry_date']:
                continue

            data_slice = self.all_data[symbol].loc[:current_day]
            # Parabolic SAR 需要一些數據點來計算，這裡保持一個合理的最小值
            if data_slice.empty or len(data_slice) < 20:
                continue

            # --- 使用 Parabolic SAR 作為移動停損 ---
            # 必須先計算包含當前日在內的所有指標
            df_with_indicators = self.analyzer.calculate_technical_indicators(data_slice)
            if df_with_indicators is None or df_with_indicators.empty:
                continue

            current_price = df_with_indicators['Close'].iloc[-1]
            current_sar = df_with_indicators['SAR'].iloc[-1]

            # 1. 檢查數據有效性
            if pd.isna(current_price) or pd.isna(current_sar):
                print(f"   - [CRITICAL WARNING] {symbol} 在 {current_day.strftime('%Y-%m-%d')} 缺少價格或SAR數據，無法評估出場。")
                continue

            should_sell = False
            # 2. 優先執行 Parabolic SAR 移動停損檢查
            if current_price < current_sar:
                print(f"   - [出場信號] {symbol}: 觸發 Parabolic SAR 移動停損 (價格: {current_price:.2f} < SAR: {current_sar:.2f})。")
                should_sell = True
            else:
                # 3. 若未觸發SAR停損，才執行綜合模型評估
                # 我們需要完整的分析快照，而不僅僅是指標
                latest_analysis_snapshot = self.run_analysis_on_slice(symbol, data_slice)
                if not latest_analysis_snapshot:
                    continue

                exit_report = evaluate_exit_confidence(trade_info, latest_analysis_snapshot)
                
                if exit_report.get('exit_confidence', 0.0) >= 0.8:
                    print(f"   - [出場信號] {symbol}: 出場信心度達到 {exit_report['exit_confidence']:.2f} (>= 0.8)。")
                    should_sell = True

            if should_sell:
                symbols_to_sell.append(symbol)

        for symbol in symbols_to_sell:
            if next_day not in self.all_data[symbol].index:
                print(f"   - [賣出失敗] {symbol} 在 {next_day.strftime('%Y-%m-%d')} 無數據。")
                continue
            exit_price = self.all_data[symbol].loc[next_day]['Open']
            self.execute_sell(symbol, next_day, exit_price)

    def check_and_execute_entries(self, current_day, next_day):
        for symbol in self.symbols:
            if symbol in self.portfolio:
                continue
            
            if symbol not in self.all_data:
                continue

            data_slice = self.all_data[symbol].loc[:current_day]
            if data_slice.empty or len(data_slice) < 60:
                continue

            analysis_result = self.run_analysis_on_slice(symbol, data_slice)
            if not analysis_result:
                continue

            composite_score = analysis_result.get('composite_score', 0)
            confidence_score = analysis_result.get('confidence_score', 0)

            if composite_score >= 90 and confidence_score >= 80:
                print(f"   - [進場信號] {symbol}: 綜合評分 {composite_score:.2f}, 信心度 {confidence_score:.2f}")
                if next_day not in self.all_data[symbol].index:
                    print(f"   - [買入失敗] {symbol} 在 {next_day.strftime('%Y-%m-%d')} 無數據。")
                    continue
                entry_price = self.all_data[symbol].loc[next_day]['Open']
                self.execute_buy(symbol, next_day, entry_price, analysis_result)

    def run_analysis_on_slice(self, symbol, data_slice):
        df = self.analyzer.calculate_technical_indicators(data_slice)
        if df is None: return None

        signals = self.analyzer.detect_bullish_signals(df)
        if not signals: return None
        
        latest_signal = signals[-1]

        long_signal_price, long_signal_confidence = self.analyzer.calculate_long_signal_price(df)
        entry_advice, confidence_score, confidence_level, confidence_factors = self.analyzer.assess_entry_opportunity(df)
        
        current_price = df['Close'].iloc[-1]
        distance_to_signal = ((current_price - long_signal_price) / long_signal_price) * 100
        
        days_since_signal = (df.index[-1] - latest_signal['date']).days
        max_days = 30
        long_days_score = max(0, (max_days - days_since_signal) / max_days * 100)
        distance_score = np.maximum(0, 100 - distance_to_signal)
        entry_scores = {'強烈推薦進場': 100, '建議進場': 80, '觀望': 50, '不建議進場': 20}
        entry_score = entry_scores.get(entry_advice, 0)
        
        composite_score = (long_days_score * 0.3 + distance_score * 0.3 + entry_score * 0.2 + confidence_score * 0.2)

        return {
            'symbol': symbol,
            'composite_score': composite_score,
            'confidence_score': confidence_score,
            'trend_reversal_confirmation': df['Trend_Reversal_Confirmation'].iloc[-1],
            'reversal_strength': df['Reversal_Strength'].iloc[-1],
            'reversal_reliability': df['Reversal_Reliability'].iloc[-1],
            'short_term_momentum_turn': df['Short_Term_Momentum_Turn'].iloc[-1],
            'initial_analysis_snapshot': {
                'symbol': symbol,
                'entry_price': current_price,
                'confidence_factors': confidence_factors,
            }
        }

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
