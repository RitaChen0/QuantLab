# QuantLab 管理腳本

常用的開發與維護工具腳本集合。

## 🚀 快速開始

```bash
# 查看所有可用腳本
ls -lh scripts/*.sh

# 執行腳本
./scripts/<script-name>.sh
```

## 📋 腳本分類

### Celery 任務管理

- **restart-celery.sh** - 重啟 Celery Worker
  ```bash
  ./scripts/restart-celery.sh
  ```
  用途：代碼更新後重新載入 worker

- **check-celery.sh** - 檢查 Celery 狀態
  ```bash
  ./scripts/check-celery.sh
  ```
  顯示：worker 狀態、活躍任務、隊列長度、速率限制等

- **monitor_celery.sh** - 即時監控 Celery 任務執行
  ```bash
  ./scripts/monitor_celery.sh
  ```
  用途：監控任務執行狀態、錯誤追蹤

- **trigger-backtest.sh** - 手動觸發回測任務（測試用）
  ```bash
  ./scripts/trigger-backtest.sh <backtest_id> <user_id>
  ```
  範例：`./scripts/trigger-backtest.sh 56 6`

### 回測管理

- **check-backtests.sh** - 檢查回測狀態
  ```bash
  ./scripts/check-backtests.sh
  ```
  顯示：最近回測、pending/running/failed 回測、統計資訊

- **cleanup-failed-backtests.sh** - 清理失敗的回測
  ```bash
  ./scripts/cleanup-failed-backtests.sh
  ```
  用途：刪除 FAILED 狀態的回測記錄

- **diagnose_backtest.sh** - 回測失敗診斷工具
  ```bash
  ./scripts/diagnose_backtest.sh
  ```
  用途：診斷回測失敗原因、查看詳細錯誤日誌

- **monitor_backtest_tasks.sh** - 監控回測任務進度
  ```bash
  ./scripts/monitor_backtest_tasks.sh
  ```
  用途：即時監控所有回測任務的執行進度

- **verify_trades.sh** - 驗證回測交易記錄
  ```bash
  ./scripts/verify_trades.sh
  ```
  用途：檢查回測交易記錄的完整性和正確性

### 數據同步

- **sync-qlib-smart.sh** - Qlib 智慧同步（增量）
  ```bash
  ./scripts/sync-qlib-smart.sh           # 完整同步
  ./scripts/sync-qlib-smart.sh --test    # 測試模式（10 檔）
  ./scripts/sync-qlib-smart.sh --stock 2330  # 單檔同步
  ```
  用途：將資料庫數據轉換為 Qlib v2 格式，支援增量同步

- **manual-sync.sh** - 手動同步財務指標（互動式）
  ```bash
  ./scripts/manual-sync.sh
  ```
  用途：手動觸發單一股票的財務指標同步

- **batch-sync.sh** - 批次同步所有股票
  ```bash
  ./scripts/batch-sync.sh           # 完整同步（約 6-8 小時）
  ./scripts/batch-sync.sh --test    # 測試模式（10 檔）
  ./scripts/batch-sync.sh --status  # 查看進度
  ./scripts/batch-sync.sh --reset   # 重新開始
  ```
  用途：批次同步 2,671 檔台股的財務指標

- **monitor-batch-sync.sh** - 監控批次同步進度
  ```bash
  ./scripts/monitor-batch-sync.sh
  ```
  用途：即時監控批次同步任務的執行狀態

### 速率限制管理

- **reset-rate-limit-quick.sh** - 快速重置速率限制
  ```bash
  ./scripts/reset-rate-limit-quick.sh
  ```
  用途：清除 RD-Agent API 速率限制（無互動）

- **reset-rate-limit.sh** - 互動式重置速率限制
  ```bash
  ./scripts/reset-rate-limit.sh
  ```
  選項：
  1. 刪除所有速率限制 keys
  2. 僅刪除 RD-Agent 相關的 keys
  3. 僅刪除因子挖掘 (factor-mining) keys
  4. 僅刪除策略優化 (strategy-optimization) keys
  5. 取消操作

### 前端管理

- **quick-clean.sh** - 快速清理前端緩存
  ```bash
  ./scripts/quick-clean.sh
  ```
  用途：快速清理 Nuxt.js 緩存（無互動）

- **clear-frontend-cache.sh** - 完整清理前端緩存（互動式）
  ```bash
  ./scripts/clear-frontend-cache.sh
  ```
  用途：完整清理前端緩存，包含 `.nuxt`、`.output`、`node_modules/.cache` 等

### 資料庫管理

- **backup_database.sh** - 完整資料庫備份
  ```bash
  ./scripts/backup_database.sh
  ```
  功能：
  - 備份整個 PostgreSQL 資料庫
  - 自動壓縮（gzip）
  - 保留最近 30 天的備份
  - 檔名格式：`quantlab_backup_YYYYMMDD_HHMMSS.sql.gz`

- **backup_industries.sh** - 產業分類資料備份
  ```bash
  ./scripts/backup_industries.sh
  ```
  功能：
  - 僅備份 `industries` 和 `stock_industries` 表
  - 用於產業分類資料的快速備份與還原

### 開發工具

- **dev.sh** - 開發模式啟動
  ```bash
  ./scripts/dev.sh
  ```
  用途：以開發模式啟動所有服務

- **setup.sh** - 初始化設定
  ```bash
  ./scripts/setup.sh
  ```
  用途：首次部署時的環境初始化

- **generate-credentials.sh** - 生成安全憑證
  ```bash
  ./scripts/generate-credentials.sh
  ```
  用途：生成強隨機密碼、JWT Secret 等安全憑證

## 🔧 常用操作流程

### 回測問題診斷

```bash
# 1. 檢查回測狀態
./scripts/check-backtests.sh

# 2. 檢查 Celery worker 狀態
./scripts/check-celery.sh

# 3. 診斷特定回測失敗原因
./scripts/diagnose_backtest.sh

# 4. 查看 Celery 日誌
docker compose logs -f celery-worker

# 5. 必要時重啟 worker
./scripts/restart-celery.sh

# 6. 驗證交易記錄
./scripts/verify_trades.sh
```

### 代碼更新後

```bash
# 1. 清理前端緩存
./scripts/quick-clean.sh

# 2. 重啟後端和 Celery
docker compose restart backend celery-worker

# 3. 驗證狀態
./scripts/check-celery.sh

# 4. 監控任務執行
./scripts/monitor_celery.sh
```

### 速率限制問題

```bash
# 1. 檢查當前限制
docker compose exec redis redis-cli KEYS "LIMITS:*"

# 2. 清除限制（快速）
./scripts/reset-rate-limit-quick.sh

# 3. 或使用互動式清除（更多選項）
./scripts/reset-rate-limit.sh

# 4. 驗證清除成功
docker compose exec redis redis-cli KEYS "LIMITS:*"
```

### 測試回測功能

```bash
# 1. 清理舊的失敗回測
./scripts/cleanup-failed-backtests.sh

# 2. 手動觸發測試回測
./scripts/trigger-backtest.sh 56 6

# 3. 即時監控執行
./scripts/monitor_backtest_tasks.sh

# 4. 查看詳細日誌
docker compose logs -f celery-worker | grep -E "(Task|ERROR|backtest)"
```

### Qlib 數據同步

```bash
# 1. 首次完整同步（所有股票）
./scripts/sync-qlib-smart.sh

# 2. 測試模式（僅 10 檔）
./scripts/sync-qlib-smart.sh --test

# 3. 日常增量更新（只同步新數據）
./scripts/sync-qlib-smart.sh

# 4. 同步單一股票
./scripts/sync-qlib-smart.sh --stock 2330
```

### 財務指標同步

```bash
# 1. 手動同步單檔（互動式）
./scripts/manual-sync.sh

# 2. 批次同步所有股票（完整）
./scripts/batch-sync.sh

# 3. 測試模式（10 檔）
./scripts/batch-sync.sh --test

# 4. 監控批次同步進度
./scripts/monitor-batch-sync.sh

# 5. 查看當前狀態
./scripts/batch-sync.sh --status
```

### 資料庫備份

```bash
# 1. 完整備份
./scripts/backup_database.sh

# 2. 僅備份產業分類資料
./scripts/backup_industries.sh

# 3. 查看備份檔案
ls -lh ~/quantlab_backups/
```

## 📊 腳本總覽

| 分類 | 腳本數量 | 主要用途 |
|------|----------|----------|
| Celery 任務管理 | 4 | Worker 管理、任務監控 |
| 回測管理 | 5 | 回測診斷、清理、驗證 |
| 數據同步 | 4 | Qlib 同步、財務指標同步 |
| 速率限制管理 | 2 | 清除 API 速率限制 |
| 前端管理 | 2 | 緩存清理 |
| 資料庫管理 | 2 | 備份與還原 |
| 開發工具 | 3 | 環境初始化、憑證生成 |
| **總計** | **22** | |

## 📚 相關文檔

- [CLAUDE.md](../CLAUDE.md) - 完整開發指南
- [DATABASE_SCHEMA_REPORT.md](../DATABASE_SCHEMA_REPORT.md) - 資料庫架構
- [DATABASE_CHANGE_CHECKLIST.md](../DATABASE_CHANGE_CHECKLIST.md) - 資料庫變更檢查清單
- [QLIB_INTEGRATION_GUIDE.md](../QLIB_INTEGRATION_GUIDE.md) - Qlib 整合指南
- [RDAGENT_INTEGRATION_GUIDE.md](../RDAGENT_INTEGRATION_GUIDE.md) - RD-Agent 整合指南
- [BATCH_SYNC_GUIDE.md](../BATCH_SYNC_GUIDE.md) - 批次同步指南
- [MANUAL_SYNC_GUIDE.md](../MANUAL_SYNC_GUIDE.md) - 手動同步指南

## 💡 提示

- 所有腳本都已設為可執行權限
- 部分腳本支援 `--help` 或 `-h` 參數
- 執行前建議先在測試環境驗證
- 重要操作會要求確認（如刪除數據）
- 日誌檔案位於 `/tmp/` 或專案根目錄
- 使用 `docker compose logs -f <service>` 即時查看服務日誌

## 🐛 故障排除

### 腳本執行權限問題

```bash
# 批次設定所有腳本為可執行
chmod +x scripts/*.sh

# 或單一腳本
chmod +x scripts/<script-name>.sh
```

### Docker 權限問題

```bash
# 將當前使用者加入 docker 群組
sudo usermod -aG docker $USER

# 重新登入後生效
```

### 資料庫連線失敗

```bash
# 檢查 PostgreSQL 容器狀態
docker compose ps postgres

# 查看資料庫日誌
docker compose logs postgres

# 重啟資料庫
docker compose restart postgres
```

### Celery Worker 無回應

```bash
# 檢查 worker 狀態
./scripts/check-celery.sh

# 查看錯誤日誌
docker compose logs celery-worker | grep ERROR

# 完全重啟 worker
docker compose stop celery-worker
docker compose rm -f celery-worker
docker compose up -d celery-worker
```

## 📦 腳本維護

新增腳本時請：
1. 將腳本放置於 `scripts/` 目錄
2. 設定可執行權限：`chmod +x scripts/new-script.sh`
3. 在腳本開頭加入簡短說明註解
4. 更新本 README.md 文件
5. 必要時更新 [CLAUDE.md](../CLAUDE.md)

## 🔄 版本歷史

- **2025-12-07**: 新增 Celery 管理腳本（restart-celery, check-celery, trigger-backtest）
- **2025-12-06**: 新增回測管理腳本（check-backtests, cleanup-failed-backtests）
- **2025-12-02**: 新增 Qlib 智慧同步腳本
- **2025-11-30**: 新增批次同步與監控腳本
- **2025-11-28**: 初始腳本集合建立
