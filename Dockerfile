# 1. Build frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend ./
RUN npm run build && ls -la dist

# 2. Build backend
FROM python:3.12-slim AS backend
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# 設定系統時區為台灣時區
ENV TZ=Asia/Taipei
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 先複製 requirements.txt 以利用緩存層
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 複製後端代碼和數據文件
COPY backend ./backend
COPY stock_watchlist.json ./
# COPY analysis_result.json ./
COPY integrated_stock_analyzer.py ./
COPY enhanced_confirmation_system.py ./
COPY multi_timeframe_analyzer.py ./
COPY api_error_handler.py ./
COPY backtester.py ./
COPY docker-entrypoint.sh ./

# 複製前端構建產物
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
RUN ls -la frontend/dist

# 設置環境變量
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV PYTHONPATH=/app
ENV ASGI_APPLICATION=backend.main:app
ENV CONTAINER_ENV=true

# 創建統一數據目錄並設置權限
RUN mkdir -p /app/data && \
    useradd -m appuser && \
    chmod +x /app/docker-entrypoint.sh

# 初始化統一數據文件
RUN echo '[]' > /app/data/monitored_stocks.json && \
    echo '[]' > /app/data/trade_history.json && \
    echo '{"result": [], "timestamp": "", "analysis_date": "", "total_stocks": 0, "analyzed_stocks": 0}' > /app/data/analysis_result.json

# 確保 /app/data 目錄完全可寫（關鍵修復）
RUN chown -R appuser:appuser /app && \
    chmod -R 755 /app && \
    chmod 775 /app/data && \
    chmod 664 /app/data/*.json

# 切換到應用程式用戶
USER appuser

# 健康檢查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

# 暴露端口
EXPOSE 8080

# 啟動命令
CMD ["./docker-entrypoint.sh"]