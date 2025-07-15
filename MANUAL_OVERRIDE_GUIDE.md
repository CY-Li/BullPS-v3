# 手動覆蓋文件後的權限修復指南

## 問題描述

當您手動覆蓋 Docker 容器中的數據文件（如 `monitored_stocks.json`）時，文件的所有者和權限會發生變化，導致應用程序無法寫入這些文件。

## 為什麼會發生這個問題？

1. **文件所有者變更**: 手動覆蓋文件時，文件的所有者可能變為 `root` 或其他用戶
2. **權限重置**: 新文件的權限可能不允許應用程序用戶寫入
3. **容器用戶限制**: 應用程序運行在特定用戶下，無法修改其他用戶擁有的文件

## 解決方案

### 方法 1: 使用 API 端點修復（推薦）

```bash
# 重置文件權限
curl -X POST http://your-app-url/api/reset-file-permissions

# 檢查文件狀態
curl http://your-app-url/api/file-paths-status
```

### 方法 2: 使用修復腳本

```bash
# 在容器內執行
/app/fix-manual-override.sh all

# 或修復特定文件
/app/fix-manual-override.sh /app/monitored_stocks.json
```

### 方法 3: 手動命令修復

```bash
# 進入容器
docker exec -it your-container-name bash

# 修復所有者
chown appuser:appuser /app/*.json

# 修復權限
chmod 666 /app/*.json

# 測試寫入
echo "test" > /app/test.tmp && rm /app/test.tmp
```

### 方法 4: 使用備份目錄（自動）

系統會自動檢測權限問題並切換到備份目錄：
- 主要目錄: `/app/`
- 備份目錄: `/tmp/bullps_data/`

## 預防措施

### 1. 正確的文件覆蓋方式

**❌ 錯誤方式:**
```bash
# 直接覆蓋會導致權限問題
docker cp monitored_stocks.json container:/app/monitored_stocks.json
```

**✅ 正確方式:**
```bash
# 複製後修復權限
docker cp monitored_stocks.json container:/app/monitored_stocks.json
docker exec container /app/fix-manual-override.sh /app/monitored_stocks.json
```

### 2. 使用 API 更新數據

**推薦使用 API 端點更新數據，而不是直接覆蓋文件:**

```bash
# 通過 API 更新監控股票
curl -X POST http://your-app-url/api/monitored-stocks \
  -H "Content-Type: application/json" \
  -d @monitored_stocks.json
```

### 3. 設置正確的文件權限

在 Dockerfile 中確保正確的權限設置：

```dockerfile
# 設置文件所有者和權限
RUN chown -R appuser:appuser /app && \
    chmod 666 /app/*.json
```

## 自動修復機制

系統已經實施了多層自動修復機制：

### 1. 路徑管理器
- 自動檢測權限問題
- 智能切換到備份路徑
- 保持數據一致性

### 2. 文件保存函數
- 多重權限修復策略
- 自動備份機制
- 優雅的錯誤處理

### 3. API 端點
- `/api/reset-file-permissions`: 重置文件權限
- `/api/file-paths-status`: 檢查文件狀態
- `/api/fix-permissions`: 全面權限診斷和修復

## 監控和診斷

### 檢查當前狀態
```bash
# 檢查文件權限
ls -la /app/*.json
ls -la /tmp/bullps_data/*.json

# 檢查文件所有者
stat /app/monitored_stocks.json

# 測試寫入權限
touch /app/test.tmp && rm /app/test.tmp
```

### 查看應用程序日誌
```bash
# 查看權限相關日誌
docker logs your-container-name | grep -i permission
docker logs your-container-name | grep -i "主要路徑\|備份路徑"
```

## 常見錯誤和解決方案

### 錯誤 1: Permission denied
```
❌ 儲存至 /app/monitored_stocks.json 時發生權限錯誤: [Errno 13] Permission denied
```

**解決方案:**
```bash
curl -X POST http://your-app-url/api/reset-file-permissions
```

### 錯誤 2: Operation not permitted
```
⚠️ 複製文件失敗: [Errno 1] Operation not permitted
```

**解決方案:**
```bash
# 使用 sudo 修復
docker exec your-container-name sudo chown appuser:appuser /app/*.json
docker exec your-container-name sudo chmod 666 /app/*.json
```

### 錯誤 3: 文件不存在
```
❌ 文件不存在: /app/monitored_stocks.json
```

**解決方案:**
```bash
# 重新創建文件
echo '[]' > /app/monitored_stocks.json
chmod 666 /app/monitored_stocks.json
```

## 最佳實踐

1. **使用 API 更新數據**: 避免直接覆蓋文件
2. **定期檢查權限**: 使用監控端點檢查文件狀態
3. **備份重要數據**: 系統會自動維護備份，但建議定期手動備份
4. **監控日誌**: 關注權限相關的日誌信息
5. **測試修復**: 在生產環境中應用修復前，先在測試環境中驗證

## 總結

通過實施多層權限修復機制，系統現在能夠：
- ✅ 自動檢測和修復權限問題
- ✅ 智能切換到備份路徑
- ✅ 提供多種修復工具和方法
- ✅ 保持數據一致性和可用性

即使在手動覆蓋文件的情況下，系統也能快速恢復正常運行。
