#!/bin/bash
# 重新觸發被撤銷的定時任務
# 用途：backend 重啟後，自動檢測並重新執行今天應該執行但被撤銷的任務

set -e

echo "========================================"
echo "🔄 檢測並重新觸發被撤銷的任務"
echo "========================================"
echo ""

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 當前時間（台灣時間）
CURRENT_HOUR=$(date +%H)
CURRENT_MINUTE=$(date +%M)
CURRENT_DAY=$(date +%u)  # 1=Monday, 7=Sunday
CURRENT_TIME="${CURRENT_HOUR}:${CURRENT_MINUTE}"

echo -e "${BLUE}📅 當前時間: $(date '+%Y-%m-%d %H:%M:%S (%A)')${NC}"
echo ""

# 定義所有定時任務及其執行時間（台灣時間）
declare -A DAILY_TASKS
DAILY_TASKS=(
    # 格式: "任務名稱|執行時間(HH:MM)|星期限制(1-7,留空=每日)|描述"
    ["sync_stock_list"]="08:00|1-5|同步股票列表"
    ["sync_daily_prices"]="21:00|1-5|同步每日價格"
    ["sync_ohlcv_data"]="22:00|1-5|同步 OHLCV 數據"
    ["sync_fundamental_latest"]="23:00|1-5|同步財務指標（快速）"
    ["sync_top_stocks_institutional"]="21:00|1-5|同步法人買賣超（Top 100）"
    ["sync_shioaji_top_stocks"]="15:00|1-5|同步 Shioaji 分鐘線（Top 50）"
    ["sync_shioaji_futures"]="15:30|1-5|同步 Shioaji 期貨分鐘線（TX/MTX）"
    ["cleanup_old_cache"]="03:00||清理過期快取"
    ["sync_fundamental_data"]="04:00|7|同步財務指標（完整，週日）"
    ["cleanup_old_institutional_data"]="02:00|7|清理過期法人數據（週日）"
    ["generate_continuous_contracts"]="18:00|6|生成期貨連續合約（週六）"
)

# 計數器
TRIGGERED_COUNT=0
SKIPPED_COUNT=0
FAILED_COUNT=0

# 檢查任務是否應該在今天執行
should_run_today() {
    local day_restriction=$1

    # 如果沒有星期限制，每天都執行
    if [ -z "$day_restriction" ]; then
        return 0
    fi

    # 檢查是否包含當前星期
    if [[ "$day_restriction" == *"-"* ]]; then
        # 範圍格式: 1-5
        IFS='-' read -r start_day end_day <<< "$day_restriction"
        if [ "$CURRENT_DAY" -ge "$start_day" ] && [ "$CURRENT_DAY" -le "$end_day" ]; then
            return 0
        fi
    elif [[ "$day_restriction" == *"$CURRENT_DAY"* ]]; then
        # 單一數字或逗號分隔
        return 0
    fi

    return 1
}

# 檢查時間是否已過
is_time_passed() {
    local task_time=$1
    local task_hour=$(echo "$task_time" | cut -d: -f1 | sed 's/^0*//')
    local task_minute=$(echo "$task_time" | cut -d: -f2 | sed 's/^0*//')

    # 處理空值（例如 00 -> 空）
    task_hour=${task_hour:-0}
    task_minute=${task_minute:-0}

    # 轉換為分鐘數進行比較
    local current_minutes=$(($CURRENT_HOUR * 60 + $CURRENT_MINUTE))
    local task_minutes=$(($task_hour * 60 + $task_minute))

    if [ "$current_minutes" -gt "$task_minutes" ]; then
        return 0  # 時間已過
    else
        return 1  # 時間未到
    fi
}

# 檢查任務是否今天已執行過
task_executed_today() {
    local task_name=$1
    local log_count=$(docker compose logs celery-worker --since 24h 2>/dev/null | grep -c "$task_name.*succeeded" || echo "0")

    if [ "$log_count" -gt 0 ]; then
        return 0  # 已執行
    else
        return 1  # 未執行
    fi
}

# 觸發任務
trigger_task() {
    local task_name=$1
    local description=$2

    echo -e "${YELLOW}🔄 觸發任務: $description${NC}"
    echo "   任務名稱: app.tasks.$task_name"

    # 執行任務
    if docker compose exec -T backend celery -A app.core.celery_app call "app.tasks.$task_name" > /tmp/celery_trigger_${task_name}.log 2>&1; then
        local task_id=$(head -n 1 /tmp/celery_trigger_${task_name}.log)
        echo -e "${GREEN}   ✅ 任務已提交: $task_id${NC}"
        TRIGGERED_COUNT=$((TRIGGERED_COUNT + 1))
        return 0
    else
        echo -e "${RED}   ❌ 任務提交失敗${NC}"
        cat /tmp/celery_trigger_${task_name}.log
        FAILED_COUNT=$((FAILED_COUNT + 1))
        return 1
    fi
}

# 主邏輯：遍歷所有任務
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 檢查任務執行狀態"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

for task_name in "${!DAILY_TASKS[@]}"; do
    IFS='|' read -r task_time day_restriction description <<< "${DAILY_TASKS[$task_name]}"

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📌 檢查: $description"
    echo "   任務: app.tasks.$task_name"
    echo "   計劃執行時間: $task_time (台灣時間)"

    # 檢查是否應該今天執行
    if ! should_run_today "$day_restriction"; then
        echo -e "${BLUE}   ⏭️  跳過: 今天不在執行日期範圍內${NC}"
        echo ""
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        continue
    fi

    # 檢查時間是否已過
    if ! is_time_passed "$task_time"; then
        echo -e "${BLUE}   ⏱️  跳過: 執行時間尚未到達 (${task_time})${NC}"
        echo ""
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        continue
    fi

    # 檢查是否已執行
    if task_executed_today "$task_name"; then
        echo -e "${GREEN}   ✅ 已執行: 今天已成功執行過${NC}"
        echo ""
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        continue
    fi

    # 需要重新觸發
    echo -e "${YELLOW}   ⚠️  狀態: 應執行但未執行，準備重新觸發...${NC}"
    trigger_task "$task_name" "$description"
    echo ""

    # 避免一次觸發太多任務，稍微延遲
    sleep 2
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 執行總結"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}✅ 重新觸發: $TRIGGERED_COUNT 個任務${NC}"
echo -e "${BLUE}⏭️  已跳過: $SKIPPED_COUNT 個任務${NC}"
if [ "$FAILED_COUNT" -gt 0 ]; then
    echo -e "${RED}❌ 失敗: $FAILED_COUNT 個任務${NC}"
fi
echo ""

if [ "$TRIGGERED_COUNT" -gt 0 ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📝 後續步驟"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "1. 查看任務執行日誌:"
    echo "   docker compose logs -f celery-worker | grep -E 'succeeded|failed'"
    echo ""
    echo "2. 檢查活動任務:"
    echo "   docker compose exec backend celery -A app.core.celery_app inspect active"
    echo ""
    echo "3. 前往後台管理頁面查看:"
    echo "   http://localhost:3000/admin → 數據同步"
    echo ""
fi

echo "========================================"
echo "✅ 檢查完成"
echo "========================================"

# 返回退出碼
if [ "$FAILED_COUNT" -gt 0 ]; then
    exit 1
else
    exit 0
fi
