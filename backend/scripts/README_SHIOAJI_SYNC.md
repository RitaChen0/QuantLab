# Shioaji → Qlib 同步工具

> 獨立的數據同步工具，專門在收盤後截取 Shioaji 1 分鐘 K 線並自動存入 Qlib + PostgreSQL

## 🎯 核心功能

1. **從 Shioaji API 獲取數據** - 1 分鐘 K 線（OHLCV）
2. **雙軌存儲** - 同時寫入 PostgreSQL 和 Qlib 二進制格式
3. **智慧去重** - 自動檢查避免重複插入
4. **定時任務友好** - 可配置為 Cron Job
5. **完整日誌** - 詳細記錄同步過程

## 📁 文件結構

```
backend/scripts/
├── sync_shioaji_to_qlib.py       # 主同步工具（Python）
└── README_SHIOAJI_SYNC.md        # 本文件

scripts/
├── sync-shioaji-today.sh         # Shell 包裝腳本（推薦使用）
└── test-shioaji-sync.sh          # 測試腳本

Document/
└── SHIOAJI_SYNC_GUIDE.md         # 完整使用指南（70+ 頁）
```

## 🚀 快速開始

### 1. 測試工具是否正常

```bash
# 執行測試（同步 2330, 2317 昨天的數據）
bash /home/ubuntu/QuantLab/scripts/test-shioaji-sync.sh
```

### 2. 同步今天的數據

```bash
# 方法 1: 使用 Shell 腳本（推薦）
bash /home/ubuntu/QuantLab/scripts/sync-shioaji-today.sh

# 方法 2: 直接執行 Python 腳本
cd /home/ubuntu/QuantLab/backend
python scripts/sync_shioaji_to_qlib.py --today
```

### 3. 配置定時任務（每天 15:00 自動同步）

```bash
crontab -e

# 添加以下行
0 15 * * 1-5 cd /home/ubuntu/QuantLab && bash scripts/sync-shioaji-today.sh >> /tmp/shioaji_cron.log 2>&1
```

## 📋 常用命令

| 命令 | 說明 |
|------|------|
| `--today` | 同步今天的數據 |
| `--yesterday` | 同步昨天的數據 |
| `--start-date 2025-12-01 --end-date 2025-12-13` | 同步指定日期範圍 |
| `--test` | 測試模式（僅同步前 5 檔） |
| `--stocks 2330,2317,2454` | 僅同步指定股票 |
| `--qlib-only` | 僅更新 Qlib，跳過 PostgreSQL |

## ⚙️ 環境變數

需要在 `.env` 文件中設定：

```bash
# Shioaji API（必須）
SHIOAJI_API_KEY=your_api_key
SHIOAJI_SECRET_KEY=your_secret_key

# PostgreSQL（可選，--qlib-only 時可跳過）
DATABASE_URL=postgresql://user:pass@localhost:5432/quantlab
```

## 📊 數據流程

```
Shioaji API
    ↓
[1 分鐘 K 線]
    ↓
    ├─→ PostgreSQL (stock_minute_prices)
    │   - 去重檢查
    │   - 批次插入
    │
    └─→ Qlib 格式 (/data/qlib/tw_stock_minute/)
        - open.1min.bin
        - high.1min.bin
        - low.1min.bin
        - close.1min.bin
        - volume.1min.bin
```

## 📈 效能參考

| 股票數 | 日期範圍 | 預計時間 | 數據量 |
|--------|----------|----------|--------|
| 1,700 檔 | 1 天 | 15-30 分鐘 | ~45 萬筆 |
| 50 檔 | 1 天 | 2-5 分鐘 | ~1.3 萬筆 |
| 1,700 檔 | 5 天 | 60-90 分鐘 | ~225 萬筆 |

## 🔍 驗證同步結果

### PostgreSQL

```sql
-- 檢查今天的數據
SELECT stock_id, COUNT(*)
FROM stock_minute_prices
WHERE datetime::date = CURRENT_DATE
GROUP BY stock_id
ORDER BY COUNT(*) DESC
LIMIT 10;
```

### Qlib

```python
from qlib.data import D
import qlib

qlib.init(provider_uri='/data/qlib/tw_stock_minute')
df = D.features(['2330'], ['$close', '$volume'], freq='1min')
print(f"數據筆數: {len(df)}")
```

## 📚 完整文檔

詳細使用說明請參閱：**[Document/SHIOAJI_SYNC_GUIDE.md](../../Document/SHIOAJI_SYNC_GUIDE.md)**

包含：
- 完整參數說明
- 進階用法（Celery 整合、Docker 部署等）
- 常見問題排查
- 效能優化建議

## ⚠️ 常見問題

### 1. Shioaji 登入失敗

檢查 `.env` 文件中的 API 金鑰是否正確。

### 2. 無數據返回

可能原因：
- 非交易日（週末、假日）
- Shioaji 歷史數據限制（通常僅 3-6 個月）

### 3. PostgreSQL 連接失敗

使用 `--qlib-only` 跳過資料庫：

```bash
python sync_shioaji_to_qlib.py --today --qlib-only
```

## 📄 授權

MIT License
