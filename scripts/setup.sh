#!/bin/bash

echo "🚀 QuantLab 環境設置腳本"
echo "=============================="

# 檢查 Docker 是否安裝
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安裝，請先安裝 Docker"
    exit 1
fi

# 檢查 Docker Compose V2
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose V2 未安裝，請先安裝 Docker Compose V2"
    exit 1
fi

echo "✅ Docker 和 Docker Compose 已安裝"

# 檢查 .env 文件
if [ ! -f .env ]; then
    echo "📝 建立 .env 文件..."
    cp .env.example .env
    echo "⚠️  請編輯 .env 文件並填入必要的設定"
    echo "   特別是："
    echo "   - DB_PASSWORD"
    echo "   - JWT_SECRET"
    echo "   - FINLAB_API_TOKEN"
    exit 0
fi

echo "✅ .env 文件已存在"

# 啟動服務
echo "🐳 啟動 Docker 容器..."
docker compose up -d

# 等待資料庫啟動
echo "⏳ 等待資料庫啟動..."
sleep 10

# 執行資料庫遷移
echo "🔄 執行資料庫遷移..."
docker compose exec -T backend alembic upgrade head

echo "=============================="
echo "✅ 設置完成！"
echo ""
echo "訪問以下網址："
echo "  前端: http://localhost:3000"
echo "  後端: http://localhost:8000"
echo "  API 文檔: http://localhost:8000/docs"
echo ""
echo "查看日誌: docker compose logs -f"
echo "停止服務: docker compose down"
