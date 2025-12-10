# QuantLab 遷移指南

> 📋 **版本**: v1.0
> 📅 **更新日期**: 2025-12-09
> 🎯 **適用場景**: 跨機器遷移、災難恢復、環境複製

---

## 📊 當前系統概況

### 系統規模
- **數據庫大小**: ~1.7 GB
- **Qlib 數據**: ~500 MB
- **總備份大小**: ~2.5 GB（壓縮後）
- **策略數量**: 46 個
- **回測記錄**: 17 個

### 服務架構
```
┌─────────────────────────────────────────────┐
│  Frontend (Nuxt.js)      :3000              │
├─────────────────────────────────────────────┤
│  Backend (FastAPI)       :8000              │
├─────────────────────────────────────────────┤
│  PostgreSQL + TimescaleDB :5432             │
│  Redis                    :6379             │
│  Celery Worker + Beat                       │
├─────────────────────────────────────────────┤
│  Qlib Data               /data/qlib         │
└─────────────────────────────────────────────┘
```

---

## 🚀 快速遷移（3 步驟）

### 方案 A：自動化遷移（推薦）⚡

#### 在舊機器上：
```bash
# 1. 執行備份腳本
cd /path/to/QuantLab
./scripts/backup-for-migration.sh

# 2. 傳輸到新機器
scp -r quantlab_migration_* user@new-server:/tmp/
```

#### 在新機器上：
```bash
# 1. 安裝 Docker（如果尚未安裝）
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# 2. 創建工作目錄
mkdir -p ~/quantlab && cd ~/quantlab

# 3. 執行還原腳本
/tmp/quantlab_migration_*/scripts/restore-from-backup.sh /tmp/quantlab_migration_*

# 4. 修改敏感配置
nano .env
# 更新: JWT_SECRET, ALLOWED_ORIGINS

# 5. 重啟服務
docker compose restart backend frontend
```

**預估時間**: 15-30 分鐘（取決於網路速度）

---

### 方案 B：手動遷移（進階）🔧

詳細步驟請參考自動生成的 `README_MIGRATION.md`。

---

## 📦 備份內容說明

### 核心數據
| 檔案名稱 | 說明 | 大小 | 必要性 |
|---------|------|------|--------|
| `database.sql.gz` | PostgreSQL 完整備份 | ~1.5 GB | ✅ 必要 |
| `redis_dump.rdb` | Redis 數據快照 | ~10 MB | ⚠️ 建議 |
| `qlib_data.tar.gz` | Qlib 量化數據 | ~400 MB | ⚠️ 建議 |
| `quantlab_repo.bundle` | Git 完整倉庫 | ~50 MB | ✅ 必要 |
| `.env.backup` | 環境變數配置 | <1 KB | ✅ 必要 |

### 元數據
- `git_commit.txt` - Git commit hash
- `git_branch.txt` - 當前分支名稱
- `git_status.txt` - Git 狀態
- `BACKUP_MANIFEST.txt` - 備份清單
- `README_MIGRATION.md` - 遷移說明

---

## 🔐 安全檢查清單

### 遷移前（舊機器）
- [ ] 確認所有數據已保存
- [ ] 記錄環境變數（尤其是 API Keys）
- [ ] 備份 `.env` 文件
- [ ] 確認 Git 倉庫沒有未提交的更改
- [ ] 測試備份完整性

### 遷移後（新機器）
- [ ] **重新生成 JWT_SECRET**
  ```bash
  openssl rand -hex 32
  ```
- [ ] 更新 `ALLOWED_ORIGINS`（改為新機器 IP）
- [ ] 檢查所有服務健康狀態
- [ ] 驗證數據完整性
- [ ] 測試登入功能
- [ ] 測試策略創建/回測功能
- [ ] 配置防火牆規則
- [ ] 設定 HTTPS（生產環境）

---

## 🌐 網路配置

### 本地開發環境
```env
# .env
ALLOWED_ORIGINS=http://localhost:3000
NUXT_PUBLIC_API_BASE=http://localhost:8000
```

### 區域網訪問
```env
# .env
ALLOWED_ORIGINS=http://192.168.1.100:3000,http://localhost:3000
NUXT_PUBLIC_API_BASE=http://192.168.1.100:8000
```

### 生產環境（HTTPS）
```env
# .env
ALLOWED_ORIGINS=https://quantlab.example.com
NUXT_PUBLIC_API_BASE=https://api.quantlab.example.com
```

---

## 🧪 驗證測試

### 1. 基礎健康檢查
```bash
# 後端 API
curl http://localhost:8000/health
# 預期: {"status":"healthy","version":"0.1.0"}

# 前端
curl -I http://localhost:3000
# 預期: HTTP/1.1 200 OK

# PostgreSQL
docker compose exec postgres pg_isready -U quantlab
# 預期: accepting connections

# Redis
docker compose exec redis redis-cli ping
# 預期: PONG
```

### 2. 數據完整性檢查
```bash
docker compose exec -T postgres psql -U quantlab quantlab << 'SQL'
-- 用戶數
SELECT count(*) as users FROM users;

-- 策略數
SELECT count(*) as strategies FROM strategies;

-- 回測數
SELECT count(*) as backtests FROM backtests;

-- 股票數據
SELECT count(*) as stocks FROM stock_list;

-- 基本面數據
SELECT count(*) as fundamentals FROM fundamental_data;

-- 產業分類
SELECT count(*) as industries FROM industries;
SQL
```

### 3. 功能測試
1. **登入測試**
   - 訪問 http://localhost:3000
   - 使用原有帳號登入
   - 檢查用戶資訊是否正確顯示

2. **策略測試**
   - 查看策略列表
   - 創建新策略
   - 編輯現有策略

3. **回測測試**
   - 查看回測記錄
   - 執行新回測
   - 檢查結果視覺化

4. **數據同步測試**
   ```bash
   # 檢查 Celery worker
   docker compose exec backend celery -A app.core.celery_app inspect active

   # 手動觸發同步任務
   docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_stock_list
   ```

---

## 🔧 常見問題排查

### 問題 1: 數據庫連接失敗
```
django.db.utils.OperationalError: could not connect to server
```

**解決方案**:
```bash
# 檢查 PostgreSQL 日誌
docker compose logs postgres

# 重置密碼
docker compose exec postgres psql -U postgres -c "ALTER USER quantlab PASSWORD 'quantlab2025';"

# 重啟數據庫
docker compose restart postgres
```

---

### 問題 2: CORS 錯誤
```
Access to fetch at 'http://localhost:8000/api/v1/...' from origin 'http://localhost:3000' has been blocked by CORS policy
```

**解決方案**:
```bash
# 1. 檢查 .env 配置
cat .env | grep ALLOWED_ORIGINS

# 2. 更新 ALLOWED_ORIGINS
nano .env
# ALLOWED_ORIGINS=http://localhost:3000,http://192.168.1.100:3000

# 3. 重啟後端
docker compose restart backend
```

---

### 問題 3: Qlib 數據讀取失敗
```
FileNotFoundError: [Errno 2] No such file or directory: '/data/qlib/...'
```

**解決方案**:
```bash
# 1. 檢查 Qlib 數據路徑
ls -la /data/qlib/

# 2. 修復權限
sudo chown -R $USER:$USER /data/qlib

# 3. 檢查 Docker volume 掛載
docker compose exec backend ls -la /data/qlib

# 4. 如果數據丟失，重新同步
./scripts/sync-qlib-smart.sh
```

---

### 問題 4: 前端無法啟動
```
[nitro] ERROR  Cannot find module '@nuxt/kit'
```

**解決方案**:
```bash
# 清理前端緩存並重建
./scripts/quick-clean.sh

# 或手動清理
docker compose stop frontend
docker compose run --rm frontend sh -c "rm -rf .nuxt .output node_modules/.cache"
docker compose up -d frontend
```

---

### 問題 5: Celery worker 無法啟動
```
[ERROR/MainProcess] consumer: Cannot connect to redis://redis:6379/0
```

**解決方案**:
```bash
# 1. 檢查 Redis 狀態
docker compose ps redis

# 2. 檢查網路連接
docker compose exec backend ping redis

# 3. 重啟 Redis 和 Celery
docker compose restart redis celery-worker celery-beat
```

---

## 📊 效能優化建議

### 新機器硬體建議

| 環境 | CPU | RAM | 磁碟 | 網路 |
|-----|-----|-----|------|------|
| 開發 | 2 核心 | 4 GB | 20 GB SSD | 100 Mbps |
| 測試 | 4 核心 | 8 GB | 50 GB SSD | 1 Gbps |
| 生產 | 8 核心 | 16 GB | 200 GB SSD | 1 Gbps |

### Docker 資源限制
```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          memory: 1G

  postgres:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          memory: 2G
```

---

## 🔄 定期備份策略

### 每日備份（推薦）
```bash
# 加入 crontab
crontab -e

# 每天凌晨 2:00 執行備份
0 2 * * * /path/to/quantlab/scripts/backup-for-migration.sh

# 保留最近 7 天的備份
0 3 * * * find /backups -name "quantlab_migration_*" -mtime +7 -exec rm -rf {} \;
```

### 備份到雲端
```bash
# AWS S3
aws s3 sync quantlab_migration_*/ s3://my-bucket/quantlab-backups/$(date +%Y%m%d)/

# Google Drive (rclone)
rclone sync quantlab_migration_*/ gdrive:QuantLab/backups/$(date +%Y%m%d)/
```

---

## 🎯 遷移檢查表

### 遷移前準備
- [ ] 閱讀完整遷移指南
- [ ] 確認新機器符合系統需求
- [ ] 安裝 Docker 和 Docker Compose
- [ ] 準備足夠的磁碟空間（至少 10 GB）
- [ ] 記錄所有 API Keys 和密碼

### 執行備份
- [ ] 運行 `backup-for-migration.sh`
- [ ] 檢查備份清單（BACKUP_MANIFEST.txt）
- [ ] 驗證備份檔案完整性
- [ ] 測試備份檔案可讀性

### 傳輸數據
- [ ] 選擇傳輸方式（scp/rsync/雲端）
- [ ] 傳輸所有備份檔案
- [ ] 驗證傳輸完整性（校驗和）

### 新機器還原
- [ ] 運行 `restore-from-backup.sh`
- [ ] 修改 `.env` 敏感信息
- [ ] 重新生成 JWT_SECRET
- [ ] 更新 ALLOWED_ORIGINS
- [ ] 重啟所有服務

### 驗證測試
- [ ] 所有服務健康檢查通過
- [ ] 數據完整性檢查通過
- [ ] 登入功能正常
- [ ] 策略創建/編輯正常
- [ ] 回測執行正常
- [ ] Celery 任務正常

### 生產環境配置（可選）
- [ ] 配置 Nginx 反向代理
- [ ] 申請 SSL 證書（Let's Encrypt）
- [ ] 設定防火牆規則
- [ ] 配置監控告警
- [ ] 設定定期備份

---

## 📚 相關文檔

- [CLAUDE.md](CLAUDE.md) - 開發指南
- [DATABASE_SCHEMA_REPORT.md](DATABASE_SCHEMA_REPORT.md) - 數據庫架構
- [QLIB_INTEGRATION_COMPLETE.md](QLIB_INTEGRATION_COMPLETE.md) - Qlib 整合
- [RDAGENT_INTEGRATION_GUIDE.md](RDAGENT_INTEGRATION_GUIDE.md) - RD-Agent 整合

---

## 🆘 支援與協助

### 日誌位置
```bash
# 所有服務日誌
docker compose logs -f

# 特定服務日誌
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f postgres
docker compose logs -f celery-worker

# 導出日誌
docker compose logs > quantlab_logs_$(date +%Y%m%d).txt
```

### 健康檢查端點
- 後端健康: http://localhost:8000/health
- API 文檔: http://localhost:8000/docs
- ReDoc 文檔: http://localhost:8000/redoc

### 故障恢復
如果遷移失敗：
1. 保留舊機器系統不變
2. 收集新機器日誌信息
3. 參考常見問題排查
4. 必要時重新執行還原流程

---

## 📝 更新記錄

| 日期 | 版本 | 更新內容 |
|------|------|---------|
| 2025-12-09 | v1.0 | 初始版本 |

---

**💡 提示**: 遷移過程中遇到問題？請查看自動生成的 `README_MIGRATION.md` 或執行 `docker compose logs` 查看詳細日誌。
