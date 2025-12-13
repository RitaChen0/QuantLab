# Shioaji 到 Qlib 同步工具使用指南（智慧增量同步版）

## 📌 概述

**sync_shioaji_to_qlib.py** 是一個獨立的 Python 工具，專門用於：
1. 從 Shioaji API 獲取台股 1 分鐘 K 線數據
2. 同時存儲到 PostgreSQL 和 Qlib 二進制格式
3. 🧠 **智慧增量同步**：自動檢測現有數據的最後日期，僅同步缺失部分
4. 支援每日增量更新和完整重建
5. 專為收盤後自動同步設計

## 🎯 主要特點

### 1. 🧠 智慧增量同步（新功能！）
- ✅ 自動檢測 PostgreSQL 和 Qlib 中每檔股票的最後日期
- ✅ 取兩者中較早的日期作為起點
- ✅ 從最後日期的下一天開始同步到今天
- ✅ 已是最新的股票自動跳過
- ✅ 首次同步自動回溯 30 天

**範例**：
```
股票 2330:
  - PostgreSQL 最後日期: 2025-12-10
  - Qlib 最後日期: 2025-12-12
  - 今天: 2025-12-13
  → 智慧判斷: 從 2025-12-11 開始同步到 2025-12-13（增量同步）
```

### 2. 獨立運行
- ✅ 不依賴 Docker 容器（可在 Host 或容器內運行）
- ✅ 可配置為 Cron 定時任務
- ✅ 完整的命令行參數支援

### 3. 雙軌存儲
- **PostgreSQL**：存入 `stock_minute_prices` 表（TimescaleDB hypertable）
- **Qlib 格式**：直接寫入 Qlib 二進制文件（`/data/qlib/tw_stock_minute/`）

### 4. 智慧去重
- 自動檢查 PostgreSQL 已存在記錄，避免重複插入
- Qlib 格式自動覆蓋（按日期範圍更新）

### 5. 詳細日誌
- 控制台輸出：同步進度、成功/失敗統計、智慧模式統計
- 日誌文件：`/tmp/shioaji_to_qlib_{time}.log`（保留 7 天）

## 🚀 快速開始

### 前置需求

1. **Shioaji API 金鑰**（必須）
   ```bash
   # 在 .env 文件中設定
   SHIOAJI_API_KEY=your_api_key
   SHIOAJI_SECRET_KEY=your_secret_key
   ```

2. **PostgreSQL 連接**（可選，`--qlib-only` 時可跳過）
   ```bash
   DATABASE_URL=postgresql://user:pass@localhost:5432/quantlab
   ```

3. **Python 依賴**
   ```bash
   # 已在 backend/requirements.txt 中
   pip install shioaji qlib pandas loguru tqdm
   ```

### 基本用法

#### 1. 🧠 智慧增量同步（最推薦！）
```bash
cd /home/ubuntu/QuantLab/backend
python scripts/sync_shioaji_to_qlib.py --smart
```

**說明**：
- 自動檢測每檔股票的最後日期
- 僅同步缺失的日期範圍
- 已是最新的股票自動跳過
- 大幅節省時間和 API 配額

#### 2. 智慧同步到指定日期
```bash
python scripts/sync_shioaji_to_qlib.py --smart --end-date 2025-12-13
```

#### 3. 傳統模式：同步今天的數據
```bash
python scripts/sync_shioaji_to_qlib.py --today
```

#### 4. 同步昨天的數據
```bash
python scripts/sync_shioaji_to_qlib.py --yesterday
```

#### 5. 同步指定日期範圍
```bash
python scripts/sync_shioaji_to_qlib.py \
  --start-date 2025-12-01 \
  --end-date 2025-12-13
```

#### 6. 測試模式（僅同步 5 檔股票）
```bash
python scripts/sync_shioaji_to_qlib.py --smart --test
```

#### 7. 僅同步指定股票
```bash
python scripts/sync_shioaji_to_qlib.py --smart --stocks 2330,2317,2454
```

#### 8. 僅更新 Qlib（跳過 PostgreSQL）
```bash
python scripts/sync_shioaji_to_qlib.py --smart --qlib-only
```

## 📋 完整參數說明

### 日期範圍參數（必選其一）

| 參數 | 說明 | 範例 |
|------|------|------|
| `--smart` | 🧠 智慧模式：自動檢測最後日期，僅同步缺失部分（推薦） | `--smart` |
| `--smart --end-date` | 智慧模式 + 指定結束日期 | `--smart --end-date 2025-12-13` |
| `--today` | 同步今天的數據（傳統模式） | `--today` |
| `--yesterday` | 同步昨天的數據（傳統模式） | `--yesterday` |
| `--start-date` | 指定開始日期（傳統模式） | `--start-date 2025-12-01` |
| `--end-date` | 指定結束日期（與 `--start-date` 搭配） | `--end-date 2025-12-13` |

### 股票範圍參數（可選）

| 參數 | 說明 | 範例 |
|------|------|------|
| `--stocks` | 指定股票代碼（逗號分隔） | `--stocks 2330,2317,2454` |
| `--test` | 測試模式（僅同步前 5 檔） | `--test` |
| `--limit` | 限制同步數量 | `--limit 10` |

### 存儲選項（可選）

| 參數 | 說明 | 範例 |
|------|------|------|
| `--qlib-only` | 僅更新 Qlib，跳過 PostgreSQL | `--qlib-only` |
| `--qlib-data-dir` | Qlib 數據目錄 | `--qlib-data-dir /data/qlib/tw_stock_minute` |

## 🔧 進階用法

### 1. 使用 Shell 包裝腳本（推薦）

```bash
# 使用預設配置同步今天的數據
bash /home/ubuntu/QuantLab/scripts/sync-shioaji-today.sh
```

**腳本特點**：
- 自動檢查環境變數
- 顏色輸出（綠色 = 成功，紅色 = 失敗）
- 顯示開始/結束時間

### 2. 配置為 Cron 定時任務

```bash
# 編輯 crontab
crontab -e

# 每個交易日 15:00 自動同步（推薦）
0 15 * * 1-5 cd /home/ubuntu/QuantLab && bash scripts/sync-shioaji-today.sh >> /tmp/shioaji_cron.log 2>&1

# 或使用 Python 腳本直接執行
0 15 * * 1-5 cd /home/ubuntu/QuantLab/backend && python scripts/sync_shioaji_to_qlib.py --today >> /tmp/shioaji_cron.log 2>&1
```

**時間選擇建議**：
- **15:00**：台股收盤後 1.5 小時（推薦，數據穩定）
- **14:00**：收盤後 30 分鐘（最快，但數據可能不完整）
- **16:00**：收盤後 2.5 小時（最保險）

### 3. 在 Docker 容器內運行

```bash
# 進入容器
docker compose exec backend bash

# 執行同步
python scripts/sync_shioaji_to_qlib.py --today

# 或使用 docker compose exec 直接執行
docker compose exec backend python scripts/sync_shioaji_to_qlib.py --today
```

### 4. 結合 Celery 定時任務

如果想整合到現有的 Celery Beat 系統，可以新增任務：

**backend/app/tasks/__init__.py**：
```python
from celery import shared_task
import subprocess

@shared_task(bind=True, max_retries=3)
def sync_shioaji_to_qlib_daily(self):
    """每日同步 Shioaji 數據到 Qlib"""
    try:
        result = subprocess.run(
            ['python', '/app/scripts/sync_shioaji_to_qlib.py', '--today'],
            capture_output=True,
            text=True,
            timeout=3600  # 1 小時超時
        )

        if result.returncode == 0:
            return {"status": "success", "output": result.stdout}
        else:
            raise Exception(f"Sync failed: {result.stderr}")

    except Exception as e:
        self.retry(exc=e, countdown=300)  # 5 分鐘後重試
```

**backend/app/core/celery_app.py**：
```python
celery_app.conf.beat_schedule.update({
    "sync-shioaji-to-qlib-daily": {
        "task": "app.tasks.sync_shioaji_to_qlib_daily",
        "schedule": crontab(hour=15, minute=0, day_of_week='1-5'),  # 週一至週五 15:00
    }
})
```

## 📊 數據流程

```
Shioaji API
    ↓
[1 分鐘 K 線] (OHLCV)
    ↓
    ├─→ PostgreSQL (stock_minute_prices 表)
    │   - 檢查去重
    │   - 批次插入
    │   - TimescaleDB 壓縮
    │
    └─→ Qlib 二進制格式 (/data/qlib/tw_stock_minute/)
        - features/{stock}/{feature}.1min.bin
        - 5 個特徵：open, high, low, close, volume
```

## 🗂️ Qlib 數據結構

同步後，Qlib 數據目錄結構如下：

```
/data/qlib/tw_stock_minute/
├── calendars/
│   └── 1min.txt              # 交易分鐘日曆（自動生成）
└── features/
    ├── 2330/                  # 台積電
    │   ├── open.1min.bin
    │   ├── high.1min.bin
    │   ├── low.1min.bin
    │   ├── close.1min.bin
    │   └── volume.1min.bin
    ├── 2317/                  # 鴻海
    │   ├── open.1min.bin
    │   └── ...
    └── ...
```

## 📈 效能指標

### 同步速度（測試環境）

| 場景 | 股票數 | 日期範圍 | 時間 | 數據量 |
|------|--------|----------|------|--------|
| 單日（今天） | 1,700 檔 | 1 天 | 15-30 分鐘 | ~45 萬筆 |
| 單日（今天） | 50 檔 | 1 天 | 2-5 分鐘 | ~1.3 萬筆 |
| 週數據 | 1,700 檔 | 5 天 | 60-90 分鐘 | ~225 萬筆 |
| 月數據 | 1,700 檔 | 20 天 | 4-6 小時 | ~900 萬筆 |

**影響因素**：
- Shioaji API 速率限制
- 網路速度
- PostgreSQL 寫入效能
- 磁碟 I/O 速度

### 優化建議

1. **限制股票數量**（測試階段）
   ```bash
   python sync_shioaji_to_qlib.py --today --limit 50
   ```

2. **僅更新 Qlib**（跳過資料庫）
   ```bash
   python sync_shioaji_to_qlib.py --today --qlib-only
   ```

3. **批次處理**（分段同步）
   ```bash
   # 先同步 Top 50
   python sync_shioaji_to_qlib.py --today --stocks $(head -50 stocks.txt | tr '\n' ',')

   # 再同步其他
   python sync_shioaji_to_qlib.py --today --stocks $(tail -n +51 stocks.txt | tr '\n' ',')
   ```

## ⚠️ 常見問題

### 1. Shioaji 登入失敗

**錯誤訊息**：
```
❌ Failed to initialize Shioaji: login failed
```

**解決方法**：
- 檢查 `.env` 文件中的 `SHIOAJI_API_KEY` 和 `SHIOAJI_SECRET_KEY`
- 確認金鑰有效期（Shioaji API 金鑰有使用期限）
- 檢查網路連線（Shioaji API 需要連線到台灣）

### 2. 無數據返回

**錯誤訊息**：
```
⚠️  2330: 無數據
```

**可能原因**：
- 指定的日期是非交易日（週末、國定假日）
- Shioaji API 歷史數據限制（通常僅保留 3-6 個月）
- 股票代碼錯誤或已下市

**解決方法**：
```bash
# 檢查是否為交易日
python -c "from datetime import date; print(date.today().weekday())"  # 0-4 是工作日

# 使用較近的日期
python sync_shioaji_to_qlib.py --yesterday
```

### 3. PostgreSQL 連接失敗

**錯誤訊息**：
```
❌ 獲取股票清單失敗: connection refused
```

**解決方法**：
```bash
# 檢查資料庫是否運行
docker compose ps postgres

# 檢查連接字串
echo $DATABASE_URL

# 使用 --qlib-only 跳過資料庫
python sync_shioaji_to_qlib.py --today --qlib-only
```

### 4. Qlib 寫入失敗

**錯誤訊息**：
```
⚠️  Qlib close: 寫入失敗 - Permission denied
```

**解決方法**：
```bash
# 檢查目錄權限
ls -ld /data/qlib/tw_stock_minute

# 修復權限
sudo chown -R $(whoami) /data/qlib/tw_stock_minute
chmod -R 755 /data/qlib/tw_stock_minute

# 或使用自訂目錄
python sync_shioaji_to_qlib.py --today --qlib-data-dir ~/qlib_data
```

### 5. 記憶體不足

**錯誤訊息**：
```
MemoryError: Unable to allocate array
```

**解決方法**：
- 減少同步數量：`--limit 100`
- 分批處理（見「優化建議」）
- 增加 Docker 容器記憶體限制（`docker-compose.yml`）

## 🔍 日誌與監控

### 查看即時日誌

```bash
# 方法 1: 直接執行時查看
python sync_shioaji_to_qlib.py --today

# 方法 2: 查看日誌文件
tail -f /tmp/shioaji_to_qlib_*.log

# 方法 3: 過濾錯誤訊息
grep '❌' /tmp/shioaji_to_qlib_*.log
```

### 統計同步結果

```bash
# 成功數量
grep '✅' /tmp/shioaji_to_qlib_*.log | wc -l

# 失敗數量
grep '❌' /tmp/shioaji_to_qlib_*.log | wc -l

# 跳過數量
grep '⏭️' /tmp/shioaji_to_qlib_*.log | wc -l
```

### 驗證數據完整性

**PostgreSQL**：
```sql
-- 檢查今天的數據量
SELECT stock_id, COUNT(*)
FROM stock_minute_prices
WHERE datetime::date = CURRENT_DATE
GROUP BY stock_id
ORDER BY COUNT(*) DESC
LIMIT 10;

-- 預期：每檔股票約 270 筆（交易時段 4.5 小時 × 60 分鐘）
```

**Qlib**：
```python
from qlib.data import D
import qlib

qlib.init(provider_uri='/data/qlib/tw_stock_minute')

# 讀取台積電今天的數據
df = D.features(['2330'], ['$close', '$volume'], freq='1min')
print(f"數據筆數: {len(df)}")
print(df.tail())
```

## 📚 相關文件

- **README.md**：QuantLab 專案概述
- **CLAUDE.md**：專案架構與設計決策
- **Document/QLIB_SYNC_GUIDE.md**：Qlib 數據同步指南（日線數據）
- **Document/OPERATIONS_GUIDE.md**：操作手冊
- **backend/app/services/shioaji_client.py**：Shioaji API 客戶端原始碼

## 🤝 貢獻與回饋

如果遇到問題或有改進建議，歡迎：
1. 提交 Issue 到 GitHub
2. 修改並提交 Pull Request
3. 更新此文檔

## 📄 授權

MIT License - 詳見 LICENSE 文件
