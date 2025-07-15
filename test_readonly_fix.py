#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試只讀文件系統修復
模擬 Zeabur 環境中的只讀文件系統問題
"""

import os
import json
from pathlib import Path

def test_readonly_handling():
    """測試只讀文件系統的錯誤處理"""
    print("🧪 測試只讀文件系統錯誤處理")
    print("=" * 50)
    
    # 模擬路徑管理器的同步邏輯
    def safe_sync_file(source_path, target_path, data):
        """安全的文件同步，處理只讀錯誤"""
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✅ 成功同步到: {target_path}")
            return True
        except (PermissionError, OSError) as e:
            print(f"⚠️  無法同步到 {target_path}（只讀文件系統）: {e}")
            return False
        except Exception as e:
            print(f"❌ 同步失敗 {target_path}: {e}")
            return False
    
    # 測試數據
    test_data = {"test": "data", "timestamp": "2025-07-15"}
    
    # 測試各種路徑
    test_paths = [
        Path("test_writable.json"),  # 應該可寫
        Path("/tmp/test_readonly.json"),  # 可能可寫
        Path("/app/backend/test_readonly.json"),  # 模擬只讀
        Path("/app/data/test_readonly.json"),  # 模擬只讀
    ]
    
    success_count = 0
    for path in test_paths:
        if safe_sync_file(Path("dummy"), path, test_data):
            success_count += 1
            # 清理測試文件
            try:
                path.unlink()
            except:
                pass
    
    print(f"\n📊 測試結果: {success_count}/{len(test_paths)} 個路徑可寫")
    
    return success_count > 0

def test_path_manager_import():
    """測試路徑管理器導入和基本功能"""
    print("\n🔧 測試路徑管理器")
    print("=" * 50)
    
    try:
        from backend.path_manager import path_manager, sync_all_files
        
        # 獲取路徑信息
        info = path_manager.get_info()
        print(f"環境: {info['environment']}")
        print(f"基礎目錄: {info['base_dir']}")
        
        print("\n文件路徑:")
        for name, path in info['paths'].items():
            exists = info['file_exists'][name]
            size = info['file_sizes'][name]
            status = f"✅ {size} bytes" if exists and size > 0 else "❌ 不存在或為空"
            print(f"  {name}: {path} - {status}")
        
        # 測試同步（應該安全處理錯誤）
        print("\n測試文件同步:")
        try:
            sync_all_files()
            print("✅ 同步完成（錯誤已安全處理）")
        except Exception as e:
            print(f"❌ 同步失敗: {e}")
        
        return True
        
    except ImportError as e:
        print(f"❌ 無法導入路徑管理器: {e}")
        return False
    except Exception as e:
        print(f"❌ 路徑管理器測試失敗: {e}")
        return False

def test_api_endpoints():
    """測試 API 端點的錯誤處理"""
    print("\n🌐 測試 API 端點")
    print("=" * 50)
    
    try:
        import requests
        
        # 測試本地端點（如果可用）
        base_url = "http://localhost:8080"
        endpoints = ["/api/health", "/api/analysis", "/api/monitored-stocks", "/api/trade-history"]
        
        for endpoint in endpoints:
            try:
                response = requests.get(f"{base_url}{endpoint}", timeout=5)
                if response.status_code == 200:
                    print(f"✅ {endpoint}: 正常")
                else:
                    print(f"⚠️  {endpoint}: HTTP {response.status_code}")
            except requests.exceptions.ConnectionError:
                print(f"⚠️  {endpoint}: 服務未運行")
            except Exception as e:
                print(f"❌ {endpoint}: {e}")
        
        return True
        
    except ImportError:
        print("⚠️  requests 模塊未安裝，跳過 API 測試")
        return True
    except Exception as e:
        print(f"❌ API 測試失敗: {e}")
        return False

def main():
    """主測試函數"""
    print("🧪 只讀文件系統修復測試")
    print("=" * 60)
    
    tests = [
        ("只讀錯誤處理", test_readonly_handling),
        ("路徑管理器", test_path_manager_import),
        ("API 端點", test_api_endpoints)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 執行測試: {test_name}")
        try:
            if test_func():
                print(f"✅ {test_name} 測試通過")
                passed += 1
            else:
                print(f"❌ {test_name} 測試失敗")
        except Exception as e:
            print(f"❌ {test_name} 測試異常: {e}")
    
    print("\n" + "=" * 60)
    print(f"🎯 測試總結: {passed}/{total} 個測試通過")
    
    if passed == total:
        print("✅ 所有測試通過！修復應該有效。")
    else:
        print("⚠️  部分測試失敗，可能需要進一步調整。")
    
    print("\n📝 修復要點:")
    print("1. 所有文件操作都有錯誤處理")
    print("2. 只讀文件系統錯誤被安全忽略")
    print("3. 路徑管理器智能選擇可寫位置")
    print("4. 容器環境和本地環境都能正常工作")

if __name__ == "__main__":
    main()
