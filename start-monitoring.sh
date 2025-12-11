#!/bin/bash
# QuantLab 監控系統啟動腳本
# 快速啟動 Prometheus + Grafana + Celery Exporter

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   QuantLab 監控系統啟動${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# 檢查 docker-compose 是否可用
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 未安裝，請先安裝 Docker${NC}"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose 未安裝，請先安裝 Docker Compose${NC}"
    exit 1
fi

# 檢查配置文件是否存在
if [ ! -f "monitoring/prometheus.yml" ]; then
    echo -e "${RED}❌ Prometheus 配置文件不存在: monitoring/prometheus.yml${NC}"
    exit 1
fi

if [ ! -d "monitoring/grafana/provisioning" ]; then
    echo -e "${RED}❌ Grafana provisioning 目錄不存在: monitoring/grafana/provisioning${NC}"
    exit 1
fi

# 詢問是否要啟動所有服務還是只啟動監控服務
echo -e "${YELLOW}選擇啟動模式:${NC}"
echo "  1) 啟動所有服務（包含 backend, frontend, 監控）"
echo "  2) 只啟動監控服務（prometheus, grafana, celery-exporter）"
echo "  3) 取消"
echo
read -p "請選擇 [1-3]: " choice

case $choice in
    1)
        echo
        echo -e "${BLUE}🚀 啟動所有服務...${NC}"
        docker compose up -d
        ;;
    2)
        echo
        echo -e "${BLUE}🚀 啟動監控服務...${NC}"
        docker compose up -d prometheus grafana celery-exporter
        ;;
    3)
        echo -e "${YELLOW}❌ 已取消${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}無效選擇${NC}"
        exit 1
        ;;
esac

# 等待服務啟動
echo
echo -e "${YELLOW}⏳ 等待服務啟動（10 秒）...${NC}"
sleep 10

# 檢查服務狀態
echo
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   服務狀態檢查${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# 檢查 Prometheus
if docker compose ps prometheus | grep -q "Up"; then
    echo -e "${GREEN}✅ Prometheus: 運行中${NC}"
    echo -e "   📊 URL: http://localhost:9090"
else
    echo -e "${RED}❌ Prometheus: 未運行${NC}"
fi

# 檢查 Grafana
if docker compose ps grafana | grep -q "Up"; then
    echo -e "${GREEN}✅ Grafana: 運行中${NC}"
    echo -e "   📈 URL: http://localhost:3001"
    echo -e "   👤 預設帳號: admin / admin123"
else
    echo -e "${RED}❌ Grafana: 未運行${NC}"
fi

# 檢查 Celery Exporter
if docker compose ps celery-exporter | grep -q "Up"; then
    echo -e "${GREEN}✅ Celery Exporter: 運行中${NC}"
    echo -e "   📡 Metrics: http://localhost:9808/metrics"
else
    echo -e "${RED}❌ Celery Exporter: 未運行${NC}"
fi

# 如果選擇啟動所有服務，檢查其他服務
if [ "$choice" == "1" ]; then
    echo

    if docker compose ps backend | grep -q "Up"; then
        echo -e "${GREEN}✅ Backend: 運行中${NC}"
        echo -e "   🔧 API: http://localhost:8000"
        echo -e "   📊 Metrics: http://localhost:8000/metrics"
    else
        echo -e "${RED}❌ Backend: 未運行${NC}"
    fi

    if docker compose ps frontend | grep -q "Up"; then
        echo -e "${GREEN}✅ Frontend: 運行中${NC}"
        echo -e "   🌐 URL: http://localhost:3000"
    else
        echo -e "${RED}❌ Frontend: 未運行${NC}"
    fi

    if docker compose ps celery-worker | grep -q "Up"; then
        echo -e "${GREEN}✅ Celery Worker: 運行中${NC}"
    else
        echo -e "${RED}❌ Celery Worker: 未運行${NC}"
    fi
fi

echo
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   啟動完成${NC}"
echo -e "${BLUE}========================================${NC}"
echo
echo -e "${GREEN}✅ 監控系統已啟動${NC}"
echo
echo -e "${YELLOW}📚 快速導航:${NC}"
echo "  • Grafana Dashboard: http://localhost:3001"
echo "  • Prometheus: http://localhost:9090"
echo "  • Backend Metrics: http://localhost:8000/metrics"
echo "  • Celery Metrics: http://localhost:9808/metrics"
echo
echo -e "${YELLOW}📖 查看日誌:${NC}"
echo "  docker compose logs -f prometheus"
echo "  docker compose logs -f grafana"
echo "  docker compose logs -f celery-exporter"
echo
echo -e "${YELLOW}🛑 停止監控服務:${NC}"
echo "  docker compose stop prometheus grafana celery-exporter"
echo
