# QuantLab 數據同步排程總覽

> **最後更新**: 2025-12-16
> **時區**: 台北時間 (UTC+8)
> **自動執行**: Celery Beat 定時任務

---

## 📋 目錄

- [快速參考表格](#快速參考表格) - 一目了然的排程總覽
- [詳細說明](#詳細說明) - 每個任務的完整資訊
- [手動執行命令](#手動執行命令) - 常用操作指令
- [監控與診斷](#監控與診斷) - 問題排查工具

---

# 快速參考表格

## 📅 每日排程總覽

| 時間 | 任務 | Celery Task | 腳本位置 | 執行時長 |
|------|------|-------------|----------|----------|
| **08:00** | 股票清單同步 | `app.tasks.sync_stock_list` | `backend/app/tasks/stock_data.py` | ~30 秒 |
| **09:00-13:00** | 即時價格（每 15 分） | `app.tasks.sync_latest_prices` | `backend/app/tasks/stock_data.py` | ~30 秒 |
| **09:00-13:00** 🔔 | **策略監控（股票）** | `app.tasks.monitor_active_strategies` | `backend/app/tasks/strategy_monitoring.py` | **~1-3 分鐘** |
| **15:00-05:00** 🔔 | **策略監控（期貨）** | `app.tasks.monitor_active_strategies` | `backend/app/tasks/strategy_monitoring.py` | **~1-3 分鐘** |
| **15:00** ⭐ | **Shioaji 分鐘線** | `app.tasks.sync_shioaji_top_stocks` | `backend/app/tasks/shioaji_sync.py` | **2-4 小時** |
| **15:30** ⭐ | **期貨分鐘線** | `app.tasks.sync_shioaji_futures` | `backend/app/tasks/shioaji_sync.py` | **5-10 分鐘** |
| **15:40** ⭐ | **選擇權因子** | `app.tasks.sync_option_daily_factors` | `backend/app/tasks/option_sync.py` | **2-5 分鐘** |
| **21:00** | 每日價格 + 法人 | `app.tasks.sync_daily_prices` | `backend/app/tasks/stock_data.py` | ~5-10 分鐘 |
| **22:00** | OHLCV 數據 | `app.tasks.sync_ohlcv_data` | `backend/app/tasks/stock_data.py` | ~10-15 分鐘 |
| **23:00** | 基本面（快速） | `app.tasks.sync_fundamental_latest` | `backend/app/tasks/fundamental_sync.py` | ~15-30 分鐘 |
| **03:00** | 清理快取 | `app.tasks.cleanup_old_cache` | `backend/app/tasks/stock_data.py` | ~30 秒 |

## 📅 每週排程

| 時間 | 任務 | Celery Task | 腳本位置 | 執行時長 |
|------|------|-------------|----------|----------|
| **週日 02:00** | 清理法人數據 | `app.tasks.cleanup_old_institutional_data` | `backend/app/tasks/institutional_investor_sync.py` | ~1-2 分鐘 |
| **週日 04:00** | 基本面（完整） | `app.tasks.sync_fundamental_data` | `backend/app/tasks/fundamental_sync.py` | ~2-4 小時 |
| **週日 04:00** 🔔 | 清理舊信號記錄 | `app.tasks.cleanup_old_signals` | `backend/app/tasks/strategy_monitoring.py` | ~10-30 秒 |
| **週日 19:00** | 註冊選擇權合約 | `app.tasks.register_option_contracts` | `backend/app/tasks/option_sync.py` | ~1-2 分鐘 |
| **週六 18:00** | 生成連續合約 | `app.tasks.generate_continuous_contracts` | `backend/app/tasks/futures_continuous.py` | ~1-2 分鐘 |

## 📅 年度排程

| 時間 | 任務 | Celery Task | 腳本位置 | 執行時長 |
|------|------|-------------|----------|----------|
| **1/1 00:05** | 註冊新年度期貨合約 | `app.tasks.register_new_futures_contracts` | `backend/app/tasks/futures_continuous.py` | ~30 秒 |

## ⚠️ 重啟時機建議

### ✅ 安全重啟時段（不影響數據同步）
- 凌晨 **02:00-07:00**
- 週末任意時間

### ⚠️ 避免重啟時段
- **09:00-13:30** - 交易時段即時價格同步
- **15:00-16:00** - 關鍵數據同步窗口（Shioaji + 期貨 + 選擇權）
- **21:00-23:00** - 日終數據處理

## 📊 數據更新優先順序

1. **最高優先** ⭐⭐⭐
   - 選擇權因子同步（15:40）- 依賴期貨數據

2. **高優先** ⭐⭐
   - 期貨分鐘線同步（15:30）
   - Shioaji 分鐘線同步（15:00）

3. **中優先** ⭐
   - 每日價格同步（21:00）
   - 法人買賣超（21:00）

4. **低優先**
   - 基本面數據（23:00）
   - OHLCV 數據（22:00）

---

# 詳細說明

## 📅 每日排程（交易日）

### 08:00 - 股票清單同步
- **任務ID**: `sync-stock-list-daily`
- **Celery Task**: `app.tasks.sync_stock_list`
- **腳本位置**: `backend/app/tasks/stock_data.py`
- **執行時長**: ~30 秒
- **數據來源**: FinLab API
- **說明**: 更新所有股票代碼、名稱、分類

**手動執行**:
```bash
# 通過 Celery
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_stock_list

# 通過後台管理介面
http://localhost:3000/admin → 數據同步 → 點擊「立即執行」
```

---

### 09:00-13:00 - 即時價格同步（每 15 分鐘）
- **任務ID**: `sync-latest-prices-frequent`
- **Celery Task**: `app.tasks.sync_latest_prices`
- **腳本位置**: `backend/app/tasks/stock_data.py`
- **執行頻率**: 每 15 分鐘（09:00, 09:15, 09:30...13:00）
- **執行天數**: 週一至週五（交易日）
- **執行時長**: ~10-30 秒
- **數據來源**: FinLab API
- **說明**: 交易時段即時價格更新

**手動執行**:
```bash
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_latest_prices
```

---

### 15:00 - Shioaji 股票分鐘線同步 ⭐
- **任務ID**: `sync-shioaji-minute-daily`
- **Celery Task**: `app.tasks.sync_shioaji_top_stocks`
- **腳本位置**: `backend/app/tasks/shioaji_sync.py`
- **執行天數**: 週一至週五（交易日）
- **執行時長**: ~2-4 小時（視缺失數據量）
- **數據來源**: Shioaji API（永豐證券）
- **同步範圍**: Top 50 權值股
- **說明**: 同步當日分鐘線到 PostgreSQL 和 Qlib

**手動執行**:
```bash
# 完整同步（Top 50）
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_shioaji_top_stocks

# 測試模式（5 檔股票）
docker compose exec backend python /app/scripts/import_shioaji_csv.py --test
```

**相關腳本**:
- `backend/app/tasks/shioaji_sync.py` - Celery 任務
- `scripts/import_all_shioaji.sh` - 手動批次同步

---

### 15:30 - Shioaji 期貨分鐘線同步 ⭐
- **任務ID**: `sync-shioaji-futures-daily`
- **Celery Task**: `app.tasks.sync_shioaji_futures`
- **腳本位置**: `backend/app/tasks/shioaji_sync.py`
- **執行天數**: 週一至週五（交易日）
- **執行時長**: ~5-10 分鐘
- **數據來源**: Shioaji API
- **同步範圍**: TX（台指期貨）、MTX（小台期貨）
- **說明**: 同步當日期貨分鐘線到 PostgreSQL 和 Qlib

**手動執行**:
```bash
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_shioaji_futures
```

**相關腳本**:
- `backend/scripts/register_futures_contracts.py` - 註冊期貨合約
- `backend/scripts/generate_continuous_contract.py` - 生成連續合約

---

### 15:40 - 選擇權每日因子同步 ⭐
- **任務ID**: `sync-option-daily-factors`
- **Celery Task**: `app.tasks.sync_option_daily_factors`
- **腳本位置**: `backend/app/tasks/option_sync.py`
- **執行天數**: 週一至週五（交易日）
- **執行時長**: ~2-5 分鐘
- **數據來源**: Shioaji API + Black-Scholes 計算
- **說明**: 計算 PCR、ATM IV、Greeks 彙總

**手動執行**:
```bash
# 同步每日因子
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_option_daily_factors

# 回補歷史數據（90 天）
docker compose exec backend python /app/scripts/backfill_option_data.py \
  --underlying TX --days-back 90

# 驗證數據品質
bash /home/ubuntu/QuantLab/verify_option_quality.sh
```

**相關腳本**:
- `backend/scripts/backfill_option_data.py` - 歷史數據回補
- `backend/scripts/backfill_option_quality.py` - 品質驗證
- `verify_option_quality.sh` - 快速驗證

---

### 21:00 - 每日價格同步 + 法人買賣超
- **任務ID**: `sync-daily-prices` + `sync-institutional-investors-daily`
- **Celery Task**:
  - `app.tasks.sync_daily_prices`
  - `app.tasks.sync_top_stocks_institutional`
- **腳本位置**:
  - `backend/app/tasks/stock_data.py`
  - `backend/app/tasks/institutional_investor_sync.py`
- **執行時長**: ~5-10 分鐘
- **數據來源**: FinLab API
- **同步範圍**: 所有股票 + Top 100 法人買賣超
- **說明**: 同步當日收盤價、成交量及法人進出

**手動執行**:
```bash
# 每日價格
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_daily_prices

# 法人買賣超（Top 100，最近 7 天）
docker compose exec backend celery -A app.core.celery_app call \
  app.tasks.sync_top_stocks_institutional --kwargs='{"limit":100,"days":7}'
```

---

### 22:00 - OHLCV 數據同步
- **任務ID**: `sync-ohlcv-daily`
- **Celery Task**: `app.tasks.sync_ohlcv_data`
- **腳本位置**: `backend/app/tasks/stock_data.py`
- **執行時長**: ~10-15 分鐘
- **數據來源**: FinLab API
- **說明**: 同步完整 OHLCV（開高低收量）

**手動執行**:
```bash
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_ohlcv_data
```

---

### 23:00 - 基本面數據同步（快速）
- **任務ID**: `sync-fundamental-latest-daily`
- **Celery Task**: `app.tasks.sync_fundamental_latest`
- **腳本位置**: `backend/app/tasks/fundamental_sync.py`
- **執行時長**: ~15-30 分鐘
- **數據來源**: FinLab API
- **說明**: 增量同步最新基本面（EPS、ROE、營收等）

**手動執行**:
```bash
# 快速同步（僅最新季度）
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_fundamental_latest

# 批次同步（自訂股票清單）
docker compose exec backend python /app/scripts/batch_sync_fundamental.py
```

---

### 03:00 - 清理過期快取
- **任務ID**: `cleanup-cache-daily`
- **Celery Task**: `app.tasks.cleanup_old_cache`
- **腳本位置**: `backend/app/tasks/stock_data.py`
- **執行時長**: ~10-30 秒
- **說明**: 清理 Redis 中的過期資料

**手動執行**:
```bash
docker compose exec backend celery -A app.core.celery_app call app.tasks.cleanup_old_cache

# 手動清理 Redis
docker compose exec redis redis-cli FLUSHDB
```

---

## 📅 每週排程詳細說明

### 週日 02:00 - 清理過期法人數據
- **任務ID**: `cleanup-institutional-data-weekly`
- **Celery Task**: `app.tasks.cleanup_old_institutional_data`
- **腳本位置**: `backend/app/tasks/institutional_investor_sync.py`
- **執行時長**: ~1-2 分鐘
- **保留天數**: 365 天
- **說明**: 清理超過一年的法人買賣超數據

**手動執行**:
```bash
docker compose exec backend celery -A app.core.celery_app call \
  app.tasks.cleanup_old_institutional_data --kwargs='{"days_to_keep":365}'
```

---

### 週日 04:00 - 基本面數據完整同步
- **任務ID**: `sync-fundamental-weekly`
- **Celery Task**: `app.tasks.sync_fundamental_data`
- **腳本位置**: `backend/app/tasks/fundamental_sync.py`
- **執行時長**: ~2-4 小時
- **數據來源**: FinLab API
- **說明**: 完整同步所有股票的基本面數據（所有季度）

**手動執行**:
```bash
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_fundamental_data
```

---

### 週日 19:00 - 註冊選擇權合約
- **任務ID**: `register-option-contracts-weekly`
- **Celery Task**: `app.tasks.register_option_contracts`
- **腳本位置**: `backend/app/tasks/option_sync.py`
- **執行時長**: ~1-2 分鐘
- **數據來源**: Shioaji API
- **說明**: 更新有效的選擇權合約清單

**手動執行**:
```bash
docker compose exec backend celery -A app.core.celery_app call app.tasks.register_option_contracts
```

---

### 週六 18:00 - 生成期貨連續合約
- **任務ID**: `generate-continuous-contracts-weekly`
- **Celery Task**: `app.tasks.generate_continuous_contracts`
- **腳本位置**: `backend/app/tasks/futures_continuous.py`
- **執行時長**: ~1-2 分鐘
- **說明**: 拼接 TX/MTX 月份合約生成 TXCONT/MTXCONT

**手動執行**:
```bash
# 生成連續合約（最近 90 天）
docker compose exec backend celery -A app.core.celery_app call \
  app.tasks.generate_continuous_contracts --kwargs='{"symbols":["TX","MTX"],"days_back":90}'

# 使用腳本生成
docker compose exec backend python /app/scripts/generate_continuous_contract.py
```

---

## 📅 年度排程詳細說明

### 1/1 00:05 - 註冊新年度期貨合約
- **任務ID**: `register-new-futures-contracts-yearly`
- **Celery Task**: `app.tasks.register_new_futures_contracts`
- **腳本位置**: `backend/app/tasks/futures_continuous.py`
- **執行時長**: ~30 秒
- **說明**: 自動註冊下一年度的 TX/MTX 月份合約

**手動執行**:
```bash
docker compose exec backend celery -A app.core.celery_app call app.tasks.register_new_futures_contracts

# 或直接使用腳本
docker compose exec backend python /app/scripts/register_futures_contracts.py
```

---

# 手動執行命令

## 🚀 立即同步數據

### 基本數據同步
```bash
# 股票清單
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_stock_list

# 每日價格
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_daily_prices

# OHLCV 數據
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_ohlcv_data

# 基本面數據（快速）
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_fundamental_latest

# 基本面數據（完整）
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_fundamental_data
```

### Shioaji 數據同步
```bash
# Shioaji 分鐘線（Top 50）
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_shioaji_top_stocks

# 期貨分鐘線
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_shioaji_futures

# 選擇權每日因子
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_option_daily_factors
```

### 法人買賣超
```bash
# 法人買賣超（Top 100，最近 7 天）
docker compose exec backend celery -A app.core.celery_app call \
  app.tasks.sync_top_stocks_institutional --kwargs='{"limit":100,"days":7}'

# 法人買賣超（自訂範圍）
docker compose exec backend celery -A app.core.celery_app call \
  app.tasks.sync_top_stocks_institutional --kwargs='{"limit":50,"days":30}'
```

## 📊 Qlib 數據導出

### 日線數據
```bash
# 智慧增量同步（推薦）
bash scripts/sync-qlib-smart.sh

# 測試模式（10 檔股票）
bash scripts/sync-qlib-smart.sh --test

# 完整導出
docker compose exec backend python /app/scripts/export_to_qlib_v2.py \
  --output-dir /data/qlib/tw_stock_v2 --stocks all
```

### 分鐘線數據
```bash
# 導出分鐘線到 Qlib
docker compose exec backend python /app/scripts/export_minute_to_qlib.py \
  --output-dir /data/qlib/tw_stock_minute

# 指定股票代碼
docker compose exec backend python /app/scripts/export_minute_to_qlib.py \
  --output-dir /data/qlib/tw_stock_minute --symbols 2330,2317
```

### 選擇權數據
```bash
# 導出選擇權到 Qlib
docker compose exec backend python /app/scripts/export_option_to_qlib.py \
  --output-dir /data/qlib/tw_option
```

## 🔄 數據回補與驗證

### 選擇權歷史數據回補
```bash
# 測試模式（3 天，不寫入）
docker compose exec backend python /app/scripts/backfill_option_data.py \
  --underlying TX --days-back 3 --dry-run

# 回補最近 7 天
docker compose exec backend python /app/scripts/backfill_option_data.py \
  --underlying TX --days-back 7

# 回補完整 90 天
docker compose exec backend python /app/scripts/backfill_option_data.py \
  --underlying TX --days-back 90

# 指定日期範圍
docker compose exec backend python /app/scripts/backfill_option_data.py \
  --underlying TX --start-date 2025-09-16 --end-date 2025-12-15
```

### 數據品質驗證
```bash
# 驗證選擇權數據品質
bash /home/ubuntu/QuantLab/verify_option_quality.sh

# 檢查並填補數據缺口
docker compose exec backend python /app/scripts/check_and_fill_gaps.py

# 重試失敗的股票
bash /home/ubuntu/QuantLab/backend/scripts/retry_failed_stocks.sh
```

---

# 監控與診斷

## 🔍 Celery 任務管理

### 查看任務狀態
```bash
# 查看已註冊任務
docker compose exec backend celery -A app.core.celery_app inspect registered

# 查看定時任務清單
docker compose exec backend celery -A app.core.celery_app inspect scheduled

# 查看活動任務
docker compose exec backend celery -A app.core.celery_app inspect active

# 查看保留的任務
docker compose exec backend celery -A app.core.celery_app inspect reserved
```

### 查看 Worker 狀態
```bash
# 查看 Worker 統計資訊
docker compose exec backend celery -A app.core.celery_app inspect stats

# 查看 Worker 活動狀態
docker compose exec backend celery -A app.core.celery_app status

# 查看 Worker 註冊的任務
docker compose exec backend celery -A app.core.celery_app inspect registered
```

## 📋 日誌查看

```bash
# 查看 Celery Beat 日誌（排程器）
docker compose logs -f celery-beat

# 查看 Celery Worker 日誌（執行器）
docker compose logs -f celery-worker

# 查看後端日誌
docker compose logs -f backend

# 查看最近 100 行日誌
docker compose logs --tail 100 celery-worker

# 查看特定時間範圍的日誌
docker compose logs --since 2025-12-16T15:00:00 celery-worker
```

## 🛠️ 服務管理

```bash
# 重啟 Celery Worker
docker compose restart celery-worker

# 重啟 Celery Beat（排程器）
docker compose restart celery-beat

# 重啟後端
docker compose restart backend

# 查看所有服務狀態
docker compose ps

# 查看 Celery 狀態（快捷腳本）
bash scripts/check-celery.sh
```

## 📊 監控腳本

```bash
# 監控批次同步
bash scripts/monitor-batch-sync.sh

# 診斷回測問題
bash scripts/diagnose_backtest.sh

# 監控回測任務
bash scripts/monitor_backtest_tasks.sh

# 診斷連線問題
bash scripts/diagnose-connection.sh
```

---

## 📊 數據流向圖

```
外部 API (FinLab, Shioaji)
         ↓
   PostgreSQL (TimescaleDB)
    ├─→ stock_prices (日線，永久保存)
    ├─→ stock_minute_prices (分鐘線，保留 6 個月)
    ├─→ fundamental_data (基本面)
    ├─→ institutional_investors (法人買賣超)
    ├─→ option_daily_factors (選擇權因子)
    └─→ futures_contracts (期貨合約)
         ↓
   Qlib 二進制格式（高效能查詢）
    ├─→ /data/qlib/tw_stock_v2/ (日線，永久)
    ├─→ /data/qlib/tw_stock_minute/ (分鐘線，7 年)
    └─→ /data/qlib/tw_option/ (選擇權)
         ↓
   回測引擎 (Backtrader + Qlib)
    ├─→ 技術指標策略 (Backtrader)
    └─→ 機器學習策略 (Qlib)
```

---

## 📝 注意事項

### 1. 時區設定
- **所有排程時間均為台北時間 (UTC+8)**
- Celery 內部使用 UTC，已自動轉換
- 修改排程時請調整 `backend/app/core/celery_app.py` 中的 UTC 時間
- 公式：**UTC 時間 = 台北時間 - 8 小時**

### 2. API 限制
- **FinLab API**: 有每日請求次數限制，避免過度呼叫
- **Shioaji API**: 有速率限制（每秒 3 次），腳本會自動重試
- 建議在非交易時段執行大量數據同步

### 3. 執行優先順序
1. **最高優先**: 選擇權因子同步（15:40，依賴期貨數據）
2. **高優先**: 期貨同步（15:30）、Shioaji 分鐘線同步（15:00）
3. **中優先**: 日終數據同步（21:00-23:00）
4. **低優先**: 清理維護任務（凌晨執行）

### 4. 錯誤處理
- 所有任務都有超時設定（參考各任務說明）
- 失敗任務會記錄在 Redis，可通過後台管理介面查看
- 關鍵任務失敗會發送通知（如已設定 Telegram）
- 可手動重試失敗的任務

### 5. 開發階段重啟建議

**安全重啟時段**（不影響數據同步）:
- ✅ 凌晨 **02:00-07:00**
- ✅ 週末任意時間
- ✅ 非交易日（國定假日）

**避免重啟時段**:
- ⚠️ **09:00-13:30** - 交易時段即時價格同步
- ⚠️ **15:00-16:00** - 關鍵數據同步窗口
- ⚠️ **21:00-23:00** - 日終數據處理

**重啟後檢查**:
```bash
# 檢查 Celery Beat 是否正常
docker compose logs celery-beat --tail 20

# 檢查下次執行時間
docker compose exec backend celery -A app.core.celery_app inspect scheduled

# 檢查 Worker 是否正常
docker compose exec backend celery -A app.core.celery_app status
```

### 6. 數據保留策略
- **PostgreSQL**:
  - 日線數據：永久保存
  - 分鐘線數據：保留 6 個月（TimescaleDB 自動清理）
  - 法人買賣超：保留 1 年（週日自動清理）

- **Qlib**:
  - 日線數據：永久保存
  - 分鐘線數據：保留 7 年
  - 選擇權數據：永久保存

### 7. 性能優化建議
- **日線同步**：使用智慧增量模式（`sync-qlib-smart.sh`）
- **分鐘線同步**：避免重複導出，僅同步新數據
- **資料庫查詢**：利用 TimescaleDB 的時間序列優化
- **Qlib 查詢**：使用二進制格式，速度快 3-10 倍

---

## 🔗 相關文檔

- [CLAUDE.md](CLAUDE.md) - 完整開發指南
- [QLIB_SYNC_GUIDE.md](Document/QLIB_SYNC_GUIDE.md) - Qlib 同步詳解
- [CELERY_TASKS_GUIDE.md](Document/CELERY_TASKS_GUIDE.md) - Celery 任務管理
- [DATABASE_SCHEMA_REPORT.md](Document/DATABASE_SCHEMA_REPORT.md) - 資料庫結構

---

**文檔版本**: 2.0（合併版）
**最後更新**: 2025-12-16
**維護者**: 開發團隊
