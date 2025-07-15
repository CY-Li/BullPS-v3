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
        self._paths = {}
        self._initialize_paths()
    
    def _initialize_paths(self):
        """初始化所有文件路徑"""
        files = {
            "analysis_result.json": self._get_analysis_result_path(),
            "monitored_stocks.json": self._get_monitored_stocks_path(),
            "trade_history.json": self._get_trade_history_path()
        }
        
        for filename, path in files.items():
            self._paths[filename] = path
            self._ensure_file_exists(path, filename)
    
    def _get_analysis_result_path(self):
        """獲取分析結果文件路徑"""
        possible_paths = [
            Path("/app/data/analysis_result.json"),
            Path("/app/analysis_result.json"),
            self.base_dir / "analysis_result.json",
            Path("/app/backend/analysis_result.json")
        ]
        
        return self._find_existing_or_default(possible_paths, "analysis_result.json")
    
    def _get_monitored_stocks_path(self):
        """獲取監控股票文件路徑"""
        possible_paths = [
            Path("/app/data/monitored_stocks.json"),
            Path("/app/backend/monitored_stocks.json"),
            self.base_dir / "backend" / "monitored_stocks.json",
            Path("/app/monitored_stocks.json")
        ]
        
        return self._find_existing_or_default(possible_paths, "monitored_stocks.json")
    
    def _get_trade_history_path(self):
        """獲取交易歷史文件路徑"""
        possible_paths = [
            Path("/app/data/trade_history.json"),
            Path("/app/backend/trade_history.json"),
            self.base_dir / "backend" / "trade_history.json",
            Path("/app/trade_history.json")
        ]
        
        return self._find_existing_or_default(possible_paths, "trade_history.json")
    
    def _find_existing_or_default(self, possible_paths, filename):
        """查找現有文件或返回默認路徑"""
        # 首先查找現有文件
        for path in possible_paths:
            if path.exists() and path.stat().st_size > 0:
                print(f"Found existing {filename} at: {path}")
                return path
        
        # 如果沒有找到，使用默認路徑
        if Path("/app/data").exists():
            default_path = Path("/app/data") / filename
        elif filename == "analysis_result.json":
            default_path = self.base_dir / filename
        else:
            default_path = self.base_dir / "backend" / filename
        
        print(f"Using default path for {filename}: {default_path}")
        return default_path
    
    def _ensure_file_exists(self, path, filename):
        """確保文件存在，如果不存在則創建空文件"""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            
            if not path.exists():
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
        for filename, primary_path in self._paths.items():
            if not primary_path.exists():
                continue
                
            try:
                with open(primary_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 同步到其他位置
                sync_paths = []
                if filename == "analysis_result.json":
                    sync_paths = [
                        Path("/app/analysis_result.json"),
                        Path("analysis_result.json"),
                        Path("backend/analysis_result.json")
                    ]
                elif filename == "monitored_stocks.json":
                    sync_paths = [
                        Path("/app/backend/monitored_stocks.json"),
                        Path("backend/monitored_stocks.json")
                    ]
                elif filename == "trade_history.json":
                    sync_paths = [
                        Path("/app/backend/trade_history.json"),
                        Path("backend/trade_history.json")
                    ]
                
                for sync_path in sync_paths:
                    if sync_path != primary_path:
                        try:
                            sync_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(sync_path, 'w', encoding='utf-8') as f:
                                json.dump(data, f, indent=2, ensure_ascii=False)
                        except Exception as e:
                            print(f"Failed to sync {filename} to {sync_path}: {e}")
                            
            except Exception as e:
                print(f"Failed to read {filename} for syncing: {e}")
    
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
