#!/bin/bash
# 手動觸發回測任務（測試用）
# 用途：直接從命令列觸發 Celery 回測任務

set -e

# 檢查參數
if [ $# -lt 2 ]; then
    echo "用法: $0 <backtest_id> <user_id>"
    echo ""
    echo "範例: $0 56 6"
    echo ""
    exit 1
fi

BACKTEST_ID=$1
USER_ID=$2

echo "🚀 手動觸發回測任務"
echo "================================"
echo "  回測 ID: $BACKTEST_ID"
echo "  使用者 ID: $USER_ID"
echo ""

# 檢查回測是否存在
echo "🔍 檢查回測記錄..."
BACKTEST_INFO=$(docker compose exec -T postgres psql -U quantlab quantlab -t -c "
SELECT id, name, status FROM backtests WHERE id = $BACKTEST_ID;
" 2>/dev/null)

if [ -z "$BACKTEST_INFO" ]; then
    echo "❌ 回測 ID $BACKTEST_ID 不存在"
    exit 1
fi

echo "📊 回測資訊："
echo "$BACKTEST_INFO"
echo ""

# 觸發任務
echo "🔄 觸發 Celery 任務..."
TASK_ID=$(docker compose exec backend python -c "
from app.core.celery_app import celery_app
from app.tasks.backtest import run_backtest_async

result = run_backtest_async.apply_async(args=[$BACKTEST_ID, $USER_ID])
print(result.id)
" 2>/dev/null | tail -1)

echo "✅ 任務已發送！"
echo "  Task ID: $TASK_ID"
echo ""

# 等待並檢查執行
echo "⏳ 等待任務執行..."
sleep 2

echo ""
echo "📋 檢查 Celery 日誌："
docker compose logs --tail 10 celery-worker | grep -E "(Task.*$TASK_ID|Celery task started|ERROR)" || echo "（無相關日誌）"

echo ""
echo "💡 提示："
echo "  - 查看完整日誌: docker compose logs -f celery-worker"
echo "  - 檢查任務狀態: ./scripts/check-celery.sh"
echo "  - 檢查回測狀態: ./scripts/check-backtests.sh"
