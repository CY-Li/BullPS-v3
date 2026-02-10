import sys
import os
import json
from pathlib import Path

# 加入路徑
project_root = "/home/jimmy161688/.openclaw/workspace/BullPS-v3"
core_dir = os.path.join(project_root, "core")
sys.path.append(project_root)
sys.path.append(core_dir)

from integrated_stock_analyzer import IntegratedStockAnalyzer

analyzer = IntegratedStockAnalyzer()
symbol = 'AMZN'
print(f"Testing {symbol}...")
data = analyzer.get_stock_data(symbol)
if data is None:
    print("Data is None")
else:
    print(f"Data length: {len(data)}")
    df = analyzer.calculate_technical_indicators(data)
    if df is None:
        print("DF is None")
    else:
        res = analyzer.analyze_stock(symbol)
        print(f"Result: {res}")
