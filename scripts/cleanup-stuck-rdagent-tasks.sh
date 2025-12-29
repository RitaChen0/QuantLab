#!/bin/bash

# ========================================
# RD-Agent 卡住任務自動清理腳本
# ========================================
# 用途：清理執行超過 24 小時仍處於 RUNNING 狀態的 RD-Agent 任務
# 使用：./scripts/cleanup-stuck-rdagent-tasks.sh
# 或加入 cron：每天 03:00 執行
# ========================================

set -e

echo "============================================"
echo "🧹 RD-Agent 卡住任務清理工具"
echo "============================================"
echo ""

# 設定超時時間（秒）- 預設 24 小時
TIMEOUT_SECONDS=${1:-86400}
TIMEOUT_HOURS=$((TIMEOUT_SECONDS / 3600))

echo "⏱️  超時設定: ${TIMEOUT_HOURS} 小時 (${TIMEOUT_SECONDS} 秒)"
echo ""

# 查詢卡住的任務
echo "🔍 檢查卡住的任務..."
STUCK_TASKS=$(docker compose exec -T postgres psql -U quantlab quantlab -t -c "
SELECT COUNT(*)
FROM rdagent_tasks
WHERE status = 'RUNNING'
  AND EXTRACT(EPOCH FROM (NOW() - started_at)) > ${TIMEOUT_SECONDS};
")

STUCK_COUNT=$(echo "$STUCK_TASKS" | xargs)

if [ "$STUCK_COUNT" -eq 0 ]; then
    echo "✅ 沒有卡住的任務"
    exit 0
fi

echo "⚠️  發現 ${STUCK_COUNT} 個卡住的任務"
echo ""

# 顯示卡住的任務詳情
echo "📋 卡住任務詳情："
docker compose exec -T postgres psql -U quantlab quantlab -c "
SELECT
    id,
    task_type,
    user_id,
    created_at,
    started_at,
    ROUND(EXTRACT(EPOCH FROM (NOW() - started_at)) / 3600, 2) as running_hours
FROM rdagent_tasks
WHERE status = 'RUNNING'
  AND EXTRACT(EPOCH FROM (NOW() - started_at)) > ${TIMEOUT_SECONDS}
ORDER BY started_at;
"

echo ""
echo "🔧 清理這些任務..."

# 更新任務狀態為 FAILED
docker compose exec -T postgres psql -U quantlab quantlab -c "
UPDATE rdagent_tasks
SET status = 'FAILED',
    error_message = 'Task timeout after ${TIMEOUT_HOURS} hours (auto-cleanup on ' || NOW()::date || ')',
    completed_at = NOW()
WHERE status = 'RUNNING'
  AND EXTRACT(EPOCH FROM (NOW() - started_at)) > ${TIMEOUT_SECONDS}
RETURNING id, task_type, error_message;
"

echo ""
echo "✅ 清理完成！"
echo ""

# 檢查 Celery Worker 狀態
echo "🔍 檢查 Celery Worker 狀態..."
ACTIVE_TASKS=$(docker compose exec backend celery -A app.core.celery_app inspect active 2>&1 | grep -c "empty" || echo "0")

if [ "$ACTIVE_TASKS" -gt 0 ]; then
    echo "✅ Celery Worker 無活躍任務"
else
    echo "⚠️  Celery Worker 有活躍任務，可能需要重啟"
    echo ""
    echo "建議執行："
    echo "  docker compose restart celery-worker celery-beat"
fi

echo ""
echo "============================================"
echo "📊 RD-Agent 任務統計"
echo "============================================"

docker compose exec -T postgres psql -U quantlab quantlab -c "
SELECT
    status,
    COUNT(*) as count,
    ROUND(AVG(EXTRACT(EPOCH FROM (COALESCE(completed_at, NOW()) - created_at))), 0) as avg_duration_sec
FROM rdagent_tasks
GROUP BY status
ORDER BY status;
"

echo ""
echo "✨ 完成！"
