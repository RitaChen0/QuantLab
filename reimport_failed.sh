#!/bin/bash
# 重新導入 547 個真正失敗的股票

STOCKS=$(cat /tmp/stocks_to_reimport.txt)

echo "🔄 開始重新導入 547 個失敗股票..."
echo "預計時間: 60-90 分鐘"
echo ""

docker compose exec -T backend python3 scripts/import_shioaji_csv.py \
    --stocks "$STOCKS" \
    --incremental \
    --batch-size 10000
