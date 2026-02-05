import json
import os

def calculate_kelly_size(win_rate, win_loss_ratio, fraction=0.5):
    """
    凱利公式計算最佳倉位比例
    :param win_rate: 勝率 (0.0 - 1.0)
    :param win_loss_ratio: 平均獲利 / 平均虧損
    :param fraction: 凱利比例 (通常取 0.5 即 'Half-Kelly' 以求穩健)
    :return: 建議投入資金比例
    """
    if win_loss_ratio <= 0:
        return 0
    
    # Kelly % = W - [(1 - W) / R]
    # W = Win Probability, R = Win/Loss Ratio
    kelly_pct = win_rate - ((1 - win_rate) / win_loss_ratio)
    
    # 應用分注 (Fractional Kelly) 並確保不為負數
    suggested_pct = max(0, kelly_pct * fraction)
    return round(suggested_pct, 4)

def get_sizing_recommendation(symbol, total_capital=10000):
    # 根據我們之前的回測數據 (AAPL 為例)
    # 勝率: 86%, 平均獲利 $49, 最大虧損 (價差寬度 $500 - 獲利)
    # 這裡簡化模擬數據
    stats = {
        'AAPL': {'win_rate': 0.86, 'r_ratio': 0.25}, # R較低因為是賣方策略，賺小賠大
        'AMZN': {'win_rate': 0.82, 'r_ratio': 0.28},
        'DIS': {'win_rate': 0.75, 'r_ratio': 0.35},
        'default': {'win_rate': 0.80, 'r_ratio': 0.25}
    }
    
    s = stats.get(symbol, stats['default'])
    pct = calculate_kelly_size(s['win_rate'], s['r_ratio'])
    
    allocation = total_capital * pct
    
    return {
        'symbol': symbol,
        'kelly_fraction': pct,
        'suggested_allocation': round(allocation, 2),
        'note': f"基於 {s['win_rate']*100}% 勝率計算 (Half-Kelly)"
    }

if __name__ == "__main__":
    print("--- 凱利公式資金管理建議 (假設總資金 $10,000) ---")
    for sym in ['AAPL', 'AMZN', 'DIS']:
        res = get_sizing_recommendation(sym)
        print(f"{sym}: 建議投入 {res['kelly_fraction']*100:.2f}% (${res['suggested_allocation']})")
