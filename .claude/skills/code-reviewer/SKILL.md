---
name: code-reviewer
description: Reviews code changes for QuantLab project using team standards. Use when reviewing pull requests, examining diffs, checking code quality, or when asked to "review code" or "check this change".
allowed-tools: Read, Grep, Glob, Bash(git:*)
model: sonnet
---

# QuantLab Code Reviewer

專為 QuantLab 台股量化交易平台設計的代碼審查技能。

## 審查流程

當收到代碼審查請求時，按以下順序進行：

### 1. 獲取變更範圍

```bash
# 檢查當前分支狀態
git status

# 查看變更的文件
git diff --name-status

# 查看完整差異
git diff
```

### 2. 執行分層審查

按優先級檢查以下項目，**發現 Critical 問題立即報告**。

---

## 審查標準

### 🏗️ A. 架構規範（Critical）

**QuantLab 使用嚴格的四層架構**：

```
api/v1/          → 路由層（HTTP 處理）
  ↓ 只能調用
services/        → 業務邏輯層
  ↓ 只能調用
repositories/    → 資料訪問層
  ↓ 只能調用
models/          → ORM 模型層
```

**檢查清單**：
- [ ] **Critical**: API 層不直接調用 Repository 或 ORM
- [ ] **Critical**: Service 層不直接操作 ORM（必須通過 Repository）
- [ ] **Warning**: 新功能是否按順序實作（Model → Repository → Service → API）
- [ ] **Info**: 是否有跨層調用（禁止）

**範例違規**：
```python
# ❌ Critical: API 層直接查詢資料庫
@router.get("/strategies/")
def get_strategies(db: Session = Depends(get_db)):
    return db.query(Strategy).all()  # 違反分層

# ✅ 正確
@router.get("/strategies/")
def get_strategies(
    strategy_service: StrategyService = Depends()
):
    return strategy_service.get_all_strategies()
```

---

### ⏰ B. 時區處理（Critical）

**QuantLab 統一使用 UTC 時區**。

**檢查清單**：
- [ ] **Critical**: 所有 Model 的 datetime 欄位使用 `DateTime(timezone=True)`
- [ ] **Critical**: 所有 Model 的 `server_default=func.now()`（不是 Python datetime）
- [ ] **Critical**: 沒有使用 `datetime.utcnow`（已棄用）
- [ ] **Critical**: 沒有使用 `datetime.now()` 不帶時區
- [ ] **Warning**: Repository/Service 使用 `timezone_helpers.now_utc()`
- [ ] **Warning**: `stock_minute_prices` 操作有時區轉換（此表使用台灣時間）
- [ ] **Info**: Celery crontab 使用 UTC 時間並附註台北時間

**範例違規**：
```python
# ❌ Critical: 缺少時區
created_at = Column(DateTime, nullable=False)

# ❌ Critical: 使用已棄用函數
created_at = datetime.utcnow()

# ✅ 正確
# Model 層
created_at = Column(DateTime(timezone=True), server_default=func.now())

# Service 層
from app.utils.timezone_helpers import now_utc
created_at = now_utc()
```

**參考文檔**：`Document/TIMEZONE_COMPLETE_GUIDE.md`

---

### 🗄️ C. 資料庫變更（Critical）

**修改 models/ 後必須執行的步驟**。

**檢查清單**：
- [ ] **Critical**: 已創建 Alembic 遷移腳本（`alembic revision --autogenerate`）
- [ ] **Critical**: 遷移腳本包含 `upgrade()` 和 `downgrade()`
- [ ] **Critical**: 已測試遷移上升和回滾
- [ ] **Warning**: 已更新 `Document/DATABASE_SCHEMA_REPORT.md`
- [ ] **Warning**: 新增資料表有索引設計（外鍵、查詢欄位）
- [ ] **Warning**: 有資料的表使用 `batch_alter_table()`（避免鎖表）
- [ ] **Info**: 參考 `DATABASE_CHANGE_CHECKLIST.md`（56 項）

**範例檢查**：
```python
# 檢查是否有新的遷移
ls -lt backend/alembic/versions/ | head -5

# 檢查遷移內容
cat backend/alembic/versions/最新的遷移文件.py
```

**參考文檔**：
- `Document/DATABASE_CHANGE_CHECKLIST.md`
- `Document/DATABASE_SCHEMA_REPORT.md`

---

### ⚙️ D. Celery 任務（Warning）

**Celery 配置統一使用 UTC 時區**。

**檢查清單**：
- [ ] **Critical**: 定時任務配置 `expires` 參數（防止 revoked）
  - 每日任務：`expires: 82800`（23 小時）
  - 每週任務：`expires: 604800`（7 天）
  - 高頻任務（15 分鐘）：**不設置** expires
- [ ] **Warning**: crontab 使用 UTC 時間，註解標註台北時間
- [ ] **Warning**: 長時間任務使用 `@skip_if_recently_executed` 裝飾器
- [ ] **Info**: 任務有失敗重試機制（`autoretry_for`）

**範例違規**：
```python
# ❌ Critical: 高頻任務設置 expires 會立即過期
@shared_task(expires=300)
@celery_app.task(name="sync-latest-prices")
def sync_latest_prices():
    pass

# ❌ Warning: 缺少時區註解
"schedule": crontab(hour=15, minute=0),

# ✅ 正確
# 高頻任務不設置 expires
@shared_task
@celery_app.task(name="sync-latest-prices")
def sync_latest_prices():
    pass

# 每日任務設置 expires
"sync-daily-prices": {
    "task": "app.tasks.sync_daily_prices",
    "schedule": crontab(hour=21, minute=0),  # UTC 21:00 = 台北 05:00
    "options": {"expires": 82800},  # 23 hours
},
```

**參考文檔**：`Document/CELERY_REVOKED_TASKS_FIX.md`

---

### 🔒 E. 安全性（Critical）

**檢查清單**：
- [ ] **Critical**: 無硬編碼密鑰、API token（使用環境變數）
- [ ] **Critical**: 無 SQL 注入風險（使用 ORM 參數化查詢）
- [ ] **Critical**: API 輸入驗證完整（Pydantic schema）
- [ ] **Critical**: 無 XSS 風險（前端輸出轉義）
- [ ] **Warning**: 敏感操作有權限檢查
- [ ] **Warning**: 文件上傳有類型和大小限制
- [ ] **Info**: CORS 配置正確

**範例違規**：
```python
# ❌ Critical: SQL 注入風險
query = f"SELECT * FROM stocks WHERE stock_id = '{stock_id}'"

# ❌ Critical: 硬編碼密鑰
API_KEY = "sk-1234567890abcdef"

# ✅ 正確
# 使用 ORM
stocks = db.query(Stock).filter(Stock.stock_id == stock_id).all()

# 使用環境變數
from app.core.config import settings
api_key = settings.FINLAB_API_TOKEN
```

---

### 🧪 F. 測試規範（Warning）

**QuantLab 使用 pytest，測試文件必須在 `backend/tests/` 目錄下**。

**檢查清單**：
- [ ] **Critical**: 測試文件在 `backend/tests/` 目錄下（不在根目錄或 scripts/）
- [ ] **Warning**: 新功能有單元測試（目標覆蓋率 >80%）
- [ ] **Warning**: 整合測試使用 `@pytest.mark.integration`
- [ ] **Warning**: 慢速測試使用 `@pytest.mark.slow`
- [ ] **Info**: 測試涵蓋邊界情況和異常處理

**範例檢查**：
```bash
# ❌ Critical: 錯誤位置
/test_my_feature.py
/backend/test_my_feature.py
/backend/scripts/test_my_feature.py

# ✅ 正確位置
/backend/tests/services/test_my_feature.py
/backend/tests/api/test_my_endpoint.py
```

**測試結構**：
```
backend/tests/
├── api/          # API 端點測試
├── services/     # 業務邏輯測試
├── repositories/ # 資料訪問測試
├── tasks/        # Celery 任務測試
└── scripts/      # 腳本測試
```

**參考**：`CLAUDE.md` 的測試規範章節

---

### 📝 G. 代碼質量（Info）

**檢查清單**：
- [ ] **Warning**: 函數長度 < 50 行（複雜函數應拆分）
- [ ] **Warning**: 無明顯代碼重複（DRY 原則）
- [ ] **Info**: 變數命名清晰（避免 `x`, `tmp`, `data`）
- [ ] **Info**: 複雜邏輯有註解說明
- [ ] **Info**: Type hints 完整（Python）或 strict mode（TypeScript）

---

## 審查報告格式

按嚴重程度分類列出問題：

```markdown
## 代碼審查報告

### 📊 變更概覽
- 修改文件：X 個
- 新增行數：+XXX
- 刪除行數：-XXX

---

### 🚨 Critical Issues（必須修復）

1. **[檔案:行號] 問題描述**
   - 違反規範：具體說明
   - 建議修復：具體代碼

   ```python
   # ❌ 當前代碼
   錯誤代碼

   # ✅ 建議修改
   正確代碼
   ```

---

### ⚠️ Warnings（強烈建議修復）

1. **[檔案:行號] 問題描述**
   - 原因：...
   - 建議：...

---

### 💡 Info（最佳實踐建議）

1. **[檔案:行號] 建議**
   - 說明：...

---

### ✅ 正面評價

列出代碼中做得好的地方：
- 正確使用了...
- 良好的...設計

---

### 📚 相關文檔

- [CLAUDE.md](../../../CLAUDE.md) - 開發指南
- [Document/DATABASE_CHANGE_CHECKLIST.md](../../../Document/DATABASE_CHANGE_CHECKLIST.md)
- [Document/TIMEZONE_COMPLETE_GUIDE.md](../../../Document/TIMEZONE_COMPLETE_GUIDE.md)
```

---

## 快速參考

### 常見問題快速檢查

```bash
# 1. 檢查時區處理
grep -r "datetime.now()" --include="*.py" | grep -v "timezone.utc"
grep -r "datetime.utcnow" --include="*.py"
grep -r "DateTime(" backend/app/models/ | grep -v "timezone=True"

# 2. 檢查測試文件位置
find . -name "test_*.py" -not -path "*/backend/tests/*" -not -path "*/__pycache__/*"

# 3. 檢查是否有遷移
ls -lt backend/alembic/versions/ | head -5

# 4. 檢查跨層調用
grep -r "db.query" backend/app/api/ --include="*.py"
grep -r "from.*models import" backend/app/api/ --include="*.py"

# 5. 檢查硬編碼密鑰
grep -r "api_key\s*=\s*['\"]" --include="*.py"
grep -r "password\s*=\s*['\"]" --include="*.py"
```

---

## 使用範例

### 範例 1：審查 Pull Request

**用戶請求**：
```
請審查這個 PR
```

**操作流程**：
1. `git diff main...current-branch` 查看所有變更
2. 按 A-G 順序檢查每個類別
3. 發現問題立即記錄（Critical 優先）
4. 生成審查報告

### 範例 2：審查特定文件

**用戶請求**：
```
審查 backend/app/services/backtest_service.py
```

**操作流程**：
1. 讀取文件內容
2. 重點檢查：
   - 是否調用了 Repository（正確）還是直接操作 ORM（錯誤）
   - 時區處理是否使用 `timezone_helpers`
   - 業務邏輯是否清晰
3. 生成報告

### 範例 3：審查資料庫變更

**用戶請求**：
```
我修改了 models/strategy.py，請檢查
```

**操作流程**：
1. 讀取 `backend/app/models/strategy.py`
2. **重點檢查**：
   - DateTime 欄位有 `timezone=True`
   - server_default 使用 `func.now()`
3. 檢查是否有 Alembic 遷移
4. 提醒更新 DATABASE_SCHEMA_REPORT.md

---

## 自動觸發條件

當用戶說以下內容時，自動使用此技能：

- "請審查這個 PR"
- "Review this code"
- "檢查這段代碼"
- "這樣寫對嗎"
- "幫我看看這個修改"
- "code review"
- "審查變更"

---

## 注意事項

1. **Critical 問題必須優先報告** - 發現架構違規或安全問題立即說明
2. **提供具體修復建議** - 不只指出問題，要給出正確代碼範例
3. **參考項目文檔** - 引用 CLAUDE.md 和 Document/ 下的相關指南
4. **正面反饋** - 列出代碼中做得好的地方
5. **避免過度檢查** - 小改動（如修改註解）不需要完整審查

---

## 相關文檔

- [CLAUDE.md](../../../CLAUDE.md) - QuantLab 開發指南（核心）
- [Document/DATABASE_CHANGE_CHECKLIST.md](../../../Document/DATABASE_CHANGE_CHECKLIST.md) - 56 項檢查清單
- [Document/TIMEZONE_COMPLETE_GUIDE.md](../../../Document/TIMEZONE_COMPLETE_GUIDE.md) - 時區處理規範
- [Document/CELERY_REVOKED_TASKS_FIX.md](../../../Document/CELERY_REVOKED_TASKS_FIX.md) - Celery 配置指南
- [Document/DATABASE_SCHEMA_REPORT.md](../../../Document/DATABASE_SCHEMA_REPORT.md) - 資料庫架構

---

**版本**: 1.0
**最後更新**: 2025-12-27
