# Zeabur 備份目錄方案使用指南

## 🎯 方案概述

由於 Zeabur 環境中的 `/app` 目錄是只讀文件系統，我們實施了**備份目錄優先策略**，在 Zeabur 環境中自動使用 `/tmp/bullps_data` 作為主要數據存儲目錄。

## 🔧 實施的改進

### 1. 自動環境檢測
- 系統會自動檢測 Zeabur 環境
- 在 Zeabur 環境中自動設置 `BULLPS_FORCE_BACKUP_DIR=true`
- 所有數據文件將直接使用 `/tmp/bullps_data` 目錄

### 2. 路徑管理器改進
- 智能環境檢測
- 自動目錄切換
- 確保數據一致性

### 3. 容器啟動優化
- 優先初始化備份目錄
- 自動設置正確的權限
- 詳細的狀態報告

## 📋 現在如何手動覆蓋文件

### 方法 1: 直接複製到備份目錄（推薦）

```bash
# 將您的 monitored_stocks0714.json 複製到備份目錄
docker cp c:\Users\Jimmy\Downloads\monitored_stocks0714.json your-container:/tmp/bullps_data/monitored_stocks.json

# 設置正確的權限
docker exec your-container chmod 666 /tmp/bullps_data/monitored_stocks.json
```

### 方法 2: 使用複製腳本（Linux/Mac）

```bash
# 使用提供的腳本（需要在 Linux/Mac 環境中）
./copy-to-zeabur.sh /path/to/monitored_stocks0714.json your-container monitored_stocks
```

### 方法 3: 手動步驟（Windows）

```powershell
# 1. 複製文件到容器
docker cp "c:\Users\Jimmy\Downloads\monitored_stocks0714.json" your-container:/tmp/bullps_data/monitored_stocks.json

# 2. 設置權限
docker exec your-container chmod 666 /tmp/bullps_data/monitored_stocks.json

# 3. 驗證文件
docker exec your-container ls -la /tmp/bullps_data/monitored_stocks.json

# 4. 檢查文件內容
docker exec your-container head -n 10 /tmp/bullps_data/monitored_stocks.json
```

## 🔍 驗證部署

### 1. 檢查環境設置

```bash
# 檢查環境變數
docker exec your-container env | grep BULLPS

# 應該看到:
# BULLPS_BACKUP_DIR=/tmp/bullps_data
# BULLPS_FORCE_BACKUP_DIR=true (在 Zeabur 環境中)
```

### 2. 檢查文件路徑狀態

```bash
# 調用 API 檢查文件狀態
curl http://your-zeabur-app-url/api/file-paths-status
```

### 3. 檢查容器日誌

```bash
# 查看啟動日誌
docker logs your-container

# 應該看到類似信息:
# 🔍 檢測到 Zeabur 環境
# ✅ 已設置 BULLPS_FORCE_BACKUP_DIR=true
# ✅ Zeabur 環境使用備份目錄: /tmp/bullps_data
```

## 📊 文件路徑映射

### Zeabur 環境中的文件位置

| 文件類型 | 新位置 | 舊位置 |
|---------|--------|--------|
| 監控股票 | `/tmp/bullps_data/monitored_stocks.json` | `/app/monitored_stocks.json` |
| 交易歷史 | `/tmp/bullps_data/trade_history.json` | `/app/trade_history.json` |
| 分析結果 | `/tmp/bullps_data/analysis_result.json` | `/app/analysis_result.json` |

### 本地環境中的文件位置

本地環境仍然使用項目根目錄，不受影響。

## 🚀 立即解決您的問題

**現在您可以按照以下步驟更新您的 `monitored_stocks0714.json` 文件：**

### 步驟 1: 找到您的容器名稱

```bash
# 列出所有運行的容器
docker ps

# 或者列出所有容器（包括停止的）
docker ps -a
```

### 步驟 2: 複製文件

```bash
# 替換 YOUR_CONTAINER_NAME 為實際的容器名稱
docker cp "c:\Users\Jimmy\Downloads\monitored_stocks0714.json" YOUR_CONTAINER_NAME:/tmp/bullps_data/monitored_stocks.json
```

### 步驟 3: 設置權限

```bash
# 設置文件權限
docker exec YOUR_CONTAINER_NAME chmod 666 /tmp/bullps_data/monitored_stocks.json
```

### 步驟 4: 驗證更新

```bash
# 檢查文件是否存在
docker exec YOUR_CONTAINER_NAME ls -la /tmp/bullps_data/monitored_stocks.json

# 檢查文件內容
docker exec YOUR_CONTAINER_NAME head -n 5 /tmp/bullps_data/monitored_stocks.json
```

### 步驟 5: 重啟應用（可選）

```bash
# 如果需要，重啟容器以確保應用程序載入新數據
docker restart YOUR_CONTAINER_NAME
```

## 🔧 故障排除

### 問題 1: 找不到容器

```bash
# 檢查容器狀態
docker ps -a

# 如果容器停止了，啟動它
docker start YOUR_CONTAINER_NAME
```

### 問題 2: 權限仍然有問題

```bash
# 調用權限修復 API
curl -X POST http://your-zeabur-app-url/api/reset-file-permissions

# 或者手動修復
docker exec YOUR_CONTAINER_NAME /app/fix-manual-override.sh all
```

### 問題 3: 文件沒有生效

```bash
# 檢查應用程序是否使用了正確的路徑
curl http://your-zeabur-app-url/api/file-paths-status

# 重啟應用程序
docker restart YOUR_CONTAINER_NAME
```

## 📈 優勢

使用備份目錄方案的優勢：

1. **✅ 完全避免權限問題**: `/tmp` 目錄始終可寫
2. **✅ 簡化操作流程**: 直接複製到目標位置
3. **✅ 自動環境適配**: 系統自動檢測並使用正確的目錄
4. **✅ 向後兼容**: 本地環境不受影響
5. **✅ 數據持久性**: 容器重啟後數據仍然存在

## 🎉 總結

現在您可以：

1. **直接複製文件到 `/tmp/bullps_data/` 目錄**
2. **不再需要擔心權限問題**
3. **系統會自動使用正確的文件位置**
4. **手動覆蓋文件後立即生效**

這個方案徹底解決了 Zeabur 環境中的只讀文件系統問題，讓您可以輕鬆地手動更新數據文件。
