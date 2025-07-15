#!/bin/bash
set -e

# 確保數據目錄存在
mkdir -p /app/data

# 初始化數據文件（如果不存在）
if [ ! -f "/app/data/monitored_stocks.json" ]; then
    echo '[]' > /app/data/monitored_stocks.json
fi

if [ ! -f "/app/data/trade_history.json" ]; then
    echo '[]' > /app/data/trade_history.json
fi

if [ ! -f "/app/data/analysis_result.json" ]; then
    echo '{"result": []}' > /app/data/analysis_result.json
fi

# 確保文件權限正確
chmod 644 /app/data/*.json

# 啟動應用程式
exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}
