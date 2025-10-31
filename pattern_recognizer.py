#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
經典技術分析圖形識別模組
"""
import pandas as pd
import numpy as np

class PatternRecognizer:
    def __init__(self, debug=False):
        self.debug = debug

    def find_local_extrema(self, series, window=5):
        """
        尋找局部高點和低點 (極值點)
        :param series: pandas Series (通常是'Low'或'High')
        :param window: 尋找極值的窗口大小
        :return: 包含極值點索引的Index
        """
        local_min = series.rolling(window=window, center=True).min()
        local_max = series.rolling(window=window, center=True).max()
        
        min_points = series[series == local_min].index
        max_points = series[series == local_max].index
        
        return min_points, max_points

    def detect_w_bottom(self, df, lookback=60, tolerance=0.03):
        """
        檢測W底（雙重底）模式
        :param df: 包含'Low', 'High', 'Close'的DataFrame
        :param lookback: 回溯期（天）
        :param tolerance: 兩個底部的價格容忍度（百分比）
        :return: 包含檢測結果的字典
        """
        if len(df) < lookback:
            return {'found': False}

        data = df.iloc[-lookback:]
        lows, highs = self.find_local_extrema(data['Low'], window=7)
        
        if len(lows) < 2:
            return {'found': False}

        # 尋找最近的兩個谷底 (b1, b2) 和它們之間的波峰 (p1)
        try:
            b2_date = lows[-1]
            p1_date = highs[highs > b2_date].min() # 找到b2之後的第一個高點是不對的, 應該是b1和b2之間的高點
            
            # 重新定位 p1_date, 必須在 b1 和 b2 之間
            b1_candidates = lows[lows < b2_date]
            if b1_candidates.empty: return {'found': False}
            b1_date = b1_candidates[-1]

            p1_candidates = highs[(highs > b1_date) & (highs < b2_date)]
            if p1_candidates.empty: return {'found': False}
            p1_date = p1_candidates[0]

        except (IndexError, ValueError):
            return {'found': False}

        b1_price = data.loc[b1_date, 'Low']
        b2_price = data.loc[b2_date, 'Low']
        p1_price = data.loc[p1_date, 'High'] # 頸線價格

        # 條件檢查
        # 1. 兩個底部的價格必須在容忍度範圍內
        if abs(b1_price - b2_price) / max(b1_price, b2_price) > tolerance:
            return {'found': False}

        # 2. 頸線必須顯著高於兩個底部
        if p1_price < max(b1_price, b2_price) * 1.05: # 至少高出5%
            return {'found': False}
            
        # 3. 時間間隔不能太短或太長
        time_delta = (b2_date - b1_date).days
        if not 10 < time_delta < (lookback * 0.8):
            return {'found': False}

        current_price = data['Close'].iloc[-1]
        
        # 判斷當前狀態：是正在形成，還是已經突破
        status = "forming"
        confirmed = False
        if current_price > p1_price:
            status = "confirmed_breakout"
            confirmed = True
        elif current_price > (p1_price * 0.98):
            status = "approaching_neckline"

        if self.debug:
            print(f"[W-Bottom Debug] b1: {b1_date.date()} (${b1_price:.2f}), p1: {p1_date.date()} (${p1_price:.2f}), b2: {b2_date.date()} (${b2_price:.2f}), status: {status}")

        return {
            'found': True,
            'status': status,
            'confirmed': confirmed,
            'neckline': p1_price,
            'bottom_price': (b1_price + b2_price) / 2,
            'days_between_bottoms': time_delta
        }

    def detect_rounding_bottom(self, df, lookback=40, slope_threshold=0.05):
        """
        檢測圓弧底模式
        特徵是下跌趨勢的斜率逐漸變緩，然後轉為上升
        :param df: DataFrame
        :param lookback: 回溯期
        :param slope_threshold: 斜率變化的閾值
        :return: 包含檢測結果的字典
        """
        if len(df) < lookback:
            return {'found': False}

        data = df.iloc[-lookback:]
        
        # 使用短期均線來平滑價格走勢
        ma = data['Close'].rolling(window=5).mean().dropna()
        if len(ma) < lookback // 2:
            return {'found': False}

        # 將時間序列分成兩半
        first_half = ma.iloc[:len(ma)//2]
        second_half = ma.iloc[len(ma)//2:]

        # 計算兩半的線性回歸斜率
        # 使用 np.polyfit(x, y, 1)[0] 來計算斜率
        x1 = np.arange(len(first_half))
        x2 = np.arange(len(second_half))
        
        # 處理數據點不足的情況
        if len(x1) < 2 or len(x2) < 2:
            return {'found': False}

        slope1 = np.polyfit(x1, first_half, 1)[0]
        slope2 = np.polyfit(x2, second_half, 1)[0]

        # 條件檢查
        # 1. 前半段必須是下降趨勢 (斜率為負)
        # 2. 後半段必須是上升趨勢 (斜率為正)
        # 3. 斜率變化必須足夠顯著
        if slope1 < 0 and slope2 > 0 and (slope2 - slope1) > slope_threshold:
            if self.debug:
                print(f"[Rounding Bottom Debug] Found: slope1={slope1:.4f}, slope2={slope2:.4f}")
            return {
                'found': True,
                'status': 'turning_up',
                'confirmed': slope2 > abs(slope1) * 0.5, # 上升斜率至少是下降斜率的一半
                'first_half_slope': slope1,
                'second_half_slope': slope2
            }
            
        return {'found': False}

    def detect_obv_divergence(self, df, lookback=30, tolerance=0.05):
        """
        檢測OBV看漲背離
        價格創新低，但OBV沒有創新低
        """
        if len(df) < lookback or 'OBV' not in df.columns:
            return {'found': False}

        data = df.iloc[-lookback:]
        
        lows, _ = self.find_local_extrema(data['Low'], window=5)
        if len(lows) < 2:
            return {'found': False}

        # 取最近的兩個價格低點
        b2_date = lows[-1]
        b1_candidates = lows[lows < b2_date]
        if b1_candidates.empty: return {'found': False}
        b1_date = b1_candidates[-1]

        b1_price = data.loc[b1_date, 'Low']
        b2_price = data.loc[b2_date, 'Low']

        # 條件1: 價格創了更低的低點 (或在容忍度內)
        if b2_price > b1_price * (1 + tolerance):
            return {'found': False}

        # 條件2: 對應的OBV形成了更高的低點
        b1_obv = data.loc[b1_date, 'OBV']
        b2_obv = data.loc[b2_date, 'OBV']

        if b2_obv > b1_obv:
            # 條件3: 背離發生在近期 (5個交易日內)
            if (data.index[-1] - b2_date).days < 5:
                if self.debug:
                    print(f"[OBV Divergence Debug] Found: Price {b1_price:.2f}->{b2_price:.2f}, OBV {b1_obv:.0f}->{b2_obv:.0f}")
                return {
                    'found': True,
                    'status': 'confirmed',
                    'confirmed': True,
                    'price_low_1': b1_price,
                    'price_low_2': b2_price,
                    'obv_low_1': b1_obv,
                    'obv_low_2': b2_obv
                }

        return {'found': False}

    def run_all_patterns(self, df):
        """
        運行所有圖形識別檢測
        :param df: DataFrame
        :return: 一個包含所有檢測結果的字典
        """
        patterns = {
            'w_bottom': self.detect_w_bottom(df),
            'rounding_bottom': self.detect_rounding_bottom(df),
            'obv_divergence': self.detect_obv_divergence(df)
        }

        # ===== 強制調試輸出 =====
        if self.debug and (patterns['w_bottom']['found'] or patterns['rounding_bottom']['found'] or patterns['obv_divergence']['found']):
             print(f"    [Recognizer DEBUG] Patterns found: {patterns}")
        # ===== 調試結束 =====
        
        # 計算一個綜合的圖形確認分數
        total_score = 0
        confirmed_patterns = []
        
        if patterns['w_bottom'].get('confirmed'):
            total_score += 50
            confirmed_patterns.append("W底突破頸線")
        elif patterns['w_bottom'].get('status') == 'approaching_neckline':
            total_score += 25
            confirmed_patterns.append("W底接近頸線")

        if patterns['rounding_bottom'].get('confirmed'):
            total_score += 30
            confirmed_patterns.append("圓弧底確認")
        elif patterns['rounding_bottom'].get('found'):
            total_score += 15
            confirmed_patterns.append("圓弧底形成中")
            
        if patterns['obv_divergence'].get('confirmed'):
            total_score += 40  # OBV背離是個很強的信號
            confirmed_patterns.append("OBV看漲背離")

        patterns['summary'] = {
            'score': min(total_score, 100),
            'confirmed_patterns': confirmed_patterns
        }
        
        return patterns
