# API DateTime 序列化最佳實踐指南

**創建日期**: 2025-12-20
**適用範圍**: FastAPI + Pydantic v2
**目的**: 統一 API 層的 datetime 序列化方式

---

## 問題背景

當前系統中存在兩種 datetime 序列化方式：

### 方式 1：Pydantic 自動序列化（推薦）✅

```python
# Response Model
class BacktestResponse(BaseModel):
    created_at: datetime  # Pydantic 自動序列化為 ISO 8601

# API Endpoint
@router.get("/backtest/{id}", response_model=BacktestResponse)
def get_backtest(id: int, db: Session = Depends(get_db)):
    backtest = db.query(Backtest).filter(Backtest.id == id).first()
    return backtest  # ✅ Pydantic 自動處理 datetime
```

**輸出**:
```json
{
  "created_at": "2025-12-20T00:18:21+00:00"
}
```

---

### 方式 2：手動 .isoformat()（功能正確但不推薦）

```python
# Response Model
class FactorEvaluationHistoryResponse(BaseModel):
    created_at: str  # 定義為字符串

# API Endpoint
@router.get("/evaluations", response_model=List[FactorEvaluationHistoryResponse])
def get_evaluations(db: Session = Depends(get_db)):
    evaluations = db.query(Evaluation).all()
    return [
        dict(
            created_at=eval.created_at.isoformat()  # ⚠️ 手動序列化
        )
        for eval in evaluations
    ]
```

**輸出**:
```json
{
  "created_at": "2025-12-20T00:18:21+00:00"
}
```

---

## 為何推薦 Pydantic 自動序列化？

### 優點

1. **減少代碼冗餘** - 無需手動調用 `.isoformat()`
2. **型別明確** - Response Model 使用 `datetime` 而非 `str`
3. **自動驗證** - Pydantic 會驗證 datetime 格式
4. **一致性** - 整個系統使用相同的序列化邏輯
5. **易於維護** - 修改序列化格式只需在一處配置

### Pydantic v2 自動處理

Pydantic v2 會自動將 timezone-aware datetime 序列化為 ISO 8601 格式：

```python
from pydantic import BaseModel
from datetime import datetime, timezone

class Example(BaseModel):
    timestamp: datetime

example = Example(timestamp=datetime.now(timezone.utc))
print(example.model_dump_json())
# 輸出: {"timestamp":"2025-12-20T00:18:21+00:00"}
```

---

## 當前系統狀況

### ✅ 已使用 Pydantic 自動序列化的 API（大多數）

大部分 API 已經正確使用 Pydantic 自動序列化，例如：

- `app/api/v1/backtest.py` - BacktestResponse
- `app/api/v1/strategies.py` - StrategyResponse
- `app/api/v1/rdagent.py` - RDAgentTaskResponse
- 等等...

### ⚠️ 仍使用手動 .isoformat() 的 API（少數）

以下 API 端點使用手動 `.isoformat()`：

1. **factor_evaluation.py:209, 269**
   - Response Model: `FactorEvaluationHistoryResponse`
   - 字段: `created_at: str`
   - 用途: 因子評估歷史記錄

2. **admin.py:684**
   - Response Model: 手動構建 dict
   - 字段: `detected_at`
   - 用途: 策略信號檢測結果

3. **intraday.py:298, backtest.py:779, admin.py:817**
   - 用途: 動態生成當前時間戳（非資料庫欄位）
   - 字段: `timestamp`

---

## 遷移策略

### 階段 1：新 API 端點（立即生效）✅

**所有新的 API 端點必須使用 Pydantic 自動序列化**

**正確示例**:
```python
from datetime import datetime
from pydantic import BaseModel

# ✅ Response Model 使用 datetime
class NewFeatureResponse(BaseModel):
    id: int
    name: str
    created_at: datetime  # 使用 datetime 而非 str
    updated_at: datetime

# ✅ API Endpoint 直接返回 ORM 對象或 dict
@router.get("/new-feature/{id}", response_model=NewFeatureResponse)
def get_new_feature(id: int, db: Session = Depends(get_db)):
    feature = db.query(NewFeature).filter(NewFeature.id == id).first()
    return feature  # Pydantic 自動序列化
```

**錯誤示例**:
```python
# ❌ 不要這樣做
class NewFeatureResponse(BaseModel):
    created_at: str  # 錯誤：使用 str

# ❌ 不要手動調用 .isoformat()
return dict(
    created_at=feature.created_at.isoformat()  # 錯誤
)
```

---

### 階段 2：現有 API 端點（可選優化）

**現有使用 `.isoformat()` 的端點可以保持現狀，或在有機會時重構**

#### 選項 A：保持現狀（功能正確）

如果 API 端點已經穩定運行且功能正確，**可以保持現狀**。添加註解說明即可：

```python
# Response Model 定義為 str（歷史原因，功能正確）
class FactorEvaluationHistoryResponse(BaseModel):
    created_at: str  # str type for backward compatibility

# 手動序列化（保持向後兼容）
return [
    dict(
        created_at=eval.created_at.isoformat()  # Manual serialization for str response
    )
    for eval in evaluations
]
```

#### 選項 B：重構為 Pydantic 自動序列化（推薦但非必須）

如果有時間和測試資源，可以重構：

```python
# 1. 修改 Response Model
class FactorEvaluationHistoryResponse(BaseModel):
    created_at: datetime  # 改為 datetime

# 2. 移除手動 .isoformat()
return evaluations  # 直接返回 ORM 對象列表
```

**注意**:
- 需要測試確保前端兼容性
- JSON 輸出格式不變（都是 ISO 8601）
- 有小風險，建議在非關鍵 API 上先試驗

---

## 特殊情況：動態生成的 timestamp

對於動態生成的當前時間戳（非資料庫欄位），有兩種處理方式：

### 方式 1：Response Model 定義 timestamp（推薦）

```python
class ResponseWithTimestamp(BaseModel):
    data: dict
    timestamp: datetime  # ✅ 使用 datetime

@router.get("/endpoint", response_model=ResponseWithTimestamp)
def endpoint():
    return ResponseWithTimestamp(
        data={"key": "value"},
        timestamp=datetime.now(timezone.utc)  # ✅ Pydantic 自動序列化
    )
```

### 方式 2：手動 .isoformat()（可接受）

如果 Response Model 已定義 `timestamp: str`，可以保持手動序列化：

```python
return {
    "data": data,
    "timestamp": datetime.now(timezone.utc).isoformat()  # 功能正確
}
```

---

## Code Review 檢查清單

### 新 API 端點檢查項目

- [ ] Response Model 中 datetime 欄位使用 `datetime` 型別（非 `str`）
- [ ] 沒有手動調用 `.isoformat()`
- [ ] 直接返回 ORM 對象或 Pydantic Model
- [ ] 資料庫 datetime 欄位是 timezone-aware (TIMESTAMPTZ)

### 現有 API 端點檢查項目

- [ ] 如果使用 `.isoformat()`，已添加註解說明原因
- [ ] 功能正確，無時區錯誤
- [ ] 如果重構，已測試前端兼容性

---

## 實際案例對比

### 案例 1: Backtest API（良好示例）✅

**Response Model**:
```python
class BacktestResponse(BaseModel):
    id: int
    name: str
    status: str
    created_at: datetime  # ✅ 使用 datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
```

**API Endpoint**:
```python
@router.get("/backtest/{backtest_id}", response_model=BacktestResponse)
def get_backtest(backtest_id: int, db: Session = Depends(get_db)):
    backtest = db.query(Backtest).filter(Backtest.id == backtest_id).first()
    return backtest  # ✅ Pydantic 自動序列化
```

**輸出**:
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

**為何是良好示例**:
- Response Model 使用 `datetime` 型別
- 沒有手動序列化
- 代碼簡潔清晰

---

### 案例 2: Factor Evaluation API（可接受但不推薦）

**Response Model**:
```python
class FactorEvaluationHistoryResponse(BaseModel):
    id: int
    factor_id: int
    created_at: str  # ⚠️ 使用 str（歷史原因）
```

**API Endpoint**:
```python
@router.get("/evaluations", response_model=List[FactorEvaluationHistoryResponse])
def get_evaluations(db: Session = Depends(get_db)):
    evaluations = db.query(Evaluation).all()
    return [
        dict(
            id=eval.id,
            factor_id=eval.factor_id,
            created_at=eval.created_at.isoformat()  # ⚠️ 手動序列化
        )
        for eval in evaluations
    ]
```

**輸出**:
```json
{
  "id": 456,
  "factor_id": 789,
  "created_at": "2025-12-20T00:18:21+00:00"
}
```

**為何可接受但不推薦**:
- 功能正確，JSON 輸出符合 ISO 8601
- 但手動序列化增加代碼冗餘
- 型別定義為 `str` 而非 `datetime`，語義不明確

**如何改進**（可選）:
```python
# 1. 修改 Response Model
class FactorEvaluationHistoryResponse(BaseModel):
    created_at: datetime  # 改為 datetime

# 2. 簡化 API Endpoint
return evaluations  # 直接返回 ORM 對象列表
```

---

## 總結

### 最佳實踐

1. **新 API 端點**：必須使用 Pydantic 自動序列化（`datetime` 型別）
2. **現有 API 端點**：可以保持現狀（如果功能正確），或在重構時改進
3. **手動 .isoformat()**：功能正確但不推薦，僅在向後兼容時使用

### 優先級

- **P1（高）**: 所有新 API 端點遵循最佳實踐
- **P3（低）**: 現有 API 端點可選性重構

### 影響

- **JSON 輸出格式不變**：兩種方式都輸出 ISO 8601 格式
- **向後兼容**：重構不影響前端（格式相同）
- **代碼品質**：使用 Pydantic 自動序列化提升代碼品質

---

## 參考資源

- [Pydantic v2 Documentation - Serialization](https://docs.pydantic.dev/latest/concepts/serialization/)
- [FastAPI - Response Model](https://fastapi.tiangolo.com/tutorial/response-model/)
- [TIMEZONE_BEST_PRACTICES.md](TIMEZONE_BEST_PRACTICES.md) - 系統時區處理規範

---

**文檔版本**: 1.0
**最後更新**: 2025-12-20
**維護者**: 開發團隊
