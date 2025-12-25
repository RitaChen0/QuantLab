#!/bin/bash
# TX 期貨日線系統健康檢查腳本
# 用途：快速診斷系統狀態，發現潛在問題
# 使用：bash check_tx_health.sh

echo "🔍 TX 期貨日線系統健康檢查"
echo "================================"
echo ""

# 檢查 1：Celery 服務狀態
echo "1️⃣ Celery 服務狀態"
echo "-------------------"
docker compose ps celery-worker celery-beat | tail -n +2
echo ""

# 檢查 2：任務註冊狀態
echo "2️⃣ 任務註冊狀態"
echo "-------------------"
TASK_REGISTERED=$(docker compose exec backend celery -A app.core.celery_app inspect registered 2>/dev/null | grep "generate_tx_daily_from_minute")
if [ -n "$TASK_REGISTERED" ]; then
    echo "✅ app.tasks.generate_tx_daily_from_minute 已註冊"
else
    echo "❌ 任務未註冊（請檢查 backend/app/tasks/__init__.py）"
fi
echo ""

# 檢查 3：定時排程
echo "3️⃣ 定時排程配置"
echo "-------------------"
SCHEDULE=$(docker compose logs celery-beat --tail 100 2>/dev/null | grep "generate-tx-daily-from-minute" | tail -1)
if [ -n "$SCHEDULE" ]; then
    echo "✅ 定時排程已載入："
    echo "   $SCHEDULE"
else
    echo "❌ 定時排程未找到（請檢查 backend/app/core/celery_app.py）"
fi
echo ""

# 檢查 4：PostgreSQL 分鐘線數據
echo "4️⃣ PostgreSQL 分鐘線數據範圍"
echo "-------------------"
docker compose exec postgres psql -U quantlab quantlab -c "
SELECT stock_id,
       COUNT(*) as bars,
       MIN(datetime::date) as earliest,
       MAX(datetime::date) as latest,
       COUNT(DISTINCT datetime::date) as trading_days
FROM stock_minute_prices
WHERE stock_id IN ('TX202512', 'TX202601', 'TX202602')
GROUP BY stock_id
ORDER BY latest DESC;" 2>/dev/null
echo ""

# 檢查 5：Qlib 日線檔案
echo "5️⃣ Qlib 日線檔案"
echo "-------------------"
if [ -d "/data/qlib/tw_stock_v2/features/tx" ]; then
    ls -lh /data/qlib/tw_stock_v2/features/tx/ | grep ".day.bin"
    echo ""
    echo "檔案更新時間："
    stat -c '%y %n' /data/qlib/tw_stock_v2/features/tx/close.day.bin 2>/dev/null | head -1
else
    echo "❌ TX 目錄不存在：/data/qlib/tw_stock_v2/features/tx/"
fi
echo ""

# 檢查 6：Qlib 數據讀取測試
echo "6️⃣ Qlib 數據讀取測試"
echo "-------------------"
QLIB_TEST=$(docker compose exec backend python -c "
import qlib
from qlib.data import D
qlib.init(provider_uri='/data/qlib/tw_stock_v2', region='tw')
df = D.features(['tx'], ['\$close'], start_time='2025-12-01')
print(f'交易日數：{len(df)}')
print(f'最新日期：{df.index.get_level_values(1).max()}')
print(f'缺失值：{df.isnull().sum().sum()} 筆')
" 2>&1 | grep -v "WARNING" | grep -v "UserWarning" | grep -v "INFO" | tail -3)

if [ -n "$QLIB_TEST" ]; then
    echo "✅ Qlib 讀取成功："
    echo "$QLIB_TEST" | sed 's/^/   /'
else
    echo "❌ Qlib 讀取失敗"
fi
echo ""

# 檢查 7：最近任務執行記錄
echo "7️⃣ 最近任務執行記錄（最近 5 筆）"
echo "-------------------"
RECENT_LOGS=$(docker compose logs celery-worker --tail 200 2>/dev/null | grep "TX 期貨日線" | tail -5)
if [ -n "$RECENT_LOGS" ]; then
    echo "$RECENT_LOGS"
else
    echo "❌ 未找到任務執行記錄（可能尚未執行過）"
fi
echo ""

# 檢查 8：磁碟空間
echo "8️⃣ 磁碟空間使用率"
echo "-------------------"
df -h /data 2>/dev/null | tail -1 || df -h / | tail -1
echo ""

# 總結
echo "================================"
echo "✅ 健康檢查完成"
echo ""
echo "💡 提示："
echo "   - 如發現問題，請參考 /tmp/TX_TROUBLESHOOTING_GUIDE.md"
echo "   - 手動執行聚合：docker compose exec backend python /app/scripts/generate_tx_daily_from_minute.py --contract TX202601"
echo "   - 重啟服務：docker compose restart celery-worker celery-beat"
