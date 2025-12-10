#!/bin/bash

################################################################################
# QuantLab 開發環境快速啟動
# 用途：快速啟動開發環境（僅必要服務）
# 使用：./scripts/dev-quick-start.sh
################################################################################

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   QuantLab 開發環境快速啟動工具         ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""

# 檢查 .env 是否存在
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env 文件不存在${NC}"
    if [ -f ".env.example" ]; then
        echo -e "${GREEN}正在從 .env.example 複製...${NC}"
        cp .env.example .env
        echo -e "${YELLOW}請編輯 .env 文件並添加必要的 API Keys${NC}"
        echo -e "${YELLOW}按 Enter 繼續...${NC}"
        read
    else
        echo -e "${RED}錯誤：.env.example 也不存在！${NC}"
        exit 1
    fi
fi

# 檢查 Docker 是否運行
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}錯誤：Docker 未運行${NC}"
    echo "請啟動 Docker Desktop 或 Docker 服務"
    exit 1
fi

# 停止所有現有容器（避免衝突）
echo -e "${CYAN}[1/5] 停止現有容器...${NC}"
docker compose down > /dev/null 2>&1 || true

# 啟動基礎服務（PostgreSQL, Redis）
echo -e "${CYAN}[2/5] 啟動基礎服務（PostgreSQL, Redis）...${NC}"
docker compose up -d postgres redis

# 等待數據庫就緒
echo -e "${CYAN}[3/5] 等待服務就緒...${NC}"
echo -n "  PostgreSQL: "
for i in {1..30}; do
    if docker compose exec -T postgres pg_isready -U quantlab > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

echo -n "  Redis: "
for i in {1..10}; do
    if docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

# 運行數據庫遷移
echo -e "${CYAN}[4/5] 執行數據庫遷移...${NC}"
docker compose run --rm backend alembic upgrade head

# 啟動開發服務
echo -e "${CYAN}[5/5] 啟動開發服務...${NC}"
echo ""
echo -e "${YELLOW}選擇啟動模式：${NC}"
echo "  1) 完整模式（所有服務）"
echo "  2) 後端模式（僅後端 + Celery）"
echo "  3) 前端模式（僅前端）"
echo "  4) 最小模式（僅基礎服務）"
echo ""
read -p "請選擇 (1-4): " mode

case $mode in
    1)
        echo -e "${GREEN}啟動完整開發環境...${NC}"
        docker compose up -d backend frontend celery-worker celery-beat
        ;;
    2)
        echo -e "${GREEN}啟動後端開發環境...${NC}"
        docker compose up -d backend celery-worker celery-beat
        ;;
    3)
        echo -e "${GREEN}啟動前端開發環境...${NC}"
        docker compose up -d frontend
        ;;
    4)
        echo -e "${GREEN}已啟動基礎服務（PostgreSQL, Redis）${NC}"
        ;;
    *)
        echo -e "${RED}無效的選擇${NC}"
        exit 1
        ;;
esac

# 等待服務啟動
if [ "$mode" != "4" ]; then
    echo ""
    echo -e "${CYAN}等待服務啟動（5 秒）...${NC}"
    sleep 5
fi

# 顯示服務狀態
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           服務狀態                       ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""
docker compose ps

# 顯示訪問信息
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           服務訪問信息                   ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""

if docker compose ps backend | grep -q "Up"; then
    echo -e "  ${GREEN}✓${NC} 後端 API:    ${CYAN}http://localhost:8000${NC}"
    echo -e "  ${GREEN}✓${NC} API 文檔:    ${CYAN}http://localhost:8000/docs${NC}"
    echo -e "  ${GREEN}✓${NC} ReDoc:       ${CYAN}http://localhost:8000/redoc${NC}"
fi

if docker compose ps frontend | grep -q "Up"; then
    echo -e "  ${GREEN}✓${NC} 前端應用:    ${CYAN}http://localhost:3000${NC}"
fi

if docker compose ps postgres | grep -q "Up"; then
    echo -e "  ${GREEN}✓${NC} PostgreSQL:  ${CYAN}localhost:5432${NC}"
fi

if docker compose ps redis | grep -q "Up"; then
    echo -e "  ${GREEN}✓${NC} Redis:       ${CYAN}localhost:6379${NC}"
fi

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           常用指令                       ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "  查看日誌:      docker compose logs -f"
echo "  查看特定服務:  docker compose logs -f backend"
echo "  重啟服務:      docker compose restart backend"
echo "  停止所有:      docker compose down"
echo "  進入後端:      docker compose exec backend bash"
echo "  運行測試:      docker compose exec backend pytest"
echo ""
echo -e "${GREEN}✨ 開發環境已就緒！開始編碼吧！${NC}"
echo ""

# 提供快捷操作選項
echo -e "${YELLOW}需要執行其他操作嗎？${NC}"
echo "  1) 查看實時日誌"
echo "  2) 運行測試"
echo "  3) 進入後端 Shell"
echo "  4) 清理 Qlib 快取"
echo "  5) 退出"
echo ""
read -p "請選擇 (1-5): " action

case $action in
    1)
        echo -e "${CYAN}顯示實時日誌（Ctrl+C 退出）...${NC}"
        docker compose logs -f
        ;;
    2)
        echo -e "${CYAN}運行測試...${NC}"
        docker compose exec backend pytest -v
        ;;
    3)
        echo -e "${CYAN}進入後端 Shell...${NC}"
        docker compose exec backend bash
        ;;
    4)
        echo -e "${CYAN}清理 Qlib 快取...${NC}"
        docker compose exec backend rm -rf /tmp/qlib_cache/*
        echo -e "${GREEN}✓ 快取已清理${NC}"
        ;;
    5)
        echo -e "${GREEN}Bye!${NC}"
        ;;
    *)
        echo -e "${YELLOW}無效的選擇，退出${NC}"
        ;;
esac
