import json
import os
import sys

# Setup path
sys.path.append(os.path.join(os.getcwd(), "BullPS-v3"))

from core.integrated_stock_analyzer import IntegratedStockAnalyzer

analyzer = IntegratedStockAnalyzer()
for symbol in ['XRT', 'XLF', 'SIRI']:
    print(f"--- {symbol} ---")
    analysis = analyzer.analyze_stock(symbol)
    print("Confidence Factors:", analysis.get('confidence_factors', []))
    print("Signal Conditions:", analysis.get('signal_conditions', []))
