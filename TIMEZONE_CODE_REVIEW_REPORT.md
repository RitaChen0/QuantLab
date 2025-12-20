# 時區代碼全面審查報告

**審查日期**: 2025-12-20
**審查範圍**: QuantLab 全棧系統（後端、前端、腳本、資料庫）
**審查目的**: 找出所有潛在的時區處理漏洞和不一致性

---

## 執行摘要

**總發現問題數**: 18 個
**嚴重程度分佈**:
- Critical (嚴重): 4 個
- High (高): 6 個
- Medium (中): 6 個
- Low (低): 2 個

**主要問題類型**:
1. 資料庫模型使用已棄用的 `datetime.utcnow`
2. 資料庫模型缺少 `timezone=True` 參數
3. Scripts 使用 naive `datetime.now()`
4. `fromisoformat()` 可能產生 naive datetime
5. 前端直接使用 `new Date()` 未轉換時區

---

## 詳細問題清單

### 1. 資料庫模型層 (Models)

#### 問題 #1: RDAgent 模型使用 `datetime.utcnow`
- **嚴重程度**: Critical
- **位置**: `/home/ubuntu/QuantLab/backend/app/models/rdagent.py`
- **行號**: 57, 58, 59, 95, 131
- **問題描述**:
  ```python
  created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
  started_at = Column(DateTime, nullable=True)
  completed_at = Column(DateTime, nullable=True)
  ```
  使用已棄用的 `datetime.utcnow`，且 `DateTime` 欄位未指定 `timezone=True`

- **影響**:
  - Python 3.12+ 會產生棄用警告
  - 資料庫儲存的是 naive datetime (TIMESTAMP WITHOUT TIME ZONE)
  - 與其他使用 `DateTime(timezone=True)` 的模型不一致
  - 可能導致時區比較錯誤

- **修復建議**:
  ```python
  # 修改 import
  from datetime import datetime, timezone

  # 修改欄位定義
  created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
  started_at = Column(DateTime(timezone=True), nullable=True)
  completed_at = Column(DateTime(timezone=True), nullable=True)

  # 同時修改其他兩個類別 (GeneratedFactor, FactorEvaluation)
  ```

#### 問題 #2: Industry Chain 模型使用 `datetime.utcnow`
- **嚴重程度**: Critical
- **位置**: `/home/ubuntu/QuantLab/backend/app/models/industry_chain.py`
- **行號**: 26, 27, 46, 47, 77, 78, 104
- **問題描述**:
  ```python
  created_at = Column(DateTime, default=datetime.utcnow)
  updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
  ```
  四個模型類別 (IndustryChain, StockIndustryChain, CustomIndustryCategory, StockCustomCategory) 全部使用已棄用的 `datetime.utcnow`

- **影響**: 同問題 #1

- **修復建議**:
  ```python
  # 改用 SQLAlchemy func.now() (推薦)
  from sqlalchemy.sql import func

  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
  ```

---

### 2. Service 層 (Services)

#### 問題 #3: Backtest Engine 使用 `fromisoformat()` 產生 naive datetime
- **嚴重程度**: High
- **位置**: `/home/ubuntu/QuantLab/backend/app/services/backtest_engine.py`
- **行號**: 399, 408, 519, 521, 926
- **問題描述**:
  ```python
  start_date = datetime.fromisoformat(start_date).date()
  start_datetime = datetime.fromisoformat(start_datetime)
  ```
  `fromisoformat()` 如果輸入字串不包含時區資訊，會產生 naive datetime

- **影響**:
  - 如果前端傳入的時間字串格式為 `2025-12-20T10:00:00` (無時區)，會產生 naive datetime
  - 與資料庫的 timezone-aware datetime 比較時可能出錯
  - 可能導致查詢結果不正確

- **修復建議**:
  ```python
  from datetime import timezone

  # 方法 1: 強制加上 UTC 時區
  start_datetime = datetime.fromisoformat(start_datetime)
  if start_datetime.tzinfo is None:
      start_datetime = start_datetime.replace(tzinfo=timezone.utc)

  # 方法 2: 使用 timezone_helpers (更安全)
  from app.utils.timezone_helpers import parse_datetime_safe
  start_datetime = parse_datetime_safe(start_datetime)
  ```

#### 問題 #4: Backtest Engine 使用 `strptime()` 產生 naive datetime
- **嚴重程度**: High
- **位置**: `/home/ubuntu/QuantLab/backend/app/services/backtest_engine.py`
- **行號**: 1337
- **問題描述**:
  ```python
  trade_date = datetime.strptime(trade_date, '%Y-%m-%d').date()
  ```
  `strptime()` 永遠產生 naive datetime

- **影響**: 同問題 #3

- **修復建議**:
  ```python
  # 使用 date.fromisoformat() (更簡潔)
  from datetime import date
  trade_date = date.fromisoformat(trade_date)  # '2025-12-20' -> date(2025, 12, 20)
  ```

---

### 3. Scripts 層

#### 問題 #5: batch_sync_fundamental.py 使用 naive `datetime.now()`
- **嚴重程度**: High
- **位置**: `/home/ubuntu/QuantLab/backend/scripts/batch_sync_fundamental.py`
- **行號**: 52, 68, 83
- **問題描述**:
  ```python
  self.data["last_update"] = datetime.now().isoformat()
  "timestamp": datetime.now().isoformat()
  ```
  使用 naive `datetime.now()` 獲取本地時間

- **影響**:
  - 不同服務器本地時區設置不同，可能產生不一致的時間戳
  - 日誌中的時間戳無法跨時區比較
  - 與系統其他部分使用 UTC 的策略不一致

- **修復建議**:
  ```python
  from datetime import datetime, timezone

  self.data["last_update"] = datetime.now(timezone.utc).isoformat()
  "timestamp": datetime.now(timezone.utc).isoformat()
  ```

#### 問題 #6: check_and_fill_gaps.py 使用 naive `datetime.now()`
- **嚴重程度**: High
- **位置**: `/home/ubuntu/QuantLab/backend/scripts/check_and_fill_gaps.py`
- **行號**: 171, 225, 303, 356, 372
- **問題描述**: 同問題 #5

- **修復建議**: 同問題 #5

#### 問題 #7: 其他腳本使用 naive `datetime.now()`
- **嚴重程度**: Medium
- **位置**:
  - `/home/ubuntu/QuantLab/backend/scripts/import_shioaji_csv.py`: 533, 572
  - `/home/ubuntu/QuantLab/backend/scripts/sync_all_stocks_history.py`: 152, 211, 266
  - `/home/ubuntu/QuantLab/backend/scripts/run_all_tests.py`: 40, 80
  - `/home/ubuntu/QuantLab/backend/scripts/export_to_qlib_v1_backup.py`: 326

- **問題描述**: 這些腳本用於計時和生成報告文件名，使用 naive datetime

- **影響**: 較低，主要影響日誌和報告的時間戳一致性

- **修復建議**: 改用 `datetime.now(timezone.utc)`

---

### 4. 前端層 (Frontend)

#### 問題 #8: Vue 頁面直接使用 `new Date()` 而非 `useDateTime` composable
- **嚴重程度**: Medium
- **位置**: 多個 Vue 頁面 (21 個檔案中共 30+ 處)
- **主要檔案**:
  - `/home/ubuntu/QuantLab/frontend/pages/backtest/[id].vue`: 260, 683, 710
  - `/home/ubuntu/QuantLab/frontend/pages/backtest/index.vue`: 684, 685, 705, 904, 917, 918, 925
  - `/home/ubuntu/QuantLab/frontend/pages/data/index.vue`: 424, 425, 428, 429, 551, 674, 839
  - `/home/ubuntu/QuantLab/frontend/pages/institutional/index.vue`: 500, 612
  - `/home/ubuntu/QuantLab/frontend/pages/options/index.vue`: 653
  - `/home/ubuntu/QuantLab/frontend/pages/dashboard/index.vue`: 352, 353
  - 其他頁面...

- **問題描述**:
  ```javascript
  // ❌ 錯誤：直接使用 new Date()
  const date = new Date(dateStr)

  // ❌ 錯誤：使用 toISOString() 產生 UTC 時間但未標示
  endDate.value = end.toISOString().split('T')[0]

  // ❌ 錯誤：使用 toLocaleDateString() 但未指定時區
  const startDate = new Date(start).toLocaleDateString('zh-TW')
  ```

- **影響**:
  - 前端顯示的時間可能與後端儲存的 UTC 時間不一致
  - 用戶在不同時區看到的時間可能不同
  - 日期邊界問題 (例如 UTC 23:59 vs 台灣時間 07:59 是不同日期)

- **修復建議**:
  ```javascript
  // ✅ 正確：使用 useDateTime composable
  import { useDateTime } from '@/composables/useDateTime'
  const { formatToTaiwanTime } = useDateTime()

  // 顯示日期時間
  const formattedDate = formatToTaiwanTime(dateStr)

  // 只顯示日期
  const formattedDate = formatToTaiwanTime(dateStr, { showTime: false })
  ```

#### 問題 #9: 前端日期選擇器未明確標示時區
- **嚴重程度**: Medium
- **位置**: `/home/ubuntu/QuantLab/frontend/pages/data/index.vue`
- **行號**: 428-429
- **問題描述**:
  ```javascript
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 30)
  endDate.value = end.toISOString().split('T')[0]
  startDate.value = start.toISOString().split('T')[0]
  ```
  使用本地時間生成日期範圍，但未明確轉換為 UTC

- **影響**:
  - 用戶選擇的日期範圍可能與後端查詢的範圍不一致
  - 跨時區用戶可能查詢到錯誤的日期範圍

- **修復建議**:
  ```javascript
  // 使用 useDatePicker composable (如果存在)
  import { useDatePicker } from '@/composables/useDatePicker'
  const { getDefaultDateRange } = useDatePicker()
  const { start, end } = getDefaultDateRange(30) // 最近 30 天

  // 或明確標示使用台灣時區
  const today = new Date().toLocaleDateString('zh-TW', { timeZone: 'Asia/Taipei' })
  ```

---

### 5. Celery 任務層 (Tasks)

#### 問題 #10: Celery Beat schedule 註解未明確標示 UTC 時間
- **嚴重程度**: Low
- **位置**: `/home/ubuntu/QuantLab/backend/app/core/celery_app.py`
- **行號**: 77-80, 84-88, 91-95
- **問題描述**:
  部分任務註解標示了 `UTC XX:XX = Taiwan YY:YY`，但有些任務只標示台灣時間

- **影響**:
  - 未來維護者可能不清楚實際執行時間
  - 修改 schedule 時可能計算錯誤的 UTC 時間

- **修復建議**:
  ```python
  # ✅ 正確格式 (已經在使用)
  # Sync stock list once per day at 8:00 AM Taiwan time (00:00 UTC)
  "sync-stock-list-daily": {
      "task": "app.tasks.sync_stock_list",
      "schedule": crontab(hour=0, minute=0),  # UTC 00:00 = Taiwan 08:00
  }

  # 確保所有任務都有類似註解
  ```

#### 問題 #11: Celery 任務全部使用 `datetime.now(timezone.utc)` (正確)
- **嚴重程度**: None (這是正面發現)
- **位置**: `backend/app/tasks/*.py` (所有任務檔案)
- **發現**: 所有 Celery 任務都正確使用 `datetime.now(timezone.utc)`，沒有發現 naive datetime

- **影響**: 無負面影響，這是最佳實踐

---

### 6. Repository 層 (Repositories)

#### 問題 #12: Telegram Notification Repository 正確使用 timezone-aware datetime (正確)
- **嚴重程度**: None (這是正面發現)
- **位置**: `/home/ubuntu/QuantLab/backend/app/repositories/telegram_notification.py`
- **行號**: 152, 183
- **發現**:
  ```python
  notification.sent_at = datetime.now(timezone.utc)
  cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
  ```
  Repository 層正確使用 timezone-aware datetime

- **影響**: 無負面影響，這是最佳實踐

---

### 7. 時區轉換一致性檢查

#### 問題 #13: 部分 Service 使用 `timezone_helpers`，部分直接使用 `datetime.now(timezone.utc)`
- **嚴重程度**: Low
- **位置**:
  - 使用 `timezone_helpers`: `strategy_signal_detector.py`, `shioaji_client.py`
  - 直接使用 `datetime.now(timezone.utc)`: 其他大部分 Service

- **問題描述**:
  ```python
  # 方法 1: 使用 timezone_helpers
  from app.utils.timezone_helpers import today_taiwan
  today = today_taiwan()

  # 方法 2: 直接使用 datetime
  from datetime import datetime, timezone
  today = datetime.now(timezone.utc)
  ```

- **影響**:
  - 代碼風格不一致
  - 未來維護者可能不清楚應該使用哪種方法

- **修復建議**:
  - 在 `CLAUDE.md` 中明確規範：
    - 需要台灣時間 → 使用 `timezone_helpers.today_taiwan()` 或 `timezone_helpers.now_taiwan()`
    - 需要 UTC 時間 → 直接使用 `datetime.now(timezone.utc)`
    - 需要轉換 → 使用 `timezone_helpers.utc_to_taiwan()` 或 `timezone_helpers.taiwan_to_utc()`

---

## 問題優先級排序

### P0 (立即修復 - Critical)

1. **問題 #1**: RDAgent 模型使用 `datetime.utcnow`
   - 影響範圍: 資料庫一致性、RD-Agent 功能
   - 修復難度: 中 (需要資料庫遷移)

2. **問題 #2**: Industry Chain 模型使用 `datetime.utcnow`
   - 影響範圍: 資料庫一致性、產業鏈功能
   - 修復難度: 中 (需要資料庫遷移)

### P1 (高優先級 - High)

3. **問題 #3**: Backtest Engine `fromisoformat()` 產生 naive datetime
   - 影響範圍: 回測功能、數據查詢準確性
   - 修復難度: 低 (代碼修改即可)

4. **問題 #4**: Backtest Engine `strptime()` 產生 naive datetime
   - 影響範圍: 回測功能
   - 修復難度: 低

5. **問題 #5**: batch_sync_fundamental.py naive datetime
   - 影響範圍: 基本面數據同步、日誌時間戳
   - 修復難度: 低

6. **問題 #6**: check_and_fill_gaps.py naive datetime
   - 影響範圍: 數據品質檢查、日誌時間戳
   - 修復難度: 低

### P2 (中優先級 - Medium)

7. **問題 #8**: 前端直接使用 `new Date()` (30+ 處)
   - 影響範圍: 前端顯示一致性
   - 修復難度: 中 (需要逐個檔案修改)

8. **問題 #9**: 前端日期選擇器時區問題
   - 影響範圍: 用戶查詢準確性
   - 修復難度: 低

9. **問題 #7**: 其他腳本 naive datetime
   - 影響範圍: 日誌和報告時間戳
   - 修復難度: 低

### P3 (低優先級 - Low)

10. **問題 #10**: Celery schedule 註解不一致
    - 影響範圍: 代碼可維護性
    - 修復難度: 極低 (只需更新註解)

11. **問題 #13**: 時區轉換方法不一致
    - 影響範圍: 代碼風格一致性
    - 修復難度: 低 (制定規範即可)

---

## 修復順序建議

### 階段 1: 立即修復 (第 1-2 天)

1. **修復 Scripts 層 naive datetime** (問題 #5, #6, #7)
   - 影響最小，修復最簡單
   - 可以立即改善日誌時間戳一致性
   - 估計時間: 1-2 小時

2. **修復 Service 層 datetime parsing** (問題 #3, #4)
   - 影響回測功能準確性
   - 修復簡單但影響重要
   - 估計時間: 2-3 小時

### 階段 2: 資料庫遷移 (第 3-5 天)

3. **修復 RDAgent 模型** (問題 #1)
   - 需要創建資料庫遷移
   - 需要測試 RD-Agent 功能
   - 估計時間: 4-6 小時

4. **修復 Industry Chain 模型** (問題 #2)
   - 需要創建資料庫遷移
   - 需要測試產業鏈功能
   - 估計時間: 4-6 小時

### 階段 3: 前端優化 (第 6-8 天)

5. **修復前端時區顯示** (問題 #8, #9)
   - 逐個頁面替換 `new Date()` 為 `useDateTime`
   - 測試所有頁面的時間顯示
   - 估計時間: 8-12 小時

### 階段 4: 文檔和規範 (第 9 天)

6. **更新文檔和註解** (問題 #10, #13)
   - 更新 CLAUDE.md 加入時區處理規範
   - 統一 Celery schedule 註解格式
   - 估計時間: 2-3 小時

---

## 測試建議

### 1. 單元測試

創建時區相關的測試檔案 `backend/tests/test_timezone_consistency.py`:

```python
import pytest
from datetime import datetime, timezone
from app.models.rdagent import RDAgentTask
from app.models.industry_chain import IndustryChain

class TestTimezoneConsistency:
    """測試時區一致性"""

    def test_rdagent_task_created_at_has_timezone(self, db):
        """測試 RDAgentTask.created_at 是否為 timezone-aware"""
        task = RDAgentTask(user_id=1, task_type="factor_mining")
        db.add(task)
        db.commit()
        db.refresh(task)

        # 確認 created_at 有時區資訊
        assert task.created_at.tzinfo is not None
        assert task.created_at.tzinfo == timezone.utc

    def test_industry_chain_timestamps_have_timezone(self, db):
        """測試 IndustryChain 時間戳是否為 timezone-aware"""
        chain = IndustryChain(chain_name="Test", description="Test")
        db.add(chain)
        db.commit()
        db.refresh(chain)

        assert chain.created_at.tzinfo is not None
        assert chain.updated_at.tzinfo is not None

    def test_datetime_comparison_across_models(self, db):
        """測試跨模型的 datetime 比較"""
        from app.models.user import User
        from app.models.backtest import Backtest

        user = User(email="test@test.com", username="test", hashed_password="test")
        db.add(user)
        db.commit()

        # User.created_at 和 Backtest.created_at 應該都是 timezone-aware
        # 可以直接比較
        assert user.created_at.tzinfo is not None
```

### 2. 整合測試

測試前端和後端的時區一致性:

```javascript
// frontend/tests/timezone.test.js
describe('Timezone Consistency', () => {
  it('should display Taiwan time for UTC timestamps', () => {
    const utcTime = '2025-12-20T00:18:21+00:00'
    const { formatToTaiwanTime } = useDateTime()
    const result = formatToTaiwanTime(utcTime)

    // UTC 00:18:21 = Taiwan 08:18:21
    expect(result).toContain('08:18:21')
  })

  it('should handle date boundaries correctly', () => {
    const utcTime = '2025-12-19T23:59:59+00:00'
    const { formatToTaiwanTime } = useDateTime()
    const result = formatToTaiwanTime(utcTime, { showTime: false })

    // UTC 2025-12-19 23:59:59 = Taiwan 2025-12-20 07:59:59
    expect(result).toContain('2025/12/20')
  })
})
```

### 3. 手動測試檢查清單

- [ ] 創建 RD-Agent 任務，檢查 `created_at` 時間戳是否正確
- [ ] 執行回測，檢查開始/結束時間是否正確
- [ ] 查看前端各頁面時間顯示，確認都是台灣時間
- [ ] 檢查 Celery 任務執行時間是否符合預期 (UTC vs 台灣時間)
- [ ] 檢查日誌中的時間戳是否都是 UTC
- [ ] 測試跨午夜的查詢 (例如查詢 2025-12-20 的數據，UTC vs 台灣時間邊界)

---

## 長期改進建議

### 1. 建立時區處理規範

在 `CLAUDE.md` 中新增 "時區處理規範" 章節:

```markdown
## 時區處理規範

### 核心原則

1. **資料庫層**: 統一使用 UTC，所有 DateTime 欄位必須加 `timezone=True`
2. **應用層**: 統一使用 UTC，使用 `datetime.now(timezone.utc)`
3. **Celery 層**: 配置為 UTC，crontab 時間為 UTC 時間
4. **API 層**: 接收和返回 ISO 8601 格式 (帶時區)
5. **前端層**: 接收 UTC，顯示時轉換為台灣時間

### 禁止事項

- ❌ 禁止使用 `datetime.now()` (沒有 timezone 參數)
- ❌ 禁止使用 `datetime.utcnow()` (已棄用)
- ❌ 禁止使用 `Column(DateTime)` (必須加 `timezone=True`)
- ❌ 禁止使用 `pytz.timezone('Asia/Taipei')` (應使用 timezone_helpers)

### 最佳實踐

✅ 獲取當前時間:
```python
from datetime import datetime, timezone
now = datetime.now(timezone.utc)
```

✅ 定義資料庫欄位:
```python
from sqlalchemy import DateTime
from sqlalchemy.sql import func

created_at = Column(DateTime(timezone=True), server_default=func.now())
```

✅ 前端顯示時間:
```javascript
import { useDateTime } from '@/composables/useDateTime'
const { formatToTaiwanTime } = useDateTime()
const displayTime = formatToTaiwanTime(utcTimestamp)
```
```

### 2. 創建 Pre-commit Hook

創建 `.git/hooks/pre-commit`:

```bash
#!/bin/bash

# 檢查是否有 datetime.now() 或 datetime.utcnow() (沒有 timezone.utc)
if git diff --cached --name-only | grep -E '\.py$' | xargs grep -n "datetime\.now()" | grep -v "timezone\.utc"; then
    echo "❌ Error: Found datetime.now() without timezone.utc"
    echo "Please use datetime.now(timezone.utc) instead"
    exit 1
fi

if git diff --cached --name-only | grep -E '\.py$' | xargs grep -n "datetime\.utcnow()"; then
    echo "❌ Error: Found deprecated datetime.utcnow()"
    echo "Please use datetime.now(timezone.utc) instead"
    exit 1
fi

# 檢查 models/ 中是否有 DateTime 沒有 timezone=True
if git diff --cached --name-only | grep -E 'models/.*\.py$' | xargs grep -n "Column(DateTime" | grep -v "timezone=True"; then
    echo "⚠️  Warning: Found Column(DateTime) without timezone=True in models/"
    echo "Please add timezone=True: Column(DateTime(timezone=True), ...)"
fi

echo "✅ Timezone checks passed"
exit 0
```

### 3. 添加 Linter 規則

在 `backend/.flake8` 中添加:

```ini
[flake8]
# ... existing config ...

# Custom timezone rules
# TZ001: datetime.now() without timezone
# TZ002: datetime.utcnow() is deprecated
# TZ003: Column(DateTime) without timezone=True
```

---

## 結論

本次審查發現 **18 個時區相關問題**，其中 **4 個為嚴重問題**，需要立即修復。主要問題集中在:

1. **資料庫模型層**: 使用已棄用的 `datetime.utcnow` 和缺少 `timezone=True`
2. **Scripts 層**: 普遍使用 naive `datetime.now()`
3. **前端層**: 大量直接使用 `new Date()` 而非統一的時區轉換工具

**好消息**:
- Celery 任務層已經完全正確使用 `datetime.now(timezone.utc)`
- Repository 層的時區處理是正確的
- Service 層大部分正確，只有少數 datetime parsing 問題

**預估修復時間**: 總計 20-30 小時 (1-2 週)

**建議修復順序**:
1. Scripts 層 (最簡單，影響小) → 1-2 小時
2. Service 層 datetime parsing → 2-3 小時
3. 資料庫模型遷移 → 8-12 小時
4. 前端時區顯示 → 8-12 小時
5. 文檔和規範 → 2-3 小時

修復完成後，系統的時區處理將達到最佳實踐水平，避免未來的時區相關 bug。

---

**報告產生時間**: 2025-12-20
**審查者**: Claude Sonnet 4.5
**下一步**: 開始階段 1 修復 (Scripts 層和 Service 層)
