# Agent Architecture (Deployed Status)

目前系統已實裝以下多 Agent 架構：

## 1. 🎖️ Commander (指揮官) - *Current*
- **權限**: 全域調度，管理 MEMORY，負責與用戶對話。
- **任務**: 接收指令，派發任務給子 Agent，並彙整報告。

## 2. 🛡️ US-Monitor (美股監控官)
- **定義檔**: `skills/us-monitor/SKILL.md`
- **狀態**: ✅ Ready
- **觸發**: `sessions_spawn(agent='us-monitor', ...)`
- **任務**: 執行盤前掃描 (`scan_bps`)、盤中監控 (`profit_monitor`)。

## 3. 🇺🇸 US-Dev (美股研發官)
- **定義檔**: `skills/us-dev/SKILL.md`
- **狀態**: ✅ Ready
- **觸發**: `sessions_spawn(agent='us-dev', ...)`
- **任務**: 開發 V4 核心、優化演算法、執行回測。

## 4. 🇹🇼 TW-Dev (台股研發官)
- **定義檔**: `skills/tw-dev/SKILL.md`
- **狀態**: ✅ Ready
- **觸發**: `sessions_spawn(agent='tw-dev', ...)`
- **任務**: 維護 TW-Quant-Shioaji 專案。

---
*Updated: 2026-02-06*
