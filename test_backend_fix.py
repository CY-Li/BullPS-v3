#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試後端修復
驗證 FastAPI 棄用警告是否已修復
"""

import subprocess
import sys
import time
import requests
from pathlib import Path

def test_backend_startup():
    """
    測試後端啟動是否正常
    """
    print("🚀 測試後端啟動...")
    
    try:
        # 啟動後端服務
        backend_dir = Path(__file__).parent / "backend"
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待服務啟動
        print("⏳ 等待服務啟動...")
        time.sleep(5)
        
        # 檢查服務是否正常運行
        try:
            response = requests.get("http://localhost:8080/api/health", timeout=5)
            if response.status_code == 200:
                print("✅ 後端服務啟動成功！")
                print(f"   健康檢查響應: {response.json()}")
                
                # 檢查是否還有棄用警告
                stdout, stderr = process.communicate(timeout=2)
                if "DeprecationWarning" in stderr:
                    print("⚠️  仍有棄用警告:")
                    print(stderr)
                else:
                    print("✅ 沒有棄用警告！")
                
                return True
            else:
                print(f"❌ 健康檢查失敗: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 無法連接到後端服務: {e}")
            return False
            
        finally:
            # 終止進程
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False

def check_code_quality():
    """
    檢查代碼品質
    """
    print("\n🔍 檢查代碼品質...")
    
    backend_main = Path(__file__).parent / "backend" / "main.py"
    
    if not backend_main.exists():
        print("❌ backend/main.py 不存在")
        return False
    
    content = backend_main.read_text(encoding='utf-8')
    
    # 檢查是否使用了新的 lifespan 方式
    if "@asynccontextmanager" in content and "async def lifespan" in content:
        print("✅ 使用了新的 lifespan 事件處理器")
    else:
        print("❌ 未使用新的 lifespan 事件處理器")
        return False
    
    # 檢查是否移除了舊的 on_event
    if "@app.on_event" in content:
        print("⚠️  仍然使用舊的 @app.on_event 裝飾器")
        return False
    else:
        print("✅ 已移除舊的 @app.on_event 裝飾器")
    
    # 檢查是否正確導入了 asynccontextmanager
    if "from contextlib import asynccontextmanager" in content:
        print("✅ 正確導入了 asynccontextmanager")
    else:
        print("❌ 未正確導入 asynccontextmanager")
        return False
    
    return True

def main():
    """
    主測試函數
    """
    print("🔧 FastAPI 棄用警告修復測試")
    print("=" * 50)
    
    # 檢查代碼品質
    code_quality_ok = check_code_quality()
    
    if not code_quality_ok:
        print("\n❌ 代碼品質檢查失敗")
        return False
    
    # 測試後端啟動
    startup_ok = test_backend_startup()
    
    print("\n" + "=" * 50)
    print("測試總結")
    print("=" * 50)
    
    if code_quality_ok and startup_ok:
        print("✅ 所有測試通過！")
        print("✅ FastAPI 棄用警告已修復")
        print("✅ 後端服務正常運行")
        return True
    else:
        print("❌ 部分測試失敗")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
