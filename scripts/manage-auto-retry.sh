#!/bin/bash
# 管理自動任務重試守護進程

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTO_RETRY_SCRIPT="$SCRIPT_DIR/auto-retry-after-restart.sh"
PID_FILE="/tmp/auto-retry.pid"
LOG_FILE="/tmp/auto-retry-tasks.log"

case "$1" in
  start)
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
      echo "⚠️  自動重試守護進程已在運行中"
      echo "   PID: $(cat $PID_FILE)"
      exit 1
    fi

    echo "🚀 啟動自動重試守護進程..."
    nohup bash "$AUTO_RETRY_SCRIPT" > /tmp/auto-retry.log 2>&1 &
    echo $! > "$PID_FILE"
    echo "✅ 已啟動，PID: $(cat $PID_FILE)"
    echo "📝 日誌位置: $LOG_FILE"
    ;;

  stop)
    if [ ! -f "$PID_FILE" ]; then
      echo "⚠️  守護進程未運行"
      exit 1
    fi

    PID=$(cat "$PID_FILE")
    echo "🛑 停止守護進程 (PID: $PID)..."
    kill $PID 2>/dev/null
    rm -f "$PID_FILE"
    echo "✅ 已停止"
    ;;

  status)
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
      echo "✅ 守護進程運行中"
      echo "   PID: $(cat $PID_FILE)"
      echo "   日誌: tail -f $LOG_FILE"
    else
      echo "❌ 守護進程未運行"
      [ -f "$PID_FILE" ] && rm -f "$PID_FILE"
    fi
    ;;

  logs)
    if [ ! -f "$LOG_FILE" ]; then
      echo "⚠️  日誌文件不存在"
      exit 1
    fi

    if [ "$2" == "-f" ]; then
      tail -f "$LOG_FILE"
    else
      tail -30 "$LOG_FILE"
    fi
    ;;

  restart)
    $0 stop
    sleep 2
    $0 start
    ;;

  *)
    echo "用法: $0 {start|stop|status|logs|logs -f|restart}"
    echo ""
    echo "命令說明:"
    echo "  start   - 啟動守護進程"
    echo "  stop    - 停止守護進程"
    echo "  status  - 查看運行狀態"
    echo "  logs    - 查看最近 30 行日誌"
    echo "  logs -f - 實時追蹤日誌"
    echo "  restart - 重啟守護進程"
    exit 1
    ;;
esac
