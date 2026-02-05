# 2026-02-03 研究日誌 (11:06 更新)

## 1. 投資組合診斷結果 (portfolio_diagnostic.py)
- **最新市場敏感度 (Beta)**:
  - AAPL: 1.29 (Corr: 0.77)
  - AMZN: 1.35 (Corr: 0.75)
  - DIS: 1.08 (Corr: 0.67)
- **分析**: 
  - 持倉呈現中高 Beta 特性，AAPL 與 AMZN 與大盤相關性強 (>0.74)。
  - DIS 提供了一定的防禦性 (Beta 1.08, Corr 0.67)。
  - 目前整體組合偏向 Bullish 且具備槓桿屬性。

## 2. 自動停利檢查 (profit_tracker.py)
- **AAPL (2026-03-20)**: 
  - 現價 $270.01, Spread 價值 $0.88。
  - **獲利: 54.6% (已達標)**。
- **AMZN (2026-03-20)**: 
  - 現價 $242.96, Spread 價值 $1.85。
  - **獲利: 7.5% (穩定持倉)**。
- **DIS (2026-03-06)**: 
  - 現價 $104.45, Spread 價值 $0.90。
  - **獲利: -94.6% (虧損中，需注意 100 支撐位)**。

## 3. 下一階段優化方向 (TODO)
- [x] **[已完成]** 實作 `Nearest Strike` 與 `Interpolated Price` 邏輯以精準估算權利金。
- [x] **[已完成]** 在 `monitored_stocks.json` 補齊 `entry_premium` 欄位。
- [ ] **[核心功能]** 修復 `profit_tracker.py` 中 `send_line_message` 的執行路徑問題。
- [ ] **[風險管理]** 針對 DIS 虧損部位，建立「止損/轉倉(Roll)」警示邏輯。
- [ ] **[自動化]** 建立 `watchdog_loop.py` 長期背景執行獲利檢查並限制 API 調用頻率 (避開 429 Error)。
