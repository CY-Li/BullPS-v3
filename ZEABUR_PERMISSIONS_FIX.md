# 🔧 Zeabur 文件權限問題解決方案

## 🐛 問題描述

在 Zeabur 部署後，手動覆蓋 JSON 文件（如 `monitored_stocks.json`、`trade_history.json`、`analysis_result.json`）會導致權限錯誤：

```
❌ 儲存至 /app/data/monitored_stocks.json 時發生權限錯誤: [Errno 13] Permission denied: '/app/data/monitored_stocks.json'
```

**根本原因**: 手動覆蓋文件後，文件權限被重置，導致應用程式用戶 `appuser` 無法寫入。

---

## ✅ 解決方案

本次更新提供了多層次的權限修復機制，確保在 Zeabur 環境中 `/app/data` 目錄始終可寫。

### **1. 容器啟動時自動修復**

容器啟動時會自動：
- 檢測 Zeabur 環境
- 修復 `/app/data` 目錄權限（設為 777）
- 修復所有 JSON 文件權限（設為 666）
- 測試文件寫入權限

### **2. API 端點修復**

提供了專門的 API 端點用於手動修復權限：
```
POST /api/fix-permissions
```

### **3. 手動修復腳本**

提供了專門的修復腳本：
```bash
./fix-zeabur-permissions.sh
```

---

## 🚀 使用方法

### **方法 1: 重新部署應用**

最簡單的方法是重新部署應用，讓容器啟動時自動修復權限：

1. 在 Zeabur 控制台中重新部署應用
2. 查看日誌確認權限修復成功

### **方法 2: 使用 API 修復**

如果不想重新部署，可以使用 API 修復權限：

```bash
curl -X POST https://your-app.zeabur.app/api/fix-permissions
```

或在瀏覽器中訪問：
```
https://your-app.zeabur.app/api/fix-permissions
```

### **方法 3: 使用修復腳本**

如果有 Zeabur 控制台的 Shell 訪問權限：

```bash
cd /app
./fix-zeabur-permissions.sh
```

---

## 🔍 手動覆蓋文件後的處理流程

如果需要手動覆蓋 JSON 文件，請按照以下步驟操作：

1. **覆蓋文件**
   ```bash
   # 例如，覆蓋監控股票文件
   cp your_monitored_stocks.json /app/data/monitored_stocks.json
   ```

2. **修復權限**
   ```bash
   # 方法 1: 使用修復腳本
   ./fix-zeabur-permissions.sh
   
   # 方法 2: 直接修復權限
   chmod 666 /app/data/*.json
   chmod 777 /app/data
   ```

3. **驗證權限**
   ```bash
   # 檢查文件權限
   ls -la /app/data/
   
   # 測試寫入
   echo "test" > /app/data/write_test.tmp && echo "Success" || echo "Failed"
   rm -f /app/data/write_test.tmp
   ```

---

## 📊 技術實現

### **1. Dockerfile 修改**

```dockerfile
# 確保 /app/data 目錄完全可寫（Zeabur 權限修復）
RUN chown -R appuser:appuser /app && \
    chmod -R 755 /app && \
    chmod 777 /app/data && \
    chmod 666 /app/data/*.json
```

### **2. 啟動腳本增強**

```bash
# 修復目錄權限 (Zeabur 部署後權限修復)
chmod -R 777 /app/data 2>/dev/null
chmod 666 /app/data/*.json 2>/dev/null
```

### **3. 路徑管理器增強**

```python
# 在 Zeabur 環境中嘗試修復權限
if is_zeabur:
    print("🔧 檢測到 Zeabur 環境，嘗試修復權限...")
    self._fix_zeabur_permissions(data_dir)
```

---

## 🔧 故障排除

### **如果仍然遇到權限問題**

1. **檢查日誌**
   - 查看 Zeabur 控制台中的應用日誌
   - 尋找權限相關的錯誤信息

2. **檢查文件權限**
   ```bash
   ls -la /app/data/
   ```
   - 確保目錄權限為 `drwxrwxrwx` (777)
   - 確保文件權限為 `-rw-rw-rw-` (666)

3. **手動修復權限**
   ```bash
   chmod -R 777 /app/data
   chmod 666 /app/data/*.json
   ```

4. **檢查用戶**
   ```bash
   whoami
   ```
   - 確保應用以 `appuser` 運行

5. **檢查磁盤空間**
   ```bash
   df -h
   ```
   - 確保有足夠的磁盤空間

---

## 📈 最佳實踐

### **1. 避免直接覆蓋文件**

盡量使用應用程式的 API 或界面更新數據，而不是直接覆蓋文件。

### **2. 使用 API 備份和恢復**

使用 API 端點備份和恢復數據：
```
GET /api/monitored-stocks  # 備份
POST /api/update-monitored-stocks  # 恢復
```

### **3. 定期備份**

定期備份重要數據文件，特別是在重大更新前。

---

## 🎉 成功標誌

當您看到以下情況時，說明解決方案生效：

✅ **啟動日誌顯示權限修復成功**  
✅ **API 寫入操作成功**  
✅ **手動覆蓋文件後應用仍能正常寫入**  
✅ **前端「立即更新」功能正常**  

---

**解決方案完成時間**: 2023-07-20  
**狀態**: ✅ **Zeabur 文件權限問題已解決**
