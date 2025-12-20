# QuantLab 時區處理安全審查報告

**審查日期**: 2025-12-20
**審查者**: Code Review Agent
**系統版本**: QuantLab v1.0
**審查範圍**: 資料庫層、API層、任務調度層、前端顯示層

---

## 📋 執行摘要

本次審查深入檢查了 QuantLab 系統中的時區處理機制，發現系統已實施 **Hybrid UTC + Taiwan Time** 策略。總體而言，系統在時區處理上**基本正確**，但仍存在 **3 個嚴重問題**、**5 個警告級問題** 和 **2 個資訊級注意事項**。

**關鍵發現**:
- ✅ 已建立 `timezone_helpers.py` 輔助函數
- ✅ Celery 已正確配置為 UTC
- ✅ 前端已實作自動時區轉換
- 🔴 **Critical**: `institutional_investors` 表使用 `DateTime` 而非 `DateTime(timezone=True)`
- 🔴 **Critical**: Option 相關表使用 `TIMESTAMP` 而非 `TIMESTAMPTZ`
- 🟡 **Warning**: 多處使用 `.date()` 可能導致時區錯誤

---

## 🔴 Critical Issues (必須修復)

### 1. institutional_investors 表缺少時區資訊

**問題描述**:
```python
# backend/app/models/institutional_investor.py (Line 39-40)
created_at = Column(DateTime, server_default=func.now(), nullable=False)
updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
```

**問題**:
- 使用 `DateTime` 而非 `DateTime(timezone=True)`
- 資料庫欄位為 `TIMESTAMP WITHOUT TIME ZONE`
- PostgreSQL `func.now()` 返回 UTC，但欄位不記錄時區資訊

**影響**:
- 時間戳記無法確定是 UTC 還是本地時間
- 與系統其他表（使用 `TIMESTAMPTZ`）不一致
- 可能導致查詢時時間比對錯誤

**修復方案**:
```python
# 修改模型
created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
```

**遷移腳本**:
```python
# alembic/versions/fix_institutional_timezone.py
def upgrade():
    op.execute("""
        ALTER TABLE institutional_investors
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';
    """)
    op.execute("""
        ALTER TABLE institutional_investors
        ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC';
    """)
```

---

### 2. Option 相關表使用 TIMESTAMP 而非 TIMESTAMPTZ

**問題描述**:
```python
# backend/app/models/option.py
# OptionContract (Line 91-100)
created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'), nullable=False)
updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'), nullable=False)

# OptionDailyFactor (Line 234-238)
created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'), nullable=False)

# OptionMinutePrice (Line 277-280)
datetime = Column(TIMESTAMP, nullable=False, comment="時間戳記")

# OptionGreeks (Line 367-370)
datetime = Column(TIMESTAMP, nullable=False, comment="時間戳記")

# OptionSyncConfig (Line 473-477)
updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'), nullable=False)
```

**問題**:
- 所有 Option 相關表的 datetime 欄位都缺少時區資訊
- 與系統設計原則不一致（除 `stock_minute_prices` 外應使用 UTC）
- `CURRENT_TIMESTAMP` 在 PostgreSQL 返回時區感知時間，但 `TIMESTAMP` 會丟棄時區

**影響**:
- 選擇權數據時間戳記可能誤解為台灣時間或 UTC
- 跨時區回測時會出錯
- 與期貨數據（使用台灣時間）混用時容易混淆

**修復方案**:
```python
# 1. 修改模型（除 OptionMinutePrice.datetime 和 OptionGreeks.datetime 外）
from sqlalchemy import DateTime
from sqlalchemy.sql import func

# OptionContract
created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# OptionDailyFactor
created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# OptionSyncConfig
updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

**特殊處理 - OptionMinutePrice 和 OptionGreeks**:

由於這兩張表是 TimescaleDB hypertable，且參考 `stock_minute_prices` 的設計，建議：

**選項 A（推薦）**: 保持 `TIMESTAMP`（台灣時間），並創建對應的時區轉換函數
```python
# 在 timezone_helpers.py 中新增
def option_datetime_to_utc(dt: datetime) -> datetime:
    """Convert option_minute_prices/option_greeks datetime to UTC"""
    return naive_taipei_to_utc(dt)

def utc_to_option_datetime(dt: datetime) -> datetime:
    """Convert UTC to option_minute_prices/option_greeks datetime"""
    return utc_to_naive_taipei(dt)
```

**選項 B**: 改為 `TIMESTAMPTZ`（需要在資料量小時修改）
```sql
ALTER TABLE option_minute_prices
ALTER COLUMN datetime TYPE TIMESTAMP WITH TIME ZONE USING datetime AT TIME ZONE 'Asia/Taipei';

ALTER TABLE option_greeks
ALTER COLUMN datetime TYPE TIMESTAMP WITH TIME ZONE USING datetime AT TIME ZONE 'Asia/Taipei';
```

---

### 3. Celery Beat Schedule 與 TIMEZONE_STRATEGY.md 不一致

**問題描述**:

根據 `TIMEZONE_STRATEGY.md` (2025-12-19 制定)，系統已統一改為 UTC，但發現：

```python
# backend/app/core/celery_app.py (Line 17-18)
timezone="UTC",  # ✅ 統一使用 UTC 時區
enable_utc=True,  # ✅ 啟用 UTC 模式
```

**實際狀態**: ✅ **已正確配置**

**但是**，文檔中的檢查清單顯示：
```markdown
- [ ] 清空 Redis task_history  # ❌ 未完成
- [ ] 重啟所有服務              # ❌ 未完成
- [ ] 驗證資料正確性            # ❌ 未完成
```

**風險**:
- 如果 Redis 中仍有舊的台灣時區 task_history，可能導致任務執行時間判斷錯誤
- 未重啟服務可能導致配置未生效

**驗證命令**:
```bash
# 檢查 Celery Worker 是否使用 UTC
docker compose exec celery-worker celery -A app.core.celery_app inspect conf | grep -E "(timezone|enable_utc)"

# 檢查 Redis task_history
docker compose exec redis redis-cli --scan --pattern "task_history:*" | head -5

# 驗證任務執行時間
docker compose logs celery-beat | grep "Scheduler" | tail -5
```

**修復方案**:
```bash
# 1. 清空 Redis task_history
docker compose exec redis redis-cli --scan --pattern "task_history:*" | \
  xargs -L 1 docker compose exec -T redis redis-cli DEL

# 2. 重啟所有服務
docker compose restart backend celery-worker celery-beat

# 3. 驗證
docker compose logs celery-beat -f
# 觀察任務是否在正確的 UTC 時間觸發
```

---

## 🟡 Warning Issues (建議修復)

### 4. 多處使用 `.date()` 轉換可能丟失時區資訊

**問題描述**:

在多個 Service 層發現使用 `.date()` 轉換，可能導致時區錯誤：

```python
# backend/app/services/strategy_signal_detector.py (Line 多處)
end_date = datetime.now(timezone.utc).date()  # ✅ 正確：先取 UTC 再轉日期
recent_signals = [s for s in signals if s['datetime'].date() == last_date.date()]  # ⚠️ 風險

# backend/app/services/backtest_engine.py (Line 多處)
start_date = datetime.fromisoformat(start_date).date()  # ⚠️ 風險：fromisoformat 可能丟失時區
end_date = start_date.date()  # ⚠️ 風險：如果 start_date 是台灣時間會錯誤
```

**問題**:
- `datetime.fromisoformat()` 如果輸入字串沒有時區資訊，會返回 naive datetime
- 對 naive datetime 調用 `.date()` 無法確定是哪個時區的日期
- 在跨時區場景下，同一個 UTC 時間在不同時區的日期可能不同

**範例問題**:
```python
# 假設用戶在台灣（UTC+8）輸入日期 "2025-12-20"
# 前端可能發送 "2025-12-20" 或 "2025-12-20T00:00:00"
# 但沒有時區資訊！

# 錯誤處理
start_date = datetime.fromisoformat("2025-12-20").date()  # naive datetime
# → 2025-12-20（但不知道是 UTC 還是台灣時間）

# 正確處理
from datetime import timezone
start_datetime = datetime.fromisoformat("2025-12-20").replace(tzinfo=timezone.utc)
start_date = start_datetime.date()  # 明確是 UTC 的日期
```

**修復方案**:

在 `backtest_engine.py` 中統一處理日期輸入：

```python
def _parse_date_input(date_input: str | datetime | date) -> date:
    """
    安全地解析日期輸入，確保時區一致性

    Args:
        date_input: 日期字串、datetime 或 date 物件

    Returns:
        date 物件（基於 UTC）
    """
    if isinstance(date_input, str):
        # 解析字串為 datetime
        dt = datetime.fromisoformat(date_input)
        # 如果沒有時區資訊，假定為 UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.date()
    elif isinstance(date_input, datetime):
        # 如果是 naive datetime，假定為 UTC
        if date_input.tzinfo is None:
            logger.warning(f"Received naive datetime, assuming UTC: {date_input}")
            date_input = date_input.replace(tzinfo=timezone.utc)
        return date_input.date()
    elif isinstance(date_input, date):
        return date_input
    else:
        raise TypeError(f"Invalid date input type: {type(date_input)}")
```

---

### 5. Shioaji API 返回時間的時區未明確處理

**問題描述**:

```python
# backend/app/services/shioaji_client.py (Line 436-437)
timestamp_ns = kbars.ts[i]
dt = pd.to_datetime(timestamp_ns, unit='ns')
```

**問題**:
- Shioaji API 返回的時間戳記可能是台灣時間或 UTC（文檔未明確說明）
- `pd.to_datetime(timestamp_ns, unit='ns')` 會返回 UTC naive datetime
- 未驗證返回的時間是否正確

**驗證測試**:
```python
# 添加測試代碼
def test_shioaji_timezone():
    with ShioajiClient() as client:
        df = client.get_kbars('2330',
            start_datetime=datetime(2025, 12, 19, 9, 0),
            end_datetime=datetime(2025, 12, 19, 13, 30),
            timeframe='1min'
        )

        # 檢查第一筆數據的時間
        first_time = df.iloc[0]['datetime']
        print(f"First bar time: {first_time}")
        print(f"Timezone: {first_time.tzinfo}")

        # 驗證：台股開盤是 09:00（台灣時間）
        # 如果是 UTC，應該是 01:00
        # 如果是台灣時間，應該是 09:00
```

**修復方案**:

在 `ShioajiClient.get_kbars()` 中明確處理時區：

```python
# 轉換為 DataFrame
for i in range(len(kbars.ts)):
    timestamp_ns = kbars.ts[i]
    dt = pd.to_datetime(timestamp_ns, unit='ns')

    # ⚠️ 驗證：Shioaji 返回的時間是 UTC 還是台灣時間？
    # 根據測試結果，假設返回台灣時間（需要實際驗證）
    if dt.tzinfo is None:
        # 假定為台灣時間，轉換為 UTC
        from app.utils.timezone_helpers import naive_taipei_to_utc
        dt = naive_taipei_to_utc(dt)
        logger.debug(f"Converted Shioaji time to UTC: {dt}")

    data.append({
        'datetime': dt,
        ...
    })
```

---

### 6. API 端點未驗證日期參數的時區

**問題描述**:

```python
# backend/app/api/v1/data.py (Line 252-253)
start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
```

**問題**:
- 用戶輸入 "2025-12-20" 時，沒有時區資訊
- `strptime` 返回 naive datetime
- 可能導致日期邊界錯誤（例如用戶想查 "2025-12-20"，但系統可能查到 "2025-12-19 16:00 UTC" 到 "2025-12-20 15:59 UTC"）

**修復方案**:

統一假定用戶輸入的日期為**台灣時區的日期**（符合台股用戶習慣）：

```python
from datetime import timezone
import pytz

TAIWAN_TZ = pytz.timezone('Asia/Taipei')

def parse_date_param(date_str: str | None) -> date | None:
    """
    解析日期參數（假定為台灣時區）

    Args:
        date_str: YYYY-MM-DD 格式字串

    Returns:
        date 物件（UTC）
    """
    if not date_str:
        return None

    # 解析為台灣時區的日期開始時間
    naive_dt = datetime.strptime(date_str, "%Y-%m-%d")
    taiwan_dt = TAIWAN_TZ.localize(naive_dt)
    utc_dt = taiwan_dt.astimezone(timezone.utc)

    return utc_dt.date()

# 使用
start = parse_date_param(start_date)
end = parse_date_param(end_date)
```

**或者**，明確要求前端傳遞時區資訊：

```python
# API Schema
class OHLCVRequest(BaseModel):
    stock_id: str
    start_date: str = Field(..., description="開始日期（YYYY-MM-DD，台灣時區）")
    end_date: str = Field(..., description="結束日期（YYYY-MM-DD，台灣時區）")
    timezone: str = Field(default="Asia/Taipei", description="時區")
```

---

### 7. 前端日期選擇器未指定時區

**問題描述**:

前端使用原生 HTML `<input type="date">` 或 JavaScript Date 物件時，瀏覽器會使用**用戶本地時區**。

**問題場景**:
1. 台灣用戶選擇 "2025-12-20" → 瀏覽器傳送 `2025-12-20T00:00:00+08:00`
2. 新加坡用戶選擇 "2025-12-20" → 瀏覽器傳送 `2025-12-20T00:00:00+08:00`
3. 美國用戶選擇 "2025-12-20" → 瀏覽器傳送 `2025-12-20T00:00:00-08:00`（錯誤！）

**驗證命令**:
```bash
# 檢查前端是否有日期選擇器
grep -r "type=\"date\"" frontend/pages --include="*.vue"
grep -r "new Date" frontend/pages --include="*.vue" -A 2 -B 2 | head -20
```

**修復方案**:

在前端統一使用台灣時區：

```vue
<!-- frontend/components/DatePicker.vue -->
<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  modelValue: String  // YYYY-MM-DD
})

const emit = defineEmits(['update:modelValue'])

// 轉換為 ISO 8601 格式（台灣時區）
const handleDateChange = (event: Event) => {
  const dateStr = (event.target as HTMLInputElement).value  // "2025-12-20"

  // 明確指定台灣時區
  const taiwanDate = new Date(dateStr + 'T00:00:00+08:00')

  // 轉換為 ISO 8601（後端期望格式）
  const isoStr = taiwanDate.toISOString()  // "2025-12-19T16:00:00.000Z"

  emit('update:modelValue', isoStr)
}
</script>

<template>
  <input
    type="date"
    :value="modelValue"
    @change="handleDateChange"
  />
</template>
```

---

### 8. PostgreSQL server_default 使用 text() 而非 func.now()

**問題描述**:

```python
# backend/app/models/option.py 和其他模型
created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'), nullable=False)

# VS 正確做法（其他模型）
created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

**問題**:
- `text('CURRENT_TIMESTAMP')` 是原始 SQL，Alembic 可能無法正確處理
- `func.now()` 是 SQLAlchemy 函數，類型安全且可跨資料庫

**修復方案**:
```python
from sqlalchemy.sql import func

# 修改所有使用 text('CURRENT_TIMESTAMP') 的地方
created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

---

## 🟢 Info (建議改進)

### 9. stock_minute_prices 表的例外處理需要更多文檔

**狀態**: 已有 `timezone_helpers.py` 和文檔，但可以改進

**建議**:

在 `stock_minute_price.py` 模型檔案頂部添加警告註釋：

```python
"""
Stock Minute Price Model

⚠️ 重要：時區例外
本表使用 TIMESTAMP WITHOUT TIME ZONE（台灣本地時間），與系統其他表不同！

原因：
- 60M+ 筆資料，已被 TimescaleDB 壓縮
- 修改欄位類型需要 2-4 小時 + 50GB 磁碟空間
- 資料正確性風險高

使用時必須使用 timezone_helpers.py 中的轉換函數：
- 讀取：naive_taipei_to_utc(record.datetime)
- 寫入：utc_to_naive_taipei(utc_datetime)

詳見：TIMEZONE_STRATEGY.md
"""
```

---

### 10. 缺少時區相關的自動化測試

**問題描述**:

未發現針對時區處理的完整測試套件。

**建議測試案例**:

```python
# tests/test_timezone.py

import pytest
from datetime import datetime, timezone, date
from app.utils.timezone_helpers import (
    naive_taipei_to_utc,
    utc_to_naive_taipei,
    now_taipei_naive,
    now_utc
)

class TestTimezoneHelpers:
    """測試時區輔助函數"""

    def test_naive_taipei_to_utc(self):
        """測試台灣時間轉 UTC"""
        # 台灣 2025-12-20 08:00 = UTC 2025-12-20 00:00
        taipei_naive = datetime(2025, 12, 20, 8, 0, 0)
        utc_aware = naive_taipei_to_utc(taipei_naive)

        assert utc_aware.hour == 0
        assert utc_aware.minute == 0
        assert utc_aware.tzinfo == timezone.utc

    def test_utc_to_naive_taipei(self):
        """測試 UTC 轉台灣時間"""
        # UTC 2025-12-20 00:00 = 台灣 2025-12-20 08:00
        utc_aware = datetime(2025, 12, 20, 0, 0, 0, tzinfo=timezone.utc)
        taipei_naive = utc_to_naive_taipei(utc_aware)

        assert taipei_naive.hour == 8
        assert taipei_naive.minute == 0
        assert taipei_naive.tzinfo is None

    def test_round_trip_conversion(self):
        """測試往返轉換保持一致"""
        original = datetime(2025, 12, 20, 15, 30, 0, tzinfo=timezone.utc)
        taipei = utc_to_naive_taipei(original)
        back_to_utc = naive_taipei_to_utc(taipei)

        assert original == back_to_utc

    def test_dst_handling(self):
        """測試夏令時處理（台灣無夏令時，但應確保函數不會錯誤處理）"""
        # 台灣全年 UTC+8，無夏令時
        summer = datetime(2025, 7, 1, 12, 0, 0)
        winter = datetime(2025, 12, 1, 12, 0, 0)

        summer_utc = naive_taipei_to_utc(summer)
        winter_utc = naive_taipei_to_utc(winter)

        # 時區偏移應該相同（都是 +8）
        assert (summer - summer_utc.replace(tzinfo=None)).seconds == 8 * 3600
        assert (winter - winter_utc.replace(tzinfo=None)).seconds == 8 * 3600


class TestStockMinutePriceTimezone:
    """測試 stock_minute_prices 時區處理"""

    def test_insert_with_utc_conversion(self, db):
        """測試插入時正確轉換為台灣時間"""
        from app.repositories.stock_minute_price import StockMinutePriceRepository
        from app.schemas.stock_minute_price import StockMinutePriceCreate

        # 當前 UTC 時間
        utc_now = datetime.now(timezone.utc)

        # 創建記錄（應自動轉換為台灣時間）
        price_data = StockMinutePriceCreate(
            stock_id="2330",
            datetime=utc_to_naive_taipei(utc_now),
            timeframe="1min",
            open=600.0,
            high=605.0,
            low=599.0,
            close=603.0,
            volume=1000000
        )

        result = StockMinutePriceRepository.create(db, price_data)

        # 讀取並轉換回 UTC
        result_utc = naive_taipei_to_utc(result.datetime)

        # 應該與原始時間一致（允許秒級誤差）
        assert abs((result_utc - utc_now).total_seconds()) < 1

    def test_query_with_timezone_conversion(self, db):
        """測試查詢時正確轉換時區"""
        from app.repositories.stock_minute_price import StockMinutePriceRepository

        # 查詢範圍：UTC 時間
        start_utc = datetime(2025, 12, 20, 1, 0, 0, tzinfo=timezone.utc)  # 台灣 09:00
        end_utc = datetime(2025, 12, 20, 5, 30, 0, tzinfo=timezone.utc)  # 台灣 13:30

        # Repository 應自動轉換
        results = StockMinutePriceRepository.get_by_stock(
            db, "2330",
            start_datetime=start_utc,
            end_datetime=end_utc
        )

        # 驗證返回的時間都在台灣交易時段（09:00-13:30）
        for record in results:
            taiwan_time = record.datetime  # Already in Taiwan time (naive)
            assert 9 <= taiwan_time.hour <= 13


class TestCeleryTimezone:
    """測試 Celery 時區配置"""

    def test_celery_uses_utc(self):
        """測試 Celery 使用 UTC"""
        from app.core.celery_app import celery_app

        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True

    def test_beat_schedule_times(self):
        """測試定時任務時間正確"""
        from app.core.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule

        # 驗證：sync-stock-list-daily 應在 UTC 00:00（台灣 08:00）
        stock_list_task = schedule["sync-stock-list-daily"]
        assert stock_list_task["schedule"].hour == 0
        assert stock_list_task["schedule"].minute == 0

        # 驗證：sync-daily-prices 應在 UTC 13:00（台灣 21:00）
        daily_prices_task = schedule["sync-daily-prices"]
        assert daily_prices_task["schedule"].hour == 13


class TestAPITimezone:
    """測試 API 時區處理"""

    def test_date_param_parsing(self):
        """測試日期參數解析"""
        # 這個測試需要實際實作 parse_date_param 函數後編寫
        pass

    def test_response_timezone_conversion(self):
        """測試響應中的時間轉換"""
        # 驗證 API 返回的時間都是 UTC（前端負責轉換）
        pass
```

**執行測試**:
```bash
# 執行所有時區測試
docker compose exec backend pytest tests/test_timezone.py -v

# 執行特定測試
docker compose exec backend pytest tests/test_timezone.py::TestTimezoneHelpers::test_naive_taipei_to_utc -v
```

---

## 📊 統計摘要

### 問題分布

| 嚴重程度 | 數量 | 百分比 |
|---------|------|--------|
| 🔴 Critical | 3 | 30% |
| 🟡 Warning | 5 | 50% |
| 🟢 Info | 2 | 20% |
| **總計** | **10** | **100%** |

### 影響範圍

| 層級 | 問題數 | 關鍵問題 |
|------|--------|----------|
| 資料庫層 | 4 | institutional_investors, option 表 |
| API 層 | 2 | 日期參數解析 |
| 服務層 | 2 | Shioaji API, .date() 轉換 |
| 任務調度層 | 1 | Redis task_history |
| 前端層 | 1 | 日期選擇器 |

---

## ✅ 已驗證正確的設計

### 1. Celery 配置正確
```python
✅ timezone="UTC"
✅ enable_utc=True
✅ crontab 時間已轉換為 UTC
```

### 2. timezone_helpers.py 設計良好
```python
✅ 明確的轉換函數
✅ 清楚的文檔說明
✅ 處理 stock_minute_prices 例外
```

### 3. 前端時區轉換邏輯正確
```typescript
✅ useDateTime.ts 使用 toLocaleString('zh-TW', { timeZone: 'Asia/Taipei' })
✅ 自動處理 UTC → 台灣時間
```

### 4. 大部分模型使用正確的 DateTime(timezone=True)
```python
✅ users, backtests, strategies 等表
✅ 使用 func.now() 而非 text('CURRENT_TIMESTAMP')
```

### 5. Repository 層已實作時區轉換
```python
✅ StockMinutePriceRepository 在查詢時自動轉換
✅ 使用 utc_to_naive_taipei 和 naive_taipei_to_utc
```

---

## 🚀 修復優先級建議

### P0 - 立即修復（本週內）
1. 修復 `institutional_investors` 表時區
2. 修復 Option 相關表時區（`created_at`, `updated_at`）
3. 驗證並清空 Redis task_history

### P1 - 短期修復（2 週內）
4. 統一 API 日期參數解析邏輯
5. 驗證 Shioaji API 返回時間的時區
6. 修復 `.date()` 轉換問題

### P2 - 中期改進（1 個月內）
7. 改進前端日期選擇器（指定時區）
8. 統一使用 `func.now()` 而非 `text('CURRENT_TIMESTAMP')`

### P3 - 長期優化（3 個月內）
9. 添加完整的時區測試套件
10. 決定 `OptionMinutePrice` 和 `OptionGreeks` 的時區策略

---

## 📝 修復步驟範例

### 修復 institutional_investors 表

```bash
# 1. 創建遷移腳本
cd /home/ubuntu/QuantLab/backend
docker compose exec backend alembic revision -m "fix_institutional_investors_timezone"

# 2. 編輯遷移腳本
# alembic/versions/XXXX_fix_institutional_investors_timezone.py
```

```python
def upgrade() -> None:
    # 修改欄位類型為 TIMESTAMPTZ
    op.execute("""
        ALTER TABLE institutional_investors
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';
    """)
    op.execute("""
        ALTER TABLE institutional_investors
        ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC';
    """)

def downgrade() -> None:
    op.execute("""
        ALTER TABLE institutional_investors
        ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    """)
    op.execute("""
        ALTER TABLE institutional_investors
        ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    """)
```

```bash
# 3. 執行遷移
docker compose exec backend alembic upgrade head

# 4. 驗證
docker compose exec postgres psql -U quantlab quantlab -c "
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'institutional_investors'
    AND column_name IN ('created_at', 'updated_at');
"
# 預期輸出：
# column_name | data_type                   | is_nullable
# created_at  | timestamp with time zone    | NO
# updated_at  | timestamp with time zone    | NO
```

---

## 🎯 最終建議

1. **立即行動**: 修復 Critical 級別的問題（institutional_investors 和 option 表）

2. **驗證配置**: 執行 TIMEZONE_STRATEGY.md 中未完成的檢查項目
   - 清空 Redis task_history
   - 重啟所有服務
   - 驗證資料正確性

3. **添加測試**: 實作時區相關的自動化測試，防止未來回歸

4. **文檔更新**: 在每個有時區例外的模型檔案頂部添加明確警告

5. **Code Review**: 未來新增代碼時，嚴格檢查：
   - 使用 `DateTime(timezone=True)` 而非 `DateTime`
   - 使用 `func.now()` 而非 `text('CURRENT_TIMESTAMP')`
   - 處理用戶輸入日期時明確指定時區
   - 調用 `.date()` 前確保 datetime 是 timezone-aware

6. **監控告警**: 添加時區相關的監控指標
   - Celery 任務執行時間偏移
   - API 返回時間與預期時區不符
   - 資料庫時間戳記異常

---

## 📚 參考文檔

- [TIMEZONE_STRATEGY.md](/home/ubuntu/QuantLab/TIMEZONE_STRATEGY.md) - 系統時區策略
- [timezone_helpers.py](/home/ubuntu/QuantLab/backend/app/utils/timezone_helpers.py) - 時區轉換輔助函數
- [PostgreSQL Timezone Documentation](https://www.postgresql.org/docs/current/datatype-datetime.html)
- [SQLAlchemy DateTime Types](https://docs.sqlalchemy.org/en/20/core/type_basics.html#sqlalchemy.types.DateTime)
- [Celery Timezone Configuration](https://docs.celeryq.dev/en/stable/userguide/configuration.html#timezone)

---

**審查完成日期**: 2025-12-20
**下次審查建議**: 2026-01-20（修復後 1 個月）
