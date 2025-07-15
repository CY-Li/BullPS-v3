# 🔍 Zeabur 部署問題診斷指南

## 🐛 問題描述

本地端 `/api/analysis` 正常返回數據，但 Zeabur 部署後返回空值：
- 本地: `http://localhost:8080/api/analysis` ✅ 正常
- Zeabur: `https://bullps-v3.zeabur.app/api/analysis` ❌ 空值

## 🔍 診斷步驟

### 1. **檢查健康狀態**
訪問: `https://bullps-v3.zeabur.app/api/health`

預期返回信息：
```json
{
  "status": "healthy",
  "timestamp": "2025-07-15T...",
  "environment": "container",
  "analysis_path": "/app/data/analysis_result.json",
  "analysis_file_exists": false,
  "data_dir_exists": true,
  "static_dir_exists": true,
  "static_dir_path": "/app/frontend/dist",
  "files_in_static": [...]
}
```

**關鍵檢查點**:
- `environment`: 應該是 "container"
- `analysis_file_exists`: 如果是 `false`，說明分析文件不存在
- `data_dir_exists`: 應該是 `true`

### 2. **觸發分析**
如果 `analysis_file_exists` 為 `false`，需要觸發分析：

**方法 1**: POST 請求
```bash
curl -X POST https://bullps-v3.zeabur.app/api/run-now
```

**方法 2**: GET 請求（測試用）
```bash
curl https://bullps-v3.zeabur.app/api/trigger-analysis
```

**方法 3**: 前端界面
- 訪問 `https://bullps-v3.zeabur.app`
- 點擊「立即更新」按鈕

### 3. **監控分析狀態**
```bash
curl https://bullps-v3.zeabur.app/api/analysis-status
```

預期返回：
```json
{
  "is_running": true,
  "current_stage": "正在分析股票...",
  "progress": 50,
  "message": "分析進行中"
}
```

### 4. **檢查分析結果**
分析完成後再次檢查：
```bash
curl https://bullps-v3.zeabur.app/api/analysis
```

## 🔧 可能的問題和解決方案

### 問題 1: 分析文件不存在
**症狀**: `analysis_file_exists: false`

**原因**: 
- 容器啟動後沒有運行過分析
- 文件路徑配置問題
- 權限問題

**解決方案**:
1. 手動觸發分析（見上述步驟2）
2. 檢查容器日誌是否有錯誤
3. 確認數據目錄權限正確

### 問題 2: 分析運行失敗
**症狀**: 觸發分析後仍然沒有結果

**可能原因**:
- API 限制或網絡問題
- 依賴包缺失
- 內存不足
- 超時問題

**解決方案**:
1. 檢查 Zeabur 日誌
2. 確認所有依賴已正確安裝
3. 檢查內存使用情況
4. 調整超時設置

### 問題 3: 路徑配置問題
**症狀**: `environment` 不是 "container" 或路徑錯誤

**解決方案**:
1. 確認 Dockerfile 正確創建了 `/app/data` 目錄
2. 檢查環境變量設置
3. 重新構建和部署

### 問題 4: 權限問題
**症狀**: 分析運行但無法寫入文件

**解決方案**:
1. 檢查 `/app/data` 目錄權限
2. 確認 appuser 有寫入權限
3. 檢查 docker-entrypoint.sh 是否正確執行

## 🚀 修復步驟

### 立即修復
1. **推送更新的代碼**:
   ```bash
   git add .
   git commit -m "改進 Zeabur 部署診斷和錯誤處理"
   git push origin main
   ```

2. **等待 Zeabur 重新部署**

3. **驗證修復**:
   - 檢查 `/api/health` 端點
   - 觸發分析
   - 確認結果返回

### 深度診斷
如果問題持續存在：

1. **檢查 Zeabur 日誌**:
   - 在 Zeabur 控制台查看應用日誌
   - 尋找錯誤信息和警告

2. **檢查環境差異**:
   - 比較本地和容器環境
   - 確認所有文件路徑正確

3. **測試容器本地運行**:
   ```bash
   docker build -t bullps-v3-test .
   docker run -p 8080:8080 bullps-v3-test
   ```

## 📝 預防措施

### 1. **自動初始化**
確保容器啟動時自動運行一次分析：
- 修改 docker-entrypoint.sh
- 添加啟動後的初始化邏輯

### 2. **健康檢查**
定期檢查應用狀態：
- 設置監控告警
- 定期檢查關鍵端點

### 3. **日誌監控**
改進日誌記錄：
- 添加更詳細的調試信息
- 記錄關鍵操作的執行狀態

## 🎯 預期結果

修復後，Zeabur 部署應該：
- ✅ `/api/health` 顯示正確的環境信息
- ✅ `/api/analysis` 返回完整的分析數據
- ✅ 前端正常顯示分析結果摘要
- ✅ 所有功能與本地環境一致

---

**診斷指南創建時間**: 2025-07-15  
**狀態**: 🔄 待驗證  
**下一步**: 推送代碼並重新部署到 Zeabur
