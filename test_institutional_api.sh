#!/bin/bash
# 法人買賣超 API 端點測試腳本

set -e

API_BASE="http://localhost:8000/api/v1"
BACKEND_CONTAINER="quantlab-backend"

echo "========================================="
echo "法人買賣超 API 端點測試"
echo "========================================="

# 顏色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 步驟 1: 檢查 Backend 狀態
echo -e "\n${YELLOW}步驟 1: 檢查 Backend 狀態${NC}"
HEALTH=$(curl -s http://localhost:8000/health)
if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Backend 運行正常${NC}"
    echo "   版本: $(echo $HEALTH | jq -r '.version')"
else
    echo -e "${RED}❌ Backend 未運行${NC}"
    exit 1
fi

# 步驟 2: 創建測試用戶並獲取 Token
echo -e "\n${YELLOW}步驟 2: 獲取認證 Token${NC}"
# 使用 docker exec 直接在容器內創建 token
TOKEN=$(docker compose exec -T backend python3 -c "
import sys
sys.path.insert(0, '/app')
from app.core.security import create_access_token
print(create_access_token('1'))
" 2>/dev/null | tr -d '\r')

if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Token 獲取失敗${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Token 已獲取${NC}"
echo "   Token 前綴: ${TOKEN:0:20}..."

# 步驟 3: 測試各個端點
echo -e "\n${YELLOW}步驟 3: 測試 API 端點${NC}"

# 測試 3.1: 查詢最新數據日期
echo -e "\n  ${YELLOW}3.1 查詢最新數據日期${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "$API_BASE/institutional/status/latest-date?stock_id=2330")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "      ${GREEN}✅ 狀態碼: $HTTP_CODE${NC}"
    echo "      響應: $BODY" | jq .
else
    echo -e "      ${RED}❌ 狀態碼: $HTTP_CODE${NC}"
    echo "      錯誤: $BODY"
fi

# 測試 3.2: 查詢法人買賣超數據
echo -e "\n  ${YELLOW}3.2 查詢法人買賣超數據${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "$API_BASE/institutional/stocks/2330/data?start_date=2024-12-01&end_date=2024-12-05")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "      ${GREEN}✅ 狀態碼: $HTTP_CODE${NC}"
    COUNT=$(echo "$BODY" | jq 'length')
    echo "      查詢到 $COUNT 筆記錄"
    echo "      範例數據:" | head -1
    echo "$BODY" | jq '.[0]' 2>/dev/null || echo "$BODY"
else
    echo -e "      ${RED}❌ 狀態碼: $HTTP_CODE${NC}"
    echo "      錯誤: $BODY"
fi

# 測試 3.3: 查詢單日摘要
echo -e "\n  ${YELLOW}3.3 查詢單日摘要${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "$API_BASE/institutional/stocks/2330/summary?target_date=2024-12-02")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "      ${GREEN}✅ 狀態碼: $HTTP_CODE${NC}"
    echo "      響應: $BODY" | jq .
else
    echo -e "      ${RED}❌ 狀態碼: $HTTP_CODE${NC}"
    echo "      錯誤: $BODY"
fi

# 測試 3.4: 查詢統計數據
echo -e "\n  ${YELLOW}3.4 查詢統計數據${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "$API_BASE/institutional/stocks/2330/stats?investor_type=Foreign_Investor&start_date=2024-12-01&end_date=2024-12-05")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "      ${GREEN}✅ 狀態碼: $HTTP_CODE${NC}"
    echo "      響應: $BODY" | jq .
else
    # 如果沒有數據，404 是正常的
    if [ "$HTTP_CODE" = "404" ]; then
        echo -e "      ${YELLOW}⚠️  狀態碼: $HTTP_CODE (期間內無數據)${NC}"
    else
        echo -e "      ${RED}❌ 狀態碼: $HTTP_CODE${NC}"
    fi
    echo "      響應: $BODY"
fi

# 測試 3.5: 查詢排行榜
echo -e "\n  ${YELLOW}3.5 查詢買賣超排行榜${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "$API_BASE/institutional/rankings/2024-12-02?investor_type=Foreign_Investor&limit=5")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "      ${GREEN}✅ 狀態碼: $HTTP_CODE${NC}"
    COUNT=$(echo "$BODY" | jq 'length' 2>/dev/null || echo "0")
    echo "      返回 $COUNT 筆排行"
    echo "$BODY" | jq '.[0:3]' 2>/dev/null || echo "$BODY"
else
    echo -e "      ${RED}❌ 狀態碼: $HTTP_CODE${NC}"
    echo "      錯誤: $BODY"
fi

# 測試 3.6: 觸發數據同步
echo -e "\n  ${YELLOW}3.6 觸發數據同步 (異步任務)${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Authorization: Bearer $TOKEN" \
    "$API_BASE/institutional/sync/2330?start_date=2024-12-01&end_date=2024-12-02")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "      ${GREEN}✅ 狀態碼: $HTTP_CODE${NC}"
    TASK_ID=$(echo "$BODY" | jq -r '.task_id' 2>/dev/null)
    echo "      任務 ID: $TASK_ID"
    echo "      響應: $BODY" | jq .
else
    echo -e "      ${RED}❌ 狀態碼: $HTTP_CODE${NC}"
    echo "      錯誤: $BODY"
fi

# 步驟 4: 檢查 OpenAPI 文檔
echo -e "\n${YELLOW}步驟 4: 檢查 OpenAPI 文檔${NC}"
OPENAPI=$(curl -s "$API_BASE/openapi.json")
ENDPOINTS=$(echo "$OPENAPI" | jq '[.paths | keys[] | select(. | contains("institutional"))]')
COUNT=$(echo "$ENDPOINTS" | jq 'length')

echo -e "${GREEN}✅ OpenAPI 文檔已生成${NC}"
echo "   法人買賣超端點數量: $COUNT"
echo "   端點列表:"
echo "$ENDPOINTS" | jq -r '.[]' | sed 's/^/     - /'

# 總結
echo -e "\n========================================="
echo -e "${GREEN}測試完成！${NC}"
echo "========================================="
echo ""
echo "📚 完整 API 文檔："
echo "   - Swagger UI: http://localhost:8000/docs"
echo "   - ReDoc: http://localhost:8000/redoc"
echo "   - 使用指南: /home/ubuntu/QuantLab/INSTITUTIONAL_API_GUIDE.md"
echo ""
