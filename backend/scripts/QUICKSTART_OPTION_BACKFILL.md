# 選擇權回補快速開始

## ⚠️ 重要提醒

1. **執行時間長**：回補 1 天約需 **10-30 分鐘**（取決於合約數量）
2. **API 速率限制**：已自動添加延遲控制，但仍建議小批次執行
3. **最佳執行時間**：建議在**非交易時段**執行（18:00-08:00）

## 🚀 最簡單的使用方式

### 方案 1：回補最近 3 天（推薦新手）

```bash
# 先測試（不寫入資料庫）
docker compose exec backend python scripts/backfill_option_data.py --days-back 3 --dry-run

# 確認無誤後真實執行
docker compose exec backend python scripts/backfill_option_data.py --days-back 3
```

**預計時間**：30-90 分鐘
**數據量**：~600-900 個合約 × 3 天 = 約 2000 次 API 查詢

### 方案 2：每天增量回補（推薦日常維護）

```bash
# 每天執行一次，只回補昨天的數據
docker compose exec backend python scripts/backfill_option_data.py --days-back 1
```

**預計時間**：10-30 分鐘
**數據量**：~300 個合約 × 1 天

### 方案 3：回補特定日期（精確控制）

```bash
# 回補單一日期
docker compose exec backend python scripts/backfill_option_data.py \
  --start-date 2025-12-12 \
  --end-date 2025-12-12
```

## 🔍 執行中如何監控

### 方式 1：查看即時日誌

```bash
# 在另一個終端窗口執行
docker compose logs backend -f | grep "\[BACKFILL\]"
```

### 方式 2：檢查資料庫進度

```bash
# 查看已回補的最新日期
docker compose exec postgres psql -U quantlab quantlab -c "
SELECT underlying_id, MAX(date) as latest_date, COUNT(*) as total_days
FROM option_daily_factors
GROUP BY underlying_id;
"
```

## ⚡ 執行優化建議

### 1. 分批回補（避免超時）

```bash
# 不建議：一次回補 30 天（可能需要 5-10 小時）
docker compose exec backend python scripts/backfill_option_data.py --days-back 30

# 建議：分 3 次執行，每次 10 天
docker compose exec backend python scripts/backfill_option_data.py \
  --start-date 2025-11-01 --end-date 2025-11-10

docker compose exec backend python scripts/backfill_option_data.py \
  --start-date 2025-11-11 --end-date 2025-11-20

docker compose exec backend python scripts/backfill_option_data.py \
  --start-date 2025-11-21 --end-date 2025-11-30
```

### 2. 使用背景執行（長時間任務）

```bash
# 使用 nohup 在背景執行
nohup docker compose exec backend python scripts/backfill_option_data.py \
  --days-back 10 > /tmp/backfill.log 2>&1 &

# 查看進度
tail -f /tmp/backfill.log | grep "\[BACKFILL\]"
```

### 3. 設定 Cron 定時任務

```bash
# 每天凌晨 2:00 自動回補昨天的數據
# 編輯 crontab
crontab -e

# 添加以下行
0 2 * * * cd /home/ubuntu/QuantLab && docker compose exec -T backend python scripts/backfill_option_data.py --days-back 1 >> /tmp/option_backfill_cron.log 2>&1
```

## 🐛 常見問題解決

### 問題 1：`Not ready` 錯誤

**錯誤訊息**：`[E] [thread XXX] Not ready`

**原因**：
- API 速率限制（查詢太快）
- Shioaji 伺服器忙碌

**解決**：
1. 腳本已自動添加延遲（每 50 個合約暫停 2 秒）
2. 如仍頻繁出現，建議縮小批次大小
3. 避開交易時段執行（白天 API 負載較高）

### 問題 2：大量合約查詢失敗

**現象**：`Success rate < 50%`

**可能原因**：
- 查詢的日期太舊（超過 Shioaji 歷史資料範圍）
- 非交易日（週末/假日）
- 合約在該日期尚未上市

**解決**：
- 只回補最近 3-6 個月的數據
- 確認查詢的是交易日

### 問題 3：執行時間過長

**優化方案**：
1. 減少 `--days-back` 天數
2. 分多次執行，每次 3-5 天
3. 使用背景執行 + nohup

### 問題 4：查詢歷史資料返回空

**錯誤**：`No data fetched for 2025-XX-XX`

**原因**：
- Shioaji 歷史資料限制（通常只有 3-6 個月）
- 該日期為非交易日
- 非交易時段查詢可能不穩定

**解決**：
- 只回補最近 90 天內的數據
- 確認日期為交易日（使用 `--days-back` 會自動跳過週末）

## 📊 查看回補結果

### 1. 檢查數據範圍

```sql
SELECT
    underlying_id,
    MIN(date) as earliest_date,
    MAX(date) as latest_date,
    COUNT(*) as total_days
FROM option_daily_factors
GROUP BY underlying_id;
```

### 2. 查看最新數據品質

```sql
SELECT
    date,
    pcr_volume,
    atm_iv,
    data_quality_score
FROM option_daily_factors
WHERE underlying_id = 'TX'
ORDER BY date DESC
LIMIT 10;
```

### 3. 檢查數據完整性

```sql
-- 查看哪些日期缺少數據
SELECT date_series::date
FROM generate_series(
    (SELECT MIN(date) FROM option_daily_factors WHERE underlying_id = 'TX'),
    (SELECT MAX(date) FROM option_daily_factors WHERE underlying_id = 'TX'),
    '1 day'::interval
) AS date_series
WHERE date_series::date NOT IN (
    SELECT date FROM option_daily_factors WHERE underlying_id = 'TX'
)
AND EXTRACT(dow FROM date_series) NOT IN (0, 6)  -- 排除週末
ORDER BY date_series;
```

## 💡 最佳實踐

### 初次設置建議流程

```bash
# 第 1 天：測試回補（確認功能正常）
docker compose exec backend python scripts/backfill_option_data.py \
  --days-back 1 --dry-run

# 第 2 天：回補最近 1 週
docker compose exec backend python scripts/backfill_option_data.py \
  --days-back 7

# 第 3 天：逐步擴展到 1 個月
docker compose exec backend python scripts/backfill_option_data.py \
  --days-back 30

# 之後：設定每日自動回補
# 使用 cron 每天凌晨自動執行
```

### 性能參考

| 回補範圍 | 合約數量 | API 查詢次數 | 預計時間 | 建議執行時段 |
|---------|---------|------------|---------|------------|
| 1 天 | ~300 | ~300 | 10-30 分鐘 | 任何時段 |
| 3 天 | ~900 | ~900 | 30-90 分鐘 | 非交易時段 |
| 7 天 | ~2100 | ~2100 | 1-3 小時 | 夜間/清晨 |
| 30 天 | ~9000 | ~9000 | 5-10 小時 | 背景執行 |

## 🔧 進階配置

### 調整速率限制參數

如果您的 Shioaji API 配額較高，可以修改腳本中的參數：

```python
# 在 scripts/backfill_option_data.py 第 280-282 行
batch_size = 50        # 增加到 100（更快，但可能觸發限制）
batch_delay = 2.0      # 減少到 1.0（更快）
request_delay = 0.1    # 減少到 0.05（更快）
```

**⚠️ 警告**：修改這些參數可能導致更多 API 錯誤

## 📞 需要幫助？

- 詳細文檔：`/home/ubuntu/QuantLab/backend/scripts/README_OPTION_BACKFILL.md`
- 檢查日誌：`docker compose logs backend -f | grep "\[BACKFILL\]"`
- 測試連接：確認 Shioaji API 可用（參考上方測試命令）

---

**提示**：首次使用建議從 **1-3 天** 開始測試，確認功能正常後再擴大範圍。
