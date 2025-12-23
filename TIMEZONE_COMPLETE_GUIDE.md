# QuantLab 時區處理完整指南

**創建日期**: 2025-12-23
**版本**: 1.0
**維護者**: 開發團隊
**目的**: 統一系統時區處理策略與實作規範

---

## 📋 目錄

1. [系統時區策略](#系統時區策略)
2. [各層時區處理規則](#各層時區處理規則)
3. [Celery 時區配置](#celery-時區配置)
4. [前端時區顯示規範](#前端時區顯示規範)
5. [timezone_helpers.py 使用指南](#timezone_helperspy-使用指南)
6. [常見場景與代碼示例](#常見場景與代碼示例)
7. [檢查清單](#檢查清單)
8. [故障排除](#故障排除)

---

## 系統時區策略

### 核心原則

**統一使用 UTC 時區**：整個系統（資料庫、應用層、Celery）統一使用 UTC 時區儲存和處理時間。

**為什麼選擇 UTC？**
- ✅ 避免夏令時問題
- ✅ 便於跨時區協作
- ✅ 符合國際標準
- ✅ 簡化時區轉換邏輯

### 架構概覽

```
┌─────────────────────────────────────────────────────────┐
│                      前端層                              │
│  顯示：台灣時間 (UTC+8) + 標註 "(台北時間)"              │
└────────────────────┬────────────────────────────────────┘
                     │ API (ISO 8601 + 時區)
                     ↓
┌─────────────────────────────────────────────────────────┐
│                     後端層                               │
│  處理：UTC timezone-aware datetime                      │
│  - API 層：解析/序列化 datetime                         │
│  - Service 層：業務邏輯                                  │
│  - Repository 層：資料訪問                               │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│                   資料庫層                               │
│  儲存：TIMESTAMPTZ (UTC)                                │
│  例外：stock_minute_prices 使用台灣時間（見下方說明）   │
└─────────────────────────────────────────────────────────┘
```

### 例外情況

**stock_minute_prices 表**：使用台灣時區（timezone-naive）

**原因**：
- 包含 60M+ 行數據且被 TimescaleDB 壓縮
- 修改欄位類型需要解壓所有 chunks（數小時）
- 數據已儲存為台灣時間，轉換風險高

**處理方式**：使用 `timezone_helpers.py` 提供的轉換函數

---

## 各層時區處理規則

### 1. Model 層（資料庫）

#### ✅ 正確做法

```python
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func

class Stock(Base):
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

**關鍵點**：
- 使用 `DateTime(timezone=True)` - 對應 PostgreSQL 的 `TIMESTAMPTZ`
- 使用 `func.now()` - 資料庫層級時間戳，確保一致性
- **不要使用** `datetime.utcnow`（Python 3.12+ 已棄用）

#### ❌ 錯誤做法

```python
# ❌ 不要這樣做
from datetime import datetime

class Stock(Base):
    created_at = Column(DateTime, default=datetime.utcnow)  # 缺少 timezone=True
    updated_at = Column(DateTime, default=datetime.now)     # 使用 naive datetime
```

### 2. Repository 層（資料訪問）

#### stock_minute_prices 的特殊處理

```python
from app.utils.timezone_helpers import utc_to_naive_taipei, naive_taipei_to_utc

def get_by_stock(db: Session, stock_id: str, start_datetime: datetime, end_datetime: datetime):
    """
    ⚠️ stock_minute_prices 使用台灣時間，需要轉換
    """
    # 如果傳入 UTC aware datetime，轉換為台灣 naive datetime
    if start_datetime and start_datetime.tzinfo is not None:
        start_datetime = utc_to_naive_taipei(start_datetime)

    if end_datetime and end_datetime.tzinfo is not None:
        end_datetime = utc_to_naive_taipei(end_datetime)

    return db.query(StockMinutePrice).filter(
        StockMinutePrice.stock_id == stock_id,
        StockMinutePrice.datetime >= start_datetime,
        StockMinutePrice.datetime <= end_datetime
    ).all()
```

#### 其他資料表（標準處理）

```python
from app.utils.timezone_helpers import now_utc, parse_datetime_safe

def create_backtest(db: Session, data: BacktestCreate):
    """
    標準資料表使用 UTC timezone-aware datetime
    """
    # 解析用戶輸入的時間（確保 timezone-aware）
    start_datetime = parse_datetime_safe(data.start_datetime)

    backtest = Backtest(
        start_datetime=start_datetime,
        created_at=now_utc(),  # 使用 UTC 時間
        **data.dict()
    )
    db.add(backtest)
    db.commit()
    return backtest
```

### 3. Service 層（業務邏輯）

```python
from datetime import datetime, timezone, date
from app.utils.timezone_helpers import now_utc, parse_datetime_safe, today_taiwan

class BacktestService:
    def create_backtest(self, data: BacktestCreate):
        # ✅ 使用 now_utc() 記錄時間戳
        current_time = now_utc()

        # ✅ 解析用戶輸入的日期/時間（確保 timezone-aware）
        if isinstance(data.start_date, str):
            start_date = date.fromisoformat(data.start_date)

        if isinstance(data.start_datetime, str):
            start_datetime = parse_datetime_safe(data.start_datetime)

        # ✅ 獲取台灣今日日期（用於市場數據）
        taiwan_today = today_taiwan()

        # 業務邏輯...
        return self.repository.create(data)
```

### 4. API 層（路由）

```python
from fastapi import APIRouter, Depends
from datetime import datetime, timezone
from app.utils.timezone_helpers import parse_datetime_safe

router = APIRouter()

@router.get("/backtests/{backtest_id}")
def get_backtest(backtest_id: int, db: Session = Depends(get_db)):
    """
    API 返回的 datetime 會自動序列化為 ISO 8601 格式（帶時區）
    """
    backtest = BacktestRepository.get_by_id(db, backtest_id)

    # Pydantic v2 會自動正確序列化 timezone-aware datetime
    # 輸出: {"created_at": "2025-12-20T00:18:21+00:00"}
    return backtest

@router.post("/backtests/")
def create_backtest(data: BacktestCreate, db: Session = Depends(get_db)):
    """
    API 接收的 datetime 字符串會自動解析
    """
    # ✅ 使用 parse_datetime_safe 確保 timezone-aware
    start_datetime = parse_datetime_safe(data.start_datetime)

    return BacktestService.create_backtest(db, data)
```

### 5. Celery 任務層

```python
from celery import shared_task
from datetime import datetime, timezone
from app.utils.timezone_helpers import now_utc

@shared_task
def sync_daily_prices():
    """
    Celery 任務使用 UTC 時區

    注意：Celery 配置為 timezone="UTC", enable_utc=True
    """
    start_time = now_utc()  # ✅ 使用 UTC 時間

    # 任務邏輯...

    duration = (now_utc() - start_time).total_seconds()
    print(f"Task completed in {duration} seconds")
```

### 6. Scripts 層

```python
from datetime import datetime, timezone, date
from app.utils.timezone_helpers import now_utc, today_taiwan

def main():
    """
    腳本應該始終使用 UTC 時間記錄
    """
    start_time = now_utc()  # ✅ 記錄開始時間

    # 如果需要台灣今日日期
    taiwan_today = today_taiwan()

    # 腳本邏輯...

    end_time = now_utc()
    duration = (end_time - start_time).total_seconds()
    print(f"Script completed at {end_time.isoformat()}, duration: {duration}s")

if __name__ == "__main__":
    main()
```

### 7. 前端層

```typescript
// frontend/composables/useDateTime.ts

// ✅ 使用 composable 進行時區轉換
import { useDateTime } from '@/composables/useDateTime'

const { formatToTaiwanTime, formatRelativeTime } = useDateTime()

// 顯示後端返回的 UTC 時間
const displayTime = formatToTaiwanTime(backtest.created_at)
// "2025-12-20 08:18:21" (台灣時間)

// ❌ 不要直接使用 new Date()
const wrongTime = new Date(backtest.created_at).toLocaleString()  // 可能顯示錯誤時區
```

---

## Celery 時區配置

### 當前配置

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

### 重要說明

- **所有時間使用 UTC**：Celery 配置為 `timezone="UTC"`, `enable_utc=True`
- **定時任務 crontab 使用 UTC 時間**：例如 `crontab(hour=21, minute=0)` 表示 UTC 21:00（台北時間隔天 05:00）
- **應用層時區轉換**：應用代碼使用 `datetime.now(timezone.utc)` 獲取 UTC 時間，必要時轉換為台灣時間
- **一致性策略**：資料庫、Celery、應用層全部統一使用 UTC，避免時區混亂

### crontab 時間解讀規則

**關鍵原則**：crontab 參數使用 UTC 時間，需要在腦中換算為台北時間（+8 小時）

| crontab 配置 | UTC 時間 | 台北時間 | 說明 |
|-------------|---------|---------|------|
| `hour=0, minute=0` | 00:00 | 08:00 | 台灣早上 8 點 |
| `hour=1, minute=0` | 01:00 | 09:00 | 台灣早上 9 點 |
| `hour='1-5', minute='*/15'` | 01:00-05:59 | 09:00-13:59 | 交易時段每 15 分鐘 |
| `hour=7, minute=0` | 07:00 | 15:00 | 台灣下午 3 點 |
| `hour=13, minute=0` | 13:00 | 21:00 | 台灣晚上 9 點 |
| `hour=21, minute=0` | 21:00 | 次日 05:00 | 台灣隔天凌晨 5 點 |

### 定時任務配置範例

```python
# backend/app/core/celery_app.py
celery_app.conf.beat_schedule = {
    # 每天台灣時間 08:00 執行
    "sync-stock-list-daily": {
        "task": "app.tasks.sync_stock_list",
        "schedule": crontab(hour=0, minute=0),  # UTC 00:00 = Taiwan 08:00
        "options": {"expires": 3600},
    },

    # 交易日台灣時間 09:00-13:59 每 15 分鐘執行
    "sync-latest-prices-frequent": {
        "task": "app.tasks.sync_latest_prices",
        "schedule": crontab(
            minute='*/15',
            hour='1-5',  # UTC 01:00-05:59 = Taiwan 09:00-13:59
            day_of_week='mon,tue,wed,thu,fri'
        ),
        # Note: 移除 expires 設置，避免 Beat 重啟後任務被標記為過期
    },

    # 每天台灣時間 21:00 執行
    "sync-daily-prices": {
        "task": "app.tasks.sync_daily_prices",
        "schedule": crontab(hour=13, minute=0),  # UTC 13:00 = Taiwan 21:00
        "options": {"expires": 7200},
    },
}
```

### 驗證方法

```bash
# 1. 確認 Celery 配置
docker compose exec backend python -c "
from app.core.celery_app import celery_app
print(f'timezone: {celery_app.conf.timezone}')
print(f'enable_utc: {celery_app.conf.enable_utc}')
"
# 預期輸出：
# timezone: UTC
# enable_utc: True

# 2. 檢查定時任務排程
docker compose exec backend celery -A app.core.celery_app inspect scheduled

# 3. 查看 Beat 日誌（時間戳為 UTC）
docker compose logs celery-beat --tail=100
```

---

## 前端時區顯示規範

### 顯示標準

**核心原則**：統一顯示台灣時間並標註時區（避免用戶混淆）

| 顯示內容 | 格式 | 標註時區 | 範例 |
|---------|------|---------|------|
| **完整日期時間** | `YYYY/MM/DD HH:mm:ss` | ✅ 必須 | `2025/12/22 13:45:00 (台北時間)` |
| **日期** | `YYYY/MM/DD` | ⚠️ 選填 | `2025/12/22` 或 `2025/12/22 (台北)` |
| **時間範圍** | `HH:mm-HH:mm` | ✅ 必須 | `09:00-13:59 (台北時間)` |
| **Crontab 排程** | 人類可讀 + 時區 | ✅ 必須 | `交易日 09:00-13:59 每 15 分鐘 (台北時間)` |
| **相對時間** | `N 分鐘前` | ❌ 不需要 | `3 分鐘前` |

### 前端實作

#### ✅ 正確範例

```vue
<template>
  <div>
    <!-- 完整日期時間 -->
    <div>
      最後執行: {{ formatToTaiwanTime(task.last_run) }}
      <span class="text-gray-500 text-sm">(台北時間)</span>
    </div>

    <!-- 時間範圍（Crontab） -->
    <div>排程: {{ task.schedule }}</div>
    <!-- 後端已包含時區標註，例如："交易日 09:00-13:59 每 15 分鐘 (台北時間)" -->

    <!-- 表格標題 -->
    <th>註冊時間 (台北時間)</th>
    <th>最後登入 (台北時間)</th>
  </div>
</template>

<script setup lang="ts">
import { useDateTime } from '@/composables/useDateTime'
const { formatToTaiwanTime } = useDateTime()
</script>

<style scoped>
.text-gray-500 {
  color: #6b7280;
}
</style>
```

#### ❌ 錯誤範例

```vue
<!-- ❌ 沒有標註時區，用戶不知道是 UTC 還是台北時間 -->
<div>最後執行: {{ formatToTaiwanTime(task.last_run) }}</div>

<!-- ❌ 使用原生 JS，可能顯示錯誤時區 -->
<div>{{ new Date(task.last_run).toLocaleString() }}</div>

<!-- ❌ 排程沒有標註時區 -->
<div>排程: 交易日 01:00-05:59</div>
```

### 後端 Crontab 格式化

```python
# backend/app/api/v1/admin.py

def format_crontab_schedule(schedule) -> str:
    """
    將 crontab schedule 轉換為人類可讀的文字

    重要：Celery 配置為 timezone="UTC", enable_utc=True
    因此 crontab 的時間參數是 UTC 時間，需要轉換為台北時間顯示！

    Examples:
        crontab(hour=1, minute=0) -> "每天 09:00 (台北時間)"
        crontab(hour='1-5', minute='*/15', day_of_week='mon,tue,wed,thu,fri')
        -> "交易日 09:00-13:59 每 15 分鐘 (台北時間)"
    """
    def utc_to_taipei(hour_utc: int) -> int:
        """Convert UTC hour to Taipei hour (UTC+8)"""
        return (hour_utc + 8) % 24

    # ... 實作時必須將 UTC 時間轉換為台北時間（+8 小時）
    # ... 並在返回字符串末尾加上 " (台北時間)"
```

---

## timezone_helpers.py 使用指南

### 可用函數

```python
from app.utils.timezone_helpers import (
    now_utc,                # 獲取當前 UTC 時間（timezone-aware）
    now_taipei_naive,       # 獲取當前台灣時間（naive）
    today_taiwan,           # 獲取台灣今日日期
    parse_datetime_safe,    # 解析 datetime 並確保 timezone-aware
    utc_to_naive_taipei,    # UTC → 台灣 naive
    naive_taipei_to_utc,    # 台灣 naive → UTC
)
```

### 1. now_utc()

**用途**：記錄時間戳、獲取當前時間

```python
from app.utils.timezone_helpers import now_utc

# ✅ 記錄操作時間
task = RDAgentTask(
    created_at=now_utc(),
    ...
)

# ✅ 計算時間差
start = now_utc()
# ... 執行操作 ...
duration = (now_utc() - start).total_seconds()
```

### 2. parse_datetime_safe()

**用途**：解析 API 輸入、確保 datetime 是 timezone-aware

```python
from app.utils.timezone_helpers import parse_datetime_safe

# ✅ 解析字符串（自動處理各種格式）
dt1 = parse_datetime_safe("2025-12-20T08:18:21+08:00")  # 帶時區
dt2 = parse_datetime_safe("2025-12-20T08:18:21")        # 無時區（假設 UTC）

# ✅ 確保 datetime 對象是 timezone-aware
dt_naive = datetime(2025, 12, 20, 8, 18, 21)
dt_aware = parse_datetime_safe(dt_naive)  # 假設為 UTC 並添加時區
```

### 3. today_taiwan()

**用途**：獲取台灣市場當前日期

```python
from app.utils.timezone_helpers import today_taiwan

# ✅ 獲取台灣今日日期（用於查詢當日市場數據）
taiwan_today = today_taiwan()
stocks = db.query(StockPrice).filter(StockPrice.date == taiwan_today).all()

# ❌ 不要使用 UTC 日期
utc_today = datetime.now(timezone.utc).date()  # 可能與台灣日期不同！
```

### 4. utc_to_naive_taipei() / naive_taipei_to_utc()

**用途**：stock_minute_prices 表的時區轉換

```python
from app.utils.timezone_helpers import utc_to_naive_taipei, naive_taipei_to_utc

# 寫入 stock_minute_prices
utc_time = now_utc()
record = StockMinutePrice(
    datetime=utc_to_naive_taipei(utc_time),  # UTC → 台灣 naive
    ...
)

# 讀取 stock_minute_prices
result = db.query(StockMinutePrice).first()
utc_time = naive_taipei_to_utc(result.datetime)  # 台灣 naive → UTC
```

---

## 常見場景與代碼示例

### 場景 1: 創建新記錄並記錄時間戳

```python
from app.utils.timezone_helpers import now_utc

def create_strategy(db: Session, data: StrategyCreate):
    strategy = Strategy(
        name=data.name,
        created_at=now_utc(),  # ✅ 使用 UTC 時間戳
        updated_at=now_utc(),
        ...
    )
    db.add(strategy)
    db.commit()
    return strategy
```

### 場景 2: 查詢分鐘線數據（stock_minute_prices）

```python
from app.utils.timezone_helpers import utc_to_naive_taipei

def get_minute_prices(db: Session, stock_id: str, start_utc: datetime, end_utc: datetime):
    """
    查詢分鐘線數據（需要時區轉換）

    Args:
        start_utc: UTC timezone-aware datetime
        end_utc: UTC timezone-aware datetime
    """
    # ✅ 轉換 UTC → 台灣 naive（stock_minute_prices 使用台灣時間）
    start_taipei = utc_to_naive_taipei(start_utc)
    end_taipei = utc_to_naive_taipei(end_utc)

    return db.query(StockMinutePrice).filter(
        StockMinutePrice.stock_id == stock_id,
        StockMinutePrice.datetime >= start_taipei,
        StockMinutePrice.datetime <= end_taipei
    ).all()
```

### 場景 3: 獲取台灣市場當日數據

```python
from app.utils.timezone_helpers import today_taiwan

def get_today_market_data(db: Session):
    """
    獲取台灣市場當日數據

    重要：使用 today_taiwan() 而非 datetime.now(timezone.utc).date()
    """
    # ✅ 台灣今日日期
    taiwan_today = today_taiwan()

    # 查詢當日數據
    return db.query(StockPrice).filter(
        StockPrice.date == taiwan_today
    ).all()

# 範例：當 UTC 時間是 2025-12-20 17:00（台灣 2025-12-21 01:00）
# today_taiwan() → 2025-12-21 ✅ 正確
# datetime.now(timezone.utc).date() → 2025-12-20 ❌ 錯誤！
```

### 場景 4: Celery Beat 定時任務

```python
# backend/app/core/celery_app.py
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "sync-daily-prices": {
        "task": "app.tasks.sync_daily_prices",
        "schedule": crontab(hour=13, minute=0),  # UTC 13:00 = Taiwan 21:00
        "options": {"expires": 7200},
    },
}

# 任務實作
from app.utils.timezone_helpers import now_utc

@shared_task
def sync_daily_prices():
    start_time = now_utc()  # ✅ 使用 UTC 時間

    # 同步邏輯...

    logger.info(f"Sync completed at {start_time.isoformat()}")
```

---

## 檢查清單

### 新增功能時的時區檢查

- [ ] **Model 層**：所有 datetime 欄位使用 `DateTime(timezone=True)` 和 `func.now()`
- [ ] **Repository 層**：
  - [ ] stock_minute_prices 查詢/寫入使用 timezone_helpers 轉換
  - [ ] 其他表使用 timezone-aware datetime
- [ ] **Service 層**：
  - [ ] 使用 `now_utc()` 記錄時間戳
  - [ ] 使用 `parse_datetime_safe()` 解析輸入
  - [ ] 使用 `today_taiwan()` 獲取台灣日期
- [ ] **API 層**：Pydantic schema 正確序列化 datetime（不要手動加 'Z'）
- [ ] **Celery 任務**：crontab 時間使用 UTC（註解標註台灣時間對應）
- [ ] **Scripts**：使用 `now_utc()` 記錄開始/結束時間
- [ ] **前端**：使用 `useDateTime` composable 顯示時間，並標註 "(台北時間)"

### Code Review 時的檢查項目

- [ ] 沒有使用 `datetime.now()` 而不指定時區
- [ ] 沒有使用 `datetime.utcnow`（已棄用）
- [ ] 沒有使用 `datetime.strptime()` 而不處理時區
- [ ] stock_minute_prices 操作有正確的時區轉換
- [ ] Celery crontab 時間有正確的註解（UTC → Taiwan）
- [ ] 資料庫遷移中的 datetime 欄位包含 `timezone=True`
- [ ] 前端沒有直接使用 `new Date()` 進行顯示
- [ ] 前端時間顯示有 "(台北時間)" 標註

### 測試時的驗證項目

- [ ] 跨日期邊界測試（UTC 23:59 vs Taiwan 07:59）
- [ ] 台灣凌晨時段測試（確保使用正確的日期）
- [ ] API 返回的 datetime 格式正確（ISO 8601 + 時區）
- [ ] 分鐘線查詢返回正確時間段的數據
- [ ] Celery 任務在正確的台灣時間執行
- [ ] 前端顯示時間正確（台北時間）

---

## 故障排除

### 常見錯誤 1：使用 datetime.now() 而不指定時區

```python
# ❌ 錯誤：產生 naive datetime
now = datetime.now()

# ✅ 正確：使用 timezone-aware datetime
from app.utils.timezone_helpers import now_utc
now = now_utc()
```

### 常見錯誤 2：使用已棄用的 datetime.utcnow

```python
# ❌ 錯誤：Python 3.12+ 已棄用
from datetime import datetime
created_at = Column(DateTime, default=datetime.utcnow)

# ✅ 正確：使用 func.now()
from sqlalchemy.sql import func
created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 常見錯誤 3：忘記 stock_minute_prices 的時區轉換

```python
# ❌ 錯誤：直接使用 UTC 時間查詢（會查不到數據）
utc_time = now_utc()
results = db.query(StockMinutePrice).filter(
    StockMinutePrice.datetime >= utc_time
).all()

# ✅ 正確：轉換為台灣時間
from app.utils.timezone_helpers import utc_to_naive_taipei
taipei_time = utc_to_naive_taipei(utc_time)
results = db.query(StockMinutePrice).filter(
    StockMinutePrice.datetime >= taipei_time
).all()
```

### 常見錯誤 4：混用 naive 和 timezone-aware datetime

```python
# ❌ 錯誤：混用會導致 TypeError
naive_dt = datetime(2025, 12, 20, 9, 0, 0)
aware_dt = datetime(2025, 12, 20, 1, 0, 0, tzinfo=timezone.utc)
diff = aware_dt - naive_dt  # TypeError!

# ✅ 正確：統一使用 timezone-aware
from app.utils.timezone_helpers import parse_datetime_safe
aware_dt1 = parse_datetime_safe(naive_dt)  # 轉為 timezone-aware
aware_dt2 = datetime(2025, 12, 20, 1, 0, 0, tzinfo=timezone.utc)
diff = aware_dt2 - aware_dt1  # OK
```

### 常見錯誤 5：使用 UTC 日期查詢台灣市場數據

```python
# ❌ 錯誤：在台灣凌晨時會查到昨天的數據
from datetime import datetime, timezone
utc_today = datetime.now(timezone.utc).date()
stocks = db.query(StockPrice).filter(StockPrice.date == utc_today).all()

# ✅ 正確：使用台灣日期
from app.utils.timezone_helpers import today_taiwan
taiwan_today = today_taiwan()
stocks = db.query(StockPrice).filter(StockPrice.date == taiwan_today).all()
```

### 常見錯誤 6：前端未標註時區

```vue
<!-- ❌ 錯誤：沒有標註時區 -->
<div>最後執行: {{ formatToTaiwanTime(task.last_run) }}</div>

<!-- ✅ 正確：標註時區 -->
<div>最後執行: {{ formatToTaiwanTime(task.last_run) }} (台北時間)</div>
```

### 常見錯誤 7：Crontab 顯示 UTC 時間

```python
# ❌ 錯誤：直接顯示 UTC 時間，用戶會混淆
return "交易日 01:00-05:59"

# ✅ 正確：轉換為台北時間並標註
return "交易日 09:00-13:59 (台北時間)"
```

---

## 快速參考

### Import 語句

```python
# 標準庫
from datetime import datetime, timezone, date, timedelta

# SQLAlchemy
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func

# timezone_helpers
from app.utils.timezone_helpers import (
    now_utc,                # 當前 UTC 時間
    now_taipei_naive,       # 當前台灣時間（naive）
    today_taiwan,           # 台灣今日日期
    parse_datetime_safe,    # 解析 datetime（確保 timezone-aware）
    utc_to_naive_taipei,    # UTC → 台灣 naive
    naive_taipei_to_utc,    # 台灣 naive → UTC
)
```

### 常用模式

```python
# 記錄時間戳
created_at = now_utc()

# 解析 API 輸入
dt = parse_datetime_safe(input_datetime)

# 獲取台灣今日日期
today = today_taiwan()

# Model 定義
created_at = Column(DateTime(timezone=True), server_default=func.now())

# stock_minute_prices 轉換
taipei_time = utc_to_naive_taipei(utc_time)
utc_time = naive_taipei_to_utc(taipei_time)
```

---

## 相關文檔

- [CLAUDE.md](CLAUDE.md) - 開發指南
- [backend/app/utils/timezone_helpers.py](backend/app/utils/timezone_helpers.py) - 時區工具函數
- [CELERY_REVOKED_TASKS_FIX.md](CELERY_REVOKED_TASKS_FIX.md) - Celery Revoked Tasks 問題解決方案
- [frontend/composables/useDateTime.ts](frontend/composables/useDateTime.ts) - 前端時區轉換工具

---

**文檔版本**: 1.0
**最後更新**: 2025-12-23
**維護者**: 開發團隊
**涵蓋範圍**: 系統時區策略、各層處理規則、Celery 配置、前端顯示規範、工具使用、故障排除
