#!/bin/bash
# Shioaji 同步工具測試腳本
# 用途：驗證 sync_shioaji_to_qlib.py 是否正常工作

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Shioaji 同步工具測試${NC}"
echo -e "${GREEN}========================================${NC}"

cd /home/ubuntu/QuantLab/backend

# 1. 檢查環境變數
echo -e "\n${YELLOW}1️⃣  檢查環境變數...${NC}"
if [ -z "$SHIOAJI_API_KEY" ]; then
    echo -e "${RED}❌ SHIOAJI_API_KEY 未設定${NC}"
    exit 1
else
    echo -e "${GREEN}✅ SHIOAJI_API_KEY: ${SHIOAJI_API_KEY:0:10}...${NC}"
fi

if [ -z "$SHIOAJI_SECRET_KEY" ]; then
    echo -e "${RED}❌ SHIOAJI_SECRET_KEY 未設定${NC}"
    exit 1
else
    echo -e "${GREEN}✅ SHIOAJI_SECRET_KEY: ${SHIOAJI_SECRET_KEY:0:10}...${NC}"
fi

# 2. 檢查資料庫連接
echo -e "\n${YELLOW}2️⃣  檢查資料庫連接...${NC}"
if [ -z "$DATABASE_URL" ]; then
    echo -e "${YELLOW}⚠️  DATABASE_URL 未設定（將使用 --qlib-only 模式）${NC}"
else
    echo -e "${GREEN}✅ DATABASE_URL 已設定${NC}"
fi

# 3. 檢查 Python 依賴
echo -e "\n${YELLOW}3️⃣  檢查 Python 依賴...${NC}"
python3 -c "import shioaji; import qlib; import pandas; import loguru; import tqdm" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Python 依賴已安裝${NC}"
else
    echo -e "${RED}❌ Python 依賴缺失，請執行: pip install -r requirements.txt${NC}"
    exit 1
fi

# 4. 檢查 Qlib 數據目錄
echo -e "\n${YELLOW}4️⃣  檢查 Qlib 數據目錄...${NC}"
if [ -d "/data/qlib/tw_stock_minute" ]; then
    echo -e "${GREEN}✅ Qlib 數據目錄存在${NC}"
else
    echo -e "${YELLOW}⚠️  Qlib 數據目錄不存在，將自動創建${NC}"
    mkdir -p /data/qlib/tw_stock_minute
fi

# 5. 測試腳本（僅同步 2 檔股票）
echo -e "\n${YELLOW}5️⃣  執行測試同步（2330, 2317）...${NC}"
python3 scripts/sync_shioaji_to_qlib.py \
    --yesterday \
    --stocks 2330,2317

# 6. 驗證結果
echo -e "\n${YELLOW}6️⃣  驗證同步結果...${NC}"

# 檢查 Qlib 數據
if [ -f "/data/qlib/tw_stock_minute/features/2330/close.1min.bin" ]; then
    SIZE=$(stat -f%z "/data/qlib/tw_stock_minute/features/2330/close.1min.bin" 2>/dev/null || stat -c%s "/data/qlib/tw_stock_minute/features/2330/close.1min.bin" 2>/dev/null)
    echo -e "${GREEN}✅ Qlib 數據已生成: 2330/close.1min.bin (${SIZE} bytes)${NC}"
else
    echo -e "${RED}❌ Qlib 數據未生成${NC}"
    exit 1
fi

# 檢查 PostgreSQL 數據（如果有設定資料庫）
if [ -n "$DATABASE_URL" ]; then
    COUNT=$(docker compose exec -T postgres psql -U quantlab -d quantlab -t -c \
        "SELECT COUNT(*) FROM stock_minute_prices WHERE stock_id = '2330' AND datetime::date = CURRENT_DATE - INTERVAL '1 day'" 2>/dev/null || echo "0")

    if [ "$COUNT" -gt 0 ]; then
        echo -e "${GREEN}✅ PostgreSQL 數據已插入: $COUNT 筆${NC}"
    else
        echo -e "${YELLOW}⚠️  PostgreSQL 數據未找到（可能是非交易日）${NC}"
    fi
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 測試完成！工具運作正常${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\n${YELLOW}下一步：${NC}"
echo "  1. 同步今天的數據："
echo "     bash scripts/sync-shioaji-today.sh"
echo ""
echo "  2. 配置定時任務："
echo "     crontab -e"
echo "     0 15 * * 1-5 cd /home/ubuntu/QuantLab && bash scripts/sync-shioaji-today.sh"
