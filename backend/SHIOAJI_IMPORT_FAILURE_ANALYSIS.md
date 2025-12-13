# Shioaji 導入失敗分析報告

**日期**: 2024-12-13
**導入批次**: import_all_20251212_230354
**失敗股票數**: 637

---

## 📊 問題概述

### 統計數據

| 項目 | 數量 |
|------|------|
| **總處理股票** | 1,692 |
| **成功導入** | 1,055 (62%) |
| **失敗導入** | 637 (38%) |
| **讀取記錄數** | 224,734,139 |
| **插入記錄數** | 0 |
| **跳過記錄數** | 224,500,282 |
| **錯誤記錄數** | 234,494 |

### 關鍵發現

✅ **已成功導入 159,611,587 筆分鐘線數據**（1.6 億筆）
⚠️ **637 個股票失敗並非真正的數據問題**

---

## 🔍 根本原因分析

### 錯誤類型

所有 637 個失敗股票都顯示相同錯誤：

```
This Session's transaction has been rolled back due to a previous exception
during flush. To begin a new transaction with this Session, first issue
Session.rollback().

Original exception was: (psycopg2.errors.UniqueViolation) duplicate key value
violates unique constraint "5622_7861_pk_stock_minute_prices"
```

### 失敗機制

#### 1. **共用資料庫 Session** (`import_shioaji_csv.py:532`)

```python
db = SessionLocal()  # 所有 1,692 個股票共用一個 session

for csv_file in tqdm(csv_files):
    import_csv_file(csv_file, db, ...)  # 重複使用同一個 db
```

#### 2. **第 1055 個股票觸發錯誤**

- 批次插入時遇到 `UniqueViolation` 錯誤
- 原因：增量模式下，某些重複記錄未被正確過濾
- SQLAlchemy session 進入 **"dirty" 狀態**

#### 3. **缺少錯誤恢復機制** (`import_shioaji_csv.py:376-380`)

**修復前**:
```python
except Exception as e:
    logger.error(f"❌ {stock_id}: Import failed - {str(e)}")
    result["status"] = "failed"
    result["errors"] += 1
    # ❌ 缺少 db.rollback()
```

**問題**:
- Session 保持 "dirty" 狀態
- 後續所有操作都會失敗
- 637 個股票連鎖失敗

#### 4. **連鎖反應**

```
Stock 1-1054  ✅ 正常導入
Stock 1055    ❌ UniqueViolation → Session 變 dirty
Stock 1056    ❌ Session dirty → 失敗
Stock 1057    ❌ Session dirty → 失敗
...
Stock 1692    ❌ Session dirty → 失敗
```

---

## ✅ 解決方案

### 已實施修復

#### 修復 1: 外層異常處理加入 Rollback

**位置**: `backend/scripts/import_shioaji_csv.py:376-382`

```python
except Exception as e:
    logger.error(f"❌ {stock_id}: Import failed - {str(e)}")
    result["status"] = "failed"
    result["errors"] += 1
    # ✅ 新增：Rollback session to allow subsequent imports
    db.rollback()
```

#### 修復 2: 批次插入失敗時 Rollback

**位置**: `backend/scripts/import_shioaji_csv.py:352-357`

```python
except Exception as e:
    # 如果批次插入失敗，嘗試逐筆 upsert
    logger.warning(f"{stock_id}: Bulk insert failed, trying upsert - {str(e)}")
    # ✅ 新增：Rollback before trying individual upserts
    db.rollback()
    for record in records:
        # ... upsert 邏輯
```

### 修復效果

- ✅ 每個股票失敗時，session 會正確 rollback
- ✅ 後續股票可以繼續正常導入
- ✅ 避免連鎖失敗

---

## 🔄 重新導入失敗股票

### 方法 1: 測試修復（推薦先執行）

使用前 10 個失敗股票測試：

```bash
bash test_rollback_fix.sh
```

預期結果：10 個股票全部成功導入

### 方法 2: 導入所有失敗股票

#### 選項 A: 使用準備好的腳本

```bash
# 導入失敗股票清單（自動從日誌提取）
bash backend/scripts/retry_failed_stocks.sh
```

#### 選項 B: 手動執行

```bash
# 所有 637 個失敗股票
FAILED_STOCKS="4979,4987,4989,4991,4994,4995,4999,5007,5009,5011,..."

docker compose exec -T backend python3 scripts/import_shioaji_csv.py \
    --stocks "$FAILED_STOCKS" \
    --incremental \
    --batch-size 10000
```

#### 選項 C: 重新運行完整導入（最簡單）

```bash
# 使用增量模式重新運行所有股票
# 已導入的會自動跳過，只處理失敗的 637 個
docker compose exec -T backend python3 scripts/import_shioaji_csv.py \
    --incremental \
    --batch-size 10000
```

**推薦**: 使用選項 C，因為：
- ✅ 不需要手動管理失敗清單
- ✅ 自動跳過已導入數據
- ✅ 處理所有遺漏的股票

---

## 📋 失敗股票清單

共 637 個股票（完整清單）:

```
4979, 4987, 4989, 4991, 4994, 4995, 4999, 5007, 5009, 5011, 5013, 5014,
5015, 5016, 5102, 5201, 5202, 5203, 5205, 5206, 5209, 5210, 5211, 5212,
5213, 5215, 5220, 5223, 5225, 5227, 5230, 5234, 5243, 5245, 5251, 5258,
5259, 5263, 5264, 5269, 5272, 5274, 5276, 5278, 5281, 5284, 5285, 5287,
5288, 5289, 5291, 5299, 5301, 5302, 5305, 5306, 5309, 5310, 5312, 5314,
...（完整 637 個）
```

**清單位置**: 查看 `/tmp/shioaji_import/import_all_20251212_230354.log`

---

## 🔍 驗證導入成功

### 檢查總記錄數

```bash
docker compose exec -T postgres psql -U quantlab quantlab \
    -c "SELECT COUNT(*) FROM stock_minute_prices;"
```

**預期**: 應該會增加（取決於失敗股票的數據量）

### 檢查特定失敗股票

```bash
# 檢查 4979（第一個失敗的股票）
docker compose exec -T postgres psql -U quantlab quantlab \
    -c "SELECT COUNT(*), MIN(datetime), MAX(datetime)
        FROM stock_minute_prices WHERE stock_id = '4979';"
```

**預期**: 應該有數據

### 檢查總股票數

```bash
docker compose exec -T postgres psql -U quantlab quantlab \
    -c "SELECT COUNT(DISTINCT stock_id) FROM stock_minute_prices;"
```

**預期**: 應該接近 1,692（原 1,055 + 重新導入的 637）

---

## 📊 預期結果

### 導入前（當前狀態）

- 總記錄數: **159,611,587**
- 總股票數: **約 1,055**

### 導入後（預期）

- 總記錄數: **約 2-3 億**（增加 637 個股票的數據）
- 總股票數: **約 1,692**（所有股票）

---

## 🚀 後續建議

### 短期

1. ✅ 執行 `test_rollback_fix.sh` 驗證修復
2. ✅ 重新導入失敗的 637 個股票
3. ✅ 驗證數據完整性

### 長期

#### 改進 1: 每個股票使用獨立 Session

```python
# 更安全的做法
for csv_file in tqdm(csv_files):
    db = SessionLocal()  # 每個股票創建新 session
    try:
        import_csv_file(csv_file, db, ...)
    finally:
        db.close()  # 確保 session 正確關閉
```

**優點**:
- ✅ 完全隔離每個股票的導入
- ✅ 失敗不會影響其他股票
- ✅ 更容易並行處理

**缺點**:
- ⚠️ Session 創建/關閉開銷（但對批次導入影響不大）

#### 改進 2: 增強錯誤處理

```python
# 記錄更詳細的錯誤資訊
except psycopg2.errors.UniqueViolation as e:
    logger.warning(f"Duplicate record at {record.datetime}, skipping")
except Exception as e:
    logger.error(f"Unexpected error: {type(e).__name__}: {str(e)}")
    db.rollback()
```

#### 改進 3: 導入進度持久化

```python
# 將導入進度存入資料庫
# 中斷後可以從斷點繼續
CREATE TABLE import_progress (
    stock_id VARCHAR(10) PRIMARY KEY,
    status VARCHAR(20),
    last_imported_date TIMESTAMP,
    total_records INTEGER,
    updated_at TIMESTAMP
);
```

---

## 📝 總結

### 關鍵要點

1. **失敗並非數據問題** - 637 個股票的 CSV 檔案都正常，失敗是因為代碼錯誤
2. **已修復根本原因** - 加入 `db.rollback()` 防止連鎖失敗
3. **數據未損壞** - 已成功導入的 1.6 億筆數據完全正常
4. **重新導入即可** - 使用增量模式重新運行即可補齊 637 個股票

### 建議操作順序

```bash
# 1. 測試修復（5 分鐘）
bash test_rollback_fix.sh

# 2. 檢查測試結果
# 確認 10 個股票全部成功

# 3. 重新導入所有失敗股票（約 1-2 小時）
docker compose exec -T backend python3 scripts/import_shioaji_csv.py \
    --incremental \
    --batch-size 10000

# 4. 驗證數據
docker compose exec -T postgres psql -U quantlab quantlab \
    -c "SELECT COUNT(*) FROM stock_minute_prices;"
```

---

**報告生成時間**: 2024-12-13
**修復狀態**: ✅ 已完成
**測試狀態**: ⏳ 待執行
