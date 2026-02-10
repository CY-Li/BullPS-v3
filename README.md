# US-Quant: 美股 Bull Put Spread 量化交易系統

**US-Quant** 是一個專為美股設計的自動化量化交易系統，核心策略為 **Bull Put Spread (多頭賣權價差)**。系統結合了深度技術分析、波動率評估與獨創的「信心侵蝕模型」，旨在高勝率的基礎上追求穩定的現金流。

---

## 核心哲學 (Core Philosophy)

1.  **資本保護 (Protect Capital)**: 永遠先評估風險。透過 BPS 的價差保護機制與嚴格的止損邏輯，限制單筆交易的最大虧損。
2.  **數據驅動 (Data-Driven)**: 拒絕憑感覺交易。所有決策基於 RSI、MACD、SAR、IV Rank 等量化指標。
3.  **理由生存 (Reason Survival)**: 進場理由消失即出場。我們不祈禱股價反彈，只相信當下的數據。

---

## 系統架構 (System Architecture)

```text
/workspace
├── core/                # 策略大腦
│   ├── integrated_stock_analyzer.py  # 綜合技術分析引擎
│   └── bps_optimizer.py              # BPS 履約價優化器
├── tools/               # 執行手臂
│   ├── scan.py                       # 機會掃描器 (Scanner)
│   └── profit_monitor.py             # 獲利與風險監控 (Watchdog)
├── config/              # 系統設定
│   ├── stock_watchlist.json          # 監控標的清單
│   └── monitored_stocks.json         # 當前持倉紀錄
└── memory/              # 歷史記憶 (由 Agent 自動維護)
```

---

## 🛠️ 工具深度解析 (Tools Deep Dive)

### 1. 機會掃描器 (`tools/scan.py`)

這是系統的「眼睛」，負責從數百支股票中篩選出符合 BPS 策略的標的。

#### 使用方式
```bash
python3 tools/scan.py --mode [standard|strict|relaxed] --limit [數量]
```

#### 三種掃描模式 (Modes)

| 模式 | 參數名稱 | 篩選標準 | 適用場景 |
| :--- | :--- | :--- | :--- |
| **標準模式** | `standard` (預設) | Score > 75, Conf > 70 | 平穩市場，尋求高質量標的。 |
| **鐵盾模式** | `strict` (Iron Shield) | Score > 75, Conf > 70, **IV Rank > 20** | 波動市場。強制過濾低 IV 標的，確保權利金夠肥，安全邊際夠大。 |
| **寬鬆模式** | `relaxed` | Score > 50, **IV Rank > 15** | 強力牛市。降低技術指標門檻，捕捉動能強勁但指標過熱的標的。 |

#### 輸出邏輯
掃描器會自動計算最佳的 BPS 組合：
- **Short Strike**: 建議賣出履約價 (通常在支撐位下方)。
- **Long Strike**: 保護履約價。
- **ROI**: 預期回報率 (權利金 / 風險保證金)。

---

### 2. 獲利監控器 (`tools/profit_monitor.py`)

這是系統的「衛兵」，負責 24/7 監看 `config/monitored_stocks.json` 中的持倉。

#### 使用方式
```bash
python3 tools/profit_monitor.py
```

#### 雙重出場機制 (Dual Exit Logic)

1.  **停利出場 (Profit Taking)**:
    *   **目標**: 50% 權利金回收 (50% Max Profit)。
    *   **邏輯**: 當選擇權權利金跌至進場價的 50% 時，Theta 衰減效率降低，建議平倉釋放保證金。

2.  **信心侵蝕出場 (Erosion Model Exit)**:
    *   **核心概念**: 進場時我們基於特定理由 (如: RSI 背離 + 支撐測試)。如果這些理由消失，交易就失效了。
    *   **侵蝕計算**:
        *   價格跌破關鍵均線 (MA20/SAR): 扣分。
        *   動能指標翻空 (MACD 死叉): 扣分。
        *   **Erosion Score**: 當信心度低於 60% (或自定義閾值)，系統會發出「信心崩潰」警報，建議立即止損。

---

## 設定檔說明 (Configuration)

### `config/stock_watchlist.json`
掃描器的目標清單。格式：
```json
{
  "stocks": ["AAPL", "MSFT", "TSLA", ...]
}
```

### `config/monitored_stocks.json`
當前持倉清單 (由 User 或 Agent 手動維護，或未來自動寫入)。格式：
```json
[
  {
    "symbol": "AAPL",
    "short_strike": 150,
    "long_strike": 145,
    "expiry": "2024-12-20",
    "entry_credit": 0.85,
    "entry_date": "2024-11-20",
    "snapshot": { ... } // 進場時的技術指標快照，用於 Erosion 計算
  }
]
```

---

## 快速開始 (Quick Start)

1.  **安裝依賴**:
    ```bash
    pip install pandas numpy yfinance
    ```

2.  **執行掃描 (尋找機會)**:
    ```bash
    # 尋找高質量的 BPS 機會
    python3 tools/scan.py --mode strict
    ```

3.  **執行監控 (檢查持倉)**:
    ```bash
    # 檢查是否該停利或止損
    python3 tools/profit_monitor.py
    ```

---

## 專案大腦 (Project Brain)
更多關於策略細節、參數權重與開發日誌，請參閱根目錄下的 **`PROJECT_BRAIN.md`**。這是 AI Agent (Pi) 的核心記憶庫。
