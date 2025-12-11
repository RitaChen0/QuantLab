#!/bin/bash
# Celery 任務監控腳本
# 功能：監控 Celery worker 狀態、活躍任務、任務統計

set -e

echo "======================================"
echo "   Celery 任務監控系統"
echo "======================================"
echo

# 檢查 Docker Compose 服務狀態
check_services() {
    echo "📊 檢查服務狀態..."
    docker compose ps backend celery-worker celery-beat redis
    echo
}

# 檢查 Worker 狀態
check_workers() {
    echo "👷 Worker 狀態:"
    docker compose exec backend celery -A app.core.celery_app inspect active_queues 2>/dev/null || echo "⚠️  無法連接到 worker"
    echo
}

# 檢查活躍任務
check_active_tasks() {
    echo "🏃 活躍任務:"
    docker compose exec backend celery -A app.core.celery_app inspect active 2>/dev/null || echo "ℹ️  當前無活躍任務"
    echo
}

# 檢查已註冊的任務
check_registered_tasks() {
    echo "📝 已註冊任務:"
    docker compose exec backend celery -A app.core.celery_app inspect registered | head -30
    echo
}

# 檢查 Worker 統計
check_stats() {
    echo "📈 Worker 統計資訊:"
    docker compose exec backend celery -A app.core.celery_app inspect stats 2>/dev/null || echo "⚠️  無法取得統計資訊"
    echo
}

# 檢查 Redis 隊列
check_redis_queues() {
    echo "🔴 Redis 隊列狀態:"
    echo "  - Backtest 隊列長度:"
    docker compose exec redis redis-cli LLEN celery-task-meta-backtest 2>/dev/null || echo "    N/A"
    echo "  - 總 Key 數量:"
    docker compose exec redis redis-cli DBSIZE
    echo
}

# 檢查最近日誌
check_recent_logs() {
    echo "📜 最近日誌（celery-worker，最近 20 行）:"
    docker compose logs --tail 20 celery-worker | tail -20
    echo
}

# 主菜單
show_menu() {
    echo "======================================"
    echo "選擇監控項目:"
    echo "  1) 服務狀態"
    echo "  2) Worker 狀態"
    echo "  3) 活躍任務"
    echo "  4) 已註冊任務"
    echo "  5) Worker 統計"
    echo "  6) Redis 隊列"
    echo "  7) 最近日誌"
    echo "  8) 完整報告（全部）"
    echo "  9) 持續監控（每 10 秒刷新）"
    echo "  0) 退出"
    echo "======================================"
    read -p "請選擇 [0-9]: " choice
}

# 完整報告
full_report() {
    clear
    echo "======================================"
    echo "   Celery 完整監控報告"
    echo "   時間: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "======================================"
    echo

    check_services
    check_workers
    check_active_tasks
    check_stats
    check_redis_queues
    check_recent_logs
}

# 持續監控
continuous_monitor() {
    while true; do
        full_report
        echo "⏳ 等待 10 秒後刷新... (Ctrl+C 停止)"
        sleep 10
    done
}

# 如果有參數，直接執行對應功能
if [ "$1" == "--full" ]; then
    full_report
    exit 0
elif [ "$1" == "--watch" ]; then
    continuous_monitor
    exit 0
elif [ "$1" == "--help" ]; then
    echo "用法: $0 [選項]"
    echo "選項:"
    echo "  --full    顯示完整報告"
    echo "  --watch   持續監控（每 10 秒）"
    echo "  --help    顯示此幫助訊息"
    echo
    echo "無參數時顯示互動式菜單"
    exit 0
fi

# 互動模式
while true; do
    show_menu

    case $choice in
        1)
            clear
            check_services
            read -p "按 Enter 繼續..."
            ;;
        2)
            clear
            check_workers
            read -p "按 Enter 繼續..."
            ;;
        3)
            clear
            check_active_tasks
            read -p "按 Enter 繼續..."
            ;;
        4)
            clear
            check_registered_tasks
            read -p "按 Enter 繼續..."
            ;;
        5)
            clear
            check_stats
            read -p "按 Enter 繼續..."
            ;;
        6)
            clear
            check_redis_queues
            read -p "按 Enter 繼續..."
            ;;
        7)
            clear
            check_recent_logs
            read -p "按 Enter 繼續..."
            ;;
        8)
            full_report
            read -p "按 Enter 繼續..."
            ;;
        9)
            continuous_monitor
            ;;
        0)
            echo "退出監控系統"
            exit 0
            ;;
        *)
            echo "無效選擇，請重試"
            sleep 1
            ;;
    esac

    clear
done
