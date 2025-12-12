# Celery 任務管理指南

完整的 Celery 任務系統操作手冊。

## 目錄

- [概述](#概述)
- [定時任務](#定時任務)
- [手動觸發任務](#手動觸發任務)
- [監控與日誌](#監控與日誌)
- [任務開發](#任務開發)
- [故障排查](#故障排查)

## 概述

### 系統架構

QuantLab 使用 Celery 處理異步任務和定時任務：

- **celery-worker**：任務執行器（處理異步任務）
- **celery-beat**：任務調度器（觸發定時任務）
- **redis**：消息代理和結果後端

### 配置位置

```
backend/app/core/celery_app.py    # Celery 應用配置
backend/app/tasks/                # 任務定義目錄
  ├── __init__.py                 # 任務導出
  ├── stock_data.py               # 股票數據同步任務
  └── qlib_tasks.py               # Qlib 相關任務
```

## 定時任務

### 已實作任務列表

| 任務名稱 | 執行時間 | 說明 | 快取時間 |
|---------|---------|------|---------|
| `sync_stock_list` | 每天 8:00 AM | 同步股票清單（2,671 檔） | 24 小時 |
| `sync_daily_prices` | 每天 9:00 PM | 同步每日價格（15 檔熱門股，7 天） | 10 分鐘 |
| `sync_ohlcv_data` | 每天 10:00 PM | 同步 OHLCV 數據（5 檔，30 天） | 10 分鐘 |
| `sync_latest_prices` | 交易時段每 15 分鐘 | 同步即時價格（10 檔熱門股） | 5 分鐘 |
| `cleanup_old_cache` | 每天 3:00 AM | 清理過期快取 | - |

### 查看定時任務配置

```python
# backend/app/core/celery_app.py
celery_app.conf.beat_schedule = {
    "sync-stock-list-daily": {
        "task": "app.tasks.sync_stock_list",
        "schedule": crontab(hour=8, minute=0),  # 每天 8:00 AM
    },
    "sync-daily-prices": {
        "task": "app.tasks.sync_daily_prices",
        "schedule": crontab(hour=21, minute=0),  # 每天 9:00 PM
    },
    "sync-ohlcv-daily": {
        "task": "app.tasks.sync_ohlcv_data",
        "schedule": crontab(hour=22, minute=0),  # 每天 10:00 PM
    },
    "sync-latest-prices-frequent": {
        "task": "app.tasks.sync_latest_prices",
        "schedule": crontab(minute='*/15', hour='9-13', day_of_week='mon,tue,wed,thu,fri'),
    },
    "cleanup-cache-daily": {
        "task": "app.tasks.cleanup_old_cache",
        "schedule": crontab(hour=3, minute=0),  # 每天 3:00 AM
    },
}
```

### 修改定時任務時間

```bash
# 1. 編輯配置檔案
vim backend/app/core/celery_app.py

# 2. 修改 crontab 表達式
# 範例：改為每天 10:00 AM
"schedule": crontab(hour=10, minute=0)

# 3. 重啟 celery-beat
docker compose restart celery-beat
```

## 手動觸發任務

### 基本命令

```bash
# 觸發股票清單同步
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_stock_list

# 觸發每日價格同步
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_daily_prices

# 觸發 OHLCV 數據同步
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_ohlcv_data

# 觸發即時價格同步
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_latest_prices

# 觸發清理快取
docker compose exec backend celery -A app.core.celery_app call app.tasks.cleanup_old_cache
```

### 傳遞參數給任務

```bash
# 範例：同步特定股票
docker compose exec backend python -c "
from app.tasks.stock_data import sync_daily_prices
result = sync_daily_prices.apply_async(args=['2330'])
print(f'任務 ID: {result.id}')
"
```

### 使用後台管理頁面觸發

```bash
# 1. 訪問後台管理頁面
http://localhost:3000/admin

# 2. 點擊「數據同步」標籤

# 3. 選擇任務並點擊「立即執行」
```

## 監控與日誌

### 查看任務執行狀態

```bash
# 查看所有註冊的任務
docker compose exec backend celery -A app.core.celery_app inspect registered

# 查看當前活躍的任務
docker compose exec backend celery -A app.core.celery_app inspect active

# 查看預定的任務（scheduled）
docker compose exec backend celery -A app.core.celery_app inspect scheduled

# 查看保留的任務（reserved）
docker compose exec backend celery -A app.core.celery_app inspect reserved
```

### 查看 Worker 資訊

```bash
# 查看 worker 統計資訊
docker compose exec backend celery -A app.core.celery_app inspect stats

# 查看 worker 狀態
docker compose exec backend celery -A app.core.celery_app status

# 查看 worker 配置
docker compose exec backend celery -A app.core.celery_app inspect conf
```

### 實時日誌監控

```bash
# 查看 worker 日誌
docker compose logs -f celery-worker

# 查看 beat 日誌
docker compose logs -f celery-beat

# 查看最近 100 行
docker compose logs --tail=100 celery-worker

# 查看最近 1 小時
docker compose logs --since 1h celery-worker

# 過濾特定任務
docker compose logs celery-worker | grep "sync_stock_list"

# 過濾錯誤
docker compose logs celery-worker | grep -i error
```

### 使用監控腳本

```bash
# 啟動監控腳本
./monitor_celery.sh

# 腳本會顯示：
# - Worker 狀態
# - 活躍任務
# - 任務統計
# - 錯誤日誌
```

## 任務開發

### 標準任務模式

```python
# backend/app/tasks/example.py
from celery import Task
from app.core.celery_app import celery_app
from loguru import logger

@celery_app.task(bind=True, name="app.tasks.example_task")
def example_task(self: Task, param1: str) -> dict:
    """
    任務說明

    Args:
        param1: 參數說明

    Returns:
        dict: 任務執行結果
    """
    try:
        logger.info(f"開始執行任務: {param1}")

        # 業務邏輯
        result = do_something(param1)

        logger.info(f"任務執行成功: {result}")
        return {
            "status": "success",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"任務執行失敗: {str(e)}")
        # 重試 3 次，每次延遲 300 秒
        raise self.retry(exc=e, countdown=300, max_retries=3)
```

### 添加新任務

**步驟 1：創建任務函數**
```python
# backend/app/tasks/my_tasks.py
from app.core.celery_app import celery_app

@celery_app.task(bind=True, name="app.tasks.my_new_task")
def my_new_task(self):
    # 任務邏輯
    pass
```

**步驟 2：導出任務**
```python
# backend/app/tasks/__init__.py
from app.tasks.my_tasks import my_new_task

__all__ = [
    "my_new_task",
    # ... 其他任務
]
```

**步驟 3：添加定時任務（可選）**
```python
# backend/app/core/celery_app.py
celery_app.conf.beat_schedule = {
    "my-new-task-daily": {
        "task": "app.tasks.my_new_task",
        "schedule": crontab(hour=10, minute=0),
    },
}
```

**步驟 4：重啟服務**
```bash
# 清除 Python cache
docker compose exec celery-worker find /app -name __pycache__ -type d -exec rm -rf {} +

# 重啟 worker 和 beat
docker compose restart celery-worker celery-beat

# 驗證任務已註冊
docker compose exec backend celery -A app.core.celery_app inspect registered | grep my_new_task
```

### 任務重試配置

```python
@celery_app.task(
    bind=True,
    name="app.tasks.example",
    max_retries=5,              # 最大重試次數
    default_retry_delay=60,     # 預設重試延遲（秒）
    autoretry_for=(Exception,), # 自動重試的異常類型
    retry_backoff=True,         # 使用指數退避
    retry_backoff_max=600,      # 最大退避時間（秒）
    retry_jitter=True,          # 添加隨機抖動
)
def example_task(self):
    # 任務邏輯
    pass
```

### 任務優先級

```python
# 高優先級任務
example_task.apply_async(priority=10)

# 低優先級任務
example_task.apply_async(priority=1)
```

## 任務執行記錄

### 查看任務歷史

```bash
# 使用 Flower（需額外安裝）
docker compose exec backend celery -A app.core.celery_app flower

# 訪問 http://localhost:5555

# 或查看 Redis 中的結果
docker compose exec backend redis-cli -h redis keys "celery-task-meta-*"
```

### 清理任務結果

```bash
# 清理所有任務結果
docker compose exec backend celery -A app.core.celery_app purge

# 清理特定任務結果
docker compose exec backend redis-cli -h redis del "celery-task-meta-任務ID"
```

## 故障排查

### Worker 無法連接 Redis

**症狀**：
```
[ERROR] Consumer: Cannot connect to redis://redis:6379/0: Error 111 connecting to redis:6379. Connection refused.
```

**解決方案**：
```bash
# 1. 確認 Redis 運行
docker compose ps redis

# 2. 測試連接
docker compose exec backend redis-cli -h redis ping

# 3. 檢查環境變數
docker compose exec backend env | grep CELERY

# 4. 重啟 worker
docker compose restart celery-worker
```

### 任務未執行

**症狀**：定時任務到時間未執行

**解決方案**：
```bash
# 1. 確認 beat 運行
docker compose ps celery-beat

# 2. 查看 beat 日誌
docker compose logs celery-beat

# 3. 確認任務已註冊
docker compose exec backend celery -A app.core.celery_app inspect registered

# 4. 重啟 beat
docker compose restart celery-beat
```

### 任務更新後無法載入

**症狀**：新增任務出現 ImportError

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

### 任務執行超時

**症狀**：
```
[ERROR] Task app.tasks.sync_stock_list[...] raised unexpected: TimeLimitExceeded()
```

**解決方案**：
```python
# 調整任務時間限制
@celery_app.task(
    bind=True,
    name="app.tasks.sync_stock_list",
    time_limit=3600,        # 硬限制（秒）
    soft_time_limit=3300,   # 軟限制（秒）
)
def sync_stock_list(self):
    # 任務邏輯
    pass
```

### 任務重複執行

**症狀**：同一任務被執行多次

**解決方案**：
```bash
# 1. 檢查是否有多個 beat 實例
docker compose ps | grep celery-beat

# 2. 停止多餘的 beat 實例
docker compose scale celery-beat=1

# 3. 清理 Redis 中的調度鎖
docker compose exec backend redis-cli -h redis del "celery-schedule-lock"
```

### 內存洩漏

**症狀**：worker 內存持續增長

**解決方案**：
```yaml
# docker-compose.yml
services:
  celery-worker:
    environment:
      - CELERYD_MAX_TASKS_PER_CHILD=1000  # 每處理 1000 個任務後重啟 worker
```

## 效能優化

### Worker 並發設定

```bash
# 使用多進程
docker compose exec celery-worker celery -A app.core.celery_app worker --concurrency=4

# 使用 gevent
docker compose exec celery-worker celery -A app.core.celery_app worker --pool=gevent --concurrency=1000
```

### 任務預取

```yaml
# docker-compose.yml
services:
  celery-worker:
    environment:
      - CELERYD_PREFETCH_MULTIPLIER=1  # 避免長任務阻塞
```

### 結果後端優化

```python
# backend/app/core/celery_app.py
celery_app.conf.result_expires = 3600  # 1 小時後過期
celery_app.conf.result_backend_transport_options = {
    'master_name': 'mymaster',
    'visibility_timeout': 3600,
}
```

## 最佳實踐

### 1. 任務設計原則

- **冪等性**：任務可以安全地重複執行
- **原子性**：任務執行成功或完全失敗
- **無狀態**：不依賴全局狀態
- **超時處理**：設定合理的超時時間

### 2. 日誌記錄

```python
from loguru import logger

@celery_app.task(bind=True)
def my_task(self):
    logger.info(f"開始執行任務 {self.request.id}")
    # ... 業務邏輯
    logger.info(f"任務執行成功，處理了 {count} 筆數據")
```

### 3. 錯誤處理

```python
@celery_app.task(bind=True, max_retries=3)
def my_task(self):
    try:
        # 業務邏輯
        risky_operation()
    except TemporaryError as exc:
        # 可恢復錯誤，重試
        raise self.retry(exc=exc, countdown=60)
    except PermanentError as exc:
        # 永久錯誤，記錄並返回
        logger.error(f"任務失敗: {exc}")
        return {"status": "failed", "error": str(exc)}
```

### 4. 監控指標

定期檢查：
- Worker 數量和狀態
- 任務執行時間
- 失敗率
- 隊列長度
- 內存使用

## 相關文檔

- [操作指南](OPERATIONS_GUIDE.md)
- [開發指南](DEVELOPMENT_GUIDE.md)
- [Celery 官方文檔](https://docs.celeryproject.org/)
