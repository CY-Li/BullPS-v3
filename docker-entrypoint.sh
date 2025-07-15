#!/bin/bash
set -e

echo "🚀 Starting BullPS-v3 with unified data directory..."

# 確保統一數據目錄存在且有正確權限
echo "📁 Ensuring /app/data directory permissions..."
if [ -d "/app/data" ]; then
    echo "✅ /app/data directory exists"

    # 修復目錄權限 (Zeabur 部署後權限修復)
    echo "🔧 Fixing /app/data directory permissions..."
    if command -v sudo >/dev/null 2>&1; then
        sudo chmod -R 777 /app/data 2>/dev/null && echo "✅ Fixed directory permissions with sudo" || echo "⚠️ Failed to fix permissions with sudo"
        sudo chown -R $(whoami) /app/data 2>/dev/null && echo "✅ Fixed ownership with sudo" || echo "⚠️ Failed to fix ownership with sudo"
    else
        chmod -R 777 /app/data 2>/dev/null && echo "✅ Fixed directory permissions" || echo "⚠️ Failed to fix permissions"
    fi

    # 檢查目錄權限
    if [ -w "/app/data" ]; then
        echo "✅ /app/data directory is writable"
    else
        echo "⚠️  /app/data directory is not writable"
        # 嘗試使用其他方法修復權限
        echo "🔧 Trying alternative permission fix..."
        mkdir -p /app/data 2>/dev/null
        touch /app/data/test_write.tmp 2>/dev/null && echo "✅ Write test successful" || echo "❌ Write test failed"
        rm -f /app/data/test_write.tmp 2>/dev/null
    fi

    # 初始化數據文件（如果不存在）並修復權限
    for file in "monitored_stocks.json" "trade_history.json"; do
        if [ ! -f "/app/data/$file" ]; then
            echo '[]' > "/app/data/$file" 2>/dev/null && echo "✅ Created $file" || echo "❌ Cannot create $file"
        fi
        # 修復文件權限
        chmod 666 "/app/data/$file" 2>/dev/null && echo "✅ Fixed $file permissions" || echo "⚠️ Failed to fix $file permissions"
    done

    if [ ! -f "/app/data/analysis_result.json" ]; then
        echo '{"result": [], "timestamp": "", "analysis_date": "", "total_stocks": 0, "analyzed_stocks": 0}' > /app/data/analysis_result.json 2>/dev/null && echo "✅ Created analysis_result.json" || echo "❌ Cannot create analysis_result.json"
    fi
    # 修復分析結果文件權限
    chmod 666 "/app/data/analysis_result.json" 2>/dev/null && echo "✅ Fixed analysis_result.json permissions" || echo "⚠️ Failed to fix analysis_result.json permissions"

    # 顯示文件狀態
    echo "📊 Data files status:"
    ls -la /app/data/ 2>/dev/null || echo "❌ Cannot list /app/data/"

else
    echo "❌ /app/data directory does not exist"
    # 嘗試創建目錄
    mkdir -p /app/data 2>/dev/null && echo "✅ Created /app/data directory" || echo "❌ Cannot create /app/data directory"
    # 設置權限
    chmod 777 /app/data 2>/dev/null && echo "✅ Set /app/data permissions" || echo "❌ Cannot set /app/data permissions"
fi

echo "✅ Using unified data directory: /app/data"
echo "📊 All components will use the same data files:"
echo "   - Analysis results: /app/data/analysis_result.json"
echo "   - Monitored stocks: /app/data/monitored_stocks.json"
echo "   - Trade history: /app/data/trade_history.json"

echo "🌐 Starting application server..."
exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}
