#!/bin/bash
# Shioaji 智慧增量同步腳本
# 用途：收盤後自動同步缺失的 1 分鐘 K 線到 PostgreSQL + Qlib
# 建議定時任務：每個交易日 15:00 執行

set -e

# 顏色輸出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🧠 Shioaji 智慧增量同步${NC}"
echo -e "${GREEN}時間: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${GREEN}========================================${NC}"

# 進入專案目錄
cd /home/ubuntu/QuantLab/backend

# 檢查 Shioaji 環境變數
if [ -z "$SHIOAJI_API_KEY" ] || [ -z "$SHIOAJI_SECRET_KEY" ]; then
    echo -e "${RED}❌ 錯誤: Shioaji API 金鑰未設定${NC}"
    echo -e "${YELLOW}請在 .env 文件中設定:${NC}"
    echo "  SHIOAJI_API_KEY=your_api_key"
    echo "  SHIOAJI_SECRET_KEY=your_secret_key"
    exit 1
fi

# 顯示設定
echo -e "${YELLOW}📊 同步設定:${NC}"
echo "  - 模式: 🧠 智慧增量（自動檢測最後日期）"
echo "  - 目標日期: 今天 ($(date '+%Y-%m-%d'))"
echo "  - 股票: 從 PostgreSQL 讀取清單"
echo "  - 存儲: PostgreSQL + Qlib 雙軌"
echo ""

# 執行同步（使用智慧模式）
echo -e "${GREEN}🚀 開始智慧同步...${NC}"
python3 scripts/sync_shioaji_to_qlib.py --smart

# 檢查執行結果
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 同步完成！${NC}"
else
    echo -e "${RED}❌ 同步失敗，請檢查日誌${NC}"
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}同步結束: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${GREEN}========================================${NC}"
