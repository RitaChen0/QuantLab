# QuantLab 時區處理深度審查報告

## 📅 審查信息

- **審查日期**：2025-12-20
- **審查者**：Claude Code (Code Reviewer)
- **審查範圍**：全系統時區處理邏輯
- **審查文件數**：35+ 個關鍵文件

## 🎯 執行摘要

經過全面的代碼審查，QuantLab 系統在時區處理上**整體架構良好**，但仍發現 **7 個問題**需要修復：

| 嚴重程度 | 數量 | 狀態 |
|---------|------|------|
| 🔴 Critical | 2 | 需立即修復 |
| 🟠 Medium | 3 | 短期修復 |
| 🟡 Low | 2 | 長期優化 |

---

## 🔴 嚴重問題 (Critical)

### 問題 1：使用已棄用的 `datetime.utcnow()`

**嚴重程度**：🔴 **Critical**

**影響範圍**：10 處代碼

**具體位置**：
```python
# app/tasks/factor_evaluation_tasks.py
- Line 53:  cutoff_time = datetime.utcnow() - timedelta(hours=24)
- Line 76:  cutoff_time = datetime.utcnow() - timedelta(hours=24)
- Line 181: cutoff_time = datetime.utcnow() - timedelta(hours=24)
- Line 192: cutoff_time = datetime.utcnow() - timedelta(hours=24)
- Line 269: cutoff_time = datetime.utcnow() - timedelta(hours=24)
- Line 280: cutoff_time = datetime.utcnow() - timedelta(hours=24)

# app/tasks/system_maintenance.py
- Line 85:  cutoff = datetime.utcnow() - timedelta(days=retention_days)

# app/services/rdagent_service.py
- Line 206: task.started_at = datetime.utcnow()
- Line 209: task.completed_at = datetime.utcnow()

# app/repositories/telegram_notification.py
- Line 152: cutoff = datetime.utcnow() - timedelta(days=days)
- Line 183: cutoff = datetime.utcnow() - timedelta(days=days)
```

**問題描述**：
1. `datetime.utcnow()` 在 Python 3.12+ 已被標記為棄用（PEP 615）
2. 返回 naive datetime（無時區信息），與系統 UTC 策略不一致
3. 與 timezone-aware datetime 比較時會引發 `TypeError`

**實際影響**：
```python
# 錯誤示例
cutoff_time = datetime.utcnow() - timedelta(hours=24)  # naive datetime
now = datetime.now(timezone.utc)  # aware datetime

# 比較時會報錯
if some_aware_datetime > cutoff_time:  # TypeError!
    ...
```

**修復方案**：
```python
# ❌ 錯誤
from datetime import datetime, timedelta
cutoff_time = datetime.utcnow() - timedelta(hours=24)

# ✅ 正確
from datetime import datetime, timezone, timedelta
cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
```

**修復優先級**：🔥 **立即** - Python 版本升級後會直接報錯

**預估工作量**：10 分鐘（簡單的搜尋替換）

---

### 問題 2：CLAUDE.md 文檔與實際配置不一致

**嚴重程度**：🔴 **Critical** (文檔錯誤)

**位置**：`CLAUDE.md` 第 88-90 行

**問題描述**：

**文檔聲稱**（CLAUDE.md）：
```markdown
### 1. Celery 時區錯誤

**症狀**：定時任務執行時間偏移 8 小時

**原因**：`enable_utc=True` 會將 crontab 視為 UTC

**解決**：
```python
# backend/app/core/celery_app.py
celery_app.conf.update(
    timezone="Asia/Taipei",  # ❌ 文檔錯誤
    enable_utc=False,        # ❌ 文檔錯誤
)
```

**實際配置**（backend/app/core/celery_app.py:17-18）：
```python
celery_app.conf.update(
    timezone="UTC",      # ✅ 實際為 UTC
    enable_utc=True,     # ✅ 實際為 True
)
```

**影響**：
1. 誤導開發者以為 Celery 使用台灣時區
2. 新增定時任務時可能使用錯誤的時間計算
3. 與 TIMEZONE_STRATEGY.md 描述不一致

**修復方案**：

更新 CLAUDE.md：
```markdown
### ✅ 已修復：Celery 時區配置

**當前配置**（2025-12-20 更新）：
```python
# backend/app/core/celery_app.py
celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
)
```

**重要**：
- 所有 crontab 時間為 UTC（台灣時間 -8 小時）
- 例如：`hour=1` 表示 UTC 01:00（台灣 09:00）
- 詳見 TIMEZONE_STRATEGY.md
```

**修復優先級**：🔥 **立即** - 防止開發者誤解

**預估工作量**：5 分鐘

---

## 🟠 中等問題 (Medium)

### 問題 3：API 日期參數缺少時區處理和驗證

**嚴重程度**：🟠 **Medium**

**影響範圍**：8 處代碼

**具體位置**：
```python
# app/api/v1/data.py
- Line 252: start = datetime.strptime(start_date, "%Y-%m-%d").date()
- Line 253: end = datetime.strptime(end_date, "%Y-%m-%d").date()
- Line 308: date=datetime.strptime(date, "%Y-%m-%d").date()

# scripts/sync_shioaji_to_qlib.py
- Line 1018: start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
- Line 1028: start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
- Line 1029: end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()

# scripts/backfill_option_data.py
- Line 601: start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
- Line 603: end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()

# app/services/backtest_engine.py
- Line 1337: trade_date = datetime.strptime(trade_date, '%Y-%m-%d').date()
```

**問題描述**：

1. **隱式時區假設**：
   ```python
   # API 接收日期字符串 "2025-12-20"
   start = datetime.strptime(start_date, "%Y-%m-%d").date()
   # 問題：這是哪個時區的 2025-12-20？
   # 隱式假設：台灣時區
   # 實際：沒有驗證或文檔化
   ```

2. **跨時區問題**：
   ```python
   # 假設用戶在美國時間 2025-12-20 00:00（PST）
   # 此時台灣已經是 2025-12-20 16:00
   # 用戶查詢 "2025-12-20" 應該看到哪些數據？
   ```

3. **缺少驗證**：
   ```python
   # 沒有檢查日期是否超過台灣當日
   end_date = datetime.strptime("2099-12-31", "%Y-%m-%d").date()
   # 查詢未來日期不會報錯
   ```

**當前狀況**：
- 系統隱式假設所有日期為台灣日期
- API 文檔沒有說明時區假設
- 僅當前所有用戶都在台灣時區時正常

**潛在風險**：
- 國際化時會產生混淆
- 不同時區用戶看到不同結果

**修復方案**：

**方案 1：明確文檔化**（最簡單，推薦）
```python
@router.get("/price/{stock_id}", response_model=StockDataResponse)
async def get_stock_price(
    stock_id: str,
    start_date: Optional[str] = Query(
        None,
        description="開始日期 (YYYY-MM-DD)，**基於台灣時區 (UTC+8)**"
    ),
    end_date: Optional[str] = Query(
        None,
        description="結束日期 (YYYY-MM-DD)，**基於台灣時區 (UTC+8)**"
    ),
):
    """
    取得股票價格資料

    **重要**：所有日期參數基於台灣時區解析。
    """
```

**方案 2：創建統一解析函數**（最嚴謹）
```python
# app/utils/date_parser.py
from datetime import date, datetime
from app.utils.timezone_helpers import today_taiwan

def parse_market_date(date_str: str) -> date:
    """
    解析市場日期字符串（基於台灣時區）

    Args:
        date_str: YYYY-MM-DD 格式日期字符串

    Returns:
        date 對象

    Raises:
        ValueError: 日期格式錯誤或超過台灣當日
    """
    try:
        parsed = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(f"日期格式錯誤，應為 YYYY-MM-DD: {date_str}") from e

    # 驗證不超過台灣當日
    taiwan_today = today_taiwan()
    if parsed > taiwan_today:
        raise ValueError(
            f"日期不能超過今天（台灣時區 {taiwan_today}）: {parsed}"
        )

    return parsed

# 使用
start = parse_market_date(start_date) if start_date else None
```

**修復優先級**：🔶 **短期** - 當前影響有限，但國際化前必須修復

**預估工作量**：
- 方案 1：30 分鐘（更新文檔）
- 方案 2：2 小時（創建函數 + 修改所有調用）

---

### 問題 4：Pandas DataFrame 時區處理不一致

**嚴重程度**：🟠 **Medium**

**影響範圍**：4 處代碼

**具體位置**：
```python
# app/services/qlib_data_adapter.py
- Line 167: qlib_df.index = pd.to_datetime(qlib_df.index)

# app/core/trading_hours.py
- Line 217: df[datetime_column] = pd.to_datetime(df[datetime_column])

# app/services/institutional_investor_service.py
- Line 249: df['date'] = pd.to_datetime(df['date'])

# 對比：正確處理
# app/services/shioaji_client.py
- Line 440: dt = pd.to_datetime(timestamp_ns, unit='ns', utc=True)\
              .tz_convert('Asia/Taipei').tz_localize(None)
```

**問題描述**：

1. **缺少時區參數**：
   ```python
   # ❌ 錯誤：返回 naive datetime
   df['datetime'] = pd.to_datetime(df['datetime'])

   # ✅ 正確：明確指定時區
   df['datetime'] = pd.to_datetime(df['datetime'], utc=True)
   ```

2. **不一致處理**：
   - shioaji_client.py 正確指定了時區
   - 其他文件沒有指定
   - 導致同一系統中 DataFrame 時區不一致

3. **潛在錯誤**：
   ```python
   # 時區 aware 和 naive 混用
   df1['dt'] = pd.to_datetime(df1['dt'])  # naive
   df2['dt'] = pd.to_datetime(df2['dt'], utc=True)  # aware

   # 合併時可能報錯
   merged = pd.merge(df1, df2, on='dt')  # TypeError!
   ```

**影響**：
- Pandas 時間序列操作可能產生錯誤
- 與資料庫 timestamp 比較失敗
- 數據處理邏輯不正確

**修復方案**：

創建統一的輔助函數：
```python
# app/utils/pandas_helpers.py
import pandas as pd
from typing import Union

def parse_datetime_taiwan(series: pd.Series) -> pd.Series:
    """
    解析 datetime 字符串為台灣時區的 naive datetime

    用於 stock_minute_prices 等儲存台灣時間的數據
    """
    return pd.to_datetime(series).dt.tz_localize('Asia/Taipei').dt.tz_localize(None)

def parse_datetime_utc(series: pd.Series) -> pd.Series:
    """
    解析 datetime 字符串為 UTC timezone-aware datetime

    用於一般數據處理
    """
    return pd.to_datetime(series, utc=True)

def parse_date(series: pd.Series) -> pd.Series:
    """
    解析日期字符串為 date 對象

    用於 date 類型欄位（無時區）
    """
    return pd.to_datetime(series).dt.date
```

使用範例：
```python
# ❌ Before
df['datetime'] = pd.to_datetime(df['datetime'])

# ✅ After
from app.utils.pandas_helpers import parse_datetime_taiwan
df['datetime'] = parse_datetime_taiwan(df['datetime'])
```

**修復優先級**：🔶 **短期** - 影響數據處理邏輯

**預估工作量**：2 小時（創建函數 + 修改 4 處調用 + 測試）

---

### 問題 5：stock_minute_prices API 響應缺少時區信息

**嚴重程度**：🟠 **Medium**

**影響範圍**：API 響應、前端顯示

**位置**：
```
app/schemas/stock_minute_price.py:16
app/api/v1/intraday.py (所有返回 StockMinutePriceResponse 的端點)
```

**問題描述**：

**當前 Schema**：
```python
# app/schemas/stock_minute_price.py
class StockMinutePriceBase(BaseModel):
    datetime: datetime  # ❌ 沒有說明這是 naive Taiwan time
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
```

**API 響應範例**：
```json
{
  "datetime": "2025-12-19T15:30:00",  // ❌ 缺少時區信息
  "open": 100.0,
  "close": 100.5
}
```

**前端問題**：
```javascript
// 前端解析
const data = await fetch('/api/v1/intraday/2330')
const record = data[0]

// 問題：瀏覽器如何解釋這個時間？
new Date("2025-12-19T15:30:00")
// 瀏覽器假設為本地時區
// 台灣用戶：2025-12-19 15:30 CST ✅ 正確
// 美國用戶：2025-12-19 15:30 PST ❌ 錯誤！實際應該是 23:30 PST
```

**影響**：
- 非台灣用戶看到錯誤的時間
- 國際化時會產生嚴重問題

**修復方案**：

**方案 1：Repository 層轉換為 UTC**（推薦）
```python
# app/repositories/stock_minute_price.py
def get_by_stock(
    self, db: Session, stock_id: str, ...
) -> List[StockMinutePrice]:
    results = db.query(StockMinutePrice).filter(...).all()

    # 轉換為 UTC timezone-aware datetime
    from app.utils.timezone_helpers import naive_taipei_to_utc
    for record in results:
        record.datetime = naive_taipei_to_utc(record.datetime)

    return results
```

**方案 2：Schema 層轉換**
```python
# app/schemas/stock_minute_price.py
from app.utils.timezone_helpers import naive_taipei_to_utc

class StockMinutePriceResponse(StockMinutePriceBase):
    """分鐘級股票價格響應 Schema

    注意：datetime 自動轉換為 UTC timezone-aware
    """

    @classmethod
    def from_db_record(cls, record: StockMinutePrice) -> "StockMinutePriceResponse":
        return cls(
            datetime=naive_taipei_to_utc(record.datetime),
            open=record.open,
            high=record.high,
            low=record.low,
            close=record.close,
            volume=record.volume,
        )
```

API 響應（修復後）：
```json
{
  "datetime": "2025-12-19T15:30:00+08:00",  // ✅ 包含時區 或
  "datetime": "2025-12-19T07:30:00+00:00",  // ✅ UTC 時間
  "open": 100.0,
  "close": 100.5
}
```

**方案 3：明確文檔化**（最簡單，但不推薦）
```python
class StockMinutePriceBase(BaseModel):
    """分鐘級股票價格基礎 Schema

    ⚠️  警告：datetime 欄位為 naive datetime（台灣時間），無時區信息
    前端解析時需要手動加上 'Asia/Taipei' 時區
    """
    datetime: datetime = Field(
        ...,
        description="時間（台灣時區 UTC+8，無 tzinfo，前端需自行處理）"
    )
```

**修復優先級**：🔶 **短期** - 國際化前必須修復

**預估工作量**：
- 方案 1/2：3 小時（修改 Repository/Schema + 測試 + 前端調整）
- 方案 3：30 分鐘（僅文檔）

---

## 🟡 低風險問題 (Low)

### 問題 6：Backtest 引擎日期比較可能丟失時區

**嚴重程度**：🟡 **Low**

**位置**：`app/services/backtest_engine.py:1337-1339`

**代碼**：
```python
trade_date = trade_data['date']
# 確保日期是 date 對象
if isinstance(trade_date, str):
    from datetime import datetime
    trade_date = datetime.strptime(trade_date, '%Y-%m-%d').date()
elif hasattr(trade_date, 'date'):
    trade_date = trade_date.date()  # ❌ 可能丟失時區信息
```

**問題**：
- 如果 `trade_date` 是 aware datetime，`.date()` 會直接取日期部分
- 在跨日交易（期貨夜盤）時可能產生錯誤日期

**範例**：
```python
# 期貨夜盤交易：2025-12-19 23:00 台灣時間
trade_dt = datetime(2025, 12, 19, 23, 0, tzinfo=timezone.utc)  # UTC 23:00
# 實際是台灣時間 2025-12-20 07:00

# 錯誤處理
trade_date = trade_dt.date()  # 2025-12-19 ❌ 錯誤！應該是 2025-12-20
```

**影響範圍**：
- 僅影響 Qlib 格式的交易記錄處理
- 當前 Backtrader 引擎可能不受影響

**修復方案**：
```python
elif hasattr(trade_date, 'date'):
    # 如果是 aware datetime，先轉換為台灣時區再取日期
    if hasattr(trade_date, 'tzinfo') and trade_date.tzinfo is not None:
        from app.utils.timezone_helpers import utc_to_naive_taipei
        trade_date = utc_to_naive_taipei(trade_date).date()
    else:
        trade_date = trade_date.date()
```

**修復優先級**：🟢 **低** - 影響範圍有限

**預估工作量**：15 分鐘

---

### 問題 7：缺少全局 Pydantic 時區序列化配置

**嚴重程度**：🟡 **Low** (建議，非必須)

**問題描述**：
- 大部分 Schema 依賴 Pydantic v2 默認行為
- 沒有統一的基類確保時區序列化一致性
- RDAgent schema 有明確註釋，但其他沒有

**當前狀況**：
```python
# 各個 Schema 自行配置
class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class StrategyBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# 沒有統一的時區處理說明
```

**建議方案**（非必須）：
```python
# app/schemas/base.py
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class TimezoneAwareBaseModel(BaseModel):
    """
    所有 Schema 的基類，確保 datetime 正確序列化

    時區處理策略：
    - 所有 timezone-aware datetime 序列化為 ISO 8601 (含時區)
    - 例如：2025-12-20T00:18:21+00:00
    - Pydantic v2 會自動處理，無需額外配置
    """
    model_config = ConfigDict(
        from_attributes=True,
        # Pydantic v2 默認正確處理 timezone-aware datetime
    )

# 使用
from app.schemas.base import TimezoneAwareBaseModel

class UserBase(TimezoneAwareBaseModel):
    # 繼承統一配置
    ...
```

**優勢**：
- 統一的時區處理策略
- 明確的文檔說明
- 方便未來調整

**修復優先級**：🟢 **低** - Pydantic v2 默認已正確

**預估工作量**：1 小時（創建基類 + 文檔 + 遷移部分 Schema）

---

## 📊 修復計劃

### 立即修復（本週）

| 任務 | 優先級 | 工作量 | 負責人 |
|------|--------|--------|--------|
| 1. 替換所有 `datetime.utcnow()` | 🔥 P0 | 10 分鐘 | - |
| 2. 更新 CLAUDE.md 文檔 | 🔥 P0 | 5 分鐘 | - |

### 短期修復（2 週內）

| 任務 | 優先級 | 工作量 | 負責人 |
|------|--------|--------|--------|
| 3. 統一 Pandas 時區處理 | 🔶 P1 | 2 小時 | - |
| 4. 完善 API 日期文檔 | 🔶 P1 | 30 分鐘 | - |
| 5. 修復 stock_minute_prices 響應 | 🔶 P1 | 3 小時 | - |

### 長期優化（1 個月內）

| 任務 | 優先級 | 工作量 | 負責人 |
|------|--------|--------|--------|
| 6. 修復 Backtest 時區處理 | 🟢 P2 | 15 分鐘 | - |
| 7. 創建統一 Schema 基類 | 🟢 P3 | 1 小時 | - |

---

## 🎯 建議的修復順序

### Phase 1：緊急修復（今天）
1. ✅ 替換 `datetime.utcnow()` → `datetime.now(timezone.utc)`
2. ✅ 更新 CLAUDE.md 文檔

### Phase 2：短期修復（本週）
3. ✅ 創建 Pandas 輔助函數
4. ✅ 更新 API 文檔和 Swagger 描述
5. ✅ 修復 stock_minute_prices 序列化

### Phase 3：長期優化（有時間時）
6. ✅ 優化 Backtest 引擎
7. ✅ 創建統一 Pydantic 基類

---

## 🧪 驗證檢查清單

修復完成後，請驗證：

### 代碼檢查
- [ ] 無遺漏的 `datetime.utcnow()`
- [ ] 所有 `pd.to_datetime()` 明確指定時區或使用輔助函數
- [ ] API 文檔說明日期參數時區假設
- [ ] stock_minute_prices 響應包含時區信息

### 功能測試
- [ ] API 日期範圍查詢正常
- [ ] Backtest 引擎日期處理正確
- [ ] Pandas DataFrame 時區一致
- [ ] 前端時間顯示正確

### 文檔更新
- [ ] CLAUDE.md Celery 配置正確
- [ ] API Swagger 文檔更新
- [ ] Schema 時區處理說明完整

---

## 📚 相關文檔

- [TIMEZONE_STRATEGY.md](TIMEZONE_STRATEGY.md) - 時區策略總覽
- [TIMEZONE_FIXES_SUMMARY.md](TIMEZONE_FIXES_SUMMARY.md) - 修復總結
- [CLAUDE.md](CLAUDE.md) - 開發指南

---

## ✅ 審查結論

**總體評價**：🟢 **良好**

QuantLab 時區處理架構整體良好，主要問題集中在：
1. 舊代碼使用已棄用的 API
2. 文檔與實際配置不一致
3. 部分邊緣場景缺少明確處理

**修復成本**：低（總計約 6-7 小時）

**風險評估**：
- 🔴 Critical 問題會在 Python 版本升級時報錯
- 🟠 Medium 問題在國際化時會產生問題
- 🟡 Low 問題影響範圍有限

**建議**：優先修復 Critical 問題（15 分鐘），短期內完成 Medium 問題修復（5-6 小時）。

---

**審查完成日期**：2025-12-20
**下次審查建議**：修復完成後 1 週
**審查者簽名**：Claude Code (Code Reviewer)
