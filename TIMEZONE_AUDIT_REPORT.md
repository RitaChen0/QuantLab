# 時區審查報告

**審查日期**: 2025-12-20
**審查者**: Claude Code
**嚴重程度**: 🔴 高危 - 發現多個關鍵漏洞

---

## 📋 執行摘要

時區遷移已完成基礎架構變更，但發現 **7 個關鍵漏洞**，可能導致：
- 時間顯示不一致
- 資料查詢錯誤
- 跨時區用戶體驗問題
- 資料庫寫入時區混亂

**必須修復的問題數量**: 4 個高優先級，3 個中優先級

---

## 🔴 高優先級問題（必須立即修復）

### 問題 #1：後端大量使用 `datetime.now()` 而非 `datetime.now(timezone.utc)`

**嚴重程度**: 🔴 高危
**影響範圍**: 30+ 處代碼
**問題描述**:

大量代碼使用 `datetime.now()` 生成 naive datetime（無時區標記），而非 `datetime.now(timezone.utc)`。這會導致：
1. 寫入 TIMESTAMPTZ 欄位時，PostgreSQL 會假設這是伺服器本地時區（可能不是 UTC）
2. 時間比較時混用 naive 和 aware datetime，導致不一致
3. 容器時區變更時，行為會改變

**受影響的文件**（部分列表）:
```python
# backend/app/api/v1/admin.py:613
now = datetime.now()  # ❌ 應該用 datetime.now(timezone.utc)

# backend/app/repositories/institutional_investor.py:57
existing.updated_at = datetime.now()  # ❌ 寫入 TIMESTAMPTZ 欄位

# backend/app/repositories/option.py:597
target_datetime = datetime.now()  # ❌ 用於資料庫查詢

# backend/app/tasks/institutional_investor_sync.py:53
start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')  # ❌

# backend/app/tasks/stock_data.py:158
end_date = datetime.now().strftime("%Y-%m-%d")  # ❌

# backend/app/tasks/option_sync.py:58
start_time = datetime.now()  # ❌ 用於計算執行時間

# backend/app/utils/alert.py:66
timestamp = datetime.now()  # ❌ 寫入告警檔案
```

**發現位置**（共 30+ 處）:
- `api/v1/admin.py` - 1 處
- `api/v1/intraday.py` - 2 處
- `api/v1/backtest.py` - 1 處
- `repositories/option.py` - 2 處
- `repositories/institutional_investor.py` - 1 處
- `tasks/*.py` - 20+ 處
- `services/*.py` - 2 處
- `utils/alert.py` - 1 處

**修復方案**:
```python
# ❌ 錯誤
from datetime import datetime
now = datetime.now()

# ✅ 正確
from datetime import datetime, timezone
now = datetime.now(timezone.utc)
```

**修復優先級**: P0 - 必須立即修復
**預計工時**: 2-3 小時（需要逐一檢查每處使用）

---

### 問題 #2：Pydantic Schema 強制加上 'Z' 後綴但時間可能不是 UTC

**嚴重程度**: 🔴 高危
**影響範圍**: `rdagent.py` schemas
**問題描述**:

`rdagent.py` 中的 json_encoders 強制在所有 datetime 後加上 'Z'：

```python
# backend/app/schemas/rdagent.py:61-62
json_encoders = {
    datetime: lambda v: v.isoformat() + 'Z' if v else None
}
```

問題：
1. 'Z' 表示 UTC 時區，但如果 `v` 是 naive datetime 或非 UTC aware datetime，這會造成錯誤的時區標記
2. 應該檢查 `v.tzinfo` 是否為 UTC，或者轉換為 UTC 後再加 'Z'
3. Pydantic v2 已經有更好的 datetime 序列化機制

**修復方案**:
```python
# ✅ 正確方式 1：移除 json_encoders，讓 Pydantic 處理
class Config:
    from_attributes = True
    # Pydantic v2 會自動正確序列化 timezone-aware datetime

# ✅ 正確方式 2：確保只對 UTC 時間加 'Z'
json_encoders = {
    datetime: lambda v: (
        v.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
        if v and v.tzinfo
        else v.isoformat() if v else None
    )
}
```

**修復優先級**: P0 - 必須立即修復
**預計工時**: 30 分鐘

---

### 問題 #3：`timezone_helpers.py` 未被使用

**嚴重程度**: 🔴 高危
**影響範圍**: 所有涉及 `stock_minute_prices` 的查詢和寫入
**問題描述**:

我們創建了 `timezone_helpers.py` 工具模組用於處理 `stock_minute_prices` 的時區轉換，但：
1. **沒有任何文件 import 這個模組**
2. 所有涉及 `stock_minute_prices` 的查詢和寫入都沒有進行時區轉換
3. 這意味著如果傳入 UTC 時間查詢，會得到錯誤結果（時差 8 小時）

**受影響的操作**:
```python
# backend/app/repositories/stock_minute_price.py:74-76
# ❌ 直接使用傳入的 datetime，沒有轉換
if start_datetime:
    query = query.filter(StockMinutePrice.datetime >= start_datetime)
if end_datetime:
    query = query.filter(StockMinutePrice.datetime <= end_datetime)

# 應該是：
# ✅ 先轉換為台灣時間
from app.utils.timezone_helpers import utc_to_naive_taipei

if start_datetime:
    start_tw = utc_to_naive_taipei(start_datetime)
    query = query.filter(StockMinutePrice.datetime >= start_tw)
if end_datetime:
    end_tw = utc_to_naive_taipei(end_datetime)
    query = query.filter(StockMinutePrice.datetime <= end_tw)
```

**受影響的文件**:
- `repositories/stock_minute_price.py` - 所有查詢方法
- `tasks/shioaji_sync.py` - 寫入分鐘線數據
- `scripts/sync_shioaji_to_qlib.py` - Qlib 同步
- 任何讀取或寫入 `stock_minute_prices` 的代碼

**修復方案**:
1. 在所有涉及 `stock_minute_prices` 的查詢前，使用 `utc_to_naive_taipei()` 轉換時間
2. 在寫入 `stock_minute_prices` 前，確保時間已經是台灣本地時間
3. 從資料庫讀取後，如果需要返回 API，使用 `naive_taipei_to_utc()` 轉換回 UTC

**修復優先級**: P0 - 必須立即修復
**預計工時**: 3-4 小時（需要修改多個查詢和寫入點）

---

### 問題 #4：前端其他頁面沒有指定時區參數

**嚴重程度**: 🟡 中危
**影響範圍**: Dashboard, Backtest, Strategies 等頁面
**問題描述**:

除了 `admin/index.vue` 已修復外，其他頁面的時間格式化函數沒有指定 `timeZone` 參數：

```typescript
// ❌ 錯誤：使用瀏覽器本地時區
// frontend/pages/dashboard/index.vue:360
return date.toLocaleDateString('zh-TW')

// frontend/pages/backtest/index.vue:901
return date.toLocaleDateString('zh-TW', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit'
  // ❌ 缺少 timeZone: 'Asia/Taipei'
})
```

**影響**:
- 如果用戶在台灣以外地區（如美國、歐洲），時間顯示會不正確
- 同一筆數據在不同地區的用戶看到的時間不一樣
- 與管理後台顯示不一致

**受影響的頁面**:
- `pages/dashboard/index.vue`
- `pages/backtest/index.vue`
- `pages/backtest/[id].vue`
- `pages/strategies/index.vue`
- `pages/strategies/[id]/index.vue`
- `pages/rdagent/*.vue`
- `pages/options/index.vue`
- `pages/institutional/index.vue`

**修復方案**:
```typescript
// ✅ 方案 1：使用全局 composable（推薦）
const { formatToTaiwanTime } = useDateTime()
return formatToTaiwanTime(dateStr)

// ✅ 方案 2：手動指定時區
return date.toLocaleDateString('zh-TW', {
  timeZone: 'Asia/Taipei',  // ← 加上這行
  year: 'numeric',
  month: '2-digit',
  day: '2-digit'
})
```

**修復優先級**: P1 - 應儘快修復
**預計工時**: 2-3 小時（需要修改 8+ 個頁面）

---

## 🟡 中優先級問題（建議修復）

### 問題 #5：Celery crontab 的 day_of_week 受時區影響

**嚴重程度**: 🟡 中危
**影響範圍**: 週末執行的任務
**問題描述**:

Celery crontab 的 `day_of_week` 在 UTC 時區下可能與台灣時間不同日：

```python
# backend/app/core/celery_app.py
"cleanup-institutional-data-weekly": {
    "task": "app.tasks.cleanup_old_institutional_data",
    "schedule": crontab(hour=18, minute=0, day_of_week='saturday'),
    # UTC Saturday 18:00 = 台灣 Sunday 02:00 ⚠️
}

"generate-continuous-contracts-weekly": {
    "task": "app.tasks.generate_continuous_contracts",
    "schedule": crontab(hour=10, minute=0, day_of_week='saturday'),
    # UTC Saturday 10:00 = 台灣 Saturday 18:00 ✅
}
```

**問題**:
- `cleanup-institutional-data-weekly`：設定為 UTC Saturday 18:00，實際執行在台灣 **Sunday** 02:00
- 如果業務邏輯要求「週六執行」，這會導致語意不符

**受影響的任務**:
- `cleanup-institutional-data-weekly` - UTC Sat 18:00 = 台灣 Sun 02:00
- `cleanup-old-signals-weekly` - UTC Sat 20:00 = 台灣 Sun 04:00
- `sync-fundamental-weekly` - UTC Sat 20:00 = 台灣 Sun 04:00
- `generate-continuous-contracts-weekly` - UTC Sat 10:00 = 台灣 Sat 18:00 ✅

**修復方案**:
```python
# 選項 1：調整為台灣週六執行
"cleanup-institutional-data-weekly": {
    "schedule": crontab(hour=18, minute=0, day_of_week='friday'),
    # UTC Friday 18:00 = 台灣 Saturday 02:00
}

# 選項 2：接受現狀，在文檔中說明
# 註：任務會在台灣週日凌晨執行
```

**修復優先級**: P2 - 可以稍後修復
**預計工時**: 30 分鐘（需與用戶確認業務需求）

---

### 問題 #6：資料庫時區設定未明確記錄

**嚴重程度**: 🟡 中危
**影響範圍**: 運維和新開發者
**問題描述**:

PostgreSQL 容器的時區設定未明確記錄，可能導致：
1. 新部署時忘記設定正確的時區
2. `func.now()` 的行為依賴未記錄的配置
3. 開發者不知道資料庫使用的時區

**當前狀態**:
- PostgreSQL 容器時區：UTC（來自容器 `SELECT NOW()`）
- 但 `docker-compose.yml` 中沒有明確設定 `TZ` 環境變數

**修復方案**:
```yaml
# docker-compose.yml
postgres:
  image: timescale/timescaledb:latest-pg15
  environment:
    POSTGRES_DB: quantlab
    POSTGRES_USER: quantlab
    POSTGRES_PASSWORD: quantlab2025
    TZ: UTC  # ← 明確設定時區
    PGTZ: UTC  # ← PostgreSQL 特定時區設定
```

**修復優先級**: P2 - 建議修復
**預計工時**: 15 分鐘

---

### 問題 #7：缺少時區相關的單元測試

**嚴重程度**: 🟡 中危
**影響範圍**: 測試覆蓋率和可靠性
**問題描述**:

沒有專門測試時區轉換邏輯的單元測試，無法保證：
1. `timezone_helpers.py` 的轉換邏輯正確
2. `stock_minute_prices` 的查詢在使用時區轉換後仍然正確
3. 跨日期邊界的任務執行時間正確

**建議的測試案例**:
```python
# tests/utils/test_timezone_helpers.py
def test_naive_taipei_to_utc():
    """測試台灣時間轉 UTC"""
    taipei_time = datetime(2025, 12, 20, 8, 0, 0)  # 台灣 08:00
    utc_time = naive_taipei_to_utc(taipei_time)
    assert utc_time.hour == 0  # UTC 00:00
    assert utc_time.tzinfo == timezone.utc

def test_utc_to_naive_taipei():
    """測試 UTC 轉台灣時間"""
    utc_time = datetime(2025, 12, 20, 0, 0, 0, tzinfo=timezone.utc)
    taipei_time = utc_to_naive_taipei(utc_time)
    assert taipei_time.hour == 8  # 台灣 08:00
    assert taipei_time.tzinfo is None  # naive datetime

def test_stock_minute_price_query_with_timezone():
    """測試分鐘線查詢的時區轉換"""
    # 傳入 UTC 時間
    utc_start = datetime(2025, 12, 20, 1, 0, 0, tzinfo=timezone.utc)
    utc_end = datetime(2025, 12, 20, 5, 0, 0, tzinfo=timezone.utc)

    # 應該查詢台灣 09:00-13:00 的數據
    results = StockMinutePriceRepository.get_minute_prices(
        db, stock_id='2330',
        start_datetime=utc_start,
        end_datetime=utc_end
    )

    # 驗證返回的數據時間範圍正確
    ...
```

**修復優先級**: P3 - 長期改善
**預計工時**: 4-6 小時

---

## ✅ 已正確實施的部分

1. ✅ **Models 使用 TIMESTAMPTZ**：除 `stock_minute_prices` 外，所有表格都正確使用 `DateTime(timezone=True)`
2. ✅ **Celery 配置正確**：`timezone='UTC'`, `enable_utc=True`
3. ✅ **Crontab 時間已調整**：所有排程都已轉換為 UTC 時間
4. ✅ **前端管理後台已修復**：`admin/index.vue` 使用 `useDateTime` composable
5. ✅ **文檔齊全**：`TIMEZONE_STRATEGY.md`, `CELERY_TIMEZONE_EXPLAINED.md` 等
6. ✅ **task_history.py 已修復**：使用 `datetime.now(timezone.utc)`

---

## 📊 修復優先級總覽

| 優先級 | 問題編號 | 問題描述 | 預計工時 | 狀態 |
|--------|---------|---------|---------|------|
| P0 | #1 | 後端大量使用 `datetime.now()` | 2-3 小時 | ⏳ 待修復 |
| P0 | #2 | Pydantic json_encoders 不正確 | 30 分鐘 | ⏳ 待修復 |
| P0 | #3 | `timezone_helpers.py` 未使用 | 3-4 小時 | ⏳ 待修復 |
| P1 | #4 | 前端其他頁面缺少時區指定 | 2-3 小時 | ⏳ 待修復 |
| P2 | #5 | Celery crontab day_of_week 問題 | 30 分鐘 | 💭 待確認 |
| P2 | #6 | 資料庫時區未明確記錄 | 15 分鐘 | ⏳ 待修復 |
| P3 | #7 | 缺少單元測試 | 4-6 小時 | 💡 長期改善 |

**總預計修復工時**: 13-17 小時

---

## 🎯 建議的修復順序

### 第一階段（立即執行，3-4 小時）
1. **問題 #2**：修復 `rdagent.py` 的 json_encoders（30 分鐘）
2. **問題 #6**：明確設定 PostgreSQL 時區（15 分鐘）
3. **問題 #3**：在 `stock_minute_price.py` 中使用 `timezone_helpers`（3-4 小時）

### 第二階段（1-2 天內，5-6 小時）
4. **問題 #1**：批次修復 `datetime.now()` → `datetime.now(timezone.utc)`（2-3 小時）
5. **問題 #4**：修復前端其他頁面的時區顯示（2-3 小時）

### 第三階段（與用戶確認後）
6. **問題 #5**：確認業務需求並調整 crontab（30 分鐘）

### 第四階段（長期）
7. **問題 #7**：添加單元測試（4-6 小時）

---

## 🚨 緊急風險評估

### 當前系統可能出現的問題

**場景 1：分鐘線數據查詢錯誤**
- 用戶請求台灣時間 09:00-13:00 的數據
- 前端傳送 UTC 01:00-05:00
- 後端沒有轉換，直接查詢
- 資料庫中存的是台灣時間 09:00-13:00
- **結果**：查無數據或查到錯誤時間的數據 ❌

**場景 2：資料庫寫入時區混亂**
- Task 使用 `datetime.now()` 生成時間（無時區）
- 寫入 TIMESTAMPTZ 欄位
- PostgreSQL 假設這是伺服器本地時區（UTC）
- 但實際 container 系統時區是 CST +0800
- **結果**：時間記錄錯誤 8 小時 ❌

**場景 3：跨時區用戶看到不同時間**
- 台灣用戶：瀏覽器時區 Asia/Taipei
- 美國用戶：瀏覽器時區 America/New_York
- 前端使用 `toLocaleDateString()` 不指定時區
- **結果**：同一筆數據顯示不同時間 ❌

---

## 📝 修復檢查清單

修復完成後，使用以下清單驗證：

### 後端檢查
- [ ] 搜尋 `datetime.now()`，確認所有改為 `datetime.now(timezone.utc)`
- [ ] 檢查所有 Pydantic schemas 的 datetime 序列化
- [ ] 驗證 `timezone_helpers.py` 在所有 `stock_minute_price` 操作中被使用
- [ ] 確認資料庫查詢的時區轉換正確
- [ ] 測試跨時區的數據寫入和讀取

### 前端檢查
- [ ] 搜尋 `toLocaleDateString`/`toLocaleTimeString`，確認都有 `timeZone: 'Asia/Taipei'`
- [ ] 所有頁面使用 `useDateTime` composable
- [ ] 測試不同時區瀏覽器的顯示一致性

### 系統檢查
- [ ] docker-compose.yml 明確設定 `TZ=UTC`
- [ ] 文檔更新，說明時區處理規範
- [ ] 添加時區相關的單元測試

---

## 💡 長期改善建議

1. **建立 pre-commit hook**：檢查新代碼是否使用了 `datetime.now()` 而非 `datetime.now(timezone.utc)`
2. **使用 Linter 規則**：配置 flake8/pylint 檢測不安全的 datetime 使用
3. **創建開發者指南**：在 CLAUDE.md 中添加時區處理的最佳實踐
4. **監控時區錯誤**：添加 Sentry/日誌警告，檢測 naive datetime 的使用
5. **完整遷移**：長期目標將 `stock_minute_prices` 也遷移為 TIMESTAMPTZ

---

**審查總結**: 時區遷移的基礎架構正確，但實際代碼中仍有大量時區處理不當的地方，需要系統性修復。建議先修復 P0 優先級問題，確保核心功能正確運作。

**下一步行動**: 立即修復問題 #2 和 #3，這兩個問題影響最大且修復相對獨立。
