#!/bin/bash

################################################################################
# QuantLab 遷移備份腳本
# 用途：將整個系統打包以便遷移到其他機器
# 使用：./scripts/backup-for-migration.sh
################################################################################

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
BACKUP_DIR="quantlab_migration_$(date +%Y%m%d_%H%M%S)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}=== QuantLab 遷移備份工具 ===${NC}"
echo -e "${YELLOW}備份目錄: $BACKUP_DIR${NC}"
echo ""

# 創建備份目錄
mkdir -p "$BACKUP_DIR"

# 1. 備份 PostgreSQL 數據庫
echo -e "${GREEN}[1/6] 備份 PostgreSQL 數據庫...${NC}"
docker compose exec -T postgres pg_dump -U quantlab quantlab | gzip > "$BACKUP_DIR/database.sql.gz"
DB_SIZE=$(du -sh "$BACKUP_DIR/database.sql.gz" | cut -f1)
echo -e "  ✓ 數據庫備份完成 (大小: $DB_SIZE)"

# 2. 備份 Redis 數據
echo -e "${GREEN}[2/6] 備份 Redis 數據...${NC}"
docker compose exec -T redis redis-cli SAVE > /dev/null 2>&1
docker compose cp redis:/data/dump.rdb "$BACKUP_DIR/redis_dump.rdb"
REDIS_SIZE=$(du -sh "$BACKUP_DIR/redis_dump.rdb" | cut -f1)
echo -e "  ✓ Redis 備份完成 (大小: $REDIS_SIZE)"

# 3. 備份 Qlib 數據
echo -e "${GREEN}[3/6] 備份 Qlib 數據...${NC}"
if [ -d "/data/qlib" ]; then
    tar -czf "$BACKUP_DIR/qlib_data.tar.gz" -C /data qlib
    QLIB_SIZE=$(du -sh "$BACKUP_DIR/qlib_data.tar.gz" | cut -f1)
    echo -e "  ✓ Qlib 數據備份完成 (大小: $QLIB_SIZE)"
else
    echo -e "  ${YELLOW}⚠ Qlib 數據目錄不存在，跳過${NC}"
fi

# 4. 備份環境配置文件
echo -e "${GREEN}[4/6] 備份配置文件...${NC}"
cp "$PROJECT_ROOT/.env" "$BACKUP_DIR/.env.backup"
cp "$PROJECT_ROOT/docker-compose.yml" "$BACKUP_DIR/"
cp "$PROJECT_ROOT/.env.example" "$BACKUP_DIR/" 2>/dev/null || true
echo -e "  ✓ 配置文件備份完成"

# 5. 複製代碼（使用 Git）
echo -e "${GREEN}[5/6] 複製項目代碼...${NC}"
cd "$PROJECT_ROOT"
git bundle create "$BACKUP_DIR/quantlab_repo.bundle" --all
GIT_SIZE=$(du -sh "$BACKUP_DIR/quantlab_repo.bundle" | cut -f1)
echo -e "  ✓ Git 倉庫打包完成 (大小: $GIT_SIZE)"

# 記錄當前 Git 狀態
git rev-parse HEAD > "$BACKUP_DIR/git_commit.txt"
git branch --show-current > "$BACKUP_DIR/git_branch.txt"
git status --short > "$BACKUP_DIR/git_status.txt" || true

# 6. 創建遷移說明文件
echo -e "${GREEN}[6/6] 生成遷移說明文件...${NC}"
cat > "$BACKUP_DIR/README_MIGRATION.md" << 'EOF'
# QuantLab 遷移指南

## 📦 備份內容

此備份包含：
- `database.sql.gz` - PostgreSQL 數據庫（壓縮）
- `redis_dump.rdb` - Redis 數據快照
- `qlib_data.tar.gz` - Qlib 量化數據（壓縮）
- `quantlab_repo.bundle` - Git 完整倉庫
- `.env.backup` - 環境變數配置（需檢查敏感信息）
- `docker-compose.yml` - Docker 編排配置

## 🚀 遷移步驟

### 1️⃣ 準備新機器

**系統需求**：
- Ubuntu 20.04+ / CentOS 7+ / macOS
- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB RAM
- 至少 10GB 可用磁碟空間

**安裝 Docker**：
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 安裝 Docker Compose
sudo apt-get install docker-compose-plugin
```

### 2️⃣ 傳輸備份文件

將整個備份目錄傳輸到新機器：

**方法 1：使用 scp**
```bash
scp -r quantlab_migration_* user@new-server:/path/to/destination/
```

**方法 2：使用 rsync**
```bash
rsync -avz --progress quantlab_migration_* user@new-server:/path/to/destination/
```

**方法 3：使用雲端存儲**
```bash
# 打包
tar -czf quantlab_migration.tar.gz quantlab_migration_*/

# 上傳到 Google Drive / Dropbox / AWS S3
# 在新機器下載並解壓
tar -xzf quantlab_migration.tar.gz
```

### 3️⃣ 在新機器上還原

```bash
# 進入備份目錄
cd quantlab_migration_*/

# 1. 還原 Git 倉庫
git clone quantlab_repo.bundle quantlab
cd quantlab

# 2. 切換到原來的分支
BRANCH=$(cat ../git_branch.txt)
git checkout $BRANCH

# 3. 複製環境配置
cp ../.env.backup .env

# 4. ⚠️ 重要：修改 .env 中的敏感信息
nano .env
# 檢查並更新：
# - JWT_SECRET (建議重新生成)
# - FINLAB_API_TOKEN
# - OPENAI_API_KEY (如果有)
# - ALLOWED_ORIGINS (更新為新機器的 IP)

# 5. 創建 Qlib 數據目錄
sudo mkdir -p /data/qlib
sudo tar -xzf ../qlib_data.tar.gz -C /data/
sudo chown -R $USER:$USER /data/qlib

# 6. 啟動 Docker 服務
docker compose up -d postgres redis

# 等待數據庫啟動（約 10 秒）
sleep 10

# 7. 還原 PostgreSQL 數據庫
gunzip < ../database.sql.gz | docker compose exec -T postgres psql -U quantlab quantlab

# 8. 還原 Redis 數據
docker compose cp ../redis_dump.rdb redis:/data/dump.rdb
docker compose restart redis

# 9. 啟動所有服務
docker compose up -d

# 10. 檢查服務狀態
docker compose ps
docker compose logs -f
```

### 4️⃣ 驗證遷移

```bash
# 1. 檢查服務健康狀態
curl http://localhost:8000/health
# 預期: {"status":"healthy","version":"0.1.0"}

# 2. 檢查前端
curl http://localhost:3000
# 預期: 返回 HTML

# 3. 檢查數據庫連接
docker compose exec backend python -c "from app.db.session import SessionLocal; db = SessionLocal(); print(f'Connected: {db.is_active}')"

# 4. 檢查 Celery worker
docker compose exec backend celery -A app.core.celery_app inspect active

# 5. 登入前端測試
# 訪問 http://localhost:3000
# 使用原有帳號登入
# 檢查策略、回測數據是否完整
```

### 5️⃣ 常見問題排查

**問題 1：數據庫連接失敗**
```bash
# 檢查 PostgreSQL 日誌
docker compose logs postgres

# 重置數據庫密碼
docker compose exec postgres psql -U quantlab -c "ALTER USER quantlab PASSWORD 'quantlab2025';"
```

**問題 2：前端無法連接後端**
```bash
# 檢查 .env 中的 NUXT_PUBLIC_API_BASE
# 確保指向正確的後端地址（通常是 http://localhost:8000）
nano .env
# NUXT_PUBLIC_API_BASE=http://localhost:8000

# 重啟前端
docker compose restart frontend
```

**問題 3：Qlib 數據讀取失敗**
```bash
# 檢查 Qlib 數據路徑權限
ls -la /data/qlib/
sudo chown -R $USER:$USER /data/qlib

# 檢查環境變數
docker compose exec backend printenv | grep QLIB
```

**問題 4：CORS 錯誤**
```bash
# 更新 .env 中的 ALLOWED_ORIGINS
nano .env
# ALLOWED_ORIGINS=http://localhost:3000,http://new-server-ip:3000

# 重啟後端
docker compose restart backend
```

## 📊 數據完整性檢查

遷移後執行以下 SQL 查詢確認數據：

```bash
docker compose exec -T postgres psql -U quantlab quantlab << 'SQL'
-- 檢查用戶數
SELECT count(*) as user_count FROM users;

-- 檢查策略數
SELECT count(*) as strategy_count FROM strategies;

-- 檢查回測數
SELECT count(*) as backtest_count FROM backtests;

-- 檢查股票數據
SELECT count(*) as stock_count FROM stock_list;

-- 檢查基本面數據
SELECT count(*) as fundamental_count FROM fundamental_data;

-- 檢查產業分類
SELECT count(*) as industry_count FROM industries;
SQL
```

## 🔐 安全注意事項

1. **立即更換敏感 Key**：
   ```bash
   # 生成新的 JWT_SECRET
   openssl rand -hex 32
   ```

2. **檢查防火牆設定**：
   ```bash
   # 僅允許必要的端口
   sudo ufw allow 3000/tcp  # 前端
   sudo ufw allow 8000/tcp  # 後端（視需求）
   sudo ufw enable
   ```

3. **設定 HTTPS（生產環境）**：
   - 使用 Nginx 反向代理
   - 申請 SSL 證書（Let's Encrypt）

4. **定期備份新機器**：
   ```bash
   # 加入 crontab
   0 2 * * * /path/to/quantlab/scripts/backup-for-migration.sh
   ```

## 📝 回滾計劃

如果遷移失敗，可在原機器上：

1. 保留原有系統不變
2. 檢查新機器日誌找出問題
3. 修復後重新遷移

## 🆘 技術支援

- GitHub Issues: https://github.com/your-repo/quantlab/issues
- 文檔: `/docs` 目錄
- API 文檔: http://localhost:8000/docs

EOF

echo -e "  ✓ 遷移說明文件已生成"

# 生成備份清單
echo -e "${GREEN}生成備份清單...${NC}"
cat > "$BACKUP_DIR/BACKUP_MANIFEST.txt" << EOF
QuantLab 遷移備份清單
備份時間: $(date '+%Y-%m-%d %H:%M:%S')
備份目錄: $BACKUP_DIR

=== 檔案清單 ===
EOF

ls -lh "$BACKUP_DIR" >> "$BACKUP_DIR/BACKUP_MANIFEST.txt"

echo "" >> "$BACKUP_DIR/BACKUP_MANIFEST.txt"
echo "=== Git 資訊 ===" >> "$BACKUP_DIR/BACKUP_MANIFEST.txt"
echo "Commit: $(cat $BACKUP_DIR/git_commit.txt)" >> "$BACKUP_DIR/BACKUP_MANIFEST.txt"
echo "Branch: $(cat $BACKUP_DIR/git_branch.txt)" >> "$BACKUP_DIR/BACKUP_MANIFEST.txt"

# 計算總大小
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

echo ""
echo -e "${GREEN}=== 備份完成 ===${NC}"
echo -e "${BLUE}備份位置: $(pwd)/$BACKUP_DIR${NC}"
echo -e "${BLUE}備份大小: $TOTAL_SIZE${NC}"
echo ""
echo -e "${YELLOW}下一步操作：${NC}"
echo "1. 查看遷移說明: cat $BACKUP_DIR/README_MIGRATION.md"
echo "2. 傳輸到新機器: scp -r $BACKUP_DIR user@new-server:/path/"
echo "3. 在新機器上還原（參考 README_MIGRATION.md）"
echo ""
echo -e "${RED}⚠️  注意：請檢查 .env.backup 中的敏感信息！${NC}"
echo -e "${RED}⚠️  建議在新機器上重新生成 JWT_SECRET${NC}"
