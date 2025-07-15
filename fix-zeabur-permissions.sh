#!/bin/bash
# 修復 Zeabur 環境中的文件權限問題
# 使用方法: 在 Zeabur 控制台中執行此腳本

set -e

echo "🔧 Zeabur 文件權限修復工具"
echo "=================================="

# 檢查是否在 Zeabur 環境中
if [ -z "$ZEABUR" ] && [[ ! $(hostname) == *zeabur* ]]; then
    echo "⚠️  警告: 此腳本設計用於 Zeabur 環境"
    echo "   如果您確定要在非 Zeabur 環境中運行，請按 Enter 繼續"
    echo "   否則請按 Ctrl+C 取消"
    read -r
fi

# 修復根目錄權限
echo "🔧 修復 /app 根目錄權限..."
chmod -R 777 /app 2>/dev/null && echo "✅ 目錄權限已修復" || echo "❌ 無法修復目錄權限"

# 初始化文件（如果不存在）
echo "📄 確保數據文件存在..."

# monitored_stocks.json
if [ ! -f "/app/monitored_stocks.json" ]; then
    echo '[]' > /app/monitored_stocks.json 2>/dev/null && echo "✅ 已創建 monitored_stocks.json" || echo "❌ 無法創建 monitored_stocks.json"
else
    echo "✅ monitored_stocks.json 已存在"
fi

# trade_history.json
if [ ! -f "/app/trade_history.json" ]; then
    echo '[]' > /app/trade_history.json 2>/dev/null && echo "✅ 已創建 trade_history.json" || echo "❌ 無法創建 trade_history.json"
else
    echo "✅ trade_history.json 已存在"
fi

# analysis_result.json
if [ ! -f "/app/analysis_result.json" ]; then
    echo '{"result": [], "timestamp": "", "analysis_date": "", "total_stocks": 0, "analyzed_stocks": 0}' > /app/analysis_result.json 2>/dev/null && echo "✅ 已創建 analysis_result.json" || echo "❌ 無法創建 analysis_result.json"
else
    echo "✅ analysis_result.json 已存在"
fi

# 修復文件權限
echo "🔧 修復文件權限..."
chmod 666 /app/*.json 2>/dev/null && echo "✅ 文件權限已修復" || echo "❌ 無法修復文件權限"

# 顯示文件狀態
echo "📊 數據文件狀態:"
ls -la /app/*.json 2>/dev/null || echo "❌ 無法列出 /app/*.json 文件"

# 測試文件寫入
echo "🧪 測試文件寫入..."
echo "test" > /app/write_test.tmp 2>/dev/null && echo "✅ 寫入測試成功" || echo "❌ 寫入測試失敗"
rm -f /app/write_test.tmp 2>/dev/null

echo "=================================="
echo "🔍 診斷信息:"
echo "- 用戶: $(whoami)"
echo "- 目錄: $(pwd)"
echo "- 環境變量:"
echo "  ZEABUR=$(echo $ZEABUR)"
echo "  HOSTNAME=$(echo $HOSTNAME)"
echo "  USER=$(echo $USER)"
echo "  HOME=$(echo $HOME)"

echo "=================================="
echo "✅ 權限修復完成"
echo "如果仍然遇到問題，請嘗試以下操作:"
echo "1. 在 Zeabur 控制台中重啟應用"
echo "2. 訪問 API 端點: POST /api/fix-permissions"
echo "3. 聯繫 Zeabur 支持團隊"
