# 🔍 Zeabur 前端數據顯示問題診斷指南

## 🎯 問題焦點

**前端到底讀取哪個文件？**

前端通過以下 API 端點讀取數據：
- `/api/analysis` → 分析結果摘要
- `/api/monitored-stocks` → 股票監控清單  
- `/api/trade-history` → 歷史交易紀錄

## 🔍 診斷步驟

### 1. **立即檢查 Zeabur API 狀態**

推送修復代碼後，運行診斷腳本：
```bash
python debug_zeabur_paths.py
```

### 2. **手動檢查關鍵端點**

**步驟 A**: 檢查健康狀態
```bash
curl https://bullps-v3.zeabur.app/api/health
```

**步驟 B**: 檢查調試信息
```bash
curl https://bullps-v3.zeabur.app/api/debug-files
```

**步驟 C**: 檢查前端讀取的 API
```bash
# 分析結果（前端第一個標籤頁）
curl https://bullps-v3.zeabur.app/api/analysis

# 監控股票（前端第二個標籤頁）
curl https://bullps-v3.zeabur.app/api/monitored-stocks

# 交易歷史（前端第三個標籤頁）
curl https://bullps-v3.zeabur.app/api/trade-history
```

### 3. **分析可能的問題**

#### 問題 A: 路徑管理器導入失敗
**症狀**: `/api/health` 顯示 "Path manager failed"
**解決**: 代碼已添加回退機制

#### 問題 B: 文件路徑不一致
**症狀**: `/api/debug-files` 顯示文件存在但 API 返回空
**解決**: 檢查實際使用的路徑

#### 問題 C: 前端緩存問題
**症狀**: API 返回數據但前端不顯示
**解決**: 清除瀏覽器緩存，強制刷新

#### 問題 D: 容器環境路徑問題
**症狀**: 本地正常，Zeabur 異常
**解決**: 檢查容器內的實際文件位置

## 🛠️ 修復措施

### **已實施的修復**

1. **回退機制**: 如果路徑管理器失敗，使用原始邏輯
2. **調試端點**: `/api/debug-files` 顯示所有文件位置
3. **詳細日誌**: 記錄實際使用的路徑
4. **錯誤處理**: 改進 API 端點的錯誤處理

### **代碼修復重點**

```python
# backend/main.py - 回退機制
try:
    from backend.path_manager import path_manager
    ANALYSIS_PATH = path_manager.get_analysis_path()
except ImportError:
    # 使用原始路徑邏輯
    if os.path.exists("/app/data"):
        ANALYSIS_PATH = Path("/app/data/analysis_result.json")
    else:
        ANALYSIS_PATH = BASE_DIR / "analysis_result.json"
```

## 📊 預期診斷結果

### **正常情況**
```json
{
  "status": "healthy",
  "path_manager_info": {
    "environment": "container",
    "paths": {
      "analysis_result.json": "/app/data/analysis_result.json",
      "monitored_stocks.json": "/app/data/monitored_stocks.json", 
      "trade_history.json": "/app/data/trade_history.json"
    },
    "file_exists": {
      "analysis_result.json": true,
      "monitored_stocks.json": true,
      "trade_history.json": true
    },
    "file_sizes": {
      "analysis_result.json": 319230,
      "monitored_stocks.json": 1024,
      "trade_history.json": 2048
    }
  }
}
```

### **問題情況**
```json
{
  "path_manager_info": {
    "error": "Path manager failed: ...",
    "fallback_paths": {
      "analysis": "/app/data/analysis_result.json",
      "monitored_stocks": "/app/data/monitored_stocks.json",
      "trade_history": "/app/data/trade_history.json"
    },
    "fallback_exists": {
      "analysis": false,
      "monitored_stocks": false, 
      "trade_history": false
    }
  }
}
```

## 🎯 解決方案

### **如果 API 返回空數據**

1. **檢查文件位置**:
   ```bash
   curl https://bullps-v3.zeabur.app/api/debug-files
   ```

2. **手動觸發分析**:
   ```bash
   curl https://bullps-v3.zeabur.app/api/trigger-analysis
   ```

3. **等待分析完成後重新檢查**:
   ```bash
   curl https://bullps-v3.zeabur.app/api/analysis
   ```

### **如果 API 有數據但前端不顯示**

1. **清除瀏覽器緩存**
2. **硬刷新頁面** (Ctrl+F5)
3. **檢查瀏覽器控制台錯誤**
4. **檢查網絡請求是否成功**

### **如果路徑管理器失敗**

代碼已添加回退機制，會自動使用原始路徑邏輯：
- 容器環境: `/app/data/*.json`
- 本地環境: `backend/*.json`

## 🚀 部署後驗證流程

1. **推送代碼**:
   ```bash
   git add .
   git commit -m "添加路徑診斷和回退機制"
   git push origin main
   ```

2. **等待部署完成** (約 2-3 分鐘)

3. **運行診斷**:
   ```bash
   python debug_zeabur_paths.py
   ```

4. **檢查前端**:
   - 訪問 `https://bullps-v3.zeabur.app`
   - 檢查三個標籤頁是否正常顯示
   - 如果不顯示，清除緩存後重試

5. **如果仍有問題**:
   - 檢查 `/api/debug-files` 的詳細信息
   - 在 Zeabur 控制台查看應用日誌
   - 手動觸發分析並重新檢查

## 📝 常見問題排除

### Q: API 返回數據但前端顯示空白
**A**: 清除瀏覽器緩存，檢查控制台錯誤

### Q: `/api/health` 顯示文件不存在
**A**: 手動觸發 `/api/trigger-analysis` 重新生成文件

### Q: 路徑管理器導入失敗
**A**: 代碼已添加回退機制，會自動使用原始邏輯

### Q: 本地正常但 Zeabur 異常
**A**: 檢查 `/api/debug-files` 確認容器內的實際文件位置

---

**診斷指南創建時間**: 2025-07-15  
**狀態**: 🔄 等待部署後驗證  
**重點**: 確定前端讀取的 API 端點和實際文件位置的對應關係
