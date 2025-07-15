#!/bin/bash
# 修復手動覆蓋文件後的權限問題
# 此腳本用於在手動覆蓋 Docker 容器中的文件後修復權限

set -e

echo "🔧 手動覆蓋文件權限修復工具"
echo "=================================="

# 檢查參數
if [ $# -eq 0 ]; then
    echo "用法: $0 <文件路徑>"
    echo "例如: $0 /app/monitored_stocks.json"
    echo ""
    echo "或使用 'all' 修復所有數據文件:"
    echo "$0 all"
    exit 1
fi

# 修復指定文件權限
fix_file_permissions() {
    local file_path="$1"
    
    if [ -f "$file_path" ]; then
        echo "🔍 修復文件: $file_path"
        
        # 顯示當前權限
        echo "- 當前權限: $(ls -l $file_path)"
        
        # 修復權限
        chmod 666 "$file_path" 2>/dev/null && echo "✅ 權限修復成功" || echo "⚠️ chmod 修復失敗"
        
        # 如果有 sudo 權限，嘗試使用 sudo
        if command -v sudo >/dev/null 2>&1; then
            sudo chown $(whoami) "$file_path" 2>/dev/null && echo "✅ 所有者修復成功" || echo "⚠️ 所有者修復失敗"
            sudo chmod 666 "$file_path" 2>/dev/null && echo "✅ sudo 權限修復成功" || echo "⚠️ sudo 權限修復失敗"
        fi
        
        # 測試寫入
        if echo "test" > "$file_path.test" 2>/dev/null; then
            rm -f "$file_path.test"
            echo "✅ 寫入測試成功"
        else
            echo "❌ 寫入測試失敗"
        fi
        
        # 顯示修復後權限
        echo "- 修復後權限: $(ls -l $file_path)"
    else
        echo "❌ 文件不存在: $file_path"
    fi
}

# 修復所有數據文件
fix_all_data_files() {
    echo "🔄 修復所有數據文件..."
    
    # 主要數據文件
    for file in "/app/monitored_stocks.json" "/app/trade_history.json" "/app/analysis_result.json"; do
        fix_file_permissions "$file"
        echo ""
    done
    
    # 備份數據文件
    echo "🔄 修復備份數據文件..."
    mkdir -p /tmp/bullps_data 2>/dev/null
    chmod 777 /tmp/bullps_data 2>/dev/null
    
    for file in "/tmp/bullps_data/monitored_stocks.json" "/tmp/bullps_data/trade_history.json" "/tmp/bullps_data/analysis_result.json"; do
        if [ -f "$file" ]; then
            fix_file_permissions "$file"
        else
            echo "❌ 備份文件不存在: $file"
        fi
        echo ""
    done
}

# 主程序
if [ "$1" = "all" ]; then
    fix_all_data_files
else
    fix_file_permissions "$1"
fi

echo "=================================="
echo "✅ 權限修復完成"
echo ""
echo "如果仍然遇到權限問題，請嘗試:"
echo "1. 使用 API 端點: POST /api/reset-file-permissions"
echo "2. 重啟容器"
echo "3. 使用備份目錄: /tmp/bullps_data/"
