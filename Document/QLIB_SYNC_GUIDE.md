# Qlib 數據同步指南

完整的 Qlib v2 數據同步操作手冊。

## 目錄

- [概述](#概述)
- [快速開始](#快速開始)
- [智慧同步邏輯](#智慧同步邏輯)
- [同步選項](#同步選項)
- [效能優化](#效能優化)
- [故障排查](#故障排查)

## 概述

### Qlib v2 官方格式

QuantLab 使用 **Qlib v2 官方格式**，將資料庫中的股票歷史數據轉換為 Qlib 二進制格式。

**關鍵特性**：
- **官方格式**：使用 `FileFeatureStorage` API，確保完全兼容
- **目錄結構**：`features/{stock}/` 而非舊的 `instruments/`
- **檔案格式**：`{feature}.day.bin`（如 `close.day.bin`）
- **二進制存儲**：讀取速度比 pandas 快 3-10 倍
- **智慧同步**：自動判斷增量/完整/跳過（節省 95%+ 時間）
- **特徵欄位**：6 個（open, high, low, close, volume, factor）
- **Fallback 機制**：本地數據不存在時自動使用 FinLab API

### 數據路徑

```bash
# 環境變數
QLIB_DATA_PATH=/data/qlib/tw_stock_v2

# Docker volume 掛載
/data/qlib:/data/qlib  # 持久化儲存

# 數據目錄結構
/data/qlib/tw_stock_v2/
├── features/
│   ├── 2330/
│   │   ├── close.day.bin
│   │   ├── open.day.bin
│   │   ├── high.day.bin
│   │   ├── low.day.bin
│   │   ├── volume.day.bin
│   │   └── factor.day.bin
│   ├── 2454/
│   │   └── ...
│   └── ...
├── calendars/
└── instruments/
```

## 快速開始

### 1. 智慧同步（推薦）

```bash
# 自動增量更新，跳過已同步的股票
./scripts/sync-qlib-smart.sh

# 範例輸出
# ⏭️  跳過（已是最新）: 2330 (台積電)
# ➕ 增量同步: 2454 (最後日期: 2024-11-20 → 2024-12-10)
# 📦 完整同步: 1234 (無歷史數據)
```

### 2. 測試模式

```bash
# 僅同步 10 檔股票（測試用）
./scripts/sync-qlib-smart.sh --test
```

### 3. 同步單一股票

```bash
# 同步台積電
./scripts/sync-qlib-smart.sh --stock 2330
```

### 4. 手動執行同步腳本

```bash
# 完整命令
docker compose exec backend python /app/scripts/export_to_qlib_v2.py \
  --output-dir /data/qlib/tw_stock_v2 \
  --stocks all \
  --smart

# 限制處理數量（測試用）
docker compose exec backend python /app/scripts/export_to_qlib_v2.py \
  --output-dir /data/qlib/tw_stock_v2 \
  --stocks all \
  --smart \
  --limit 100

# 強制完整重新同步（不使用智慧模式）
docker compose exec backend python /app/scripts/export_to_qlib_v2.py \
  --output-dir /data/qlib/tw_stock_v2 \
  --stocks all
```

## 智慧同步邏輯

### 同步判斷流程

```
1. 檢查 Qlib 已有數據
   ├─ 無數據 → 📦 完整同步
   ├─ Qlib 最後日期 >= 資料庫 → ⏭️  跳過（已是最新）
   └─ 有新數據 → ➕ 增量同步（只同步新增日期）
```

### 範例場景

**場景 1：首次同步**
```bash
資料庫：2330 (2020-01-01 ~ 2024-12-10)
Qlib：無數據
結果：📦 完整同步（1,234 天）
```

**場景 2：增量同步**
```bash
資料庫：2330 (2020-01-01 ~ 2024-12-10)
Qlib：已有數據至 2024-11-20
結果：➕ 增量同步（2024-11-21 ~ 2024-12-10，20 天）
```

**場景 3：跳過同步**
```bash
資料庫：2330 (2020-01-01 ~ 2024-12-10)
Qlib：已有數據至 2024-12-10
結果：⏭️  跳過（已是最新）
```

## 同步選項

### 指定股票代碼

```bash
# 單一股票
./scripts/sync-qlib-smart.sh --stock 2330

# 多檔股票（修改腳本）
docker compose exec backend python /app/scripts/export_to_qlib_v2.py \
  --output-dir /data/qlib/tw_stock_v2 \
  --stocks 2330,2454,2881 \
  --smart
```

### 同步模式

**智慧模式（預設）**：
```bash
# 使用 --smart 參數
./scripts/sync-qlib-smart.sh
```

**完整重新同步**：
```bash
# 不使用 --smart 參數
docker compose exec backend python /app/scripts/export_to_qlib_v2.py \
  --output-dir /data/qlib/tw_stock_v2 \
  --stocks all
```

### 限制數量

```bash
# 只處理前 100 檔
docker compose exec backend python /app/scripts/export_to_qlib_v2.py \
  --output-dir /data/qlib/tw_stock_v2 \
  --stocks all \
  --smart \
  --limit 100
```

## 效能優化

### 效能對比

| 同步方式 | 股票數 | 平均每檔記錄 | 預估時間 | 節省時間 |
|---------|--------|-------------|---------|---------|
| 首次同步 | 2,671 | 1,000+ 筆 | 2-4 小時 | - |
| 日常增量 | 2,671 | 10 筆新數據 | 2-5 分鐘 | ~95% |
| 已是最新 | 2,671 | 0 筆 | < 30 秒 | ~99% |

### 批次處理建議

**首次同步**：
```bash
# 分批處理，避免一次性載入過多數據
docker compose exec backend python /app/scripts/export_to_qlib_v2.py \
  --output-dir /data/qlib/tw_stock_v2 \
  --stocks all \
  --smart \
  --limit 500

# 完成後再執行下一批
# 重複執行直到所有股票同步完成
```

**日常增量**：
```bash
# 每天收盤後執行一次
./scripts/sync-qlib-smart.sh
```

### 監控同步進度

```bash
# 查看已同步股票數量
ls -1 /data/qlib/tw_stock_v2/features/ | wc -l

# 查看特定股票數據
ls -lh /data/qlib/tw_stock_v2/features/2330/

# 檢查檔案大小
du -sh /data/qlib/tw_stock_v2/
```

## 數據驗證

### 檢查同步結果

```bash
# 測試 Qlib 引擎
docker compose exec backend python scripts/test_qlib_engine.py

# 查看特定股票數據範圍
docker compose exec backend python -c "
from qlib.data import D
import pandas as pd

df = D.features(
    instruments=['2330'],
    fields=['$close', '$volume'],
    start_time='2024-01-01',
    end_time='2024-12-31'
)
print(df.head())
print(df.tail())
print(f'總筆數: {len(df)}')
"
```

### 比對資料庫數據

```bash
# 查詢資料庫中的數據範圍
docker compose exec postgres psql -U quantlab quantlab -c \
  "SELECT stock_id, COUNT(*), MIN(date), MAX(date)
   FROM stock_prices
   WHERE stock_id = '2330'
   GROUP BY stock_id;"

# 比對 Qlib 和資料庫數據一致性
docker compose exec backend python -c "
from qlib.data import D
from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
stock_id = '2330'

# 資料庫數據
result = db.execute(
    text('SELECT COUNT(*), MIN(date), MAX(date) FROM stock_prices WHERE stock_id = :stock_id'),
    {'stock_id': stock_id}
).fetchone()
print(f'資料庫: {result}')

# Qlib 數據
df = D.features(instruments=[stock_id], fields=['$close'])
print(f'Qlib: {len(df)} 筆, {df.index.min()} ~ {df.index.max()}')
"
```

## 故障排查

### 常見問題

#### 1. Qlib 初始化失敗

**症狀**：
```
RuntimeError: Qlib is not initialized
```

**解決方案**：
```bash
# 檢查環境變數
docker compose exec backend env | grep QLIB_DATA_PATH

# 檢查數據目錄是否存在
docker compose exec backend ls -la /data/qlib/tw_stock_v2/

# 確認 Docker volume 掛載
docker compose exec backend mount | grep qlib
```

#### 2. 檔案權限問題

**症狀**：
```
PermissionError: [Errno 13] Permission denied: '/data/qlib/tw_stock_v2/features/2330/close.day.bin'
```

**解決方案**：
```bash
# 修改目錄權限
docker compose exec backend chmod -R 755 /data/qlib/tw_stock_v2/
```

#### 3. 數據不存在

**症狀**：
```
No data found for stock 2330
```

**解決方案**：
```bash
# 1. 檢查資料庫是否有數據
docker compose exec postgres psql -U quantlab quantlab -c \
  "SELECT COUNT(*) FROM stock_prices WHERE stock_id = '2330';"

# 2. 如果資料庫有數據，重新同步
./scripts/sync-qlib-smart.sh --stock 2330

# 3. 檢查 Qlib 檔案
docker compose exec backend ls -la /data/qlib/tw_stock_v2/features/2330/
```

#### 4. 增量同步未生效

**症狀**：每次都執行完整同步

**解決方案**：
```bash
# 確認使用 --smart 參數
cat scripts/sync-qlib-smart.sh

# 檢查 Qlib 檔案最後修改時間
docker compose exec backend stat /data/qlib/tw_stock_v2/features/2330/close.day.bin
```

### 效能問題

#### 同步速度過慢

**原因**：
- 資料庫查詢慢
- 網路延遲（使用 FinLab API Fallback）
- 磁碟 I/O 瓶頸

**解決方案**：
```bash
# 1. 使用增量同步
./scripts/sync-qlib-smart.sh

# 2. 減少處理數量
docker compose exec backend python /app/scripts/export_to_qlib_v2.py \
  --limit 100 --smart

# 3. 檢查資料庫索引
docker compose exec postgres psql -U quantlab quantlab -c \
  "SELECT * FROM pg_indexes WHERE tablename = 'stock_prices';"
```

## Qlib 數據適配器

### Fallback 機制

當 Qlib 本地數據不存在時，系統自動使用 FinLab API：

```python
# app/services/qlib_data_adapter.py
def get_qlib_ohlcv(symbol, start_date, end_date):
    # 1. 優先使用本地 Qlib 數據（快 3-10 倍）
    if self.qlib_initialized and self._check_qlib_data_exists(symbol):
        df = D.features(instruments=[symbol], fields=fields, ...)
        if df is not None:
            return df  # ✅ 使用本地數據

    # 2. Fallback: 從 FinLab API 獲取
    df = self.finlab_client.get_ohlcv(symbol, ...)
    return df  # ⚠️ API 調用（較慢但可靠）
```

### Qlib 表達式範例

```python
from app.services.qlib_data_adapter import QlibDataAdapter

adapter = QlibDataAdapter()

# 獲取 OHLCV 數據
df = adapter.get_qlib_ohlcv('2330', '2024-01-01', '2024-12-31')

# 使用 Qlib 表達式計算技術指標
fields = [
    '$close',                           # 收盤價
    'Mean($close, 5)',                  # 5 日均線
    'Std($close, 20)',                  # 20 日標準差
    '$close / Mean($close, 20)',        # 價格相對均線比率
    '$volume / Mean($volume, 20)',      # 成交量比率
    'Corr($close, $volume, 10)',        # 價量相關性
]
df = adapter.get_qlib_features('2330', '2024-01-01', '2024-12-31', fields=fields)
```

## 定期維護

### 每日維護

```bash
# 收盤後執行增量同步
./scripts/sync-qlib-smart.sh

# 檢查同步狀態
docker compose exec backend python -c "
from qlib.data import D
print('Qlib 引擎狀態: OK')
"
```

### 每月維護

```bash
# 檢查數據目錄大小
du -sh /data/qlib/tw_stock_v2/

# 清理過期快取
docker compose exec backend rm -rf /tmp/qlib_cache/*

# 驗證數據完整性
docker compose exec backend python scripts/test_qlib_engine.py
```

## 腳本版本說明

### 推薦使用

**export_to_qlib_v2.py**：
- ✅ 官方格式
- ✅ 智慧同步
- ✅ 效能優化
- ✅ 主動維護

### 舊版本（保留參考）

**export_to_qlib.py**：
- ⚠️ 自定義格式
- ⚠️ 不兼容 Qlib 新版本
- ⚠️ 不推薦使用

## 相關文檔

- [操作指南](OPERATIONS_GUIDE.md)
- [開發指南](DEVELOPMENT_GUIDE.md)
- [Qlib 官方文檔](https://qlib.readthedocs.io/)
