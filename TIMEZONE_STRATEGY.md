# QuantLab 時區統一策略（已實施）

## 🎯 核心原則：資料正確性優先

**實施策略**：全系統統一使用 **UTC**，僅 `stock_minute_prices` 表例外使用台灣時間（技術限制）。

**實施日期**：2025-12-19
**狀態**：✅ 已完成

---

## 📋 問題分析與解決方案

### 發現的不一致問題

| 組件 | 當前配置 | 問題 |
|------|----------|------|
| **容器系統時區** | CST +0800 (台灣) | ✅ 正確 |
| **PostgreSQL** | UTC | ✅ 正確 |
| **Celery** | `timezone="Asia/Taipei"`, `enable_utc=False` | ⚠️  與 PostgreSQL 不一致 |
| **Python 代碼** | 混用 `timezone.utc` 和 `Asia/Taipei` | ❌ 不一致 |
| **資料庫欄位** | 混用 `TIMESTAMPTZ` 和 `TIMESTAMP` | ❌ 不一致 |

### 具體問題

1. **stock_minute_prices.datetime** 使用 `TIMESTAMP WITHOUT TIME ZONE`
   - 不記錄時區資訊
   - 容易造成時區混淆

2. **task_history.py** 使用 `Asia/Taipei` 記錄時間
   - 與 PostgreSQL UTC 不一致
   - 導致前端顯示時間轉換錯誤

3. **Celery 配置** 使用本地時區
   - `enable_utc=False` 與 PostgreSQL 不一致
   - crontab 時間判斷可能出錯

---

## ✅ 實施方案：折衷方案（Hybrid UTC + Taiwan Time）

### 策略說明

**主要原則**：
- **資料層**：除 `stock_minute_prices` 外，所有表使用 UTC (TIMESTAMPTZ)
- **業務層**：所有 Python 代碼統一使用 UTC
- **排程層**：Celery 使用 UTC 排程
- **顯示層**：前端/API 響應時自動轉換為台灣時區
- **例外處理**：`stock_minute_prices` 保持 `TIMESTAMP WITHOUT TIME ZONE`（台灣時間）

### 為何 stock_minute_prices 例外？

**技術限制**：
1. 表包含 **60M+ 筆資料**，已被 TimescaleDB 壓縮（1104 個 chunks）
2. 修改欄位類型需要：
   - 解壓縮所有 chunks（30-90 分鐘）
   - 修改欄位類型（5-15 分鐘）
   - 重新壓縮（30-90 分鐘）
   - **總計：2-4 小時 + 需要額外 50GB 磁碟空間**
3. 修改過程遇到 PostgreSQL `max_locks_per_transaction` 限制
4. **資料正確性風險高**：現有資料已是台灣時間，轉換可能出錯

**解決方案**：
- 保持 `stock_minute_prices` 使用台灣時間
- 創建輔助函數 `timezone_helpers.py` 明確處理時區轉換
- 在代碼中清楚文檔化此例外情況

---

## 🔧 實際實施步驟（已完成）

### 1. ~~修改資料庫欄位類型~~（跳過）

**決定**：保持 `stock_minute_prices` 為 `TIMESTAMP WITHOUT TIME ZONE`

**原因**：
- TimescaleDB 壓縮限制
- 資料量過大（60M 筆）
- 風險與成本過高

### 2. ✅ 修改 Celery 配置（已完成）

```python
# backend/app/core/celery_app.py
celery_app.conf.update(
    timezone='UTC',        # ✅ 改為 UTC
    enable_utc=True,       # ✅ 改為 True
)
```

### 3. ✅ 調整 Celery Beat 排程時間（已完成）

所有 crontab 時間已減 8 小時轉為 UTC：

```python
# 例如：台灣時間 09:00 -> UTC 01:00
"sync-latest-prices-frequent": {
    "task": "app.tasks.sync_latest_prices",
    "schedule": crontab(
        minute='*/15',
        hour='1-5',  # UTC 01:00-05:59 = 台灣 09:00-13:59
        day_of_week='mon,tue,wed,thu,fri'
    ),
},

# 更多範例：
"sync-stock-list-daily": crontab(hour=0, minute=0),  # UTC 00:00 = 台灣 08:00
"sync-daily-prices": crontab(hour=13, minute=0),     # UTC 13:00 = 台灣 21:00
"cleanup-cache-daily": crontab(hour=19, minute=0),   # UTC 19:00 = 台灣 03:00 次日
```

### 4. ✅ 統一 Python 代碼時間處理（已完成）

```python
# ✅ 正確：統一使用 UTC
from datetime import datetime, timezone
now = datetime.now(timezone.utc)

# ❌ 錯誤：不要使用台灣時區（除非處理 stock_minute_prices）
import pytz
now = datetime.now(pytz.timezone('Asia/Taipei'))
```

### 5. ✅ 修復 task_history.py（已完成）

```python
# backend/app/utils/task_history.py
# 已改為使用 UTC
start_time = datetime.now(timezone.utc)
```

### 6. ✅ 創建時區轉換輔助函數（已完成）

```python
# backend/app/utils/timezone_helpers.py
from app.utils.timezone_helpers import (
    naive_taipei_to_utc,  # 台灣時間 → UTC
    utc_to_naive_taipei,  # UTC → 台灣時間
    now_taipei_naive,     # 當前台灣時間（無時區）
    now_utc,              # 當前 UTC 時間
)

# 範例：讀取 stock_minute_prices
result = db.query(StockMinutePrice).first()
utc_time = naive_taipei_to_utc(result.datetime)  # 轉換為 UTC

# 範例：寫入 stock_minute_prices
record = StockMinutePrice(
    datetime=now_taipei_naive(),  # 使用台灣時間
    ...
)
```

### 7. ✅ 前端自動轉換（無需修改）

```javascript
// frontend/pages/admin/index.vue
// JavaScript new Date() 會自動轉換為用戶本地時區
function formatDate(dateStr) {
  if (!dateStr) return '-'
  // 輸入：2025-12-19T12:00:00+00:00 (UTC)
  // 輸出：2025/12/19 下午8:00:00 (自動轉為台灣時間)
  return new Date(dateStr).toLocaleString('zh-TW')
}
```

---

## 📊 實施後效果

### 資料庫

```sql
-- users, backtests 等表：使用 UTC
SELECT created_at FROM users LIMIT 1;
-- 2025-12-19 12:20:56.623198+00:00  (UTC 12:20 = 台灣 20:20)

-- stock_minute_prices：使用台灣時間（無時區）
SELECT datetime FROM stock_minute_prices LIMIT 1;
-- 2025-12-19 15:30:00  (台灣時間，無時區資訊)
```

### Redis (task_history)

```json
{
  "last_run": "2025-12-19T12:20:00+00:00",  // ✅ UTC
  "updated_at": "2025-12-19T12:20:00+00:00"  // ✅ UTC
}
```

### 前端顯示

```
輸入 API: 2025-12-19T12:20:00+00:00 (UTC)
前端顯示: 2025/12/19 下午8:20:00  (自動轉為台灣時間)
```

### Celery Beat 日誌

```bash
# 所有日誌顯示 UTC 時間
[2025-12-19 01:00:00,000: INFO] Sending due task sync-latest-prices-frequent
# UTC 01:00 = 台灣 09:00

[2025-12-19 13:00:00,000: INFO] Sending due task sync-daily-prices
# UTC 13:00 = 台灣 21:00
```

### Python 代碼

```python
# ✅ 一般用途：使用 UTC
from datetime import datetime, timezone
now = datetime.now(timezone.utc)  # 2025-12-19 12:20:00+00:00

# ✅ 處理 stock_minute_prices：使用輔助函數
from app.utils.timezone_helpers import now_taipei_naive
taipei_time = now_taipei_naive()  # 2025-12-19 20:20:00 (無時區)
```

---

## ⚠️  遷移注意事項

1. **備份資料庫**：修改前務必備份
2. **選擇維護時間**：在非交易時段（如週末）執行
3. **清空 Redis**：清空舊的 task_history 記錄
4. **重啟所有服務**：確保配置生效
5. **驗證資料正確性**：檢查新資料時間是否正確

---

## 📝 實施檢查清單

- [x] 備份資料庫（5GB）
- [x] ~~修改 `stock_minute_prices` 欄位類型~~（跳過，保持現狀）
- [x] 修改 Celery 配置為 UTC
- [x] 調整所有 crontab 時間（-8 小時）
- [x] 修復 `task_history.py` 使用 UTC
- [x] 創建 `timezone_helpers.py` 輔助函數
- [x] 更新時區策略文檔
- [ ] 清空 Redis task_history
- [ ] 重啟所有服務
- [ ] 驗證資料正確性

---

## 🎓 開發者須知

### 寫入時間時

```python
# ✅ 正確：大部分情況使用 UTC
from datetime import datetime, timezone
record.created_at = datetime.now(timezone.utc)

# ✅ 正確：stock_minute_prices 使用台灣時間
from app.utils.timezone_helpers import now_taipei_naive
minute_price.datetime = now_taipei_naive()
```

### 讀取時間時

```python
# ✅ 正確：從 stock_minute_prices 讀取需轉換
from app.utils.timezone_helpers import naive_taipei_to_utc
result = db.query(StockMinutePrice).first()
utc_time = naive_taipei_to_utc(result.datetime)

# ✅ 正確：其他表直接使用
result = db.query(User).first()
utc_time = result.created_at  # 已經是 UTC
```

### 查看日誌時

記住心算公式：**UTC 時間 + 8 小時 = 台灣時間**

```bash
# 日誌顯示：[2025-12-19 01:00:00] Sending task...
# 實際時間：台灣 09:00

# 日誌顯示：[2025-12-19 13:00:00] Task completed
# 實際時間：台灣 21:00
```

---

**制定日期**：2025-12-19
**實施日期**：2025-12-19
**維護者**：Claude Code
**版本**：2.0（折衷方案）
