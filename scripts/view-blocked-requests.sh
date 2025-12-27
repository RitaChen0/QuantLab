#!/bin/bash
# 查看被 Nginx 攔截的惡意請求

echo "=== 被攔截的惡意請求統計 ==="
echo ""

if docker compose exec nginx test -f /var/log/nginx/blocked.log; then
    echo "📊 過去 24 小時內被攔截的請求："
    docker compose exec nginx sh -c "tail -1000 /var/log/nginx/blocked.log | awk '{print \$7}' | sort | uniq -c | sort -rn | head -20"
    echo ""
    echo "📈 攔截總數："
    docker compose exec nginx sh -c "wc -l /var/log/nginx/blocked.log"
else
    echo "✅ 尚未記錄到任何被攔截的請求"
fi

echo ""
echo "=== 即時監控被攔截的請求（按 Ctrl+C 停止）==="
docker compose logs nginx -f | grep --line-buffered "444"
