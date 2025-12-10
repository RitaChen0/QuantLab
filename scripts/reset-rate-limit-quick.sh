#!/bin/bash
# 快速重置 RD-Agent 速率限制（無互動）
# 用途：除錯時快速重置所有 RD-Agent 速率限制

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🔧 快速重置 RD-Agent 速率限制...${NC}"

# 檢查 Redis 容器
if ! docker compose ps redis | grep -q "Up"; then
    echo -e "${RED}❌ Redis 容器未運行${NC}"
    exit 1
fi

# 查找並刪除所有 RD-Agent 相關的速率限制 keys
RDAGENT_KEYS=$(docker compose exec -T redis redis-cli KEYS "LIMITS:*rdagent*" 2>/dev/null || echo "")

if [ -z "$RDAGENT_KEYS" ]; then
    echo -e "${GREEN}✅ 沒有發現 RD-Agent 速率限制 keys${NC}"
    exit 0
fi

# 刪除找到的 keys
DELETED=0
while IFS= read -r key; do
    if [ -n "$key" ]; then
        docker compose exec -T redis redis-cli DEL "$key" > /dev/null
        DELETED=$((DELETED + 1))
    fi
done <<< "$RDAGENT_KEYS"

echo -e "${GREEN}✅ 已刪除 $DELETED 個 RD-Agent 速率限制 keys${NC}"
