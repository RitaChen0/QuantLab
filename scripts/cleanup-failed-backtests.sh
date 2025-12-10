#!/bin/bash
# 清理失敗的回測記錄
# 用途：刪除 FAILED 狀態的回測，釋放資料庫空間

set -e

echo "🧹 清理失敗的回測記錄"
echo "================================"
echo ""

# 顯示將要刪除的回測
echo "📋 即將刪除的 FAILED 回測："
docker compose exec -T postgres psql -U quantlab quantlab -c "
SELECT
    id,
    name,
    strategy_id,
    LEFT(error_message, 50) as error,
    TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') as created
FROM backtests
WHERE status = 'FAILED'
ORDER BY created_at DESC;
" 2>/dev/null

# 確認
echo ""
read -p "確定要刪除這些回測嗎？(y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 已取消"
    exit 0
fi

# 執行刪除
echo "🗑️  刪除中..."
DELETED=$(docker compose exec -T postgres psql -U quantlab quantlab -t -c "
DELETE FROM backtests WHERE status = 'FAILED';
SELECT ROW_COUNT();
" 2>/dev/null | tr -d ' \n')

echo ""
echo "✅ 已刪除 $DELETED 個失敗的回測記錄"
echo ""

# 顯示剩餘回測統計
echo "📊 剩餘回測統計："
docker compose exec -T postgres psql -U quantlab quantlab -c "
SELECT
    status,
    COUNT(*) as count
FROM backtests
GROUP BY status
ORDER BY count DESC;
" 2>/dev/null

echo ""
echo "✅ 清理完成！"
