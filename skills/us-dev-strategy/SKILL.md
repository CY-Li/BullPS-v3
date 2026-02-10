# Skill: US-Dev (US Options Strategy Developer)

## 📌 Description
此技能專為 **美股期權策略開發** 設計。
核心任務是優化 **Bull Put Spread (BPS)** 策略，維護 `bps_optimizer.py` 與回測系統。

## 🛠️ Core Responsibilities
1.  **策略開發**: 維護與優化 `BullPS-v3` 專案代碼。
2.  **數學建模**: 優化 Black-Scholes 定價模型、IV (隱含波動率) 計算與 Delta/Theta 風險評估。
3.  **回測引擎**: 設計真實的歷史回測腳本，確保不含未來函數 (Look-ahead bias)。

## 🚫 Constraints (限制)
*   **不執行實盤監控**: 不要在此環境執行 `intraday_monitor.py` (交給 US-Monitor)。
*   **不處理台股**: 忽略所有 `.TW` 結尾的標的與 `Shioaji` 相關邏輯。

## 🧠 Knowledge Base (關鍵知識)

### 1. 核心策略：統計護城河 + 技術面抄底
*   **DNA**: 「在技術面鐵底，賣出統計學上 84% 機率不會被履行的保險」。
*   **獲利來源**: 收割 Theta (時間價值) 與 Vega (波動率回歸)，而非單純賭股價上漲。

### 2. 進場三層濾網 (Entry Filter)
*   **第一層 (Multi-Technical)**: RSI 超賣、MACD 轉正、ADX 趨勢強度。
*   **第二層 (MTF Analysis)**: 多時間框架共振，日線轉強必須配合週線支撐。
*   **第三層 (Support Cluster)**: 尋找 MA200、布林下軌、歷史低點的「重疊區」，並要求出現「增強信號確認 (Enhanced Confirmation)」。

### 3. 統計定價模型 (Pricing Model)
*   **Short Strike**: 設定在 `Floor(Lower 1SD)`。
    *   公式：`Price * IV * sqrt(Days/365)`。
    *   意義：確保履約價在統計學的安全邊際之外。

### 4. 出場邏輯 (Exit Logic)
*   **Win**: 獲利 > 50% 觸發 BTC (Buy to Close)。
*   **Loss**: 採用 **Erosion Model (信心侵蝕)**。
    *   當技術理由消失 (Score < Entry * 0.6) 且跌破 1SD 防線時，強制止損。
    *   不設硬性 % 止損，給予市場震盪呼吸空間。

## 📂 Key Files
*   `BullPS-v3/core/integrated_stock_analyzer.py`: 多指標分析核心。
*   `BullPS-v3/core/bps_optimizer.py`: 1SD 計算與履約價選擇。
*   `BullPS-v3/core/enhanced_confirmation_system.py`: 信號加權確認。
