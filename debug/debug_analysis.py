
import sys
import os
import json
import numpy as np

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.floating)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return super(NpEncoder, self).default(obj)

# 加入路徑
project_root = '/home/jimmy161688/.openclaw/workspace/BullPS-v3'
core_dir = os.path.join(project_root, "core")
if project_root not in sys.path: sys.path.append(project_root)
if core_dir not in sys.path: sys.path.append(core_dir)

from core.integrated_stock_analyzer import IntegratedStockAnalyzer

analyzer = IntegratedStockAnalyzer()
analysis = analyzer.analyze_stock('DIS')
print(json.dumps(analysis, indent=2, ensure_ascii=False, cls=NpEncoder))
