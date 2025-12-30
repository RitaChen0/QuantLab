# QuantLab 系統遷移指南

**文檔版本**: 1.0
**生成日期**: 2025-12-30
**當前系統**: Ubuntu Linux (122.116.152.55)
**遷移類型**: 完整系統遷移（代碼 + 資料庫 + 數據文件）

---

## 📋 目錄

1. [系統概覽](#系統概覽)
2. [遷移前準備](#遷移前準備)
3. [備份步驟](#備份步驟)
4. [新機器環境準備](#新機器環境準備)
5. [還原步驟](#還原步驟)
6. [驗證步驟](#驗證步驟)
7. [故障排除](#故障排除)
8. [回滾計劃](#回滾計劃)

---

## 系統概覽

### 當前系統配置

**容器架構**（12 個容器）:
```
quantlab-backend                 - FastAPI 後端服務
quantlab-frontend                - Nuxt.js 前端服務
quantlab-postgres                - TimescaleDB 資料庫
quantlab-redis                   - Redis 快取/訊息佇列
quantlab-celery-worker           - Celery 異步任務執行器
quantlab-celery-beat             - Celery 定時任務調度器
quantlab-celery-evaluation-worker - Celery 因子評估專用 Worker
quantlab-celery-exporter         - Celery Prometheus 指標導出器
quantlab-telegram-bot            - Telegram Bot 服務
quantlab-nginx                   - Nginx 反向代理
quantlab-prometheus              - Prometheus 監控
quantlab-grafana                 - Grafana 儀表板
```

**資料規模**:
- **資料庫大小**: 2.5 GB（PostgreSQL + TimescaleDB）
- **Qlib 數據**: 24 GB（股票歷史數據）
- **Docker Volumes**: 6 個持久化卷
- **總磁碟使用**: ~82 GB

**網路配置**:
- **HTTP 端口**: 80（Nginx）
- **HTTPS 端口**: 443（Nginx）
- **PostgreSQL**: 5432（對外開放）
- **Redis**: 6379（對外開放）
- **Prometheus**: 9090
- **Grafana**: 3001
- **Celery Exporter**: 9808

---

## 遷移前準備

### 1. 評估新機器需求

**最低硬體需求**:
- **CPU**: 4 核心（建議 8 核心）
- **記憶體**: 16 GB RAM（建議 32 GB）
- **磁碟空間**: 120 GB 可用空間（建議 250 GB）
- **網路**: 穩定的網際網路連線

**作業系統**:
- Ubuntu 20.04 LTS 或更新版本（推薦 22.04 LTS）
- Debian 11+ 或其他相容的 Linux 發行版

**軟體需求**:
- Docker Engine 24.0+
- Docker Compose V2 (2.20+)
- Git 2.25+
- rsync（用於數據傳輸）

### 2. 檢查清單

**遷移前確認**:
- [ ] 新機器已準備好並可透過 SSH 訪問
- [ ] 新機器有足夠的磁碟空間（至少 120 GB）
- [ ] 新機器已安裝 Docker 和 Docker Compose
- [ ] 確認沒有正在執行的重要任務（回測、RD-Agent）
- [ ] 通知所有用戶即將進行維護（建議停機時間：2-4 小時）
- [ ] 準備好備份儲存位置（外部硬碟或雲端儲存）

**時間規劃**:
- **備份時間**: 1-2 小時（取決於網路速度）
- **傳輸時間**: 1-3 小時（取決於網路速度）
- **還原時間**: 30-60 分鐘
- **驗證時間**: 30 分鐘
- **總計**: 3-6.5 小時

---

## 備份步驟

### 步驟 1：停止所有服務（保持資料一致性）

```bash
cd /home/ubuntu/QuantLab

# 停止所有容器（保留數據）
docker compose stop

# 驗證所有容器已停止
docker compose ps
```

**預期輸出**: 所有容器狀態為 `Exited` 或 `Created`

### 步驟 2：備份 Git 倉庫（代碼）

```bash
# 方案 A：直接壓縮整個專案目錄（推薦）
cd /home/ubuntu
tar -czf quantlab_code_$(date +%Y%m%d).tar.gz QuantLab/

# 方案 B：使用 Git bundle（僅程式碼，不含 node_modules 等）
cd /home/ubuntu/QuantLab
git bundle create /tmp/quantlab_repo_$(date +%Y%m%d).bundle --all
```

**推薦**: 使用方案 A（包含所有配置和依賴）

**檔案大小**: 約 500 MB - 2 GB（取決於 node_modules 是否包含）

### 步驟 3：備份環境變數

```bash
# 備份 .env 檔案（包含敏感資訊）
cd /home/ubuntu/QuantLab
cp .env /tmp/quantlab_env_$(date +%Y%m%d).backup

# 備份 docker-compose.yml（以防自訂修改）
cp docker-compose.yml /tmp/quantlab_compose_$(date +%Y%m%d).backup
```

**重要**: `.env` 包含資料庫密碼、API 金鑰等敏感資訊，請妥善保管！

### 步驟 4：備份 Docker Volumes（資料庫和快取）

**方案 A：直接備份 Volume 目錄（快速）**

```bash
# 找到 Docker Volume 實際位置
docker volume inspect quantlab_postgres_data --format '{{ .Mountpoint }}'
# 通常位於 /var/lib/docker/volumes/quantlab_postgres_data/_data

# 備份所有 Volumes（需 root 權限）
sudo tar -czf /tmp/quantlab_volumes_$(date +%Y%m%d).tar.gz \
  /var/lib/docker/volumes/quantlab_postgres_data \
  /var/lib/docker/volumes/quantlab_redis_data \
  /var/lib/docker/volumes/quantlab_grafana_data \
  /var/lib/docker/volumes/quantlab_prometheus_data \
  /var/lib/docker/volumes/quantlab_celerybeat_schedule \
  /var/lib/docker/volumes/quantlab_backend_cache

# 修改權限（讓非 root 用戶可讀取）
sudo chown ubuntu:ubuntu /tmp/quantlab_volumes_$(date +%Y%m%d).tar.gz
```

**方案 B：使用 Docker 官方備份方法（推薦）**

```bash
# 備份 PostgreSQL 資料庫
docker compose up -d postgres  # 暫時啟動資料庫
docker compose exec postgres pg_dump -U quantlab quantlab > /tmp/quantlab_db_$(date +%Y%m%d).sql
docker compose stop postgres

# 備份 Grafana 配置
docker run --rm \
  -v quantlab_grafana_data:/data \
  -v /tmp:/backup \
  alpine tar -czf /backup/quantlab_grafana_$(date +%Y%m%d).tar.gz /data

# 備份 Prometheus 數據（可選，可重新收集）
docker run --rm \
  -v quantlab_prometheus_data:/data \
  -v /tmp:/backup \
  alpine tar -czf /backup/quantlab_prometheus_$(date +%Y%m%d).tar.gz /data

# 備份 Redis 數據（可選，快取數據可重建）
docker compose up -d redis
docker compose exec redis redis-cli SAVE
docker run --rm \
  -v quantlab_redis_data:/data \
  -v /tmp:/backup \
  alpine tar -czf /backup/quantlab_redis_$(date +%Y%m%d).tar.gz /data
docker compose stop redis
```

**推薦**:
- **必須備份**: PostgreSQL（方案 B 的 pg_dump）
- **建議備份**: Grafana、Prometheus
- **可選備份**: Redis（快取數據，可重建）

**檔案大小**:
- PostgreSQL dump: ~2.5 GB
- Grafana: ~50 MB
- Prometheus: ~500 MB - 2 GB（取決於監控歷史長度）
- Redis: ~50 MB - 200 MB

### 步驟 5：備份 Qlib 數據文件

```bash
# Qlib 日線數據（tw_stock_v2）
cd /data/qlib
tar -czf /tmp/quantlab_qlib_daily_$(date +%Y%m%d).tar.gz tw_stock_v2/

# Qlib 分鐘線數據（tw_stock_minute）
tar -czf /tmp/quantlab_qlib_minute_$(date +%Y%m%d).tar.gz tw_stock_minute/

# 或者一次打包所有 Qlib 數據
tar -czf /tmp/quantlab_qlib_all_$(date +%Y%m%d).tar.gz /data/qlib/
```

**重要**:
- 日線數據: ~2-5 GB
- 分鐘線數據: ~18-20 GB
- **總計**: ~24 GB

**壓縮時間**: 約 30-60 分鐘（取決於 CPU 性能）

**替代方案（如果壓縮太慢）**:
```bash
# 直接使用 rsync 傳輸（更快，但需要兩台機器互通）
rsync -avz --progress /data/qlib/ user@new-server:/data/qlib/
```

### 步驟 6：備份 Nginx 配置（如有自訂）

```bash
cd /home/ubuntu/QuantLab
tar -czf /tmp/quantlab_nginx_$(date +%Y%m%d).tar.gz nginx/
```

### 步驟 7：彙總所有備份檔案

```bash
# 列出所有備份檔案
ls -lh /tmp/quantlab_*

# 建議的檔案清單：
# quantlab_code_YYYYMMDD.tar.gz          (~1-2 GB)
# quantlab_env_YYYYMMDD.backup           (~5 KB)
# quantlab_db_YYYYMMDD.sql               (~2.5 GB)
# quantlab_qlib_all_YYYYMMDD.tar.gz      (~24 GB)
# quantlab_grafana_YYYYMMDD.tar.gz       (~50 MB)
# quantlab_prometheus_YYYYMMDD.tar.gz    (~500 MB)
# quantlab_nginx_YYYYMMDD.tar.gz         (~10 KB)

# 總大小：約 28-30 GB

# 打包成單一檔案（可選）
cd /tmp
tar -czf quantlab_full_backup_$(date +%Y%m%d).tar.gz quantlab_*

# 或生成 MD5 校驗和（驗證傳輸完整性）
md5sum quantlab_* > quantlab_backup_$(date +%Y%m%d).md5
```

### 步驟 8：傳輸備份到安全位置

**方案 A：傳輸到新機器**
```bash
# 使用 rsync（推薦，可斷點續傳）
rsync -avz --progress /tmp/quantlab_* user@new-server:/tmp/

# 或使用 scp
scp /tmp/quantlab_* user@new-server:/tmp/
```

**方案 B：上傳到雲端儲存**
```bash
# AWS S3
aws s3 cp /tmp/quantlab_full_backup_$(date +%Y%m%d).tar.gz s3://your-bucket/backups/

# Google Cloud Storage
gsutil cp /tmp/quantlab_full_backup_$(date +%Y%m%d).tar.gz gs://your-bucket/backups/

# 或使用 rclone（支援多種雲端）
rclone copy /tmp/quantlab_* remote:backups/
```

**方案 C：本地外接硬碟**
```bash
# 掛載外接硬碟（假設為 /dev/sdb1）
sudo mount /dev/sdb1 /mnt/backup
cp /tmp/quantlab_* /mnt/backup/
sudo umount /mnt/backup
```

---

## 新機器環境準備

### 步驟 1：安裝 Docker 和 Docker Compose

**Ubuntu/Debian**:
```bash
# 更新套件列表
sudo apt-get update

# 安裝依賴
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 新增 Docker 官方 GPG 金鑰
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 設定 Docker APT 倉庫
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安裝 Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 啟動 Docker 服務
sudo systemctl start docker
sudo systemctl enable docker

# 將當前用戶加入 docker 群組（避免每次使用 sudo）
sudo usermod -aG docker $USER

# 登出並重新登入以套用群組變更
# 或執行：newgrp docker

# 驗證安裝
docker --version
docker compose version
```

**預期輸出**:
```
Docker version 24.0.7, build afdd53b
Docker Compose version v2.23.3
```

### 步驟 2：安裝其他必要工具

```bash
sudo apt-get install -y \
    git \
    rsync \
    vim \
    htop \
    net-tools \
    curl \
    wget
```

### 步驟 3：準備數據目錄

```bash
# 創建 Qlib 數據目錄
sudo mkdir -p /data/qlib
sudo chown -R $USER:$USER /data/qlib

# 創建備份還原目錄
mkdir -p /tmp/quantlab_restore
```

### 步驟 4：配置防火牆（如需要）

```bash
# 使用 ufw（Ubuntu 預設防火牆）
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS

# 如果需要外部訪問資料庫（不推薦生產環境）
sudo ufw allow 5432/tcp  # PostgreSQL
sudo ufw allow 6379/tcp  # Redis

# 啟用防火牆
sudo ufw enable

# 檢查狀態
sudo ufw status
```

### 步驟 5：配置 SSH（可選，提升安全性）

```bash
# 生成新的 SSH 金鑰對（如果還沒有）
ssh-keygen -t ed25519 -C "quantlab@new-server"

# 將公鑰複製到 authorized_keys
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys

# 設定 SSH 配置（禁用密碼登入，僅允許金鑰）
sudo vim /etc/ssh/sshd_config
# 設定：
# PasswordAuthentication no
# PubkeyAuthentication yes

# 重啟 SSH 服務
sudo systemctl restart sshd
```

---

## 還原步驟

### 步驟 1：還原程式碼

```bash
# 方案 A：從壓縮檔還原（推薦）
cd /home/ubuntu
tar -xzf /tmp/quantlab_code_YYYYMMDD.tar.gz

# 方案 B：從 Git bundle 還原
cd /home/ubuntu
git clone /tmp/quantlab_repo_YYYYMMDD.bundle QuantLab
cd QuantLab
git checkout master  # 或您使用的主分支名稱
```

### 步驟 2：還原環境變數

```bash
cd /home/ubuntu/QuantLab
cp /tmp/quantlab_env_YYYYMMDD.backup .env

# 重要：檢查並更新以下變數（如果新機器 IP 或主機名不同）
vim .env

# 需要檢查的變數：
# - DB_HOST (如果使用外部資料庫)
# - REDIS_HOST (如果使用外部 Redis)
# - NUXT_PUBLIC_API_BASE (前端 API 端點)
# - ALLOWED_HOSTS (如果有設定)
```

**關鍵環境變數檢查**:
```bash
# 如果新機器 IP 為 192.168.1.100，需要更新：
# NUXT_PUBLIC_API_BASE=http://192.168.1.100:8000
# 或使用域名：NUXT_PUBLIC_API_BASE=http://quantlab.yourdomain.com
```

### 步驟 3：還原 Qlib 數據

```bash
# 解壓縮 Qlib 數據到 /data/qlib
cd /data/qlib
tar -xzf /tmp/quantlab_qlib_all_YYYYMMDD.tar.gz --strip-components=2

# 或分別解壓縮
tar -xzf /tmp/quantlab_qlib_daily_YYYYMMDD.tar.gz
tar -xzf /tmp/quantlab_qlib_minute_YYYYMMDD.tar.gz

# 驗證數據完整性
ls -lh /data/qlib/tw_stock_v2/
ls -lh /data/qlib/tw_stock_minute/

# 預期看到：
# tw_stock_v2/features/     - 日線數據
# tw_stock_v2/calendars/    - 交易日曆
# tw_stock_minute/features/ - 分鐘線數據
```

**解壓縮時間**: 約 15-30 分鐘（24 GB 數據）

### 步驟 4：建立 Docker Volumes

```bash
cd /home/ubuntu/QuantLab

# Docker Compose 會自動創建 volumes，但我們需要先創建空的
docker volume create quantlab_postgres_data
docker volume create quantlab_redis_data
docker volume create quantlab_grafana_data
docker volume create quantlab_prometheus_data
docker volume create quantlab_celerybeat_schedule
docker volume create quantlab_backend_cache

# 驗證 volumes 已創建
docker volume ls | grep quantlab
```

### 步驟 5：還原資料庫

**方案 A：從 SQL dump 還原（推薦）**

```bash
cd /home/ubuntu/QuantLab

# 啟動 PostgreSQL 容器
docker compose up -d postgres

# 等待資料庫初始化（約 30 秒）
sleep 30

# 檢查資料庫是否已啟動
docker compose exec postgres pg_isready -U quantlab

# 還原資料庫
docker compose exec -T postgres psql -U quantlab quantlab < /tmp/quantlab_db_YYYYMMDD.sql

# 或從外部檔案還原
cat /tmp/quantlab_db_YYYYMMDD.sql | docker compose exec -T postgres psql -U quantlab quantlab
```

**預期輸出**: 大量的 `CREATE TABLE`, `INSERT`, `ALTER TABLE` 等 SQL 語句執行日誌

**還原時間**: 約 10-30 分鐘（取決於資料庫大小）

**驗證資料庫還原**:
```bash
# 檢查表數量
docker compose exec postgres psql -U quantlab quantlab -c "\dt" | wc -l

# 檢查用戶數量
docker compose exec postgres psql -U quantlab quantlab -c "SELECT COUNT(*) FROM users;"

# 檢查股票數據
docker compose exec postgres psql -U quantlab quantlab -c "SELECT COUNT(*) FROM stocks;"
docker compose exec postgres psql -U quantlab quantlab -c "SELECT COUNT(*) FROM stock_prices;"
```

**方案 B：從 Volume 備份還原（如果使用方案 A 失敗）**

```bash
# 停止 PostgreSQL
docker compose stop postgres

# 還原 Volume 數據
docker run --rm \
  -v quantlab_postgres_data:/data \
  -v /tmp:/backup \
  alpine sh -c "cd /data && tar -xzf /backup/quantlab_volumes_YYYYMMDD.tar.gz --strip-components=5"

# 重啟 PostgreSQL
docker compose up -d postgres
```

### 步驟 6：還原其他服務數據

**Grafana**:
```bash
docker run --rm \
  -v quantlab_grafana_data:/data \
  -v /tmp:/backup \
  alpine sh -c "cd / && tar -xzf /backup/quantlab_grafana_YYYYMMDD.tar.gz"
```

**Prometheus** (可選):
```bash
docker run --rm \
  -v quantlab_prometheus_data:/data \
  -v /tmp:/backup \
  alpine sh -c "cd / && tar -xzf /backup/quantlab_prometheus_YYYYMMDD.tar.gz"
```

**Redis** (可選，快取數據可重建):
```bash
docker run --rm \
  -v quantlab_redis_data:/data \
  -v /tmp:/backup \
  alpine sh -c "cd / && tar -xzf /backup/quantlab_redis_YYYYMMDD.tar.gz"
```

### 步驟 7：構建 Docker 映像

```bash
cd /home/ubuntu/QuantLab

# 構建所有服務映像
docker compose build

# 或分別構建（更快，可並行）
docker compose build backend &
docker compose build frontend &
docker compose build telegram-bot &
wait

# 驗證映像已構建
docker images | grep quantlab
```

**構建時間**: 約 10-20 分鐘（首次構建，後續會快很多）

### 步驟 8：啟動所有服務

```bash
cd /home/ubuntu/QuantLab

# 啟動所有服務
docker compose up -d

# 檢查容器狀態
docker compose ps

# 查看日誌（確認無錯誤）
docker compose logs -f --tail 100
```

**預期輸出**: 所有 12 個容器狀態為 `Up` 或 `Up (healthy)`

**啟動順序**（自動處理，無需手動干預）:
1. postgres, redis（基礎服務）
2. backend（依賴資料庫）
3. frontend, celery-worker, celery-beat, telegram-bot（依賴後端）
4. nginx（反向代理）
5. prometheus, grafana, celery-exporter（監控服務）

### 步驟 9：執行資料庫遷移（如有需要）

```bash
# 檢查當前資料庫版本
docker compose exec backend alembic current

# 升級到最新版本（如果有新的遷移）
docker compose exec backend alembic upgrade head

# 如果遷移失敗，可能需要手動修復
# 查看遷移歷史
docker compose exec backend alembic history
```

---

## 驗證步驟

### 1. 檢查容器健康狀態

```bash
# 所有容器應為 Up 或 Up (healthy)
docker compose ps

# 檢查各容器的詳細健康狀態
docker compose exec backend curl -f http://localhost:8000/api/v1/health || echo "Backend unhealthy"
docker compose exec postgres pg_isready -U quantlab || echo "PostgreSQL unhealthy"
docker compose exec redis redis-cli ping || echo "Redis unhealthy"
```

**預期輸出**:
```json
// Backend health check
{"status":"healthy","database":"connected","redis":"connected"}

// PostgreSQL
/var/run/postgresql:5432 - accepting connections

// Redis
PONG
```

### 2. 驗證資料庫連線

```bash
# 檢查資料庫表
docker compose exec postgres psql -U quantlab quantlab -c "\dt" | head -20

# 檢查關鍵資料
docker compose exec postgres psql -U quantlab quantlab -c "
SELECT
    (SELECT COUNT(*) FROM users) as users_count,
    (SELECT COUNT(*) FROM stocks) as stocks_count,
    (SELECT COUNT(*) FROM stock_prices) as daily_prices_count,
    (SELECT COUNT(*) FROM stock_minute_prices) as minute_prices_count,
    (SELECT COUNT(*) FROM strategies) as strategies_count,
    (SELECT COUNT(*) FROM backtests) as backtests_count;
"
```

**預期輸出**: 應與舊機器的數量一致

### 3. 驗證 Qlib 數據

```bash
# 測試 Qlib 數據讀取
docker compose exec backend python -c "
import qlib
from qlib.data import D

qlib.init(provider_uri='/data/qlib/tw_stock_v2', region='tw')

# 讀取台積電收盤價
data = D.features(['2330'], ['$close'], start_time='2024-01-01', end_time='2024-12-31')
print('Qlib 日線數據測試:')
print(data.head())
print(f'總共 {len(data)} 筆數據')
"

# 測試分鐘線數據
docker compose exec backend python -c "
import qlib
from qlib.data import D

qlib.init(provider_uri='/data/qlib/tw_stock_minute', region='tw')

data = D.features(['2330'], ['$close'], start_time='2024-12-01', end_time='2024-12-31', freq='1min')
print('Qlib 分鐘線數據測試:')
print(data.head())
print(f'總共 {len(data)} 筆數據')
"
```

**預期輸出**: 應顯示台積電的價格數據，無錯誤

### 4. 測試前端訪問

```bash
# 方案 A：從瀏覽器訪問（推薦）
# 開啟瀏覽器訪問：http://新機器IP

# 方案 B：使用 curl 測試
curl -I http://localhost/

# 預期輸出：HTTP/1.1 200 OK
```

**測試項目**:
- [ ] 登入頁面可正常顯示
- [ ] 可使用現有帳號登入
- [ ] 儀表板數據正確顯示
- [ ] 策略列表顯示正確
- [ ] 回測列表顯示正確

### 5. 測試 API 端點

```bash
# 健康檢查
curl http://localhost/api/v1/health

# 登入測試（使用現有帳號）
curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'

# 股票列表測試
curl http://localhost/api/v1/stocks/ | head -20
```

### 6. 測試 Celery 任務

```bash
# 檢查 Celery workers 狀態
docker compose exec backend celery -A app.core.celery_app inspect active

# 檢查 Celery Beat 排程
docker compose exec backend celery -A app.core.celery_app inspect scheduled

# 測試手動觸發任務
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_stock_list

# 查看 Celery 日誌
docker compose logs celery-worker --tail 50
```

### 7. 測試 Telegram Bot（如有使用）

```bash
# 檢查 Telegram Bot 狀態
docker compose logs telegram-bot --tail 50

# 從 Telegram 發送 /start 命令測試
```

### 8. 檢查監控服務

**Prometheus**:
```bash
# 訪問 Prometheus UI
curl http://localhost:9090/

# 或從瀏覽器訪問：http://新機器IP:9090
```

**Grafana**:
```bash
# 訪問 Grafana UI（預設帳號：admin/admin）
curl http://localhost:3001/

# 或從瀏覽器訪問：http://新機器IP:3001
```

**測試項目**:
- [ ] Prometheus 可訪問，顯示指標
- [ ] Grafana 可登入，儀表板正確顯示
- [ ] Celery Exporter 指標正常（http://localhost:9808/metrics）

### 9. 效能測試

```bash
# 測試資料庫查詢效能
docker compose exec postgres psql -U quantlab quantlab -c "
EXPLAIN ANALYZE
SELECT * FROM stock_prices WHERE stock_id = '2330' ORDER BY date DESC LIMIT 100;
"

# 測試 API 回應時間
time curl -s http://localhost/api/v1/stocks/ > /dev/null

# 測試 Qlib 數據讀取效能
time docker compose exec backend python -c "
import qlib
from qlib.data import D
qlib.init(provider_uri='/data/qlib/tw_stock_v2', region='tw')
data = D.features(['2330'], ['$close'], start_time='2020-01-01', end_time='2024-12-31')
print(f'讀取 {len(data)} 筆數據')
"
```

**預期效能**（參考值）:
- 股票列表 API: < 500ms
- Qlib 讀取 5 年日線數據: < 2 秒
- 資料庫單表查詢: < 100ms

### 10. 完整性檢查清單

**資料完整性**:
- [ ] 用戶數量與舊系統一致
- [ ] 股票數量與舊系統一致
- [ ] 歷史價格數據與舊系統一致
- [ ] 策略和回測記錄與舊系統一致
- [ ] Qlib 數據完整（日線 + 分鐘線）

**功能完整性**:
- [ ] 登入/註冊功能正常
- [ ] 策略建立/編輯功能正常
- [ ] 回測執行功能正常
- [ ] 數據查詢功能正常
- [ ] Telegram 通知功能正常
- [ ] RD-Agent 功能正常（如有使用）

**系統健康**:
- [ ] 所有容器運行正常
- [ ] 資料庫連線穩定
- [ ] Redis 快取正常
- [ ] Celery 任務執行正常
- [ ] 監控服務正常

---

## 故障排除

### 問題 1：容器無法啟動

**症狀**: `docker compose up -d` 後某些容器狀態為 `Exited` 或 `Restarting`

**診斷**:
```bash
# 查看容器日誌
docker compose logs <service-name> --tail 100

# 常見服務名稱：backend, postgres, redis, frontend
```

**常見原因與解決方案**:

**1.1 PostgreSQL 無法啟動**
```bash
# 錯誤訊息：FATAL: database files are incompatible with server
# 原因：PostgreSQL 版本不一致

# 解決方案：
# 方案 A：使用相同版本的 PostgreSQL
# 檢查舊機器版本
docker compose exec postgres psql -V
# 修改 docker-compose.yml 使用相同版本

# 方案 B：升級資料庫（需要 pg_upgrade）
# 參考：https://www.postgresql.org/docs/current/pgupgrade.html
```

**1.2 Backend 無法連接資料庫**
```bash
# 錯誤訊息：could not connect to server: Connection refused

# 解決方案：
# 確認 PostgreSQL 已啟動並健康
docker compose exec postgres pg_isready -U quantlab

# 檢查 .env 中的資料庫連線設定
grep DATABASE_URL .env

# 重啟 backend
docker compose restart backend
```

**1.3 端口衝突**
```bash
# 錯誤訊息：Bind for 0.0.0.0:80 failed: port is already allocated

# 解決方案：
# 查看占用端口的程序
sudo lsof -i :80
sudo lsof -i :5432

# 停止衝突的服務
sudo systemctl stop apache2  # 或其他 web 服務
sudo systemctl stop postgresql  # 如果有本機 PostgreSQL

# 或修改 docker-compose.yml 使用不同端口
# ports:
#   - "8080:80"  # 將 80 改為 8080
```

### 問題 2：資料庫還原失敗

**症狀**: SQL dump 導入時出現錯誤

**診斷**:
```bash
# 嘗試還原並捕獲錯誤
docker compose exec -T postgres psql -U quantlab quantlab < /tmp/quantlab_db_YYYYMMDD.sql 2>&1 | tee /tmp/restore_errors.log

# 查看錯誤日誌
grep -i "error\|fatal" /tmp/restore_errors.log
```

**常見錯誤與解決方案**:

**2.1 角色（Role）不存在**
```sql
-- 錯誤訊息：role "some_user" does not exist

-- 解決方案：手動創建角色
docker compose exec postgres psql -U quantlab quantlab -c "CREATE ROLE some_user WITH LOGIN PASSWORD 'password';"
```

**2.2 擴充套件（Extension）缺失**
```sql
-- 錯誤訊息：extension "timescaledb" is not available

-- 解決方案：安裝 TimescaleDB 擴充
docker compose exec postgres psql -U quantlab quantlab -c "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"
```

**2.3 資料庫版本不相容**
```bash
# 解決方案：升級或降級 PostgreSQL 版本
# 修改 docker-compose.yml 中的 postgres 映像版本
# image: timescale/timescaledb:latest-pg15  # 改為與舊系統相同版本
```

### 問題 3：Qlib 數據讀取失敗

**症狀**: Qlib 初始化或數據讀取時報錯

**診斷**:
```bash
# 測試 Qlib 初始化
docker compose exec backend python -c "
import qlib
try:
    qlib.init(provider_uri='/data/qlib/tw_stock_v2', region='tw')
    print('Qlib 初始化成功')
except Exception as e:
    print(f'Qlib 初始化失敗: {e}')
"
```

**常見錯誤與解決方案**:

**3.1 數據目錄不存在或為空**
```bash
# 檢查數據目錄
ls -lh /data/qlib/tw_stock_v2/
ls -lh /data/qlib/tw_stock_minute/

# 解決方案：重新解壓縮 Qlib 數據
cd /data/qlib
tar -xzf /tmp/quantlab_qlib_all_YYYYMMDD.tar.gz --strip-components=2
```

**3.2 文件權限問題**
```bash
# 錯誤訊息：Permission denied

# 解決方案：修改權限
sudo chown -R 1000:1000 /data/qlib/
# 或
sudo chmod -R 755 /data/qlib/
```

**3.3 數據格式損壞**
```bash
# 解決方案：使用 Qlib 工具檢查並修復
docker compose exec backend python -c "
from qlib.data.storage.file_storage import FileFeatureStorage
import os

# 檢查特定股票的數據
stock_id = '2330'
field = 'close'
storage = FileFeatureStorage(instrument=stock_id, field=field, freq='day',
                             provider_uri='/data/qlib/tw_stock_v2')
try:
    data = storage.read()
    print(f'{stock_id} {field} 數據正常，共 {len(data)} 筆')
except Exception as e:
    print(f'數據讀取失敗: {e}')
"
```

### 問題 4：前端無法訪問

**症狀**: 瀏覽器訪問 http://新機器IP 無回應或顯示錯誤

**診斷**:
```bash
# 測試 Nginx 是否運行
docker compose exec nginx nginx -t

# 測試前端容器是否運行
docker compose exec frontend curl -I http://localhost:3000/

# 測試後端 API
curl http://localhost:8000/api/v1/health
```

**常見錯誤與解決方案**:

**4.1 Nginx 配置錯誤**
```bash
# 檢查 Nginx 配置
docker compose exec nginx nginx -t

# 如果配置錯誤，檢查 nginx/nginx.conf
vim /home/ubuntu/QuantLab/nginx/nginx.conf

# 重新載入配置
docker compose restart nginx
```

**4.2 前端環境變數錯誤**
```bash
# 檢查前端環境變數
docker compose exec frontend env | grep NUXT

# 應該看到：
# NUXT_PUBLIC_API_BASE=http://新機器IP:8000 或 http://quantlab.yourdomain.com

# 如果錯誤，修改 .env 並重新構建前端
vim .env
docker compose build frontend
docker compose restart frontend
```

**4.3 CORS 問題**
```bash
# 錯誤訊息（瀏覽器控制台）：Access to XMLHttpRequest has been blocked by CORS policy

# 解決方案：檢查後端 CORS 設定
docker compose exec backend python -c "
from app.core.config import settings
print(f'CORS Origins: {settings.CORS_ORIGINS}')
"

# 修改 .env 或 backend/app/core/config.py
# CORS_ORIGINS=["http://新機器IP","http://localhost:3000"]
```

### 問題 5：Celery 任務無法執行

**症狀**: Celery 任務一直處於 PENDING 狀態或執行失敗

**診斷**:
```bash
# 檢查 Celery worker 狀態
docker compose exec backend celery -A app.core.celery_app inspect active

# 檢查 Redis 連線
docker compose exec backend python -c "
import redis
r = redis.from_url('redis://redis:6379/0')
print(r.ping())  # 應輸出 True
"

# 查看 Celery 日誌
docker compose logs celery-worker --tail 100
```

**常見錯誤與解決方案**:

**5.1 Redis 連線失敗**
```bash
# 錯誤訊息：Error 111 connecting to redis:6379. Connection refused

# 解決方案：
# 1. 確認 Redis 容器運行中
docker compose ps redis

# 2. 檢查 .env 中的 Redis 設定
grep REDIS_URL .env

# 3. 重啟 Redis 和 Celery
docker compose restart redis celery-worker celery-beat
```

**5.2 任務被撤銷（Revoked）**
```bash
# 檢查 revoked 任務
docker compose exec backend celery -A app.core.celery_app inspect revoked

# 解決方案：清空 revoked 列表並重啟
docker compose exec redis redis-cli FLUSHDB
docker compose restart celery-worker celery-beat
```

**5.3 任務超時**
```bash
# 錯誤訊息：TimeLimitExceeded

# 解決方案：調整任務超時設定
# 修改 backend/app/core/celery_app.py
# task_soft_time_limit 和 task_time_limit
```

### 問題 6：網路連線問題

**症狀**: 容器之間無法通訊

**診斷**:
```bash
# 檢查 Docker 網路
docker network ls | grep quantlab

# 檢查容器網路連線
docker compose exec backend ping -c 3 postgres
docker compose exec backend ping -c 3 redis
docker compose exec frontend ping -c 3 backend
```

**解決方案**:
```bash
# 重新創建網路
docker compose down
docker network prune -f
docker compose up -d

# 或手動創建網路
docker network create quantlab_default
```

### 問題 7：磁碟空間不足

**症狀**: 容器無法啟動或數據無法寫入

**診斷**:
```bash
# 檢查磁碟使用量
df -h

# 檢查 Docker 磁碟使用
docker system df
```

**解決方案**:
```bash
# 清理未使用的 Docker 資源
docker system prune -a --volumes

# 清理舊的映像
docker image prune -a

# 清理未使用的 volumes
docker volume prune

# 如果仍不足，考慮：
# 1. 刪除 Prometheus 歷史數據（可重新收集）
# 2. 壓縮或移動 Qlib 數據到更大的磁碟
# 3. 清理資料庫舊數據（使用我們實作的 cleanup 任務）
```

---

## 回滾計劃

如果新機器遷移失敗，需要回滾到舊機器：

### 步驟 1：停止新機器服務

```bash
# 在新機器上
cd /home/ubuntu/QuantLab
docker compose down
```

### 步驟 2：重啟舊機器服務

```bash
# 在舊機器上
cd /home/ubuntu/QuantLab
docker compose up -d

# 驗證所有服務正常
docker compose ps
```

### 步驟 3：更新 DNS 或負載均衡器（如有使用）

```bash
# 將流量重新導向舊機器 IP
# 這取決於您的網路設定
```

### 步驟 4：通知用戶

```
尊敬的用戶：

由於技術原因，系統遷移已暫停並回滾至原有機器。
服務已恢復正常，對造成的不便深感抱歉。

QuantLab 團隊
```

---

## 遷移後清理

遷移成功並穩定運行 1-2 週後，可以清理舊機器：

### 步驟 1：最終備份

```bash
# 在舊機器上進行最終備份（以防萬一）
cd /home/ubuntu/QuantLab
docker compose exec postgres pg_dump -U quantlab quantlab > /tmp/final_backup_$(date +%Y%m%d).sql
```

### 步驟 2：停止舊機器服務

```bash
# 在舊機器上
cd /home/ubuntu/QuantLab
docker compose down -v  # -v 會刪除 volumes

# 停止 Docker 服務（可選）
sudo systemctl stop docker
sudo systemctl disable docker
```

### 步驟 3：清理磁碟空間

```bash
# 刪除 Docker 相關檔案
sudo apt-get purge docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 刪除 Docker 資料目錄
sudo rm -rf /var/lib/docker
sudo rm -rf /var/lib/containerd

# 刪除專案目錄（請三思！）
# rm -rf /home/ubuntu/QuantLab
# rm -rf /data/qlib

# 或保留壓縮備份
tar -czf /tmp/quantlab_old_machine_final.tar.gz /home/ubuntu/QuantLab /data/qlib
```

---

## 附錄

### A. 完整檢查清單

**遷移前準備**:
- [ ] 新機器硬體符合需求
- [ ] 新機器已安裝 Docker 和 Docker Compose
- [ ] 已通知用戶即將維護
- [ ] 已確認無重要任務運行
- [ ] 已準備備份儲存空間（至少 50 GB）

**備份階段**:
- [ ] 已停止舊機器所有容器
- [ ] 已備份程式碼（~2 GB）
- [ ] 已備份環境變數（.env）
- [ ] 已備份資料庫（~2.5 GB）
- [ ] 已備份 Qlib 數據（~24 GB）
- [ ] 已備份 Docker Volumes
- [ ] 已備份 Nginx 配置
- [ ] 已傳輸備份到安全位置

**還原階段**:
- [ ] 已還原程式碼
- [ ] 已還原環境變數
- [ ] 已還原 Qlib 數據
- [ ] 已還原資料庫
- [ ] 已還原其他服務數據
- [ ] 已構建 Docker 映像
- [ ] 已啟動所有容器

**驗證階段**:
- [ ] 所有容器健康運行
- [ ] 資料庫數據完整
- [ ] Qlib 數據可正常讀取
- [ ] 前端可正常訪問
- [ ] API 端點正常回應
- [ ] Celery 任務正常執行
- [ ] Telegram Bot 正常運作
- [ ] 監控服務正常

**切換階段**:
- [ ] 已更新 DNS 記錄（如有）
- [ ] 已更新負載均衡器（如有）
- [ ] 已通知用戶服務已遷移
- [ ] 舊機器服務已停止（備用）

**清理階段**（遷移後 1-2 週）:
- [ ] 新機器穩定運行
- [ ] 已進行最終備份
- [ ] 已清理舊機器資源

### B. 常用命令速查

**Docker Compose**:
```bash
# 啟動服務
docker compose up -d

# 停止服務
docker compose stop

# 重啟服務
docker compose restart <service>

# 查看日誌
docker compose logs -f <service>

# 查看容器狀態
docker compose ps

# 進入容器
docker compose exec <service> bash

# 構建映像
docker compose build

# 停止並刪除所有容器
docker compose down

# 停止並刪除所有容器和 volumes
docker compose down -v
```

**資料庫操作**:
```bash
# 連接資料庫
docker compose exec postgres psql -U quantlab quantlab

# 執行 SQL 檔案
docker compose exec -T postgres psql -U quantlab quantlab < backup.sql

# 匯出資料庫
docker compose exec postgres pg_dump -U quantlab quantlab > backup.sql

# 檢查資料庫大小
docker compose exec postgres psql -U quantlab quantlab -c "SELECT pg_size_pretty(pg_database_size('quantlab'));"
```

**系統監控**:
```bash
# 查看容器資源使用
docker stats

# 查看磁碟使用
df -h
du -sh /data/qlib

# 查看 Docker 資源使用
docker system df

# 查看容器日誌
docker compose logs --tail 100 <service>
```

### C. 緊急聯絡資訊

**技術支援**:
- GitHub Issues: https://github.com/your-org/QuantLab/issues
- Email: support@quantlab.com
- Telegram: @QuantLabSupport

**關鍵服務帳號**:
- Docker Hub: your-dockerhub-account
- 雲端儲存: your-cloud-storage
- 域名註冊商: your-domain-registrar

---

## 總結

本遷移指南提供了完整的 QuantLab 系統遷移流程，包括：

1. **備份**: 程式碼、資料庫、Qlib 數據、配置檔案
2. **還原**: 環境準備、數據還原、服務啟動
3. **驗證**: 全方位的功能和效能測試
4. **故障排除**: 常見問題的診斷和解決方案
5. **回滾計劃**: 萬一失敗的應急預案

**關鍵提醒**:
- ⚠️ 遷移前務必進行完整備份
- ⚠️ 建議在低峰時段進行遷移（如週末深夜）
- ⚠️ 遷移過程中保持舊機器運行，直到新機器完全驗證通過
- ⚠️ 新機器穩定運行 1-2 週後再清理舊機器

**預估時間**:
- **總計**: 3-6.5 小時
- **備份**: 1-2 小時
- **傳輸**: 1-3 小時（取決於網路速度）
- **還原**: 30-60 分鐘
- **驗證**: 30 分鐘

祝您遷移順利！

---

**文檔維護者**: QuantLab 開發團隊
**最後更新**: 2025-12-30
**文檔版本**: 1.0
