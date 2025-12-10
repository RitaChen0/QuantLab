#!/bin/bash
# Test script for concurrent backtest execution
# Purpose: Verify distributed lock prevents race conditions

set -e

echo "=========================================="
echo "分佈式鎖測試 - 並發回測執行"
echo "=========================================="
echo ""

# Step 1: Create test user and get token
echo "=== Step 1: 建立測試用戶 ==="
USER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "locktest@example.com",
    "username": "locktest",
    "password": "password123",
    "full_name": "Lock Test User"
  }')

echo "用戶建立結果: $USER_RESPONSE"
echo ""

# Step 2: Login to get token
echo "=== Step 2: 登入取得 Token ==="
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "locktest",
    "password": "password123"
  }' | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
  # Try existing user
  echo "用戶已存在，嘗試登入..."
  TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{
      "username": "locktest",
      "password": "password123"
    }' | jq -r '.access_token')
fi

echo "Token 取得: ${TOKEN:0:20}..."
echo ""

# Step 3: Create a test strategy
echo "=== Step 3: 建立測試策略 ==="
STRATEGY_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/strategies/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Lock Test Strategy",
    "description": "Strategy for testing distributed lock",
    "code": "import backtrader as bt\n\nclass TestStrategy(bt.Strategy):\n    def __init__(self):\n        pass\n    def next(self):\n        pass",
    "parameters": {},
    "status": "draft"
  }')

STRATEGY_ID=$(echo $STRATEGY_RESPONSE | jq -r '.id')
echo "策略建立成功，ID: $STRATEGY_ID"
echo ""

# Step 4: Create two backtest configurations
echo "=== Step 4: 建立兩個回測配置 ==="
BACKTEST1=$(curl -s -X POST http://localhost:8000/api/v1/backtest/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"strategy_id\": $STRATEGY_ID,
    \"symbol\": \"2330\",
    \"start_date\": \"2024-01-01\",
    \"end_date\": \"2024-12-01\",
    \"initial_capital\": 1000000,
    \"parameters\": {}
  }")

BACKTEST_ID1=$(echo $BACKTEST1 | jq -r '.id')
echo "回測 1 建立成功，ID: $BACKTEST_ID1"

BACKTEST2=$(curl -s -X POST http://localhost:8000/api/v1/backtest/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"strategy_id\": $STRATEGY_ID,
    \"symbol\": \"2330\",
    \"start_date\": \"2024-01-01\",
    \"end_date\": \"2024-12-01\",
    \"initial_capital\": 1000000,
    \"parameters\": {}
  }")

BACKTEST_ID2=$(echo $BACKTEST2 | jq -r '.id')
echo "回測 2 建立成功，ID: $BACKTEST_ID2"
echo ""

# Step 5: Test concurrent execution (the critical test)
echo "=== Step 5: 測試並發執行 (關鍵測試) ==="
echo "同時啟動兩個回測執行請求..."
echo ""

# Start both requests in background
(
  echo ">>> 請求 A 開始 (Backtest ID: $BACKTEST_ID1) - $(date +%H:%M:%S)"
  RESPONSE_A=$(curl -s -X POST http://localhost:8000/api/v1/backtest/run \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"backtest_id\": $BACKTEST_ID1}" \
    -w "\nHTTP_CODE:%{http_code}")

  HTTP_CODE_A=$(echo "$RESPONSE_A" | grep "HTTP_CODE" | cut -d: -f2)
  RESPONSE_BODY_A=$(echo "$RESPONSE_A" | sed '/HTTP_CODE/d')

  echo ">>> 請求 A 結束 - $(date +%H:%M:%S)"
  echo "    HTTP 狀態: $HTTP_CODE_A"
  echo "    回應內容: $RESPONSE_BODY_A"
  echo ""
) &

PID_A=$!

# Wait a moment to ensure some overlap
sleep 0.5

(
  echo ">>> 請求 B 開始 (Backtest ID: $BACKTEST_ID2) - $(date +%H:%M:%S)"
  RESPONSE_B=$(curl -s -X POST http://localhost:8000/api/v1/backtest/run \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"backtest_id\": $BACKTEST_ID2}" \
    -w "\nHTTP_CODE:%{http_code}")

  HTTP_CODE_B=$(echo "$RESPONSE_B" | grep "HTTP_CODE" | cut -d: -f2)
  RESPONSE_BODY_B=$(echo "$RESPONSE_B" | sed '/HTTP_CODE/d')

  echo ">>> 請求 B 結束 - $(date +%H:%M:%S)"
  echo "    HTTP 狀態: $HTTP_CODE_B"
  echo "    回應內容: $RESPONSE_BODY_B"
  echo ""
) &

PID_B=$!

# Wait for both requests to complete
wait $PID_A
wait $PID_B

echo ""
echo "=== 測試結果分析 ==="
echo "預期行為："
echo "  ✅ 其中一個請求應成功 (HTTP 200)"
echo "  ✅ 另一個請求應被鎖阻擋 (HTTP 503 或 409)"
echo "  ✅ 錯誤訊息應包含: '另一個回測正在執行中，請稍後再試'"
echo ""
echo "實際結果請查看上方輸出。"
echo ""
echo "=========================================="
echo "測試完成"
echo "=========================================="
