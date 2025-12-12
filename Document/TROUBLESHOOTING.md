# 故障排查快速索引

快速查找和解決常見問題。

## 🔍 問題分類

- [容器問題](#容器問題)
- [資料庫問題](#資料庫問題)
- [前端問題](#前端問題)
- [Celery 問題](#celery-問題)
- [Qlib 問題](#qlib-問題)
- [權限問題](#權限問題)
- [效能問題](#效能問題)

---

## 容器問題

### ❌ 後端容器反覆重啟

**症狀**：`docker compose ps` 顯示 backend 狀態為 `Restarting`

**快速檢查**：
```bash
docker compose logs backend --tail=50
```

**常見原因與解決方案**：

| 錯誤訊息 | 原因 | 解決方案 |
|---------|------|---------|
| `could not connect to server: Connection refused` | 資料庫連接失敗 | 檢查 `DATABASE_URL`，確認 postgres 容器運行 |
| `JWT_SECRET is required` | 環境變數缺失 | 在 `.env` 添加 `JWT_SECRET` |
| `ModuleNotFoundError: No module named 'xxx'` | Python 依賴缺失 | `docker compose build backend` |
| `Port 8000 is already in use` | 端口被佔用 | `lsof -i :8000` 找出佔用進程並 kill |

**完整排查步驟**：
```bash
# 1. 查看詳細錯誤
docker compose logs backend

# 2. 檢查環境變數
docker compose exec backend env | grep -E "DATABASE_URL|JWT_SECRET|REDIS_URL"

# 3. 重新構建
docker compose build backend

# 4. 重啟
docker compose up -d backend
```

**參考文檔**：[Document/OPERATIONS_GUIDE.md#後端容器反覆重啟](Document/OPERATIONS_GUIDE.md)

---

### ❌ 前端容器無法啟動

**症狀**：`docker compose ps` 顯示 frontend 狀態為 `Exit 1`

**快速檢查**：
```bash
docker compose logs frontend --tail=50
```

**常見原因**：

| 錯誤訊息 | 解決方案 |
|---------|---------|
| `ENOENT: no such file or directory` | `docker compose build frontend` |
| `Module not found` | `docker compose exec frontend npm install` |
| `Port 3000 is already in use` | `lsof -i :3000` 找出佔用進程 |

---

## 資料庫問題

### ❌ Alembic 遷移失敗

**症狀**：`alembic upgrade head` 執行失敗

**快速診斷**：
```bash
# 檢查 PostgreSQL 健康
docker compose ps postgres
docker compose exec postgres pg_isready -U quantlab

# 查看當前版本
docker compose exec backend alembic current

# 查看遷移歷史
docker compose exec backend alembic history
```

**常見錯誤**：

| 錯誤訊息 | 原因 | 解決方案 |
|---------|------|---------|
| `Target database is not up to date` | 遷移版本衝突 | `alembic downgrade -1` 後重新 upgrade |
| `relation "xxx" already exists` | 資料表已存在 | 檢查遷移腳本，移除重複的 create table |
| `cannot import name 'XXX'` | 模型未在 base.py 導入 | 在 `app/db/base.py` 添加 `from app.models.xxx import XXX` |

**參考文檔**：[Document/OPERATIONS_GUIDE.md#alembic-遷移失敗](Document/OPERATIONS_GUIDE.md)

---

### ❌ 產業指標計算返回 0 個結果

**症狀**：API 返回 `"indicators": []`

**原因**：`fundamental_data` 表使用季度字串（如 "2024-Q4"），不是日期格式

**解決方案**：
```python
# ❌ 錯誤：使用 date.today()
metric_date = date.today()  # "2025-12-12"

# ✅ 正確：查詢最新季度
latest_quarter = db.execute(
    text("SELECT date FROM fundamental_data ORDER BY date DESC LIMIT 1")
).fetchone()[0]  # "2024-Q4"
```

**檢查資料**：
```bash
docker compose exec postgres psql -U quantlab quantlab -c \
  "SELECT DISTINCT date FROM fundamental_data ORDER BY date DESC LIMIT 10;"
```

**參考**：`backend/app/services/industry_service.py:142-244`

---

## 前端問題

### ❌ 前端白屏或 500 錯誤

**快速檢查**：
```bash
# 查看前端日誌
docker compose logs frontend --tail=100

# 檢查 API 連接
curl http://localhost:8000/health
```

**常見原因**：

| 症狀 | 解決方案 |
|------|---------|
| 白屏無錯誤 | 清理緩存：`./scripts/quick-clean.sh` |
| 500 Internal Server Error | 檢查後端日誌：`docker compose logs backend` |
| `Cannot read property of undefined` | 檢查 API 返回數據格式 |
| `Module not found` | `docker compose exec frontend npm install` |

---

### ❌ 前端緩存問題

**症狀**：
- 組件重命名後仍出現舊組件警告
- 代碼更新後未生效
- 頁面顯示異常

**快速解決**：
```bash
# 方案 1：快速清理（推薦）
./scripts/quick-clean.sh

# 方案 2：完整重建（最徹底）
docker compose down
docker compose build --no-cache frontend
docker compose up -d
```

**參考文檔**：[Document/OPERATIONS_GUIDE.md#前端緩存問題](Document/OPERATIONS_GUIDE.md)

---

### ❌ SVG 圖示顯示異常

**症狀**：SVG 圖示佔據整個螢幕

**原因**：Tailwind CSS 的 `w-{n}` 和 `h-{n}` 在 `<style scoped>` 中失效

**解決方案**：
```vue
<style scoped>
svg.w-4 {
  width: 1rem !important;
  height: 1rem !important;
  flex-shrink: 0;
}
</style>
```

**參考實作**：
- `frontend/pages/docs.vue:320-325`
- `frontend/pages/industry/index.vue:1052-1068`

---

### ❌ 前端導航後需重新登入

**症狀**：從某些頁面返回後 token 遺失

**原因**：使用 `<a href>` 觸發完整頁面重載，清除 Vue 狀態

**解決方案**：
```vue
<!-- ❌ 錯誤 -->
<a href="/dashboard">返回儀表板</a>

<!-- ✅ 正確 -->
<NuxtLink to="/dashboard">返回儀表板</NuxtLink>
```

---

## Celery 問題

### ❌ Worker 無法連接 Redis

**症狀**：
```
[ERROR] Consumer: Cannot connect to redis://redis:6379/0
```

**快速診斷**：
```bash
# 1. 確認 Redis 運行
docker compose ps redis

# 2. 測試連接
docker compose exec backend redis-cli -h redis ping

# 3. 檢查環境變數
docker compose exec backend env | grep CELERY
```

**解決方案**：
```bash
docker compose restart redis celery-worker
```

---

### ❌ 任務未執行

**症狀**：定時任務到時間未執行

**快速診斷**：
```bash
# 1. 確認 beat 運行
docker compose ps celery-beat

# 2. 查看 beat 日誌
docker compose logs celery-beat --tail=50

# 3. 確認任務已註冊
docker compose exec backend celery -A app.core.celery_app inspect registered
```

**解決方案**：
```bash
docker compose restart celery-beat
```

---

### ❌ 任務更新後無法載入

**症狀**：新增任務出現 `ImportError`

**原因**：
1. 任務未在 `app/tasks/__init__.py` 導出
2. Python cache 未清除

**解決方案**：
```bash
# 1. 檢查任務導出
cat backend/app/tasks/__init__.py

# 2. 清除 cache
docker compose exec celery-worker find /app -name __pycache__ -type d -exec rm -rf {} +

# 3. 重啟
docker compose restart celery-worker celery-beat

# 4. 驗證
docker compose exec backend celery -A app.core.celery_app inspect registered | grep my_new_task
```

**參考文檔**：[Document/CELERY_TASKS_GUIDE.md#任務更新後無法載入](Document/CELERY_TASKS_GUIDE.md)

---

## Qlib 問題

### ❌ Qlib 初始化失敗

**症狀**：
```
RuntimeError: Qlib is not initialized
```

**快速診斷**：
```bash
# 檢查環境變數
docker compose exec backend env | grep QLIB_DATA_PATH

# 檢查數據目錄
docker compose exec backend ls -la /data/qlib/tw_stock_v2/

# 檢查 volume 掛載
docker compose exec backend mount | grep qlib
```

**解決方案**：
```bash
# 確保環境變數正確
echo "QLIB_DATA_PATH=/data/qlib/tw_stock_v2" >> .env

# 重啟服務
docker compose restart backend
```

---

### ❌ 數據同步失敗

**症狀**：`sync-qlib-smart.sh` 執行失敗

**快速檢查**：
```bash
# 檢查資料庫是否有數據
docker compose exec postgres psql -U quantlab quantlab -c \
  "SELECT COUNT(*) FROM stock_prices LIMIT 5;"

# 檢查 Qlib 檔案權限
docker compose exec backend ls -la /data/qlib/tw_stock_v2/features/
```

**常見問題**：

| 錯誤 | 解決方案 |
|------|---------|
| `PermissionError` | `docker compose exec backend chmod -R 755 /data/qlib/` |
| `No data found` | 檢查資料庫是否有數據 |
| 速度過慢 | 使用 `--limit 100` 測試 |

**參考文檔**：[Document/QLIB_SYNC_GUIDE.md](Document/QLIB_SYNC_GUIDE.md)

---

## 權限問題

### ❌ 檔案權限錯誤

**症狀**：`Permission denied` 錯誤

**快速解決**：
```bash
# Python 檔案
chmod 644 backend/app/新檔案.py

# 目錄
chmod 755 backend/app/新目錄

# 批次處理
chmod -R a+r backend/app/
chmod -R a+X backend/app/
```

---

### ❌ Qlib 數據目錄權限

**症狀**：無法寫入 Qlib 數據

**解決方案**：
```bash
docker compose exec backend chmod -R 755 /data/qlib/tw_stock_v2/
```

---

## 效能問題

### ❌ API 響應緩慢

**快速診斷**：
```bash
# 檢查資料庫查詢效能
docker compose exec postgres psql -U quantlab quantlab -c \
  "SELECT query, calls, total_time, mean_time
   FROM pg_stat_statements
   ORDER BY mean_time DESC
   LIMIT 10;"
```

**常見原因**：

| 症狀 | 解決方案 |
|------|---------|
| 特定 API 慢 | 檢查是否缺少索引 |
| 所有 API 慢 | 檢查 Redis 是否運行 |
| 首次請求慢 | 正常（快取未命中） |

---

### ❌ 資料庫查詢慢

**優化步驟**：
```sql
-- 1. 分析查詢計劃
EXPLAIN ANALYZE SELECT * FROM strategies WHERE user_id = 1;

-- 2. 檢查索引使用
SELECT * FROM pg_indexes WHERE tablename = 'strategies';

-- 3. 創建缺失的索引
CREATE INDEX idx_strategies_user_id ON strategies(user_id);
```

---

## 🔧 開發常見問題

### ❌ Vue 模板編譯錯誤

**症狀**：
```
[vue/compiler-sfc] Unexpected token, expected "}"
```

**原因**：Python f-string 的 `$` 被 Vue 誤認為模板插值

**解決方案**：
```javascript
// ❌ 錯誤
code: `print(f'價格 ${order.price:.2f}')`

// ✅ 正確：使用單反斜線轉義
code: `print(f'價格 \${order.price:.2f}')`
```

**受影響檔案**：
- `frontend/components/StrategyTemplates.vue`
- `frontend/components/QlibStrategyTemplates.vue`

---

### ❌ Pydantic RecursionError

**症狀**：Schema 出現遞迴錯誤

**解決方案**：
1. 避免使用過於複雜的 Field 描述
2. 簡化 schema 定義
3. 檢查是否有循環引用

---

## 📞 獲取幫助

### 快速查詢流程

```
1. 查看本文件 (TROUBLESHOOTING.md) ← 你在這裡
   ↓ 未找到解決方案
2. 查看相關操作指南 (Document/OPERATIONS_GUIDE.md)
   ↓ 未找到解決方案
3. 查看詳細文檔 (Document/ 目錄)
   ↓ 未找到解決方案
4. 查看日誌尋找線索 (docker compose logs)
   ↓ 未找到解決方案
5. 提交 GitHub Issue
```

### 日誌查詢命令

```bash
# 後端日誌（最近 100 行）
docker compose logs backend --tail=100

# 前端日誌
docker compose logs frontend --tail=100

# Celery worker 日誌
docker compose logs celery-worker --tail=100

# 所有錯誤日誌
docker compose logs | grep -i error

# 最近 1 小時的日誌
docker compose logs --since 1h backend
```

## 相關文檔

- [README.md](README.md) - 快速開始
- [Document/OPERATIONS_GUIDE.md](Document/OPERATIONS_GUIDE.md) - 完整操作手冊
- [Document/DEVELOPMENT_GUIDE.md](Document/DEVELOPMENT_GUIDE.md) - 開發指南
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - 專案結構索引
