#!/bin/bash
# 回測失敗診斷工具

echo "🔍 回測失敗診斷工具"
echo "===================="
echo ""

# 1. 檢查回測配置
echo "📋 回測 #15 配置："
docker compose exec postgres psql -U quantlab -d quantlab -t -c "
SELECT
    '  ID: ' || id ||
    '\n  名稱: ' || name ||
    '\n  股票: ' || symbol ||
    '\n  日期: ' || start_date || ' ~ ' || end_date ||
    '\n  狀態: ' || status ||
    '\n  策略 ID: ' || strategy_id
FROM backtests WHERE id = 15;
"
echo ""

# 2. 檢查策略代碼
echo "📝 策略代碼："
docker compose exec postgres psql -U quantlab -d quantlab -t -c "
SELECT code
FROM strategies
WHERE id = (SELECT strategy_id FROM backtests WHERE id = 15);
" | head -20
echo ""

# 3. 檢查數據範圍
echo "📊 2330 數據範圍："
docker compose exec postgres psql -U quantlab -d quantlab -t -c "
SELECT
    '  最早日期: ' || MIN(date) ||
    '\n  最新日期: ' || MAX(date) ||
    '\n  總記錄數: ' || COUNT(*)
FROM stock_prices WHERE stock_id = '2330';
"
echo ""

# 4. 檢查最近的錯誤日誌
echo "🔴 最近的錯誤日誌："
docker compose logs celery-worker --tail 50 | grep -i "error\|failed" | tail -10
echo ""

# 5. 檢查 Python 代碼版本
echo "💻 代碼檢查："
echo "  日期處理邏輯："
docker compose exec backend grep -A 3 "先查詢該股票在資料庫中的實際日期範圍" /app/app/services/backtest_engine.py | head -5
echo ""

echo "✅ 診斷完成"
