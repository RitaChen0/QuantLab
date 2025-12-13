#!/bin/bash
# 從 PostgreSQL 轉換分鐘線數據到 Qlib 格式
# 用途：一次性轉換現有的 6500 萬筆分鐘線資料

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}📊 PostgreSQL → Qlib 分鐘線轉換${NC}"
echo -e "${GREEN}時間: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${GREEN}========================================${NC}"

# 進入專案目錄
cd /home/ubuntu/QuantLab/backend

# 檢查資料庫連接
echo -e "\n${YELLOW}1️⃣  檢查資料庫連接...${NC}"
if docker compose exec -T postgres psql -U quantlab -d quantlab -c "SELECT COUNT(*) FROM stock_minute_prices;" > /dev/null 2>&1; then
    RECORD_COUNT=$(docker compose exec -T postgres psql -U quantlab -d quantlab -t -c "SELECT COUNT(*) FROM stock_minute_prices;")
    echo -e "${GREEN}✅ 資料庫連接成功${NC}"
    echo -e "   總記錄數: $(echo $RECORD_COUNT | xargs) 筆"
else
    echo -e "${RED}❌ 無法連接資料庫${NC}"
    exit 1
fi

# 顯示設定
echo -e "\n${YELLOW}2️⃣  轉換設定:${NC}"
echo "  - 來源: PostgreSQL (stock_minute_prices 表)"
echo "  - 目標: /data/qlib/tw_stock_minute/"
echo "  - 模式: 🧠 智慧增量轉換"
echo "  - 股票: 全部 (約 1,626 檔)"
echo ""

# 執行轉換
echo -e "${GREEN}🚀 開始轉換...${NC}"
python3 scripts/export_minute_to_qlib.py \
    --output-dir /data/qlib/tw_stock_minute \
    --smart

# 檢查執行結果
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ 轉換完成！${NC}"

    # 顯示結果統計
    echo -e "\n${YELLOW}3️⃣  驗證結果:${NC}"
    if [ -d "/data/qlib/tw_stock_minute/features/2330" ]; then
        echo -e "${GREEN}✅ Qlib 數據已生成${NC}"
        ls -lh /data/qlib/tw_stock_minute/features/2330/ | head -10
    else
        echo -e "${RED}❌ Qlib 數據未生成${NC}"
    fi
else
    echo -e "${RED}❌ 轉換失敗，請檢查日誌${NC}"
    exit 1
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}轉換結束: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${GREEN}========================================${NC}"
