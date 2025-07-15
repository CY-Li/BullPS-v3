#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
驗證整個專案的路徑一致性
確保所有組件都使用相同的數據文件路徑
"""

import os
import sys
from pathlib import Path

def test_path_manager():
    """測試路徑管理器的統一路徑"""
    print("🔧 測試路徑管理器")
    print("-" * 40)
    
    try:
        from backend.path_manager import path_manager
        
        info = path_manager.get_info()
        print(f"環境: {info['environment']}")
        print(f"數據目錄: {path_manager.data_dir}")
        print()
        
        print("統一路徑:")
        paths = {}
        for name, path in info['paths'].items():
            paths[name] = str(path)
            exists = info['file_exists'][name]
            size = info['file_sizes'][name]
            status = f"✅ {size} bytes" if exists and size > 0 else "❌ 不存在或為空"
            print(f"  {name}: {path} - {status}")
        
        return True, paths
        
    except Exception as e:
        print(f"❌ 路徑管理器測試失敗: {e}")
        return False, {}

def test_backend_main():
    """測試後端主程式的路徑配置"""
    print("\n🌐 測試後端 API 路徑")
    print("-" * 40)
    
    try:
        # 模擬後端主程式的路徑邏輯
        sys.path.insert(0, str(Path(__file__).parent))
        
        from backend.path_manager import path_manager
        ANALYSIS_PATH = path_manager.get_analysis_path()
        MONITORED_STOCKS_PATH = path_manager.get_monitored_stocks_path()
        TRADE_HISTORY_PATH = path_manager.get_trade_history_path()
        
        backend_paths = {
            "analysis_result.json": str(ANALYSIS_PATH),
            "monitored_stocks.json": str(MONITORED_STOCKS_PATH),
            "trade_history.json": str(TRADE_HISTORY_PATH)
        }
        
        print("後端 API 使用的路徑:")
        for name, path in backend_paths.items():
            print(f"  {name}: {path}")
        
        return True, backend_paths
        
    except Exception as e:
        print(f"❌ 後端路徑測試失敗: {e}")
        return False, {}

def test_portfolio_manager():
    """測試投資組合管理器的路徑配置"""
    print("\n💼 測試投資組合管理器路徑")
    print("-" * 40)
    
    try:
        from backend.portfolio_manager import PORTFOLIO_FILE, ANALYSIS_RESULT_FILE, TRADE_HISTORY_FILE
        
        portfolio_paths = {
            "analysis_result.json": str(ANALYSIS_RESULT_FILE),
            "monitored_stocks.json": str(PORTFOLIO_FILE),
            "trade_history.json": str(TRADE_HISTORY_FILE)
        }
        
        print("投資組合管理器使用的路徑:")
        for name, path in portfolio_paths.items():
            print(f"  {name}: {path}")
        
        return True, portfolio_paths
        
    except Exception as e:
        print(f"❌ 投資組合管理器路徑測試失敗: {e}")
        return False, {}

def test_analyzer_paths():
    """測試分析器的路徑邏輯"""
    print("\n📊 測試分析器路徑邏輯")
    print("-" * 40)
    
    try:
        # 模擬分析器的路徑獲取邏輯
        from backend.path_manager import get_analysis_path, get_monitored_stocks_path
        
        analysis_path = get_analysis_path()
        monitored_path = get_monitored_stocks_path()
        
        analyzer_paths = {
            "analysis_result.json": str(analysis_path),
            "monitored_stocks.json": str(monitored_path),
            "trade_history.json": "N/A (不直接寫入)"
        }
        
        print("分析器使用的路徑:")
        for name, path in analyzer_paths.items():
            print(f"  {name}: {path}")
        
        return True, analyzer_paths
        
    except Exception as e:
        print(f"❌ 分析器路徑測試失敗: {e}")
        return False, {}

def compare_paths(path_sets):
    """比較所有組件的路徑是否一致"""
    print("\n🔍 路徑一致性比較")
    print("=" * 50)
    
    files = ["analysis_result.json", "monitored_stocks.json", "trade_history.json"]
    all_consistent = True
    
    for filename in files:
        print(f"\n📁 {filename}:")
        
        paths_for_file = []
        for component_name, paths in path_sets.items():
            if filename in paths and paths[filename] != "N/A (不直接寫入)":
                paths_for_file.append((component_name, paths[filename]))
        
        if len(set(path for _, path in paths_for_file)) == 1:
            # 所有路徑相同
            common_path = paths_for_file[0][1] if paths_for_file else "無路徑"
            print(f"  ✅ 所有組件使用相同路徑: {common_path}")
            for component_name, path in paths_for_file:
                print(f"    - {component_name}: {path}")
        else:
            # 路徑不一致
            print(f"  ❌ 路徑不一致:")
            for component_name, path in paths_for_file:
                print(f"    - {component_name}: {path}")
            all_consistent = False
    
    return all_consistent

def test_data_directory_structure():
    """測試數據目錄結構"""
    print("\n📂 測試數據目錄結構")
    print("-" * 40)
    
    # 檢查本地數據目錄
    local_data_dir = Path("data")
    container_data_dir = Path("/app/data")
    
    print("本地環境:")
    if local_data_dir.exists():
        print(f"  ✅ 數據目錄存在: {local_data_dir}")
        files = list(local_data_dir.glob("*.json"))
        for file in files:
            size = file.stat().st_size
            print(f"    - {file.name}: {size} bytes")
    else:
        print(f"  ⚠️  數據目錄不存在: {local_data_dir}")
    
    print("\n容器環境:")
    if container_data_dir.exists():
        print(f"  ✅ 數據目錄存在: {container_data_dir}")
        files = list(container_data_dir.glob("*.json"))
        for file in files:
            size = file.stat().st_size
            print(f"    - {file.name}: {size} bytes")
    else:
        print(f"  ⚠️  數據目錄不存在: {container_data_dir} (正常，非容器環境)")

def main():
    """主測試函數"""
    print("🧪 BullPS-v3 路徑一致性驗證")
    print("=" * 60)
    
    # 執行各組件路徑測試
    tests = [
        ("路徑管理器", test_path_manager),
        ("後端 API", test_backend_main),
        ("投資組合管理器", test_portfolio_manager),
        ("分析器", test_analyzer_paths)
    ]
    
    path_sets = {}
    passed_tests = 0
    
    for test_name, test_func in tests:
        success, paths = test_func()
        if success:
            path_sets[test_name] = paths
            passed_tests += 1
    
    # 比較路徑一致性
    if path_sets:
        is_consistent = compare_paths(path_sets)
    else:
        is_consistent = False
    
    # 測試數據目錄結構
    test_data_directory_structure()
    
    # 總結
    print("\n" + "=" * 60)
    print("🎯 驗證總結")
    print("=" * 60)
    
    print(f"組件測試: {passed_tests}/{len(tests)} 通過")
    print(f"路徑一致性: {'✅ 一致' if is_consistent else '❌ 不一致'}")
    
    if passed_tests == len(tests) and is_consistent:
        print("\n🎉 路徑一致性驗證通過！")
        print("✅ 所有組件使用統一的數據文件路徑")
        print("✅ 前端更新時所有節點讀寫同一份 JSON")
        print("✅ 無論本地或雲端部署都保持一致")
    else:
        print("\n⚠️  路徑一致性驗證失敗")
        print("需要檢查和修復路徑配置問題")
    
    print("\n📋 建議:")
    print("1. 確保所有組件都使用 path_manager")
    print("2. 避免硬編碼文件路徑")
    print("3. 定期運行此驗證腳本")
    print("4. 部署前確認路徑一致性")

if __name__ == "__main__":
    main()
