#!/bin/bash
# 背景匯入所有 Shioaji 股票資料
# 使用方法：
#   ./scripts/import_all_shioaji.sh           # 完整匯入所有股票
#   ./scripts/import_all_shioaji.sh --incremental  # 增量匯入（只匯入新資料）

set -e

# ==================== 配置 ====================
# 主機路徑（用於檢查）
HOST_DATA_DIR="/home/ubuntu/QuantLab/ShioajiData/shioaji-stock"
# 容器內路徑（傳遞給 Python 腳本）
CONTAINER_DATA_DIR="/data/shioaji/shioaji-stock"
LOG_DIR="/tmp/shioaji_import"
LOG_FILE="${LOG_DIR}/import_all_$(date +%Y%m%d_%H%M%S).log"
PROGRESS_FILE="${LOG_DIR}/progress.json"
BATCH_SIZE=50000  # 大批次提升效能

# ==================== 顏色輸出 ====================
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ==================== 函數 ====================
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1" | tee -a "$LOG_FILE"
}

# ==================== 初始化 ====================
mkdir -p "$LOG_DIR"

log_step "Shioaji 完整資料匯入"
echo "================================================" | tee -a "$LOG_FILE"
log_info "開始時間: $(date '+%Y-%m-%d %H:%M:%S')"
log_info "主機資料目錄: $HOST_DATA_DIR"
log_info "容器資料目錄: $CONTAINER_DATA_DIR"
log_info "日誌檔案: $LOG_FILE"
log_info "進度檔案: $PROGRESS_FILE"
echo "================================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# 檢查資料目錄（在主機上檢查）
if [ ! -d "$HOST_DATA_DIR" ]; then
    log_error "資料目錄不存在: $HOST_DATA_DIR"
    exit 1
fi

# 統計檔案數量（在主機上統計）
TOTAL_FILES=$(ls "$HOST_DATA_DIR"/*.csv 2>/dev/null | wc -l)
log_info "📁 發現 $TOTAL_FILES 個 CSV 檔案"

if [ "$TOTAL_FILES" -eq 0 ]; then
    log_error "找不到任何 CSV 檔案"
    exit 1
fi

# 解析參數
INCREMENTAL_FLAG=""
if [[ "$1" == "--incremental" ]]; then
    INCREMENTAL_FLAG="--incremental"
    log_info "🔄 增量匯入模式（只匯入新資料）"
else
    log_info "📦 完整匯入模式（匯入所有資料）"
fi

# ==================== 執行匯入 ====================
log_step "開始背景匯入..."
echo "" | tee -a "$LOG_FILE"

# 在 Docker 容器內執行匯入腳本（使用容器內路徑）
docker compose exec -T backend python /app/scripts/import_shioaji_csv.py \
    --data-dir "$CONTAINER_DATA_DIR" \
    --batch-size $BATCH_SIZE \
    $INCREMENTAL_FLAG \
    2>&1 | tee -a "$LOG_FILE" &

# 儲存背景程序 PID
IMPORT_PID=$!
echo "$IMPORT_PID" > "${LOG_DIR}/import.pid"

log_info "✅ 匯入程序已在背景執行 (PID: $IMPORT_PID)"
echo "" | tee -a "$LOG_FILE"

# ==================== 監控提示 ====================
echo "================================================" | tee -a "$LOG_FILE"
log_info "🔍 監控指令："
echo "" | tee -a "$LOG_FILE"
echo "  # 即時監控進度" | tee -a "$LOG_FILE"
echo "  tail -f $LOG_FILE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "  # 檢查匯入狀態" | tee -a "$LOG_FILE"
echo "  ps aux | grep import_shioaji_csv" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "  # 停止匯入" | tee -a "$LOG_FILE"
echo "  kill $IMPORT_PID" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "  # 查看資料庫記錄數" | tee -a "$LOG_FILE"
echo "  docker compose exec postgres psql -U quantlab quantlab -c \"SELECT COUNT(*) FROM stock_minute_prices;\"" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "  # 查看已匯入的股票數" | tee -a "$LOG_FILE"
echo "  docker compose exec postgres psql -U quantlab quantlab -c \"SELECT COUNT(DISTINCT stock_id) FROM stock_minute_prices;\"" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "================================================" | tee -a "$LOG_FILE"

# ==================== 完成提示 ====================
log_info "💡 匯入將在背景執行，預計需要 4-8 小時（視資料量而定）"
log_info "📋 完整日誌: $LOG_FILE"
echo ""
