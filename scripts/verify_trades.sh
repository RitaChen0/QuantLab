#!/bin/bash
# 驗證回測交易記錄腳本

echo "========================================="
echo "回測交易記錄驗證工具"
echo "========================================="
echo ""

# 檢查參數
BACKTEST_ID=${1:-16}

echo "檢查回測 ID: $BACKTEST_ID"
echo ""

# 1. 檢查回測基本信息
echo "1️⃣  回測基本信息："
docker compose exec postgres psql -U quantlab -d quantlab -c \
  "SELECT id, name, symbol, status,
          TO_CHAR(start_date, 'YYYY-MM-DD') as start_date,
          TO_CHAR(end_date, 'YYYY-MM-DD') as end_date
   FROM backtests WHERE id = $BACKTEST_ID;"

echo ""

# 2. 檢查回測結果
echo "2️⃣  回測績效結果："
docker compose exec postgres psql -U quantlab -d quantlab -c \
  "SELECT total_return, sharpe_ratio, max_drawdown, win_rate,
          total_trades, winning_trades, losing_trades,
          average_profit, average_loss
   FROM backtest_results WHERE backtest_id = $BACKTEST_ID;"

echo ""

# 3. 檢查交易記錄數量
echo "3️⃣  交易記錄統計："
docker compose exec postgres psql -U quantlab -d quantlab -c \
  "SELECT
     COUNT(*) as total_records,
     SUM(CASE WHEN action = 'buy' THEN 1 ELSE 0 END) as buy_count,
     SUM(CASE WHEN action = 'sell' THEN 1 ELSE 0 END) as sell_count
   FROM trades WHERE backtest_id = $BACKTEST_ID;"

echo ""

# 4. 顯示詳細交易記錄（前10筆）
echo "4️⃣  交易記錄詳情（前 10 筆 BUY）："
docker compose exec postgres psql -U quantlab -d quantlab -c \
  "SELECT
     TO_CHAR(date, 'YYYY-MM-DD') as date,
     action,
     quantity,
     price,
     commission,
     total_amount,
     profit_loss
   FROM trades
   WHERE backtest_id = $BACKTEST_ID AND action = 'buy'
   ORDER BY date
   LIMIT 10;"

echo ""

echo "5️⃣  交易記錄詳情（前 10 筆 SELL）："
docker compose exec postgres psql -U quantlab -d quantlab -c \
  "SELECT
     TO_CHAR(date, 'YYYY-MM-DD') as date,
     action,
     quantity,
     price,
     commission,
     total_amount,
     profit_loss
   FROM trades
   WHERE backtest_id = $BACKTEST_ID AND action = 'sell'
   ORDER BY date
   LIMIT 10;"

echo ""

# 6. 配對顯示完整交易（進出場配對）
echo "6️⃣  完整交易配對（前 5 組）："
docker compose exec postgres psql -U quantlab -d quantlab -c \
  "WITH buy_trades AS (
     SELECT
       ROW_NUMBER() OVER (ORDER BY date) as rn,
       TO_CHAR(date, 'YYYY-MM-DD') as entry_date,
       price as entry_price,
       quantity
     FROM trades
     WHERE backtest_id = $BACKTEST_ID AND action = 'buy'
   ),
   sell_trades AS (
     SELECT
       ROW_NUMBER() OVER (ORDER BY date) as rn,
       TO_CHAR(date, 'YYYY-MM-DD') as exit_date,
       price as exit_price,
       profit_loss
     FROM trades
     WHERE backtest_id = $BACKTEST_ID AND action = 'sell'
   )
   SELECT
     b.rn as trade_no,
     b.entry_date,
     b.entry_price,
     s.exit_date,
     s.exit_price,
     b.quantity,
     s.profit_loss,
     EXTRACT(DAY FROM (s.exit_date::date - b.entry_date::date)) as holding_days
   FROM buy_trades b
   JOIN sell_trades s ON b.rn = s.rn
   LIMIT 5;"

echo ""
echo "========================================="
echo "驗證完成！"
echo "========================================="
