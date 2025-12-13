# 分鐘線數據管理指南

## 📊 數據現況

### PostgreSQL 分鐘線數據（✅ 已存在）

```sql
-- 查看統計
SELECT
    COUNT(*) as total_records,
    COUNT(DISTINCT stock_id) as stock_count,
    MIN(datetime) as earliest,
    MAX(datetime) as latest
FROM stock_minute_prices;
```

**結果**：
- **總筆數**：65,343,960 筆（6500 萬筆）
- **股票數**：1,626 檔
- **時間範圍**：2018-12-07 09:01:00 ~ 2025-12-10 13:30:00（約 7 年）
- **數據來源**：ShioajiData CSV 檔案（已匯入）

### Qlib 格式分鐘線（需要轉換）

目前 **不存在**，需要從以下兩種方式之一獲取：

---

## 🔄 兩種數據獲取方式

### 方式一：從 PostgreSQL 轉換（推薦）✅

**工具**：`export_minute_to_qlib.py`

**優點**：
- ✅ **超快速**：本地數據，不需網路請求
- ✅ **完整**：已有 7 年歷史數據（2018-2025）
- ✅ **穩定**：不受 API 限制
- ✅ **免費**：不消耗 Shioaji API 配額

**使用方式**：
```bash
# 🧠 智慧增量轉換（推薦）
bash /home/ubuntu/QuantLab/scripts/convert-minute-to-qlib.sh

# 或直接執行 Python 腳本
cd /home/ubuntu/QuantLab/backend
python scripts/export_minute_to_qlib.py \
    --output-dir /data/qlib/tw_stock_minute \
    --smart
```

**預計時間**：
- 首次轉換：10-30 分鐘（1,626 檔股票 × 7 年數據）
- 增量轉換：1-5 分鐘（僅轉換新增數據）

---

### 方式二：從 Shioaji API 下載（備用）

**工具**：`sync_shioaji_to_qlib.py`

**優點**：
- ✅ 可以獲取最新數據（如果 PostgreSQL 落後）
- ✅ 支援雙軌存儲（PostgreSQL + Qlib）

**缺點**：
- ❌ **慢**：需要逐一調用 Shioaji API
- ❌ **受限**：API 有速率限制
- ❌ **不完整**：Shioaji 歷史數據通常只保留 3-6 個月

**使用方式**：
```bash
cd /home/ubuntu/QuantLab/backend
python scripts/sync_shioaji_to_qlib.py --smart
```

**適用場景**：
- PostgreSQL 數據缺失或過舊
- 需要雙軌存儲到 PostgreSQL + Qlib
- 僅需同步近期數據（如今天）

---

## 🎯 推薦流程

### 初次設置（一次性）

1. **轉換現有數據**（PostgreSQL → Qlib）
   ```bash
   bash /home/ubuntu/QuantLab/scripts/convert-minute-to-qlib.sh
   ```

2. **驗證結果**
   ```bash
   ls -lh /data/qlib/tw_stock_minute/features/2330/
   # 應該看到 5 個 .1min.bin 檔案
   ```

### 日常維護（每日）

**選項 A**：僅更新 Qlib（推薦，快速）
```bash
cd /home/ubuntu/QuantLab/backend
python scripts/export_minute_to_qlib.py \
    --output-dir /data/qlib/tw_stock_minute \
    --smart
```

**選項 B**：雙軌更新（PostgreSQL + Qlib）
```bash
cd /home/ubuntu/QuantLab/backend
python scripts/sync_shioaji_to_qlib.py --smart
```

---

## 📁 Qlib 分鐘線數據結構

轉換完成後，目錄結構如下：

```
/data/qlib/tw_stock_minute/
├── calendars/
│   └── 1min.txt              # 交易分鐘日曆
└── features/
    ├── 2330/                 # 台積電
    │   ├── open.1min.bin     # 開盤價
    │   ├── high.1min.bin     # 最高價
    │   ├── low.1min.bin      # 最低價
    │   ├── close.1min.bin    # 收盤價
    │   └── volume.1min.bin   # 成交量
    ├── 2317/                 # 鴻海
    └── ...                   # 其他 1,624 檔股票
```

---

## 🔍 驗證數據

### 方式一：使用 Qlib API

```python
from qlib.data import D
import qlib

qlib.init(provider_uri='/data/qlib/tw_stock_minute')

# 讀取台積電分鐘線數據
df = D.features(['2330'], ['$close', '$volume'], freq='1min')
print(f"數據筆數: {len(df)}")
print(df.head())
print(df.tail())
```

### 方式二：檢查檔案大小

```bash
# 台積電應該有約 42 萬筆分鐘數據（7 年 × 約 270 分鐘/天 × 240 交易日/年）
ls -lh /data/qlib/tw_stock_minute/features/2330/

# 預期檔案大小：約 1.6 MB/特徵（42 萬 × 4 bytes）
```

---

## ⚙️ 進階選項

### 僅轉換指定股票

```bash
python scripts/export_minute_to_qlib.py \
    --output-dir /data/qlib/tw_stock_minute \
    --stocks 2330,2317,2454
```

### 測試模式（僅轉換 10 檔）

```bash
python scripts/export_minute_to_qlib.py \
    --output-dir /data/qlib/tw_stock_minute \
    --test
```

### 限制轉換數量

```bash
python scripts/export_minute_to_qlib.py \
    --output-dir /data/qlib/tw_stock_minute \
    --limit 100
```

---

## 📊 效能比較

| 方式 | 首次時間 | 增量時間 | 數據完整性 | API 依賴 |
|------|----------|----------|------------|----------|
| **PostgreSQL 轉換** | 10-30 分鐘 | 1-5 分鐘 | ✅ 7 年完整 | ❌ 不需要 |
| **Shioaji API** | 2-5 小時 | 15-30 分鐘 | ⚠️ 僅 3-6 個月 | ✅ 需要 |

---

## 🤔 常見問題

### Q: 我應該使用哪種方式？

**A**:
- **首次設置**：方式一（PostgreSQL 轉換），快速且完整
- **日常更新**：方式一的智慧模式，僅轉換新增日期
- **補充最新數據**：如果 PostgreSQL 落後，使用方式二

### Q: 兩種方式可以一起用嗎？

**A**: 可以！
1. 先用方式一轉換歷史數據（2018-2025）
2. 每天用方式二同步最新數據到 PostgreSQL + Qlib

### Q: 轉換後檔案大小多大？

**A**: 約 **3-5 GB**（1,626 檔 × 5 特徵 × 1.6 MB）

### Q: 智慧模式如何工作？

**A**:
1. 檢查 Qlib 中每檔股票的最後日期
2. 僅轉換最後日期之後的新數據
3. 已是最新的股票自動跳過

---

## 📚 相關文檔

- **SHIOAJI_SYNC_GUIDE.md** - Shioaji 同步工具完整指南
- **SMART_SYNC_README.md** - 智慧增量同步說明
- **QLIB_SYNC_GUIDE.md** - Qlib 日線數據同步指南

---

## 📄 授權

MIT License
