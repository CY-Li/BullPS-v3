import json
from pathlib import Path
import yfinance as yf
from datetime import datetime
import pytz
import pandas as pd
import numpy as np
import time

# 沿用 integrated_stock_analyzer.py 的指標計算邏輯
# 這裡可以簡化，因為我們只需要最新的指標值
class StockExitEvaluator:
    def __init__(self):
        pass

    def get_stock_data(self, symbol, period='90d', max_retries=3):
        for attempt in range(max_retries):
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period=period, timeout=30)
                if data.empty:
                    return None
                return data
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    print(f"❌ 無法獲取 {symbol} 的數據: {e}")
                    return None
        return None

    def calculate_technical_indicators(self, data):
        if data is None or data.empty or len(data) < 30:
            return None
            
        df = data.copy()
        
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA30'] = df['Close'].rolling(window=30).mean()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
        
        low_min = df['Low'].rolling(window=9).min()
        high_max = df['High'].rolling(window=9).max()
        df['RSV'] = (df['Close'] - low_min) / (high_max - low_min) * 100
        df['K'] = df['RSV'].ewm(com=2).mean()
        df['D'] = df['K'].ewm(com=2).mean()

        bb_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['MA20'] + (bb_std * 2)
        
        df['Price_Momentum'] = df['Close'].pct_change(periods=5)
        
        # 簡易SAR計算
        sar = [df['Low'].iloc[0]]
        ep = df['High'].iloc[0]
        trend = 1
        af_val = 0.02
        max_af = 0.2
        for i in range(1, len(df)):
            prev_sar = sar[-1]
            if trend == 1:
                sar_val = prev_sar + af_val * (ep - prev_sar)
                if df['Low'].iloc[i] < sar_val:
                    trend = -1; sar_val = ep; ep = df['Low'].iloc[i]; af_val = 0.02
                else:
                    if df['High'].iloc[i] > ep: ep = df['High'].iloc[i]; af_val = min(af_val + 0.02, max_af)
            else:
                sar_val = prev_sar + af_val * (ep - prev_sar)
                if df['High'].iloc[i] > sar_val:
                    trend = 1; sar_val = ep; ep = df['High'].iloc[i]; af_val = 0.02
                else:
                    if df['Low'].iloc[i] < ep: ep = df['Low'].iloc[i]; af_val = min(af_val + 0.02, max_af)
            sar.append(sar_val)
        df['SAR'] = pd.Series(sar, index=df.index)

        return df # 返回包含所有指標的完整DataFrame

    def check_exit_conditions(self, stock_info, latest_indicators, data):
        # Define categories for exit reasons
        EXIT_CATEGORY_SUPPORT_BREAK = "關鍵支撐位跌破"
        EXIT_CATEGORY_TECH_INDICATOR_BAD = "技術指標惡化"
        EXIT_CATEGORY_ABNORMAL_VOLUME = "成交量異常"
        EXIT_CATEGORY_TARGET_REACHED = "目標價位達成"
        EXIT_CATEGORY_MOMENTUM_WEAKENING = "動能減弱/趨勢反轉訊號"

        categorized_exit_reasons = {
            EXIT_CATEGORY_SUPPORT_BREAK: [],
            EXIT_CATEGORY_TECH_INDICATOR_BAD: [],
            EXIT_CATEGORY_ABNORMAL_VOLUME: [],
            EXIT_CATEGORY_TARGET_REACHED: [],
            EXIT_CATEGORY_MOMENTUM_WEAKENING: []
        }
        current_price = latest_indicators['Close']
        
        # 1. 關鍵支撐位跌破
        if current_price < stock_info['long_signal_price_at_entry']:
            categorized_exit_reasons[EXIT_CATEGORY_SUPPORT_BREAK].append(f"股價 ({current_price:.2f}) 低於進場時的抄底價 ({stock_info['long_signal_price_at_entry']:.2f})")
        if current_price < latest_indicators['MA20']:
            categorized_exit_reasons[EXIT_CATEGORY_SUPPORT_BREAK].append(f"股價 ({current_price:.2f}) 跌破 MA20 ({latest_indicators['MA20']:.2f})")
        if current_price < latest_indicators['MA30']:
            categorized_exit_reasons[EXIT_CATEGORY_SUPPORT_BREAK].append(f"股價 ({current_price:.2f}) 跌破 MA30 ({latest_indicators['MA30']:.2f})")
        if current_price < latest_indicators['SAR']:
            categorized_exit_reasons[EXIT_CATEGORY_SUPPORT_BREAK].append(f"SAR 指標翻空：股價 ({current_price:.2f}) 低於 SAR ({latest_indicators['SAR']:.2f})")
        
        # 新增：固定百分比止損
        if 'entry_price' in stock_info and 'stop_loss_percent' in stock_info and stock_info['stop_loss_percent'] > 0:
            stop_loss_price = stock_info['entry_price'] * (1 - stock_info['stop_loss_percent'])
            if current_price <= stop_loss_price:
                categorized_exit_reasons[EXIT_CATEGORY_SUPPORT_BREAK].append(f"固定百分比止損：股價 ({current_price:.2f}) 跌破止損價 ({stop_loss_price:.2f})，止損百分比 {stock_info['stop_loss_percent']:.2%}")

        # 2. 技術指標惡化
        if latest_indicators['RSI'] < 40: # 保持40，如果需要30可以再調整
            categorized_exit_reasons[EXIT_CATEGORY_TECH_INDICATOR_BAD].append(f"RSI ({latest_indicators['RSI']:.2f}) 跌破 40")
        if latest_indicators['MACD_Histogram'] < 0:
            categorized_exit_reasons[EXIT_CATEGORY_TECH_INDICATOR_BAD].append(f"MACD 柱狀圖轉負 ({latest_indicators['MACD_Histogram']:.2f})")
        # MACD 死叉判斷 (需要歷史數據，這裡簡化為柱狀圖轉負)
        if latest_indicators['K'] < 50 and latest_indicators['K'] < latest_indicators['D']:
             categorized_exit_reasons[EXIT_CATEGORY_TECH_INDICATOR_BAD].append(f"KD 死叉且 K值 ({latest_indicators['K']:.2f}) 跌破 50")

        # 3. 成交量異常
        if latest_indicators['Close'] < latest_indicators['Open'] and latest_indicators['Volume'] > data['Volume'].rolling(20).mean().iloc[-1] * 1.5:
             categorized_exit_reasons[EXIT_CATEGORY_ABNORMAL_VOLUME].append(f"股價下跌但成交量放大")

        # 4. 目標價位達成
        if current_price >= latest_indicators['BB_Upper']:
            categorized_exit_reasons[EXIT_CATEGORY_TARGET_REACHED].append(f"股價 ({current_price:.2f}) 觸及或突破布林通道上軌 ({latest_indicators['BB_Upper']:.2f})")
        # 股價接近或觸及前高阻力位 (目前未實作，需要額外邏輯)

        # 新增：固定百分比止盈
        if 'entry_price' in stock_info and 'take_profit_percent' in stock_info and stock_info['take_profit_percent'] > 0:
            take_profit_price = stock_info['entry_price'] * (1 + stock_info['take_profit_percent'])
            if current_price >= take_profit_price:
                categorized_exit_reasons[EXIT_CATEGORY_TARGET_REACHED].append(f"固定百分比止盈：股價 ({current_price:.2f}) 達到止盈價 ({take_profit_price:.2f})，止盈百分比 {stock_info['take_profit_percent']:.2%}")

        # 5. 動能減弱/趨勢反轉訊號
        if latest_indicators['RSI'] > 70 and latest_indicators['RSI'] < data['RSI'].iloc[-2]: # 保持70，如果需要80可以再調整
            categorized_exit_reasons[EXIT_CATEGORY_MOMENTUM_WEAKENING].append(f"RSI 在超買區 ({latest_indicators['RSI']:.2f}) 開始向下")
        if latest_indicators['MACD_Histogram'] < data['MACD_Histogram'].iloc[-2]:
            categorized_exit_reasons[EXIT_CATEGORY_MOMENTUM_WEAKENING].append(f"MACD 柱狀圖縮小")
        # MACD 死叉 (已在技術指標惡化中部分涵蓋，這裡不再重複)
        if latest_indicators['K'] < latest_indicators['D'] and data['K'].iloc[-2] > data['D'].iloc[-2]:
             categorized_exit_reasons[EXIT_CATEGORY_MOMENTUM_WEAKENING].append(f"KD 死叉")
        if latest_indicators['Price_Momentum'] < 0:
            categorized_exit_reasons[EXIT_CATEGORY_MOMENTUM_WEAKENING].append(f"價格動量轉負 ({latest_indicators['Price_Momentum']:.2%})")
        if latest_indicators['MA5'] < latest_indicators['MA20'] and data['MA5'].iloc[-2] > data['MA20'].iloc[-2]:
            categorized_exit_reasons[EXIT_CATEGORY_MOMENTUM_WEAKENING].append(f"均線死叉 (MA5下穿MA20)")
        
        # 新增：成交量萎縮
        # 判斷當前成交量是否顯著低於過去20日平均成交量的一半 (可調整閾值)
        if latest_indicators['Volume'] < data['Volume'].rolling(20).mean().iloc[-1] * 0.5:
            categorized_exit_reasons[EXIT_CATEGORY_MOMENTUM_WEAKENING].append(f"成交量萎縮：當前成交量 ({latest_indicators['Volume']:.0f}) 顯著低於20日均量")
        # 價量背離 (目前未實作，需要額外邏輯)
        # 趨勢反轉相關指標 (目前未實作)

        return categorized_exit_reasons

def run_portfolio_manager():
    print("🚀 啟動投資組合管理器...")
    
    BASE_DIR = Path(__file__).parent
    MONITORED_STOCKS_PATH = BASE_DIR / "monitored_stocks.json"
    TRADE_HISTORY_PATH = BASE_DIR / "trade_history.json"
    
    try:
        with open(MONITORED_STOCKS_PATH, 'r', encoding='utf-8') as f:
            monitored_stocks = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("ℹ️  監控清單為空或不存在，無需處理。")
        monitored_stocks = []

    try:
        with open(TRADE_HISTORY_PATH, 'r', encoding='utf-8') as f:
            trade_history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        trade_history = []

    if not monitored_stocks:
        print("✅ 監控清單為空，任務完成。")
        return

    print(f"🔍 開始檢查 {len(monitored_stocks)} 支監控中的股票...")
    evaluator = StockExitEvaluator()
    
    remaining_monitored_stocks = []
    stocks_to_close = []

    # 設定綜合評估閾值
    MIN_CATEGORIES_TRIGGERED = 2  # 至少需要觸發的類別數量
    MIN_TOTAL_REASONS_TRIGGERED = 3 # 至少需要觸發的總條件數量

    for stock in monitored_stocks:
        symbol = stock['symbol']
        print(f"   正在評估 {symbol}...")
        
        data = evaluator.get_stock_data(symbol)
        if data is None:
            print(f"   ⚠️ 無法獲取 {symbol} 的數據，本次跳過。")
            remaining_monitored_stocks.append(stock) # 保留無法獲取數據的股票
            continue
            
        df_with_indicators = evaluator.calculate_technical_indicators(data)
        if df_with_indicators is None:
            print(f"   ⚠️ 無法計算 {symbol} 的技術指標，本次跳過。")
            remaining_monitored_stocks.append(stock)
            continue

        latest_indicators = df_with_indicators.iloc[-1]
        categorized_exit_reasons = evaluator.check_exit_conditions(stock, latest_indicators, df_with_indicators)
        
        # 綜合評估平倉條件
        triggered_categories = [category for category, reasons in categorized_exit_reasons.items() if reasons]
        total_triggered_reasons = sum(len(reasons) for reasons in categorized_exit_reasons.values())

        if len(triggered_categories) >= MIN_CATEGORIES_TRIGGERED and total_triggered_reasons >= MIN_TOTAL_REASONS_TRIGGERED:
            # 將所有觸發原因扁平化為一個列表，用於記錄
            all_exit_reasons = []
            for category, reasons in categorized_exit_reasons.items():
                if reasons:
                    all_exit_reasons.append(f"{category}: {'; '.join(reasons)}")

            current_price = latest_indicators['Close']
            entry_price = stock['entry_price']
            profit_loss = ((current_price - entry_price) / entry_price) * 100
            
            print(f"   ❗️觸發平倉條件: {symbol} (原因: {all_exit_reasons[0]})") # 這裡只顯示第一個主要原因
            
            trade_record = {
                **stock,
                "exit_date": datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d'),
                "exit_price": current_price,
                "profit_loss_percent": profit_loss,
                "exit_reasons": all_exit_reasons # 記錄所有觸發原因
            }
            trade_history.append(trade_record)
            stocks_to_close.append(stock)
        else:
            print(f"   ✅ {symbol} 未觸發平倉條件，繼續監控。")
            remaining_monitored_stocks.append(stock)

    if stocks_to_close:
        print(f"\n💾 正在更新檔案...")
        with open(MONITORED_STOCKS_PATH, 'w', encoding='utf-8') as f:
            json.dump(remaining_monitored_stocks, f, indent=2, ensure_ascii=False)
        print(f"   - {MONITORED_STOCKS_PATH} 已更新，移除了 {len(stocks_to_close)} 支股票。")
        
        with open(TRADE_HISTORY_PATH, 'w', encoding='utf-8') as f:
            json.dump(trade_history, f, indent=2, ensure_ascii=False)
        print(f"   - {TRADE_HISTORY_PATH} 已更新，新增了 {len(stocks_to_close)} 筆交易紀錄。")
    else:
        print("\nℹ️  本次檢查無任何股票觸發平倉條件。")

    print("\n✅ 投資組合管理任務完成！")

if __name__ == "__main__":
    run_portfolio_manager()
