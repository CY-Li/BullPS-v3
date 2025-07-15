#!/bin/bash
set -e

echo "🚀 Starting BullPS-v3 with unified data directory..."

# 確保統一數據目錄存在
mkdir -p /app/data 2>/dev/null || true

# 初始化統一數據文件（如果不存在）
if [ ! -f "/app/data/monitored_stocks.json" ]; then
    echo '[]' > /app/data/monitored_stocks.json 2>/dev/null || echo "⚠️  Cannot write to /app/data/monitored_stocks.json"
fi

if [ ! -f "/app/data/trade_history.json" ]; then
    echo '[]' > /app/data/trade_history.json 2>/dev/null || echo "⚠️  Cannot write to /app/data/trade_history.json"
fi

if [ ! -f "/app/data/analysis_result.json" ]; then
    echo '{"result": [], "timestamp": "", "analysis_date": "", "total_stocks": 0, "analyzed_stocks": 0}' > /app/data/analysis_result.json 2>/dev/null || echo "⚠️  Cannot write to /app/data/analysis_result.json"
fi

# 確保文件權限正確（修復所有者問題）
echo "🔧 Fixing file permissions..."
chown appuser:appuser /app/data/*.json 2>/dev/null || echo "⚠️  Cannot change ownership (may be read-only)"
chmod 664 /app/data/*.json 2>/dev/null || echo "⚠️  Cannot change permissions (may be read-only)"

echo "📁 Unified data directory status:"
ls -la /app/data/ 2>/dev/null || echo "❌ /app/data/ not accessible"

echo "✅ Using unified data directory: /app/data"
echo "📊 All components will use the same data files:"
echo "   - Analysis results: /app/data/analysis_result.json"
echo "   - Monitored stocks: /app/data/monitored_stocks.json"
echo "   - Trade history: /app/data/trade_history.json"

echo "🌐 Starting application server..."
exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}
