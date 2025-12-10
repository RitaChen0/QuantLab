#!/bin/bash
# 回測任務監控腳本

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   📊 QuantLab 回測任務監控${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 1. 檢查正在執行的任務
echo -e "${YELLOW}🔄 正在執行的任務：${NC}"
ACTIVE_TASKS=$(docker compose exec -T celery-worker celery -A app.core.celery_app inspect active 2>/dev/null)

if echo "$ACTIVE_TASKS" | grep -q "empty"; then
    echo -e "${GREEN}✅ 目前沒有任務正在執行${NC}"
else
    echo "$ACTIVE_TASKS"
fi
echo ""

# 2. 檢查排隊中的任務
echo -e "${YELLOW}⏳ 排隊中的任務：${NC}"
RESERVED_TASKS=$(docker compose exec -T celery-worker celery -A app.core.celery_app inspect reserved 2>/dev/null)

if echo "$RESERVED_TASKS" | grep -q "empty"; then
    echo -e "${GREEN}✅ 沒有任務在排隊${NC}"
else
    echo "$RESERVED_TASKS"
fi
echo ""

# 3. 檢查 Redis 隊列長度
echo -e "${YELLOW}📦 Redis 隊列狀態：${NC}"
echo -n "  backtest 隊列: "
BACKTEST_QUEUE=$(docker compose exec -T redis redis-cli LLEN backtest 2>/dev/null)
if [ "$BACKTEST_QUEUE" = "0" ]; then
    echo -e "${GREEN}0 (空)${NC}"
else
    echo -e "${RED}${BACKTEST_QUEUE}${NC}"
fi

echo -n "  celery 隊列: "
CELERY_QUEUE=$(docker compose exec -T redis redis-cli LLEN celery 2>/dev/null)
if [ "$CELERY_QUEUE" = "0" ]; then
    echo -e "${GREEN}0 (空)${NC}"
else
    echo -e "${RED}${CELERY_QUEUE}${NC}"
fi
echo ""

# 4. 任務執行統計
echo -e "${YELLOW}📈 任務執行統計：${NC}"
docker compose exec -T celery-worker celery -A app.core.celery_app inspect stats 2>/dev/null | grep -A 5 '"total"'
echo ""

# 5. Worker 狀態
echo -e "${YELLOW}⚙️  Worker 狀態：${NC}"
docker compose exec -T celery-worker celery -A app.core.celery_app inspect active_queues 2>/dev/null
echo ""

# 6. 最近的 Celery 日誌
echo -e "${YELLOW}📋 最近的回測日誌 (最後 10 行)：${NC}"
docker compose logs celery-worker --tail 10 | grep -i "backtest\|task"
echo ""

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}監控完成！ $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
