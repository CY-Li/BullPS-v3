#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
診斷綜合評分為 NaN 的原因
檢查可能導致 NaN 值的各種情況
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path

def analyze_nan_causes():
    """分析可能導致 NaN 的原因"""
    print("🔍 診斷綜合評分 NaN 問題")
    print("=" * 60)
    
    # 模擬可能導致 NaN 的情況
    test_cases = []
    
    # 情況 1: long_days 為 None 或 NaN
    print("\n📊 測試情況 1: long_days 問題")
    test_data_1 = pd.DataFrame({
        'symbol': ['TEST1', 'TEST2', 'TEST3'],
        'long_days': [None, np.nan, 5],
        'distance_to_signal': [10, 15, 20],
        'entry_opportunity': ['建議進場', '觀望', '強烈推薦進場'],
        'confidence_score': [75, 80, 85]
    })
    
    result_1 = test_composite_score_calculation(test_data_1, "long_days 問題")
    test_cases.append(("long_days 問題", result_1))
    
    # 情況 2: distance_to_signal 為 None 或 NaN
    print("\n📊 測試情況 2: distance_to_signal 問題")
    test_data_2 = pd.DataFrame({
        'symbol': ['TEST1', 'TEST2', 'TEST3'],
        'long_days': [3, 5, 7],
        'distance_to_signal': [None, np.nan, 20],
        'entry_opportunity': ['建議進場', '觀望', '強烈推薦進場'],
        'confidence_score': [75, 80, 85]
    })
    
    result_2 = test_composite_score_calculation(test_data_2, "distance_to_signal 問題")
    test_cases.append(("distance_to_signal 問題", result_2))
    
    # 情況 3: entry_opportunity 無法映射
    print("\n📊 測試情況 3: entry_opportunity 映射問題")
    test_data_3 = pd.DataFrame({
        'symbol': ['TEST1', 'TEST2', 'TEST3'],
        'long_days': [3, 5, 7],
        'distance_to_signal': [10, 15, 20],
        'entry_opportunity': ['未知建議', None, '強烈推薦進場'],
        'confidence_score': [75, 80, 85]
    })
    
    result_3 = test_composite_score_calculation(test_data_3, "entry_opportunity 映射問題")
    test_cases.append(("entry_opportunity 映射問題", result_3))
    
    # 情況 4: confidence_score 為 None 或 NaN
    print("\n📊 測試情況 4: confidence_score 問題")
    test_data_4 = pd.DataFrame({
        'symbol': ['TEST1', 'TEST2', 'TEST3'],
        'long_days': [3, 5, 7],
        'distance_to_signal': [10, 15, 20],
        'entry_opportunity': ['建議進場', '觀望', '強烈推薦進場'],
        'confidence_score': [None, np.nan, 85]
    })
    
    result_4 = test_composite_score_calculation(test_data_4, "confidence_score 問題")
    test_cases.append(("confidence_score 問題", result_4))
    
    # 情況 5: 所有 long_days 相同（導致 max_days - long_days = 0）
    print("\n📊 測試情況 5: 所有 long_days 相同")
    test_data_5 = pd.DataFrame({
        'symbol': ['TEST1', 'TEST2', 'TEST3'],
        'long_days': [5, 5, 5],  # 所有值相同
        'distance_to_signal': [10, 15, 20],
        'entry_opportunity': ['建議進場', '觀望', '強烈推薦進場'],
        'confidence_score': [75, 80, 85]
    })
    
    result_5 = test_composite_score_calculation(test_data_5, "所有 long_days 相同")
    test_cases.append(("所有 long_days 相同", result_5))
    
    # 情況 6: 極端的 distance_to_signal 值
    print("\n📊 測試情況 6: 極端 distance_to_signal 值")
    test_data_6 = pd.DataFrame({
        'symbol': ['TEST1', 'TEST2', 'TEST3'],
        'long_days': [3, 5, 7],
        'distance_to_signal': [np.inf, -np.inf, 20],
        'entry_opportunity': ['建議進場', '觀望', '強烈推薦進場'],
        'confidence_score': [75, 80, 85]
    })
    
    result_6 = test_composite_score_calculation(test_data_6, "極端 distance_to_signal 值")
    test_cases.append(("極端 distance_to_signal 值", result_6))
    
    # 總結報告
    print("\n" + "=" * 60)
    print("診斷結果總結")
    print("=" * 60)
    
    for case_name, result in test_cases:
        has_nan = result['has_nan']
        nan_count = result['nan_count']
        total_count = result['total_count']
        
        if has_nan:
            print(f"❌ {case_name}: 發現 {nan_count}/{total_count} 個 NaN 值")
            print(f"   原因: {result['cause']}")
        else:
            print(f"✅ {case_name}: 無 NaN 值")
    
    # 提供解決方案
    print("\n" + "=" * 60)
    print("解決方案建議")
    print("=" * 60)
    
    solutions = [
        "1. 檢查 long_days 計算: 確保信號檢測正常",
        "2. 檢查 distance_to_signal 計算: 確保價格數據有效",
        "3. 檢查 entry_opportunity 映射: 確保所有可能值都有對應分數",
        "4. 檢查 confidence_score 計算: 確保評分函數返回有效數值",
        "5. 處理邊界情況: 當所有 long_days 相同時的除零問題",
        "6. 添加 NaN 檢查: 在計算前檢查並處理 NaN 值"
    ]
    
    for solution in solutions:
        print(f"  {solution}")

def test_composite_score_calculation(df, test_name):
    """測試綜合評分計算"""
    print(f"  測試: {test_name}")
    
    try:
        # 模擬原始計算邏輯
        signal_stocks = df[df['long_days'].notna()].copy()
        
        if signal_stocks.empty:
            print("    ⚠️  沒有有效的信號股票")
            return {
                'has_nan': False,
                'nan_count': 0,
                'total_count': len(df),
                'cause': '沒有有效信號股票'
            }
        
        # Long Days評分
        max_days = signal_stocks['long_days'].max()
        print(f"    max_days: {max_days}")
        
        if max_days == 0 or pd.isna(max_days):
            print("    ❌ max_days 為 0 或 NaN")
            return {
                'has_nan': True,
                'nan_count': len(signal_stocks),
                'total_count': len(df),
                'cause': 'max_days 為 0 或 NaN，導致除零錯誤'
            }
        
        signal_stocks['long_days_score'] = (max_days - signal_stocks['long_days']) / max_days * 100
        
        # 距離評分
        signal_stocks['distance_score'] = np.maximum(0, 100 - signal_stocks['distance_to_signal'])
        
        # 進場建議評分
        entry_scores = {
            '強烈推薦進場': 100,
            '建議進場': 80,
            '觀望': 50,
            '不建議進場': 20
        }
        signal_stocks['entry_score'] = signal_stocks['entry_opportunity'].map(entry_scores)
        
        # 綜合評分
        signal_stocks['composite_score'] = (
            signal_stocks['long_days_score'] * 0.3 +
            signal_stocks['distance_score'] * 0.3 +
            signal_stocks['entry_score'] * 0.2 +
            signal_stocks['confidence_score'] * 0.2
        )
        
        # 檢查 NaN
        nan_mask = signal_stocks['composite_score'].isna()
        nan_count = nan_mask.sum()
        
        if nan_count > 0:
            print(f"    ❌ 發現 {nan_count} 個 NaN 值")
            
            # 詳細分析每個組件
            for idx in signal_stocks[nan_mask].index:
                row = signal_stocks.loc[idx]
                print(f"      {row['symbol']}:")
                print(f"        long_days_score: {row['long_days_score']}")
                print(f"        distance_score: {row['distance_score']}")
                print(f"        entry_score: {row['entry_score']}")
                print(f"        confidence_score: {row['confidence_score']}")
            
            # 找出原因
            causes = []
            if signal_stocks['long_days_score'].isna().any():
                causes.append("long_days_score 有 NaN")
            if signal_stocks['distance_score'].isna().any():
                causes.append("distance_score 有 NaN")
            if signal_stocks['entry_score'].isna().any():
                causes.append("entry_score 有 NaN")
            if signal_stocks['confidence_score'].isna().any():
                causes.append("confidence_score 有 NaN")
            
            cause = "; ".join(causes) if causes else "未知原因"
        else:
            print(f"    ✅ 無 NaN 值")
            cause = "無問題"
        
        return {
            'has_nan': nan_count > 0,
            'nan_count': nan_count,
            'total_count': len(signal_stocks),
            'cause': cause
        }
        
    except Exception as e:
        print(f"    ❌ 計算錯誤: {e}")
        return {
            'has_nan': True,
            'nan_count': len(df),
            'total_count': len(df),
            'cause': f"計算異常: {str(e)}"
        }

def check_real_data():
    """檢查實際數據"""
    print("\n🔍 檢查實際分析結果數據")
    print("=" * 60)
    
    analysis_file = Path("analysis_result.json")
    if analysis_file.exists():
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'result' in data and data['result']:
                df = pd.DataFrame(data['result'])
                
                print(f"總股票數: {len(df)}")
                
                # 檢查各個字段的 NaN 情況
                fields_to_check = ['composite_score', 'confidence_score', 'long_days', 'distance_to_signal']
                
                for field in fields_to_check:
                    if field in df.columns:
                        nan_count = df[field].isna().sum()
                        total_count = len(df)
                        print(f"{field}: {nan_count}/{total_count} 個 NaN 值")
                        
                        if nan_count > 0:
                            nan_symbols = df[df[field].isna()]['symbol'].tolist()
                            print(f"  NaN 的股票: {nan_symbols[:5]}{'...' if len(nan_symbols) > 5 else ''}")
                    else:
                        print(f"{field}: 字段不存在")
                
            else:
                print("分析結果為空")
                
        except Exception as e:
            print(f"讀取分析結果失敗: {e}")
    else:
        print("analysis_result.json 不存在")

if __name__ == "__main__":
    analyze_nan_causes()
    check_real_data()
