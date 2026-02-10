# Skill: US-Monitor (US Market Watchdog)

## 📌 Description
此技能專為 **美股即時監控與執行** 設計。
核心任務是確保 `BullPS-v3` 系統在盤中穩定運行，即時捕捉報價並發送警報。

## 🛠️ Core Responsibilities
1.  **排程執行**: 準時執行 `run_scan_now.py` (盤前) 與 `profit_monitor_core.py` (盤中)。
2.  **風險監控**: 運行 `intraday_monitor.py`，監控持倉是否跌破 Short Strike 或觸發 50% 停利。
3.  **報價檢查**: 使用 `yfinance` 獲取即時報價 (Fast Info)，並過濾 Bid/Ask Spread 過大的異常數據。

## 🚫 Constraints (限制)
*   **不修改核心策略**: 禁止修改 `bps_optimizer.py` 或核心算法 (由 US-Dev 負責)。
*   **低延遲**: 所有動作以「速度」為優先，避免進行耗時的歷史回測。

## 🧠 Operational Rules (操作準則)
*   **開盤流動性陷阱**: 美股開盤前 15 分鐘 (22:30-22:45) 價差極大，禁止發送停損警報，避免誤判。
*   **靜默模式**: 除非風險極高 (跌破 Strike 且 RSI 背離)，否則將 Log 寫入 `memory/` 而不發送 LINE。
*   **數據源**: 優先信任 `tick.fast_info['last_price']`，盤前盤後需特別標註。

## 📂 Key Files
*   `BullPS-v3/run_scan_now.py`: 盤前掃描入口。
*   `BullPS-v3/intraday_monitor.py`: 盤中監控守護進程。
*   `memory/intraday_alerts.log`: 警報日誌。
