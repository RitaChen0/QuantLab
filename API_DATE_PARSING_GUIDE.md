# API 日期參數解析指南

## 📋 概述

本文檔說明 QuantLab API 如何處理日期/時間參數，確保時區處理的一致性和正確性。

**最後更新**：2025-12-20

---

## 🎯 核心原則

### 1. 日期參數使用台灣市場時間

**原因**：
- 台股交易數據基於台灣交易時間（Asia/Taipei, UTC+8）
- 用戶期望使用台灣日期查詢數據（例如 "2025-12-20" 表示台灣 12/20）
- 避免時區轉換導致的日期偏移（UTC 日期可能與台灣日期不同）

**適用範圍**：
- `start_date`, `end_date` - 日線數據查詢
- `date` - 單日數據查詢
- `sync_date` - 數據同步日期

### 2. 日期時間參數使用 UTC 或明確標註時區

**原因**：
- 分鐘線數據需要精確的時間戳
- 系統內部統一使用 UTC 時間
- 避免夏令時和跨時區問題

**適用範圍**：
- `start_datetime`, `end_datetime` - 分鐘線數據查詢
- `datetime` - 精確時間戳

---

## 📝 API 參數規範

### 日期參數 (Date Parameters)

**格式**: `YYYY-MM-DD`

**示例**: `2025-12-20`

**時區**: 台灣時間（Asia/Taipei, UTC+8）

**處理邏輯**:
```python
from datetime import datetime, date

# ✅ 正確：直接解析為台灣日期
def parse_date_param(date_str: Optional[str]) -> Optional[date]:
    """
    解析 API 日期參數（台灣時間）

    Args:
        date_str: 日期字串 "YYYY-MM-DD"

    Returns:
        date 物件（代表台灣日期）
    """
    if not date_str:
        return None

    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}, expected YYYY-MM-DD")

# ❌ 錯誤：不要轉換為 UTC 日期
# utc_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).date()
# 原因：這會導致日期偏移（台灣 12/20 != UTC 12/20）
```

**使用範例**:
```bash
# 查詢台灣時間 2025-12-01 到 2025-12-20 的數據
GET /api/v1/data/stock-prices?start_date=2025-12-01&end_date=2025-12-20
```

### 日期時間參數 (DateTime Parameters)

**格式**: `YYYY-MM-DD HH:MM:SS`

**示例**: `2025-12-20 09:30:00`

**時區**:
- **預設**: 台灣時間（Asia/Taipei, UTC+8）
- **推薦**: 使用 ISO 8601 格式明確標註時區

**處理邏輯**:
```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# ✅ 方案 1：假設為台灣時間（預設）
def parse_datetime_param_taiwan(datetime_str: Optional[str]) -> Optional[datetime]:
    """
    解析 API 日期時間參數（假設為台灣時間）

    Args:
        datetime_str: 日期時間字串 "YYYY-MM-DD HH:MM:SS"

    Returns:
        datetime 物件（UTC，已從台灣時間轉換）
    """
    if not datetime_str:
        return None

    try:
        # 解析為 naive datetime
        dt_naive = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")

        # 標記為台灣時區
        dt_taiwan = dt_naive.replace(tzinfo=ZoneInfo("Asia/Taipei"))

        # 轉換為 UTC（資料庫存儲）
        dt_utc = dt_taiwan.astimezone(timezone.utc)

        return dt_utc
    except ValueError:
        raise ValueError(f"Invalid datetime format: {datetime_str}")

# ✅ 方案 2：要求 ISO 8601 格式（推薦）
def parse_datetime_param_iso(datetime_str: Optional[str]) -> Optional[datetime]:
    """
    解析 ISO 8601 日期時間參數（包含時區）

    Args:
        datetime_str: ISO 8601 格式 "2025-12-20T09:30:00+08:00"

    Returns:
        datetime 物件（UTC）
    """
    if not datetime_str:
        return None

    try:
        # datetime.fromisoformat 自動處理時區
        dt = datetime.fromisoformat(datetime_str)

        # 轉換為 UTC
        return dt.astimezone(timezone.utc)
    except ValueError:
        raise ValueError(f"Invalid ISO 8601 datetime: {datetime_str}")
```

**使用範例**:
```bash
# 方案 1：使用台灣時間（預設）
GET /api/v1/intraday/minute-prices?start_datetime=2025-12-20 09:00:00&end_datetime=2025-12-20 13:30:00

# 方案 2：使用 ISO 8601（推薦）
GET /api/v1/intraday/minute-prices?start_datetime=2025-12-20T09:00:00+08:00&end_datetime=2025-12-20T13:30:00+08:00
```

---

## 🔧 API 端點時區處理

### 1. 日線數據端點（Stock Prices）

**端點**: `/api/v1/data/stock-prices`

**參數**:
- `start_date` (YYYY-MM-DD)
- `end_date` (YYYY-MM-DD)

**時區處理**:
```python
@router.get("/stock-prices")
async def get_stock_prices(
    stock_id: str,
    start_date: Optional[str] = Query(None, description="開始日期 (YYYY-MM-DD, 台灣時間)"),
    end_date: Optional[str] = Query(None, description="結束日期 (YYYY-MM-DD, 台灣時間)")
):
    """
    獲取日線價格數據

    時區說明：
    - start_date/end_date 使用台灣日期
    - 返回數據的 date 欄位為台灣日期
    """
    # 直接解析為 Python date 物件
    start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

    # 查詢資料庫（date 欄位為 DATE 類型，無時區概念）
    prices = service.get_prices(stock_id, start, end)

    return prices
```

### 2. 分鐘線數據端點（Minute Prices）

**端點**: `/api/v1/intraday/minute-prices`

**參數**:
- `start_datetime` (YYYY-MM-DD HH:MM:SS)
- `end_datetime` (YYYY-MM-DD HH:MM:SS)

**時區處理**:
```python
from app.utils.timezone_helpers import parse_taiwan_datetime

@router.get("/minute-prices")
async def get_minute_prices(
    stock_id: str,
    start_datetime: Optional[str] = Query(None, description="開始時間 (YYYY-MM-DD HH:MM:SS, 台灣時間)"),
    end_datetime: Optional[str] = Query(None, description="結束時間 (YYYY-MM-DD HH:MM:SS, 台灣時間)")
):
    """
    獲取分鐘線價格數據

    時區說明：
    - start_datetime/end_datetime 假設為台灣時間
    - stock_minute_prices 表使用 TIMESTAMP WITHOUT TIME ZONE（台灣時間）
    - 返回數據的 datetime 欄位為台灣時間（naive datetime）

    注意：這是設計決策，見 TIMEZONE_STRATEGY.md
    """
    # 解析為台灣時間（naive datetime）
    start = parse_taiwan_datetime(start_datetime) if start_datetime else None
    end = parse_taiwan_datetime(end_datetime) if end_datetime else None

    # 查詢資料庫（直接比較 naive datetime）
    prices = service.get_minute_prices(stock_id, start, end)

    return prices
```

### 3. 法人買賣超端點（Institutional Investors）

**端點**: `/api/v1/institutional/top-stocks`

**參數**:
- `start_date` (YYYY-MM-DD)
- `end_date` (YYYY-MM-DD)

**時區處理**:
```python
@router.get("/top-stocks")
async def get_top_stocks(
    start_date: Optional[str] = Query(None, description="開始日期 (YYYY-MM-DD, 台灣交易日)"),
    end_date: Optional[str] = Query(None, description="結束日期 (YYYY-MM-DD, 台灣交易日)")
):
    """
    獲取法人買賣超排行

    時區說明：
    - start_date/end_date 使用台灣交易日
    - 法人數據基於台灣證券交易所公布的交易日
    """
    start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

    data = service.get_top_stocks(start, end)

    return data
```

---

## 📚 參考函數庫

### timezone_helpers.py

```python
"""
時區轉換輔助函數
位置：backend/app/utils/timezone_helpers.py
"""

from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo

def parse_taiwan_datetime(datetime_str: str) -> datetime:
    """
    解析台灣時間字串為 naive datetime

    用於 stock_minute_prices 表查詢（TIMESTAMP WITHOUT TIME ZONE）
    """
    dt_naive = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    return dt_naive

def today_taiwan() -> date:
    """
    獲取當前台灣日期

    用於獲取台灣市場的「今天」日期
    """
    taiwan_tz = ZoneInfo("Asia/Taipei")
    return datetime.now(taiwan_tz).date()

def now_taipei() -> datetime:
    """
    獲取當前台灣時間（aware datetime）
    """
    return datetime.now(ZoneInfo("Asia/Taipei"))

def now_taipei_naive() -> datetime:
    """
    獲取當前台灣時間（naive datetime）

    用於 stock_minute_prices 表插入
    """
    return now_taipei().replace(tzinfo=None)
```

---

## ⚠️ 常見陷阱

### 1. 日期偏移問題

**錯誤**:
```python
# ❌ 將台灣日期當作 UTC 日期
start_date_str = "2025-12-20"  # 用戶輸入台灣日期
start_utc = datetime.strptime(start_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
# 這會導致查詢 UTC 12/20，但台灣 12/20 對應的是 UTC 12/19 16:00 - 12/20 16:00
```

**正確**:
```python
# ✅ 直接使用 date 物件（無時區概念）
start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
```

### 2. 分鐘線時區混淆

**錯誤**:
```python
# ❌ 將台灣時間轉換為 UTC 查詢 stock_minute_prices
datetime_str = "2025-12-20 09:30:00"  # 台灣時間
dt_taiwan = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("Asia/Taipei"))
dt_utc = dt_taiwan.astimezone(timezone.utc)

# 查詢 stock_minute_prices（表中存儲的是台灣時間）
prices = db.query(StockMinutePrice).filter(StockMinutePrice.datetime >= dt_utc).all()
# 這會導致查詢結果錯誤，因為比較的是 UTC 時間 vs 台灣時間
```

**正確**:
```python
# ✅ 直接使用 naive datetime 查詢
dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
prices = db.query(StockMinutePrice).filter(StockMinutePrice.datetime >= dt).all()
```

### 3. API 響應時區標註

**錯誤**:
```python
# ❌ 返回 naive datetime，用戶不知道是什麼時區
return {
    "datetime": "2025-12-20 09:30:00",  # 這是 UTC 還是台灣時間？
    "price": 100.0
}
```

**正確**:
```python
# ✅ 使用 ISO 8601 格式明確標註時區
return {
    "datetime": "2025-12-20T09:30:00+08:00",  # 明確標註為台灣時間
    "price": 100.0
}

# 或在文檔中明確說明
"""
返回數據說明：
- datetime: 台灣時間（Asia/Taipei, UTC+8）
- 格式: YYYY-MM-DD HH:MM:SS
"""
```

---

## 🧪 測試建議

### 單元測試

```python
import pytest
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

def test_parse_date_param():
    """測試日期參數解析"""
    # 測試正常情況
    result = parse_date_param("2025-12-20")
    assert result == date(2025, 12, 20)

    # 測試 None
    result = parse_date_param(None)
    assert result is None

    # 測試錯誤格式
    with pytest.raises(ValueError):
        parse_date_param("20-12-2025")

def test_parse_datetime_param():
    """測試日期時間參數解析"""
    # 測試台灣時間
    result = parse_datetime_param_taiwan("2025-12-20 09:30:00")
    expected = datetime(2025, 12, 20, 9, 30, 0, tzinfo=ZoneInfo("Asia/Taipei"))
    assert result.astimezone(ZoneInfo("Asia/Taipei")) == expected

    # 測試 ISO 8601
    result = parse_datetime_param_iso("2025-12-20T09:30:00+08:00")
    assert result.astimezone(ZoneInfo("Asia/Taipei")) == expected
```

### 整合測試

```python
def test_api_date_parameter(client):
    """測試 API 日期參數"""
    # 測試台灣日期查詢
    response = client.get("/api/v1/data/stock-prices", params={
        "stock_id": "2330",
        "start_date": "2025-12-01",
        "end_date": "2025-12-20"
    })

    assert response.status_code == 200
    data = response.json()

    # 驗證返回的日期範圍
    assert data["start_date"] == "2025-12-01"
    assert data["end_date"] == "2025-12-20"
```

---

## 📖 相關文檔

- [TIMEZONE_STRATEGY.md](TIMEZONE_STRATEGY.md) - 整體時區策略
- [TIMEZONE_FIXES_SUMMARY.md](TIMEZONE_FIXES_SUMMARY.md) - 時區修復總結
- [backend/app/utils/timezone_helpers.py](backend/app/utils/timezone_helpers.py) - 時區輔助函數

---

**維護者**：開發團隊
**最後更新**：2025-12-20
