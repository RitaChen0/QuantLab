#!/bin/bash
# QuantLab 資料庫備份腳本
# 用途: 定期備份完整資料庫

set -e  # 遇到錯誤立即停止

# 設定
BACKUP_DIR="/data/CCTest/QuantLab/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="quantlab_backup_${TIMESTAMP}.sql"
LOG_FILE="${BACKUP_DIR}/backup.log"

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================================"
echo "QuantLab 資料庫備份工具"
echo "開始時間: $(date)"
echo "============================================================"

# 創建備份目錄
mkdir -p "$BACKUP_DIR"

# 記錄到日誌
echo "[$(date)] 開始備份" >> "$LOG_FILE"

# 執行備份
echo "📦 正在備份資料庫..."
if docker compose exec -T postgres pg_dump -U quantlab quantlab > "${BACKUP_DIR}/${BACKUP_FILE}"; then
    echo -e "${GREEN}✅ 資料庫備份成功${NC}"
    echo "[$(date)] 備份成功: ${BACKUP_FILE}" >> "$LOG_FILE"
else
    echo -e "${RED}❌ 資料庫備份失敗${NC}"
    echo "[$(date)] 備份失敗" >> "$LOG_FILE"
    exit 1
fi

# 壓縮備份檔案
echo "🗜️  正在壓縮備份檔案..."
if gzip "${BACKUP_DIR}/${BACKUP_FILE}"; then
    echo -e "${GREEN}✅ 壓縮完成${NC}"

    # 顯示檔案大小
    SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}.gz" | cut -f1)
    echo "📊 備份檔案大小: ${SIZE}"
    echo "[$(date)] 壓縮完成,大小: ${SIZE}" >> "$LOG_FILE"
else
    echo -e "${RED}❌ 壓縮失敗${NC}"
    exit 1
fi

# 清理舊備份 (保留最近 30 天)
echo "🧹 清理 30 天前的舊備份..."
DELETED_COUNT=$(find "$BACKUP_DIR" -name "quantlab_backup_*.sql.gz" -mtime +30 -delete -print | wc -l)

if [ "$DELETED_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ 清理了 ${DELETED_COUNT} 個舊備份檔案${NC}"
    echo "[$(date)] 清理了 ${DELETED_COUNT} 個舊備份" >> "$LOG_FILE"
else
    echo "ℹ️  沒有需要清理的舊備份"
fi

# 列出當前所有備份
echo ""
echo "📋 當前備份列表 (最近 10 個):"
ls -lht "${BACKUP_DIR}"/quantlab_backup_*.sql.gz 2>/dev/null | head -10 || echo "無備份檔案"

# 顯示磁碟使用情況
echo ""
echo "💾 備份目錄磁碟使用情況:"
du -sh "$BACKUP_DIR"

echo ""
echo "============================================================"
echo -e "${GREEN}✅ 備份完成!${NC}"
echo "備份檔案: ${BACKUP_FILE}.gz"
echo "完成時間: $(date)"
echo "============================================================"

# 記錄完成
echo "[$(date)] 備份流程完成" >> "$LOG_FILE"
