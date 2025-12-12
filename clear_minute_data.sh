#!/bin/bash
# 清空分鐘線資料表，準備重新匯入

set -e

echo "================================================"
echo "⚠️  清空分鐘線資料表"
echo "================================================"
echo ""
echo "此操作將刪除 stock_minute_prices 資料表中的所有資料！"
echo ""
read -p "確定要繼續嗎？(yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "操作已取消"
    exit 0
fi

echo ""
echo "🗑️  清空資料表..."

# 清空資料表（保留結構）
docker compose exec postgres psql -U quantlab quantlab -c "TRUNCATE TABLE stock_minute_prices;"

echo ""
echo "✅ 資料表已清空"
echo ""

# 驗證
RECORD_COUNT=$(docker compose exec -T postgres psql -U quantlab quantlab -t -c "SELECT COUNT(*) FROM stock_minute_prices;" | xargs)

echo "📊 當前記錄數: $RECORD_COUNT"
echo ""
echo "現在可以執行 ./import_full.sh 開始完整匯入"
echo ""
