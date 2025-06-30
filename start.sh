#!/bin/sh

# 確保環境變量存在
export PORT=${PORT:-8080}
export PYTHONPATH=${PYTHONPATH:-/app}

# 顯示當前環境
echo "Current directory: $(pwd)"
echo "Python path: $PYTHONPATH"
echo "Port: $PORT"
echo "Files in current directory:"
ls -la

# 顯示 Python 路徑
echo "Python sys.path:"
python3 -c "import sys; print('\n'.join(sys.path))"

# 啟動應用
exec uvicorn backend.main:app --host 0.0.0.0 --port $PORT 