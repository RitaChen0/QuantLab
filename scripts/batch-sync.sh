#!/bin/bash
#
# 批次同步所有股票財務指標
#
# 使用方式：
#   ./scripts/batch-sync.sh              # 正常執行（斷點續傳）
#   ./scripts/batch-sync.sh --reset      # 重新開始
#   ./scripts/batch-sync.sh --status     # 查看進度
#   ./scripts/batch-sync.sh --test       # 測試模式（僅10檔）
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          批次同步財務指標數據 - QuantLab                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 檢查服務狀態
check_services() {
    echo -e "${YELLOW}🔍 檢查服務狀態...${NC}"

    if ! docker compose ps backend | grep -q "Up"; then
        echo -e "${RED}❌ Backend 服務未運行${NC}"
        exit 1
    fi

    if ! docker compose ps postgres | grep -q "Up"; then
        echo -e "${RED}❌ PostgreSQL 服務未運行${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ 所有服務正常運行${NC}"
    echo ""
}

# 顯示進度
show_status() {
    echo -e "${BLUE}📊 查詢同步進度...${NC}"
    echo ""
    docker compose exec backend python /app/scripts/batch_sync_fundamental.py --status
}

# 測試模式（僅10檔）
test_mode() {
    echo -e "${YELLOW}⚠️  測試模式：僅處理前 10 檔股票${NC}"
    echo ""
    docker compose exec -T backend python /app/scripts/batch_sync_fundamental.py \
        --max-stocks 10 \
        --batch-size 5 \
        --batch-delay 10 \
        --reset
}

# 正常執行
normal_run() {
    local reset_flag=""

    if [ "$1" == "--reset" ]; then
        reset_flag="--reset"
        echo -e "${YELLOW}⚠️  重置模式：將清除進度並從頭開始${NC}"
    else
        echo -e "${GREEN}📋 斷點續傳模式：將從上次中斷處繼續${NC}"
    fi

    echo ""

    # 執行同步
    docker compose exec -T backend python /app/scripts/batch_sync_fundamental.py \
        --batch-size 100 \
        --batch-delay 60 \
        $reset_flag
}

# 主流程
main() {
    cd "$PROJECT_ROOT"

    # 檢查服務
    check_services

    # 根據參數執行
    case "$1" in
        --status)
            show_status
            ;;
        --test)
            test_mode
            ;;
        --reset)
            normal_run --reset
            ;;
        *)
            normal_run
            ;;
    esac
}

# 捕捉 Ctrl+C
trap 'echo -e "\n${YELLOW}⚠️  收到中斷信號，正在儲存進度...${NC}"; sleep 2; echo -e "${GREEN}✅ 進度已儲存，下次執行將續傳${NC}"; exit 0' INT

main "$@"
