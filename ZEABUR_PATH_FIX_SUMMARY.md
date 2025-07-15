# 🔧 Zeabur 文件路徑問題修復總結

## 🐛 問題描述

**症狀**: 
- 本地環境: 所有 API 端點正常返回數據 ✅
- Zeabur 環境: `/api/analysis`、`/api/monitored-stocks`、`/api/trade-history` 都返回空值 ❌
- 確認: 所有數據文件 (`analysis_result.json`、`monitored_stocks.json`、`trade_history.json`) 都存在且有數據

**根本原因**: 
容器環境中的文件路徑檢測邏輯錯誤。代碼檢測到 `/app/data` 目錄存在，就假設所有文件都在該目錄下，但實際文件可能在 `/app/` 根目錄。

## ✅ 修復方案

### 1. **動態文件路徑檢測**

**修復前** (`backend/main.py`):
```python
# 簡單的二選一邏輯
if os.path.exists("/app/data"):
    ANALYSIS_PATH = Path("/app/data") / "analysis_result.json"
else:
    ANALYSIS_PATH = BASE_DIR / "analysis_result.json"
```

**修復後** (`backend/main.py`):
```python
def get_file_path(filename):
    """動態檢測文件的實際位置"""
    possible_paths = [
        Path("/app/data") / filename,  # 容器數據目錄
        Path("/app") / filename,       # 容器根目錄
        BASE_DIR / filename,           # 本地根目錄
        BASE_DIR / "backend" / filename  # 本地backend目錄
    ]
    
    for path in possible_paths:
        if path.exists():
            logger.info(f"Found {filename} at: {path}")
            return path
    
    # 回退到默認路徑
    return default_path

# 動態設置所有文件路徑
ANALYSIS_PATH = get_file_path("analysis_result.json")
MONITORED_STOCKS_PATH = get_file_path("monitored_stocks.json")
TRADE_HISTORY_PATH = get_file_path("trade_history.json")
```

### 2. **portfolio_manager.py 同步修復**

**修復前**:
```python
if os.path.exists("/app/data"):
    PORTFOLIO_FILE = "/app/data/monitored_stocks.json"
else:
    PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), 'monitored_stocks.json')
```

**修復後**:
```python
def find_file_path(filename):
    """動態查找文件的實際位置"""
    possible_paths = [
        os.path.join("/app/data", filename),
        os.path.join("/app", filename),
        os.path.join(os.path.dirname(__file__), filename),
        os.path.join(os.path.dirname(__file__), '..', filename)
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return default_path

PORTFOLIO_FILE = find_file_path("monitored_stocks.json")
ANALYSIS_RESULT_FILE = find_file_path("analysis_result.json")
TRADE_HISTORY_FILE = find_file_path("trade_history.json")
```

### 3. **增強健康檢查**

**新的 `/api/health` 端點**:
```json
{
  "status": "healthy",
  "timestamp": "2025-07-15T...",
  "environment": "container",
  "file_paths": {
    "analysis_path": "/app/analysis_result.json",
    "monitored_stocks_path": "/app/backend/monitored_stocks.json",
    "trade_history_path": "/app/backend/trade_history.json"
  },
  "file_exists": {
    "analysis_file": true,
    "monitored_stocks_file": true,
    "trade_history_file": true
  }
}
```

### 4. **測試驗證工具**

創建了 `test_file_paths.py` 來驗證文件檢測邏輯：
- ✅ 本地測試通過
- ✅ 檢測到 200 個分析結果
- ✅ 檢測到 2 個監控股票
- ✅ 檢測到 7 個交易記錄

## 🚀 部署步驟

### 1. **推送修復代碼**
```bash
git add .
git commit -m "修復 Zeabur 文件路徑檢測問題 - 動態路徑檢測"
git push origin main
```

### 2. **等待 Zeabur 重新部署**
- Zeabur 會自動檢測代碼更新
- 重新構建和部署應用

### 3. **驗證修復效果**

**步驟 1**: 檢查健康狀態
```bash
curl https://bullps-v3.zeabur.app/api/health
```

**預期結果**: 所有 `file_exists` 都應該是 `true`

**步驟 2**: 測試 API 端點
```bash
# 分析結果
curl https://bullps-v3.zeabur.app/api/analysis

# 監控股票
curl https://bullps-v3.zeabur.app/api/monitored-stocks

# 交易歷史
curl https://bullps-v3.zeabur.app/api/trade-history
```

**預期結果**: 所有端點都應該返回完整數據

**步驟 3**: 檢查前端界面
- 訪問 `https://bullps-v3.zeabur.app`
- 確認「分析結果摘要」正常顯示
- 確認「股票監控清單」正常顯示
- 確認「歷史交易紀錄」正常顯示

## 🎯 修復原理

### **問題根源**
1. **假設錯誤**: 代碼假設如果 `/app/data` 存在，所有文件就在該目錄
2. **路徑硬編碼**: 沒有動態檢測文件的實際位置
3. **環境差異**: 本地和容器環境的文件結構不同

### **解決方案**
1. **動態檢測**: 按優先級順序檢查多個可能的路徑
2. **實際驗證**: 使用 `path.exists()` 確認文件真實存在
3. **日誌記錄**: 記錄找到文件的實際路徑，便於調試
4. **回退機制**: 如果都找不到，使用合理的默認路徑

### **優勢**
- ✅ **環境無關**: 同一套代碼在本地和容器中都能正常工作
- ✅ **自動適應**: 自動找到文件的實際位置
- ✅ **調試友好**: 詳細的日誌記錄便於問題診斷
- ✅ **向後兼容**: 不影響現有的本地開發環境

## 📊 預期結果

修復後，Zeabur 部署應該：

### **API 端點**
- ✅ `/api/analysis` - 返回完整的股票分析結果
- ✅ `/api/monitored-stocks` - 返回監控股票清單
- ✅ `/api/trade-history` - 返回交易歷史記錄
- ✅ `/api/health` - 顯示正確的文件路徑和狀態

### **前端界面**
- ✅ **分析結果摘要** - 顯示所有分析的股票
- ✅ **股票監控清單** - 顯示正在監控的股票
- ✅ **歷史交易紀錄** - 顯示過往交易記錄

### **系統狀態**
- ✅ **本地開發** - 繼續正常工作
- ✅ **容器部署** - 正確找到所有數據文件
- ✅ **Zeabur 雲端** - 與本地環境行為一致

## 🔍 故障排除

如果修復後仍有問題：

1. **檢查健康端點**: 確認 `file_exists` 都是 `true`
2. **查看 Zeabur 日誌**: 尋找文件路徑相關的日誌信息
3. **手動觸發分析**: 使用 `/api/trigger-analysis` 重新生成數據
4. **比較路徑**: 對比健康檢查中的路徑與實際文件位置

---

**修復完成時間**: 2025-07-15  
**狀態**: ✅ 代碼已修復，等待部署驗證  
**預期**: 完全解決 Zeabur 部署的數據顯示問題
