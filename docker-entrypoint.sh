#!/bin/bash
set -e

# 確保數據目錄存在（忽略錯誤）
mkdir -p /app/data 2>/dev/null || true

# 初始化數據文件（如果不存在且可寫）
if [ ! -f "/app/data/monitored_stocks.json" ]; then
    echo '[]' > /app/data/monitored_stocks.json 2>/dev/null || echo "Cannot write to /app/data/monitored_stocks.json"
fi

if [ ! -f "/app/data/trade_history.json" ]; then
    echo '[]' > /app/data/trade_history.json 2>/dev/null || echo "Cannot write to /app/data/trade_history.json"
fi

if [ ! -f "/app/data/analysis_result.json" ]; then
    echo '{"result": []}' > /app/data/analysis_result.json 2>/dev/null || echo "Cannot write to /app/data/analysis_result.json"
fi

# 嘗試設置文件權限（忽略錯誤）
chmod 644 /app/data/*.json 2>/dev/null || echo "Cannot change permissions in /app/data/"

# 確保 backend 目錄中的文件存在（作為回退）
mkdir -p /app/backend 2>/dev/null || true

if [ ! -f "/app/backend/monitored_stocks.json" ]; then
    echo '[]' > /app/backend/monitored_stocks.json 2>/dev/null || true
fi

if [ ! -f "/app/backend/trade_history.json" ]; then
    echo '[]' > /app/backend/trade_history.json 2>/dev/null || true
fi

if [ ! -f "/app/analysis_result.json" ]; then
    echo '{"result": []}' > /app/analysis_result.json 2>/dev/null || true
fi

echo "Starting application..."
echo "Data directory status:"
ls -la /app/data/ 2>/dev/null || echo "/app/data/ not accessible"
echo "Backend directory status:"
ls -la /app/backend/ 2>/dev/null || echo "/app/backend/ not accessible"

# 啟動應用程式
exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}
