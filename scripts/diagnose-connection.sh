#!/bin/bash
# 診斷連接問題

echo "🔍 QuantLab 連接診斷工具"
echo "================================"
echo ""

echo "1️⃣ 檢查服務狀態..."
docker compose ps | grep -E "(frontend|backend|nginx)" | awk '{print "   ", $1, $NF}'
echo ""

echo "2️⃣ 檢查端口監聽..."
netstat -tuln | grep -E ":(80|3000|8000)" | awk '{print "   ", $4, "->", $1}'
echo ""

echo "3️⃣ 測試本地連接..."
echo -n "   localhost:80 (Nginx) -> "
curl -s -o /dev/null -w "%{http_code}" http://localhost --max-time 2
echo ""
echo -n "   localhost:3000 (Frontend) -> "
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 --max-time 2
echo ""
echo -n "   localhost:8000 (Backend) -> "
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health --max-time 2
echo ""
echo ""

echo "4️⃣ 測試 IP 連接..."
echo -n "   122.116.152.55:80 (Nginx) -> "
timeout 3 curl -s -o /dev/null -w "%{http_code}" http://122.116.152.55 || echo "TIMEOUT"
echo ""
echo -n "   122.116.152.55:3000 (Frontend) -> "
timeout 3 curl -s -o /dev/null -w "%{http_code}" http://122.116.152.55:3000 || echo "TIMEOUT"
echo ""
echo -n "   122.116.152.55:8000 (Backend) -> "
timeout 3 curl -s -o /dev/null -w "%{http_code}" http://122.116.152.55:8000/health || echo "TIMEOUT"
echo ""
echo ""

echo "5️⃣ 檢查防火牆狀態..."
if command -v ufw &> /dev/null; then
    sudo ufw status | grep -E "(80|3000|8000)" || echo "   ⚠️  未找到相關端口規則"
else
    echo "   ⚠️  UFW 未安裝"
fi
echo ""

echo "================================"
echo "📝 診斷建議："
echo ""
echo "   如果本地連接正常但 IP 連接超時："
echo "   → 執行: ./scripts/open-all-ports.sh"
echo ""
echo "   如果本地連接也失敗："
echo "   → 檢查服務狀態: docker compose ps"
echo "   → 查看日誌: docker compose logs frontend"
echo ""
