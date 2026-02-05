import sys
import os
sys.path.append(os.getcwd())
from valuation_tool import get_historical_pe_valuation

targets = ['FXI', 'AAPL', 'DIS', 'F']

print("--- Fundamental Valuation Check ---")
for sym in targets:
    try:
        val = get_historical_pe_valuation(sym)
        if 'error' in val:
            print(f"{sym}: Error - {val['error']}")
            continue
            
        is_cheap = val.get('is_undervalued')
        discount = val.get('discount_pct')
        print(f"{sym}: P/E {val.get('current_pe')} (Avg {val.get('5y_avg_pe')}) | Discount: {discount}% | Signal: {'✅ UNDERVALUED' if is_cheap else '❌ OVERVALUED'}")
    except Exception as e:
        print(f"{sym}: Exception - {e}")
