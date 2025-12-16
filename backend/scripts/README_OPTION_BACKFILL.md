# 選擇權歷史資料回補指南

## 概述

使用 Shioaji API 回補選擇權歷史資料，自動計算因子並儲存到資料庫。

## 前提條件

1. ✅ Shioaji API 憑證已配置（`.env` 中的 `SHIOAJI_*` 環境變數）
2. ✅ Shioaji 已安裝在容器中
3. ✅ 資料庫已初始化（option_daily_factors 表已建立）

## 使用方式

### 方式 1：回補最近 N 天

```bash
# 回補最近 7 天（預設）
docker compose exec backend python scripts/backfill_option_data.py

# 回補最近 30 天
docker compose exec backend python scripts/backfill_option_data.py --days-back 30

# 回補最近 90 天（建議上限，Shioaji 歷史資料有限制）
docker compose exec backend python scripts/backfill_option_data.py --days-back 90
```

### 方式 2：指定日期範圍

```bash
# 回補 2024年12月整個月
docker compose exec backend python scripts/backfill_option_data.py \
  --start-date 2024-12-01 \
  --end-date 2024-12-31

# 回補特定日期範圍
docker compose exec backend python scripts/backfill_option_data.py \
  --start-date 2025-11-01 \
  --end-date 2025-12-15
```

### 方式 3：指定標的

```bash
# 回補台指選擇權（TX）
docker compose exec backend python scripts/backfill_option_data.py \
  --underlying TX \
  --days-back 30

# 回補小台選擇權（MTX）
docker compose exec backend python scripts/backfill_option_data.py \
  --underlying MTX \
  --days-back 30
```

### 測試模式（Dry Run）

先測試不寫入資料庫，檢查數據是否正確：

```bash
docker compose exec backend python scripts/backfill_option_data.py \
  --days-back 7 \
  --dry-run
```

## 參數說明

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `--underlying` | 標的代碼（TX/MTX） | TX |
| `--start-date` | 開始日期（YYYY-MM-DD） | 7 天前 |
| `--end-date` | 結束日期（YYYY-MM-DD） | 今天 |
| `--days-back` | 回補最近 N 天 | 7 |
| `--dry-run` | 測試模式（不寫入資料庫） | False |

## 工作流程

1. **獲取合約列表**：查詢 Shioaji API 獲取選擇權合約（TXO/MXO）
2. **過濾活躍合約**：只處理在回補日期範圍內尚未到期的合約
3. **獲取歷史價格**：對每個合約使用 `api.kbars()` 獲取當天收盤數據
4. **計算因子**：
   - 階段 1：PCR Volume, PCR OI, ATM IV
   - 階段 3：Greeks 摘要（如果已啟用）
5. **儲存到資料庫**：Upsert 到 `option_daily_factors` 表

## 輸出範例

```
============================================================
[BACKFILL] 🚀 Starting option data backfill for TX
============================================================
[BACKFILL] 📅 Date range: 2025-12-08 to 2025-12-15
[BACKFILL] 📊 Total trading days: 6
[BACKFILL] 🧪 Dry run: False

[BACKFILL] 📅 Processing 2025-12-08 (1/6, 16.7%)
[BACKFILL] Found 250/350 active contracts for TX on 2025-12-08
[BACKFILL] ✅ Fetched 180/250 contracts (72.0%)
[BACKFILL] 💾 Saved factors for 2025-12-08: PCR=0.95, ATM_IV=0.15, Quality=0.85

...

============================================================
[BACKFILL] 🏁 Backfill completed!
============================================================
Days processed: 6/6
Days success: 5
Days failed: 1
Contracts total: 1500
Contracts fetched: 1080
Factors saved: 5
Fetch success rate: 72.0%
Overall success rate: 83.3%
```

## 注意事項

### 1. **Shioaji API 歷史資料限制**

- 通常只提供 **3-6 個月** 的歷史資料
- 如果回補時間過早，API 可能返回空數據
- 建議分批回補，避免一次請求過多數據

### 2. **API 速率限制**

- Shioaji API 有速率限制
- 腳本已自動處理錯誤重試
- 如遇到大量失敗，建議分批執行

### 3. **合約數量**

- TX 選擇權每月約有 **200-300** 個活躍合約
- MTX 選擇權較少，約 **100-200** 個
- 回補 1 天可能需要查詢 200+ 次 API

### 4. **數據品質**

- 部分合約可能沒有交易（成交量為 0）
- 腳本會自動過濾無效數據
- `data_quality_score` 欄位記錄數據品質評分

### 5. **已存在數據**

- 腳本會自動跳過已存在的日期
- 使用 `--dry-run` 測試不會影響現有數據
- 如需覆寫，請先手動刪除資料庫記錄

## 查看回補結果

```bash
# 查詢已回補的日期範圍
docker compose exec postgres psql -U quantlab quantlab -c "
SELECT
    underlying_id,
    MIN(date) as earliest_date,
    MAX(date) as latest_date,
    COUNT(*) as total_days
FROM option_daily_factors
GROUP BY underlying_id
ORDER BY underlying_id;
"

# 查看最新的 10 筆因子數據
docker compose exec postgres psql -U quantlab quantlab -c "
SELECT
    underlying_id,
    date,
    pcr_volume,
    atm_iv,
    data_quality_score
FROM option_daily_factors
ORDER BY date DESC
LIMIT 10;
"

# 查看特定日期的詳細因子
docker compose exec postgres psql -U quantlab quantlab -c "
SELECT * FROM option_daily_factors
WHERE underlying_id = 'TX' AND date = '2025-12-15';
"
```

## 故障排除

### 問題 1：Shioaji 連接失敗

**錯誤**：`Shioaji client not available`

**解決**：
1. 檢查 `.env` 中的 Shioaji API 憑證
2. 確認 Shioaji 已安裝：`docker compose exec backend pip show shioaji`
3. 測試 API 連接：`docker compose exec backend python -c "from app.services.shioaji_client import ShioajiClient; client = ShioajiClient(); print(client.is_available())"`

### 問題 2：所有合約獲取失敗

**錯誤**：`No contracts found for TX on 2025-12-15`

**原因**：
- Shioaji API 可能在非交易時段無法返回數據
- 合約可能在該日期不存在（過早或過晚）

**解決**：
- 確認查詢日期為交易日（非週末/假日）
- 嘗試查詢更近的日期

### 問題 3：資料品質低

**現象**：`data_quality_score < 0.5`

**原因**：
- 成交量低（流動性差的合約）
- 部分合約數據缺失
- 非交易時段查詢

**解決**：正常現象，腳本會自動記錄並繼續處理

## 建議回補策略

### 初次設置

```bash
# 1. 測試回補（確認功能正常）
docker compose exec backend python scripts/backfill_option_data.py \
  --days-back 3 \
  --dry-run

# 2. 回補最近 1 週（真實執行）
docker compose exec backend python scripts/backfill_option_data.py \
  --days-back 7

# 3. 逐步回補 1 個月
docker compose exec backend python scripts/backfill_option_data.py \
  --days-back 30
```

### 定期維護

```bash
# 每週執行一次，填補遺漏的數據
docker compose exec backend python scripts/backfill_option_data.py \
  --days-back 7
```

### 完整回補

```bash
# 回補 Shioaji 支援的最長歷史（約 3-6 個月）
docker compose exec backend python scripts/backfill_option_data.py \
  --days-back 90

# 分批回補（避免超時）
docker compose exec backend python scripts/backfill_option_data.py \
  --start-date 2025-09-01 --end-date 2025-09-30

docker compose exec backend python scripts/backfill_option_data.py \
  --start-date 2025-10-01 --end-date 2025-10-31

docker compose exec backend python scripts/backfill_option_data.py \
  --start-date 2025-11-01 --end-date 2025-11-30

docker compose exec backend python scripts/backfill_option_data.py \
  --start-date 2025-12-01 --end-date 2025-12-15
```

## 相關文件

- [Shioaji API 文檔](https://sinotrade.github.io/)
- [選擇權同步任務](../app/tasks/option_sync.py)
- [選擇權因子計算器](../app/services/option_calculator.py)
- [資料庫 Schema](../../Document/DATABASE_SCHEMA_REPORT.md)
