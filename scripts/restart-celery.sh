#!/bin/bash
# 重啟 Celery Worker
# 用途：當代碼更新後需要重新載入 Celery worker

set -e

echo "🔄 重啟 Celery Worker..."
docker compose restart celery-worker

echo "⏳ 等待 Worker 啟動..."
sleep 3

echo "✅ 檢查 Worker 狀態..."
docker compose exec celery-worker celery -A app.core.celery_app inspect ping || {
    echo "❌ Worker 未正常啟動，查看日誌："
    docker compose logs --tail 30 celery-worker
    exit 1
}

echo ""
echo "✅ Celery Worker 重啟完成！"
echo ""
echo "📊 當前註冊的任務："
docker compose exec celery-worker celery -A app.core.celery_app inspect registered | grep "^\s*\*" | head -10
