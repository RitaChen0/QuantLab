# QuantLab 資料庫維護指南

**最後更新**: 2025-12-03
**維護人員**: System Administrator

---

## 📋 目錄

1. [資料庫當前狀態](#資料庫當前狀態)
2. [定期備份策略](#定期備份策略)
3. [重要資料表說明](#重要資料表說明)
4. [資料匯入腳本](#資料匯入腳本)
5. [資料庫還原步驟](#資料庫還原步驟)
6. [維護注意事項](#維護注意事項)

---

## 📊 資料庫當前狀態

### 系統資訊
- **資料庫**: PostgreSQL 15 + TimescaleDB
- **容器名稱**: `quantlab-postgres`
- **資料庫名稱**: `quantlab`
- **使用者**: `quantlab`
- **資料位置**: Docker Volume `postgres_data`

### 資料統計 (2025-12-03)

| 資料表 | 記錄數 | 說明 |
|--------|--------|------|
| **stocks** | 2,671 | 台股完整清單 |
| **industries** | 41 | TWSE 產業分類 (3層架構) |
| **stock_industries** | 1,935 | 股票-產業對應 (從 FinLab 匯入) |
| **stock_prices** | ~100萬+ | 歷史股價 (TimescaleDB Hypertable) |
| **fundamental_data** | ~10萬+ | 基本面財務數據 |
| **users** | 多筆 | 使用者帳號 |
| **strategies** | 多筆 | 交易策略 |
| **backtests** | 多筆 | 回測記錄 |

### 產業分類覆蓋率
- ✅ **1,935 / 2,671 檔股票** 已分類 (72.5%)
- ⚠️ 未分類: 736 檔 (主要為 ETF、特別股等)

---

## 💾 定期備份策略

### 自動備份腳本

創建 `/data/CCTest/QuantLab/scripts/backup_database.sh`:

```bash
#!/bin/bash
# QuantLab 資料庫備份腳本

BACKUP_DIR="/data/CCTest/QuantLab/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="quantlab_backup_${TIMESTAMP}.sql"

# 創建備份目錄
mkdir -p "$BACKUP_DIR"

# 執行備份 (包含所有資料表)
docker compose exec -T postgres pg_dump -U quantlab quantlab > "${BACKUP_DIR}/${BACKUP_FILE}"

# 壓縮備份檔案
gzip "${BACKUP_DIR}/${BACKUP_FILE}"

echo "✅ 備份完成: ${BACKUP_FILE}.gz"

# 只保留最近 30 天的備份
find "$BACKUP_DIR" -name "quantlab_backup_*.sql.gz" -mtime +30 -delete

echo "✅ 清理舊備份完成"
```

### 核心資料備份 (僅產業分類)

```bash
#!/bin/bash
# 僅備份產業分類相關資料表

BACKUP_DIR="/data/CCTest/QuantLab/backups/industries"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

mkdir -p "$BACKUP_DIR"

# 備份產業分類資料表
docker compose exec -T postgres pg_dump -U quantlab quantlab \
  -t industries -t stock_industries \
  > "${BACKUP_DIR}/industries_${TIMESTAMP}.sql"

gzip "${BACKUP_DIR}/industries_${TIMESTAMP}.sql"

echo "✅ 產業分類備份完成"
```

### 建議備份頻率

| 資料類型 | 備份頻率 | 保留期限 |
|---------|---------|---------|
| **完整資料庫** | 每週日 | 30 天 |
| **產業分類** | 每次更新後 | 永久 |
| **股價資料** | 每日 | 7 天 |
| **使用者資料** | 每日 | 30 天 |

---

## 📁 重要資料表說明

### 1. `industries` - 產業分類主表

```sql
-- 結構
CREATE TABLE industries (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,      -- 產業代碼 (M01, M1301 等)
    name_zh VARCHAR(100) NOT NULL,         -- 中文名稱
    name_en VARCHAR(100),                  -- 英文名稱
    parent_code VARCHAR(20),               -- 父產業代碼
    level INTEGER NOT NULL,                -- 階層 (1, 2, 3)
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- 資料來源: TWSE 官方產業分類
-- 初始化腳本: /backend/scripts/populate_industries.py
```

**重要性**: ⭐⭐⭐⭐⭐ (不可刪除,系統核心資料)

### 2. `stock_industries` - 股票-產業對應表

```sql
-- 結構
CREATE TABLE stock_industries (
    id SERIAL PRIMARY KEY,
    stock_id VARCHAR(10) NOT NULL,         -- 股票代號
    industry_code VARCHAR(20) NOT NULL,    -- 產業代碼
    is_primary BOOLEAN DEFAULT FALSE,      -- 是否為主要產業
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(stock_id, industry_code)
);

-- 資料來源: FinLab API (company_basic_info)
-- 匯入腳本: /backend/scripts/import_finlab_industries.py
-- 最後更新: 2025-12-03
```

**重要性**: ⭐⭐⭐⭐⭐ (核心業務資料,需定期備份)

### 3. `stocks` - 股票主表

```sql
-- 結構
CREATE TABLE stocks (
    stock_id VARCHAR(10) PRIMARY KEY,      -- 股票代號
    name VARCHAR(100) NOT NULL,            -- 股票名稱
    category VARCHAR(50),                  -- 市場類別
    market VARCHAR(20),                    -- 市場 (sii, otc)
    is_active VARCHAR(10) NOT NULL,        -- 是否活躍
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 資料來源: FinLab API
-- 同步任務: sync_stock_list (Celery, 每日 8:00)
```

**重要性**: ⭐⭐⭐⭐⭐ (系統基礎資料)

### 4. `stock_prices` - 股價歷史 (TimescaleDB)

```sql
-- TimescaleDB Hypertable
-- 資料來源: FinLab API
-- 同步任務: sync_daily_prices, sync_ohlcv_data
-- 資料量: 極大 (~百萬筆級別)
```

**重要性**: ⭐⭐⭐⭐ (可重新同步,但耗時)

---

## 🔧 資料匯入腳本

### 產業分類資料匯入

**腳本位置**: `/backend/scripts/import_finlab_industries.py`

**功能**:
- 從 FinLab API 取得完整股票產業分類
- 自動對應 FinLab 產業名稱到 TWSE 產業代碼
- 批次匯入到 `stock_industries` 資料表
- 自動清除舊資料並重新匯入

**執行方式**:
```bash
cd /data/CCTest/QuantLab/backend
docker compose exec backend python scripts/import_finlab_industries.py
```

**執行時機**:
- ✅ 首次安裝系統
- ✅ 產業分類資料有更新
- ✅ 資料庫重建後
- ⚠️ 不建議頻繁執行 (資料相對穩定)

**注意事項**:
1. 需要有效的 `FINLAB_API_TOKEN`
2. 會清除現有的 `stock_industries` 資料
3. 執行時間約 30-60 秒
4. 自動處理股票不存在的情況

---

## 🔄 資料庫還原步驟

### 完整還原

```bash
# 1. 停止所有服務
docker compose down

# 2. 清除現有資料 (⚠️ 危險操作)
docker volume rm quantlab_postgres_data

# 3. 重新啟動資料庫
docker compose up -d postgres

# 4. 等待資料庫啟動
sleep 10

# 5. 還原備份
gunzip -c /data/CCTest/QuantLab/backups/quantlab_backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose exec -T postgres psql -U quantlab quantlab

# 6. 啟動所有服務
docker compose up -d
```

### 僅還原產業分類資料

```bash
# 1. 還原備份
gunzip -c /data/CCTest/QuantLab/backups/industries/industries_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose exec -T postgres psql -U quantlab quantlab

# 2. 驗證資料
docker compose exec postgres psql -U quantlab quantlab -c \
  "SELECT COUNT(*) FROM stock_industries;"
```

### 重新匯入產業分類 (不需備份)

```bash
# 直接從 FinLab 重新匯入
docker compose exec backend python scripts/import_finlab_industries.py
```

---

## ⚠️ 維護注意事項

### DO ✅

1. **定期備份核心資料**
   - 每週備份完整資料庫
   - 每次更新產業分類後備份

2. **監控磁碟空間**
   ```bash
   docker system df -v
   df -h /var/lib/docker
   ```

3. **定期檢查資料完整性**
   ```bash
   # 檢查產業分類覆蓋率
   docker compose exec postgres psql -U quantlab quantlab -c "
   SELECT
     (SELECT COUNT(*) FROM stock_industries) as mapped_stocks,
     (SELECT COUNT(*) FROM stocks) as total_stocks,
     ROUND(100.0 * (SELECT COUNT(*) FROM stock_industries) /
           (SELECT COUNT(*) FROM stocks), 2) as coverage_percent;
   "
   ```

4. **保留匯入腳本**
   - `/backend/scripts/import_finlab_industries.py` 永久保存
   - 不要修改核心邏輯
   - 如需調整對應規則,僅修改 `INDUSTRY_MAPPING` 字典

5. **記錄重要操作**
   - 每次資料匯入記錄時間和結果
   - 保留操作日誌

### DON'T ❌

1. **不要手動修改產業分類資料**
   - ❌ 不要直接 SQL UPDATE `stock_industries`
   - ✅ 使用腳本重新匯入

2. **不要刪除 Docker Volume**
   - ❌ `docker volume rm quantlab_postgres_data` (除非確定要清空)
   - ✅ 只刪除容器: `docker compose down` (保留資料)

3. **不要在生產環境執行未測試的 SQL**
   - ❌ 直接執行 `DELETE FROM stocks`
   - ✅ 先在測試環境驗證

4. **不要忽略資料庫錯誤日誌**
   ```bash
   docker compose logs postgres | grep -i error
   ```

5. **不要在匯入過程中中斷**
   - 如果中斷,重新執行完整匯入腳本

---

## 📋 維護檢查清單

### 每週檢查 (週日)

- [ ] 執行完整資料庫備份
- [ ] 檢查備份檔案是否正常
- [ ] 檢查磁碟空間使用率
- [ ] 查看資料庫錯誤日誌

### 每月檢查

- [ ] 驗證產業分類資料完整性
- [ ] 清理超過 30 天的備份檔案
- [ ] 檢查 TimescaleDB 壓縮狀態
- [ ] 更新此維護文檔

### 系統更新後

- [ ] 執行 Alembic 資料庫遷移
- [ ] 驗證所有資料表結構
- [ ] 檢查產業分類資料是否正常
- [ ] 重新測試 API 端點

---

## 🆘 緊急聯絡資訊

### 資料庫問題排查

1. **連線問題**
   ```bash
   docker compose ps postgres
   docker compose logs postgres
   ```

2. **資料遺失**
   - 檢查最近的備份檔案
   - 使用還原步驟恢復

3. **效能問題**
   ```bash
   docker compose exec postgres psql -U quantlab quantlab -c "
   SELECT * FROM pg_stat_activity WHERE state = 'active';
   "
   ```

### 重要檔案位置

| 檔案 | 路徑 |
|-----|------|
| 產業匯入腳本 | `/backend/scripts/import_finlab_industries.py` |
| 資料庫備份 | `/data/CCTest/QuantLab/backups/` |
| Docker Compose | `/data/CCTest/QuantLab/docker-compose.yml` |
| 環境變數 | `/data/CCTest/QuantLab/.env` |
| Alembic 遷移 | `/backend/alembic/versions/` |

---

## 📝 更新歷史

| 日期 | 操作 | 說明 |
|-----|------|------|
| 2025-12-03 | 產業分類資料匯入 | 從 FinLab 匯入 1,935 筆股票-產業對應 |
| 2025-12-03 | 建立維護文檔 | 創建此維護指南 |

---

**維護原則**: 預防勝於治療,備份重於一切!

**聯絡人**: 系統管理員
**最後檢查**: 2025-12-03
