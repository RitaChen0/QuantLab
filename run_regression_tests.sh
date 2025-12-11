#!/bin/bash
# 自動化回歸測試流程
# 功能：運行所有回測測試，生成測試報告

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 測試配置
TEST_SCRIPTS=(
    "test_rate_limit_fix.py:Rate Limit 修復驗證"
    "test_long_range_backtest.py:長時間範圍回測測試"
    "test_multi_stock_backtest.py:多檔股票並發測試"
    "test_stress_backtest.py:壓力測試（10 並發）"
    "test_boundary_backtest.py:邊界測試"
)

# 測試結果儲存
TEST_RESULTS=()
PASS_COUNT=0
FAIL_COUNT=0
TOTAL_START_TIME=$(date +%s)

# 日誌檔案
LOG_DIR="test_logs"
mkdir -p "$LOG_DIR"
REPORT_FILE="$LOG_DIR/regression_test_$(date +%Y%m%d_%H%M%S).log"

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}   自動化回歸測試流程${NC}"
echo -e "${BLUE}   開始時間: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${BLUE}=====================================${NC}"
echo

# 記錄到檔案
exec > >(tee -a "$REPORT_FILE") 2>&1

echo "📝 測試報告將保存至: $REPORT_FILE"
echo

# 清除 Rate Limit
clear_rate_limits() {
    echo -e "${YELLOW}🧹 清除 Rate Limit...${NC}"
    docker compose exec redis redis-cli KEYS "LIMITS:LIMITER*" | \
        xargs -r -I {} docker compose exec redis redis-cli DEL {} > /dev/null 2>&1 || true
    echo -e "${GREEN}✅ Rate Limit 已清除${NC}"
    echo
}

# 檢查服務狀態
check_services() {
    echo -e "${YELLOW}🔍 檢查服務狀態...${NC}"

    # 檢查 backend
    if ! docker compose ps backend | grep -q "Up"; then
        echo -e "${RED}❌ Backend 服務未運行${NC}"
        exit 1
    fi

    # 檢查 celery-worker
    if ! docker compose ps celery-worker | grep -q "Up"; then
        echo -e "${RED}❌ Celery Worker 未運行${NC}"
        exit 1
    fi

    # 檢查 Redis
    if ! docker compose exec redis redis-cli ping | grep -q "PONG"; then
        echo -e "${RED}❌ Redis 未運行${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ 所有服務正常運行${NC}"
    echo
}

# 運行單個測試
run_test() {
    local test_script=$1
    local test_name=$2
    local test_num=$3
    local total_tests=$4

    echo -e "${BLUE}=====================================${NC}"
    echo -e "${BLUE}測試 $test_num/$total_tests: $test_name${NC}"
    echo -e "${BLUE}=====================================${NC}"
    echo

    local start_time=$(date +%s)
    local log_file="$LOG_DIR/$(basename $test_script .py)_$(date +%Y%m%d_%H%M%S).log"

    # 運行測試並保存日誌
    if timeout 600 python3 "$test_script" 2>&1 | tee "$log_file"; then
        local end_time=$(date +%s)
        local elapsed=$((end_time - start_time))

        echo
        echo -e "${GREEN}✅ $test_name 通過 (耗時: ${elapsed}s)${NC}"
        TEST_RESULTS+=("PASS:$test_name:${elapsed}s")
        ((PASS_COUNT++))
    else
        local end_time=$(date +%s)
        local elapsed=$((end_time - start_time))

        echo
        echo -e "${RED}❌ $test_name 失敗 (耗時: ${elapsed}s)${NC}"
        TEST_RESULTS+=("FAIL:$test_name:${elapsed}s")
        ((FAIL_COUNT++))
    fi

    echo
    sleep 2  # 測試間隔
}

# 生成測試摘要
generate_summary() {
    local total_end_time=$(date +%s)
    local total_elapsed=$((total_end_time - TOTAL_START_TIME))

    echo
    echo -e "${BLUE}=====================================${NC}"
    echo -e "${BLUE}   測試摘要${NC}"
    echo -e "${BLUE}=====================================${NC}"
    echo
    echo "總測試數: $((PASS_COUNT + FAIL_COUNT))"
    echo -e "${GREEN}通過: $PASS_COUNT${NC}"
    echo -e "${RED}失敗: $FAIL_COUNT${NC}"
    echo "總耗時: ${total_elapsed}s ($(($total_elapsed / 60))m $(($total_elapsed % 60))s)"
    echo

    echo "詳細結果:"
    echo "----------------------------------------"
    for result in "${TEST_RESULTS[@]}"; do
        IFS=':' read -r status name time <<< "$result"
        if [ "$status" = "PASS" ]; then
            echo -e "${GREEN}✅ $name - $time${NC}"
        else
            echo -e "${RED}❌ $name - $time${NC}"
        fi
    done
    echo

    # 計算成功率
    local success_rate=$((PASS_COUNT * 100 / (PASS_COUNT + FAIL_COUNT)))

    if [ $FAIL_COUNT -eq 0 ]; then
        echo -e "${GREEN}🎉 所有測試通過！(成功率: 100%)${NC}"
    elif [ $success_rate -ge 80 ]; then
        echo -e "${YELLOW}⚠️  大部分測試通過 (成功率: ${success_rate}%)${NC}"
    else
        echo -e "${RED}❌ 測試失敗率過高 (成功率: ${success_rate}%)${NC}"
    fi

    echo
    echo "📊 詳細報告已保存至: $REPORT_FILE"
}

# 主流程
main() {
    # 檢查服務
    check_services

    # 詢問是否清除 Rate Limit
    if [ -z "$1" ] || [ "$1" != "--skip-clear" ]; then
        clear_rate_limits
    fi

    # 運行所有測試
    local total_tests=${#TEST_SCRIPTS[@]}
    local test_num=1

    for test_entry in "${TEST_SCRIPTS[@]}"; do
        IFS=':' read -r script name <<< "$test_entry"

        # 檢查測試腳本是否存在
        if [ ! -f "$script" ]; then
            echo -e "${YELLOW}⚠️  跳過 $name (腳本不存在: $script)${NC}"
            echo
            continue
        fi

        run_test "$script" "$name" "$test_num" "$total_tests"
        ((test_num++))
    done

    # 生成摘要
    generate_summary
}

# 處理參數
if [ "$1" == "--help" ]; then
    echo "用法: $0 [選項]"
    echo
    echo "選項:"
    echo "  --skip-clear   跳過清除 Rate Limit（快速測試）"
    echo "  --help         顯示此幫助訊息"
    echo
    echo "測試腳本:"
    for test_entry in "${TEST_SCRIPTS[@]}"; do
        IFS=':' read -r script name <<< "$test_entry"
        echo "  - $name"
    done
    exit 0
fi

# 執行主流程
main "$@"

# 結束
echo
echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}   測試完成${NC}"
echo -e "${BLUE}   結束時間: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${BLUE}=====================================${NC}"

# 退出碼（如果有失敗測試則返回 1）
if [ $FAIL_COUNT -gt 0 ]; then
    exit 1
else
    exit 0
fi
