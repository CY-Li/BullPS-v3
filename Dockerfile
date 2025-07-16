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
    dos2unix \
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
COPY fix-zeabur-permissions.sh ./

# 複製前端構建產物
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
RUN ls -la frontend/dist

# 複製部署修復腳本
COPY deploy-zeabur-fix.sh ./
COPY fix-manual-override.sh ./

# 設置環境變量
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV PYTHONPATH=/app
ENV ASGI_APPLICATION=backend.main:app
ENV CONTAINER_ENV=true
ENV BULLPS_BACKUP_DIR=/tmp/bullps_data
ENV BULLPS_FORCE_BACKUP_DIR=false

# 創建用戶並設置權限
RUN useradd -m appuser && \
    chmod +x /app/docker-entrypoint.sh && \
    chmod +x /app/fix-zeabur-permissions.sh && \
    chmod +x /app/deploy-zeabur-fix.sh && \
    chmod +x /app/fix-manual-override.sh && \
    dos2unix /app/docker-entrypoint.sh && \
    dos2unix /app/fix-zeabur-permissions.sh && \
    dos2unix /app/deploy-zeabur-fix.sh && \
    dos2unix /app/fix-manual-override.sh

# 初始化根目錄數據文件
RUN echo '[]' > /app/monitored_stocks.json && \
    echo '[]' > /app/trade_history.json && \
    echo '{"result": [], "timestamp": "", "analysis_date": "", "total_stocks": 0, "analyzed_stocks": 0}' > /app/analysis_result.json

# 創建備份目錄並初始化備份文件
RUN mkdir -p /tmp/bullps_data && \
    echo '[]' > /tmp/bullps_data/monitored_stocks.json && \
    echo '[]' > /tmp/bullps_data/trade_history.json && \
    echo '{"result": [], "timestamp": "", "analysis_date": "", "total_stocks": 0, "analyzed_stocks": 0}' > /tmp/bullps_data/analysis_result.json

# 確保 /app 目錄完全可寫（Zeabur 權限修復）
RUN chown -R appuser:appuser /app && \
    chmod -R 755 /app && \
    chmod 777 /app/*.json && \
    chmod -R 777 /tmp/bullps_data && \
    echo "appuser ALL=(ALL) NOPASSWD: /bin/chown, /bin/chmod" >> /etc/sudoers

# 切換到應用程式用戶
USER appuser

# 健康檢查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

# 暴露端口
EXPOSE 8080

# 啟動命令
CMD ["./docker-entrypoint.sh"]