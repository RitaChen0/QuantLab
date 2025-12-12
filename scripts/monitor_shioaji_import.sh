#!/bin/bash
# 監控 Shioaji 完整匯入進度
# 使用方法：
#   ./scripts/monitor_shioaji_import.sh

set -e

# ==================== 配置 ====================
LOG_DIR="/tmp/shioaji_import"
CHECK_INTERVAL=30  # 檢查間隔（秒）

# ==================== 顏色輸出 ====================
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ==================== 清除螢幕 ====================
clear

echo "================================================"
echo -e "${BLUE}🔍 Shioaji 匯入進度監控${NC}"
echo "================================================"
echo ""
echo "Press Ctrl+C to stop monitoring (匯入會繼續執行)"
echo ""

# ==================== 主循環 ====================
while true; do
    # 找出最新的日誌檔案
    LATEST_LOG=$(ls -t ${LOG_DIR}/import_all_*.log 2>/dev/null | head -1)

    if [ -z "$LATEST_LOG" ]; then
        echo -e "${YELLOW}⚠️  找不到匯入日誌檔案${NC}"
        echo ""
        echo "請先執行匯入腳本："
        echo "  ./scripts/import_all_shioaji.sh"
        echo ""
        sleep $CHECK_INTERVAL
        continue
    fi

    # 檢查匯入程序是否仍在執行
    PID_FILE="${LOG_DIR}/import.pid"
    if [ -f "$PID_FILE" ]; then
        IMPORT_PID=$(cat "$PID_FILE")
        if ps -p "$IMPORT_PID" > /dev/null 2>&1; then
            STATUS="${GREEN}🟢 執行中${NC}"
        else
            STATUS="${YELLOW}⚪ 已完成或已停止${NC}"
        fi
    else
        STATUS="${YELLOW}⚪ 狀態未知${NC}"
    fi

    # 清除螢幕並顯示標題
    clear
    echo "================================================"
    echo -e "${BLUE}🔍 Shioaji 匯入進度監控${NC}"
    echo "================================================"
    echo -e "狀態: $STATUS"
    echo -e "時間: $(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "日誌: $LATEST_LOG"
    echo "================================================"
    echo ""

    # 檢查是否完成
    if grep -q "✅ Import Completed" "$LATEST_LOG" 2>/dev/null; then
        echo -e "${GREEN}================================================${NC}"
        echo -e "${GREEN}✅ 匯入已完成！${NC}"
        echo -e "${GREEN}================================================${NC}"
        echo ""

        # 顯示統計摘要
        tail -50 "$LATEST_LOG" | grep -A 20 "Import Completed"

        echo ""
        echo -e "${CYAN}完整日誌:${NC} $LATEST_LOG"
        echo ""
        break
    fi

    # 顯示即時統計
    echo -e "${CYAN}📊 即時統計：${NC}"
    echo "----------------------------------------"

    # 已處理的股票數（計算成功匯入的股票）
    PROCESSED=$(grep -c "✅.*Inserted" "$LATEST_LOG" 2>/dev/null || echo "0")
    echo -e "  已處理股票: ${GREEN}${PROCESSED}${NC} / ~1,692"

    # 已插入記錄數
    INSERTED=$(grep "Records inserted:" "$LATEST_LOG" 2>/dev/null | tail -1 | grep -oP '\d+(?= records/second)' || echo "0")
    if [ "$INSERTED" != "0" ]; then
        echo -e "  插入速度: ${GREEN}${INSERTED}${NC} records/second"
    fi

    # 最近處理的股票
    RECENT_STOCK=$(grep "✅.*Inserted" "$LATEST_LOG" 2>/dev/null | tail -1 | grep -oP '✅ \K\d+' || echo "N/A")
    if [ "$RECENT_STOCK" != "N/A" ]; then
        echo -e "  最近處理: ${YELLOW}${RECENT_STOCK}${NC}"
    fi

    echo "----------------------------------------"
    echo ""

    # 顯示最近 10 行日誌
    echo -e "${CYAN}📝 最近日誌：${NC}"
    echo "----------------------------------------"
    tail -10 "$LATEST_LOG" | sed 's/^/  /'
    echo "----------------------------------------"
    echo ""

    # 資料庫記錄數
    echo -e "${CYAN}💾 資料庫狀態：${NC}"
    echo "----------------------------------------"
    DB_COUNT=$(docker compose exec -T postgres psql -U quantlab quantlab -t -c "SELECT COUNT(*) FROM stock_minute_prices;" 2>/dev/null | xargs || echo "N/A")
    if [ "$DB_COUNT" != "N/A" ]; then
        echo -e "  總記錄數: ${GREEN}$(printf "%'d" $DB_COUNT)${NC}"
    else
        echo "  總記錄數: 查詢失敗"
    fi
    echo "----------------------------------------"
    echo ""

    # 操作提示
    echo -e "${BLUE}💡 操作指令：${NC}"
    echo "  tail -f $LATEST_LOG          # 即時查看完整日誌"
    echo "  kill $IMPORT_PID              # 停止匯入"
    echo ""

    # 等待下次檢查
    echo -e "${YELLOW}下次更新: ${CHECK_INTERVAL} 秒後...${NC}"
    sleep $CHECK_INTERVAL
done

echo ""
echo -e "${GREEN}監控結束${NC}"
echo ""
