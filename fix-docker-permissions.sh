#!/bin/bash
# 修復 Docker 容器中的文件權限
# 當手動更新數據文件後，使用此腳本修復權限問題

CONTAINER_NAME="bullps-v3-test"

echo "🔧 修復 Docker 容器文件權限..."

# 檢查容器是否存在且正在運行
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "❌ 容器 $CONTAINER_NAME 未運行"
    echo "請先啟動容器："
    echo "  docker run -d -p 8081:8080 --name $CONTAINER_NAME bullps-v3-unified"
    exit 1
fi

echo "📁 修復數據文件權限..."

# 修復文件所有者
docker exec -u root "$CONTAINER_NAME" chown appuser:appuser /app/analysis_result.json 2>/dev/null || echo "⚠️  analysis_result.json 權限修復失敗"
docker exec -u root "$CONTAINER_NAME" chown appuser:appuser /app/monitored_stocks.json 2>/dev/null || echo "⚠️  monitored_stocks.json 權限修復失敗"
docker exec -u root "$CONTAINER_NAME" chown appuser:appuser /app/trade_history.json 2>/dev/null || echo "⚠️  trade_history.json 權限修復失敗"

# 修復文件權限
docker exec -u root "$CONTAINER_NAME" chmod 664 /app/analysis_result.json 2>/dev/null || echo "⚠️  analysis_result.json 權限設置失敗"
docker exec -u root "$CONTAINER_NAME" chmod 664 /app/monitored_stocks.json 2>/dev/null || echo "⚠️  monitored_stocks.json 權限設置失敗"
docker exec -u root "$CONTAINER_NAME" chmod 664 /app/trade_history.json 2>/dev/null || echo "⚠️  trade_history.json 權限設置失敗"

echo "✅ 權限修復完成！"

# 顯示當前權限狀態
echo "📊 當前文件權限狀態："
docker exec "$CONTAINER_NAME" ls -la /app/*.json

echo ""
echo "🎯 現在可以正常使用應用程式的寫入功能了！"
echo "   - 前端「立即更新」功能"
echo "   - 監控股票更新"
echo "   - 交易歷史記錄"
