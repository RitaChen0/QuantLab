#!/bin/bash
# 策略監控功能診斷腳本

echo "=================================="
echo "📊 策略監控功能診斷報告"
echo "=================================="
echo ""

echo "1️⃣ 當前時間"
echo "-----------------------------------"
date "+時間: %Y-%m-%d %H:%M:%S (%A)"
echo ""

echo "2️⃣ ACTIVE 策略統計"
echo "-----------------------------------"
docker compose exec -T postgres psql -U quantlab quantlab -c "
SELECT
  engine_type,
  COUNT(*) as total,
  COUNT(CASE WHEN parameters::text LIKE '%\"stocks\"%' THEN 1 END) as with_stocks
FROM strategies
WHERE status = 'ACTIVE'
GROUP BY engine_type;
"
echo ""

echo "3️⃣ 監控任務執行記錄（最近 10 次）"
echo "-----------------------------------"
docker compose logs celery-worker --tail 500 | grep "STRATEGY_MONITOR" | tail -10
echo ""

echo "4️⃣ Celery Beat 排程狀態"
echo "-----------------------------------"
docker compose logs celery-beat --tail 50 | grep "monitor-strategies" | tail -5
echo ""

echo "5️⃣ 檢測到的信號記錄（最近 10 筆）"
echo "-----------------------------------"
docker compose exec -T postgres psql -U quantlab quantlab -c "
SELECT
  s.name as strategy_name,
  sg.stock_id,
  sg.signal_type,
  sg.price,
  sg.detected_at,
  sg.notified
FROM strategy_signals sg
JOIN strategies s ON sg.strategy_id = s.id
ORDER BY sg.detected_at DESC
LIMIT 10;
"
echo ""

echo "6️⃣ 問題診斷"
echo "-----------------------------------"

# 檢查是否有配置 stocks 的策略
stocks_count=$(docker compose exec -T postgres psql -U quantlab quantlab -t -c "
SELECT COUNT(*)
FROM strategies
WHERE status = 'ACTIVE'
  AND engine_type = 'backtrader'
  AND parameters::text LIKE '%\"stocks\"%';
" | tr -d ' ')

if [ "$stocks_count" -eq 0 ]; then
  echo "❌ 問題發現: 沒有任何 ACTIVE 策略配置了 stocks 參數"
  echo ""
  echo "📝 解決方案："
  echo "   策略監控功能需要在策略的 parameters 中配置 stocks 陣列"
  echo "   範例："
  echo "   {"
  echo "     \"stocks\": [\"2330\", \"2317\", \"2454\"],"
  echo "     \"short_period\": 5,"
  echo "     \"long_period\": 20"
  echo "   }"
  echo ""
  echo "   你可以在策略編輯頁面的「參數配置」中添加 stocks 欄位。"
else
  echo "✅ 已找到 $stocks_count 個配置了 stocks 的 ACTIVE 策略"
fi

echo ""
echo "=================================="
echo "✅ 診斷完成"
echo "=================================="
