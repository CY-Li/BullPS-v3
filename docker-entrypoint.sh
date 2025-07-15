#!/bin/bash
set -e

echo "🚀 Starting BullPS-v3 with unified data directory..."

# 確保統一數據目錄存在且有正確權限
echo "📁 Ensuring /app/data directory permissions..."
if [ -d "/app/data" ]; then
    echo "✅ /app/data directory exists"

    # 檢查目錄權限
    if [ -w "/app/data" ]; then
        echo "✅ /app/data directory is writable"
    else
        echo "⚠️  /app/data directory is not writable"
    fi

    # 初始化數據文件（如果不存在）
    if [ ! -f "/app/data/monitored_stocks.json" ]; then
        echo '[]' > /app/data/monitored_stocks.json 2>/dev/null && echo "✅ Created monitored_stocks.json" || echo "❌ Cannot create monitored_stocks.json"
    fi

    if [ ! -f "/app/data/trade_history.json" ]; then
        echo '[]' > /app/data/trade_history.json 2>/dev/null && echo "✅ Created trade_history.json" || echo "❌ Cannot create trade_history.json"
    fi

    if [ ! -f "/app/data/analysis_result.json" ]; then
        echo '{"result": [], "timestamp": "", "analysis_date": "", "total_stocks": 0, "analyzed_stocks": 0}' > /app/data/analysis_result.json 2>/dev/null && echo "✅ Created analysis_result.json" || echo "❌ Cannot create analysis_result.json"
    fi

    # 顯示文件狀態
    echo "📊 Data files status:"
    ls -la /app/data/ 2>/dev/null || echo "❌ Cannot list /app/data/"

else
    echo "❌ /app/data directory does not exist"
fi

echo "✅ Using unified data directory: /app/data"
echo "📊 All components will use the same data files:"
echo "   - Analysis results: /app/data/analysis_result.json"
echo "   - Monitored stocks: /app/data/monitored_stocks.json"
echo "   - Trade history: /app/data/trade_history.json"

echo "🌐 Starting application server..."
exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}
