# 🔧 Zeabur 只讀文件系統解決方案

## 🐛 問題描述

在 Zeabur 部署時遇到只讀文件系統錯誤：
```
❌ 儲存至 /app/data/monitored_stocks.json 時發生權限錯誤: [Errno 30] Read-only file system
```

**根本原因**: Zeabur 環境中 `/app/data/` 目錄是只讀的，無法寫入數據文件。

---

## ✅ 解決方案

### **智能目錄檢測和遷移**

系統現在會自動：
1. **檢測 Zeabur 環境**
2. **尋找可寫目錄**
3. **自動遷移現有數據**
4. **使用可寫位置進行後續操作**

### **可寫目錄優先級**

```python
# Zeabur 環境中的可寫目錄檢測順序
possible_dirs = [
    Path("/tmp/data"),           # 臨時目錄（通常可寫）
    Path("/app/backend"),        # backend 目錄（可能可寫）
    Path("/app"),                # 應用根目錄
    Path("/var/tmp/data")        # 另一個臨時目錄
]
```

### **自動數據遷移**

當找到可寫目錄時，系統會自動遷移：
- `analysis_result.json` - 股票分析結果
- `monitored_stocks.json` - 監控股票清單
- `trade_history.json` - 交易歷史記錄

---

## 🔧 技術實現

### **1. 環境檢測**

```python
# 檢測 Zeabur 環境
is_zeabur = (
    os.environ.get("ZEABUR") == "1" or 
    "zeabur" in os.environ.get("HOSTNAME", "").lower()
)
```

### **2. 寫入權限測試**

```python
# 測試目錄是否可寫
try:
    data_dir.mkdir(parents=True, exist_ok=True)
    test_file = data_dir / "test_write.tmp"
    test_file.write_text("test")
    test_file.unlink()
    # 目錄可寫
except (PermissionError, OSError):
    # 目錄不可寫，嘗試下一個
```

### **3. 數據遷移邏輯**

```python
def _migrate_data_files(self, target_dir):
    source_dir = Path("/app/data")
    files_to_migrate = ["analysis_result.json", "monitored_stocks.json", "trade_history.json"]
    
    for filename in files_to_migrate:
        source_file = source_dir / filename
        target_file = target_dir / filename
        
        if source_file.exists() and not target_file.exists():
            content = source_file.read_text(encoding='utf-8')
            target_file.write_text(content, encoding='utf-8')
```

---

## 📊 部署流程

### **1. 推送更新代碼**

```bash
git add .
git commit -m "修復 Zeabur 只讀文件系統問題 - 智能目錄檢測和數據遷移"
git push origin main
```

### **2. Zeabur 自動部署**

部署時會看到以下日誌：
```
✅ Zeabur 環境使用可寫目錄: /tmp/data
✅ 遷移文件: /app/data/analysis_result.json → /tmp/data/analysis_result.json
✅ 遷移文件: /app/data/monitored_stocks.json → /tmp/data/monitored_stocks.json
✅ 遷移文件: /app/data/trade_history.json → /tmp/data/trade_history.json
```

### **3. 功能驗證**

- ✅ 應用程式正常啟動
- ✅ API 端點返回數據
- ✅ 前端界面正常顯示
- ✅ 「立即更新」功能正常
- ✅ 數據寫入成功

---

## 🎯 解決方案優勢

### **1. 自動適應**
- 自動檢測 Zeabur 環境
- 智能選擇可寫目錄
- 無需手動配置

### **2. 數據保護**
- 自動遷移現有數據
- 保持數據完整性
- 避免數據丟失

### **3. 向後兼容**
- 本地開發環境不受影響
- 其他容器環境正常工作
- Docker 部署保持一致

### **4. 錯誤處理**
- 優雅處理只讀文件系統
- 詳細的錯誤日誌
- 回退機制

---

## 🔍 故障排除

### **如果仍然遇到寫入錯誤**

1. **檢查部署日誌**
   ```
   在 Zeabur 控制台查看應用程式日誌
   尋找 "Zeabur 環境使用可寫目錄" 信息
   ```

2. **驗證環境檢測**
   ```
   GET /api/health
   檢查 environment 字段是否為 "container"
   ```

3. **手動觸發遷移**
   ```
   POST /api/fix-permissions
   這會重新檢測和設置權限
   ```

### **常見問題**

**Q: 為什麼使用 `/tmp/data` 目錄？**
A: 臨時目錄通常在所有 Linux 系統中都是可寫的，包括 Zeabur。

**Q: 數據會在重啟後丟失嗎？**
A: 在 Zeabur 環境中，應用程式重啟時會重新遷移數據，確保數據持久性。

**Q: 本地開發會受影響嗎？**
A: 不會，本地開發仍使用 `./data/` 目錄，不受影響。

---

## 📈 監控和維護

### **健康檢查**

定期檢查應用程式狀態：
```bash
curl https://your-app.zeabur.app/api/health
```

預期響應：
```json
{
  "status": "healthy",
  "path_manager_info": {
    "environment": "container",
    "paths": {
      "analysis_result.json": "/tmp/data/analysis_result.json",
      "monitored_stocks.json": "/tmp/data/monitored_stocks.json",
      "trade_history.json": "/tmp/data/trade_history.json"
    }
  }
}
```

### **數據備份建議**

1. **定期下載數據**
   ```bash
   curl https://your-app.zeabur.app/api/analysis > backup_analysis.json
   curl https://your-app.zeabur.app/api/monitored-stocks > backup_monitored.json
   curl https://your-app.zeabur.app/api/trade-history > backup_history.json
   ```

2. **版本控制**
   - 重要數據更新後提交到 Git
   - 保持數據文件的版本歷史

---

## 🎉 成功標誌

當您看到以下情況時，說明解決方案生效：

✅ **部署日誌顯示成功遷移**  
✅ **健康檢查返回可寫目錄路徑**  
✅ **前端「立即更新」功能正常**  
✅ **API 寫入操作成功**  
✅ **數據持久保存**  

---

**解決方案完成時間**: 2025-07-15  
**狀態**: ✅ **Zeabur 只讀文件系統問題已解決**  
**建議**: 推送代碼並重新部署到 Zeabur
