#!/bin/bash
# 速率限制重置工具（除錯專用）
# 用途：在開發/測試階段快速重置 API 速率限制

set -e

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "═══════════════════════════════════════════════════════════════════════════"
echo -e "${BLUE}🔧 速率限制重置工具${NC}"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""

# 檢查 Redis 容器是否運行
if ! docker compose ps redis | grep -q "Up"; then
    echo -e "${RED}❌ Redis 容器未運行${NC}"
    exit 1
fi

# 查詢所有速率限制 key
echo -e "${BLUE}► 查詢 Redis 中的速率限制 keys...${NC}"
RATE_LIMIT_KEYS=$(docker compose exec -T redis redis-cli KEYS "LIMITS:*" 2>/dev/null || echo "")

if [ -z "$RATE_LIMIT_KEYS" ]; then
    echo -e "${GREEN}✅ 沒有發現任何速率限制 keys（已經是乾淨狀態）${NC}"
    exit 0
fi

# 顯示找到的 keys
echo ""
echo -e "${YELLOW}找到以下速率限制 keys：${NC}"
echo "$RATE_LIMIT_KEYS" | nl -w2 -s'. '
echo ""

# 統計數量
KEY_COUNT=$(echo "$RATE_LIMIT_KEYS" | wc -l)
echo -e "${YELLOW}總共 $KEY_COUNT 個速率限制 keys${NC}"
echo ""

# 詢問用戶操作
echo "請選擇操作："
echo "  1) 刪除所有速率限制 keys"
echo "  2) 僅刪除 RD-Agent 相關的 keys"
echo "  3) 僅刪除因子挖掘 (factor-mining) keys"
echo "  4) 僅刪除策略優化 (strategy-optimization) keys"
echo "  5) 取消操作"
echo ""
read -p "請輸入選項 [1-5]: " choice

case $choice in
    1)
        echo ""
        echo -e "${YELLOW}⚠️  即將刪除所有 $KEY_COUNT 個速率限制 keys${NC}"
        read -p "確定要繼續嗎？[y/N]: " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            echo "$RATE_LIMIT_KEYS" | while IFS= read -r key; do
                docker compose exec -T redis redis-cli DEL "$key" > /dev/null
            done
            echo -e "${GREEN}✅ 已刪除所有 $KEY_COUNT 個速率限制 keys${NC}"
        else
            echo -e "${BLUE}已取消操作${NC}"
        fi
        ;;

    2)
        echo ""
        RDAGENT_KEYS=$(echo "$RATE_LIMIT_KEYS" | grep "rdagent" || echo "")
        if [ -z "$RDAGENT_KEYS" ]; then
            echo -e "${GREEN}✅ 沒有找到 RD-Agent 相關的 keys${NC}"
        else
            RDAGENT_COUNT=$(echo "$RDAGENT_KEYS" | wc -l)
            echo -e "${YELLOW}找到 $RDAGENT_COUNT 個 RD-Agent keys：${NC}"
            echo "$RDAGENT_KEYS" | nl -w2 -s'. '
            echo ""
            read -p "確定要刪除這些 keys 嗎？[y/N]: " confirm
            if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                echo "$RDAGENT_KEYS" | while IFS= read -r key; do
                    docker compose exec -T redis redis-cli DEL "$key" > /dev/null
                done
                echo -e "${GREEN}✅ 已刪除 $RDAGENT_COUNT 個 RD-Agent keys${NC}"
            else
                echo -e "${BLUE}已取消操作${NC}"
            fi
        fi
        ;;

    3)
        echo ""
        FACTOR_KEYS=$(echo "$RATE_LIMIT_KEYS" | grep "factor-mining" || echo "")
        if [ -z "$FACTOR_KEYS" ]; then
            echo -e "${GREEN}✅ 沒有找到因子挖掘相關的 keys${NC}"
        else
            FACTOR_COUNT=$(echo "$FACTOR_KEYS" | wc -l)
            echo -e "${YELLOW}找到 $FACTOR_COUNT 個因子挖掘 keys：${NC}"
            echo "$FACTOR_KEYS" | nl -w2 -s'. '
            echo ""
            read -p "確定要刪除這些 keys 嗎？[y/N]: " confirm
            if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                echo "$FACTOR_KEYS" | while IFS= read -r key; do
                    docker compose exec -T redis redis-cli DEL "$key" > /dev/null
                done
                echo -e "${GREEN}✅ 已刪除 $FACTOR_COUNT 個因子挖掘 keys${NC}"
            else
                echo -e "${BLUE}已取消操作${NC}"
            fi
        fi
        ;;

    4)
        echo ""
        STRATEGY_KEYS=$(echo "$RATE_LIMIT_KEYS" | grep "strategy-optimization" || echo "")
        if [ -z "$STRATEGY_KEYS" ]; then
            echo -e "${GREEN}✅ 沒有找到策略優化相關的 keys${NC}"
        else
            STRATEGY_COUNT=$(echo "$STRATEGY_KEYS" | wc -l)
            echo -e "${YELLOW}找到 $STRATEGY_COUNT 個策略優化 keys：${NC}"
            echo "$STRATEGY_KEYS" | nl -w2 -s'. '
            echo ""
            read -p "確定要刪除這些 keys 嗎？[y/N]: " confirm
            if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                echo "$STRATEGY_KEYS" | while IFS= read -r key; do
                    docker compose exec -T redis redis-cli DEL "$key" > /dev/null
                done
                echo -e "${GREEN}✅ 已刪除 $STRATEGY_COUNT 個策略優化 keys${NC}"
            else
                echo -e "${BLUE}已取消操作${NC}"
            fi
        fi
        ;;

    5|"")
        echo ""
        echo -e "${BLUE}已取消操作${NC}"
        echo ""
        exit 0
        ;;

    *)
        echo ""
        echo -e "${RED}❌ 無效的選項${NC}"
        echo ""
        exit 1
        ;;
esac

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ 操作完成${NC}"
echo "═══════════════════════════════════════════════════════════════════════════"
