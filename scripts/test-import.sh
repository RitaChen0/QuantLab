#!/bin/bash
# 快速測試 Shioaji CSV 匯入功能
# 僅匯入 3 檔股票（2330、2317、2454）作為驗證

set -e

echo "=========================================="
echo "🧪 Shioaji CSV Import Test"
echo "=========================================="
echo ""
echo "📊 Will import 3 stocks: 2330, 2317, 2454"
echo "⏱️  Estimated time: 1-2 minutes"
echo ""
read -p "Press Enter to start..."

cd /home/ubuntu/QuantLab/backend

# 執行測試匯入
docker compose exec backend python scripts/import_shioaji_csv.py \
  --stocks 2330,2317,2454 \
  --batch-size 10000 \
  --verbose

echo ""
echo "=========================================="
echo "✅ Test Import Completed!"
echo "=========================================="
echo ""
echo "📊 Verify data in PostgreSQL:"
echo ""
echo "docker compose exec postgres psql -U quantlab quantlab -c \\"
echo "  SELECT stock_id, COUNT(*) as records, MIN(datetime) as start_date, MAX(datetime) as end_date \\"
echo "  FROM stock_minute_prices \\"
echo "  WHERE stock_id IN ('2330', '2317', '2454') \\"
echo "  GROUP BY stock_id \\"
echo "  ORDER BY stock_id;\\"
echo ""
