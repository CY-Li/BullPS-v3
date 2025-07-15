# 本地數據目錄使用指南

## 🎯 概述

為了方便在本地開發環境中手動管理數據文件，我們創建了一個專用的 `data` 目錄，您可以直接將文件複製到這個目錄中，應用程序會自動讀取這些文件。

## 📁 目錄結構

```
BullPS-v3/
├── data/                      # 本地數據目錄
│   ├── monitored_stocks.json  # 監控股票數據
│   ├── trade_history.json     # 交易歷史數據
│   └── analysis_result.json   # 分析結果數據
├── use_local_data_dir.bat     # 啟用本地數據目錄的批處理文件
└── ...
```

## 🚀 使用方法

### 方法 1: 使用批處理文件啟動（推薦）

1. 雙擊運行 `use_local_data_dir.bat`
2. 批處理文件會設置必要的環境變量並啟動應用程序
3. 應用程序將自動使用 `data` 目錄中的文件

### 方法 2: 手動設置環境變量

```bash
# Windows CMD
set BULLPS_USE_LOCAL_DATA_DIR=true
python -m backend.main

# Windows PowerShell
$env:BULLPS_USE_LOCAL_DATA_DIR="true"
python -m backend.main

# Linux/Mac
export BULLPS_USE_LOCAL_DATA_DIR=true
python -m backend.main
```

## 📋 手動更新數據文件

您可以直接編輯或替換 `data` 目錄中的文件：

### 更新監控股票

1. 編輯或替換 `data/monitored_stocks.json`
2. 應用程序會自動讀取更新後的文件

### 更新交易歷史

1. 編輯或替換 `data/trade_history.json`
2. 應用程序會自動讀取更新後的文件

### 更新分析結果

1. 編輯或替換 `data/analysis_result.json`
2. 應用程序會自動讀取更新後的文件

## 🔍 驗證設置

啟動應用程序後，您可以通過以下方式驗證是否正確使用了 `data` 目錄：

1. 檢查控制台輸出，應該看到類似信息：
   ```
   📁 本地環境使用 data 目錄: C:\Users\Jimmy\BullPS-v3\data
   ✅ 本地 data 目錄創建成功: C:\Users\Jimmy\BullPS-v3\data
   ```

2. 訪問文件路徑狀態 API：
   ```
   http://localhost:8080/api/file-paths-status
   ```

3. 修改 `data` 目錄中的文件，然後刷新頁面，查看是否生效

## 🔄 在本地和 Zeabur 環境之間切換

- **本地環境**: 使用 `data` 目錄
- **Zeabur 環境**: 使用 `/tmp/bullps_data` 目錄

系統會自動檢測環境並使用正確的目錄，您不需要修改任何代碼。

## 📊 文件路徑映射

| 文件類型 | 本地路徑 | Zeabur 路徑 |
|---------|---------|------------|
| 監控股票 | `data/monitored_stocks.json` | `/tmp/bullps_data/monitored_stocks.json` |
| 交易歷史 | `data/trade_history.json` | `/tmp/bullps_data/trade_history.json` |
| 分析結果 | `data/analysis_result.json` | `/tmp/bullps_data/analysis_result.json` |

## 🔧 故障排除

### 問題 1: 應用程序沒有使用 `data` 目錄

確保您已經設置了環境變量 `BULLPS_USE_LOCAL_DATA_DIR=true`，或者使用提供的批處理文件啟動應用程序。

### 問題 2: 更新文件後沒有生效

1. 確認文件格式正確（有效的 JSON）
2. 確認文件權限正確
3. 重新啟動應用程序

### 問題 3: 找不到 `data` 目錄

1. 確認您在正確的項目根目錄中
2. 手動創建 `data` 目錄
3. 重新啟動應用程序

## 🎉 總結

使用本地 `data` 目錄的優勢：

1. **✅ 簡化文件管理**: 直接編輯或替換文件
2. **✅ 即時生效**: 應用程序自動讀取更新後的文件
3. **✅ 環境一致性**: 本地和 Zeabur 環境使用相同的文件結構
4. **✅ 無需修改代碼**: 系統自動檢測環境並使用正確的目錄
