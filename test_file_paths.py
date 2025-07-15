#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試文件路徑檢測邏輯
驗證在不同環境下能否正確找到數據文件
"""

import os
import json
from pathlib import Path

def test_file_detection():
    """測試文件檢測邏輯"""
    print("🔍 測試文件路徑檢測邏輯")
    print("=" * 50)
    
    # 模擬 get_file_path 函數
    def get_file_path(filename):
        """動態檢測文件的實際位置"""
        BASE_DIR = Path(__file__).parent
        
        # 可能的路徑列表（按優先級排序）
        possible_paths = [
            Path("/app/data") / filename,  # 容器數據目錄
            Path("/app") / filename,       # 容器根目錄
            BASE_DIR / filename,           # 本地根目錄
            BASE_DIR / "backend" / filename  # 本地backend目錄
        ]
        
        print(f"\n📁 尋找文件: {filename}")
        for i, path in enumerate(possible_paths, 1):
            exists = path.exists()
            status = "✅ 找到" if exists else "❌ 不存在"
            print(f"  {i}. {path} - {status}")
            if exists:
                return path
        
        # 如果都不存在，使用默認路徑
        if os.path.exists("/app/data"):
            default_path = Path("/app/data") / filename
        else:
            default_path = BASE_DIR / "backend" / filename if filename != "analysis_result.json" else BASE_DIR / filename
        
        print(f"  ⚠️  使用默認路徑: {default_path}")
        return default_path
    
    # 測試三個關鍵文件
    files_to_test = [
        "analysis_result.json",
        "monitored_stocks.json", 
        "trade_history.json"
    ]
    
    results = {}
    for filename in files_to_test:
        path = get_file_path(filename)
        results[filename] = {
            "path": str(path),
            "exists": path.exists(),
            "size": path.stat().st_size if path.exists() else 0
        }
    
    # 顯示結果摘要
    print("\n" + "=" * 50)
    print("📊 檢測結果摘要")
    print("=" * 50)
    
    for filename, info in results.items():
        status = "✅ 正常" if info["exists"] and info["size"] > 0 else "❌ 問題"
        print(f"{filename}:")
        print(f"  路徑: {info['path']}")
        print(f"  存在: {info['exists']}")
        print(f"  大小: {info['size']} bytes")
        print(f"  狀態: {status}")
        print()
    
    return results

def test_api_simulation():
    """模擬 API 端點的文件讀取"""
    print("🌐 模擬 API 端點測試")
    print("=" * 50)
    
    # 模擬後端的文件路徑檢測
    BASE_DIR = Path(__file__).parent
    
    def get_file_path(filename):
        possible_paths = [
            Path("/app/data") / filename,
            Path("/app") / filename,
            BASE_DIR / filename,
            BASE_DIR / "backend" / filename
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        if os.path.exists("/app/data"):
            return Path("/app/data") / filename
        else:
            return BASE_DIR / "backend" / filename if filename != "analysis_result.json" else BASE_DIR / filename
    
    # 測試各個 API 端點
    endpoints = {
        "/api/analysis": "analysis_result.json",
        "/api/monitored-stocks": "monitored_stocks.json", 
        "/api/trade-history": "trade_history.json"
    }
    
    for endpoint, filename in endpoints.items():
        print(f"\n🔗 測試端點: {endpoint}")
        file_path = get_file_path(filename)
        
        try:
            if file_path.exists():
                content = file_path.read_text(encoding='utf-8').strip()
                if content:
                    data = json.loads(content)
                    if filename == "analysis_result.json":
                        result_count = len(data.get('result', []))
                        print(f"  ✅ 成功讀取，包含 {result_count} 個分析結果")
                    elif filename == "monitored_stocks.json":
                        stock_count = len(data) if isinstance(data, list) else 0
                        print(f"  ✅ 成功讀取，包含 {stock_count} 個監控股票")
                    elif filename == "trade_history.json":
                        trade_count = len(data) if isinstance(data, list) else 0
                        print(f"  ✅ 成功讀取，包含 {trade_count} 個交易記錄")
                else:
                    print(f"  ⚠️  文件為空")
            else:
                print(f"  ❌ 文件不存在: {file_path}")
                
        except json.JSONDecodeError as e:
            print(f"  ❌ JSON 解析錯誤: {e}")
        except Exception as e:
            print(f"  ❌ 讀取錯誤: {e}")

def check_environment():
    """檢查當前環境"""
    print("🔧 環境檢查")
    print("=" * 50)
    
    checks = [
        ("當前工作目錄", os.getcwd()),
        ("Python 執行路徑", os.path.dirname(os.path.abspath(__file__))),
        ("/app/data 目錄存在", os.path.exists("/app/data")),
        ("/app 目錄存在", os.path.exists("/app")),
        ("backend 目錄存在", os.path.exists("backend")),
    ]
    
    for name, value in checks:
        print(f"  {name}: {value}")

def main():
    """主測試函數"""
    print("🧪 BullPS-v3 文件路徑檢測測試")
    print("=" * 60)
    
    # 環境檢查
    check_environment()
    print()
    
    # 文件檢測測試
    results = test_file_detection()
    print()
    
    # API 模擬測試
    test_api_simulation()
    
    # 總結
    print("\n" + "=" * 60)
    print("🎯 測試總結")
    print("=" * 60)
    
    all_files_ok = all(
        info["exists"] and info["size"] > 0 
        for info in results.values()
    )
    
    if all_files_ok:
        print("✅ 所有文件檢測正常，API 應該能正常工作")
    else:
        print("❌ 部分文件有問題，需要檢查文件路徑配置")
        
    print("\n建議:")
    print("1. 確保所有數據文件存在且不為空")
    print("2. 檢查文件路徑配置是否正確")
    print("3. 在 Zeabur 部署後運行此測試驗證")

if __name__ == "__main__":
    main()
