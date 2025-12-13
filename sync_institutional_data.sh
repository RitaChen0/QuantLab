#!/bin/bash
# 法人買賣超數據批量同步腳本

set -e

API_BASE="http://localhost:8000/api/v1"

echo "========================================="
echo "法人買賣超數據批量同步"
echo "========================================="

# 顏色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 獲取 Token
echo -e "\n${YELLOW}步驟 1: 獲取認證 Token${NC}"
TOKEN=$(docker compose exec -T backend python3 -c "
import sys
sys.path.insert(0, '/app')
from app.core.security import create_access_token
print(create_access_token('1'))
" 2>/dev/null | tr -d '\r')

if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Token 獲取失敗${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Token 已獲取${NC}"

# 獲取 Top 50 股票列表
echo -e "\n${YELLOW}步驟 2: 獲取 Top 50 股票列表${NC}"
STOCK_LIST=$(docker compose exec -T backend python3 -c "
import sys
sys.path.insert(0, '/app')
from app.core.config import settings
from app.services.data_service import DataService
from app.db.session import SessionLocal

db = SessionLocal()
try:
    service = DataService()
    stocks = service.get_top_stocks_by_market_cap(db, limit=50)
    print(','.join([s.stock_id for s in stocks]))
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
finally:
    db.close()
" 2>/dev/null | tr -d '\r')

if [ -z "$STOCK_LIST" ] || [[ "$STOCK_LIST" == ERROR* ]]; then
    echo -e "${RED}❌ 獲取股票列表失敗${NC}"
    echo -e "${YELLOW}使用預設 Top 20 股票${NC}"
    STOCK_LIST="2330,2317,2454,2412,2882,2881,2886,2891,2892,2884,3711,2308,2303,1301,1303,2382,2395,2002,1326,2801"
fi

echo -e "${GREEN}✅ 股票列表已獲取${NC}"

# 將逗號分隔的字串轉為陣列
IFS=',' read -ra STOCKS <<< "$STOCK_LIST"
TOTAL_STOCKS=${#STOCKS[@]}

echo "   股票數量: $TOTAL_STOCKS"
echo "   股票列表: ${STOCKS[@]:0:10}..." # 只顯示前 10 個

# 設定同步日期範圍（近 365 天）
END_DATE=$(date +%Y-%m-%d)
START_DATE=$(date -d "365 days ago" +%Y-%m-%d)

echo -e "\n${YELLOW}步驟 3: 執行批量同步${NC}"
echo "   日期範圍: $START_DATE ~ $END_DATE"
echo "   股票數量: $TOTAL_STOCKS"

# 批量同步
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    "$API_BASE/institutional/sync/batch" \
    -d "{
        \"stock_ids\": [$(printf '"%s",' "${STOCKS[@]}" | sed 's/,$//')],
        \"start_date\": \"$START_DATE\",
        \"end_date\": \"$END_DATE\"
    }")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ 批量同步任務已創建${NC}"
    echo "$BODY" | jq '.'

    TASK_IDS=$(echo "$BODY" | jq -r '.task_ids | join(",")')
    echo -e "\n${YELLOW}任務 ID: $TASK_IDS${NC}"

    echo -e "\n${YELLOW}步驟 4: 監控同步進度${NC}"
    echo "   請使用以下命令監控 Celery Worker 日誌："
    echo "   docker compose logs celery-worker -f"

else
    echo -e "${RED}❌ 批量同步失敗 - 狀態碼: $HTTP_CODE${NC}"
    echo "   錯誤: $BODY"
    exit 1
fi

echo -e "\n${YELLOW}步驟 5: 檢查數據庫記錄數${NC}"
sleep 10 # 等待一些數據同步完成

RECORD_COUNT=$(docker compose exec -T postgres psql -U quantlab -d quantlab -t -c "
SELECT COUNT(*) FROM institutional_investors;
" 2>/dev/null | tr -d ' \n\r')

echo "   當前記錄數: $RECORD_COUNT"

echo -e "\n========================================="
echo -e "${GREEN}同步任務已啟動！${NC}"
echo "========================================="
echo ""
echo "📊 監控進度："
echo "   1. 查看 Celery Worker 日誌："
echo "      docker compose logs celery-worker -f"
echo ""
echo "   2. 查看數據庫記錄數："
echo "      docker compose exec postgres psql -U quantlab -d quantlab -c 'SELECT stock_id, COUNT(*) FROM institutional_investors GROUP BY stock_id ORDER BY COUNT(*) DESC LIMIT 10;'"
echo ""
echo "   3. 檢查特定股票數據："
echo "      docker compose exec postgres psql -U quantlab -d quantlab -c \"SELECT * FROM institutional_investors WHERE stock_id='2330' ORDER BY date DESC LIMIT 5;\""
echo ""
