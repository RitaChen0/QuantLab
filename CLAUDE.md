# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> QuantLab 台股量化交易平台 - 開發指南

## 🚀 常用開發命令

### Docker 容器管理

```bash
# 啟動所有服務（6 個容器）
docker compose up -d

# 重啟特定服務（代碼變更後）
docker compose restart backend
docker compose restart celery-worker celery-beat

# 查看日誌（即時追蹤）
docker compose logs -f backend
docker compose logs -f celery-worker

# 進入容器執行命令
docker compose exec backend bash
docker compose exec postgres psql -U quantlab quantlab
```

### 資料庫操作

```bash
# 執行遷移（部署新版本時必須）
docker compose exec backend alembic upgrade head

# 創建新遷移（修改 models/ 後）
docker compose exec backend alembic revision --autogenerate -m "描述變更"

# 查看遷移歷史
docker compose exec backend alembic history

# 直接查詢資料庫
docker compose exec postgres psql -U quantlab quantlab -c "SELECT COUNT(*) FROM users;"
```

### Qlib 數據同步

```bash
# 智慧增量同步（日線資料，1-5 分鐘）
bash scripts/sync-qlib-smart.sh

# 測試模式（僅同步 10 檔股票）
bash scripts/sync-qlib-smart.sh --test

# 手動完整重新導出（30-60 分鐘，少用）
docker compose exec backend python /app/scripts/export_to_qlib_v2.py \
  --output-dir /data/qlib/tw_stock_v2 --stocks all
```

### Shioaji 分鐘線同步

```bash
# 定時任務（每天 15:00 自動執行）
# 位置：backend/app/core/celery_app.py "sync-shioaji-minute-daily"

# 手動觸發同步
docker compose exec backend python /app/scripts/sync_shioaji_to_qlib.py --smart

# 測試模式（5 檔股票）
docker compose exec backend python /app/scripts/sync_shioaji_to_qlib.py --smart --test
```

### 資料庫完整性檢查（重要！）

```bash
# 🏥 快速檢查（推薦每日執行）
bash scripts/db-integrity-check.sh

# 檢查並自動修復
bash scripts/db-integrity-check.sh --fix

# 或使用 Python 腳本（更多選項）
# 完整檢查（日線 + 分鐘線 + Qlib）
docker compose exec backend python /app/scripts/check_database_integrity.py --check-all

# 檢查並自動修復所有缺失
docker compose exec backend python /app/scripts/check_database_integrity.py --fix-all

# 只檢查特定類型
docker compose exec backend python /app/scripts/check_database_integrity.py --check-daily
docker compose exec backend python /app/scripts/check_database_integrity.py --check-minute

# 生成報告
docker compose exec backend python /app/scripts/check_database_integrity.py --check-all --report
```

**自動檢查**：系統每天 06:00 和 06:30 自動執行檢查和修復（Celery 定時任務）

### 日線缺失補齊

```bash
# 🧠 智慧模式（推薦）：自動檢測分鐘線範圍內的所有缺失
docker compose exec backend python /app/scripts/backfill_daily_from_minute.py --smart

# 智慧檢查（不修復）
docker compose exec backend python /app/scripts/backfill_daily_from_minute.py --smart --check

# 智慧預覽（不寫入）
docker compose exec backend python /app/scripts/backfill_daily_from_minute.py --smart --dry-run

# 補齊特定日期
docker compose exec backend python /app/scripts/backfill_daily_from_minute.py --date 2025-12-23

# 補齊日期範圍
docker compose exec backend python /app/scripts/backfill_daily_from_minute.py \
  --start 2025-12-19 --end 2025-12-24
```

### 選擇權數據回補

```bash
# 回補選擇權歷史數據（使用 Shioaji API 獲取真實價格並計算 Greeks）
# 測試模式（3 天，不寫入資料庫）
docker compose exec backend python /app/scripts/backfill_option_data.py \
  --underlying TX \
  --days-back 3 \
  --dry-run

# 實際回補最近 7 天
docker compose exec backend python /app/scripts/backfill_option_data.py \
  --underlying TX \
  --days-back 7

# 回補完整 90 天（需時 2-3 小時）
docker compose exec backend python /app/scripts/backfill_option_data.py \
  --underlying TX \
  --days-back 90

# 指定日期範圍
docker compose exec backend python /app/scripts/backfill_option_data.py \
  --underlying TX \
  --start-date 2025-09-16 \
  --end-date 2025-12-15

# 驗證選擇權數據品質
bash /home/ubuntu/QuantLab/verify_option_quality.sh
```

**重要說明**：
- MTX (小台期貨) **沒有選擇權產品**，僅 TX (台指期貨) 有 TXO (台指選擇權)
- 回補腳本會計算真實的 Black-Scholes Greeks（Delta, Gamma, Theta, Vega, Rho, Vanna）
- 數據品質驗證會檢查 Greeks 是否為真實計算而非估算值
- 回補過程中會自動處理 API 限制並重試

### Celery 任務管理

```bash
# 查看已註冊任務
docker compose exec backend celery -A app.core.celery_app inspect registered

# 查看定時任務清單
docker compose exec backend celery -A app.core.celery_app inspect scheduled

# 查看活動任務
docker compose exec backend celery -A app.core.celery_app inspect active

# 檢查 revoked tasks（被撤銷的任務）
docker compose exec backend celery -A app.core.celery_app inspect revoked

# 手動觸發任務
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_stock_list

# 手動清理 Celery 元數據
docker compose exec backend celery -A app.core.celery_app call app.tasks.cleanup_celery_metadata

# 清空任務隊列（開發環境）
docker compose exec redis redis-cli FLUSHDB
```

### 測試

```bash
# 執行所有測試
docker compose exec backend pytest

# 執行特定測試檔案
docker compose exec backend pytest tests/services/test_shioaji_client.py

# 執行特定測試函數
docker compose exec backend pytest tests/test_auth.py::test_register

# 執行帶標記的測試（見 pytest.ini）
docker compose exec backend pytest -m unit        # 快速單元測試
docker compose exec backend pytest -m integration # 整合測試
docker compose exec backend pytest -m futures     # 期貨相關測試

# 顯示測試覆蓋率
docker compose exec backend pytest --cov=app --cov-report=html
```

### 開發工具

```bash
# Python 代碼格式化
docker compose exec backend black app/
docker compose exec backend flake8 app/ --max-line-length=88

# 前端 Linting
docker compose exec frontend npm run lint
docker compose exec frontend npm run lint:fix

# 清理前端快取（更新後無變化時）
bash scripts/quick-clean.sh
docker compose restart frontend
```

### 速率限制重置

```bash
# 開發時重置速率限制
bash scripts/reset-rate-limit.sh

# 或手動清除 Redis
docker compose exec redis redis-cli --scan --pattern "slowapi:*" | xargs docker compose exec -T redis redis-cli del
```

---

## 🏗️ 高層架構

### 系統概覽

**定位**：台股量化交易平台（雙引擎 Backtrader + Qlib）

**核心特色**：
- 雙量化引擎（技術指標 + 機器學習）
- AI 因子挖掘（RD-Agent + LLM）
- 完整數據管道（日線 + 分鐘線）

### 容器架構（6 個服務）

```
┌─────────────────────────────────────────────────────────┐
│  frontend (3000)      ←→   backend (8000)               │
│  Nuxt.js 3                  FastAPI + SQLAlchemy       │
└─────────────────────────────────────────────────────────┘
           ↓                         ↓
    ┌──────────────┐         ┌──────────────┐
    │   postgres   │         │    redis     │
    │ TimescaleDB  │         │ Cache + MQ   │
    └──────────────┘         └──────────────┘
                                     ↓
                         ┌──────────────────────┐
                         │  celery-worker       │
                         │  celery-beat         │
                         │  定時任務 + 異步處理  │
                         └──────────────────────┘
```

### 後端四層架構

**關鍵原則**：嚴格分層，禁止跨層調用

```
app/
├── api/v1/          # 🌐 HTTP 路由層
│   ├── strategies.py      - 調用 StrategyService
│   └── backtests.py       - 調用 BacktestService
│   （職責：請求處理、依賴注入、錯誤處理）
│   （禁止：業務邏輯、直接查詢資料庫）
│
├── services/        # 💼 業務邏輯層
│   ├── strategy_service.py    - 策略驗證、配額檢查
│   └── backtest_service.py    - 回測執行、結果計算
│   （職責：業務邏輯、數據驗證、調用 Repository）
│   （禁止：直接操作 ORM、HTTP 處理）
│
├── repositories/    # 🗄️ 資料訪問層
│   ├── strategy.py        - CRUD、查詢建構
│   └── backtest.py        - 事務管理
│   （職責：資料庫操作、查詢優化）
│   （禁止：業務邏輯）
│
├── models/          # 📊 ORM 模型（SQLAlchemy）
├── schemas/         # 📋 API Schema（Pydantic）
├── tasks/           # ⚙️ Celery 異步任務
└── core/            # 🔧 核心配置
```

**新增功能時的正確流程**：
1. 定義 `models/` 和 `schemas/`
2. 實作 `repositories/` 的資料訪問方法
3. 實作 `services/` 的業務邏輯
4. 實作 `api/v1/` 的路由端點
5. 執行 `alembic revision --autogenerate`

### 雙引擎數據架構

**關鍵設計**：PostgreSQL 為單一真實來源，Qlib 為高效能快取

#### 日線資料流

```
FinLab API → PostgreSQL (stock_prices) → Qlib 二進制
                ↓                            ↓
           永久保存                    快 3-10 倍
        (2007 至今)                  (智慧增量同步)
```

**同步邏輯**（export_to_qlib_v2.py）：
- ✅ 只檢查 Qlib 最後日期
- ✅ 從 PostgreSQL 讀取缺失範圍
- ✅ 單向同步：PG → Qlib

#### 分鐘線資料流

```
                    Shioaji API
                         ↓
         ┌───────────────┴───────────────┐
         ↓                               ↓
    PostgreSQL                         Qlib
(stock_minute_prices)          (tw_stock_minute/)
  保留 6 個月                      保留 7 年
 (TimescaleDB)                   (18 GB 二進制)
```

**同步邏輯**（sync_shioaji_to_qlib.py）：
- ✅ 檢查 PostgreSQL 和 Qlib 最後日期
- ✅ 取較早日期作為起點（確保兩邊最終一致）
- ✅ 雙向同步：API → [PG, Qlib]

**定時任務**：每天 15:00 執行（`sync-shioaji-minute-daily`）

#### 期貨資料流

```
                    Shioaji API
                         ↓
         ┌───────────────┴───────────────┐
         ↓                               ↓
    PostgreSQL                         Qlib
(stock_minute_prices)          (tw_stock_minute/)
   月份合約數據                    連續合約數據
   (TX202512)                      (TXCONT)
```

**月份合約 → 連續合約流程**：
1. **註冊合約**：`scripts/register_futures_contracts.py` 註冊 TX/MTX 月份合約到 stocks 表
2. **同步數據**：`sync-shioaji-futures-daily` 任務每天 15:30 同步月份合約分鐘線
3. **生成連續合約**：`generate-continuous-contracts-weekly` 任務每週六 18:00 拼接為連續合約
4. **自動註冊新年度**：每年 1/1 00:05 自動註冊下一年度月份合約

**關鍵概念**：
- **月份合約**（TX202512）：實際交易的合約，每月第三個週三結算
- **連續合約**（TXCONT）：拼接多個月份合約，用於長期回測
- **換月邏輯**：結算日前 3 天自動切換到下月合約

#### 選擇權資料流

```
                    Shioaji API
                         ↓
                  ┌──────┴──────┐
                  ↓             ↓
            合約快照        歷史價格
                  ↓             ↓
         Black-Scholes     選擇權因子
           Greeks 計算      (option_daily_factors)
                  ↓
            PostgreSQL
```

**選擇權數據特性**：
- **標的限制**：僅 TX (台指期貨) 有選擇權，MTX (小台) **無選擇權產品**
- **數據來源**：Shioaji API TXO (台指選擇權) 合約
- **Greeks 計算**：使用 Black-Scholes 模型計算 Delta, Gamma, Theta, Vega, Rho, Vanna
- **因子儲存**：`option_daily_factors` 表（PCR, ATM IV, Greeks 彙總）
- **品質保證**：真實計算 vs 估算值（delta_iv_ratio != 0.10）

**回補流程**（backfill_option_data.py）：
1. 獲取特定日期的有效選擇權合約（過濾即將到期）
2. 批次獲取合約快照（價格、履約價、類型）
3. 計算每個合約的隱含波動率和 Greeks
4. 彙總為每日因子並儲存
5. 自動重試處理 API 限制

### Qlib 數據格式

**位置**：
- 日線：`/data/qlib/tw_stock_v2/`
- 分鐘線：`/data/qlib/tw_stock_minute/`

**目錄結構**（Qlib v2 官方格式）：
```
features/
├── 2330/
│   ├── open.day.bin       # float32 陣列
│   ├── high.day.bin
│   ├── low.day.bin
│   ├── close.day.bin
│   ├── volume.day.bin
│   └── factor.day.bin
└── calendars/
    └── day.txt            # 交易日曆
```

**使用 FileFeatureStorage API**（確保格式正確）：
```python
from qlib.data.storage.file_storage import FileFeatureStorage

storage = FileFeatureStorage(instrument="2330", field="close", freq="day")
storage.write(data)  # numpy array
```

### Celery 定時任務（Celery Beat）

**時區配置**（⚠️ 關鍵）：
```python
# backend/app/core/celery_app.py
celery_app.conf.update(
    timezone="UTC",  # 統一使用 UTC 時區
    enable_utc=True,  # 啟用 UTC 模式

    # 任務確認策略（改善可靠性，減少任務丟失）
    task_acks_late=True,  # 任務執行完成後才確認
    task_reject_on_worker_lost=False,  # Worker 丟失時重新排隊任務

    # Worker 自動重啟（防止 revoked 列表積累和內存洩漏）
    worker_max_memory_per_child=512000,  # 512MB 後自動重啟

    # 結果自動過期
    result_expires=3600,  # 結果 1 小時後過期
)
```

**重要說明**：
- **所有時間使用 UTC**：Celery 配置為 `timezone="UTC"`, `enable_utc=True`
- **定時任務 crontab 使用 UTC 時間**：例如 `crontab(hour=21, minute=0)` 表示 UTC 21:00（台北時間隔天 05:00）
- **應用層時區轉換**：應用代碼使用 `datetime.now(timezone.utc)` 獲取 UTC 時間，必要時轉換為台灣時間
- **一致性策略**：資料庫、Celery、應用層全部統一使用 UTC，避免時區混亂
- 高頻任務（15 分鐘間隔）不應設置 `expires`，避免任務立即過期
- 詳見 [TIMEZONE_COMPLETE_GUIDE.md](TIMEZONE_COMPLETE_GUIDE.md) 和 [CELERY_REVOKED_TASKS_FIX.md](CELERY_REVOKED_TASKS_FIX.md)

**任務清單**（按時間排序）：
| 時間 | 任務 | 用途 |
|------|------|------|
| 03:00 | `cleanup_old_cache` | 清理 Redis 過期快取 |
| 05:00 | **`cleanup_celery_metadata`** | **清理 Celery 元數據（防止 revoked tasks 積累）** |
| 08:00 | `sync_stock_list` | 更新股票清單（FinLab） |
| 09:00-13:30 每 15 分 | `sync_latest_prices` | 即時價格（交易時段） |
| 15:00 | **`sync_shioaji_minute_data`** | **Shioaji 股票分鐘線（Top 50）** |
| 15:30 | **`sync_shioaji_futures`** | **Shioaji 期貨分鐘線（TX/MTX）** |
| 21:00 | `sync_daily_prices` | 每日價格（FinLab） |
| 21:00 | `sync_top_stocks_institutional` | 法人買賣超（Top 100） |
| 22:00 | `sync_ohlcv_data` | OHLCV 數據 |
| 23:00 | `sync_fundamental_latest` | 基本面（增量） |
| 週日 02:00 | `cleanup_old_institutional_data` | 清理舊法人資料 |
| 週日 04:00 | `sync_fundamental_data` | 基本面（完整） |
| 週六 18:00 | `generate_continuous_contracts` | 生成期貨連續合約 |
| 每年 1/1 00:05 | `register_new_futures_contracts` | 註冊新年度月份合約 |

**新增定時任務**：
```python
# backend/app/core/celery_app.py
celery_app.conf.beat_schedule = {
    "task-name": {
        "task": "app.tasks.your_task",
        "schedule": crontab(hour=15, minute=0),  # 每天 15:00
        "options": {"expires": 3600},
    },
}
```

### TimescaleDB 優化

**Hypertable**（自動分區）：
- `stock_prices` - 按 `date` 分區
- `stock_minute_prices` - 按 `datetime` 分區

**保留策略**（自動刪除舊資料）：
```sql
-- stock_minute_prices: 6 個月後自動刪除
SELECT add_retention_policy('stock_minute_prices', INTERVAL '6 months');

-- 查看策略
SELECT * FROM timescaledb_information.jobs WHERE proc_name = 'policy_retention';
```

**壓縮策略**（節省空間）：
```sql
-- 7 天後壓縮
SELECT add_compression_policy('stock_minute_prices', INTERVAL '7 days');
```

### RD-Agent 架構

**流程**：
```
用戶請求 → API 層 → Service 配置 RD-Agent
                      ↓
                Celery 異步執行
                      ↓
            生成 Qlib 表達式因子
                      ↓
         存入 generated_factors 表
                      ↓
         前端獲取結果並插入策略
```

**跨引擎整合**：
- **Backtrader**：自動轉換為 `bt.indicators`
- **Qlib**：直接插入 `QLIB_FIELDS` 陣列

**表結構**：
- `rdagent_tasks` - 任務記錄
- `generated_factors` - AI 生成的因子

---

## 🔑 關鍵設計決策

### 為何使用四層架構？

**問題**：早期代碼將業務邏輯寫在 API 路由中，難以測試和重用

**解決**：
- API 層只處理 HTTP，不含邏輯
- Service 層可被 API 和 Celery Task 共用
- Repository 層統一資料訪問，便於切換資料庫

**影響**：
- 新增功能時必須依序實作 Repository → Service → API
- 禁止 API 直接調用 Repository（會觸發 code review 警告）

### 為何需要雙引擎？

**Backtrader**：
- 目標：技術指標策略（MA、RSI、MACD）
- 優勢：簡單易學、文檔完整
- 用戶：個人交易者

**Qlib**：
- 目標：機器學習策略（GBDT、MLP、Transformer）
- 優勢：原生 ML 支援、表達式引擎
- 用戶：機構投資者

**互補而非競爭**：滿足不同需求層次

### 為何 Qlib 數據同步邏輯不同？

**日線**（export_to_qlib_v2.py）：
- PostgreSQL 永遠是最新（FinLab API 每日更新）
- Qlib 只是「匯出快照」
- 單向同步：PG → Qlib

**分鐘線**（sync_shioaji_to_qlib.py）：
- Shioaji API 是唯一來源
- PostgreSQL 和 Qlib 都是「同步目標」
- 需確保兩邊最終一致
- 雙向同步：API → [PG, Qlib]

### 為何期貨需要月份合約和連續合約？

**月份合約**（TX202512、MTX202501）：
- 真實交易合約，有結算日（每月第三個週三）
- 用於實盤交易、短期策略
- 問題：合約到期後無法繼續回測

**連續合約**（TXCONT、MTXCONT）：
- 拼接多個月份合約，無到期日
- 用於長期回測、策略開發
- 實現：結算日前 N 天自動切換到下月合約

**Backtrader 整合**：
- 自動檢測期貨代碼（TX/MTX）
- 應用對應手續費和保證金（`TXCommissionInfo`、`MTXCommissionInfo`）
- 支援期貨特有指標（持倉成本、保證金使用率）

---

## 📋 資料庫變更檢查清單

**修改 models/ 後必須執行**：

1. ✅ 創建遷移：`alembic revision --autogenerate -m "描述"`
2. ✅ 檢查生成的遷移檔案（`alembic/versions/`）
3. ✅ 測試遷移：`alembic upgrade head`
4. ✅ 測試回滾：`alembic downgrade -1`
5. ✅ 更新 `Document/DATABASE_SCHEMA_REPORT.md`

**完整檢查清單**：[Document/DATABASE_CHANGE_CHECKLIST.md](Document/DATABASE_CHANGE_CHECKLIST.md)（56 項）

---

## 🐛 常見開發陷阱

### 1. Celery 時區配置

**✅ 當前配置（正確）**：
```python
# backend/app/core/celery_app.py
celery_app.conf.update(
    timezone="UTC",  # 統一使用 UTC
    enable_utc=True,  # 啟用 UTC 模式
)
```

**重要**：
- **不要修改為 `timezone="Asia/Taipei"` 和 `enable_utc=False`**
- 系統已統一使用 UTC 時區（資料庫、Celery、應用層）
- crontab 時間為 UTC 時間，例如 `crontab(hour=21, minute=0)` = UTC 21:00 = 台北時間隔天 05:00
- 使用 `datetime.now(timezone.utc)` 獲取當前 UTC 時間
- 必要時使用 `timezone_helpers.py` 中的函數進行時區轉換

### 2. 前端快取未更新

**症狀**：修改代碼後前端無變化

**解決**：
```bash
bash scripts/quick-clean.sh
docker compose restart frontend
```

### 3. Qlib 同步速度慢

**錯誤做法**：使用完整重新導出（30-60 分鐘）

**正確做法**：使用智慧增量同步（1-5 分鐘）
```bash
bash scripts/sync-qlib-smart.sh
```

### 4. 速率限制阻擋開發

**症狀**：API 返回 429 Too Many Requests

**解決**：
```bash
bash scripts/reset-rate-limit.sh
```

### 5. TimescaleDB 資料被自動刪除

**症狀**：`stock_minute_prices` 只有 6 個月資料

**原因**：設定了保留策略（預設行為）

**檢查**：
```sql
SELECT * FROM timescaledb_information.jobs WHERE proc_name = 'policy_retention';
```

### 6. 期貨回測失敗或手續費異常

**症狀**：期貨策略回測結果不正確

**檢查項目**：
1. 合約代碼格式：TX/MTX 會自動套用期貨手續費，TXCONT/MTXCONT 為連續合約
2. 數據可用性：確認 Qlib 是否有對應合約數據
3. 結算日處理：月份合約在結算日後會標記為 `inactive`

**驗證**：
```bash
# 檢查期貨合約是否已註冊
docker compose exec postgres psql -U quantlab quantlab -c \
  "SELECT stock_id, name, is_active FROM stocks WHERE category = 'FUTURES_MONTHLY' ORDER BY stock_id DESC LIMIT 10;"

# 檢查連續合約數據
docker compose exec backend ls -lh /data/qlib/tw_stock_minute/features/TXCONT/
```

### 7. 日誌格式不統一導致搜尋困難

**症狀**：無法快速定位特定類型的日誌

**解決**：使用標準化日誌前綴進行搜尋
```bash
# 搜尋期貨相關日誌
docker compose logs backend | grep "\[FUTURES\]"

# 搜尋合約處理日誌
docker compose logs backend | grep "\[CONTRACT\]"

# 搜尋 Celery 任務日誌
docker compose logs celery-worker | grep "\[TASK\]"

# 搜尋合約註冊日誌
docker compose logs backend | grep "\[REGISTER\]"

# 搜尋告警日誌
docker compose logs backend | grep "\[ALERT\]"
```

**告警檔案位置**：
- 告警 JSON：`/tmp/quantlab_alerts/*.json`
- 任務日誌：`/tmp/futures_logs/*.log`

### 8. 選擇權回測零交易

**症狀**：Delta Neutral 等選擇權策略回測顯示 COMPLETED 但交易次數為 0

**常見原因**：
1. **使用 MTX**：小台期貨沒有選擇權產品 → 改用 TX
2. **Greeks 數據缺失**：`avg_call_delta`, `avg_put_delta` 為 NULL
3. **Greeks 為估算值**：delta_iv_ratio = 0.10（非真實計算）
4. **歷史數據不足**：策略需要至少 10 天數據，但只有 2-3 天

**診斷步驟**：
```bash
# 1. 檢查選擇權因子數據
docker compose exec postgres psql -U quantlab quantlab -c "
SELECT date, avg_call_delta, avg_put_delta,
       ROUND((avg_call_delta - 0.5) / NULLIF(atm_iv, 0), 3) as delta_iv_ratio
FROM option_daily_factors
WHERE underlying_id = 'TX'
ORDER BY date DESC LIMIT 5;"

# 2. 檢查期貨數據範圍
docker compose exec postgres psql -U quantlab quantlab -c "
SELECT stock_id, MIN(datetime::date), MAX(datetime::date), COUNT(DISTINCT datetime::date)
FROM stock_minute_prices
WHERE stock_id IN ('TX', 'TXCONT')
GROUP BY stock_id;"

# 3. 驗證數據品質
bash /home/ubuntu/QuantLab/verify_option_quality.sh
```

**解決方案**：
```bash
# 清除估算值並重新回補真實 Greeks
docker compose exec postgres psql -U quantlab quantlab -c "
UPDATE option_daily_factors
SET avg_call_delta = NULL, avg_put_delta = NULL,
    gamma_exposure = NULL, vanna_exposure = NULL
WHERE underlying_id = 'TX'
  AND ABS((avg_call_delta - 0.5) / NULLIF(atm_iv, 0) - 0.10) < 0.001;"

# 回補真實選擇權數據
docker compose exec backend python /app/scripts/backfill_option_data.py \
  --underlying TX --days-back 90
```

### 9. Celery Worker 被卡住

**症狀**：新的回測任務一直處於 PENDING 狀態

**原因**：Worker 被長時間運行的任務（如 Greeks 計算）阻塞

**診斷**：
```bash
# 檢查活動任務
docker compose exec backend celery -A app.core.celery_app inspect active

# 檢查隊列長度
docker compose exec redis redis-cli LLEN celery
```

**解決**：
```bash
# 停止 Worker
docker compose stop celery-worker celery-beat

# 清空 Redis 隊列
docker compose exec redis redis-cli FLUSHDB

# 重啟 Worker
docker compose start celery-worker celery-beat
```

### 10. Celery 任務被標記為 Revoked

**症狀**：所有定時任務顯示 "尚未執行"，日誌顯示 `Discarding revoked task`

**原因**：
1. **Beat 重啟補發機制**：Beat 重啟後補發所有逾期任務，但這些任務的 `expires` 時間早已過期
2. **Worker 標記為 revoked**：Worker 正確地將過期任務標記為 REVOKED
3. **內存積累**：Revoked task IDs 在 Worker 內存中積累，重啟前無法清除

**診斷**：
```bash
# 檢查 revoked 列表
docker compose exec backend celery -A app.core.celery_app inspect revoked

# 檢查 Worker 配置
docker compose exec backend celery -A app.core.celery_app inspect conf | grep -E "(task_acks_late|result_expires|worker_max_memory_per_child)"
```

**解決方案**：
1. **立即修復**：重啟 Worker 清空 revoked 列表
```bash
docker compose restart celery-worker celery-beat
```

2. **永久修復**（✅ 2025-12-23 已優化）：
   - **智慧 expires 配置**：
     - 每日任務：`expires: 82800`（23 小時）
     - 每週任務：`expires: 604800`（7 天）
     - 高頻任務（15 分鐘）：**無 expires**
     - 長時間任務：`expires: 18000`（5 小時，例如同步所有股票）
   - **三層防護機制**：
     1. 充足的 expires 時間（覆蓋整個任務週期）
     2. `@skip_if_recently_executed` 裝飾器去重
     3. Redis 分佈式鎖防止並發
   - `task_acks_late=True` - 改善任務可靠性
   - `worker_max_memory_per_child=512000` - Worker 定期自動重啟，清空 revoked 列表
   - 每天 05:00 自動執行 `cleanup_celery_metadata` 任務

**驗證**：
```bash
# 檢查 revoked 列表應該為空
docker compose exec backend celery -A app.core.celery_app inspect revoked
# 預期輸出：-> celery@xxx: OK
#            - empty -
```

**詳細說明**：
- [CELERY_REVOKED_TASKS_FIX.md](CELERY_REVOKED_TASKS_FIX.md) - Revoked Tasks 問題分析
- [CELERY_EXPIRES_OPTIMIZATION.md](CELERY_EXPIRES_OPTIMIZATION.md) - Expires 智慧優化（2025-12-23）
- [CELERY_SMART_REVOKED_CLEANUP.md](CELERY_SMART_REVOKED_CLEANUP.md) - 智慧 Revoked 清理機制（2025-12-23）✨

---

## ⏰ 時區處理規範

### 系統時區策略

**核心原則**：統一使用 UTC 時區儲存和處理時間

- **資料庫**：所有 datetime 欄位使用 `TIMESTAMPTZ`（timezone-aware）
- **應用層**：使用 `datetime.now(timezone.utc)` 或 `timezone_helpers.now_utc()`
- **Celery**：配置為 `timezone="UTC"`, `enable_utc=True`
- **前端**：使用 `useDateTime` composable 轉換為台灣時間顯示

**唯一例外**：`stock_minute_prices` 表使用台灣時間（timezone-naive）
- 原因：60M+ 行數據，已壓縮，修改成本高
- 處理：使用 `timezone_helpers.py` 進行轉換

### 各層時區處理規則

#### ✅ Model 層（資料庫）

```python
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func

class Stock(Base):
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

**關鍵點**：
- 使用 `DateTime(timezone=True)` - 對應 `TIMESTAMPTZ`
- 使用 `func.now()` - 資料庫層級時間戳
- **不要使用** `datetime.utcnow`（Python 3.12+ 已棄用）

#### ✅ Repository 層

```python
from app.utils.timezone_helpers import now_utc, parse_datetime_safe, utc_to_naive_taipei

# 標準資料表
def create_backtest(db: Session, data: BacktestCreate):
    backtest = Backtest(
        created_at=now_utc(),  # 使用 UTC 時間戳
        ...
    )
    return backtest

# stock_minute_prices 特殊處理
def get_minute_prices(db: Session, stock_id: str, start_utc: datetime):
    # 轉換 UTC → 台灣時間
    start_taipei = utc_to_naive_taipei(start_utc)
    return db.query(StockMinutePrice).filter(...).all()
```

#### ✅ Service 層

```python
from app.utils.timezone_helpers import now_utc, parse_datetime_safe, today_taiwan

class BacktestService:
    def create_backtest(self, data: BacktestCreate):
        # 解析用戶輸入（確保 timezone-aware）
        start_datetime = parse_datetime_safe(data.start_datetime)

        # 獲取台灣今日日期（用於市場數據）
        taiwan_today = today_taiwan()

        # 記錄時間戳
        current_time = now_utc()
```

#### ✅ API 層

```python
# Pydantic v2 會自動正確序列化 timezone-aware datetime
# 輸出: {"created_at": "2025-12-20T00:18:21+00:00"}

@router.post("/backtests/")
def create_backtest(data: BacktestCreate):
    # 解析輸入
    start_datetime = parse_datetime_safe(data.start_datetime)
    return BacktestService.create_backtest(data)
```

#### ✅ Celery 任務

```python
from app.utils.timezone_helpers import now_utc

@shared_task
def sync_daily_prices():
    start_time = now_utc()  # 使用 UTC 時間
    # 任務邏輯...
```

#### ✅ Scripts

```python
from app.utils.timezone_helpers import now_utc, today_taiwan

def main():
    start_time = now_utc()  # 記錄開始時間
    taiwan_today = today_taiwan()  # 台灣今日日期
    # 腳本邏輯...
```

#### ✅ 前端

```typescript
import { useDateTime } from '@/composables/useDateTime'
const { formatToTaiwanTime } = useDateTime()

// 顯示台灣時間
const displayTime = formatToTaiwanTime(backtest.created_at)
```

### timezone_helpers.py 快速參考

```python
from app.utils.timezone_helpers import (
    now_utc,                # 當前 UTC 時間（timezone-aware）
    now_taipei_naive,       # 當前台灣時間（naive）
    today_taiwan,           # 台灣今日日期
    parse_datetime_safe,    # 解析並確保 timezone-aware
    utc_to_naive_taipei,    # UTC → 台灣 naive
    naive_taipei_to_utc,    # 台灣 naive → UTC
)
```

**常用模式**：
```python
# 記錄時間戳
created_at = now_utc()

# 解析 API 輸入
dt = parse_datetime_safe(input_datetime)

# 獲取台灣今日
today = today_taiwan()

# stock_minute_prices 轉換
taipei_time = utc_to_naive_taipei(utc_time)
```

### 開發檢查清單

新增功能時：
- [ ] Model 層：datetime 欄位使用 `DateTime(timezone=True)` 和 `func.now()`
- [ ] Repository 層：stock_minute_prices 使用 timezone_helpers 轉換
- [ ] Service 層：使用 `now_utc()`、`parse_datetime_safe()`、`today_taiwan()`
- [ ] API 層：不要手動加 'Z'，讓 Pydantic 自動序列化
- [ ] Celery：crontab 使用 UTC 時間（註解標註台灣時間）
- [ ] 前端：使用 `useDateTime` composable 顯示時間

Code Review 時：
- [ ] 沒有使用 `datetime.now()` 而不指定時區
- [ ] 沒有使用 `datetime.utcnow`（已棄用）
- [ ] stock_minute_prices 操作有正確的時區轉換
- [ ] Celery crontab 有正確的時區註解

**詳細說明**：參見 [TIMEZONE_COMPLETE_GUIDE.md](TIMEZONE_COMPLETE_GUIDE.md)

---

## 📚 文檔導航

**快速開始**：[README.md](README.md)

**詳細操作**：
- [OPERATIONS_GUIDE.md](Document/OPERATIONS_GUIDE.md) - 完整操作手冊
- [QLIB_SYNC_GUIDE.md](Document/QLIB_SYNC_GUIDE.md) - Qlib 同步詳解
- [CELERY_TASKS_GUIDE.md](Document/CELERY_TASKS_GUIDE.md) - Celery 任務管理
- [TIMEZONE_COMPLETE_GUIDE.md](TIMEZONE_COMPLETE_GUIDE.md) - 時區處理完整指南（系統策略、各層規則、Celery 配置、前端顯示）
- [CELERY_REVOKED_TASKS_FIX.md](CELERY_REVOKED_TASKS_FIX.md) - Revoked Tasks 問題解決方案

**資料庫**：
- [DATABASE_SCHEMA_REPORT.md](Document/DATABASE_SCHEMA_REPORT.md) - 16 個資料表
- [DATABASE_CHANGE_CHECKLIST.md](Document/DATABASE_CHANGE_CHECKLIST.md) - 變更檢查清單

**技術專題**：
- [docs/QLIB.md](docs/QLIB.md) - Qlib 引擎完整指南
- [docs/RDAGENT.md](docs/RDAGENT.md) - RD-Agent 完整指南
- [docs/SECURITY.md](docs/SECURITY.md) - 安全機制

**API 文檔**：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 🔧 環境變數

**必填**：
```bash
DATABASE_URL=postgresql://quantlab:quantlab2025@postgres:5432/quantlab
REDIS_URL=redis://redis:6379/0
JWT_SECRET=<至少 32 字元的隨機字串>
FINLAB_API_TOKEN=<從 https://ai.finlab.tw/ 取得>
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

**選填**（AI 功能）：
```bash
OPENAI_API_KEY=<RD-Agent 因子挖掘>
ANTHROPIC_API_KEY=<Claude API>

# Shioaji 期貨交易 API
SHIOAJI_API_KEY=<永豐證券 API Key>
SHIOAJI_SECRET_KEY=<永豐證券 Secret Key>
SHIOAJI_PERSON_ID=<身分證字號>
SHIOAJI_SIMULATION_MODE=True  # True=模擬交易，False=實盤
SHIOAJI_ENABLE_ORDER=False    # True=允許下單，False=僅查詢
```

---

## 🧪 測試規範

### Pytest 配置

測試使用標記（markers）進行分類（定義於 `backend/pytest.ini`）：

- `@pytest.mark.unit` - 快速單元測試，無外部依賴
- `@pytest.mark.integration` - 整合測試，需要資料庫或 API
- `@pytest.mark.slow` - 執行時間超過 1 秒的測試
- `@pytest.mark.futures` - 期貨合約相關測試

### 測試覆蓋目標

**必須測試**：
1. 所有 `services/` 業務邏輯
2. 所有 `repositories/` 資料訪問方法
3. 關鍵 `scripts/` 腳本（如期貨合約註冊）
4. 所有 Celery 任務的成功/失敗/超時場景

**測試檔案結構**：
```
tests/
├── services/           # 業務邏輯測試
│   └── test_shioaji_client.py
├── scripts/            # 腳本測試
│   └── test_register_futures_contracts.py
├── tasks/              # Celery 任務測試
│   └── test_futures_continuous.py
├── integration/        # 整合測試
└── unit/               # 純單元測試
```

### 避免常見測試陷阱

**1. Celery 裝飾器問題**：
```python
# ❌ 錯誤：直接調用會失敗
result = generate_continuous_contracts(symbols=['TX'])

# ✅ 正確：繞過裝飾器
from app.tasks import futures_continuous
func = futures_continuous.generate_continuous_contracts.__wrapped__.__wrapped__
result = func(Mock(), symbols=['TX'], days_back=90)
```

**2. 外部 API Mock**：
```python
# 整合測試標記為 @pytest.mark.integration
# 需要真實 API 的測試應該可選擇性執行
@pytest.mark.integration
def test_real_shioaji_api():
    # 只在提供 API key 時執行
    if not settings.SHIOAJI_API_KEY:
        pytest.skip("SHIOAJI_API_KEY not set")
```

---

**文檔版本**：2025-12-17
**維護者**：開發團隊
**最後更新**：修復 Celery 時區配置錯誤、Revoked Tasks 問題，新增相關文檔鏈接
