#!/bin/bash
# 開放 80 端口用於 HTTP 訪問

echo "🔓 開放防火牆 80 端口..."

# 開放 80 端口
sudo ufw allow 80/tcp

# 重新載入防火牆
sudo ufw reload

# 顯示防火牆狀態
echo ""
echo "📊 當前防火牆狀態："
sudo ufw status | grep -E "(80|3000|8000)"

echo ""
echo "✅ 完成！現在可以通過以下方式訪問："
echo "   - http://122.116.152.55 (通過 Nginx)"
echo "   - http://122.116.152.55:3000 (直接訪問前端)"
echo "   - http://122.116.152.55:8000 (直接訪問後端 API)"
