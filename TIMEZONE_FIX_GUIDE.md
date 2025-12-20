# 時區問題修復指南

本指南提供逐步修復時區不一致問題的操作步驟。

---

## 🎯 修復優先級

根據 [TIMEZONE_MIGRATION_AUDIT_REPORT.md](TIMEZONE_MIGRATION_AUDIT_REPORT.md) 的審查結果，按以下順序修復：

### P0 - 高優先級（立即修復）

1. ✅ 修復 `institutional_investor.py` 時區標記
2. ✅ 批量修復 44 處 `datetime.now()` 未設置時區
3. ✅ 修復 5 處 `datetime.utcnow()` 使用

### P1 - 中優先級（近期修復）

4. 統一 API Schema `json_encoders`
5. 統一前端時區轉換函數

### P2 - 低優先級（改進項目）

6. 修復舊 Alembic 遷移
7. 增加時區相關註釋

---

## 🛠️  修復步驟

### 步驟 1: 備份與準備

```bash
cd /home/ubuntu/QuantLab

# 1. 確保所有變更已提交
git status

# 2. 創建修復分支
git checkout -b fix/timezone-consistency

# 3. 備份資料庫（可選，但建議）
docker compose exec postgres pg_dump -U quantlab quantlab > backup_before_timezone_fix.sql
```

---

### 步驟 2: 修復 institutional_investor.py 時區標記

#### 2.1 修改模型

編輯 `/home/ubuntu/QuantLab/backend/app/models/institutional_investor.py`:

```python
# 找到第 39-40 行
created_at = Column(DateTime, server_default=func.now(), nullable=False)
updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

# 修改為
created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
```

#### 2.2 創建資料庫遷移

```bash
# 進入後端容器
docker compose exec backend bash

# 創建遷移
alembic revision --autogenerate -m "fix institutional_investor timezone"

# 退出容器
exit
```

#### 2.3 檢查遷移文件

```bash
# 查看最新遷移文件
ls -lt backend/alembic/versions/*.py | head -1

# 檢查內容，應包含類似這樣的變更:
# op.alter_column('institutional_investors', 'created_at',
#     type_=sa.DateTime(timezone=True))
```

#### 2.4 執行遷移

```bash
docker compose exec backend alembic upgrade head
```

#### 2.5 驗證

```bash
# 連接資料庫檢查欄位類型
docker compose exec postgres psql -U quantlab quantlab -c "
  SELECT column_name, data_type, is_nullable
  FROM information_schema.columns
  WHERE table_name = 'institutional_investors'
    AND column_name IN ('created_at', 'updated_at');
"

# 應顯示: timestamp with time zone
```

---

### 步驟 3: 批量修復 datetime.now() 和 datetime.utcnow()

#### 3.1 預覽修改

```bash
# 使用修復腳本（預覽模式）
python scripts/fix_datetime_timezone.py --dry-run

# 檢查輸出，確認修改正確
```

#### 3.2 執行修復

```bash
# 實際執行修改
python scripts/fix_datetime_timezone.py

# 查看變更
git diff backend/app
```

#### 3.3 手動檢查特殊情況

有些代碼可能需要手動調整，特別是:

```python
# 情況 1: import datetime (而非 from datetime import datetime)
import datetime
now = datetime.datetime.now(datetime.timezone.utc)  # 自動替換後的結果

# 建議手動改為:
from datetime import datetime, timezone
now = datetime.now(timezone.utc)

# 情況 2: 註釋中的 datetime.now()
# 腳本會忽略註釋，無需處理

# 情況 3: 字串中的 "datetime.now()"
text = "使用 datetime.now() 獲取時間"  # 腳本會忽略字串
```

#### 3.4 驗證修改

```bash
# 檢查是否還有遺漏
grep -r "datetime\.now()" backend/app --include="*.py" | grep -v "timezone.utc" | grep -v "#"

# 應該沒有輸出（或僅有註釋/字串）

# 檢查 utcnow
grep -r "datetime\.utcnow()" backend/app --include="*.py"

# 應該沒有輸出
```

---

### 步驟 4: 統一 API Schema json_encoders

#### 4.1 創建基礎 Schema

創建 `/home/ubuntu/QuantLab/backend/app/schemas/base.py`:

```python
"""
Base Schemas with Timezone-Aware Serialization

所有 Pydantic schemas 的基類，統一處理時區序列化。
"""
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class TimezoneAwareSchema(BaseModel):
    """
    時區感知的 Schema 基類

    自動將 datetime 序列化為 ISO 8601 格式（包含時區標記）

    Example:
        >>> class UserSchema(TimezoneAwareSchema):
        ...     created_at: datetime
        >>> user = UserSchema(created_at=datetime.now(timezone.utc))
        >>> user.model_dump_json()
        '{"created_at": "2025-12-20T12:30:00+00:00"}'
    """
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )
```

#### 4.2 更新現有 Schemas

逐個修改以下文件，將基類改為 `TimezoneAwareSchema`:

**檔案清單**:
- `backend/app/schemas/backtest.py`
- `backend/app/schemas/strategy.py`
- `backend/app/schemas/user.py`
- `backend/app/schemas/stock.py`
- `backend/app/schemas/stock_price.py`
- `backend/app/schemas/stock_minute_price.py`
- `backend/app/schemas/fundamental.py`
- `backend/app/schemas/institutional_investor.py`
- 其他 schema 文件

**修改範例**:

```python
# 原代碼
from pydantic import BaseModel, ConfigDict

class BacktestInDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    # ...

# 修改為
from app.schemas.base import TimezoneAwareSchema

class BacktestInDB(TimezoneAwareSchema):
    # model_config 會從基類繼承
    # ...
```

#### 4.3 驗證

```bash
# 啟動服務
docker compose up -d

# 測試 API 響應
curl -s http://localhost:8000/api/v1/strategies | jq '.strategies[0].created_at'

# 應輸出類似: "2025-12-20T12:30:00+00:00" (包含 +00:00)
```

---

### 步驟 5: 統一前端時區轉換

#### 5.1 檢查需要修改的頁面

```bash
# 運行檢查腳本
bash scripts/check_frontend_timezone.sh

# 查看輸出，找出未使用 useDateTime 的頁面
```

#### 5.2 逐頁修改

對每個需要修改的頁面，執行以下步驟:

**範例: pages/account/profile.vue**

原代碼 (line 223):
```javascript
const formatDate = (date: any) => {
  if (!date) return '未知'
  return new Date(date).toLocaleString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
```

修改為:
```javascript
import { formatToTaiwanTime } from '@/composables/useDateTime'

const formatDate = (date: any) => {
  return formatToTaiwanTime(date, { showSeconds: false })
}
```

#### 5.3 批量查找替換

可使用以下命令協助查找:

```bash
cd /home/ubuntu/QuantLab/frontend

# 查找所有使用 toLocaleString 的地方
grep -rn "toLocaleString" pages/ --include="*.vue"

# 查找自定義 formatDate 函數
grep -rn "function formatDate\|const formatDate" pages/ --include="*.vue"
```

#### 5.4 測試前端

```bash
# 重啟前端
docker compose restart frontend

# 在瀏覽器中檢查各頁面的時間顯示是否正確
```

---

### 步驟 6: 執行測試

#### 6.1 後端測試

```bash
# 執行所有測試
docker compose exec backend pytest

# 執行特定測試
docker compose exec backend pytest tests/test_timezone.py -v
```

#### 6.2 前端測試

```bash
# 執行 linting
docker compose exec frontend npm run lint

# 手動測試關鍵頁面
# - /admin - 任務歷史時間
# - /strategies - 策略創建/更新時間
# - /backtest - 回測時間
```

#### 6.3 整合測試

```bash
# 測試完整流程
# 1. 創建策略 -> 檢查 created_at 時間
# 2. 執行回測 -> 檢查 started_at, completed_at 時間
# 3. 查看任務歷史 -> 檢查 last_run 時間
```

---

### 步驟 7: 提交與部署

#### 7.1 檢查變更

```bash
git status
git diff

# 確保修改正確
```

#### 7.2 提交變更

```bash
git add .
git commit -m "fix: 統一時區處理，修復 datetime.now() 和前端時區轉換

修改內容:
1. 修復 institutional_investor.py DateTime(timezone=True)
2. 批量修復 44 處 datetime.now() -> datetime.now(timezone.utc)
3. 修復 5 處 datetime.utcnow() -> datetime.now(timezone.utc)
4. 創建 TimezoneAwareSchema 統一 API 序列化
5. 統一前端使用 formatToTaiwanTime()

參考: TIMEZONE_MIGRATION_AUDIT_REPORT.md"
```

#### 7.3 合併到主分支

```bash
# 切換到 master
git checkout master

# 合併修復分支
git merge fix/timezone-consistency

# 推送到遠端
git push origin master
```

#### 7.4 重啟服務

```bash
# 重啟所有服務以應用變更
docker compose restart

# 清空 Redis (清除舊的 task_history)
docker compose exec redis redis-cli FLUSHDB

# 檢查日誌
docker compose logs -f backend | head -50
```

---

## ✅ 驗證檢查清單

修復完成後，逐項檢查:

### 後端

- [ ] `institutional_investor` 表的 `created_at`/`updated_at` 為 `TIMESTAMPTZ`
- [ ] 無任何 `datetime.now()` (應為 `datetime.now(timezone.utc)`)
- [ ] 無任何 `datetime.utcnow()` (已棄用)
- [ ] 所有 Schemas 繼承 `TimezoneAwareSchema`
- [ ] API 響應包含時區標記 (如 `+00:00`)

### 前端

- [ ] 所有頁面使用 `formatToTaiwanTime` 而非 `toLocaleString`
- [ ] 時間顯示格式一致
- [ ] 跨日期邊界顯示正確 (UTC 16:00 = 台灣次日 00:00)

### 資料庫

- [ ] 查詢 `institutional_investors` 表，`created_at` 包含時區
- [ ] 新插入的資料時間正確

### Celery

- [ ] 任務執行時間正確 (UTC 時間)
- [ ] `task_history` 記錄時間為 UTC

---

## 🐛 常見問題排查

### 問題 1: Alembic 遷移失敗

**症狀**: `alembic upgrade head` 報錯

**解決**:
```bash
# 檢查當前版本
docker compose exec backend alembic current

# 回滾到上一版本
docker compose exec backend alembic downgrade -1

# 修復遷移腳本後重試
docker compose exec backend alembic upgrade head
```

### 問題 2: 修復腳本誤修改註釋

**症狀**: 註釋中的 `datetime.now()` 被替換

**解決**:
```bash
# 手動還原
git checkout backend/app/path/to/file.py

# 或編輯文件手動修復
```

### 問題 3: 前端時間顯示錯誤

**症狀**: 時間偏移 8 小時

**診斷**:
```bash
# 檢查 API 響應
curl -s http://localhost:8000/api/v1/strategies | jq '.strategies[0].created_at'

# 應包含 +00:00，如: "2025-12-20T12:30:00+00:00"
# 如果沒有，檢查 Schema json_encoders
```

### 問題 4: 測試失敗

**症狀**: pytest 執行失敗

**解決**:
```bash
# 查看詳細錯誤
docker compose exec backend pytest -v --tb=short

# 修復測試代碼中的時區問題
# 確保測試也使用 datetime.now(timezone.utc)
```

---

## 📚 參考資料

- [TIMEZONE_MIGRATION_AUDIT_REPORT.md](TIMEZONE_MIGRATION_AUDIT_REPORT.md) - 完整審查報告
- [TIMEZONE_STRATEGY.md](TIMEZONE_STRATEGY.md) - 時區統一策略
- [backend/app/utils/timezone_helpers.py](backend/app/utils/timezone_helpers.py) - 時區轉換工具
- [frontend/composables/useDateTime.ts](frontend/composables/useDateTime.ts) - 前端時區格式化

---

**制定日期**: 2025-12-20
**維護者**: Claude Code
