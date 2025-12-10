#!/bin/bash
# QuantLab 手動同步腳本
# 用於手動觸發各種數據同步任務

set -e

echo "=========================================="
echo "QuantLab 手動同步工具"
echo "=========================================="
echo ""

# 顏色定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

show_menu() {
    echo "請選擇要執行的任務："
    echo ""
    echo "  1) 同步股票列表 (sync_stock_list)"
    echo "  2) 同步每日價格 (sync_daily_prices)"
    echo "  3) 同步 OHLCV 數據 (sync_ohlcv_data)"
    echo "  4) 同步最新價格 (sync_latest_prices)"
    echo "  5) 清理過期快取 (cleanup_old_cache)"
    echo "  6) 🔥 同步財務指標 - 完整版 (sync_fundamental_data)"
    echo "  7) 🔥 同步財務指標 - 快速版 (sync_fundamental_latest)"
    echo "  8) 🚀 執行所有同步任務"
    echo "  9) 📊 查看任務狀態"
    echo "  0) 退出"
    echo ""
}

run_task() {
    local task_name=$1
    local display_name=$2

    echo -e "${BLUE}開始執行: ${display_name}${NC}"
    echo "任務名稱: $task_name"

    result=$(docker compose exec -T backend python -c "
from app.core.celery_app import celery_app
result = celery_app.send_task('$task_name')
print(f'Task ID: {result.id}')
")

    echo -e "${GREEN}✅ 任務已提交${NC}"
    echo "$result"
    echo ""
}

check_status() {
    echo -e "${BLUE}查詢任務狀態...${NC}"
    docker compose exec backend celery -A app.core.celery_app inspect active
}

# 主程式
if [ "$1" != "" ]; then
    # 命令行參數模式
    case $1 in
        1|stock-list)
            run_task "app.tasks.sync_stock_list" "同步股票列表"
            ;;
        2|daily-prices)
            run_task "app.tasks.sync_daily_prices" "同步每日價格"
            ;;
        3|ohlcv)
            run_task "app.tasks.sync_ohlcv_data" "同步 OHLCV 數據"
            ;;
        4|latest-prices)
            run_task "app.tasks.sync_latest_prices" "同步最新價格"
            ;;
        5|cleanup)
            run_task "app.tasks.cleanup_old_cache" "清理過期快取"
            ;;
        6|fundamental)
            run_task "app.tasks.sync_fundamental_data" "同步財務指標（完整版）"
            ;;
        7|fundamental-latest)
            run_task "app.tasks.sync_fundamental_latest" "同步財務指標（快速版）"
            ;;
        8|all)
            echo -e "${YELLOW}執行所有同步任務...${NC}"
            run_task "app.tasks.sync_stock_list" "1/7 同步股票列表"
            sleep 2
            run_task "app.tasks.sync_daily_prices" "2/7 同步每日價格"
            sleep 2
            run_task "app.tasks.sync_ohlcv_data" "3/7 同步 OHLCV 數據"
            sleep 2
            run_task "app.tasks.sync_latest_prices" "4/7 同步最新價格"
            sleep 2
            run_task "app.tasks.cleanup_old_cache" "5/7 清理過期快取"
            sleep 2
            run_task "app.tasks.sync_fundamental_data" "6/7 同步財務指標（完整版）"
            sleep 2
            run_task "app.tasks.sync_fundamental_latest" "7/7 同步財務指標（快速版）"
            echo -e "${GREEN}✅ 所有任務已提交${NC}"
            ;;
        9|status)
            check_status
            ;;
        *)
            echo "未知選項: $1"
            echo "用法: $0 [1-9|stock-list|daily-prices|ohlcv|latest-prices|cleanup|fundamental|fundamental-latest|all|status]"
            exit 1
            ;;
    esac
else
    # 互動模式
    while true; do
        show_menu
        read -p "請輸入選項 [0-9]: " choice

        case $choice in
            1)
                run_task "app.tasks.sync_stock_list" "同步股票列表"
                ;;
            2)
                run_task "app.tasks.sync_daily_prices" "同步每日價格"
                ;;
            3)
                run_task "app.tasks.sync_ohlcv_data" "同步 OHLCV 數據"
                ;;
            4)
                run_task "app.tasks.sync_latest_prices" "同步最新價格"
                ;;
            5)
                run_task "app.tasks.cleanup_old_cache" "清理過期快取"
                ;;
            6)
                run_task "app.tasks.sync_fundamental_data" "同步財務指標（完整版）"
                ;;
            7)
                run_task "app.tasks.sync_fundamental_latest" "同步財務指標（快速版）"
                ;;
            8)
                echo -e "${YELLOW}執行所有同步任務...${NC}"
                run_task "app.tasks.sync_stock_list" "1/7 同步股票列表"
                sleep 2
                run_task "app.tasks.sync_daily_prices" "2/7 同步每日價格"
                sleep 2
                run_task "app.tasks.sync_ohlcv_data" "3/7 同步 OHLCV 數據"
                sleep 2
                run_task "app.tasks.sync_latest_prices" "4/7 同步最新價格"
                sleep 2
                run_task "app.tasks.cleanup_old_cache" "5/7 清理過期快取"
                sleep 2
                run_task "app.tasks.sync_fundamental_data" "6/7 同步財務指標（完整版）"
                sleep 2
                run_task "app.tasks.sync_fundamental_latest" "7/7 同步財務指標（快速版）"
                echo -e "${GREEN}✅ 所有任務已提交${NC}"
                ;;
            9)
                check_status
                ;;
            0)
                echo "退出"
                exit 0
                ;;
            *)
                echo -e "${YELLOW}無效選項，請重新選擇${NC}"
                ;;
        esac

        echo ""
        read -p "按 Enter 繼續..."
        clear
    done
fi
