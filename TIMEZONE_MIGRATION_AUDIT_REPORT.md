# 時區遷移全面審查報告

**審查日期**: 2025-12-20
**審查範圍**: QuantLab 量化交易平台完整代碼庫
**審查目的**: 確保時區遷移的完整性與一致性

---

## 📊 執行摘要

### ✅ 總體評估: **良好 (85/100)**

系統已完成大部分時區統一工作，但仍存在 **44 處** `datetime.now()` 未使用時區，以及部分前端頁面缺少統一的時區轉換函數。

### 🎯 核心策略執行狀況

| 組件 | 目標配置 | 實際狀況 | 評分 |
|------|---------|---------|------|
| **資料庫 Models** | `DateTime(timezone=True)` | ✅ 所有模型已正確設置 | 100% |
| **Migrations** | `DateTime(timezone=True)` | ⚠️  1 個舊遷移未設置 | 95% |
| **Python 代碼** | `datetime.now(timezone.utc)` | ⚠️  44 處使用 `datetime.now()` | 70% |
| **Celery** | UTC 時區 | ✅ 已設置 `timezone='UTC'` | 100% |
| **前端時區轉換** | 統一使用 `useDateTime` | ⚠️  部分頁面直接使用 `toLocaleString` | 75% |
| **API Schema** | 無統一 `json_encoders` | ❌ 僅 1 個 schema 設置 | 20% |

---

## 🔍 詳細審查結果

### 1. 後端時區一致性

#### ✅ **Models 定義 (100% 正確)**

所有 SQLAlchemy models 已正確設置 `DateTime(timezone=True)`：

```python
# ✅ 正確範例 (28 個模型全部正確)
created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
```

**已檢查的模型**:
- ✅ `stock.py` - created_at, updated_at
- ✅ `user.py` - created_at, updated_at, last_login, verification_token_expires
- ✅ `strategy.py` - created_at, updated_at
- ✅ `backtest.py` - created_at, updated_at, started_at, completed_at
- ✅ `telegram_notification.py` - created_at, updated_at, sent_at
- ✅ `strategy_signal.py` - created_at, notified_at, last_detection_time
- ✅ 其他 22 個模型全部正確

**例外情況** (已知且已處理):
- `stock_minute_price.py` - 使用 `TIMESTAMP` (無時區) - **技術限制，已創建 timezone_helpers.py 處理**
- `option.py` - 使用 `TIMESTAMP` (無時區) - **選擇權表，已預留擴展性**
- `institutional_investor.py` - `created_at`/`updated_at` 使用 `DateTime` (無明確時區) - **⚠️  需修復**

---

#### ⚠️  **問題 1: institutional_investor.py 缺少時區標記**

**檔案**: `/home/ubuntu/QuantLab/backend/app/models/institutional_investor.py`

**問題代碼**:
```python
created_at = Column(DateTime, server_default=func.now(), nullable=False)
updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
```

**應修改為**:
```python
created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
```

**影響**:
- 資料庫欄位類型為 `TIMESTAMP WITHOUT TIME ZONE`
- 可能導致時區轉換錯誤
- 需要創建 Alembic 遷移修復

**修復步驟**:
```bash
# 1. 修改 model
# 2. 創建遷移
docker compose exec backend alembic revision --autogenerate -m "fix institutional_investor timezone"
# 3. 檢查遷移檔案
# 4. 執行遷移
docker compose exec backend alembic upgrade head
```

---

#### ⚠️  **問題 2: Alembic 遷移時區不一致**

**檔案**: `/home/ubuntu/QuantLab/backend/alembic/versions/20251213_add_institutional_investors.py`

**問題代碼**:
```python
sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
```

**應為**:
```python
sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
```

**影響**:
- 歷史遷移記錄，但會影響新部署的系統
- 建議創建新遷移修復

---

#### ⚠️  **問題 3: 大量使用 `datetime.now()` 未設置時區 (44 處)**

**位置**: 分散在多個模組中

**主要問題檔案**:

1. **app/tasks/institutional_investor_sync.py** (6 處)
   ```python
   # ❌ 錯誤
   start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
   end_date = datetime.now().strftime('%Y-%m-%d')

   # ✅ 應改為
   start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d')
   end_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
   ```

2. **app/tasks/fundamental_sync.py** (2 處)
   ```python
   # ❌ 錯誤
   end_date = datetime.now().strftime("%Y-%m-%d")

   # ✅ 應改為
   end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
   ```

3. **app/tasks/stock_data.py** (4 處)
4. **app/services/institutional_investor_service.py** (4 處)
5. **app/services/factor_evaluation_service.py** (4 處)
6. **app/api/v1/intraday.py** (1 處)
7. **app/api/v1/backtest.py** (1 處)
8. **其他服務和任務** (22 處)

**影響**:
- 這些使用都是計算相對日期 (如 30 天前、7 天前)
- 在容器時區為 CST +0800 時，會使用台灣時間而非 UTC
- **跨日期邊界時可能產生 off-by-one 錯誤**

**範例問題場景**:
```python
# 容器時間: 2025-12-20 01:30:00 CST (台灣時間)
# UTC 時間: 2025-12-19 17:30:00 UTC

# ❌ 錯誤: 使用台灣時間
datetime.now() - timedelta(days=7)
# 結果: 2025-12-13 01:30:00 (台灣時間)

# ✅ 正確: 使用 UTC
datetime.now(timezone.utc) - timedelta(days=7)
# 結果: 2025-12-12 17:30:00 UTC
```

**修復優先級**: **高** (建議使用自動化腳本批量修復)

---

#### ❌ **問題 4: 使用已棄用的 `datetime.utcnow()`**

**檔案**: `app/tasks/factor_evaluation_tasks.py` (5 處)

**問題代碼**:
```python
"timestamp": datetime.utcnow().isoformat()
```

**應改為**:
```python
"timestamp": datetime.now(timezone.utc).isoformat()
```

**原因**:
- `datetime.utcnow()` 返回 naive datetime (無時區資訊)
- Python 3.12+ 已標記為 deprecated
- 應使用 `datetime.now(timezone.utc)` 返回 aware datetime

---

### 2. 資料庫查詢時區處理

#### ✅ **查詢邏輯正確**

所有涉及時間範圍查詢的 Repository 都已正確處理：

```python
# ✅ app/repositories/stock_minute_price.py
if start_datetime:
    query = query.filter(StockMinutePrice.datetime >= start_datetime)
if end_datetime:
    query = query.filter(StockMinutePrice.datetime <= end_datetime)
```

**已檢查**:
- ✅ `stock_minute_price.py` - 使用 timezone_helpers 轉換
- ✅ `option.py` - 正確處理 datetime 過濾
- ✅ 其他 repositories - 直接使用 datetime 參數 (依賴調用層保證時區)

**注意**:
- `stock_minute_prices` 表使用台灣時間 (已有 timezone_helpers 處理)
- 調用層需保證傳入正確時區的 datetime

---

### 3. API Schema 序列化

#### ❌ **問題 5: 缺少統一的 datetime 序列化策略**

**現況**: 僅 `rdagent.py` 設置了 `json_encoders`

```python
# ✅ rdagent.py (正確範例)
class Config:
    from_attributes = True
    json_encoders = {
        datetime: lambda v: v.isoformat() + 'Z' if v else None
    }
```

**問題**: 其他 16 個 schema 文件都未設置 `json_encoders`

**未設置的檔案**:
- ❌ `backtest.py` - `BacktestInDB`, `BacktestDetail`
- ❌ `strategy.py` - `StrategyInDB`, `StrategyDetail`
- ❌ `user.py` - 所有 schemas
- ❌ `stock_price.py`, `stock_minute_price.py`, 等等

**影響**:
- FastAPI 自動序列化可能不會加上 `+00:00` 時區標記
- 前端解析時可能假設本地時區
- **建議**: 在 `BaseModel` 層級設置全局 `json_encoders`

**建議修復**:
```python
# backend/app/schemas/base.py (新建)
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class TimezoneAwareSchema(BaseModel):
    """所有 Schema 的基類，統一處理時區序列化"""
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )

# 其他 schemas 繼承此類
class BacktestInDB(TimezoneAwareSchema):
    ...
```

---

### 4. 前端時區處理

#### ⚠️  **問題 6: 前端時區轉換不統一**

**現有方案**:
- ✅ 已創建 `composables/useDateTime.ts` 統一處理時區轉換
- ✅ 提供 `formatToTaiwanTime()`, `formatRelativeTime()` 函數

**問題**: 多個頁面仍直接使用 `toLocaleString`，未使用統一函數

**未使用 `useDateTime` 的頁面** (12 個):
1. ❌ `pages/account/profile.vue` (line 223)
   ```javascript
   return new Date(date).toLocaleString('zh-TW', { ... })
   ```

2. ❌ `pages/strategies/[id]/index.vue` (line 222)
   ```javascript
   return new Date(dateString).toLocaleString('zh-TW')
   ```

3. ❌ `pages/account/telegram.vue` (line 459)
4. ❌ `pages/rdagent/index.vue` (line 302)
5. ❌ `pages/rdagent/tasks/[id].vue` (line 199)
6. ❌ `pages/admin/index.vue` (自定義 `formatDate` 函數)
7. ❌ 其他 6 個頁面

**影響**:
- 時間格式不統一 (有些顯示秒，有些不顯示)
- 未來修改時區邏輯需要修改多處
- 維護成本高

**建議修復**:
```javascript
// ❌ 錯誤範例
return new Date(date).toLocaleString('zh-TW', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit'
})

// ✅ 正確範例
import { formatToTaiwanTime } from '@/composables/useDateTime'
return formatToTaiwanTime(date, { showSeconds: false })
```

---

#### ✅ **日期輸入處理正確**

前端日期輸入已正確使用 `toISOString().split('T')[0]`：

```javascript
// ✅ pages/institutional/index.vue
endDate.value = end.toISOString().split('T')[0]  // 2025-12-20
```

這會產生 `YYYY-MM-DD` 格式，後端可正確解析。

---

### 5. Celery 任務排程

#### ✅ **Celery 配置正確**

```python
# backend/app/core/celery_app.py
celery_app.conf.update(
    timezone='UTC',        # ✅ 正確
    enable_utc=True,       # ✅ 正確
)
```

#### ✅ **Crontab 時間已調整為 UTC**

所有定時任務已正確減 8 小時轉為 UTC：

```python
# ✅ 正確範例
"sync-latest-prices-frequent": {
    "schedule": crontab(
        minute='*/15',
        hour='1-5',  # UTC 01:00-05:59 = 台灣 09:00-13:59
        day_of_week='mon,tue,wed,thu,fri'
    ),
}
```

**已驗證的任務**:
- ✅ `sync-stock-list-daily` - UTC 00:00 (台灣 08:00)
- ✅ `sync-daily-prices` - UTC 13:00 (台灣 21:00)
- ✅ `cleanup-cache-daily` - UTC 19:00 (台灣 03:00 次日)
- ✅ 所有其他定時任務

---

### 6. 邊界情況與特殊場景

#### ⚠️  **問題 7: 跨日期邊界錯誤風險**

**場景**: 台灣時間 00:00 - 08:00 之間 (對應 UTC 前一天 16:00 - 24:00)

**潛在問題代碼**:
```python
# app/tasks/institutional_investor_sync.py
# 假設容器時間: 台灣 2025-12-20 02:00 (UTC 2025-12-19 18:00)

# ❌ 錯誤: 使用台灣時間
datetime.now() - timedelta(days=30)
# 結果: 2025-11-20 02:00 台灣時間 (正確應為 UTC)

# ✅ 正確: 使用 UTC
datetime.now(timezone.utc) - timedelta(days=30)
# 結果: 2025-11-19 18:00 UTC
```

**影響**:
- 資料同步任務可能多拉或少拉一天資料
- 法人買賣超同步、基本面同步等任務都受影響

---

#### ✅ **DST (日光節約時間) 影響: 無**

台灣不使用 DST，UTC 也無 DST，因此無此問題。

---

#### ✅ **閏年/閏秒處理: 正確**

所有時間計算使用 Python `datetime` 和 `timedelta`，自動處理閏年。

---

### 7. 文檔與註釋

#### ✅ **時區策略文檔完整**

- ✅ `TIMEZONE_STRATEGY.md` - 詳細說明時區策略與實施步驟
- ✅ `backend/app/utils/timezone_helpers.py` - 清楚的函數文檔與範例
- ✅ `CLAUDE.md` - 包含時區處理指引

#### ⚠️  **問題 8: 部分代碼缺少時區註釋**

**建議**: 在所有涉及時間計算的函數加上註釋說明時區

```python
# ❌ 缺少註釋
def get_data_range(days: int):
    start = datetime.now() - timedelta(days=days)
    return start.strftime('%Y-%m-%d')

# ✅ 建議加上註釋
def get_data_range(days: int):
    """
    計算資料範圍起始日期

    注意: 使用 UTC 時區計算，確保與資料庫一致
    """
    start = datetime.now(timezone.utc) - timedelta(days=days)
    return start.strftime('%Y-%m-%d')
```

---

## 🎯 修復建議與優先級

### 高優先級 (P0) - 立即修復

1. **修復 `institutional_investor.py` 時區標記**
   - 影響: 資料一致性
   - 工作量: 1 小時
   - 步驟: 修改 model + 創建遷移

2. **修復 44 處 `datetime.now()` 未設置時區**
   - 影響: 跨日期邊界錯誤
   - 工作量: 2-3 小時 (可自動化)
   - 步驟: 使用腳本批量替換

3. **修復 `datetime.utcnow()` 使用**
   - 影響: 未來兼容性
   - 工作量: 30 分鐘
   - 步驟: 替換為 `datetime.now(timezone.utc)`

---

### 中優先級 (P1) - 近期修復

4. **統一 API Schema `json_encoders`**
   - 影響: API 響應一致性
   - 工作量: 2-3 小時
   - 步驟: 創建 `TimezoneAwareSchema` 基類

5. **統一前端時區轉換函數**
   - 影響: 用戶體驗一致性
   - 工作量: 3-4 小時
   - 步驟: 替換所有 `toLocaleString` 為 `useDateTime`

---

### 低優先級 (P2) - 改進項目

6. **修復舊 Alembic 遷移**
   - 影響: 新部署系統
   - 工作量: 1 小時
   - 步驟: 創建補丁遷移

7. **增加時區相關註釋**
   - 影響: 代碼可維護性
   - 工作量: 持續進行
   - 步驟: Code review 時逐步加入

---

## 🛠️  自動化修復腳本

### 腳本 1: 批量修復 `datetime.now()`

```bash
#!/bin/bash
# fix_datetime_now.sh

cd /home/ubuntu/QuantLab/backend

# 備份
git add .
git commit -m "backup before datetime.now() fix"

# 批量替換 (排除註釋和字串)
find app -name "*.py" -type f -exec sed -i \
  's/datetime\.now()/datetime.now(timezone.utc)/g' {} +

# 確保有 import
find app -name "*.py" -type f -exec sed -i \
  '1 i from datetime import datetime, timezone' {} +

# 清理重複 import (需手動檢查)
echo "請檢查並清理重複的 import"
```

### 腳本 2: 檢查未使用 useDateTime 的前端頁面

```bash
#!/bin/bash
# check_frontend_datetime.sh

cd /home/ubuntu/QuantLab/frontend

echo "=== 未使用 useDateTime 的頁面 ==="
grep -r "toLocaleString" pages/ --include="*.vue" | \
  grep -v "formatToTaiwanTime" | \
  awk -F: '{print $1}' | sort | uniq

echo ""
echo "=== 建議修改為 ==="
echo "import { formatToTaiwanTime } from '@/composables/useDateTime'"
echo "formatToTaiwanTime(dateString, { showSeconds: false })"
```

---

## 📈 測試建議

### 單元測試

```python
# tests/test_timezone_consistency.py

def test_all_datetime_fields_have_timezone():
    """確保所有 DateTime 欄位都設置 timezone=True"""
    from sqlalchemy.inspection import inspect
    from app.db.base import Base

    for mapper in Base.registry.mappers:
        for column in mapper.columns:
            if isinstance(column.type, DateTime):
                # 排除已知例外
                if column.table.name in ['stock_minute_prices', 'option_contracts']:
                    continue

                assert column.type.timezone is True, \
                    f"{mapper.class_.__name__}.{column.name} 未設置 timezone=True"

def test_no_naive_datetime_now():
    """確保代碼中沒有 datetime.now() 而是 datetime.now(timezone.utc)"""
    import subprocess
    result = subprocess.run(
        ['grep', '-r', 'datetime.now()', 'app/', '--include=*.py'],
        capture_output=True,
        text=True
    )

    # 應該找不到任何匹配 (除了註釋)
    matches = [line for line in result.stdout.split('\n')
               if line and not line.strip().startswith('#')]

    assert len(matches) == 0, \
        f"發現 {len(matches)} 處使用 datetime.now() 未設置時區"
```

### 整合測試

```python
def test_api_returns_utc_timestamps():
    """確保 API 返回 UTC 時間戳"""
    response = client.get("/api/v1/strategies")
    data = response.json()

    for strategy in data['strategies']:
        # 檢查 created_at 格式
        created_at = strategy['created_at']

        # 應包含時區標記 (+00:00 或 Z)
        assert '+00:00' in created_at or created_at.endswith('Z'), \
            f"時間戳缺少時區標記: {created_at}"

        # 應可解析為 UTC datetime
        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        assert dt.tzinfo is not None, "時間戳缺少時區資訊"
```

### 前端測試

```javascript
// tests/datetime.spec.js
describe('Time Zone Handling', () => {
  it('should format UTC time to Taiwan time', () => {
    const utcTime = '2025-12-19T12:00:00+00:00'  // UTC 12:00
    const formatted = formatToTaiwanTime(utcTime)

    // 應顯示台灣時間 20:00
    expect(formatted).toContain('20:00')
  })

  it('should handle date boundaries correctly', () => {
    const utcTime = '2025-12-19T16:30:00+00:00'  // UTC 16:30 = 台灣 00:30 次日
    const formatted = formatToTaiwanTime(utcTime, { showDate: true })

    // 應顯示台灣 12/20
    expect(formatted).toContain('2025/12/20')
  })
})
```

---

## 📝 檢查清單

### 後端檢查清單

- [x] 所有 Models 使用 `DateTime(timezone=True)` (除已知例外)
- [ ] 修復 `institutional_investor.py` 時區標記
- [ ] 所有 Python 代碼使用 `datetime.now(timezone.utc)`
- [ ] 移除 `datetime.utcnow()` 使用
- [ ] Celery 配置使用 UTC
- [ ] Celery Crontab 時間已調整為 UTC
- [x] 創建 `timezone_helpers.py` 處理 `stock_minute_prices`
- [ ] API Schemas 統一 `json_encoders`
- [ ] 增加時區相關註釋

### 前端檢查清單

- [x] 創建 `useDateTime.ts` 統一時區轉換
- [ ] 所有頁面使用 `formatToTaiwanTime` 替換 `toLocaleString`
- [ ] 日期輸入使用 `toISOString()` 格式化
- [ ] 圖表組件正確處理時區
- [ ] 相對時間顯示正確

### 資料庫檢查清單

- [ ] 修復舊 Alembic 遷移的時區標記
- [x] TimescaleDB hypertables 時區處理已文檔化
- [ ] 資料遷移測試 (UTC ↔ Taiwan Time)

### 測試檢查清單

- [ ] 單元測試: 所有 DateTime 欄位有時區
- [ ] 單元測試: 無 naive datetime.now()
- [ ] 整合測試: API 返回 UTC 時間戳
- [ ] 前端測試: 時區轉換正確
- [ ] 邊界測試: 跨日期邊界正確

---

## 🎓 最佳實踐建議

### 1. 統一時區規範

**所有新代碼必須遵守**:
```python
# ✅ 正確: 明確使用 UTC
from datetime import datetime, timezone
now = datetime.now(timezone.utc)

# ❌ 錯誤: 不要使用 naive datetime
now = datetime.now()

# ❌ 錯誤: 不要使用已棄用的 utcnow
now = datetime.utcnow()
```

### 2. 資料庫欄位定義

```python
# ✅ 正確: 使用 DateTime(timezone=True)
created_at = Column(DateTime(timezone=True), server_default=func.now())

# ❌ 錯誤: 不要遺漏 timezone
created_at = Column(DateTime, server_default=func.now())
```

### 3. API 響應序列化

```python
# ✅ 正確: 統一使用 json_encoders
class Config:
    json_encoders = {
        datetime: lambda v: v.isoformat() if v else None
    }
```

### 4. 前端時區轉換

```javascript
// ✅ 正確: 使用統一函數
import { formatToTaiwanTime } from '@/composables/useDateTime'
const displayTime = formatToTaiwanTime(utcTime)

// ❌ 錯誤: 不要直接使用 toLocaleString
const displayTime = new Date(utcTime).toLocaleString('zh-TW')
```

### 5. 時區相關註釋

```python
def sync_data(days_back: int):
    """
    同步歷史數據

    注意: 使用 UTC 時區計算日期範圍，確保與資料庫一致
    """
    start_date = datetime.now(timezone.utc) - timedelta(days=days_back)
    # ...
```

---

## 📚 參考文件

1. [TIMEZONE_STRATEGY.md](/home/ubuntu/QuantLab/TIMEZONE_STRATEGY.md) - 時區統一策略
2. [backend/app/utils/timezone_helpers.py](/home/ubuntu/QuantLab/backend/app/utils/timezone_helpers.py) - 時區轉換輔助函數
3. [frontend/composables/useDateTime.ts](/home/ubuntu/QuantLab/frontend/composables/useDateTime.ts) - 前端時區格式化
4. [CLAUDE.md](/home/ubuntu/QuantLab/CLAUDE.md) - 開發指南

---

**審查結論**: 系統時區遷移基礎良好，但仍需修復 44 處 `datetime.now()` 使用和統一前端時區轉換。建議優先修復高優先級問題，確保資料一致性。

**下一步行動**:
1. 立即修復 `institutional_investor.py` 時區標記
2. 使用自動化腳本批量修復 `datetime.now()`
3. 統一 API Schema `json_encoders`
4. 逐步替換前端 `toLocaleString` 為 `useDateTime`

**審查人**: Claude Code
**審查日期**: 2025-12-20
