#!/bin/bash
# Celery 監控腳本

echo "===================================="
echo "📊 Celery 任務監控"
echo "===================================="
echo ""

# 檢查服務狀態
echo "1️⃣  服務狀態:"
docker compose ps celery-worker celery-beat | tail -n +2
echo ""

# 檢查最近的任務執行
echo "2️⃣  最近 5 個任務執行結果:"
docker compose logs --tail=200 celery-worker 2>&1 | \
    grep "Task.*succeeded\|Task.*failed" | \
    tail -5
echo ""

# 檢查是否有錯誤
echo "3️⃣  錯誤檢查 (最近 1 小時):"
ERROR_LOGS=$(docker compose logs --since 1h celery-worker celery-beat 2>&1 | \
    grep -E "ERROR|CRITICAL|Exception" | \
    grep -v "ImportError: cannot import name 'sync_stock_data'" || true)

if [ -z "$ERROR_LOGS" ]; then
    echo "   ✅ 沒有發現錯誤"
else
    echo "   ⚠️  發現錯誤:"
    echo "$ERROR_LOGS" | tail -5
fi
echo ""

# 顯示任務統計
echo "4️⃣  任務執行統計 (最近 1 小時):"
SUCCEEDED=$(docker compose logs --since 1h celery-worker 2>&1 | grep -c "succeeded" || echo "0")
FAILED=$(docker compose logs --since 1h celery-worker 2>&1 | grep -c "failed" || echo "0")
echo "   ✅ 成功: $SUCCEEDED"
echo "   ❌ 失敗: $FAILED"
echo ""

echo "===================================="
echo "💡 提示: 使用以下指令實時監控日誌"
echo "   docker compose logs -f celery-worker celery-beat"
echo "===================================="
