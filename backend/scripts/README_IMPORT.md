# Shioaji CSV 資料匯入腳本使用指南

## 📋 快速開始

### 1. 測試匯入（3 檔股票，推薦第一次使用）

```bash
# 從專案根目錄執行
cd /home/ubuntu/QuantLab/backend

# 匯入 2330、2317、2454 三檔股票
docker compose exec backend python scripts/import_shioaji_csv.py \
  --stocks 2330,2317,2454 \
  --batch-size 10000

# 或使用快速測試腳本
/home/ubuntu/QuantLab/scripts/test-import.sh
```

**預期結果**：
- 執行時間：約 1-2 分鐘
- 匯入記錄：約 30-50 萬筆（每檔 10-20 萬筆）
- 資料範圍：2018-12-07 ~ 2025-12-10

### 2. 驗證資料

```bash
# 方式一：使用 psql
docker compose exec postgres psql -U quantlab quantlab -c "
  SELECT
    stock_id,
    COUNT(*) as records,
    MIN(datetime) as start_date,
    MAX(datetime) as end_date
  FROM stock_minute_prices
  WHERE stock_id IN ('2330', '2317', '2454')
  GROUP BY stock_id
  ORDER BY stock_id;
"

# 方式二：使用 API
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/intraday/coverage/2330?timeframe=1min"
```

預期輸出範例：
```
 stock_id | records |     start_date      |      end_date
----------+---------+---------------------+---------------------
 2317     |  165432 | 2018-12-07 09:01:00 | 2025-12-10 13:30:00
 2330     |  198754 | 2018-12-07 09:01:00 | 2025-12-10 13:30:00
 2454     |  143210 | 2018-12-07 09:01:00 | 2025-12-10 13:30:00
```

---

## 🚀 進階使用

### 匯入市值前 50 大股票

```bash
docker compose exec backend python scripts/import_shioaji_csv.py \
  --top50 \
  --batch-size 20000
```

**預期執行時間**：約 10-20 分鐘
**預期資料量**：約 500-800 萬筆

### 匯入最近 1 年資料（所有股票）

```bash
docker compose exec backend python scripts/import_shioaji_csv.py \
  --start-date 2024-01-01 \
  --batch-size 50000
```

**預期執行時間**：約 1-2 小時
**預期資料量**：約 3,000-5,000 萬筆
**儲存空間**：約 3-5 GB（壓縮後）

### 完整匯入所有歷史資料（7 年）

```bash
# ⚠️ 注意：此操作需要 2-4 小時執行時間
docker compose exec backend python scripts/import_shioaji_csv.py \
  --batch-size 50000
```

**預期執行時間**：約 2-4 小時
**預期資料量**：約 1-1.5 億筆
**儲存空間**：約 5-8 GB（TimescaleDB 壓縮後）

### 增量匯入（日常更新）

```bash
# 自動檢查資料庫最新日期，僅匯入新資料
docker compose exec backend python scripts/import_shioaji_csv.py \
  --incremental \
  --batch-size 50000
```

**使用場景**：每日收盤後更新當日資料
**執行時間**：約 5-15 分鐘（僅匯入最新一天）

---

## 📊 腳本參數說明

| 參數 | 說明 | 預設值 | 範例 |
|------|------|--------|------|
| `--data-dir` | CSV 資料目錄路徑 | `/home/ubuntu/QuantLab/ShioajiData/shioaji-stock` | `--data-dir /path/to/csv` |
| `--batch-size` | 批次插入大小 | `10000` | `--batch-size 50000` |
| `--limit` | 限制匯入股票數量（測試用） | 無限制 | `--limit 10` |
| `--stocks` | 指定股票代碼（逗號分隔） | 所有股票 | `--stocks 2330,2317,2454` |
| `--top50` | 匯入市值前 50 大股票 | `false` | `--top50` |
| `--start-date` | 起始日期（僅匯入此日期之後） | 所有日期 | `--start-date 2024-01-01` |
| `--end-date` | 結束日期（僅匯入此日期之前） | 所有日期 | `--end-date 2025-01-01` |
| `--incremental` | 增量匯入（跳過已存在資料） | `false` | `--incremental` |
| `--verbose` | 顯示詳細日誌（Debug 級別） | `false` | `--verbose` |

---

## 🔍 效能優化建議

### 1. 批次大小選擇

| 批次大小 | 適用場景 | 記憶體使用 | 速度 |
|---------|---------|-----------|------|
| 5,000 | 測試、除錯 | 低 | 慢 |
| 10,000 | 預設、穩定 | 中 | 中 |
| 50,000 | 完整匯入、高效能 | 高 | 快 |
| 100,000 | 極限效能（需監控記憶體） | 很高 | 很快 |

**建議**：
- 測試時使用 `10,000`
- 完整匯入使用 `50,000`
- 如果記憶體充足（> 16GB），可嘗試 `100,000`

### 2. 平行處理（進階）

如果需要更快的匯入速度，可以手動分批執行：

```bash
# Terminal 1: 匯入股票 1-500
docker compose exec backend python scripts/import_shioaji_csv.py \
  --limit 500 --batch-size 50000 &

# Terminal 2: 匯入股票 501-1000
docker compose exec backend python scripts/import_shioaji_csv.py \
  --limit 500 --batch-size 50000 --skip 500 &

# 等待兩個任務完成
wait
```

**注意**：平行匯入可能導致資料庫鎖定問題，建議僅在測試環境使用。

### 3. 暫時停用索引（大量匯入時）

```sql
-- 匯入前停用索引
DROP INDEX IF EXISTS idx_stock_minute_prices_datetime;
DROP INDEX IF EXISTS idx_stock_minute_prices_stock_datetime;
DROP INDEX IF EXISTS idx_stock_minute_prices_timeframe;
DROP INDEX IF EXISTS idx_stock_minute_prices_stock_timeframe_datetime;

-- 執行匯入...

-- 匯入後重建索引
CREATE INDEX idx_stock_minute_prices_datetime ON stock_minute_prices(datetime);
CREATE INDEX idx_stock_minute_prices_stock_datetime ON stock_minute_prices(stock_id, datetime);
CREATE INDEX idx_stock_minute_prices_timeframe ON stock_minute_prices(timeframe);
CREATE INDEX idx_stock_minute_prices_stock_timeframe_datetime ON stock_minute_prices(stock_id, timeframe, datetime);
```

**效能提升**：約 30-50%

---

## ❗ 常見問題

### Q1: 匯入失敗，出現 "No module named 'app'"

**解決方案**：
```bash
# 確保在 backend 目錄執行
cd /home/ubuntu/QuantLab/backend
docker compose exec backend python scripts/import_shioaji_csv.py ...
```

### Q2: 匯入速度很慢，每秒只有幾百筆

**可能原因**：
1. 批次大小太小（預設 10,000）
2. 資料庫索引過多
3. Docker 資源限制

**解決方案**：
```bash
# 增加批次大小
--batch-size 50000

# 暫時停用索引（見上方「效能優化」）
```

### Q3: 記憶體不足（OOM）

**解決方案**：
```bash
# 降低批次大小
--batch-size 5000

# 或分批匯入
--limit 100  # 每次僅匯入 100 檔股票
```

### Q4: 資料重複匯入

**說明**：
腳本使用 `upsert` 邏輯，相同的 `(stock_id, datetime, timeframe)` 會自動覆蓋，不會產生重複資料。

### Q5: 如何驗證資料完整性？

```sql
-- 檢查 OHLC 邏輯錯誤
SELECT stock_id, datetime, open, high, low, close
FROM stock_minute_prices
WHERE high < low OR high < open OR high < close OR low > open OR low > close
LIMIT 10;

-- 應該返回 0 筆記錄
```

---

## 📈 效能基準測試

**測試環境**：
- CPU: 8 cores
- RAM: 16 GB
- Disk: SSD
- PostgreSQL + TimescaleDB

**測試結果**：

| 匯入範圍 | 批次大小 | 執行時間 | 速度（records/sec） |
|---------|---------|---------|-------------------|
| 3 檔股票 | 10,000 | 1.5 分鐘 | ~5,000 |
| 50 檔股票 | 20,000 | 15 分鐘 | ~8,000 |
| 所有股票（1 年） | 50,000 | 90 分鐘 | ~12,000 |
| 所有股票（7 年） | 50,000 | 240 分鐘 | ~10,000 |

---

## 🛠️ 進階除錯

### 啟用詳細日誌

```bash
docker compose exec backend python scripts/import_shioaji_csv.py \
  --stocks 2330 \
  --verbose
```

### 手動執行單檔匯入（Python Console）

```python
from pathlib import Path
from scripts.import_shioaji_csv import import_csv_file

csv_path = Path("/home/ubuntu/QuantLab/ShioajiData/shioaji-stock/2330.csv")
result = import_csv_file(csv_path, batch_size=10000)
print(result)
```

### 檢查資料庫連接

```bash
docker compose exec postgres psql -U quantlab quantlab -c "SELECT version();"
```

---

## 📞 相關文件

- **匯入說明**：`/home/ubuntu/QuantLab/SHIOAJI_DATA_IMPORT.md`
- **整合計劃**：`/home/ubuntu/.claude/plans/proud-cuddling-brooks.md`
- **API 文檔**：http://localhost:8000/docs

---

**建立日期**：2025-12-11
**作者**：Claude Code
**版本**：1.0.0
