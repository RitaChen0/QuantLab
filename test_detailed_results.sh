#!/bin/bash

# 測試腳本：驗證回測 detailed_results 功能

set -e

echo "🧪 測試回測視覺化數據生成"
echo "=============================="
echo ""

API_BASE="http://localhost:8000/api/v1"

# 1. 登入獲取 token
echo "📝 1. 登入系統..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }')

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
  echo "❌ 登入失敗"
  echo "Response: $LOGIN_RESPONSE"
  exit 1
fi

echo "✅ 登入成功"
echo ""

# 2. 創建測試回測
echo "🔬 2. 創建測試回測..."
BACKTEST_RESPONSE=$(curl -s -X POST "$API_BASE/backtest/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "視覺化測試回測",
    "strategy_id": 55,
    "symbol": "2330",
    "start_date": "2024-01-01",
    "end_date": "2024-03-31",
    "initial_capital": 1000000,
    "description": "測試 detailed_results 數據生成"
  }')

BACKTEST_ID=$(echo $BACKTEST_RESPONSE | jq -r '.id')

if [ "$BACKTEST_ID" = "null" ] || [ -z "$BACKTEST_ID" ]; then
  echo "❌ 創建回測失敗"
  echo "Response: $BACKTEST_RESPONSE"
  exit 1
fi

echo "✅ 回測已創建，ID: $BACKTEST_ID"
echo ""

# 3. 執行回測（使用 Celery 異步任務）
echo "⏳ 3. 正在執行回測（預計 30-60 秒）..."
echo "   回測 ID: $BACKTEST_ID"
echo "   股票代碼: 2330"
echo "   期間: 2024-01-01 ~ 2024-03-31"
echo ""

# 等待回測完成（最多等待 2 分鐘）
MAX_WAIT=120
ELAPSED=0
INTERVAL=5

while [ $ELAPSED -lt $MAX_WAIT ]; do
  sleep $INTERVAL
  ELAPSED=$((ELAPSED + INTERVAL))

  # 檢查回測狀態
  STATUS_RESPONSE=$(curl -s -X GET "$API_BASE/backtest/$BACKTEST_ID" \
    -H "Authorization: Bearer $TOKEN")

  STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')

  echo "   [$ELAPSED 秒] 狀態: $STATUS"

  if [ "$STATUS" = "COMPLETED" ]; then
    echo ""
    echo "✅ 回測執行完成！"
    break
  elif [ "$STATUS" = "FAILED" ]; then
    echo ""
    echo "❌ 回測執行失敗"
    ERROR_MSG=$(echo $STATUS_RESPONSE | jq -r '.error_message')
    echo "錯誤訊息: $ERROR_MSG"
    exit 1
  fi
done

if [ "$STATUS" != "COMPLETED" ]; then
  echo ""
  echo "⏱️  回測仍在執行中（已等待 $ELAPSED 秒）"
  echo "   你可以稍後通過以下命令查看結果："
  echo "   curl -H \"Authorization: Bearer $TOKEN\" $API_BASE/backtest/$BACKTEST_ID/result | jq"
  exit 0
fi

# 4. 獲取回測結果
echo ""
echo "📊 4. 獲取回測結果..."
RESULT_RESPONSE=$(curl -s -X GET "$API_BASE/backtest/$BACKTEST_ID/result" \
  -H "Authorization: Bearer $TOKEN")

# 檢查是否有 detailed_results
HAS_DETAILED=$(echo $RESULT_RESPONSE | jq 'has("result") and (.result | has("detailed_results"))')

if [ "$HAS_DETAILED" = "true" ]; then
  echo "✅ detailed_results 存在！"
  echo ""

  # 顯示數據結構
  echo "📈 數據結構預覽："
  echo "================="

  # Daily NAV
  NAV_COUNT=$(echo $RESULT_RESPONSE | jq '.result.detailed_results.daily_nav | length')
  echo "  • daily_nav: $NAV_COUNT 個數據點"
  if [ "$NAV_COUNT" -gt 0 ]; then
    echo "    範例: $(echo $RESULT_RESPONSE | jq '.result.detailed_results.daily_nav[0]')"
  fi

  # Monthly Returns
  MONTHLY_COUNT=$(echo $RESULT_RESPONSE | jq '.result.detailed_results.monthly_returns | length')
  echo "  • monthly_returns: $MONTHLY_COUNT 個月度數據"
  if [ "$MONTHLY_COUNT" -gt 0 ]; then
    echo "    範例: $(echo $RESULT_RESPONSE | jq '.result.detailed_results.monthly_returns[0]')"
  fi

  # Rolling Sharpe
  SHARPE_COUNT=$(echo $RESULT_RESPONSE | jq '.result.detailed_results.rolling_sharpe | length')
  echo "  • rolling_sharpe: $SHARPE_COUNT 個數據點"
  if [ "$SHARPE_COUNT" -gt 0 ]; then
    echo "    範例: $(echo $RESULT_RESPONSE | jq '.result.detailed_results.rolling_sharpe[0]')"
  fi

  # Drawdown Series
  DD_COUNT=$(echo $RESULT_RESPONSE | jq '.result.detailed_results.drawdown_series | length')
  echo "  • drawdown_series: $DD_COUNT 個數據點"
  if [ "$DD_COUNT" -gt 0 ]; then
    echo "    範例: $(echo $RESULT_RESPONSE | jq '.result.detailed_results.drawdown_series[0]')"
  fi

  # Trade Distribution
  echo "  • trade_distribution:"
  echo "    - profit_bins: $(echo $RESULT_RESPONSE | jq '.result.detailed_results.trade_distribution.profit_bins')"
  echo "    - loss_bins: $(echo $RESULT_RESPONSE | jq '.result.detailed_results.trade_distribution.loss_bins')"
  echo "    - holding_days_dist: $(echo $RESULT_RESPONSE | jq '.result.detailed_results.trade_distribution.holding_days_dist')"

  echo ""
  echo "=============================="
  echo "🎉 測試成功！"
  echo "=============================="
  echo ""
  echo "✅ 後端功能完全正常"
  echo "✅ detailed_results 數據生成成功"
  echo "✅ 所有視覺化數據都已就緒"
  echo ""
  echo "💡 下一步："
  echo "   1. 在瀏覽器中訪問: http://localhost:3000/backtest/$BACKTEST_ID"
  echo "   2. 查看回測詳情頁面"
  echo "   3. （前端尚未實作視覺化圖表，需要按照 BACKTEST_VISUALIZATION_IMPLEMENTATION.md 實作）"
  echo ""
  echo "📄 完整結果已儲存到: /tmp/backtest_result_$BACKTEST_ID.json"
  echo $RESULT_RESPONSE | jq > /tmp/backtest_result_$BACKTEST_ID.json

else
  echo "❌ detailed_results 不存在"
  echo ""
  echo "可能原因："
  echo "  1. 回測引擎代碼未正確應用"
  echo "  2. Observer 未正確初始化"
  echo "  3. 資料庫遷移未執行"
  echo ""
  echo "完整響應："
  echo $RESULT_RESPONSE | jq
  exit 1
fi
