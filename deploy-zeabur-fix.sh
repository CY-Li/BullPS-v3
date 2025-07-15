#!/bin/bash
# Zeabur 部署權限修復腳本
# 此腳本應在 Zeabur 部署後運行，以修復文件權限問題

set -e

echo "🚀 Zeabur 權限修復腳本"
echo "=================================="

# 檢查環境
echo "🔍 檢查環境..."
echo "- 主機名: $(hostname)"
echo "- 用戶: $(whoami)"
echo "- 當前目錄: $(pwd)"
echo "- ZEABUR 環境變數: ${ZEABUR:-未設置}"
echo "- CONTAINER_ENV 環境變數: ${CONTAINER_ENV:-未設置}"

# 檢查 /app 目錄
if [ -d "/app" ]; then
    echo "✅ /app 目錄存在"
    echo "- 目錄權限: $(ls -ld /app)"
    echo "- 目錄可寫: $([ -w /app ] && echo '是' || echo '否')"
else
    echo "❌ /app 目錄不存在"
    exit 1
fi

# 修復目錄權限
echo ""
echo "🔧 修復目錄權限..."
chmod -R 777 /app 2>/dev/null && echo "✅ 目錄權限修復成功" || echo "⚠️ 目錄權限修復失敗"

# 確保數據文件存在
echo ""
echo "📄 確保數據文件存在..."

# monitored_stocks.json
if [ ! -f "/app/monitored_stocks.json" ]; then
    echo '[]' > /app/monitored_stocks.json 2>/dev/null && echo "✅ 創建 monitored_stocks.json" || echo "❌ 無法創建 monitored_stocks.json"
else
    echo "✅ monitored_stocks.json 已存在"
fi

# trade_history.json
if [ ! -f "/app/trade_history.json" ]; then
    echo '[]' > /app/trade_history.json 2>/dev/null && echo "✅ 創建 trade_history.json" || echo "❌ 無法創建 trade_history.json"
else
    echo "✅ trade_history.json 已存在"
fi

# analysis_result.json
if [ ! -f "/app/analysis_result.json" ]; then
    echo '{"result": [], "timestamp": "", "analysis_date": "", "total_stocks": 0, "analyzed_stocks": 0}' > /app/analysis_result.json 2>/dev/null && echo "✅ 創建 analysis_result.json" || echo "❌ 無法創建 analysis_result.json"
else
    echo "✅ analysis_result.json 已存在"
fi

# 修復文件權限
echo ""
echo "🔧 修復文件權限..."
chmod 666 /app/*.json 2>/dev/null && echo "✅ 文件權限修復成功" || echo "⚠️ 文件權限修復失敗"

# 創建備份目錄
echo ""
echo "📁 創建備份目錄..."
mkdir -p /tmp/bullps_data 2>/dev/null && echo "✅ 備份目錄創建成功" || echo "❌ 備份目錄創建失敗"
chmod 777 /tmp/bullps_data 2>/dev/null && echo "✅ 備份目錄權限設置成功" || echo "⚠️ 備份目錄權限設置失敗"

# 複製文件到備份目錄（如果主要目錄不可寫）
echo ""
echo "🔄 設置備份文件..."
for file in "monitored_stocks.json" "trade_history.json" "analysis_result.json"; do
    if [ -f "/app/$file" ]; then
        cp "/app/$file" "/tmp/bullps_data/$file" 2>/dev/null && echo "✅ 備份 $file" || echo "⚠️ 無法備份 $file"
    else
        # 在備份目錄創建默認文件
        if [ "$file" = "analysis_result.json" ]; then
            echo '{"result": [], "timestamp": "", "analysis_date": "", "total_stocks": 0, "analyzed_stocks": 0}' > "/tmp/bullps_data/$file" 2>/dev/null && echo "✅ 在備份目錄創建 $file" || echo "❌ 無法在備份目錄創建 $file"
        else
            echo '[]' > "/tmp/bullps_data/$file" 2>/dev/null && echo "✅ 在備份目錄創建 $file" || echo "❌ 無法在備份目錄創建 $file"
        fi
    fi
done

# 測試文件寫入
echo ""
echo "🧪 測試文件寫入..."
for file in "monitored_stocks.json" "trade_history.json" "analysis_result.json"; do
    # 測試主要位置
    if echo "test" > "/app/$file.test" 2>/dev/null; then
        rm -f "/app/$file.test" 2>/dev/null
        echo "✅ /app/$file 可寫"
    else
        echo "❌ /app/$file 不可寫"
        
        # 測試備份位置
        if echo "test" > "/tmp/bullps_data/$file.test" 2>/dev/null; then
            rm -f "/tmp/bullps_data/$file.test" 2>/dev/null
            echo "✅ /tmp/bullps_data/$file 可寫"
        else
            echo "❌ /tmp/bullps_data/$file 也不可寫"
        fi
    fi
done

# 顯示文件狀態
echo ""
echo "📊 文件狀態報告:"
echo "主要目錄 (/app):"
ls -la /app/*.json 2>/dev/null || echo "  無法列出 /app/*.json"

echo ""
echo "備份目錄 (/tmp/bullps_data):"
ls -la /tmp/bullps_data/*.json 2>/dev/null || echo "  無法列出 /tmp/bullps_data/*.json"

# 設置環境變數
echo ""
echo "🌐 設置環境變數..."
export BULLPS_BACKUP_DIR="/tmp/bullps_data"
echo "✅ 設置 BULLPS_BACKUP_DIR=$BULLPS_BACKUP_DIR"

echo ""
echo "=================================="
echo "✅ 權限修復腳本執行完成"
echo ""
echo "📋 修復摘要:"
echo "- 主要數據目錄: /app"
echo "- 備份數據目錄: /tmp/bullps_data"
echo "- 系統會自動在權限問題時切換到備份目錄"
echo ""
echo "🔧 如果仍然遇到權限問題，請:"
echo "1. 檢查 Zeabur 容器的用戶權限設置"
echo "2. 確認容器的文件系統掛載選項"
echo "3. 聯繫 Zeabur 支持團隊"
echo ""
echo "🌐 應用程序現在應該可以正常運行了"
