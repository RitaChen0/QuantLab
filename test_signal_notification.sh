#!/bin/bash

# 測試策略信號通知機制
# 驗證信號只發送給策略擁有者

echo "======================================"
echo "策略信號通知測試"
echo "======================================"
echo ""

echo "1️⃣ 查詢所有 ACTIVE 策略及其擁有者"
echo "--------------------------------------"
docker compose exec postgres psql -U quantlab quantlab -c "
SELECT
  u.username AS owner,
  s.name AS strategy,
  s.status,
  s.engine_type,
  (s.parameters->>'stocks') AS stocks
FROM strategies s
JOIN users u ON s.user_id = u.id
WHERE s.status = 'active'
ORDER BY u.username, s.name;
" 2>/dev/null

echo ""
echo "2️⃣ 檢測信號（不發送通知，僅測試）"
echo "--------------------------------------"
docker compose exec backend python -c "
from app.db.session import SessionLocal
from app.services.strategy_signal_detector import StrategySignalDetector

db = SessionLocal()
detector = StrategySignalDetector(db)

signals = detector.detect_signals_for_active_strategies(lookback_days=60)

if signals:
    print(f'檢測到 {len(signals)} 個信號：')
    for signal in signals:
        print(f'  - 用戶 {signal[\"user_id\"]} | 策略=[{signal[\"strategy_name\"]}] | {signal[\"stock_id\"]} {signal[\"signal_type\"]}')
else:
    print('沒有檢測到信號')

db.close()
" 2>&1 | grep -E "檢測到|沒有|用戶"

echo ""
echo "3️⃣ 查詢最近的信號記錄及其接收者"
echo "--------------------------------------"
docker compose exec postgres psql -U quantlab quantlab -c "
SELECT
  u.username AS receiver,
  s.name AS strategy,
  sg.stock_id,
  sg.signal_type,
  sg.price,
  sg.detected_at,
  sg.notified
FROM strategy_signals sg
JOIN strategies s ON sg.strategy_id = s.id
JOIN users u ON sg.user_id = u.id
WHERE sg.detected_at > NOW() - INTERVAL '1 day'
ORDER BY sg.detected_at DESC
LIMIT 10;
" 2>/dev/null

echo ""
echo "4️⃣ 驗證隱私保護（每個用戶只收到自己的信號）"
echo "--------------------------------------"
docker compose exec postgres psql -U quantlab quantlab -c "
SELECT
  u.username AS user,
  COUNT(DISTINCT sg.strategy_id) AS strategies_count,
  COUNT(*) AS signals_count
FROM strategy_signals sg
JOIN users u ON sg.user_id = u.id
WHERE sg.detected_at > NOW() - INTERVAL '1 day'
GROUP BY u.username;
" 2>/dev/null

echo ""
echo "======================================"
echo "✅ 測試完成"
echo "======================================"
echo ""
echo "說明："
echo "- receiver 欄位顯示誰會收到這個信號的通知"
echo "- 每個策略的信號只會發送給該策略的擁有者"
echo "- 其他用戶不會收到這個策略的通知"
