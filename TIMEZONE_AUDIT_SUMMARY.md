# 時區遷移審查摘要

**審查日期**: 2025-12-20
**總體評估**: 🟡 良好 (85/100) - 基礎良好，需修復部分遺漏項目

---

## 📊 快速概覽

| 類別 | 狀態 | 問題數 | 優先級 |
|------|------|--------|--------|
| 資料庫 Models | 🟢 優秀 | 1 個模型缺少時區標記 | P0 |
| Python 代碼 | 🟡 良好 | 44 處使用 `datetime.now()` | P0 |
| API Schemas | 🔴 需改進 | 16 個 schema 缺少 `json_encoders` | P1 |
| 前端時區轉換 | 🟡 良好 | 12 個頁面未統一 | P1 |
| Celery 配置 | 🟢 完美 | 0 | - |
| 文檔 | 🟢 完整 | 0 | - |

---

## 🔥 高優先級問題 (P0) - 立即修復

### 1. institutional_investor.py 缺少時區標記

**檔案**: `backend/app/models/institutional_investor.py` (第 39-40 行)

**問題**:
```python
created_at = Column(DateTime, ...)  # ❌ 缺少 timezone=True
```

**修復**:
```python
created_at = Column(DateTime(timezone=True), ...)  # ✅
```

**影響**: 資料庫欄位為 `TIMESTAMP WITHOUT TIME ZONE`，可能導致時區錯誤
**工作量**: 1 小時 (修改模型 + 創建遷移)

---

### 2. 44 處使用 datetime.now() 未設置時區

**位置**: 分散在 20+ 個文件中

**主要問題檔案**:
- `app/tasks/institutional_investor_sync.py` (6 處)
- `app/tasks/fundamental_sync.py` (2 處)
- `app/tasks/stock_data.py` (4 處)
- `app/services/*.py` (15+ 處)

**問題**:
```python
datetime.now() - timedelta(days=7)  # ❌ 使用台灣時間
```

**修復**:
```python
datetime.now(timezone.utc) - timedelta(days=7)  # ✅ 使用 UTC
```

**影響**: 跨日期邊界時可能產生 **off-by-one 錯誤**
**工作量**: 2-3 小時 (可使用自動化腳本)

---

### 3. 5 處使用已棄用的 datetime.utcnow()

**檔案**: `app/tasks/factor_evaluation_tasks.py`

**問題**:
```python
datetime.utcnow()  # ❌ 已棄用，返回 naive datetime
```

**修復**:
```python
datetime.now(timezone.utc)  # ✅
```

**影響**: Python 3.12+ 警告，未來版本將移除
**工作量**: 30 分鐘

---

## 📋 中優先級問題 (P1) - 近期修復

### 4. API Schemas 缺少統一 json_encoders

**現況**: 僅 1/17 個 schema 設置 `json_encoders`

**影響**: API 響應可能缺少時區標記 (`+00:00`)

**建議**: 創建 `TimezoneAwareSchema` 基類

**工作量**: 2-3 小時

---

### 5. 前端 12 個頁面未統一時區轉換

**問題**: 直接使用 `toLocaleString` 而非 `formatToTaiwanTime`

**頁面清單**:
- `pages/account/profile.vue`
- `pages/strategies/[id]/index.vue`
- `pages/account/telegram.vue`
- 其他 9 個頁面

**影響**: 時間格式不一致，維護成本高

**工作量**: 3-4 小時

---

## ✅ 已正確實施的部分

- ✅ 28 個模型的 DateTime 欄位正確設置 `timezone=True`
- ✅ Celery 配置使用 UTC (`timezone='UTC', enable_utc=True`)
- ✅ 所有 Crontab 時間已調整為 UTC
- ✅ 創建 `timezone_helpers.py` 處理 `stock_minute_prices` 例外
- ✅ 創建 `useDateTime.ts` 統一前端時區轉換
- ✅ 完整的時區策略文檔

---

## 🛠️  修復工具

我們已準備以下自動化工具:

### 1. 後端修復腳本
```bash
# 預覽修改
python scripts/fix_datetime_timezone.py --dry-run

# 執行修復
python scripts/fix_datetime_timezone.py
```

### 2. 前端檢查腳本
```bash
bash scripts/check_frontend_timezone.sh
```

---

## 📝 修復步驟 (快速指南)

### 第一階段 (1-2 小時)

```bash
# 1. 創建修復分支
git checkout -b fix/timezone-consistency

# 2. 修復 institutional_investor.py
# 編輯 backend/app/models/institutional_investor.py
# 將 DateTime 改為 DateTime(timezone=True)

# 3. 創建資料庫遷移
docker compose exec backend alembic revision --autogenerate -m "fix institutional_investor timezone"
docker compose exec backend alembic upgrade head

# 4. 批量修復 datetime.now()
python scripts/fix_datetime_timezone.py

# 5. 檢查變更
git diff
```

### 第二階段 (2-3 小時)

```bash
# 6. 創建 TimezoneAwareSchema 基類
# 新建 backend/app/schemas/base.py
# 修改其他 schemas 繼承此基類

# 7. 統一前端時區轉換
bash scripts/check_frontend_timezone.sh
# 根據輸出逐頁修改

# 8. 執行測試
docker compose exec backend pytest
docker compose exec frontend npm run lint
```

### 第三階段 (1 小時)

```bash
# 9. 提交變更
git add .
git commit -m "fix: 統一時區處理"

# 10. 部署
git checkout master
git merge fix/timezone-consistency
docker compose restart
docker compose exec redis redis-cli FLUSHDB
```

---

## 🎯 預期效果

修復完成後:

### 後端
- ✅ 所有 DateTime 欄位使用 `TIMESTAMPTZ`
- ✅ 所有時間計算使用 `datetime.now(timezone.utc)`
- ✅ API 響應包含時區標記 (`+00:00`)

### 前端
- ✅ 統一使用 `formatToTaiwanTime()` 顯示時間
- ✅ 時間格式一致
- ✅ 正確處理跨日期邊界

### 資料庫
- ✅ 所有時間戳為 UTC
- ✅ 時區資訊完整保存

---

## 📚 詳細文檔

- **完整審查報告**: [TIMEZONE_MIGRATION_AUDIT_REPORT.md](TIMEZONE_MIGRATION_AUDIT_REPORT.md)
- **修復操作指南**: [TIMEZONE_FIX_GUIDE.md](TIMEZONE_FIX_GUIDE.md)
- **時區策略文檔**: [TIMEZONE_STRATEGY.md](TIMEZONE_STRATEGY.md)

---

## ⚠️  注意事項

1. **備份資料庫**: 修改前務必備份
2. **選擇維護時間**: 建議在非交易時段執行
3. **測試完整性**: 修復後執行完整測試
4. **清空 Redis**: 清除舊的 `task_history` 記錄

---

**制定日期**: 2025-12-20
**預估修復時間**: 6-8 小時
**建議完成時間**: 2025-12-21 (週末)
