#!/bin/bash

# 測試財務分析 API

echo "=========================================="
echo "財務分析 API 測試腳本"
echo "=========================================="
echo ""

BASE_URL="http://localhost:8000"

# Helper function to format JSON
format_json() {
    python3 -m json.tool
}

# 1. 登入獲取 Token
echo "1. 登入獲取 JWT Token..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"fundamental_test","password":"test123456"}')

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | sed 's/"access_token":"//')

if [ -z "$TOKEN" ]; then
    echo "❌ 登入失敗，請確認測試帳號存在"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

echo "✅ 登入成功，Token: ${TOKEN:0:20}..."
echo ""

# 2. 列出所有可用的財務指標
echo "2. 列出所有可用的財務指標..."
RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/data/fundamental/indicators" \
  -H "Authorization: Bearer $TOKEN")
echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print('指標總數:', data['count']); print('分類:', list(data['categories'].keys()))"
echo ""

# 3. 取得指標分類
echo "3. 取得指標分類..."
RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/data/fundamental/indicators/categories" \
  -H "Authorization: Bearer $TOKEN")
echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print('總計:', data['total_count'], '個指標'); print('分類:', list(data['categories'].keys()))"
echo ""

# 4. 取得台積電的 ROE 指標
echo "4. 取得台積電 (2330) 的 ROE稅後 指標..."
RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/data/fundamental/2330/ROE稅後?start_date=2023-01-01&end_date=2024-12-31" \
  -H "Authorization: Bearer $TOKEN")
echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"指標: {data['indicator']}, 股票: {data['stock_id']}, 數據點數: {data['count']}\"); print(f\"前 3 筆數據: {data['data'][:3]}\")"
echo ""

# 5. 批量取得台積電的多個財務指標
echo "5. 批量取得台積電的多個財務指標..."
RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/data/fundamental/2330/batch" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "stock_id": "2330",
    "indicators": ["ROE稅後", "ROA稅後息前", "營業毛利率"],
    "start_date": "2023-01-01",
    "end_date": "2024-12-31"
  }')
echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"股票: {data['stock_id']}, 成功獲取: {data['count']}/{data['requested_count']}\"); print(f\"指標: {list(data['indicators'].keys())}\")"
echo ""

# 6. 取得台積電的財務摘要
echo "6. 取得台積電的財務摘要（最新數據）..."
RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/data/fundamental/2330/summary" \
  -H "Authorization: Bearer $TOKEN")
echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"股票: {data['stock_id']}, 日期: {data.get('latest_date')}\"); print(f\"ROE: {data.get('roe')}%, ROA: {data.get('roa')}%, 毛利率: {data.get('gross_margin')}%, EPS: {data.get('eps')}\")"
echo ""

# 7. 比較多個股票的 ROE 指標
echo "7. 比較台積電、聯發科、鴻海的 ROE稅後..."
RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/data/fundamental/compare" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "stock_ids": ["2330", "2317", "2454"],
    "indicator": "ROE稅後",
    "start_date": "2023-01-01",
    "end_date": "2024-12-31"
  }')
echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"指標: {data['indicator']}, 成功比較: {data['count']} 檔股票\"); print(f\"股票: {list(data['stocks'].keys())}\")"
echo ""

echo "=========================================="
echo "✅ 測試完成！"
echo "=========================================="
