import yfinance as yf
import pandas as pd
import numpy as np
from datetime import timedelta
import sys
import json

def run_aggressive_backtest(symbol, ma_period=200, delta_proxy=0.5):
    # 1. 準備數據
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="2y")
    if hist.empty:
        return {'error': 'No data'}
    hist.index = hist.index.tz_localize(None)
    
    # 動態策略信號
    # 邏輯：股價 < MA = 潛在低估 -> 啟動策略
    hist['MA_Trend'] = hist['Close'].rolling(ma_period).mean()
    
    trades = []
    capital = 10000
    total_pnl = 0
    
    # 每 30 天交易一次
    for i in range(200, len(hist)-30, 30):
        entry_date = hist.index[i]
        exit_date = hist.index[i+30]
        
        entry_price = hist['Close'].iloc[i]
        exit_price = hist['Close'].iloc[i+30]
        ma_trend = hist['MA_Trend'].iloc[i]
        
        # 策略選擇
        if entry_price < ma_trend:
            # 激進模式：根據 delta_proxy 設定 (0.5 = ATM)
            if delta_proxy >= 0.5:
                strike = entry_price # ATM
                credit = entry_price * 0.035 # ATM 權利金較高
                mode = "Aggressive (ATM)"
            else:
                strike = entry_price * 0.98 # Slightly OTM
                credit = entry_price * 0.02
                mode = f"Aggressive (Delta {delta_proxy})"
        else:
            # 保守模式：賣 1SD OTM Put (約 5% OTM)
            strike = entry_price * 0.95
            credit = entry_price * 0.01 # 權利金較少
            mode = "Conservative (OTM)"
            
        # 結算
        # 如果結算價 < Strike，虧損 = (Strike - 結算價) - 權利金
        # 如果結算價 > Strike，獲利 = 權利金
        
        if exit_price < strike:
            loss = (strike - exit_price) - credit
            pnl = -loss * 100 # 每口 100 股
            result = "LOSS"
        else:
            pnl = credit * 100
            result = "WIN"
            
        total_pnl += pnl
        trades.append({
            'date': entry_date.strftime('%Y-%m-%d'),
            'price': round(entry_price, 2),
            'mode': mode,
            'strike': round(strike, 2),
            'result': result,
            'pnl': round(pnl, 2)
        })
        
    # 統計
    df = pd.DataFrame(trades)
    win_rate = len(df[df['result']=='WIN']) / len(df) * 100
    
    return {
        'symbol': symbol,
        'total_trades': len(df),
        'win_rate': f"{win_rate:.1f}%",
        'total_pnl': f"${total_pnl:.0f}",
        'avg_pnl': f"${total_pnl/len(df):.0f}",
        'recent_trades': df.tail(3).to_dict('records')
    }

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    # 這裡確保只輸出 JSON
    # 為避免函數內的 print 干擾，我們可以暫時將 print 移除或重定向，但簡單起見我們假設函數只返回 dict
    # 修正 run_aggressive_backtest 裡的 print
    result = run_aggressive_backtest(target)
    print(json.dumps(result))
