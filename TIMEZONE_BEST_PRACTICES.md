# QuantLab 時區處理最佳實踐

**創建日期**: 2025-12-20
**版本**: 1.0
**維護者**: 開發團隊

---

## 📋 目錄

1. [系統時區策略](#系統時區策略)
2. [各層時區處理規則](#各層時區處理規則)
3. [timezone_helpers.py 使用指南](#timezone_helperspy-使用指南)
4. [常見場景與代碼示例](#常見場景與代碼示例)
5. [注意事項與陷阱](#注意事項與陷阱)
6. [檢查清單](#檢查清單)

---

## 系統時區策略

### 核心原則

**統一使用 UTC 時區**：整個系統（資料庫、應用層、Celery）統一使用 UTC 時區儲存和處理時間。

### 例外情況

**stock_minute_prices 表**：使用 Taiwan 時區（timezone-naive）

**原因**：
- 包含 60M+ 行數據且被 TimescaleDB 壓縮
- 修改欄位類型需要解壓所有 chunks（數小時）
- 數據已儲存為台灣時間，轉換風險高

**處理方式**：使用 `timezone_helpers.py` 提供的轉換函數

---

## 各層時區處理規則

### 1. 資料庫層

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

### 2. Repository 層（資料訪問層）

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

### 3. Service 層（業務邏輯層）

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

### 4. API 層（路由層）

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

### 場景 2: 查詢日期範圍內的數據

```python
from datetime import date
from app.utils.timezone_helpers import parse_datetime_safe

def get_prices_in_range(db: Session, stock_id: str, start_date: str, end_date: str):
    # ✅ 解析日期（ISO 8601 格式）
    start = date.fromisoformat(start_date)  # "2025-12-01" → date(2025, 12, 1)
    end = date.fromisoformat(end_date)

    return db.query(StockPrice).filter(
        StockPrice.stock_id == stock_id,
        StockPrice.date >= start,
        StockPrice.date <= end
    ).all()
```

### 場景 3: 查詢分鐘線數據（stock_minute_prices）

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

### 場景 4: 處理 API 輸入的日期/時間

```python
from datetime import date
from pydantic import BaseModel
from app.utils.timezone_helpers import parse_datetime_safe

class BacktestCreate(BaseModel):
    start_date: str        # "2025-12-01"
    start_datetime: str    # "2025-12-01T09:00:00+08:00"

def create_backtest(data: BacktestCreate):
    # ✅ 解析日期
    start_date = date.fromisoformat(data.start_date)

    # ✅ 解析 datetime（確保 timezone-aware）
    start_datetime = parse_datetime_safe(data.start_datetime)

    # 使用解析後的值...
```

### 場景 5: 獲取台灣市場當日數據

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

### 場景 6: 計算任務執行時間

```python
from app.utils.timezone_helpers import now_utc

def execute_long_task():
    start_time = now_utc()

    # 執行任務...

    end_time = now_utc()
    duration = (end_time - start_time).total_seconds()

    logger.info(f"Task started at {start_time.isoformat()}")
    logger.info(f"Task completed at {end_time.isoformat()}")
    logger.info(f"Duration: {duration:.2f} seconds")
```

### 場景 7: Celery Beat 定時任務

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

## 注意事項與陷阱

### ❌ 常見錯誤

#### 1. 使用 datetime.now() 而不指定時區

```python
# ❌ 錯誤：產生 naive datetime
now = datetime.now()

# ✅ 正確：使用 timezone-aware datetime
from app.utils.timezone_helpers import now_utc
now = now_utc()
```

#### 2. 使用已棄用的 datetime.utcnow

```python
# ❌ 錯誤：Python 3.12+ 已棄用
from datetime import datetime
created_at = Column(DateTime, default=datetime.utcnow)

# ✅ 正確：使用 func.now()
from sqlalchemy.sql import func
created_at = Column(DateTime(timezone=True), server_default=func.now())
```

#### 3. 忘記 stock_minute_prices 的時區轉換

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

#### 4. 混用 naive 和 timezone-aware datetime

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

#### 5. 使用 UTC 日期查詢台灣市場數據

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

#### 6. 前端直接使用 new Date() 而不轉換時區

```typescript
// ❌ 錯誤：顯示可能不正確
const displayTime = new Date(backtest.created_at).toLocaleString()

// ✅ 正確：使用 composable 轉換
import { useDateTime } from '@/composables/useDateTime'
const { formatToTaiwanTime } = useDateTime()
const displayTime = formatToTaiwanTime(backtest.created_at)
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
- [ ] **前端**：使用 `useDateTime` composable 顯示時間

### Code Review 時的檢查項目

- [ ] 沒有使用 `datetime.now()` 而不指定時區
- [ ] 沒有使用 `datetime.utcnow`（已棄用）
- [ ] 沒有使用 `datetime.strptime()` 而不處理時區
- [ ] stock_minute_prices 操作有正確的時區轉換
- [ ] Celery crontab 時間有正確的註解（UTC → Taiwan）
- [ ] 資料庫遷移中的 datetime 欄位包含 `timezone=True`
- [ ] 前端沒有直接使用 `new Date()` 進行顯示

### 測試時的驗證項目

- [ ] 跨日期邊界測試（UTC 23:59 vs Taiwan 07:59）
- [ ] 台灣凌晨時段測試（確保使用正確的日期）
- [ ] API 返回的 datetime 格式正確（ISO 8601 + 時區）
- [ ] 分鐘線查詢返回正確時間段的數據
- [ ] Celery 任務在正確的台灣時間執行

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

**文檔版本**: 1.0
**最後更新**: 2025-12-20
**相關文檔**:
- [CLAUDE.md](CLAUDE.md) - 開發指南
- [backend/app/utils/timezone_helpers.py](backend/app/utils/timezone_helpers.py) - 時區工具函數
- [CELERY_TIMEZONE_EXPLAINED.md](CELERY_TIMEZONE_EXPLAINED.md) - Celery 時區配置詳解
