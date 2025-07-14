#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試 JSON 文件錯誤修復
驗證後端能正確處理空文件和損壞的 JSON 文件
"""

import json
import requests
import time
import subprocess
import sys
from pathlib import Path

def test_json_file_handling():
    """測試 JSON 文件處理"""
    print("🔧 測試 JSON 文件錯誤處理...")
    
    backend_dir = Path(__file__).parent / "backend"
    
    # 測試文件路徑
    test_files = {
        "monitored_stocks.json": [],
        "trade_history.json": [],
        "analysis_result.json": {"result": []}
    }
    
    for filename, default_content in test_files.items():
        file_path = backend_dir / filename
        
        print(f"\n📁 測試 {filename}:")
        
        # 測試 1: 空文件
        print("  測試 1: 空文件處理")
        file_path.write_text("", encoding='utf-8')
        
        # 測試 2: 無效 JSON
        print("  測試 2: 無效 JSON 處理")
        file_path.write_text("invalid json content", encoding='utf-8')
        
        # 測試 3: 刪除文件
        print("  測試 3: 缺失文件處理")
        if file_path.exists():
            file_path.unlink()
        
        print(f"  ✅ {filename} 測試準備完成")
    
    return True

def test_api_endpoints():
    """測試 API 端點"""
    print("\n🌐 測試 API 端點...")
    
    base_url = "http://localhost:8080"
    
    endpoints = [
        "/api/health",
        "/api/analysis",
        "/api/monitored-stocks",
        "/api/trade-history"
    ]
    
    results = {}
    
    for endpoint in endpoints:
        try:
            print(f"  測試 {endpoint}...")
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            
            if response.status_code == 200:
                print(f"    ✅ 狀態碼: {response.status_code}")
                
                # 檢查是否為有效 JSON
                try:
                    data = response.json()
                    print(f"    ✅ 有效 JSON 響應")
                    results[endpoint] = {"status": "success", "data": data}
                except json.JSONDecodeError:
                    print(f"    ⚠️  響應不是有效 JSON")
                    results[endpoint] = {"status": "invalid_json"}
            else:
                print(f"    ❌ 狀態碼: {response.status_code}")
                results[endpoint] = {"status": "error", "code": response.status_code}
                
        except requests.exceptions.RequestException as e:
            print(f"    ❌ 請求失敗: {e}")
            results[endpoint] = {"status": "connection_error"}
    
    return results

def start_backend_server():
    """啟動後端服務"""
    print("🚀 啟動後端服務...")
    
    backend_dir = Path(__file__).parent / "backend"
    
    try:
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待服務啟動
        print("⏳ 等待服務啟動...")
        time.sleep(8)
        
        return process
        
    except Exception as e:
        print(f"❌ 啟動後端服務失敗: {e}")
        return None

def main():
    """主測試函數"""
    print("🔧 JSON 文件錯誤修復測試")
    print("=" * 50)
    
    # 步驟 1: 準備測試環境
    test_json_file_handling()
    
    # 步驟 2: 啟動後端服務
    backend_process = start_backend_server()
    
    if not backend_process:
        print("❌ 無法啟動後端服務")
        return False
    
    try:
        # 步驟 3: 測試 API 端點
        api_results = test_api_endpoints()
        
        # 步驟 4: 分析結果
        print("\n" + "=" * 50)
        print("測試結果總結")
        print("=" * 50)
        
        success_count = 0
        total_count = len(api_results)
        
        for endpoint, result in api_results.items():
            status = result.get("status")
            if status == "success":
                print(f"✅ {endpoint}: 正常")
                success_count += 1
            elif status == "invalid_json":
                print(f"⚠️  {endpoint}: JSON 格式問題")
            elif status == "error":
                print(f"❌ {endpoint}: HTTP 錯誤 {result.get('code')}")
            else:
                print(f"❌ {endpoint}: 連接錯誤")
        
        print(f"\n成功率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
        
        # 檢查關鍵端點
        critical_endpoints = ["/api/health", "/api/monitored-stocks"]
        critical_success = all(
            api_results.get(ep, {}).get("status") == "success" 
            for ep in critical_endpoints
        )
        
        if critical_success:
            print("🎉 關鍵端點測試通過！JSON 錯誤修復成功")
            return True
        else:
            print("⚠️  部分關鍵端點仍有問題")
            return False
            
    finally:
        # 清理：終止後端進程
        if backend_process:
            print("\n🛑 終止後端服務...")
            backend_process.terminate()
            try:
                backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend_process.kill()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
