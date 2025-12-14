#!/bin/bash
# 開放 QuantLab 所需的所有端口

echo "🔓 開放 QuantLab 所需端口..."
echo ""

# 開放 HTTP 端口 (80)
echo "📌 開放 80 端口 (HTTP/Nginx)..."
sudo ufw allow 80/tcp

# 開放前端端口 (3000)
echo "📌 開放 3000 端口 (Frontend)..."
sudo ufw allow 3000/tcp

# 開放後端 API 端口 (8000)
echo "📌 開放 8000 端口 (Backend API)..."
sudo ufw allow 8000/tcp

# 開放 Grafana 端口 (3001) - 可選
echo "📌 開放 3001 端口 (Grafana)..."
sudo ufw allow 3001/tcp

# 開放 Prometheus 端口 (9090) - 可選
echo "📌 開放 9090 端口 (Prometheus)..."
sudo ufw allow 9090/tcp

# 重新載入防火牆
echo ""
echo "🔄 重新載入防火牆..."
sudo ufw reload

# 顯示防火牆狀態
echo ""
echo "📊 當前防火牆狀態："
sudo ufw status numbered

echo ""
echo "✅ 完成！現在可以通過以下方式訪問："
echo ""
echo "   主要訪問方式："
echo "   - http://122.116.152.55        (通過 Nginx，推薦)"
echo "   - http://122.116.152.55:3000   (直接訪問前端)"
echo "   - http://122.116.152.55:8000   (後端 API)"
echo ""
echo "   監控系統："
echo "   - http://122.116.152.55:3001   (Grafana)"
echo "   - http://122.116.152.55:9090   (Prometheus)"
echo ""
