#!/bin/bash
# 重新導入失敗的 637 個股票

# 從日誌提取失敗的股票代碼
FAILED_STOCKS="4979,4987,4989,4991,4994,4995,4999,5007,5009,5011,5013,5014,5015,5016,5102,5201,5202,5203,5205,5206,5209,5210,5211,5212,5213,5215,5220,5223,5225,5227,5230,5234,5243,5245,5251,5258,5259,5263,5264,5269,5272,5274,5276,5278,5281,5284,5285,5287,5288,5289"

echo "🔄 Retrying failed stocks import..."
echo "📊 Stocks to retry: $(echo $FAILED_STOCKS | tr ',' '\n' | wc -l)"

docker compose exec -T backend python3 scripts/import_shioaji_csv.py \
    --stocks "$FAILED_STOCKS" \
    --incremental \
    --batch-size 10000

echo "✅ Retry completed!"
