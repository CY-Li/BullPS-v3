#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zeabur 路徑問題診斷腳本
快速檢查前端讀取的 API 端點和實際文件位置
"""

import requests
import json

def check_zeabur_apis():
    """檢查 Zeabur 上的 API 端點"""
    base_url = "https://bullps-v3.zeabur.app"
    
    endpoints = {
        "健康檢查": "/api/health",
        "調試文件": "/api/debug-files", 
        "分析結果": "/api/analysis",
        "監控股票": "/api/monitored-stocks",
        "交易歷史": "/api/trade-history"
    }
    
    print("🔍 檢查 Zeabur API 端點")
    print("=" * 60)
    
    for name, endpoint in endpoints.items():
        print(f"\n📡 {name} ({endpoint})")
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if endpoint == "/api/health":
                    print("  ✅ 健康檢查正常")
                    if "path_manager_info" in data:
                        path_info = data["path_manager_info"]
                        if "error" in path_info:
                            print(f"  ⚠️  路徑管理器錯誤: {path_info['error']}")
                            if "fallback_paths" in path_info:
                                print("  📁 回退路徑:")
                                for file, path in path_info["fallback_paths"].items():
                                    exists = path_info["fallback_exists"].get(file, False)
                                    status = "✅" if exists else "❌"
                                    print(f"    {file}: {path} {status}")
                        else:
                            print("  📁 路徑信息:")
                            paths = path_info.get("paths", {})
                            exists = path_info.get("file_exists", {})
                            sizes = path_info.get("file_sizes", {})
                            
                            for file, path in paths.items():
                                file_exists = exists.get(file, False)
                                file_size = sizes.get(file, 0)
                                status = f"✅ {file_size} bytes" if file_exists and file_size > 0 else "❌ 空或不存在"
                                print(f"    {file}: {path} - {status}")
                
                elif endpoint == "/api/debug-files":
                    print("  ✅ 調試信息獲取成功")
                    print("  📁 當前使用的路徑:")
                    for name, path in data.get("current_paths", {}).items():
                        exists = data.get("file_exists", {}).get(name, False)
                        size = data.get("file_sizes", {}).get(name, 0)
                        status = f"✅ {size} bytes" if exists and size > 0 else "❌ 空或不存在"
                        print(f"    {name}: {path} - {status}")
                    
                    print("  📄 找到的所有 JSON 文件:")
                    for file in data.get("all_json_files", []):
                        print(f"    {file}")
                
                elif endpoint in ["/api/analysis", "/api/monitored-stocks", "/api/trade-history"]:
                    if isinstance(data, dict) and "result" in data:
                        # 分析結果格式
                        result_count = len(data.get("result", []))
                        print(f"  ✅ 返回 {result_count} 個分析結果")
                        if result_count == 0:
                            print("  ⚠️  分析結果為空")
                    elif isinstance(data, list):
                        # 列表格式
                        count = len(data)
                        print(f"  ✅ 返回 {count} 個項目")
                        if count == 0:
                            print("  ⚠️  數據為空")
                    else:
                        print(f"  ⚠️  未知數據格式: {type(data)}")
                        
            else:
                print(f"  ❌ HTTP {response.status_code}: {response.text[:100]}")
                
        except requests.exceptions.Timeout:
            print("  ❌ 請求超時")
        except requests.exceptions.ConnectionError:
            print("  ❌ 連接錯誤")
        except Exception as e:
            print(f"  ❌ 錯誤: {e}")

def check_local_apis():
    """檢查本地 API 端點"""
    base_url = "http://localhost:8080"
    
    print("\n🏠 檢查本地 API 端點")
    print("=" * 60)
    
    endpoints = ["/api/analysis", "/api/monitored-stocks", "/api/trade-history"]
    
    for endpoint in endpoints:
        print(f"\n📡 本地 {endpoint}")
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, dict) and "result" in data:
                    result_count = len(data.get("result", []))
                    print(f"  ✅ 返回 {result_count} 個分析結果")
                elif isinstance(data, list):
                    count = len(data)
                    print(f"  ✅ 返回 {count} 個項目")
                else:
                    print(f"  ⚠️  未知數據格式: {type(data)}")
                    
            else:
                print(f"  ❌ HTTP {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("  ❌ 本地服務未運行")
        except Exception as e:
            print(f"  ❌ 錯誤: {e}")

def main():
    """主診斷函數"""
    print("🧪 BullPS-v3 Zeabur 路徑問題診斷")
    print("=" * 80)
    
    # 檢查 Zeabur API
    check_zeabur_apis()
    
    # 檢查本地 API（如果可用）
    check_local_apis()
    
    print("\n" + "=" * 80)
    print("🎯 診斷總結")
    print("=" * 80)
    
    print("\n📋 檢查清單:")
    print("1. ✅ Zeabur 健康檢查是否正常")
    print("2. ✅ 路徑管理器是否工作正常")
    print("3. ✅ 文件是否存在且不為空")
    print("4. ✅ API 端點是否返回數據")
    print("5. ✅ 前端是否能正常顯示")
    
    print("\n🔧 如果問題持續存在:")
    print("1. 檢查 /api/debug-files 端點的詳細信息")
    print("2. 在 Zeabur 控制台查看應用日誌")
    print("3. 手動觸發分析: /api/trigger-analysis")
    print("4. 確認前端緩存已清除")

if __name__ == "__main__":
    main()
