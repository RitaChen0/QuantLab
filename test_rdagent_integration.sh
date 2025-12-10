#!/bin/bash
# RD-Agent 整合測試腳本
# 目的：測試完整的 API → Celery → Service → RD-Agent → Database 流程

set -e  # 遇到錯誤立即退出

echo "═══════════════════════════════════════════════════════════════════════════"
echo "🧪 RD-Agent 整合測試"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 步驟 1: 檢查服務狀態
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 步驟 1: 檢查服務狀態"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo -e "${BLUE}► 檢查 Docker 容器...${NC}"
docker compose ps | grep -E "(backend|celery-worker|postgres|redis)"

echo ""
echo -e "${BLUE}► 檢查 Backend API 健康狀態...${NC}"
HEALTH_STATUS=$(curl -s http://localhost:8000/health | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))")
if [ "$HEALTH_STATUS" = "healthy" ]; then
    echo -e "${GREEN}✅ Backend API: $HEALTH_STATUS${NC}"
else
    echo -e "${RED}❌ Backend API 不健康${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}► 檢查 Celery Worker 狀態...${NC}"
docker compose exec celery-worker celery -A app.core.celery_app inspect ping || {
    echo -e "${RED}❌ Celery Worker 未運行${NC}"
    exit 1
}
echo -e "${GREEN}✅ Celery Worker 運行中${NC}"

# 步驟 2: 註冊測試用戶（如果不存在）
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "👤 步驟 2: 準備測試用戶"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

TEST_USER="rdagent_test@example.com"
TEST_PASS="Test123456"

echo -e "${BLUE}► 嘗試註冊測試用戶...${NC}"
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/register \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$TEST_USER\",
        \"username\": \"rdagent_test\",
        \"password\": \"$TEST_PASS\",
        \"full_name\": \"RD-Agent Test User\"
    }" || echo '{"detail":"User already exists"}')

echo "註冊響應: $REGISTER_RESPONSE"

echo ""
echo -e "${BLUE}► 登入獲取 JWT Token...${NC}"
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d "{
        \"username\": \"rdagent_test\",
        \"password\": \"$TEST_PASS\"
    }" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))")

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ 無法獲取 JWT Token${NC}"
    exit 1
fi

echo -e "${GREEN}✅ JWT Token 獲取成功${NC}"
echo "Token (前 30 字元): ${TOKEN:0:30}..."

# 步驟 3: 創建因子挖掘任務
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 步驟 3: 創建因子挖掘任務"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

TASK_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/rdagent/factor-mining \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "research_goal": "Generate profitable momentum-based trading factors for Taiwan stock market",
        "stock_pool": "Taiwan Top 50",
        "max_factors": 3,
        "llm_model": "gpt-4-turbo",
        "max_iterations": 1
    }')

echo "任務創建響應:"
echo "$TASK_RESPONSE" | python3 -m json.tool

TASK_ID=$(echo "$TASK_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))")

if [ "$TASK_ID" = "null" ] || [ -z "$TASK_ID" ]; then
    echo -e "${RED}❌ 無法創建任務${NC}"
    echo "錯誤響應: $TASK_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ 任務創建成功！任務 ID: $TASK_ID${NC}"

# 步驟 4: 監控任務執行
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⏱️  步驟 4: 監控任務執行"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo -e "${YELLOW}⏳ 監控 Celery Worker 日誌...${NC}"
echo -e "${YELLOW}提示：RD-Agent 執行需要 5-10 分鐘，請耐心等待${NC}"
echo ""

# 在背景顯示 Celery 日誌
docker compose logs -f celery-worker | grep -i "factor_mining\|rdagent\|Factor\|Loop" &
LOG_PID=$!

# 輪詢任務狀態
MAX_WAIT=600  # 最多等待 10 分鐘
WAIT_TIME=0
CHECK_INTERVAL=10

while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    sleep $CHECK_INTERVAL
    WAIT_TIME=$((WAIT_TIME + CHECK_INTERVAL))

    TASK_STATUS_RESPONSE=$(curl -s -X GET "http://localhost:8000/api/v1/rdagent/tasks/$TASK_ID" \
        -H "Authorization: Bearer $TOKEN")

    TASK_STATUS=$(echo "$TASK_STATUS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))")

    echo -e "${BLUE}[$(date +%H:%M:%S)] 任務狀態: $TASK_STATUS (等待時間: ${WAIT_TIME}s)${NC}"

    if [ "$TASK_STATUS" = "completed" ]; then
        echo -e "${GREEN}✅ 任務執行完成！${NC}"
        kill $LOG_PID 2>/dev/null || true
        break
    elif [ "$TASK_STATUS" = "failed" ]; then
        echo -e "${RED}❌ 任務執行失敗${NC}"
        ERROR_MSG=$(echo "$TASK_STATUS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('error_message', ''))")
        echo "錯誤訊息: $ERROR_MSG"
        kill $LOG_PID 2>/dev/null || true
        exit 1
    fi
done

if [ $WAIT_TIME -ge $MAX_WAIT ]; then
    echo -e "${RED}❌ 任務執行超時（超過 10 分鐘）${NC}"
    kill $LOG_PID 2>/dev/null || true
    exit 1
fi

# 步驟 5: 檢查任務結果
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 步驟 5: 檢查任務結果"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

FINAL_TASK=$(curl -s -X GET "http://localhost:8000/api/v1/rdagent/tasks/$TASK_ID" \
    -H "Authorization: Bearer $TOKEN")

echo "完整任務資訊:"
echo "$FINAL_TASK" | python3 -m json.tool

FACTORS_COUNT=$(echo "$FINAL_TASK" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('result', {}).get('generated_factors_count', 0))")
LLM_CALLS=$(echo "$FINAL_TASK" | python3 -c "import sys, json; print(json.load(sys.stdin).get('llm_calls', 0))")
LLM_COST=$(echo "$FINAL_TASK" | python3 -c "import sys, json; print(json.load(sys.stdin).get('llm_cost', 0))")

echo ""
echo -e "${GREEN}✅ 生成因子數量: $FACTORS_COUNT${NC}"
echo -e "${GREEN}✅ LLM API 調用次數: $LLM_CALLS${NC}"
echo -e "${GREEN}✅ LLM 成本: \$$LLM_COST${NC}"

# 步驟 6: 檢查資料庫中的因子
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🗄️  步驟 6: 檢查資料庫中的因子"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

FACTORS_RESPONSE=$(curl -s -X GET "http://localhost:8000/api/v1/rdagent/factors?limit=100" \
    -H "Authorization: Bearer $TOKEN")

echo "生成的因子列表:"
echo "$FACTORS_RESPONSE" | python3 -m json.tool

# 步驟 7: 測試總結
echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "📝 測試總結"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo -e "${GREEN}✅ 所有測試步驟完成！${NC}"
echo ""
echo "測試結果："
echo "  • 任務 ID: $TASK_ID"
echo "  • 任務狀態: $TASK_STATUS"
echo "  • 生成因子: $FACTORS_COUNT 個"
echo "  • LLM 調用: $LLM_CALLS 次"
echo "  • LLM 成本: \$$LLM_COST"
echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
