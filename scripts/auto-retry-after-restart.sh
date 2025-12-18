#!/bin/bash
# 自動在 backend 重啟後執行任務重試
# 用途：監控 backend 容器重啟，並自動觸發 retry-missed-tasks.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RETRY_SCRIPT="$SCRIPT_DIR/retry-missed-tasks.sh"
LOG_FILE="/tmp/auto-retry-tasks.log"
LAST_RESTART_FILE="/tmp/backend-last-restart"

echo "========================================"
echo "🤖 自動任務重試守護進程"
echo "========================================"
echo ""

# 檢查 retry 腳本是否存在
if [ ! -f "$RETRY_SCRIPT" ]; then
    echo "❌ 錯誤: 找不到 retry-missed-tasks.sh"
    echo "   預期位置: $RETRY_SCRIPT"
    exit 1
fi

echo "📝 日誌位置: $LOG_FILE"
echo ""

# 獲取 backend 容器的當前啟動時間
get_backend_start_time() {
    docker inspect quantlab-backend --format='{{.State.StartedAt}}' 2>/dev/null || echo ""
}

# 記錄到日誌
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 初始化
CURRENT_START_TIME=$(get_backend_start_time)
if [ -z "$CURRENT_START_TIME" ]; then
    log "❌ backend 容器未運行"
    exit 1
fi

log "✅ 初始化完成，開始監控 backend 容器"
log "   當前啟動時間: $CURRENT_START_TIME"

# 保存當前啟動時間
echo "$CURRENT_START_TIME" > "$LAST_RESTART_FILE"

# 主循環：每 30 秒檢查一次
while true; do
    sleep 30

    # 獲取當前啟動時間
    NEW_START_TIME=$(get_backend_start_time)

    # 檢查容器是否重啟
    if [ "$NEW_START_TIME" != "$CURRENT_START_TIME" ] && [ -n "$NEW_START_TIME" ]; then
        log "🔔 檢測到 backend 重啟！"
        log "   舊啟動時間: $CURRENT_START_TIME"
        log "   新啟動時間: $NEW_START_TIME"

        # 更新記錄
        CURRENT_START_TIME="$NEW_START_TIME"
        echo "$CURRENT_START_TIME" > "$LAST_RESTART_FILE"

        # 等待容器完全啟動（等待 30 秒）
        log "⏳ 等待容器完全啟動 (30 秒)..."
        sleep 30

        # 執行任務重試
        log "🔄 執行任務重試..."
        if bash "$RETRY_SCRIPT" >> "$LOG_FILE" 2>&1; then
            log "✅ 任務重試完成"
        else
            log "⚠️  任務重試執行中或部分失敗，請檢查日誌"
        fi

        log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    fi
done
