#!/bin/bash
# 分析被攔截的惡意 IP

echo "=== 🔒 惡意掃描 IP 分析 ==="
echo ""

# 檢查日誌是否存在
if ! docker compose exec nginx test -s /var/log/nginx/blocked.log 2>/dev/null; then
    echo "✅ 尚未記錄到惡意掃描"
    exit 0
fi

# 統計總攔截次數
TOTAL=$(docker compose exec nginx wc -l /var/log/nginx/blocked.log 2>/dev/null | awk '{print $1}')
echo "📊 總攔截次數: $TOTAL"
echo ""

# Top 10 惡意 IP
echo "🎯 Top 10 惡意 IP:"
docker compose exec nginx sh -c "awk '{print \$2}' /var/log/nginx/blocked.log | sort | uniq -c | sort -rn | head -10"
echo ""

# Top 10 被攻擊的路徑
echo "🔍 Top 10 被攻擊路徑:"
docker compose exec nginx sh -c "awk '{print \$6}' /var/log/nginx/blocked.log | sort | uniq -c | sort -rn | head -10"
echo ""

# 最近 10 次攻擊
echo "⏰ 最近 10 次攻擊:"
docker compose exec nginx tail -10 /var/log/nginx/blocked.log | awk '{print $1, $2, $6}' | column -t
echo ""

# 建議
if [ -n "$TOTAL" ] && [ "$TOTAL" -gt 100 ]; then
    echo "⚠️  建議："
    echo "   - 考慮使用 fail2ban 自動封鎖頻繁攻擊的 IP"
    echo "   - 定期清理舊日誌（避免文件過大）"
fi
