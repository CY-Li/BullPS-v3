#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統一的文件路徑管理模塊
確保所有組件使用相同的文件路徑，避免讀寫不一致問題
"""

import os
import json
from pathlib import Path

class PathManager:
    """統一管理所有數據文件的路徑"""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self._get_unified_data_dir()
        self._paths = {}
        self._initialize_paths()

    def _get_unified_data_dir(self):
        """獲取統一的數據目錄"""
        # 檢測 Zeabur 環境
        is_zeabur = os.environ.get("ZEABUR") == "1" or "zeabur" in os.environ.get("HOSTNAME", "").lower()

        # 更準確的容器環境檢測
        is_container = (
            Path("/app").exists() and
            (os.environ.get("CONTAINER_ENV") == "true" or
             os.environ.get("PORT") is not None or  # Zeabur/容器通常設置 PORT 環境變數
             Path("/proc/1/cgroup").exists())  # Linux 容器特徵
        )

        if is_zeabur:
            # Zeabur 環境：使用可寫的目錄
            # 嘗試多個可能的可寫位置
            possible_dirs = [
                Path("/tmp/data"),           # 臨時目錄通常可寫
                Path("/app/backend"),        # backend 目錄可能可寫
                Path("/app"),                # 應用根目錄
                Path("/var/tmp/data")        # 另一個臨時目錄
            ]

            for data_dir in possible_dirs:
                try:
                    data_dir.mkdir(parents=True, exist_ok=True)
                    # 測試寫入權限
                    test_file = data_dir / "test_write.tmp"
                    test_file.write_text("test")
                    test_file.unlink()
                    print(f"✅ Zeabur 環境使用可寫目錄: {data_dir}")

                    # 遷移現有數據文件
                    self._migrate_data_files(data_dir)
                    return data_dir
                except (PermissionError, OSError) as e:
                    print(f"⚠️  目錄 {data_dir} 不可寫: {e}")
                    continue

            # 如果都不可寫，回退到 /app/data（只讀模式）
            print("⚠️  所有目錄都不可寫，使用只讀模式")
            data_dir = Path("/app/data")

        elif is_container:
            # 其他容器環境：使用 /app/data
            data_dir = Path("/app/data")
        else:
            # 本地環境：使用項目根目錄下的 data
            data_dir = self.base_dir / "data"

        # 確保數據目錄存在
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            print(f"Using unified data directory: {data_dir}")
        except PermissionError:
            print(f"Cannot create data directory {data_dir}, using read-only access")

        return data_dir

    def _migrate_data_files(self, target_dir):
        """遷移現有數據文件到可寫目錄"""
        source_dir = Path("/app/data")
        if not source_dir.exists():
            return

        files_to_migrate = [
            "analysis_result.json",
            "monitored_stocks.json",
            "trade_history.json"
        ]

        for filename in files_to_migrate:
            source_file = source_dir / filename
            target_file = target_dir / filename

            if source_file.exists() and not target_file.exists():
                try:
                    # 複製文件內容
                    content = source_file.read_text(encoding='utf-8')
                    target_file.write_text(content, encoding='utf-8')
                    print(f"✅ 遷移文件: {source_file} → {target_file}")
                except Exception as e:
                    print(f"⚠️  遷移文件失敗 {filename}: {e}")

    def _initialize_paths(self):
        """初始化所有文件路徑"""
        files = {
            "analysis_result.json": self.data_dir / "analysis_result.json",
            "monitored_stocks.json": self.data_dir / "monitored_stocks.json",
            "trade_history.json": self.data_dir / "trade_history.json"
        }

        for filename, path in files.items():
            self._paths[filename] = path
            self._ensure_file_exists(path, filename)
    

    

    
    def _ensure_file_exists(self, path, filename):
        """確保文件存在，如果不存在則創建空文件"""
        try:
            # 嘗試創建目錄（忽略權限錯誤）
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                print(f"Cannot create directory for {filename}, using existing path")

            if not path.exists():
                try:
                    if filename == "analysis_result.json":
                        empty_data = {
                            "result": [],
                            "timestamp": "",
                            "analysis_date": "",
                            "total_stocks": 0,
                            "analyzed_stocks": 0
                        }
                    else:
                        empty_data = []

                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(empty_data, f, indent=2, ensure_ascii=False)
                    print(f"Created empty {filename} at: {path}")
                except (PermissionError, OSError) as e:
                    print(f"Cannot create {filename} at {path}: {e}")
        except Exception as e:
            print(f"Failed to ensure {filename} exists: {e}")
    
    def get_path(self, filename):
        """獲取指定文件的路徑"""
        return self._paths.get(filename)
    
    def get_analysis_path(self):
        """獲取分析結果文件路徑"""
        return self._paths["analysis_result.json"]
    
    def get_monitored_stocks_path(self):
        """獲取監控股票文件路徑"""
        return self._paths["monitored_stocks.json"]
    
    def get_trade_history_path(self):
        """獲取交易歷史文件路徑"""
        return self._paths["trade_history.json"]
    
    def sync_files(self):
        """同步文件到所有可能的位置（用於兼容性）"""
        print("Using unified data directory - no sync needed")
        # 統一路徑後不需要同步，所有組件都使用相同的文件位置
    
    def get_info(self):
        """獲取路徑管理器的信息"""
        info = {
            "environment": "container" if Path("/app/data").exists() else "local",
            "base_dir": str(self.base_dir),
            "paths": {name: str(path) for name, path in self._paths.items()},
            "file_exists": {name: path.exists() for name, path in self._paths.items()},
            "file_sizes": {}
        }
        
        for name, path in self._paths.items():
            try:
                info["file_sizes"][name] = path.stat().st_size if path.exists() else 0
            except Exception:
                info["file_sizes"][name] = 0
        
        return info

# 全局路徑管理器實例
path_manager = PathManager()

# 便捷函數
def get_analysis_path():
    return path_manager.get_analysis_path()

def get_monitored_stocks_path():
    return path_manager.get_monitored_stocks_path()

def get_trade_history_path():
    return path_manager.get_trade_history_path()

def sync_all_files():
    """同步所有文件到兼容位置"""
    path_manager.sync_files()

def get_path_info():
    """獲取路徑信息"""
    return path_manager.get_info()

if __name__ == "__main__":
    # 測試路徑管理器
    print("🔧 路徑管理器測試")
    print("=" * 50)
    
    info = get_path_info()
    print(f"環境: {info['environment']}")
    print(f"基礎目錄: {info['base_dir']}")
    print()
    
    print("文件路徑:")
    for name, path in info['paths'].items():
        exists = info['file_exists'][name]
        size = info['file_sizes'][name]
        status = f"✅ {size} bytes" if exists and size > 0 else "❌ 不存在或為空"
        print(f"  {name}: {path} - {status}")
    
    print("\n同步文件...")
    sync_all_files()
    print("同步完成！")
