# 📈 BullPS-v3: 全方位股票分析與交易策略平台

BullPS-v3 是一個全端網頁應用程式，旨在提供一個從股票篩選、進場時機分析、持倉管理到策略回測的完整解決方案。此系統專為技術分析交易者設計，利用多層次的數據分析與可視化儀表板，輔助使用者做出更精確的交易決策。

## 🏛️ 系統架構

本平台採用現代化的前後端分離架構：

-   **前端 (Frontend)**：使用 **React** 和 **TypeScript** 建構，並透過 **Vite** 進行打包。UI 組件庫為 **Material-UI (MUI)**。前端提供一個互動式儀表板，用於展示分析結果、管理持倉、執行回測並視覺化數據。
-   **後端 (Backend)**：使用 **Python** 和 **FastAPI** 框架打造，透過 **Uvicorn** 伺服器運行。後端負責處理數據分析、執行排程任務、管理投資組合，並透過 RESTful API 將數據提供給前端。
-   **分析核心 (Analysis Core)**：由一系列強大的 Python 模組組成，包括：
    -   `integrated_stock_analyzer.py`: 核心分析引擎，整合數十種技術指標。
    -   `multi_timeframe_analyzer.py`: 多時間框架分析器（日、週、月），確保趨勢一致性。
    -   `enhanced_confirmation_system.py`: 增強信號確認系統，提高進場可靠性。
    -   `portfolio_manager.py`: 投資組合與持倉管理器，包含智能停損/停利邏輯。
    -   `backtester.py`: 策略回測引擎，用於驗證策略的歷史績效。
-   **部署 (Deployment)**：專案已使用 **Docker** 進行容器化，並透過 `zeabur.toml` 設定檔，可一鍵部署至 **Zeabur** 平台。

## ✨ 核心功能

-   **互動式網頁儀表板**：提供清晰的數據可視化介面，取代複雜的命令列操作。
-   **自動化分析流程**：一鍵觸發或每日定時（預設為台北時間早上6點）執行完整的股票分析、持倉檢查與報告生成。
-   **進階多指標分析**：整合 RSI, MACD, KD, SAR, Bollinger Bands, OBV, ADX 等數十種技術指標，計算綜合評分與進場信心度。
-   **多時間框架分析 (Multi-Timeframe)**：同時分析日線、週線、月線圖表，確保在主要趨勢下的短期交易機會，大幅提高勝率。
-   **策略回測引擎**：內建回測功能，可針對指定股票與時間區間，驗證系統策略的歷史績效，並提供勝率、總盈虧、盈虧比等關鍵指標。
-   **投資組合管理**：
    -   自動追蹤已進場的股票 (`monitored_stocks.json`)。
    -   基於智能 SAR 移動停損和出場信心度模型，自動評估出場時機。
    -   自動記錄已平倉的交易至 `trade_history.json`。
-   **數據導入與匯出**：支援 JSON 格式的持倉數據和交易歷史的導入與匯出，方便用戶管理和備份自己的數據。
-   **RESTful API**：提供一系列 API 端點，方便進行二次開發或整合。

## 🛠️ 技術堆疊

-   **前端**: React, TypeScript, Vite, Material-UI (MUI), Axios
-   **後端**: Python, FastAPI, Uvicorn
-   **數據分析**: Pandas, NumPy, yfinance
-   **排程任務**: APScheduler
-   **容器化**: Docker
-   **部署平台**: Zeabur

## 📂 專案結構

```
BullPS-v3/
├── frontend/         # React 前端應用程式
│   ├── src/
│   │   └── App.tsx   # 主要 UI 組件與邏輯
│   └── package.json  # 前端依賴
├── backend/          # FastAPI 後端應用程式
│   ├── main.py       # API 端點與主要邏輯
│   ├── portfolio_manager.py # 投資組合與出場邏輯
│   └── path_manager.py      # 統一檔案路徑管理
├── .bmad-core/       # BMad Method 核心文件
├── web-bundles/      # BMad Method 網頁資源
├── .gemini/          # Gemini CLI 設定
├── backtester.py     # 策略回測引擎
├── integrated_stock_analyzer.py # 核心整合分析器
├── multi_timeframe_analyzer.py  # 多時間框架分析器
├── enhanced_confirmation_system.py # 增強信號確認系統
├── requirements.txt  # Python 依賴
├── Dockerfile        # Docker 容器設定
└── zeabur.toml       # Zeabur 部署設定
```

## 🚀 安裝與啟動

### 1. 環境準備

-   安裝 [Python 3.10+](https://www.python.org/)
-   安裝 [Node.js 18+](https://nodejs.org/)

### 2. 後端設定

在專案根目錄下，安裝 Python 依賴：

```bash
pip install -r requirements.txt
```

### 3. 前端設定

進入 `frontend` 目錄，安裝 Node.js 依賴：

```bash
cd frontend
npm install
```

### 4. 啟動應用程式

你需要開啟**兩個**終端視窗：

1.  **啟動後端伺服器** (在專案根目錄)：
    ```bash
    uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
    ```

2.  **啟動前端開發伺服器** (在 `frontend` 目錄)：
    ```bash
    cd frontend
    npm run dev
    ```

啟動成功後，在瀏覽器中開啟 `http://localhost:5173` 即可訪問網頁儀表板。

## 🖥️ 使用說明

### 網頁儀表板

-   **分析結果摘要**：顯示最新一輪分析後，評分最高的潛力股票。
-   **股票監控清單**：顯示已進場並正在追蹤的股票。
-   **歷史交易紀錄**：顯示所有已平倉的交易及其損益。
-   **回測勝率**：
    1.  輸入想回測的股票代號和時間區間。
    2.  點擊「開始回測」按鈕。
    3.  系統將即時顯示回測過程日誌與最終的績效報告。
-   **立即更新**：點擊此按鈕可手動觸發一次完整的分析流程。
-   **數據導入/匯出**：在「股票監OK清單」和「歷史交易紀錄」頁籤中，可使用 JSON 格式導入或匯出您的個人數據。

### 配置文件

-   `stock_watchlist.json`: 編輯此文件以設定您想分析的股票觀察清單。

## ⚠️ 免責聲明

本系統僅供學習和研究使用，不構成任何投資建議。所有分析結果與回測數據僅為歷史資料的模擬，不保證未來表現。股票投資有極高風險，請謹慎評估並自負盈虧。

---
**版本**: 3.0.0  
**更新日期**: 2025-10-03