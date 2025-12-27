# Code Reviewer 快速參考

## 🚦 審查優先級

```
Critical (🚨) → 必須修復，阻擋合併
Warning  (⚠️) → 強烈建議修復
Info     (💡) → 最佳實踐建議
```

---

## ✅ 快速檢查清單

### 1. 架構檢查（30 秒）

```bash
# 檢查 API 層是否直接調用 ORM
grep -r "db.query" backend/app/api/ --include="*.py"
grep -r "from.*models import" backend/app/api/v1/ --include="*.py"
```

- [ ] API 層只調用 Service
- [ ] Service 層只調用 Repository
- [ ] Repository 層操作 ORM

### 2. 時區檢查（30 秒）

```bash
# 檢查時區問題
grep -r "datetime.now()" backend/app/ --include="*.py" | grep -v "timezone.utc" | grep -v "timezone_helpers"
grep -r "datetime.utcnow" backend/app/ --include="*.py"
grep -r "DateTime(" backend/app/models/ --include="*.py" | grep -v "timezone=True"
```

- [ ] Model 使用 `DateTime(timezone=True)`
- [ ] Model 使用 `server_default=func.now()`
- [ ] 無 `datetime.utcnow`（已棄用）
- [ ] Service 使用 `timezone_helpers.now_utc()`

### 3. 資料庫變更檢查（1 分鐘）

```bash
# 檢查是否有新遷移
ls -lt backend/alembic/versions/ | head -5

# 如果修改了 models/，必須有新遷移
git diff --name-only | grep "backend/app/models/"
```

- [ ] 修改 models/ 後有創建遷移
- [ ] 遷移有 upgrade() 和 downgrade()
- [ ] 已更新 DATABASE_SCHEMA_REPORT.md

### 4. 測試位置檢查（10 秒）

```bash
# 查找錯誤位置的測試文件
find . -name "test_*.py" -not -path "*/backend/tests/*" -not -path "*/__pycache__/*" -not -path "*/.git/*"
```

- [ ] 所有測試在 `backend/tests/` 下
- [ ] 無根目錄或 scripts/ 下的 test_* 文件

### 5. 安全檢查（30 秒）

```bash
# 檢查硬編碼密鑰
grep -rE "(api_key|password|secret|token)\s*=\s*['\"][^$]" backend/app/ --include="*.py" | grep -v "settings\."

# 檢查 SQL 注入風險
grep -r "f\"SELECT" backend/app/ --include="*.py"
grep -r "\.format.*SELECT" backend/app/ --include="*.py"
```

- [ ] 無硬編碼密鑰
- [ ] 無 SQL 注入風險
- [ ] 使用 Pydantic 驗證輸入

---

## 🎯 常見問題速查

### 問題 1：API 層直接查詢資料庫

```python
# ❌ 錯誤
@router.get("/strategies/")
def get_strategies(db: Session = Depends(get_db)):
    return db.query(Strategy).all()

# ✅ 正確
@router.get("/strategies/")
def get_strategies(service: StrategyService = Depends()):
    return service.get_all_strategies()
```

**嚴重性**: 🚨 Critical
**理由**: 違反四層架構，難以測試和維護

---

### 問題 2：時區錯誤

```python
# ❌ 錯誤（Model）
created_at = Column(DateTime, nullable=False)

# ✅ 正確
created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# ❌ 錯誤（Service）
created_at = datetime.now()

# ✅ 正確
from app.utils.timezone_helpers import now_utc
created_at = now_utc()
```

**嚴重性**: 🚨 Critical
**理由**: 會導致時區混亂，數據不一致

---

### 問題 3：缺少資料庫遷移

```bash
# 檢查
git diff --name-only | grep "models/"
ls -lt backend/alembic/versions/ | head -1

# 如果修改了 models/ 但沒有新遷移
```

**嚴重性**: 🚨 Critical
**修復**:
```bash
docker compose exec backend alembic revision --autogenerate -m "描述變更"
docker compose exec backend alembic upgrade head
```

---

### 問題 4：測試文件位置錯誤

```bash
# ❌ 錯誤位置
/test_my_feature.py
/backend/test_my_feature.py
/backend/scripts/test_my_feature.py

# ✅ 正確位置
/backend/tests/api/test_my_endpoint.py
/backend/tests/services/test_my_service.py
```

**嚴重性**: 🚨 Critical
**理由**: 不符合測試規範，無法被 pytest 正確執行

---

### 問題 5：Celery 任務缺少 expires

```python
# ❌ 高頻任務設置 expires（會立即過期）
@shared_task(expires=300)
def sync_latest_prices():
    pass

# ⚠️ 每日任務缺少 expires
"sync-daily": {
    "task": "app.tasks.sync_daily",
    "schedule": crontab(hour=21, minute=0),
    # 缺少 expires
}

# ✅ 正確
# 高頻任務不設置 expires
@shared_task
def sync_latest_prices():
    pass

# 每日任務設置 expires
"sync-daily": {
    "task": "app.tasks.sync_daily",
    "schedule": crontab(hour=21, minute=0),  # UTC 21:00 = 台北 05:00
    "options": {"expires": 82800},  # 23 hours
}
```

**嚴重性**: 🚨 Critical (高頻任務) / ⚠️ Warning (每日任務)
**理由**: 會導致任務被標記為 revoked，無法執行

---

## 📋 完整檢查流程（5 分鐘）

### 步驟 1：獲取變更（30 秒）

```bash
git status
git diff --name-status
git diff > /tmp/review.diff
```

### 步驟 2：快速掃描（2 分鐘）

依序執行上面的 5 個快速檢查：
1. 架構檢查（30 秒）
2. 時區檢查（30 秒）
3. 資料庫檢查（1 分鐘）
4. 測試位置檢查（10 秒）
5. 安全檢查（30 秒）

### 步驟 3：詳細審查（2 分鐘）

重點審查：
- 修改的 models/ 文件
- 新增的 services/ 文件
- API 端點變更

### 步驟 4：生成報告（30 秒）

按嚴重性分類：
- 🚨 Critical Issues
- ⚠️ Warnings
- 💡 Info
- ✅ 正面評價

---

## 🔗 相關文檔

- [SKILL.md](SKILL.md) - 完整審查指南
- [../../../CLAUDE.md](../../../CLAUDE.md) - 開發規範
- [../../../Document/DATABASE_CHANGE_CHECKLIST.md](../../../Document/DATABASE_CHANGE_CHECKLIST.md)
- [../../../Document/TIMEZONE_COMPLETE_GUIDE.md](../../../Document/TIMEZONE_COMPLETE_GUIDE.md)

---

## 💡 使用技巧

### 1. 只審查變更的部分

```bash
# 只看新增和修改的文件
git diff --name-status | grep -E "^[AM]"
```

### 2. 分類審查

```bash
# 只看 models 變更
git diff backend/app/models/

# 只看 API 變更
git diff backend/app/api/v1/
```

### 3. 快速定位問題

```bash
# 在 diff 中搜尋關鍵字
git diff | grep -A 5 -B 5 "datetime.now()"
```

---

**版本**: 1.0
**最後更新**: 2025-12-27
