#!/bin/bash

################################################################################
# QuantLab 快速還原腳本
# 用途：在新機器上自動還原備份
# 使用：./scripts/restore-from-backup.sh /path/to/backup/directory
################################################################################

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 檢查參數
if [ -z "$1" ]; then
    echo -e "${RED}錯誤：請提供備份目錄路徑${NC}"
    echo "使用方式: $0 /path/to/backup/directory"
    exit 1
fi

BACKUP_DIR="$1"

# 檢查備份目錄是否存在
if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${RED}錯誤：備份目錄不存在: $BACKUP_DIR${NC}"
    exit 1
fi

echo -e "${BLUE}=== QuantLab 快速還原工具 ===${NC}"
echo -e "${YELLOW}備份目錄: $BACKUP_DIR${NC}"
echo ""

# 檢查必要文件
REQUIRED_FILES=(
    "database.sql.gz"
    "redis_dump.rdb"
    "quantlab_repo.bundle"
    ".env.backup"
    "docker-compose.yml"
)

echo -e "${GREEN}檢查備份文件...${NC}"
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$BACKUP_DIR/$file" ]; then
        echo -e "  ✓ $file"
    else
        echo -e "  ${RED}✗ $file (缺失)${NC}"
        exit 1
    fi
done

# 確認操作
echo ""
echo -e "${YELLOW}⚠️  此操作將：${NC}"
echo "  1. 還原 Git 倉庫到當前目錄"
echo "  2. 還原數據庫（會覆蓋現有數據）"
echo "  3. 還原 Redis 數據"
echo "  4. 還原 Qlib 數據到 /data/qlib"
echo ""
read -p "確定要繼續嗎？(yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "操作已取消"
    exit 0
fi

# 1. 還原 Git 倉庫
echo ""
echo -e "${GREEN}[1/7] 還原 Git 倉庫...${NC}"
if [ ! -d ".git" ]; then
    git clone "$BACKUP_DIR/quantlab_repo.bundle" .

    # 切換到原來的分支
    if [ -f "$BACKUP_DIR/git_branch.txt" ]; then
        BRANCH=$(cat "$BACKUP_DIR/git_branch.txt")
        git checkout "$BRANCH" 2>/dev/null || echo "  ${YELLOW}⚠ 分支 $BRANCH 不存在，使用當前分支${NC}"
    fi
    echo -e "  ✓ Git 倉庫已還原"
else
    echo -e "  ${YELLOW}⚠ .git 目錄已存在，跳過 Git 還原${NC}"
fi

# 2. 複製環境配置
echo -e "${GREEN}[2/7] 複製環境配置...${NC}"
cp "$BACKUP_DIR/.env.backup" .env
cp "$BACKUP_DIR/docker-compose.yml" .
echo -e "  ✓ 配置文件已複製"
echo -e "  ${YELLOW}⚠️  請記得修改 .env 中的敏感信息！${NC}"

# 3. 還原 Qlib 數據
echo -e "${GREEN}[3/7] 還原 Qlib 數據...${NC}"
if [ -f "$BACKUP_DIR/qlib_data.tar.gz" ]; then
    # 檢查是否有 sudo 權限
    if [ -w "/data" ] || sudo -n true 2>/dev/null; then
        sudo mkdir -p /data
        sudo tar -xzf "$BACKUP_DIR/qlib_data.tar.gz" -C /data/
        sudo chown -R $USER:$USER /data/qlib 2>/dev/null || true
        echo -e "  ✓ Qlib 數據已還原到 /data/qlib"
    else
        echo -e "  ${YELLOW}⚠ 需要 sudo 權限來還原 Qlib 數據${NC}"
        echo -e "  ${YELLOW}請手動執行: sudo tar -xzf $BACKUP_DIR/qlib_data.tar.gz -C /data/${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠ Qlib 備份不存在，跳過${NC}"
fi

# 4. 啟動基礎服務
echo -e "${GREEN}[4/7] 啟動 PostgreSQL 和 Redis...${NC}"
docker compose up -d postgres redis
echo -e "  ⏳ 等待服務啟動（15 秒）..."
sleep 15

# 檢查服務狀態
if docker compose ps postgres | grep -q "Up"; then
    echo -e "  ✓ PostgreSQL 已啟動"
else
    echo -e "  ${RED}✗ PostgreSQL 啟動失敗${NC}"
    docker compose logs postgres
    exit 1
fi

if docker compose ps redis | grep -q "Up"; then
    echo -e "  ✓ Redis 已啟動"
else
    echo -e "  ${RED}✗ Redis 啟動失敗${NC}"
    docker compose logs redis
    exit 1
fi

# 5. 還原 PostgreSQL 數據庫
echo -e "${GREEN}[5/7] 還原 PostgreSQL 數據庫...${NC}"
echo -e "  ⏳ 這可能需要幾分鐘..."

# 先刪除並重建數據庫（避免衝突）
docker compose exec -T postgres psql -U quantlab -c "DROP DATABASE IF EXISTS quantlab;" 2>/dev/null || true
docker compose exec -T postgres psql -U quantlab -c "CREATE DATABASE quantlab;" 2>/dev/null || true

# 還原數據
gunzip < "$BACKUP_DIR/database.sql.gz" | docker compose exec -T postgres psql -U quantlab quantlab
echo -e "  ✓ 數據庫已還原"

# 6. 還原 Redis 數據
echo -e "${GREEN}[6/7] 還原 Redis 數據...${NC}"
docker compose cp "$BACKUP_DIR/redis_dump.rdb" redis:/data/dump.rdb
docker compose restart redis
sleep 3
echo -e "  ✓ Redis 數據已還原"

# 7. 啟動所有服務
echo -e "${GREEN}[7/7] 啟動所有服務...${NC}"
docker compose up -d
echo -e "  ⏳ 等待服務啟動（10 秒）..."
sleep 10

# 顯示服務狀態
echo ""
echo -e "${BLUE}=== 服務狀態 ===${NC}"
docker compose ps

# 驗證健康狀態
echo ""
echo -e "${GREEN}=== 驗證服務 ===${NC}"

# 檢查後端健康
echo -n "後端 API: "
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo -e "${GREEN}✓ 正常${NC}"
else
    echo -e "${RED}✗ 異常${NC}"
fi

# 檢查前端
echo -n "前端服務: "
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 正常${NC}"
else
    echo -e "${YELLOW}⏳ 啟動中...${NC}"
fi

# 檢查數據完整性
echo ""
echo -e "${BLUE}=== 數據完整性檢查 ===${NC}"
docker compose exec -T postgres psql -U quantlab quantlab << 'SQL'
SELECT
    (SELECT count(*) FROM users) as 用戶數,
    (SELECT count(*) FROM strategies) as 策略數,
    (SELECT count(*) FROM backtests) as 回測數,
    (SELECT count(*) FROM stock_list) as 股票數,
    (SELECT count(*) FROM industries) as 產業數;
SQL

echo ""
echo -e "${GREEN}=== 還原完成 ===${NC}"
echo ""
echo -e "${YELLOW}下一步操作：${NC}"
echo "1. 修改 .env 中的敏感信息:"
echo "   nano .env"
echo "   - JWT_SECRET (建議重新生成: openssl rand -hex 32)"
echo "   - ALLOWED_ORIGINS (更新為新機器的 IP)"
echo ""
echo "2. 重啟服務以應用新配置:"
echo "   docker compose restart backend frontend"
echo ""
echo "3. 訪問前端測試:"
echo "   http://localhost:3000"
echo ""
echo "4. 查看日誌（如有問題）:"
echo "   docker compose logs -f"
echo ""
echo -e "${RED}⚠️  重要提醒：${NC}"
echo -e "${RED}   - 請立即修改 .env 中的 JWT_SECRET${NC}"
echo -e "${RED}   - 檢查並更新 ALLOWED_ORIGINS${NC}"
echo -e "${RED}   - 驗證所有功能是否正常${NC}"
