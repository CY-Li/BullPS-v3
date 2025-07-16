#!/bin/bash
set -e

echo "🚀 Starting BullPS-v3..."

# 初始化根目錄數據文件
echo "📁 初始化根目錄數據文件..."

for file in "monitored_stocks.json" "trade_history.json"; do
    if [ ! -f "/app/$file" ]; then
        echo '[]' > "/app/$file" 2>/dev/null && echo "✅ 創建 $file 成功" || echo "❌ 無法創建 $file"
    fi
    # 設置文件權限
    chmod 666 "/app/$file" 2>/dev/null && echo "✅ 設置 $file 權限成功" || echo "⚠️ 設置 $file 權限失敗"
done

if [ ! -f "/app/analysis_result.json" ]; then
    echo '{"result": [], "timestamp": "", "analysis_date": "", "total_stocks": 0, "analyzed_stocks": 0}' > /app/analysis_result.json 2>/dev/null && echo "✅ 創建 analysis_result.json 成功" || echo "❌ 無法創建 analysis_result.json"
fi
# 設置分析結果文件權限
chmod 666 "/app/analysis_result.json" 2>/dev/null && echo "✅ 設置 analysis_result.json 權限成功" || echo "⚠️ 設置 analysis_result.json 權限失敗"

# 顯示文件狀態
echo "📊 數據文件狀態:"
ls -la /app/*.json 2>/dev/null || echo "❌ 無法列出 /app/*.json"

echo "✅ 使用統一根目錄: /app"
echo "📊 所有組件將使用相同的數據文件:"
echo "   - 分析結果: /app/analysis_result.json"
echo "   - 監控股票: /app/monitored_stocks.json"
echo "   - 交易歷史: /app/trade_history.json"

echo "🌐 啟動應用服務器..."
exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}
