#!/bin/bash
#
# 批次同步監控腳本
#

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

clear

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          批次同步即時監控 - QuantLab                        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 檢查進度檔是否存在
if [ ! -f /tmp/batch_sync_progress.json ]; then
    echo -e "${RED}❌ 找不到進度檔，同步可能尚未啟動${NC}"
    exit 1
fi

while true; do
    # 移到螢幕頂端
    tput cup 5 0

    # 讀取進度
    COMPLETED=$(jq -r '.completed_stocks | length' /tmp/batch_sync_progress.json 2>/dev/null || echo "0")
    FAILED=$(jq -r '.failed_stocks | length' /tmp/batch_sync_progress.json 2>/dev/null || echo "0")
    TOTAL_SYNCED=$(jq -r '.total_synced' /tmp/batch_sync_progress.json 2>/dev/null || echo "0")
    START_TIME=$(jq -r '.start_time' /tmp/batch_sync_progress.json 2>/dev/null || echo "N/A")
    LAST_UPDATE=$(jq -r '.last_update' /tmp/batch_sync_progress.json 2>/dev/null || echo "N/A")

    # 計算百分比
    TOTAL=2671
    if [ "$COMPLETED" -gt 0 ]; then
        PERCENT=$((COMPLETED * 100 / TOTAL))
    else
        PERCENT=0
    fi

    # 計算已用時間
    if [ "$START_TIME" != "N/A" ] && [ "$START_TIME" != "null" ]; then
        START_EPOCH=$(date -d "$START_TIME" +%s 2>/dev/null || echo "0")
        NOW_EPOCH=$(date +%s)
        ELAPSED=$((NOW_EPOCH - START_EPOCH))
        ELAPSED_HOURS=$((ELAPSED / 3600))
        ELAPSED_MINS=$(((ELAPSED % 3600) / 60))
    else
        ELAPSED_HOURS=0
        ELAPSED_MINS=0
    fi

    # 預估剩餘時間
    if [ "$COMPLETED" -gt 10 ] && [ "$ELAPSED" -gt 0 ]; then
        AVG_TIME=$((ELAPSED / COMPLETED))
        REMAINING=$((TOTAL - COMPLETED))
        REMAINING_SECONDS=$((REMAINING * AVG_TIME))
        REMAINING_HOURS=$((REMAINING_SECONDS / 3600))
        REMAINING_MINS=$(((REMAINING_SECONDS % 3600) / 60))
    else
        REMAINING_HOURS="?"
        REMAINING_MINS="?"
    fi

    # 查詢資料庫筆數
    DB_COUNT=$(docker compose exec -T postgres psql -U quantlab quantlab -c "SELECT COUNT(*) FROM fundamental_data;" 2>/dev/null | grep -E "^\s*[0-9]+" | tr -d ' ' || echo "0")

    # 顯示資訊
    echo -e "${GREEN}📊 即時進度${NC}                                                    "
    echo -e "════════════════════════════════════════════════════════════"
    echo -e "進度: ${GREEN}$COMPLETED${NC} / $TOTAL 檔 (${PERCENT}%)                    "

    # 進度條
    BAR_LENGTH=50
    FILLED=$((PERCENT * BAR_LENGTH / 100))
    printf "["
    for ((i=0; i<FILLED; i++)); do printf "█"; done
    for ((i=FILLED; i<BAR_LENGTH; i++)); do printf "░"; done
    printf "] %d%%\n\n" $PERCENT

    echo -e "${YELLOW}📈 統計資訊${NC}                                                    "
    echo -e "✅ 成功: $COMPLETED 檔                                              "
    echo -e "❌ 失敗: $FAILED 檔                                                "
    echo -e "📊 快取數據: $(printf "%'d" $TOTAL_SYNCED) 筆                      "
    echo -e "💾 資料庫: $(printf "%'d" $DB_COUNT) 筆                            "
    echo ""

    echo -e "${BLUE}⏱️  時間資訊${NC}                                                   "
    echo -e "已執行: ${ELAPSED_HOURS}h ${ELAPSED_MINS}m                         "
    echo -e "預估剩餘: ${REMAINING_HOURS}h ${REMAINING_MINS}m                   "
    echo -e "開始時間: ${START_TIME:0:19}                                       "
    echo -e "最後更新: ${LAST_UPDATE:0:19}                                       "
    echo ""

    # 顯示最近的日誌
    echo -e "${YELLOW}📝 最近活動${NC}                                                   "
    echo -e "────────────────────────────────────────────────────────────"
    tail -5 /tmp/batch_sync_*.log 2>/dev/null | grep -E "完成:|批次" | tail -3 | cut -c 1-70 || echo "等待日誌..."
    echo ""
    echo -e "────────────────────────────────────────────────────────────"
    echo -e "${YELLOW}按 Ctrl+C 退出監控（不會停止同步）${NC}                             "

    sleep 5
done
