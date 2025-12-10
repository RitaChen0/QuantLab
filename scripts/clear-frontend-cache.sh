#!/bin/bash

# QuantLab 前端緩存清理腳本
# 用於清理 Nuxt.js 的各種緩存，解決緩存導致的問題

set -e

echo "🧹 開始清理 QuantLab 前端緩存..."
echo ""

# 顏色定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 切換到專案根目錄
cd "$(dirname "$0")/.."

echo -e "${BLUE}步驟 1/5: 停止前端服務${NC}"
docker compose stop frontend
echo -e "${GREEN}✅ 前端服務已停止${NC}"
echo ""

echo -e "${BLUE}步驟 2/5: 清理本地緩存目錄${NC}"
cd frontend
rm -rf .nuxt .output node_modules/.vite node_modules/.cache
echo -e "${GREEN}✅ 本地緩存已清理${NC}"
echo "   - .nuxt/"
echo "   - .output/"
echo "   - node_modules/.vite/"
echo "   - node_modules/.cache/"
echo ""

echo -e "${BLUE}步驟 3/5: 清理 Docker 容器內緩存${NC}"
cd ..
docker compose run --rm frontend sh -c "rm -rf .nuxt .output node_modules/.vite node_modules/.cache" 2>/dev/null || true
echo -e "${GREEN}✅ 容器內緩存已清理${NC}"
echo ""

echo -e "${BLUE}步驟 4/5: 清理 Docker 構建緩存（可選）${NC}"
read -p "是否清理 Docker 構建緩存？這會增加下次構建時間 (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    docker builder prune -f
    echo -e "${GREEN}✅ Docker 構建緩存已清理${NC}"
else
    echo -e "${YELLOW}⏭️  跳過 Docker 構建緩存清理${NC}"
fi
echo ""

echo -e "${BLUE}步驟 5/5: 重啟前端服務${NC}"
docker compose up -d frontend
echo -e "${GREEN}✅ 前端服務已重啟${NC}"
echo ""

echo "⏳ 等待服務啟動..."
sleep 10

# 檢查服務狀態
if docker compose ps frontend | grep -q "Up"; then
    echo -e "${GREEN}✅ 前端服務運行正常${NC}"
    echo ""
    echo "🎉 緩存清理完成！"
    echo ""
    echo "📝 訪問以下 URL 驗證："
    echo "   - http://localhost:3000/"
    echo "   - http://localhost:3000/strategies"
    echo ""
    echo "💡 如果仍有問題，請執行完整重建："
    echo "   docker compose down"
    echo "   docker compose build --no-cache frontend"
    echo "   docker compose up -d"
else
    echo -e "${YELLOW}⚠️  前端服務啟動異常，請檢查日誌：${NC}"
    echo "   docker compose logs frontend --tail 50"
fi
