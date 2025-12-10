#!/bin/bash
# 檢查回測狀態
# 用途：查看最近的回測記錄、失敗的回測、pending 的回測等

set -e

echo "🔍 檢查回測狀態"
echo "================================"
echo ""

# 最近的回測
echo "📊 最近 10 個回測："
docker compose exec -T postgres psql -U quantlab quantlab -c "
SELECT
    id,
    name,
    strategy_id,
    symbol,
    status,
    TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as created
FROM backtests
ORDER BY created_at DESC
LIMIT 10;
" 2>/dev/null
echo ""

# Pending 回測
echo "⏳ PENDING 狀態的回測："
docker compose exec -T postgres psql -U quantlab quantlab -c "
SELECT
    id,
    name,
    strategy_id,
    status,
    TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as created
FROM backtests
WHERE status = 'PENDING'
ORDER BY created_at DESC;
" 2>/dev/null || echo "無 PENDING 回測"
echo ""

# Running 回測
echo "🏃 RUNNING 狀態的回測："
docker compose exec -T postgres psql -U quantlab quantlab -c "
SELECT
    id,
    name,
    strategy_id,
    status,
    TO_CHAR(started_at, 'YYYY-MM-DD HH24:MI:SS') as started
FROM backtests
WHERE status = 'RUNNING'
ORDER BY started_at DESC;
" 2>/dev/null || echo "無 RUNNING 回測"
echo ""

# Failed 回測
echo "❌ FAILED 狀態的回測（最近 5 個）："
docker compose exec -T postgres psql -U quantlab quantlab -c "
SELECT
    id,
    name,
    strategy_id,
    status,
    LEFT(error_message, 50) as error,
    TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as created
FROM backtests
WHERE status = 'FAILED'
ORDER BY created_at DESC
LIMIT 5;
" 2>/dev/null || echo "無 FAILED 回測"
echo ""

# 統計
echo "📈 回測狀態統計："
docker compose exec -T postgres psql -U quantlab quantlab -c "
SELECT
    status,
    COUNT(*) as count
FROM backtests
GROUP BY status
ORDER BY count DESC;
" 2>/dev/null
echo ""

echo "✅ 檢查完成！"
