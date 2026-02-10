#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bull Put Spread (BPS) 策略優化器 (V4 Upgrade)
專門針對選擇權交易設計，計算最佳點位與風險評估
新增功能: IV Rank 計算與過濾
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

class BPSOptimizer:
    def __init__(self):
        self.tz = pytz.timezone('Asia/Taipei')

    def get_iv_rank(self, symbol, period='1y'):
        """
        [V4 Upgrade] 計算 IV Rank (隱含波動率等級)
        由於免費 API 難以獲取真實 IV，我們使用 HV (歷史波動率) 作為 IV 的代理指標。
        IV Rank = (Current IV - Low IV) / (High IV - Low IV) * 100
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            if hist.empty: return 50 # 默認中性
            
            # 計算 Rolling Volatility (20日)
            returns = hist['Close'].pct_change().dropna()
            rolling_vol = returns.rolling(window=20).std() * np.sqrt(252)
            
            if rolling_vol.empty: return 50
            
            current_vol = rolling_vol.iloc[-1]
            min_vol = rolling_vol.min()
            max_vol = rolling_vol.max()
            
            if max_vol == min_vol: return 50
            
            iv_rank = (current_vol - min_vol) / (max_vol - min_vol) * 100
            return round(iv_rank, 2)
        except Exception as e:
            # print(f"Error calculating IV Rank for {symbol}: {e}")
            return 50

    def get_expected_move(self, symbol, days_to_expiry=30):
        """
        計算預期漲跌幅 (Expected Move)
        公式: Price * IV * sqrt(T/365)
        """
        try:
            ticker = yf.Ticker(symbol)
            # 獲取當前價格 (優先使用 fast_info)
            try:
                current_price = ticker.fast_info['last_price']
            except:
                hist = ticker.history(period='1d')
                if hist.empty: return None
                current_price = hist['Close'].iloc[-1]
            
            # 獲取歷史數據計算波動率
            hist = ticker.history(period='1y')
            returns = hist['Close'].pct_change().dropna()
            annual_vol = returns.std() * np.sqrt(252)
            
            # 預期漲跌幅 (1 標準差)
            expected_move = current_price * annual_vol * np.sqrt(days_to_expiry / 365)
            
            return {
                'current_price': current_price,
                'annual_vol': annual_vol,
                'expected_move': expected_move,
                'lower_1sd': current_price - expected_move,
                'upper_1sd': current_price + expected_move
            }
        except Exception as e:
            # print(f"Error calculating expected move for {symbol}: {e}")
            return None

    def suggest_bps_strikes(self, symbol, days_to_expiry=30):
        """
        建議 BPS 的進場點位 (Short Put & Long Put)
        [V4 Upgrade] 加入 IV Rank 檢查
        """
        em_data = self.get_expected_move(symbol, days_to_expiry)
        if not em_data:
            return None
        
        current_price = em_data['current_price']
        lower_1sd = em_data['lower_1sd']
        
        # 建議 Short Put 點位在 1SD 之外
        short_put_strike = floor_to_half(lower_1sd)
        long_put_strike = short_put_strike - 5 # 假設 5 點價差
        
        # 計算 IV Rank
        iv_rank = self.get_iv_rank(symbol)
        
        # V4 濾網：如果 IV Rank < 20 (過度平靜)，建議觀望
        recommendation = "BUY"
        if iv_rank < 20:
            recommendation = "WAIT (Low IV)"
        elif iv_rank > 80:
            recommendation = "STRONG BUY (High IV)"

        # 計算建議到期日 (約 30-45 天後最近的週五)
        expiry_date = (datetime.now() + timedelta(days=days_to_expiry)).strftime('%Y-%m-%d')

        return {
            'symbol': symbol,
            'current_price': round(current_price, 2),
            'short_put_strike': short_put_strike,
            'long_put_strike': long_put_strike,
            'suggested_expiry': expiry_date,
            'safety_margin_pct': round((current_price - short_put_strike) / current_price * 100, 2),
            'expected_move_1sd': round(em_data['expected_move'], 2),
            'iv_rank': iv_rank,
            'recommendation': recommendation
        }

    def check_earnings_risk(self, symbol):
        """
        檢查近期是否有財報風險 (如微軟事件)
        """
        try:
            ticker = yf.Ticker(symbol)
            calendar = ticker.calendar
            if calendar is not None and not calendar.empty:
                # yfinance calendar 格式可能不同，做兼容處理
                if isinstance(calendar, dict):
                     earnings_date = calendar.get('Earnings Date', [None])[0]
                else:
                     earnings_date = calendar.iloc[0, 0]
                     
                if isinstance(earnings_date, datetime):
                    # 轉換為無時區或本地時區比較
                    earnings_date = earnings_date.replace(tzinfo=None)
                    days_to_earnings = (earnings_date - datetime.now()).days
                    return {
                        'earnings_date': earnings_date.strftime('%Y-%m-%d'),
                        'days_to_earnings': days_to_earnings,
                        'high_risk': 0 <= days_to_earnings < 14 # 兩週內有財報
                    }
            return {'high_risk': False, 'note': '無財報資訊'}
        except:
            return {'high_risk': False, 'note': '無法獲取財報資訊'}

def floor_to_half(val):
    return np.floor(val * 2) / 2

if __name__ == "__main__":
    optimizer = BPSOptimizer()
    # 測試
    print(optimizer.suggest_bps_strikes("TSLA"))
