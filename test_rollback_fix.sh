#!/bin/bash
# 測試 rollback 修復是否有效 - 使用前 10 個失敗的股票

echo "🧪 Testing rollback fix with 10 failed stocks..."

docker compose exec -T backend python3 scripts/import_shioaji_csv.py \
    --stocks "4979,4987,4989,4991,4994,4995,4999,5007,5009,5011" \
    --incremental \
    --batch-size 5000

echo ""
echo "✅ Test completed!"
echo "📊 Check the output above to see if all 10 stocks were imported successfully"
