# API 日期時間處理完整指南

**創建日期**: 2025-12-23
**適用範圍**: FastAPI + Pydantic v2
**目的**: 統一 API 層的日期時間參數解析和序列化方式

---

## 📋 目錄

1. [核心原則](#核心原則)
2. [API 參數規範](#api-參數規範)
3. [API 序列化最佳實踐](#api-序列化最佳實踐)
4. [API 端點時區處理](#api-端點時區處理)
5. [常見陷阱](#常見陷阱)
6. [Code Review 檢查清單](#code-review-檢查清單)

---

## 核心原則

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

### 3. Response 使用 Pydantic 自動序列化

**原因**：
- 減少代碼冗餘（無需手動 `.isoformat()`）
- 型別明確（使用 `datetime` 而非 `str`）
- 自動驗證和一致性
- 易於維護

---

## API 參數規範

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

**格式**: ISO 8601 或 `YYYY-MM-DD HH:MM:SS`

**示例**:
- `2025-12-20T09:30:00+08:00` （推薦）
- `2025-12-20 09:30:00` （假設台灣時間）

**處理邏輯**:
```python
from datetime import datetime, timezone
from app.utils.timezone_helpers import parse_datetime_safe

# ✅ 推薦：使用 timezone_helpers
def parse_datetime_param(datetime_str: Optional[str]) -> Optional[datetime]:
    """
    解析 API datetime 參數（確保 timezone-aware）

    支持格式：
    - ISO 8601: "2025-12-20T09:30:00+08:00"
    - 簡化格式: "2025-12-20 09:30:00" (假設 UTC)

    Returns:
        datetime 物件（UTC timezone-aware）
    """
    if not datetime_str:
        return None

    return parse_datetime_safe(datetime_str)
```

**使用範例**:
```bash
# 使用 ISO 8601（推薦）
GET /api/v1/intraday/minute-prices?start_datetime=2025-12-20T09:00:00+08:00&end_datetime=2025-12-20T13:30:00+08:00
```

---

## API 序列化最佳實踐

### ✅ 推薦：Pydantic 自動序列化

**Response Model 定義**:
```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class BacktestResponse(BaseModel):
    id: int
    name: str
    status: str
    created_at: datetime  # ✅ 使用 datetime 型別
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
```

**API Endpoint**:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

@router.get("/backtest/{backtest_id}", response_model=BacktestResponse)
def get_backtest(backtest_id: int, db: Session = Depends(get_db)):
    backtest = db.query(Backtest).filter(Backtest.id == backtest_id).first()
    return backtest  # ✅ Pydantic 自動序列化
```

**JSON 輸出**:
```json
{
  "id": 123,
  "name": "MA Cross Strategy",
  "status": "COMPLETED",
  "created_at": "2025-12-20T00:18:21+00:00",
  "started_at": "2025-12-20T01:00:00+00:00",
  "completed_at": "2025-12-20T02:30:00+00:00"
}
```

**優點**：
1. **減少代碼冗餘** - 無需手動調用 `.isoformat()`
2. **型別明確** - Response Model 使用 `datetime` 而非 `str`
3. **自動驗證** - Pydantic 會驗證 datetime 格式
4. **一致性** - 整個系統使用相同的序列化邏輯
5. **易於維護** - 修改序列化格式只需在一處配置

### ⚠️ 不推薦：手動 .isoformat()

```python
# ❌ 避免這樣做（除非向後兼容需要）
class LegacyResponse(BaseModel):
    created_at: str  # 不推薦：使用 str

@router.get("/legacy")
def get_legacy():
    return {
        "created_at": datetime.now(timezone.utc).isoformat()  # 不推薦
    }
```

**何時可接受**：
- 現有穩定 API 需要向後兼容
- 已添加註解說明原因

---

## API 端點時區處理

### 1. 日線數據端點（Stock Prices）

**端點**: `/api/v1/data/stock-prices`

**參數**:
- `start_date` (YYYY-MM-DD，台灣時間)
- `end_date` (YYYY-MM-DD，台灣時間)

**實作範例**:
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
- `start_datetime` (ISO 8601 或 YYYY-MM-DD HH:MM:SS)
- `end_datetime` (ISO 8601 或 YYYY-MM-DD HH:MM:SS)

**實作範例**:
```python
from app.utils.timezone_helpers import parse_datetime_safe, utc_to_naive_taipei

@router.get("/minute-prices")
async def get_minute_prices(
    stock_id: str,
    start_datetime: Optional[str] = Query(None, description="開始時間 (ISO 8601)"),
    end_datetime: Optional[str] = Query(None, description="結束時間 (ISO 8601)")
):
    """
    獲取分鐘線價格數據

    時區說明：
    - 接受 ISO 8601 格式（帶時區）
    - stock_minute_prices 表使用台灣時間（naive）
    - 自動進行時區轉換
    """
    # 解析為 UTC timezone-aware datetime
    start_utc = parse_datetime_safe(start_datetime) if start_datetime else None
    end_utc = parse_datetime_safe(end_datetime) if end_datetime else None

    # 轉換為台灣 naive datetime（stock_minute_prices 表格式）
    start_taipei = utc_to_naive_taipei(start_utc) if start_utc else None
    end_taipei = utc_to_naive_taipei(end_utc) if end_utc else None

    # 查詢資料庫
    prices = service.get_minute_prices(stock_id, start_taipei, end_taipei)

    return prices
```

### 3. 法人買賣超端點（Institutional Investors）

**端點**: `/api/v1/institutional/top-stocks`

**參數**:
- `start_date` (YYYY-MM-DD，台灣交易日)
- `end_date` (YYYY-MM-DD，台灣交易日)

**實作範例**:
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

## 常見陷阱

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
# ✅ 使用 timezone_helpers 進行轉換
from app.utils.timezone_helpers import parse_datetime_safe, utc_to_naive_taipei

dt_utc = parse_datetime_safe(datetime_str)
dt_taipei_naive = utc_to_naive_taipei(dt_utc)
prices = db.query(StockMinutePrice).filter(StockMinutePrice.datetime >= dt_taipei_naive).all()
```

### 3. Response 缺少時區標註

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
# ✅ 使用 Pydantic 自動序列化（ISO 8601 帶時區）
class PriceResponse(BaseModel):
    datetime: datetime  # Pydantic 自動序列化為 ISO 8601
    price: float

return PriceResponse(
    datetime=datetime.now(timezone.utc),
    price=100.0
)
# 輸出: {"datetime": "2025-12-20T09:30:00+00:00", "price": 100.0}
```

### 4. 手動序列化代碼冗餘

**錯誤**:
```python
# ❌ 手動調用 .isoformat()
class ResponseModel(BaseModel):
    created_at: str  # 定義為 str

return {
    "created_at": obj.created_at.isoformat()  # 手動序列化
}
```

**正確**:
```python
# ✅ 使用 Pydantic 自動序列化
class ResponseModel(BaseModel):
    created_at: datetime  # 定義為 datetime

return obj  # Pydantic 自動序列化
```

---

## Code Review 檢查清單

### 新 API 端點檢查項目

- [ ] **日期參數**：
  - [ ] 使用台灣日期（無需時區轉換）
  - [ ] 參數說明標註 "台灣時間"

- [ ] **DateTime 參數**：
  - [ ] 使用 `parse_datetime_safe()` 解析
  - [ ] stock_minute_prices 查詢使用 `utc_to_naive_taipei()` 轉換

- [ ] **Response Model**：
  - [ ] datetime 欄位使用 `datetime` 型別（非 `str`）
  - [ ] 沒有手動調用 `.isoformat()`
  - [ ] 直接返回 ORM 對象或 Pydantic Model

- [ ] **資料庫**：
  - [ ] datetime 欄位是 timezone-aware (TIMESTAMPTZ)
  - [ ] 例外：stock_minute_prices 使用 naive datetime（台灣時間）

### 現有 API 端點檢查項目

- [ ] 如果使用 `.isoformat()`，已添加註解說明原因
- [ ] 功能正確，無時區錯誤
- [ ] 如果重構，已測試前端兼容性

---

## 測試建議

### 單元測試

```python
import pytest
from datetime import date, datetime, timezone

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

def test_api_datetime_serialization():
    """測試 Pydantic 自動序列化"""
    from pydantic import BaseModel

    class TestResponse(BaseModel):
        timestamp: datetime

    response = TestResponse(timestamp=datetime(2025, 12, 20, 9, 30, 0, tzinfo=timezone.utc))
    json_str = response.model_dump_json()

    assert "2025-12-20T09:30:00+00:00" in json_str
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

## 總結

### 最佳實踐

1. **日期參數**：使用台灣日期（`YYYY-MM-DD`），無需時區轉換
2. **DateTime 參數**：使用 ISO 8601 格式或 `parse_datetime_safe()`
3. **Response 序列化**：使用 Pydantic 自動序列化（`datetime` 型別）
4. **stock_minute_prices**：使用 `utc_to_naive_taipei()` 轉換

### 優先級

- **P1（高）**: 所有新 API 端點遵循最佳實踐
- **P3（低）**: 現有 API 端點可選性重構

### 影響

- **JSON 輸出格式不變**：Pydantic 和手動序列化都輸出 ISO 8601
- **向後兼容**：重構不影響前端（格式相同）
- **代碼品質**：減少冗餘，提升可維護性

---

## 相關文檔

- [TIMEZONE_COMPLETE_GUIDE.md](../TIMEZONE_COMPLETE_GUIDE.md) - 系統時區處理完整指南
- [backend/app/utils/timezone_helpers.py](../backend/app/utils/timezone_helpers.py) - 時區輔助函數
- [Pydantic v2 Documentation - Serialization](https://docs.pydantic.dev/latest/concepts/serialization/)
- [FastAPI - Response Model](https://fastapi.tiangolo.com/tutorial/response-model/)

---

**文檔版本**: 1.0
**最後更新**: 2025-12-23
**維護者**: 開發團隊
