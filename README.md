# 📈 股票觀察池分析系統

這是一個由資深股票交易員設計的技術分析系統，專門用於找出觀察池中被低估、抄底、有高機率上漲修正的股票。

## 🎯 系統特色

- **Long Days分析**：計算最近多頭訊號距離現在的天數，天數越短表示越早在上漲趨勢時進場
- **多重技術指標**：結合RSI、MACD、布林通道、移動平均線等多種技術分析工具
- **智能進場建議**：根據當前技術指標綜合評估進場機會
- **即時數據更新**：使用Yahoo Finance API獲取最新股票數據
- **簡化配置**：只需輸入股票代號，系統自動獲取股票資訊
- **詳細分析報告**：生成完整的分析報告和CSV檔案

## 🚀 快速開始

### 1. 安裝依賴套件

```bash
pip install -r requirements.txt
```

### 2. 配置觀察池

編輯 `stock_watchlist.json` 檔案，只需要輸入股票代號：

```json
{
  "stocks": [
    "2330.TW",
    "2317.TW",
    "2454.TW",
    "AAPL",
    "TSLA",
    "NVDA"
  ],
  "settings": {
    "analysis_period": 60,
    "rsi_oversold": 30,
    "rsi_overbought": 70
  }
}
```

**股票代號格式說明**：
- 台股：`2330.TW`（台積電）、`2317.TW`（鴻海）
- 美股：`AAPL`（蘋果）、`TSLA`（特斯拉）
- 港股：`0700.HK`（騰訊）、`9988.HK`（阿里巴巴）

### 3. 執行分析

```bash
python stock_analyzer.py
```

或直接雙擊 `run_analysis.bat`

## 📊 技術分析指標

### 多頭訊號檢測條件

系統會檢測以下6種多頭訊號：

1. **黃金交叉**：5日均線穿越20日均線
2. **RSI超賣反轉**：RSI從30以下反轉向上
3. **MACD柱狀圖轉正**：MACD柱狀圖由負轉正
4. **突破布林下軌**：價格突破布林通道下軌
5. **放量上漲**：成交量放大1.5倍以上且價格上漲
6. **動量轉正**：5日價格動量由負轉正

**注意**：必須同時滿足至少2個條件才會被認定為多頭訊號。

### 進場機會評估

系統會根據以下因素綜合評分：

- **RSI評估**：
  - 30-50分：從超賣區反轉但未過熱 (+2分)
  - <30分：超賣區 (+3分)
  - >70分：超買區 (-2分)

- **MACD評估**：
  - MACD為正 (+1分)
  - MACD柱狀圖為正 (+1分)

- **成交量評估**：
  - 成交量放大1.2倍以上 (+1分)

- **價格趨勢評估**：
  - 價格在20日均線之上 (+1分)

**進場建議等級**：
- 4分以上：強烈推薦進場
- 2-3分：建議進場
- 0-1分：觀望
- 負分：不建議進場

## 📁 檔案說明

- `stock_analyzer.py`：主要分析程式
- `stock_watchlist.json`：觀察池配置文件（簡化版）
- `example_simple.json`：範例觀察池配置
- `requirements.txt`：Python依賴套件
- `run_analysis.bat`：Windows批次執行腳本
- `stock_analysis_results.csv`：分析結果輸出檔案

## 📈 輸出結果

### 控制台報告

系統會在控制台顯示：
- 最佳進場機會（Long Days最短的股票）
- 無多頭訊號的股票
- 統計摘要

### CSV檔案

`stock_analysis_results.csv` 包含以下欄位：
- `symbol`：股票代號
- `name`：股票名稱（自動獲取）
- `market`：市場（TWSE/US/HKEX）
- `long_days`：距離最近多頭訊號的天數
- `latest_signal_date`：最新訊號日期
- `current_price`：當前價格
- `entry_opportunity`：進場建議
- `rsi`：當前RSI值
- `volume_ratio`：成交量比率
- `price_change_since_signal`：訊號後價格變化百分比

## 🔧 自訂設定

您可以在 `stock_watchlist.json` 的 `settings` 區塊中調整：

```json
{
  "settings": {
    "analysis_period": 60,        // 分析期間（天）
    "rsi_oversold": 30,          // RSI超賣閾值
    "rsi_overbought": 70         // RSI超買閾值
  }
}
```

## 💡 使用建議

1. **定期更新**：建議每日或每週執行一次分析
2. **結合基本面**：技術分析應與基本面分析結合使用
3. **風險管理**：設定適當的停損點和獲利目標
4. **分散投資**：不要將所有資金投入單一股票
5. **網路連線**：確保網路連線穩定，以獲取最新股票數據

## ⚠️ 免責聲明

本系統僅供學習和研究使用，不構成投資建議。股票投資有風險，請謹慎評估並自負盈虧。

## 🤝 貢獻

歡迎提出改進建議或回報問題！

---

**開發者**：資深股票交易員兼程式設計師  
**版本**：2.0.0  
**更新日期**：2024年 

# 選擇權交易量掃描器

一個簡化的Python程式，用於掃描美股選擇權交易量並自動更新 `stock_watchlist.json` 監控清單。

## 功能特色

- 🔍 **快速掃描**: 掃描主要美股的選擇權交易量
- 📊 **數據分析**: 顯示看漲/看跌選擇權交易量和比率
- 📋 **自動更新**: 自動更新 `stock_watchlist.json` 監控清單
- 💾 **備份保護**: 自動備份原始監控清單文件
- ⚙️ **靈活配置**: 支援自定義股票列表和配置

## 檔案說明

### 主要程式
- `quick_options_scanner.py` - 快速掃描器（推薦使用）
- `options_volume_tracker_v2.py` - 完整版追蹤器
- `options_volume_config.py` - 配置文件

### 執行腳本
- `run_options_scanner.bat` - Windows批次檔案
- `run_options_scanner.ps1` - PowerShell腳本

### 輸出文件
- `stock_watchlist.json` - 監控清單（自動更新）
- `stock_watchlist.json.backup` - 備份文件
- `options_tracker.log` - 日誌文件

## 使用方法

### 方法1: 直接執行Python
```bash
python quick_options_scanner.py
```

### 方法2: 使用批次檔案
```bash
run_options_scanner.bat
```

### 方法3: 使用PowerShell
```powershell
.\run_options_scanner.ps1
```

## 程式流程

1. **輸入股票列表**: 可以自定義要掃描的股票，或使用預設列表
2. **掃描選擇權數據**: 獲取每支股票的選擇權交易量
3. **顯示排行榜**: 按交易量排序顯示結果
4. **更新監控清單**: 選擇是否更新 `stock_watchlist.json`
5. **備份保護**: 自動備份原始文件

## 預設股票列表

程式預設掃描以下20支主要美股：
- 科技股: AAPL, MSFT, GOOGL, AMZN, TSLA, META, NVDA, NFLX, AMD, INTC
- ETF: SPY, QQQ, IWM, VIX, UVXY, TQQQ, SQQQ, SOXL, SOXS, TVIX

## 輸出範例

```
選擇權交易量排行榜
============================================================
生成時間: 2025-06-30 10:42:38
============================================================
 1. SPY
    總交易量: 1,542,309.0
    看漲: 754,310.0 | 看跌: 787,999.0
    看跌/看漲比率: 1.04
    到期日: 2025-06-30

 2. NVDA
    總交易量: 1,071,554.0
    看漲: 640,526.0 | 看跌: 431,028.0
    看跌/看漲比率: 0.67
    到期日: 2025-07-03
```

## 監控清單格式

更新後的 `stock_watchlist.json` 格式：
```json
{
  "stocks": [
    "SPY",
    "NVDA",
    "TSLA",
    "QQQ",
    "AMZN"
  ],
  "settings": {
    "analysis_period": 60,
    "rsi_oversold": 30,
    "rsi_overbought": 70
  }
}
```

## 依賴套件

- `yfinance` - Yahoo Finance數據
- `pandas` - 數據處理
- `requests` - HTTP請求

## 安裝依賴

```bash
pip install yfinance pandas requests
```

## 注意事項

- 程式會自動備份原始的 `stock_watchlist.json` 文件
- 建議在美股交易時間執行以獲得最新數據
- 避免過於頻繁的API請求以避免限制
- 某些股票可能沒有選擇權數據

## 版本歷史

- **v2.0**: 簡化版本，專注於更新監控清單
- **v1.0**: 完整版本，包含多種輸出格式和歷史追蹤 