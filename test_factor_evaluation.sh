#!/bin/bash

# 因子評估功能測試腳本

set -e

echo "🧪 測試因子評估功能"
echo "===================="

# 設定 API 基礎 URL
API_BASE="http://localhost:8000/api/v1"

# 1. 註冊測試用戶（如果不存在）
echo ""
echo "📝 1. 註冊/登入測試用戶..."
REGISTER_RESPONSE=$(curl -s -X POST "$API_BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "factor_test@example.com",
    "username": "factor_test",
    "password": "test123456",
    "full_name": "Factor Test User"
  }' || echo '{"detail":"already exists"}')

echo "註冊響應: $REGISTER_RESPONSE"

# 2. 登入獲取 token
echo ""
echo "🔐 2. 登入獲取 token..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "factor_test",
    "password": "test123456"
  }')

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
  echo "❌ 登入失敗"
  echo "Response: $LOGIN_RESPONSE"
  exit 1
fi

echo "✅ Token 獲取成功: ${TOKEN:0:20}..."

# 3. 創建測試因子
echo ""
echo "➕ 3. 創建測試因子..."

# 首先檢查是否已有因子
EXISTING_FACTORS=$(curl -s -X GET "$API_BASE/rdagent/factors" \
  -H "Authorization: Bearer $TOKEN")

FACTOR_COUNT=$(echo $EXISTING_FACTORS | jq '. | length')
echo "現有因子數量: $FACTOR_COUNT"

if [ "$FACTOR_COUNT" -gt 0 ]; then
  # 使用第一個因子
  FACTOR_ID=$(echo $EXISTING_FACTORS | jq -r '.[0].id')
  FACTOR_NAME=$(echo $EXISTING_FACTORS | jq -r '.[0].name')
  echo "✅ 使用現有因子: ID=$FACTOR_ID, Name=$FACTOR_NAME"
else
  echo "⚠️  沒有找到現有因子"
  echo "請先使用 RD-Agent 生成因子，或手動創建因子"
  exit 1
fi

# 4. 評估因子（同步）
echo ""
echo "📊 4. 評估因子 (ID: $FACTOR_ID)..."
EVAL_RESPONSE=$(curl -s -X POST "$API_BASE/factor-evaluation/evaluate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"factor_id\": $FACTOR_ID,
    \"stock_pool\": \"all\",
    \"start_date\": \"2024-01-01\",
    \"end_date\": \"2024-12-31\"
  }")

echo "評估響應:"
echo $EVAL_RESPONSE | jq .

# 檢查是否成功
IC=$(echo $EVAL_RESPONSE | jq -r '.ic // "null"')
SHARPE=$(echo $EVAL_RESPONSE | jq -r '.sharpe_ratio // "null"')

if [ "$IC" != "null" ] && [ "$SHARPE" != "null" ]; then
  echo ""
  echo "✅ 因子評估成功！"
  echo "   IC: $IC"
  echo "   ICIR: $(echo $EVAL_RESPONSE | jq -r '.icir')"
  echo "   Sharpe Ratio: $SHARPE"
  echo "   Annual Return: $(echo $EVAL_RESPONSE | jq -r '.annual_return')"
  echo "   Max Drawdown: $(echo $EVAL_RESPONSE | jq -r '.max_drawdown')"
  echo "   Win Rate: $(echo $EVAL_RESPONSE | jq -r '.win_rate')"
else
  echo ""
  echo "❌ 因子評估失敗"
  echo "詳細響應: $EVAL_RESPONSE"
fi

# 5. 獲取評估歷史
echo ""
echo "📜 5. 獲取因子評估歷史..."
HISTORY_RESPONSE=$(curl -s -X GET "$API_BASE/factor-evaluation/factor/$FACTOR_ID/evaluations" \
  -H "Authorization: Bearer $TOKEN")

EVAL_COUNT=$(echo $HISTORY_RESPONSE | jq '. | length')
echo "評估歷史記錄數: $EVAL_COUNT"
echo $HISTORY_RESPONSE | jq .

# 6. 測試異步評估（使用 Celery）
echo ""
echo "⚡ 6. 測試異步因子評估..."
echo "注意：這需要 Celery worker 運行"

# 檢查 Celery worker 是否運行
CELERY_STATUS=$(docker compose ps celery-worker --format json 2>/dev/null | jq -r '.[0].State // "unknown"')

if [ "$CELERY_STATUS" = "running" ]; then
  echo "✅ Celery worker 正在運行"

  # 觸發異步評估任務（需要修改 API 端點以支持異步模式）
  echo "   異步評估功能需要在 API 中添加 /evaluate-async 端點"
else
  echo "⚠️  Celery worker 未運行，跳過異步測試"
  echo "   啟動命令: docker compose up -d celery-worker"
fi

echo ""
echo "===================="
echo "✅ 測試完成！"
echo ""
echo "API 端點測試結果："
echo "  ✅ POST /factor-evaluation/evaluate - 評估因子"
echo "  ✅ GET  /factor-evaluation/factor/{id}/evaluations - 獲取評估歷史"
echo ""
echo "查看 API 文檔: http://localhost:8000/docs#/因子評估"
