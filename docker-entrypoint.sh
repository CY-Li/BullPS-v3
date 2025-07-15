#!/bin/bash
set -e

echo "🚀 Starting BullPS-v3 with unified root directory..."

# 確保根目錄數據文件存在且有正確權限
echo "📁 Ensuring /app root directory permissions..."

# 修復目錄權限 (Zeabur 部署後權限修復)
echo "🔧 Fixing /app directory permissions..."
if command -v sudo >/dev/null 2>&1; then
    sudo chmod -R 777 /app 2>/dev/null && echo "✅ Fixed directory permissions with sudo" || echo "⚠️ Failed to fix permissions with sudo"
    sudo chown -R $(whoami) /app 2>/dev/null && echo "✅ Fixed ownership with sudo" || echo "⚠️ Failed to fix ownership with sudo"
else
    chmod -R 777 /app 2>/dev/null && echo "✅ Fixed directory permissions" || echo "⚠️ Failed to fix permissions"
fi

# 檢查目錄權限
if [ -w "/app" ]; then
    echo "✅ /app directory is writable"
else
    echo "⚠️  /app directory is not writable"
    # 嘗試使用其他方法修復權限
    echo "🔧 Trying alternative permission fix..."
    touch /app/test_write.tmp 2>/dev/null && echo "✅ Write test successful" || echo "❌ Write test failed"
    rm -f /app/test_write.tmp 2>/dev/null
fi

# 初始化數據文件（如果不存在）並修復權限
for file in "monitored_stocks.json" "trade_history.json"; do
    if [ ! -f "/app/$file" ]; then
        echo '[]' > "/app/$file" 2>/dev/null && echo "✅ Created $file" || echo "❌ Cannot create $file"
    fi
    # 修復文件權限
    chmod 666 "/app/$file" 2>/dev/null && echo "✅ Fixed $file permissions" || echo "⚠️ Failed to fix $file permissions"
done

if [ ! -f "/app/analysis_result.json" ]; then
    echo '{"result": [], "timestamp": "", "analysis_date": "", "total_stocks": 0, "analyzed_stocks": 0}' > /app/analysis_result.json 2>/dev/null && echo "✅ Created analysis_result.json" || echo "❌ Cannot create analysis_result.json"
fi
# 修復分析結果文件權限
chmod 666 "/app/analysis_result.json" 2>/dev/null && echo "✅ Fixed analysis_result.json permissions" || echo "⚠️ Failed to fix analysis_result.json permissions"

# 確保備份目錄存在
echo "📁 Ensuring backup directory exists..."
mkdir -p /tmp/bullps_data 2>/dev/null && echo "✅ Created backup directory" || echo "❌ Cannot create backup directory"
chmod -R 777 /tmp/bullps_data 2>/dev/null && echo "✅ Fixed backup directory permissions" || echo "⚠️ Failed to fix backup directory permissions"

# 初始化備份文件（如果不存在）
for file in "monitored_stocks.json" "trade_history.json"; do
    if [ ! -f "/tmp/bullps_data/$file" ]; then
        echo '[]' > "/tmp/bullps_data/$file" 2>/dev/null && echo "✅ Created backup $file" || echo "❌ Cannot create backup $file"
    fi
    # 修復文件權限
    chmod 666 "/tmp/bullps_data/$file" 2>/dev/null && echo "✅ Fixed backup $file permissions" || echo "⚠️ Failed to fix backup $file permissions"
done

if [ ! -f "/tmp/bullps_data/analysis_result.json" ]; then
    echo '{"result": [], "timestamp": "", "analysis_date": "", "total_stocks": 0, "analyzed_stocks": 0}' > /tmp/bullps_data/analysis_result.json 2>/dev/null && echo "✅ Created backup analysis_result.json" || echo "❌ Cannot create backup analysis_result.json"
fi
# 修復備份分析結果文件權限
chmod 666 "/tmp/bullps_data/analysis_result.json" 2>/dev/null && echo "✅ Fixed backup analysis_result.json permissions" || echo "⚠️ Failed to fix backup analysis_result.json permissions"

# 顯示文件狀態
echo "📊 Data files status:"
echo "Main directory (/app):"
ls -la /app/*.json 2>/dev/null || echo "❌ Cannot list /app/*.json"

echo "Backup directory (/tmp/bullps_data):"
ls -la /tmp/bullps_data/*.json 2>/dev/null || echo "❌ Cannot list /tmp/bullps_data/*.json"

echo "✅ Using unified root directory: /app"
echo "📊 All components will use the same data files:"
echo "   - Analysis results: /app/analysis_result.json (Backup: /tmp/bullps_data/analysis_result.json)"
echo "   - Monitored stocks: /app/monitored_stocks.json (Backup: /tmp/bullps_data/monitored_stocks.json)"
echo "   - Trade history: /app/trade_history.json (Backup: /tmp/bullps_data/trade_history.json)"
echo "   - Backup mechanism will be used if primary files are not writable"

# 運行 Zeabur 權限修復腳本（如果在 Zeabur 環境中）
if [[ -n "$ZEABUR" || "$(hostname)" == *zeabur* ]]; then
    echo "🔧 Detected Zeabur environment, running permission fix script..."
    /app/deploy-zeabur-fix.sh || echo "⚠️ Permission fix script failed, but continuing startup"
fi

echo "🌐 Starting application server..."
exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}
