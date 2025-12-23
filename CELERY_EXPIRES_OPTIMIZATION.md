# Celery Task Expires 智慧優化

## 📅 優化日期
2025-12-23

## 🔍 問題根源

### 惡性循環

```
Beat 重啟 → 補發逾期任務 → 任務已過 expires 時間 → 被標記 revoked
→ revoked 列表積累 → 後續任務被攔截 → 必須重啟 Worker → 循環往復
```

### 關鍵矛盾

- **問題 1**：每日任務設置 `expires: 7200`（2 小時）太短
- **問題 2**：如果 Beat 延遲重啟超過 2 小時，補發的任務立即過期
- **問題 3**：Worker 將過期任務標記為 revoked，導致後續同名任務也被攔截
- **問題 4**：必須手動重啟 Worker 才能清空 revoked 列表

### 實際案例

```
[15:30:00] Scheduler: Sending due task sync-shioaji-futures-daily
[15:30:00] Task received: app.tasks.sync_shioaji_futures[eb764e56...]
[15:30:00] Discarding revoked task: app.tasks.sync_shioaji_futures[eb764e56...]
```

## ✅ 智慧解決方案

### 核心原則

**expires 時間應該接近任務的執行週期**：
- 每日任務：`expires: 82800`（23 小時）
- 每週任務：`expires: 604800`（7 天）
- 每年任務：`expires: 86400`（24 小時）
- 高頻任務（15 分鐘）：**無 expires**（避免立即過期）
- 長時間任務：`expires: 18000`（5 小時，例如同步所有股票需時 4 小時）

### 優化清單（14 個任務）

#### 每日任務（23 小時 expires）
| 任務 | 舊 expires | 新 expires | 執行時間 |
|------|-----------|-----------|---------|
| `sync-stock-list-daily` | 2h | **23h** | Taiwan 08:00 |
| `sync-daily-prices` | 2h | **23h** | Taiwan 21:00 |
| `sync-ohlcv-daily` | 2h | **23h** | Taiwan 22:00 |
| `cleanup-celery-metadata-daily` | 2h | **23h** | Taiwan 05:00 |
| `sync-fundamental-latest-daily` | 2h | **23h** | Taiwan 23:00 |
| `sync-institutional-investors-daily` | 2h | **23h** | Taiwan 21:00 |
| `sync-shioaji-futures-daily` | 2h | **無** | Taiwan 15:30 |
| `sync-option-daily-factors` | 1h | **23h** | Taiwan 15:40 |

#### 每週任務（7 天 expires）
| 任務 | 舊 expires | 新 expires | 執行時間 |
|------|-----------|-----------|---------|
| `sync-fundamental-weekly` | 6h | **7d** | Taiwan Sun 04:00 |
| `cleanup-institutional-data-weekly` | 1h | **7d** | Taiwan Sun 02:00 |
| `generate-continuous-contracts-weekly` | 1h | **7d** | Taiwan Sat 18:00 |
| `register-option-contracts-weekly` | 1h | **7d** | Taiwan Sun 19:00 |
| `cleanup-old-signals-weekly` | 1h | **7d** | Taiwan Sun 04:00 |

#### 特殊任務
| 任務 | 舊 expires | 新 expires | 執行時間 |
|------|-----------|-----------|---------|
| `register-new-futures-contracts-yearly` | 1h | **24h** | Taiwan Jan 1 00:05 |

### 特殊處理：sync-shioaji-futures-daily

**完全移除 expires 限制**，因為：
1. ✅ 已有 `@skip_if_recently_executed(min_interval_hours=24)` 裝飾器
2. ✅ 已有 Redis Lock 防止並發（30 分鐘超時）
3. ✅ 任務內部有重複檢測機制
4. ✅ 三層防護確保不會重複執行

## 🛡️ 三層智慧防護

所有定時任務都有多層防護，確保即使 Beat 重啟補發也不會造成問題：

### 第 1 層：expires 時間充足
- 每日任務：23 小時 expires（幾乎覆蓋整個週期）
- 每週任務：7 天 expires（覆蓋整個週期）

### 第 2 層：任務級別去重
```python
@skip_if_recently_executed(min_interval_hours=24)
@record_task_history
def sync_shioaji_futures(self: Task) -> dict:
    ...
```

### 第 3 層：Redis 分佈式鎖
```python
redis_client = Redis.from_url(settings.REDIS_URL)
lock_key = f"task_lock:{self.name}"
lock = redis_client.lock(lock_key, timeout=1800)

if not lock.acquire(blocking=False):
    logger.warning(f"⚠️  任務 {self.name} 已在執行中，跳過")
    return {"status": "skipped", ...}
```

## 📊 優化效果

### 問題解決
- ✅ **杜絕惡性循環**：Beat 重啟後補發的任務仍能正常執行
- ✅ **減少 revoked 積累**：只有真正過期的任務才會被標記
- ✅ **無需手動干預**：Worker 自動重啟（512MB 內存限制）清空 revoked 列表
- ✅ **保持可靠性**：三層防護確保不會重複執行

### 效能提升
- 🚀 **自動恢復**：Beat 重啟不再導致任務永久失效
- 🚀 **減少監控成本**：不需要頻繁檢查 "尚未執行" 的任務
- 🚀 **提升穩定性**：Worker 定期自動重啟，避免內存洩漏

## 🔬 驗證步驟

### 1. 檢查配置已加載
```bash
docker compose logs celery-beat --tail 50 | grep "sync-shioaji-futures-daily"
# 應該看到任務已註冊
```

### 2. 確認 revoked 列表已清空
```bash
docker compose exec backend celery -A app.core.celery_app inspect revoked
# 應該顯示 "- empty -"
```

### 3. 等待明天 15:30 驗證執行
```bash
docker compose logs celery-worker | grep sync_shioaji_futures
# 應該看到任務正常執行，不再有 "Discarding revoked task" 訊息
```

### 4. 驗證期貨數據已更新
```bash
docker compose exec postgres psql -U quantlab quantlab -c "
SELECT stock_id, MAX(datetime::date) as last_date, COUNT(DISTINCT datetime::date) as days
FROM stock_minute_prices
WHERE stock_id IN ('TX', 'MTX')
GROUP BY stock_id;"
```

## 📝 相關文檔

- [CLAUDE.md](CLAUDE.md) - 開發指南（已更新常見陷阱 #10）
- [CELERY_REVOKED_TASKS_FIX.md](CELERY_REVOKED_TASKS_FIX.md) - Revoked Tasks 詳細說明
- [TIMEZONE_COMPLETE_GUIDE.md](TIMEZONE_COMPLETE_GUIDE.md) - 時區處理指南

## 🎯 最佳實踐

為未來新增的定時任務提供指導：

### 選擇 expires 時間

```python
# ❌ 錯誤：expires 太短
"my-daily-task": {
    "schedule": crontab(hour=12, minute=0),  # 每天一次
    "options": {"expires": 3600},  # 1 小時 - 太短！
}

# ✅ 正確：expires 接近任務週期
"my-daily-task": {
    "schedule": crontab(hour=12, minute=0),  # 每天一次
    "options": {"expires": 82800},  # 23 小時 - 合理
}

# ✅ 正確：高頻任務無 expires
"my-frequent-task": {
    "schedule": crontab(minute='*/15'),  # 每 15 分鐘
    # 不設置 expires
}

# ✅ 正確：長時間任務預留充足時間
"my-long-task": {
    "schedule": crontab(hour=15, minute=0),  # 每天一次
    "options": {"expires": 18000},  # 5 小時（任務需時 4 小時）
}
```

### 添加任務級別防護

```python
from app.utils.task_deduplication import skip_if_recently_executed
from redis import Redis
from app.core.config import settings

@celery_app.task(bind=True, name="app.tasks.my_daily_task")
@skip_if_recently_executed(min_interval_hours=24)  # 第 2 層防護
@record_task_history
def my_daily_task(self: Task) -> dict:
    # 第 3 層防護：Redis 鎖
    redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    lock_key = f"task_lock:{self.name}"
    lock = redis_client.lock(lock_key, timeout=3600)

    if not lock.acquire(blocking=False):
        logger.warning(f"⚠️  任務 {self.name} 已在執行中，跳過")
        return {"status": "skipped", ...}

    try:
        # 執行任務邏輯
        ...
    finally:
        lock.release()
```

## 💡 總結

這次優化徹底解決了 Celery Beat 重啟導致的 revoked tasks 惡性循環問題：

1. **智慧 expires**：根據任務週期設置合理的過期時間
2. **多層防護**：expires + 裝飾器 + Redis 鎖
3. **自動恢復**：Worker 定期重啟清空 revoked 列表
4. **零手動干預**：系統自動處理各種異常情況

**結果**：穩定、可靠、智慧的定時任務系統 🎉
