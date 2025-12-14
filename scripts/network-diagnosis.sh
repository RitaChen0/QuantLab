#!/bin/bash
# 網絡診斷腳本
# 快速檢查系統和網絡狀態

echo "======================================="
echo "📊 系統資源狀態"
echo "======================================="
echo "負載: $(uptime | awk -F'load average:' '{print $2}')"
free -h | grep -E "Mem|Swap"
df -h / | tail -1

echo ""
echo "======================================="
echo "🐳 Docker 容器狀態"
echo "======================================="
docker compose ps --format "table {{.Name}}\t{{.Status}}"

echo ""
echo "======================================="
echo "🌐 網絡連接統計"
echo "======================================="
echo "TCP 連接狀態分布："
netstat -ant | awk '{print $6}' | sort | uniq -c | sort -rn

echo ""
echo "關鍵服務端口監聽："
ss -tlnp | grep -E ":(22|80|443|3000|8000|5432|6379)"

echo ""
echo "======================================="
echo "🔌 SSH 連接歷史（最近 10 次）"
echo "======================================="
journalctl -u ssh -n 10 --no-pager | grep "Accepted"

echo ""
echo "======================================="
echo "🔧 SSH Keep-Alive 設定"
echo "======================================="
grep -E "ClientAlive|TCPKeepAlive" /etc/ssh/sshd_config

echo ""
echo "======================================="
echo "🌍 網絡延遲測試"
echo "======================================="
echo "Google DNS (8.8.8.8):"
ping -c 3 8.8.8.8 2>&1 | tail -2

echo ""
echo "Cloudflare DNS (1.1.1.1):"
ping -c 3 1.1.1.1 2>&1 | tail -2

echo ""
echo "======================================="
echo "✅ 診斷完成"
echo "======================================="
