#!/bin/bash
# 法人買賣超任務監控腳本

echo "========================================="
echo "法人買賣超任務監控"
echo "========================================="

# 顏色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1. 檢查 Celery Worker 狀態
echo -e "\n${YELLOW}1. Celery Worker 狀態${NC}"
WORKER_STATUS=$(docker compose ps celery-worker --format json | jq -r '.[0].State' 2>/dev/null)
if [ "$WORKER_STATUS" = "running" ]; then
    echo -e "   ${GREEN}✅ Worker 運行中${NC}"
else
    echo -e "   ${RED}❌ Worker 未運行${NC}"
fi

# 2. 檢查 Celery Beat 狀態
echo -e "\n${YELLOW}2. Celery Beat 狀態${NC}"
BEAT_STATUS=$(docker compose ps celery-beat --format json | jq -r '.[0].State' 2>/dev/null)
if [ "$BEAT_STATUS" = "running" ]; then
    echo -e "   ${GREEN}✅ Beat 運行中${NC}"
else
    echo -e "   ${RED}❌ Beat 未運行${NC}"
fi

# 3. 查看定時任務配置
echo -e "\n${YELLOW}3. 法人買賣超定時任務配置${NC}"
echo ""
echo -e "   ${BLUE}📅 每日同步任務${NC}"
echo "      任務名稱: sync-institutional-investors-daily"
echo "      執行時間: 每天 21:00"
echo "      同步範圍: Top 100 股票，最近 7 天"
echo ""
echo -e "   ${BLUE}🗑️  週度清理任務${NC}"
echo "      任務名稱: cleanup-institutional-data-weekly"
echo "      執行時間: 每週日 02:00"
echo "      保留天數: 365 天"

# 4. 檢查數據庫統計
echo -e "\n${YELLOW}4. 數據庫統計${NC}"
STATS=$(docker compose exec -T postgres psql -U quantlab -d quantlab -t -c "
SELECT
    COUNT(*) as total,
    COUNT(DISTINCT stock_id) as stocks,
    COUNT(DISTINCT date) as days,
    MIN(date) as earliest,
    MAX(date) as latest
FROM institutional_investors;
" 2>/dev/null)

if [ ! -z "$STATS" ]; then
    echo "$STATS" | while IFS='|' read -r total stocks days earliest latest; do
        total=$(echo $total | xargs)
        stocks=$(echo $stocks | xargs)
        days=$(echo $days | xargs)
        earliest=$(echo $earliest | xargs)
        latest=$(echo $latest | xargs)

        echo -e "   ${GREEN}✅ 數據統計${NC}"
        echo "      總記錄數: $total"
        echo "      股票數量: $stocks"
        echo "      交易天數: $days"
        echo "      最早日期: $earliest"
        echo "      最新日期: $latest"
    done
else
    echo -e "   ${RED}❌ 無法獲取數據統計${NC}"
fi

# 5. 查看最近的任務執行記錄（從日誌）
echo -e "\n${YELLOW}5. 最近執行的法人買賣超任務${NC}"
docker compose logs celery-worker --tail 100 2>/dev/null | \
    grep -E "institutional|sync_top_stocks" | \
    tail -5 | \
    sed 's/^/   /'

# 6. 檢查 Top 10 股票數據
echo -e "\n${YELLOW}6. Top 10 股票數據統計${NC}"
docker compose exec -T postgres psql -U quantlab -d quantlab -t -c "
SELECT
    stock_id,
    COUNT(*) as records,
    MIN(date) as earliest,
    MAX(date) as latest
FROM institutional_investors
GROUP BY stock_id
ORDER BY COUNT(*) DESC
LIMIT 10;
" 2>/dev/null | sed 's/^/   /'

echo ""
echo "========================================="
echo -e "${GREEN}監控完成！${NC}"
echo "========================================="
echo ""
echo "📊 更多監控命令："
echo ""
echo "   查看 Worker 日誌："
echo "   docker compose logs celery-worker -f"
echo ""
echo "   查看 Beat 日誌："
echo "   docker compose logs celery-beat -f"
echo ""
echo "   手動觸發同步："
echo "   docker compose exec backend python3 trigger_institutional_sync.py"
echo ""
