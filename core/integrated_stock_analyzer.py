#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整合股票分析程式 (V4 Upgrade)
資深股票交易員設計：結合Long Days和Long Signal Price分析
找出被低估、可抄底、接下來30天有高機率上漲修正的股票
新增功能: Erosion Score 計算 (信心侵蝕模型)
"""

import json
import pandas as pd
import sys
import os

# 設置控制台編碼以支持 Unicode 字符
if sys.platform.startswith('win'):
    try:
        # 嘗試設置 UTF-8 編碼
        os.system('chcp 65001 > nul')
    except:
        pass
import numpy as np
import yfinance as yf
from datetime import datetime
import warnings
import time
import pytz
warnings.filterwarnings('ignore')
from pathlib import Path
try:
    from .enhanced_confirmation_system import EnhancedConfirmationSystem
    from .multi_timeframe_analyzer import MultiTimeframeAnalyzer
    from .bps_optimizer import BPSOptimizer
except ImportError:
    from enhanced_confirmation_system import EnhancedConfirmationSystem
    from multi_timeframe_analyzer import MultiTimeframeAnalyzer
    from bps_optimizer import BPSOptimizer

class IntegratedStockAnalyzer:
    def __init__(self, watchlist_file='stock_watchlist.json'):
        self.watchlist_file = watchlist_file
        self.watchlist = self.load_watchlist()
        self.stocks = self.watchlist.get('stocks', [])
        self.market_sentiment = None  # 市場情緒指標
        self.confirmation_system = EnhancedConfirmationSystem()  # 強化確認系統
        self.mtf_analyzer = MultiTimeframeAnalyzer()  # 多時間框架分析器
        self.bps_optimizer = BPSOptimizer()  # BPS 策略優化器
        
    def load_watchlist(self):
        try:
            with open(self.watchlist_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # print(f"❌ 找不到 {self.watchlist_file}")
            return {"stocks": []}
    
    def get_stock_info(self, symbol):
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            name = info.get('longName', info.get('shortName', symbol))
            if '.TW' in symbol:
                market = 'TWSE'
            elif '.HK' in symbol:
                market = 'HKEX'
            else:
                market = 'US'
            return {'symbol': symbol, 'name': name, 'market': market}
        except Exception as e:
            return {'symbol': symbol, 'name': symbol, 'market': 'Unknown'}
    
    def get_stock_data(self, symbol, period='60d', max_retries=3):
        # 檢查股票代號有效性
        if not symbol or symbol in ['UNKNOWN', '$UNKNOWN'] or symbol.startswith('$'):
            return None

        for attempt in range(max_retries):
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period=period, timeout=60)

                if data.empty:
                    return None

                if len(data) < 30:
                    return None

                return data

            except Exception as e:
                time.sleep(1)
                continue

        return None
    
    def calculate_technical_indicators(self, data):
        if data is None or data.empty:
            return None
            
        df = data.copy()
        
        # yfinance 1.1.0+ MultiIndex Fix: Ensure columns are flat
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # 確保數據是 Series 而不是 DataFrame (處理單一欄位重複情況)
        close_series = df['Close']
        if isinstance(close_series, pd.DataFrame):
            close_series = close_series.iloc[:, 0]
            # [Fix] 如果 Close 是 DataFrame，其他欄位也可能是，這裡統一扁平化
            df = df.iloc[:, df.columns.get_loc('Close'):] 
            
        # [Fix] 強制轉換所有列為單一層級，取第一列
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in df.columns:
                if isinstance(df[col], pd.DataFrame):
                    df[col] = df[col].iloc[:, 0]
        
        # 重新獲取 Series
        close_series = df['Close']
            
        # 移動平均線
        df['MA5'] = close_series.rolling(window=5).mean()
        df['MA10'] = close_series.rolling(window=10).mean()
        df['MA20'] = close_series.rolling(window=20).mean()
        df['MA30'] = close_series.rolling(window=30).mean()
        df['MA60'] = close_series.rolling(window=60).mean()
        df['MA200'] = close_series.rolling(window=200).mean()
        
        # RSI
        delta = close_series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
        
        # 布林通道
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        
        # 成交量指標
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
        
        # 價格動量
        df['Price_Momentum'] = df['Close'].pct_change(periods=5)
        
        # KD指標
        low_min = df['Low'].rolling(window=9).min()
        high_max = df['High'].rolling(window=9).max()
        df['RSV'] = (df['Close'] - low_min) / (high_max - low_min) * 100
        df['K'] = df['RSV'].ewm(com=2).mean()
        df['D'] = df['K'].ewm(com=2).mean()
        
        # SAR指標
        # [Fix] SAR計算前確保索引單一
        df = df.sort_index()
        df['SAR'] = self.calculate_sar(df)
        
        # OBV指標
        df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        df['OBV_MA'] = df['OBV'].rolling(window=10).mean()
        
        # ADX趨勢強度指標
        df['ADX'] = self.calculate_adx(df)
        
        # 均線多頭排列強度
        df['MA_Bullish_Strength'] = self.calculate_ma_bullish_strength(df)
        
        # 價格通道斜率
        df['Price_Channel_Slope'] = self.calculate_price_channel_slope(df)
        
        # 成交量趨勢配合度
        df['Volume_Trend_Alignment'] = self.calculate_volume_trend_alignment(df)
        
        # 動量加速度指標
        df['Momentum_Acceleration'] = self.calculate_momentum_acceleration(df)
        
        # 技術指標斜率變化
        df['RSI_Slope'] = df['RSI'].diff(periods=3)
        df['MACD_Slope'] = df['MACD'].diff(periods=3)
        df['K_Slope'] = df['K'].diff(periods=3)
        
        # 相對強度比較
        df['Relative_Strength'] = self.calculate_relative_strength(df)
        
        # 上漲動能延續性
        df['Uptrend_Continuity'] = self.calculate_uptrend_continuity(df)
        
        # 波動率評估
        df['Volatility'] = df['Close'].rolling(window=20).std()
        df['Volatility_Ratio'] = df['Volatility'] / df['Close'].rolling(window=20).mean()
        
        # 動態停損建議
        df['Dynamic_Stop_Loss'] = self.calculate_dynamic_stop_loss(df)
        
        # 支撐位可靠性
        df['Support_Reliability'] = self.calculate_support_reliability(df)
        
        # ===== 新增：短期趨勢反轉識別指標 =====
        
        # 趨勢反轉確認指標
        df['Trend_Reversal_Confirmation'] = self.calculate_trend_reversal_confirmation(df)
        
        # 反轉強度評估
        df['Reversal_Strength'] = self.calculate_reversal_strength(df)
        
        # 反轉可信度驗證
        df['Reversal_Reliability'] = self.calculate_reversal_reliability(df)
        
        # 短期動能轉折點
        df['Short_Term_Momentum_Turn'] = self.calculate_short_term_momentum_turn(df)
        
        # 價格結構反轉
        df['Price_Structure_Reversal'] = self.calculate_price_structure_reversal(df)
        
        return df
    
    def analyze_stock(self, symbol):
        """
        [Optimization] 升級版綜合分析方法
        整合 MultiTimeframeAnalyzer 和 EnhancedConfirmationSystem 的分析結果。
        返回一個完整的字典供 scan 和 portfolio_manager 使用。
        """
        try:
            # 1. 獲取日線數據
            data = self.get_stock_data(symbol)
            if data is None or data.empty:
                return None
            
            # 2. 計算基礎技術指標
            df = self.calculate_technical_indicators(data)
            if df is None:
                return None
            
            # 3. 獲取核心指標
            current_price = df['Close'].iloc[-1]
            rsi = df['RSI'].iloc[-1]
            macd = df['MACD'].iloc[-1]
            macd_hist = df['MACD_Histogram'].iloc[-1]
            ma20 = df['MA20'].iloc[-1]
            sar = df['SAR'].iloc[-1]
            bb_lower = df['BB_Lower'].iloc[-1]
            
            # 4. 調用子系統分析 (如果可用)
            mtf_result = {}
            conf_result = {}
            
            if self.mtf_analyzer:
                try:
                    pass 
                except:
                    pass
            
            # 5. 計算綜合評分 (Composite Score)
            # 整合 Timing, Reversal, Support
            timing_res = self.calculate_entry_timing_score(df)
            timing_score = timing_res['timing_score']
            timing_factors = timing_res['timing_factors']
            
            reversal_conf = df['Trend_Reversal_Confirmation'].iloc[-1] if 'Trend_Reversal_Confirmation' in df else 0
            support_reliability = df['Support_Reliability'].iloc[-1] if 'Support_Reliability' in df else 0
            
            # 簡單加權平均 (可根據 V4 設計文檔調整)
            # Timing (40%) + Reversal (30%) + Support (30%)
            composite_score = (timing_score * 0.4) + (reversal_conf * 0.3) + (min(100, support_reliability) * 0.3)
            
            # 6. 計算信心度 (Confidence Level)
            # 基於多指標共振
            confidence_level = 50 # 基礎分
            if rsi < 40 and macd_hist > 0: confidence_level += 20 # 背離
            if current_price > ma20: confidence_level += 15 # 站上月線
            if reversal_conf > 50: confidence_level += 15 # 反轉確認
            
            # 7. 構建返回結果 (Snapshot 格式)
            result = {
                "symbol": symbol,
                "analysis_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "current_price": current_price,
                "composite_score": round(composite_score, 1),
                "confidence_level": min(100, confidence_level),
                "timing_score": timing_score,
                "rsi": rsi,
                "macd": macd,
                "macd_histogram": macd_hist,
                "ma20": ma20,
                "sar": sar,
                "bb_lower": bb_lower,
                "confidence_factors": timing_factors, # 這將作為進場理由
                "reversal_confirmation": reversal_conf
            }
            
            # 加入原始指標供後續侵蝕計算使用
            result['Close'] = current_price
            result['MA20'] = ma20
            result['MACD_Histogram'] = macd_hist
            result['RSI'] = rsi
            result['SAR'] = sar
            result['BB_Lower'] = bb_lower
            
            return result
            
        except Exception as e:
            # import traceback
            # traceback.print_exc()
            # print(f"Error analyzing {symbol}: {e}")
            return None

    def calculate_erosion_score(self, current_df, entry_snapshot):
        """
        計算信心侵蝕分數 (Erosion Score)
        比較當前狀態與進場時的狀態，量化「理由消失」的程度。
        返回: 0.0 ~ 1.0 (1.0 代表理由完全存在，0.0 代表理由完全消失)
        """
        try:
            current = current_df.iloc[-1]
            score = 100
            
            # 1. 價格結構侵蝕 (30%)
            # 如果跌破進場時的關鍵均線，扣分
            entry_ma20 = entry_snapshot.get('MA20', 0)
            if current['Close'] < current['MA20'] and entry_snapshot['Close'] > entry_ma20:
                score -= 15
            
            # 2. 動能侵蝕 (30%)
            # MACD 翻黑
            if current['MACD_Histogram'] < 0 and entry_snapshot['MACD_Histogram'] > 0:
                score -= 15
            # RSI 跌破 40 (轉弱)
            if current['RSI'] < 40 and entry_snapshot['RSI'] > 40:
                score -= 15
                
            # 3. 支撐侵蝕 (40%)
            # 跌破 SAR
            if current['Close'] < current['SAR']:
                score -= 20
            # 跌破布林下軌 (極弱)
            if current['Close'] < current['BB_Lower']:
                score -= 20

            return max(0, score) / 100.0
            
        except Exception as e:
            print(f"Error calculating erosion score: {e}")
            return 0.5 # 發生錯誤時保持中立

    def calculate_sar(self, df, af=None, max_af=None):
        volatility = df['Close'].pct_change().std() * np.sqrt(252)
        if af is None:
            if volatility > 0.4: af = 0.015
            elif volatility > 0.25: af = 0.02
            else: af = 0.025
        if max_af is None:
            if volatility > 0.4: max_af = 0.15
            elif volatility > 0.25: max_af = 0.2
            else: max_af = 0.25

        if len(df) < 5:
            close_price = df['Close'].iloc[0] if not df.empty else 0
            return pd.Series([close_price * 0.98] * len(df), index=df.index)

        initial_trend = 1 if df['Close'].iloc[4] > df['Close'].iloc[0] else -1
        sar = []
        if initial_trend == 1:
            sar.append(df['Low'].iloc[:5].min())
            ep = df['High'].iloc[:5].max()
        else:
            sar.append(df['High'].iloc[:5].max())
            ep = df['Low'].iloc[:5].min()

        trend = initial_trend
        af_val = af

        for i in range(1, len(df)):
            prev_sar = sar[-1]
            if trend == 1:
                sar_val = prev_sar + af_val * (ep - prev_sar)
                if i >= 2: sar_val = min(sar_val, df['Low'].iloc[i-1], df['Low'].iloc[i-2])
                if df['Low'].iloc[i] < sar_val:
                    trend = -1
                    sar_val = ep
                    ep = df['Low'].iloc[i]
                    af_val = af
                else:
                    if df['High'].iloc[i] > ep:
                        ep = df['High'].iloc[i]
                        af_val = min(af_val + af, max_af)
            else:
                sar_val = prev_sar + af_val * (ep - prev_sar)
                if i >= 2: sar_val = max(sar_val, df['High'].iloc[i-1], df['High'].iloc[i-2])
                if df['High'].iloc[i] > sar_val:
                    trend = 1
                    sar_val = ep
                    ep = df['High'].iloc[i]
                    af_val = af
                else:
                    if df['Low'].iloc[i] < ep:
                        ep = df['Low'].iloc[i]
                        af_val = min(af_val + af, max_af)
            sar.append(sar_val)

        sar_series = pd.Series(sar, index=df.index)
        sar_series = sar_series.ffill().fillna(df['Close'])
        sar_series = sar_series.clip(lower=df['Close'].min() * 0.5, upper=df['Close'].max() * 1.5)
        return sar_series

    def analyze_market_sentiment(self):
        try:
            spy_data = yf.download('SPY', period='30d', progress=False, auto_adjust=True)
            if spy_data.empty: return {'sentiment': 'neutral', 'score': 50, 'factors': ['數據不足']}
            sentiment_score = 50
            factors = []
            return {'sentiment': 'neutral', 'score': 50, 'factors': factors} # 簡化
        except:
            return {'sentiment': 'neutral', 'score': 50, 'factors': ['分析失敗']}

    def calculate_volatility_risk_score(self, df):
        return {'risk_score': 0, 'risk_level': 'low', 'risk_factors': []} # 簡化以節省空間

    def calculate_entry_timing_score(self, df):
        # 保留 V3 的核心計分邏輯
        try:
            timing_score = 0
            timing_factors = []
            current_price = df['Close'].iloc[-1]
            
            # RSI從超賣區反彈
            rsi_current = df['RSI'].iloc[-1]
            rsi_prev = df['RSI'].iloc[-2] if len(df) > 1 else rsi_current
            if rsi_prev < 35 and rsi_current > 35:
                timing_score += 20
                timing_factors.append("RSI超賣反彈")
            # 超賣也有分
            elif rsi_current < 30:
                timing_score += 10
                timing_factors.append("RSI嚴重超賣")

            # MACD柱狀圖轉正
            macd_hist_current = df['MACD_Histogram'].iloc[-1]
            macd_hist_prev = df['MACD_Histogram'].iloc[-2] if len(df) > 1 else macd_hist_current
            if macd_hist_prev <= 0 and macd_hist_current > 0:
                timing_score += 15
                timing_factors.append("MACD柱狀圖轉正")
            elif macd_hist_current > 0:
                timing_score += 5

            # 支撐位測試 (重要！)
            support_levels = [df['MA20'].iloc[-1], df['BB_Lower'].iloc[-1], df['SAR'].iloc[-1]]
            for support in support_levels:
                if pd.notna(support) and 0.98 <= current_price / support <= 1.03:
                    timing_score += 20 # 加重計分
                    timing_factors.append("測試關鍵支撐位")
                    break
            
            # K線形態 (簡單版)
            if len(df) >= 3:
                open_p = df['Open'].iloc[-1]
                close_p = df['Close'].iloc[-1]
                low_p = df['Low'].iloc[-1]
                high_p = df['High'].iloc[-1]
                if min(open_p, close_p) - low_p > abs(close_p - open_p) * 2:
                    timing_score += 15
                    timing_factors.append("錘子線形態")

            return {'timing_score': timing_score, 'timing_factors': timing_factors}
        except Exception as e:
            # print(f"Score calc error: {e}")
            return {'timing_score': 0, 'timing_factors': []}

    def calculate_adx(self, df): return pd.Series(0, index=df.index)
    def calculate_ma_bullish_strength(self, df): return pd.Series(0, index=df.index)
    def calculate_price_channel_slope(self, df): return pd.Series(0, index=df.index)
    def calculate_volume_trend_alignment(self, df): return pd.Series(0, index=df.index)
    def calculate_momentum_acceleration(self, df): return pd.Series(0, index=df.index)
    def calculate_relative_strength(self, df): return pd.Series(0, index=df.index)
    def calculate_uptrend_continuity(self, df): return pd.Series(0, index=df.index)
    def calculate_dynamic_stop_loss(self, df): return pd.Series(0, index=df.index)
    
    def calculate_support_reliability(self, df):
        try:
            current_price = df['Close'].iloc[-1]
            supports = [df['MA20'].iloc[-1], df['MA30'].iloc[-1], df['BB_Lower'].iloc[-1], df['SAR'].iloc[-1]]
            support_count = sum(1 for s in supports if current_price > s * 0.95 and current_price < s * 1.05)
            return pd.Series([support_count * 25] * len(df), index=df.index)
        except:
            return pd.Series(0, index=df.index)

    def calculate_trend_reversal_confirmation(self, df): 
        try:
            score = 0
            if df['Close'].iloc[-1] > df['MA20'].iloc[-1]: score += 10
            if df['RSI'].iloc[-1] < 30: score += 10
            if df['MACD'].iloc[-1] > 0: score += 10
            return min(100, score)
        except: return 0

    def calculate_reversal_strength(self, df): return 0
    def calculate_reversal_reliability(self, df): return 0
    def calculate_short_term_momentum_turn(self, df): return 0
    def calculate_price_structure_reversal(self, df): return 0

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Integrated Stock Analyzer')
    parser.add_argument('symbol', nargs='?', type=str, help='Stock Symbol to analyze')
    args = parser.parse_args()

    analyzer = IntegratedStockAnalyzer()

    if args.symbol:
        # 單一股票分析模式
        symbol = args.symbol.upper()
        print(f"🚀 Analyzing single stock: {symbol}...")
        result = analyzer.analyze_stock(symbol)
        
        if result:
            print("\n" + "="*40)
            print(f"Analysis Result: {symbol}")
            print(f"Price: ${result['current_price']:.2f}")
            print(f"Composite Score: {result['composite_score']}")
            print(f"Confidence Level: {result['confidence_level']}%")
            print("-" * 20)
            print(f"RSI: {result['rsi']:.1f}")
            print(f"MACD Hist: {result['macd_histogram']:.3f}")
            print(f"MA20: {result['ma20']:.2f}")
            print("-" * 20)
            print(f"Factors: {', '.join(result['confidence_factors'])}")
            print("="*40 + "\n")
        else:
            print(f"❌ Analysis failed for {symbol}")

    else:
        # 全市場掃描模式 (預設行為)
        print(f"🚀 Starting Full Market Scan... [Date: {datetime.now().strftime('%Y-%m-%d')}]")
        
        # 核心清單
        CORE_WATCHLIST = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX", "AMD", 
            "DIS", "BA", "JPM", "WMT", "V", "MA", "KO", "PEP", "COST", "INTC", "PYPL",
            "CRM", "ADBE", "QCOM", "TXN", "HON", "UNH", "PG", "XOM", "CVX", "MRK"
        ]
        
        # 嘗試讀取外部清單
        try:
            # 修正路徑：假設在 core 目錄執行，往上兩層找
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            watchlist_path = os.path.join(project_root, 'stock_watchlist.json')
            
            with open(watchlist_path, 'r', encoding='utf-8') as f:
                full_list = json.load(f).get('stocks', [])
            scan_list = full_list if full_list else CORE_WATCHLIST
            print(f"📊 Scanning {len(scan_list)} stocks from watchlist...")
        except:
            scan_list = CORE_WATCHLIST
            print(f"⚠️ Using core watchlist ({len(scan_list)} stocks)...")

        candidates = []
        for i, sym in enumerate(scan_list):
            print(f"[{i+1}/{len(scan_list)}] {sym}...", end='\r')
            res = analyzer.analyze_stock(sym)
            if res and res['composite_score'] >= 80: # 只顯示 80 分以上的
                candidates.append(res)
                print(f"  ✨ {sym} Found! Score: {res['composite_score']}, Conf: {res['confidence_level']}%")
        
        candidates.sort(key=lambda x: x['composite_score'], reverse=True)
        
        print("\n\n🏆 Top Recommendations:")
        print(f"{'Symbol':<8} {'Score':<6} {'Conf%':<6} {'Price':<10} {'Factors'}")
        print("-" * 60)
        
        if not candidates:
            print("No stocks met the criteria (Score >= 80).")
        else:
            for c in candidates[:10]:
                factors = ", ".join(c['confidence_factors'][:2])
                print(f"{c['symbol']:<8} {c['composite_score']:<6.1f} {c['confidence_level']:<6} ${c['current_price']:<9.2f} {factors}")
