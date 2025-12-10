#!/bin/bash
# QuantLab 產業分類資料備份腳本
# 用途: 僅備份產業分類相關資料表 (industries, stock_industries)

set -e

# 設定
BACKUP_DIR="/data/CCTest/QuantLab/backups/industries"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="industries_${TIMESTAMP}.sql"

# 顏色輸出
GREEN='\033[0;32m'
NC='\033[0m'

echo "============================================================"
echo "產業分類資料備份工具"
echo "開始時間: $(date)"
echo "============================================================"

# 創建備份目錄
mkdir -p "$BACKUP_DIR"

# 執行備份
echo "📦 正在備份產業分類資料..."
docker compose exec -T postgres pg_dump -U quantlab quantlab \
  -t industries \
  -t stock_industries \
  > "${BACKUP_DIR}/${BACKUP_FILE}"

# 壓縮
echo "🗜️  正在壓縮..."
gzip "${BACKUP_DIR}/${BACKUP_FILE}"

# 顯示結果
SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}.gz" | cut -f1)
echo -e "${GREEN}✅ 備份完成!${NC}"
echo "檔案: ${BACKUP_FILE}.gz"
echo "大小: ${SIZE}"

# 統計資料
echo ""
echo "📊 資料統計:"
docker compose exec -T postgres psql -U quantlab quantlab -c "
SELECT
  '產業數量' as item,
  COUNT(*)::text as count
FROM industries
UNION ALL
SELECT
  '股票-產業對應數',
  COUNT(*)::text
FROM stock_industries;
"

echo ""
echo "============================================================"
echo "完成時間: $(date)"
echo "============================================================"
