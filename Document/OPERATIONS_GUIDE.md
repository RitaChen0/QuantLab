# QuantLab 操作指南

完整的系統操作手冊，涵蓋日常運維、開發與故障排查。

## 目錄

- [Docker 環境管理](#docker-環境管理)
- [資料庫管理](#資料庫管理)
- [後端開發](#後端開發)
- [前端開發](#前端開發)
- [監控與日誌](#監控與日誌)
- [常見問題排查](#常見問題排查)

## Docker 環境管理

### 基本操作

```bash
# 啟動所有服務
docker compose up -d

# 查看服務狀態
docker compose ps

# 查看日誌（所有服務）
docker compose logs -f

# 查看特定服務日誌
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f celery-worker

# 重啟特定服務
docker compose restart backend
docker compose restart frontend

# 停止所有服務
docker compose down

# 停止並刪除所有數據（包括 volumes）
docker compose down -v

# 重新構建並啟動
docker compose up --build -d

# 重新構建特定服務
docker compose build --no-cache backend
docker compose up -d backend
```

### 容器管理

```bash
# 進入容器
docker compose exec backend bash
docker compose exec frontend sh
docker compose exec postgres psql -U quantlab -d quantlab

# 查看容器資源使用
docker stats

# 清理未使用的容器和映像
docker system prune -a
```

### 健康檢查

```bash
# Backend API
curl http://localhost:8000/health

# Frontend
curl http://localhost:3000/

# PostgreSQL
docker compose exec postgres pg_isready -U quantlab

# Redis
docker compose exec backend redis-cli -h redis ping
```

## 資料庫管理

### Alembic 遷移

```bash
# 執行遷移（升級到最新版本）
docker compose exec backend alembic upgrade head

# 創建新的遷移檔案
docker compose exec backend alembic revision --autogenerate -m "描述變更"

# 回滾到上一個版本
docker compose exec backend alembic downgrade -1

# 查看遷移歷史
docker compose exec backend alembic history

# 查看當前版本
docker compose exec backend alembic current
```

### 直接連接資料庫

```bash
# 連接到 PostgreSQL
docker compose exec postgres psql -U quantlab -d quantlab

# 常用查詢
# 查看所有資料表
\dt

# 查看資料表結構
\d users
\d strategies

# 查看資料表大小
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

# 查看資料庫大小
SELECT pg_size_pretty(pg_database_size('quantlab'));
```

### 備份與還原

```bash
# 完整備份
docker compose exec -T postgres pg_dump -U quantlab quantlab | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# 僅備份特定資料表
docker compose exec -T postgres pg_dump -U quantlab quantlab -t users -t strategies | gzip > partial_backup.sql.gz

# 還原備份
gunzip < backup.sql.gz | docker compose exec -T postgres psql -U quantlab quantlab

# 使用自動化腳本備份
./scripts/backup_database.sh
./scripts/backup_industries.sh
```

## 後端開發

### 進入後端容器

```bash
# 進入容器
docker compose exec backend bash

# 查看 Python 版本
python --version

# 查看已安裝的套件
pip list
```

### 測試

```bash
# 運行所有測試
docker compose exec backend pytest

# 運行特定測試檔案
docker compose exec backend pytest tests/test_auth.py

# 運行特定測試函數
docker compose exec backend pytest tests/test_auth.py::test_register

# 顯示詳細輸出
docker compose exec backend pytest -v

# 顯示測試覆蓋率
docker compose exec backend pytest --cov=app
```

### 代碼品質

```bash
# 檢查代碼風格
docker compose exec backend flake8 app/

# 自動格式化代碼
docker compose exec backend black app/

# 檢查格式（不修改）
docker compose exec backend black --check app/

# 類型檢查
docker compose exec backend mypy app/
```

### 添加新依賴

```bash
# 1. 編輯 requirements.txt
vim backend/requirements.txt

# 2. 重新構建容器
docker compose build backend

# 3. 重啟服務
docker compose up -d backend
```

## 前端開發

### 進入前端容器

```bash
# 進入容器
docker compose exec frontend sh

# 查看 Node 版本
node --version
npm --version
```

### 依賴管理

```bash
# 重新安裝依賴
docker compose exec frontend npm install

# 添加新依賴
docker compose exec frontend npm install package-name

# 更新依賴
docker compose exec frontend npm update
```

### 代碼品質

```bash
# 運行 linting
docker compose exec frontend npm run lint

# 自動修復 lint 錯誤
docker compose exec frontend npm run lint:fix

# 類型檢查（如果啟用）
docker compose exec frontend npm run type-check
```

### 清理緩存

```bash
# 使用自動化腳本（推薦）
./scripts/quick-clean.sh

# 手動清理
docker compose stop frontend
docker compose run --rm frontend sh -c "rm -rf .nuxt .output node_modules/.vite node_modules/.cache"
docker compose up -d frontend

# 完整重建（最徹底）
docker compose down
docker compose build --no-cache frontend
docker compose up -d
```

## 監控與日誌

### 實時日誌查看

```bash
# 所有服務
docker compose logs -f

# 特定服務
docker compose logs -f backend
docker compose logs -f celery-worker
docker compose logs -f celery-beat

# 查看最近 100 行
docker compose logs --tail=100 backend

# 查看最近 1 小時
docker compose logs --since 1h backend

# 查看錯誤日誌
docker compose logs backend | grep -i error
docker compose logs celery-worker | grep -i error
```

### 服務狀態監控

```bash
# 查看所有容器狀態
docker compose ps

# 查看容器資源使用
docker stats

# 查看 Celery worker 狀態
docker compose exec backend celery -A app.core.celery_app inspect active
docker compose exec backend celery -A app.core.celery_app inspect stats

# 使用監控腳本
./monitor_celery.sh
```

### 應用日誌查詢

```bash
# 後台管理頁面日誌查詢
# 訪問 http://localhost:3000/admin
# 點擊「日誌查詢」標籤

# 手動查詢容器日誌
docker compose logs backend --since 1h | grep "ERROR"
docker compose logs backend --since 1h | grep "user_id"
```

## 常見問題排查

### 後端容器反覆重啟

**症狀**：`docker compose ps` 顯示 backend 不斷重啟

**排查步驟**：
```bash
# 1. 查看日誌
docker compose logs backend

# 2. 檢查常見原因
# - 資料庫連接失敗：檢查 DATABASE_URL
# - 環境變數缺失：檢查 .env 文件
# - Python 依賴問題：重新構建容器

# 3. 重新構建
docker compose build backend
docker compose up -d backend
```

### Alembic 遷移失敗

**症狀**：`alembic upgrade head` 報錯

**排查步驟**：
```bash
# 1. 確認 PostgreSQL 健康
docker compose ps postgres
docker compose exec postgres pg_isready -U quantlab

# 2. 檢查遷移檔案語法
cat backend/alembic/versions/最新版本.py

# 3. 確認新模型已在 app/db/base.py 導入
cat backend/app/db/base.py

# 4. 手動回滾後重試
docker compose exec backend alembic downgrade -1
docker compose exec backend alembic upgrade head
```

### 前端白屏或 500 錯誤

**症狀**：前端頁面無法載入

**排查步驟**：
```bash
# 1. 查看前端日誌
docker compose logs frontend

# 2. 檢查 nuxt.config.ts 配置
cat frontend/nuxt.config.ts

# 3. 清理緩存並重啟
./scripts/quick-clean.sh

# 4. 檢查 API 連接
curl http://localhost:8000/health
```

### Celery worker 無法連接

**症狀**：任務無法執行

**排查步驟**：
```bash
# 1. 確認 Redis 運行
docker compose ps redis
docker compose exec backend redis-cli -h redis ping

# 2. 檢查環境變數
docker compose exec backend env | grep CELERY

# 3. 查看 worker 日誌
docker compose logs celery-worker

# 4. 重啟 worker 和 beat
docker compose restart celery-worker celery-beat
```

### 任務更新後無法載入

**症狀**：新增的 Celery 任務出現 ImportError

**解決方案**：
```bash
# 1. 檢查任務導出
cat backend/app/tasks/__init__.py

# 2. 清除 Python cache
docker compose exec celery-worker find /app -name __pycache__ -type d -exec rm -rf {} +

# 3. 重啟 worker 和 beat
docker compose restart celery-worker celery-beat

# 4. 驗證任務已註冊
docker compose exec backend celery -A app.core.celery_app inspect registered
```

### 檔案權限問題

**症狀**：無法寫入檔案

**解決方案**：
```bash
# Python 檔案
chmod 644 backend/app/新檔案.py

# 目錄
chmod 755 backend/app/新目錄

# 批次處理
chmod -R a+r backend/app/
chmod -R a+X backend/app/
```

### SVG 圖示顯示異常

**症狀**：SVG 圖示佔據整個螢幕

**解決方案**：
在 `<style scoped>` 中明確設定 SVG 尺寸：
```scss
svg.w-4 {
  width: 1rem !important;
  height: 1rem !important;
  flex-shrink: 0;
}
```

**參考**：
- `frontend/pages/docs.vue:320-325`
- `frontend/pages/industry/index.vue:1052-1068`

### 前端導航後需重新登入

**症狀**：從某些頁面返回後 token 遺失

**原因**：使用 `<a href>` 觸發完整頁面重載

**解決方案**：
```vue
<!-- ❌ 錯誤 -->
<a href="/dashboard">返回儀表板</a>

<!-- ✅ 正確 -->
<NuxtLink to="/dashboard">返回儀表板</NuxtLink>
```

### 產業指標計算失敗

**症狀**：API 返回 0 個指標

**原因**：`fundamental_data` 表使用季度字串（如 "2024-Q4"），不是日期格式

**解決方案**：
```python
# ❌ 錯誤
metric_date = date.today()  # "2025-12-12"

# ✅ 正確
latest_quarter = db.execute(
    text("SELECT date FROM fundamental_data ORDER BY date DESC LIMIT 1")
).fetchone()[0]  # "2024-Q4"
```

**檢查資料**：
```bash
docker compose exec postgres psql -U quantlab quantlab -c \
  "SELECT DISTINCT date FROM fundamental_data ORDER BY date DESC LIMIT 10;"
```

## 效能優化

### 資料庫查詢優化

```bash
# 查看慢查詢
docker compose exec postgres psql -U quantlab quantlab -c \
  "SELECT query, calls, total_time, mean_time
   FROM pg_stat_statements
   ORDER BY mean_time DESC
   LIMIT 10;"

# 分析查詢計劃
docker compose exec postgres psql -U quantlab quantlab -c \
  "EXPLAIN ANALYZE SELECT * FROM strategies WHERE user_id = 1;"
```

### 快取管理

```bash
# 查看 Redis 快取大小
docker compose exec backend redis-cli -h redis info memory

# 查看所有 keys
docker compose exec backend redis-cli -h redis keys '*'

# 清除特定 pattern 的快取
docker compose exec backend redis-cli -h redis --scan --pattern 'price:*' | xargs docker compose exec -T backend redis-cli -h redis del

# 清除所有快取
docker compose exec backend redis-cli -h redis FLUSHALL
```

### 容器資源限制

編輯 `docker-compose.yml`：
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## 安全檢查

### 環境變數檢查

```bash
# 檢查必填環境變數
docker compose exec backend env | grep -E "DATABASE_URL|REDIS_URL|JWT_SECRET|FINLAB_API_TOKEN"

# 檢查 JWT_SECRET 強度（應至少 32 字元）
docker compose exec backend env | grep JWT_SECRET | awk -F= '{print length($2)}'
```

### 密碼強度檢查

```bash
# 檢查 bcrypt cost factor（應為 12）
docker compose exec backend python -c "from app.core.config import settings; print(settings.BCRYPT_ROUNDS)"
```

### API 速率限制檢查

```bash
# 查看當前速率限制設定
cat backend/app/core/rate_limit.py

# 重置速率限制（開發環境）
./scripts/reset-rate-limit.sh
```

## 維護任務

### 定期維護清單

**每日**：
- 查看錯誤日誌
- 檢查 Celery 任務執行狀態
- 監控資料庫大小

**每週**：
- 清理過期快取
- 檢查資料庫備份
- 更新依賴套件

**每月**：
- 完整資料庫備份
- 檢查磁碟空間
- 審查安全日誌

### 自動化腳本

```bash
# 資料庫備份
./scripts/backup_database.sh

# 清理前端緩存
./scripts/quick-clean.sh

# 重置速率限制
./scripts/reset-rate-limit.sh
```

## 相關文檔

- [Qlib 同步指南](QLIB_SYNC_GUIDE.md)
- [Celery 任務管理](CELERY_TASKS_GUIDE.md)
- [開發指南](DEVELOPMENT_GUIDE.md)
- [資料庫維護指南](DATABASE_MAINTENANCE.md)
