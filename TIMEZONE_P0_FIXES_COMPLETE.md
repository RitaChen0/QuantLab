# P0 Critical Issues 修復完成報告

## ✅ 執行時間
- 開始：2025-12-20 15:02
- 完成：2025-12-20 15:08
- 總時長：6 分鐘

## 📋 修復項目

### 1. ✅ institutional_investors 表時區修復

**問題**：使用 `DateTime` 而非 `DateTime(timezone=True)`，導致存儲為 TIMESTAMP (無時區)

**修復步驟**：
1. 修改 `/home/ubuntu/QuantLab/backend/app/models/institutional_investor.py`
   - `created_at`: `DateTime` → `DateTime(timezone=True)`
   - `updated_at`: `DateTime` → `DateTime(timezone=True)`

2. 創建遷移：`7d52b94302f9_fix_institutional_investors_timezone.py`
   ```sql
   ALTER TABLE institutional_investors
   ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
   USING created_at AT TIME ZONE 'UTC';

   ALTER TABLE institutional_investors
   ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
   USING updated_at AT TIME ZONE 'UTC';
   ```

3. 執行遷移：`alembic upgrade head`

**驗證結果**：
```
column_name | data_type                | column_default
created_at  | timestamp with time zone | CURRENT_TIMESTAMP
updated_at  | timestamp with time zone | CURRENT_TIMESTAMP
```

### 2. ✅ Option 表時區修復

**問題**：3 個 Option 相關表使用 `TIMESTAMP` 和 `text('CURRENT_TIMESTAMP')`

**受影響的表和欄位**：
- `option_contracts`: created_at, updated_at
- `option_daily_factors`: created_at
- `option_sync_config`: updated_at

**修復步驟**：
1. 修改 `/home/ubuntu/QuantLab/backend/app/models/option.py`
   - 新增 imports: `DateTime`, `func`
   - OptionContract:
     - `created_at`: `TIMESTAMP` → `DateTime(timezone=True)`, `text('CURRENT_TIMESTAMP')` → `func.now()`
     - `updated_at`: `TIMESTAMP` → `DateTime(timezone=True)`, `text('CURRENT_TIMESTAMP')` → `func.now()`, 新增 `onupdate=func.now()`
   - OptionDailyFactor:
     - `created_at`: `TIMESTAMP` → `DateTime(timezone=True)`, `text('CURRENT_TIMESTAMP')` → `func.now()`
   - OptionSyncConfig:
     - `updated_at`: `TIMESTAMP` → `DateTime(timezone=True)`, `text('CURRENT_TIMESTAMP')` → `func.now()`, 新增 `onupdate=func.now()`

2. 創建遷移：`963973af160f_fix_option_tables_timezone.py`
   ```sql
   -- option_contracts 表
   ALTER TABLE option_contracts
   ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
   USING created_at AT TIME ZONE 'UTC';

   ALTER TABLE option_contracts
   ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
   USING updated_at AT TIME ZONE 'UTC';

   -- option_daily_factors 表
   ALTER TABLE option_daily_factors
   ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
   USING created_at AT TIME ZONE 'UTC';

   -- option_sync_config 表
   ALTER TABLE option_sync_config
   ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
   USING updated_at AT TIME ZONE 'UTC';
   ```

3. 執行遷移：`alembic upgrade head`

**驗證結果**：
```
table_name           | column_name | data_type
option_contracts     | created_at  | timestamp with time zone
option_contracts     | updated_at  | timestamp with time zone
option_daily_factors | created_at  | timestamp with time zone
option_sync_config   | updated_at  | timestamp with time zone
```

### 3. ✅ Redis task_history 清理

**問題**：Redis `task_history:<user_id>` 可能包含舊的台灣時區數據

**修復步驟**：
1. 檢查 Redis keys：
   ```bash
   docker compose exec -T redis redis-cli --scan --pattern "task_history:*"
   ```
   發現 1 個 key (已是 UTC 格式，但仍清理以確保)

2. 清空所有 task_history keys：
   ```bash
   docker compose exec -T redis redis-cli --scan --pattern "task_history:*" | \
     xargs -r docker compose exec -T redis redis-cli DEL
   ```

3. 重啟服務：
   ```bash
   docker compose restart backend celery-worker celery-beat
   ```

**驗證結果**：
```
task_history 鍵數量: 0
✅ Redis task_history 已清空
```

**服務狀態**：
```
quantlab-backend         Up 7 minutes (healthy)
quantlab-celery-beat     Up 7 minutes
quantlab-celery-worker   Up 7 minutes
```

## 🔧 技術細節

### 為何使用 DateTime(timezone=True)？

**Before (錯誤)**：
```python
created_at = Column(DateTime, server_default=func.now(), nullable=False)
# 或
created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'), nullable=False)
```

**After (正確)**：
```python
created_at = Column(
    DateTime(timezone=True),
    server_default=func.now(),
    onupdate=func.now(),  # 僅 updated_at 需要
    nullable=False
)
```

**關鍵差異**：
- `DateTime` → PostgreSQL `TIMESTAMP` (無時區)
- `DateTime(timezone=True)` → PostgreSQL `TIMESTAMPTZ` (有時區)
- `text('CURRENT_TIMESTAMP')` → 字符串 SQL，不跟隨 SQLAlchemy 慣例
- `func.now()` → SQLAlchemy 函數，更安全且可移植

### 為何使用 USING 子句？

```sql
ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
USING created_at AT TIME ZONE 'UTC';
```

**作用**：
1. 將現有 naive datetime 解釋為 UTC
2. 轉換為 TIMESTAMPTZ 格式
3. 保留原有數據（不丟失）

**不使用 USING 的後果**：
- PostgreSQL 可能拒絕轉換（類型不兼容）
- 或解釋為本地時區（錯誤）

## 📊 影響範圍

### 資料庫變更
- **institutional_investors** 表：2 個欄位 (created_at, updated_at)
- **option_contracts** 表：2 個欄位 (created_at, updated_at)
- **option_daily_factors** 表：1 個欄位 (created_at)
- **option_sync_config** 表：1 個欄位 (updated_at)

**總計**：4 個表，6 個欄位

### 程式碼變更
- **institutional_investor.py**: 2 行修改
- **option.py**: 5 行 imports + 4 個 Column 定義修改

### 遷移檔案
- `7d52b94302f9_fix_institutional_investors_timezone.py`
- `963973af160f_fix_option_tables_timezone.py`

## 🎯 驗證結果

### Alembic 遷移狀態
```
Current revision: 963973af160f (head)
```

### 服務健康檢查
- ✅ backend: Up 7 minutes (healthy)
- ✅ celery-worker: Up 7 minutes
- ✅ celery-beat: Up 7 minutes

### Redis 狀態
- ✅ task_history 鍵數量: 0

## 🚨 後續建議

### 1. 監控新數據
觀察新插入的數據是否正確使用 UTC 時區：

```sql
-- 檢查 institutional_investors
SELECT stock_id, date, created_at, updated_at
FROM institutional_investors
ORDER BY created_at DESC
LIMIT 5;

-- 檢查 option_contracts
SELECT contract_id, created_at, updated_at
FROM option_contracts
ORDER BY created_at DESC
LIMIT 5;
```

### 2. 驗證 task_history
等待 Celery 定時任務執行後，檢查新的 task_history 是否使用 UTC：

```bash
docker compose exec -T redis redis-cli GET "task_history:app.tasks.cleanup_old_cache"
```

預期輸出應包含：`"+00:00"` 或 `"Z"` 時區標記

### 3. 檢查日誌
監控服務日誌，確認無時區相關錯誤：

```bash
docker compose logs -f backend | grep -i timezone
docker compose logs -f celery-worker | grep -i timezone
```

## 📝 剩餘工作

根據 [TIMEZONE_SECURITY_AUDIT_REPORT.md](TIMEZONE_SECURITY_AUDIT_REPORT.md)，剩餘以下項目：

### 🟡 Warning (P1-P2)
1. **W1**: `.date()` 轉換未指定時區
2. **W2**: Shioaji API 時區對齊
3. **W3**: API 日期參數時區處理
4. **W4**: 前端日期選擇器時區
5. **W5**: text('CURRENT_TIMESTAMP') vs func.now()

### 🟢 Info (P3)
6. **I1**: 文檔更新
7. **I2**: 時區測試擴展

**建議處理順序**：
1. 先完成 W5 (text → func.now())，影響範圍小
2. 再處理 W1 (`.date()` 轉換)，需要代碼審查
3. 最後處理 W2-W4 (API 和前端)，需要測試驗證

## 🎉 總結

**P0 Critical Issues 修復完成！**

- ✅ 4 個資料表的時區欄位已修復為 TIMESTAMPTZ
- ✅ 2 個 Alembic 遷移已成功執行
- ✅ Redis task_history 已清空
- ✅ 所有服務已重啟並正常運行

**時區一致性保證**：
- 後端：統一使用 UTC (datetime.now(timezone.utc))
- 資料庫：使用 TIMESTAMPTZ 儲存
- 前端：顯示時自動轉換為台灣時間 (useDateTime composable)

---

**文檔版本**：2025-12-20
**執行者**：Claude Code
**下一步**：處理 Warning 級別的時區問題 (W1-W5)
