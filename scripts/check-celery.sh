#!/bin/bash
# 檢查 Celery Worker 狀態
# 用途：診斷 Celery worker 健康狀態、活躍任務、速率限制等

set -e

echo "🔍 檢查 Celery Worker 狀態"
echo "================================"
echo ""

# 檢查容器狀態
echo "📦 容器狀態："
docker compose ps celery-worker
echo ""

# 檢查 worker 是否在線
echo "🏃 Worker 狀態："
docker compose exec celery-worker celery -A app.core.celery_app inspect ping 2>/dev/null || {
    echo "❌ Worker 未回應"
    echo ""
    echo "📋 最近的錯誤日誌："
    docker compose logs --tail 20 celery-worker | grep -E "(ERROR|WARNING)" || echo "無錯誤日誌"
    exit 1
}
echo ""

# 檢查活躍任務
echo "🔄 活躍任務："
docker compose exec celery-worker celery -A app.core.celery_app inspect active 2>/dev/null | grep -A 5 "celery@" || echo "無活躍任務"
echo ""

# 檢查保留任務
echo "📝 保留任務（已接收但未執行）："
docker compose exec celery-worker celery -A app.core.celery_app inspect reserved 2>/dev/null | grep -A 5 "celery@" || echo "無保留任務"
echo ""

# 檢查註冊的任務及速率限制
echo "📋 註冊的任務："
docker compose exec celery-worker celery -A app.core.celery_app inspect registered 2>/dev/null | grep -E "(run_backtest|rate_limit)" | head -10
echo ""

# 檢查 worker 統計
echo "📊 Worker 統計："
docker compose exec celery-worker celery -A app.core.celery_app inspect stats 2>/dev/null | grep -E "(total|pool)" | head -10
echo ""

# 檢查隊列長度
echo "📬 Redis 隊列長度："
echo -n "  - celery: "
docker compose exec redis redis-cli LLEN celery 2>/dev/null || echo "N/A"
echo -n "  - backtest: "
docker compose exec redis redis-cli LLEN backtest 2>/dev/null || echo "N/A"
echo -n "  - data_sync: "
docker compose exec redis redis-cli LLEN data_sync 2>/dev/null || echo "N/A"
echo ""

echo "✅ 檢查完成！"
