#!/bin/bash
set -e

echo "🚀 Starting BullPS-v3..."

# 檢測 Zeabur 環境
is_zeabur=false
if [[ -n "$ZEABUR" || "$(hostname)" == *zeabur* ]]; then
    is_zeabur=true
    echo "🔍 檢測到 Zeabur 環境"
    # 自動設置強制使用備份目錄
    export BULLPS_FORCE_BACKUP_DIR=true
    echo "✅ 已設置 BULLPS_FORCE_BACKUP_DIR=true"
fi

# 確保備份目錄存在並設置權限
echo "📁 確保備份目錄存在..."
mkdir -p /tmp/bullps_data 2>/dev/null && echo "✅ 創建備份目錄成功" || echo "❌ 無法創建備份目錄"
chmod -R 777 /tmp/bullps_data 2>/dev/null && echo "✅ 設置備份目錄權限成功" || echo "⚠️ 設置備份目錄權限失敗"

# 初始化備份文件（如果不存在）
echo "📄 初始化備份文件..."
for file in "monitored_stocks.json" "trade_history.json"; do
    if [ ! -f "/tmp/bullps_data/$file" ]; then
        echo '[]' > "/tmp/bullps_data/$file" 2>/dev/null && echo "✅ 創建 $file 成功" || echo "❌ 無法創建 $file"
    fi
    # 修復文件權限
    chmod 666 "/tmp/bullps_data/$file" 2>/dev/null && echo "✅ 設置 $file 權限成功" || echo "⚠️ 設置 $file 權限失敗"
done

if [ ! -f "/tmp/bullps_data/analysis_result.json" ]; then
    echo '{"result": [], "timestamp": "", "analysis_date": "", "total_stocks": 0, "analyzed_stocks": 0}' > /tmp/bullps_data/analysis_result.json 2>/dev/null && echo "✅ 創建 analysis_result.json 成功" || echo "❌ 無法創建 analysis_result.json"
fi
# 修復分析結果文件權限
chmod 666 "/tmp/bullps_data/analysis_result.json" 2>/dev/null && echo "✅ 設置 analysis_result.json 權限成功" || echo "⚠️ 設置 analysis_result.json 權限失敗"

# 嘗試初始化主目錄文件（如果可寫）
if [ -w "/app" ]; then
    echo "📁 /app 目錄可寫，初始化主目錄文件..."

    for file in "monitored_stocks.json" "trade_history.json"; do
        if [ ! -f "/app/$file" ]; then
            echo '[]' > "/app/$file" 2>/dev/null && echo "✅ 創建主目錄 $file 成功" || echo "❌ 無法創建主目錄 $file"
        fi
        # 修復文件權限
        chmod 666 "/app/$file" 2>/dev/null && echo "✅ 設置主目錄 $file 權限成功" || echo "⚠️ 設置主目錄 $file 權限失敗"
    done

    if [ ! -f "/app/analysis_result.json" ]; then
        echo '{"result": [], "timestamp": "", "analysis_date": "", "total_stocks": 0, "analyzed_stocks": 0}' > /app/analysis_result.json 2>/dev/null && echo "✅ 創建主目錄 analysis_result.json 成功" || echo "❌ 無法創建主目錄 analysis_result.json"
    fi
    # 修復分析結果文件權限
    chmod 666 "/app/analysis_result.json" 2>/dev/null && echo "✅ 設置主目錄 analysis_result.json 權限成功" || echo "⚠️ 設置主目錄 analysis_result.json 權限失敗"
else
    echo "⚠️ /app 目錄不可寫，僅使用備份目錄"
fi

# 顯示文件狀態
echo "📊 數據文件狀態:"
echo "備份目錄 (/tmp/bullps_data):"
ls -la /tmp/bullps_data/*.json 2>/dev/null || echo "❌ 無法列出 /tmp/bullps_data/*.json"

if [ -w "/app" ]; then
    echo "主目錄 (/app):"
    ls -la /app/*.json 2>/dev/null || echo "❌ 無法列出 /app/*.json"
fi

# 設置數據目錄信息
if $is_zeabur; then
    echo "✅ Zeabur 環境使用備份目錄: /tmp/bullps_data"
    echo "📊 所有組件將使用相同的數據文件:"
    echo "   - 分析結果: /tmp/bullps_data/analysis_result.json"
    echo "   - 監控股票: /tmp/bullps_data/monitored_stocks.json"
    echo "   - 交易歷史: /tmp/bullps_data/trade_history.json"
else
    if [ -w "/app" ]; then
        echo "✅ 使用主目錄: /app (備份: /tmp/bullps_data)"
        echo "📊 所有組件將使用相同的數據文件:"
        echo "   - 分析結果: /app/analysis_result.json (備份: /tmp/bullps_data/analysis_result.json)"
        echo "   - 監控股票: /app/monitored_stocks.json (備份: /tmp/bullps_data/monitored_stocks.json)"
        echo "   - 交易歷史: /app/trade_history.json (備份: /tmp/bullps_data/trade_history.json)"
        echo "   - 如果主目錄文件不可寫，將自動使用備份目錄"
    else
        echo "✅ 主目錄不可寫，使用備份目錄: /tmp/bullps_data"
        echo "📊 所有組件將使用相同的數據文件:"
        echo "   - 分析結果: /tmp/bullps_data/analysis_result.json"
        echo "   - 監控股票: /tmp/bullps_data/monitored_stocks.json"
        echo "   - 交易歷史: /tmp/bullps_data/trade_history.json"
    fi
fi

echo "🌐 啟動應用服務器..."
exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}
