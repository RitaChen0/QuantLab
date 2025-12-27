#!/bin/bash
# Nginx 日誌查看工具

echo "=== QuantLab Nginx 日誌 ==="
echo ""

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 選單
echo "請選擇查看的日誌類型："
echo "  1) 訪問日誌（最近 20 條）"
echo "  2) 錯誤日誌（最近 20 條）"
echo "  3) 攔截日誌（惡意請求）"
echo "  4) 即時追蹤訪問日誌"
echo "  5) 統計訪問 Top 10 路徑"
echo "  6) 統計訪問來源 IP Top 10"
echo ""
read -p "選擇 [1-6]: " choice

case $choice in
    1)
        echo -e "${GREEN}=== 訪問日誌（最近 20 條）===${NC}"
        docker compose exec nginx tail -20 /var/log/nginx/quantlab-access.log
        ;;
    2)
        echo -e "${YELLOW}=== 錯誤日誌（最近 20 條）===${NC}"
        docker compose exec nginx tail -20 /var/log/nginx/quantlab-error.log
        ;;
    3)
        echo -e "${RED}=== 攔截日誌（惡意請求）===${NC}"
        if docker compose exec nginx test -f /var/log/nginx/blocked.log && [ -s /var/log/nginx/blocked.log ]; then
            echo "最近 20 條被攔截的請求："
            docker compose exec nginx tail -20 /var/log/nginx/blocked.log
            echo ""
            echo "統計被攔截的路徑："
            docker compose exec nginx sh -c "awk '{print \$4}' /var/log/nginx/blocked.log | sort | uniq -c | sort -rn | head -10"
        else
            echo "✅ 尚未記錄到被攔截的請求"
        fi
        ;;
    4)
        echo -e "${GREEN}=== 即時追蹤訪問日誌（按 Ctrl+C 停止）===${NC}"
        docker compose exec nginx tail -f /var/log/nginx/quantlab-access.log
        ;;
    5)
        echo -e "${GREEN}=== 訪問 Top 10 路徑 ===${NC}"
        docker compose exec nginx sh -c "awk '{print \$4}' /var/log/nginx/quantlab-access.log | sort | uniq -c | sort -rn | head -10"
        ;;
    6)
        echo -e "${GREEN}=== 訪問來源 IP Top 10 ===${NC}"
        docker compose exec nginx sh -c "awk '{print \$2}' /var/log/nginx/quantlab-access.log | sort | uniq -c | sort -rn | head -10"
        ;;
    *)
        echo "無效選擇"
        exit 1
        ;;
esac
