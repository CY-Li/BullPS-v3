#!/bin/bash
# 將文件複製到 Zeabur 容器的正確位置
# 使用方法: ./copy-to-zeabur.sh <本地文件路徑> <容器名稱或ID> [文件類型]

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Zeabur 文件複製工具${NC}"
echo "=================================="

# 檢查參數
if [ $# -lt 2 ]; then
    echo -e "${RED}❌ 參數不足${NC}"
    echo "用法: $0 <本地文件路徑> <容器名稱或ID> [文件類型]"
    echo ""
    echo "文件類型選項:"
    echo "  monitored_stocks  - 監控股票文件"
    echo "  trade_history     - 交易歷史文件"
    echo "  analysis_result   - 分析結果文件"
    echo ""
    echo "範例:"
    echo "  $0 /path/to/monitored_stocks0714.json my-container monitored_stocks"
    echo "  $0 ./trade_history.json my-container trade_history"
    exit 1
fi

LOCAL_FILE="$1"
CONTAINER="$2"
FILE_TYPE="${3:-auto}"

# 檢查本地文件是否存在
if [ ! -f "$LOCAL_FILE" ]; then
    echo -e "${RED}❌ 本地文件不存在: $LOCAL_FILE${NC}"
    exit 1
fi

# 自動檢測文件類型
if [ "$FILE_TYPE" = "auto" ]; then
    filename=$(basename "$LOCAL_FILE")
    if [[ "$filename" == *"monitored_stocks"* ]]; then
        FILE_TYPE="monitored_stocks"
    elif [[ "$filename" == *"trade_history"* ]]; then
        FILE_TYPE="trade_history"
    elif [[ "$filename" == *"analysis_result"* ]]; then
        FILE_TYPE="analysis_result"
    else
        echo -e "${YELLOW}⚠️ 無法自動檢測文件類型，請手動指定${NC}"
        echo "可用的文件類型: monitored_stocks, trade_history, analysis_result"
        exit 1
    fi
fi

# 設置目標文件名
case "$FILE_TYPE" in
    "monitored_stocks")
        TARGET_FILE="monitored_stocks.json"
        ;;
    "trade_history")
        TARGET_FILE="trade_history.json"
        ;;
    "analysis_result")
        TARGET_FILE="analysis_result.json"
        ;;
    *)
        echo -e "${RED}❌ 無效的文件類型: $FILE_TYPE${NC}"
        echo "可用的文件類型: monitored_stocks, trade_history, analysis_result"
        exit 1
        ;;
esac

echo -e "${BLUE}📋 複製信息:${NC}"
echo "  本地文件: $LOCAL_FILE"
echo "  容器: $CONTAINER"
echo "  文件類型: $FILE_TYPE"
echo "  目標文件: $TARGET_FILE"
echo ""

# 檢查容器是否存在
if ! docker ps -a --format "table {{.Names}}\t{{.ID}}" | grep -q "$CONTAINER"; then
    echo -e "${RED}❌ 容器不存在或無法訪問: $CONTAINER${NC}"
    echo "請檢查容器名稱或ID是否正確"
    exit 1
fi

# 檢查容器是否運行
if ! docker ps --format "table {{.Names}}\t{{.ID}}" | grep -q "$CONTAINER"; then
    echo -e "${YELLOW}⚠️ 容器未運行: $CONTAINER${NC}"
    echo "請先啟動容器"
    exit 1
fi

echo -e "${BLUE}🔄 開始複製文件...${NC}"

# 複製文件到備份目錄（Zeabur 環境的主要數據目錄）
echo "1. 複製到備份目錄 /tmp/bullps_data/"
if docker cp "$LOCAL_FILE" "$CONTAINER:/tmp/bullps_data/$TARGET_FILE"; then
    echo -e "${GREEN}✅ 複製到備份目錄成功${NC}"
else
    echo -e "${RED}❌ 複製到備份目錄失敗${NC}"
    exit 1
fi

# 設置文件權限
echo "2. 設置文件權限"
if docker exec "$CONTAINER" chmod 666 "/tmp/bullps_data/$TARGET_FILE"; then
    echo -e "${GREEN}✅ 設置權限成功${NC}"
else
    echo -e "${YELLOW}⚠️ 設置權限失敗，但文件已複製${NC}"
fi

# 嘗試複製到主目錄（如果可寫）
echo "3. 嘗試複製到主目錄 /app/"
if docker exec "$CONTAINER" test -w "/app"; then
    if docker cp "$LOCAL_FILE" "$CONTAINER:/app/$TARGET_FILE"; then
        echo -e "${GREEN}✅ 複製到主目錄成功${NC}"
        # 設置主目錄文件權限
        docker exec "$CONTAINER" chmod 666 "/app/$TARGET_FILE" 2>/dev/null || echo -e "${YELLOW}⚠️ 設置主目錄權限失敗${NC}"
    else
        echo -e "${YELLOW}⚠️ 複製到主目錄失敗，但備份目錄已更新${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ 主目錄不可寫，僅使用備份目錄${NC}"
fi

# 驗證文件
echo -e "${BLUE}🔍 驗證文件...${NC}"
echo "備份目錄文件:"
if docker exec "$CONTAINER" ls -la "/tmp/bullps_data/$TARGET_FILE" 2>/dev/null; then
    echo -e "${GREEN}✅ 備份目錄文件存在${NC}"
else
    echo -e "${RED}❌ 備份目錄文件不存在${NC}"
fi

echo "主目錄文件:"
if docker exec "$CONTAINER" ls -la "/app/$TARGET_FILE" 2>/dev/null; then
    echo -e "${GREEN}✅ 主目錄文件存在${NC}"
else
    echo -e "${YELLOW}⚠️ 主目錄文件不存在（正常，Zeabur 環境使用備份目錄）${NC}"
fi

# 測試文件內容
echo -e "${BLUE}📄 檢查文件內容...${NC}"
if docker exec "$CONTAINER" head -n 5 "/tmp/bullps_data/$TARGET_FILE" 2>/dev/null; then
    echo -e "${GREEN}✅ 文件內容正常${NC}"
else
    echo -e "${RED}❌ 無法讀取文件內容${NC}"
fi

echo ""
echo "=================================="
echo -e "${GREEN}🎉 文件複製完成！${NC}"
echo ""
echo -e "${BLUE}📋 後續步驟:${NC}"
echo "1. 重啟應用程序以載入新數據"
echo "2. 檢查應用程序日誌確認文件載入成功"
echo "3. 通過 API 驗證數據更新"
echo ""
echo -e "${BLUE}🔧 如果遇到問題:${NC}"
echo "1. 調用權限修復 API: curl -X POST http://your-app/api/reset-file-permissions"
echo "2. 檢查文件狀態: curl http://your-app/api/file-paths-status"
echo "3. 查看容器日誌: docker logs $CONTAINER"
