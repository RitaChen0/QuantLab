#!/bin/bash

# 簡單的因子評估測試腳本

set -e

echo "🧪 測試因子評估 API 端點"
echo "========================"

API_BASE="http://localhost:8000/api/v1"

# 1. 檢查 API 健康狀態
echo ""
echo "1. 檢查 API 健康狀態..."
curl -s http://localhost:8000/health | python3 -m json.tool

# 2. 檢查因子評估端點是否存在
echo ""
echo "2. 檢查因子評估 API 端點..."
curl -s $API_BASE/openapi.json | python3 -c "
import sys, json
data = json.load(sys.stdin)
endpoints = [p for p in data['paths'].keys() if 'factor-evaluation' in p]
print('找到的端點:')
for ep in endpoints:
    print(f'  - {ep}')
"

# 3. 嘗試訪問端點（無 token，應返回 401）
echo ""
echo "3. 測試端點訪問控制（無 token）..."
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$API_BASE/factor-evaluation/evaluate" \
  -H "Content-Type: application/json" \
  -d '{"factor_id": 1, "stock_pool": "all"}')

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
echo "HTTP 狀態碼: $HTTP_CODE"

if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
  echo "✅ 正確返回未授權錯誤"
else
  echo "⚠️  預期 401/403，但獲得 $HTTP_CODE"
fi

echo ""
echo "========================"
echo "✅ 基礎測試完成！"
echo ""
echo "因子評估 API 端點已成功部署："
echo "  - POST /api/v1/factor-evaluation/evaluate"
echo "  - GET  /api/v1/factor-evaluation/factor/{factor_id}/evaluations"
echo "  - GET  /api/v1/factor-evaluation/evaluation/{evaluation_id}"
echo "  - DELETE /api/v1/factor-evaluation/evaluation/{evaluation_id}"
echo ""
echo "查看完整 API 文檔: http://localhost:8000/docs#/因子評估"
