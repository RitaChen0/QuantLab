#!/bin/bash
# 快速測試：匯入 3 檔股票驗證系統正常

set -e

echo "================================================"
echo "🧪 Shioaji 匯入測試（3 檔股票）"
echo "================================================"
echo ""

# 執行測試匯入
docker compose exec -T backend python /app/scripts/import_shioaji_csv.py \
    --data-dir /data/shioaji/shioaji-stock \
    --limit 3 \
    --batch-size 50000 \
    2>&1 | grep -E "(Found|Import|Inserted|Statistics|Completed)"

echo ""
echo "================================================"
echo "✅ 測試完成"
echo "================================================"
echo ""

# 檢查資料庫
echo "📊 資料庫驗證："
docker compose exec postgres psql -U quantlab quantlab -c \
  "SELECT stock_id, COUNT(*) as records
   FROM stock_minute_prices
   GROUP BY stock_id
   ORDER BY stock_id
   LIMIT 10;"

echo ""
echo "如果測試正常，執行 ./import_full.sh 開始完整匯入"
echo ""
