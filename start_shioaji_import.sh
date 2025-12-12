#!/bin/bash
# 一鍵啟動 Shioaji 完整匯入
# 使用方法：
#   ./start_shioaji_import.sh              # 完整匯入
#   ./start_shioaji_import.sh incremental  # 增量匯入

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

clear

echo "================================================"
echo -e "${BLUE}🚀 Shioaji 完整資料匯入${NC}"
echo "================================================"
echo ""

# 檢查資料檔案（在容器內檢查）
echo -e "${BLUE}🔍 檢查資料檔案...${NC}"
TOTAL_FILES=$(docker compose exec -T backend sh -c 'ls /data/shioaji/shioaji-stock/*.csv 2>/dev/null | wc -l')

if [ "$TOTAL_FILES" -eq 0 ]; then
    echo -e "${RED}❌ 找不到資料檔案${NC}"
    echo ""
    echo "請確認："
    echo "  1. ShioajiData 目錄存在於專案根目錄"
    echo "  2. shioaji-stock 子目錄包含 CSV 檔案"
    echo "  3. Docker volume 掛載正確"
    exit 1
fi

echo -e "${GREEN}✅ 發現 $TOTAL_FILES 個 CSV 檔案${NC}"
echo ""

# 判斷匯入模式
INCREMENTAL_FLAG=""
if [ "$1" == "incremental" ]; then
    INCREMENTAL_FLAG="--incremental"
    echo -e "${YELLOW}📦 增量匯入模式（只匯入新資料）${NC}"
else
    echo -e "${YELLOW}📦 完整匯入模式（匯入所有資料）${NC}"
fi

echo ""
echo "================================================"
echo -e "${BLUE}預計時間: 4-8 小時${NC}"
echo -e "${BLUE}預計記錄數: 60,000,000 - 120,000,000 筆${NC}"
echo "================================================"
echo ""
echo "匯入將在 3 秒後開始..."
sleep 3

# 啟動匯入
echo ""
echo -e "${GREEN}🚀 啟動背景匯入...${NC}"
/home/ubuntu/QuantLab/scripts/import_all_shioaji.sh $INCREMENTAL_FLAG &

# 等待日誌檔案生成
echo ""
echo "等待日誌檔案生成..."
sleep 5

# 啟動監控
echo ""
echo -e "${GREEN}🔍 啟動進度監控...${NC}"
echo ""
sleep 2
/home/ubuntu/QuantLab/scripts/monitor_shioaji_import.sh
