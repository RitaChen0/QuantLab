#!/bin/bash
# 檢查並開放必要端口的腳本

echo "========================================="
echo "🔍 檢查當前防火牆狀態"
echo "========================================="
echo ""

# 檢查 UFW 狀態
if command -v ufw &> /dev/null; then
    echo "📋 UFW 防火牆狀態："
    sudo ufw status verbose
    echo ""
else
    echo "⚠️  UFW 未安裝"
    echo ""
fi

# 檢查正在監聽的端口
echo "========================================="
echo "🔌 正在監聽的端口"
echo "========================================="
echo ""
echo "關鍵服務端口："
sudo ss -tlnp | grep -E ":(22|80|443|3000|8000|5432|6379|9090|3100)" | awk '{print $4, $6}' | column -t
echo ""

# 檢查 Docker 端口映射
echo "========================================="
echo "🐳 Docker 端口映射"
echo "========================================="
echo ""
docker compose ps --format "table {{.Name}}\t{{.Ports}}"
echo ""

# 測試端口可達性
echo "========================================="
echo "🌐 端口可達性測試"
echo "========================================="
echo ""

test_port() {
    local port=$1
    local service=$2
    if timeout 2 bash -c "echo > /dev/tcp/localhost/$port" 2>/dev/null; then
        echo "✅ Port $port ($service) - 可訪問"
    else
        echo "❌ Port $port ($service) - 無法訪問"
    fi
}

test_port 22 "SSH"
test_port 80 "HTTP"
test_port 443 "HTTPS"
test_port 3000 "Frontend"
test_port 8000 "Backend API"
test_port 5432 "PostgreSQL"
test_port 6379 "Redis"

echo ""
echo "========================================="
echo "✅ 檢查完成"
echo "========================================="
