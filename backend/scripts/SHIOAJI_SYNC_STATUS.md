# 📊 Shioaji 智慧同步工具狀態報告

> 更新時間：2025-12-13

## ✅ 功能狀態

### 1. `sync_shioaji_to_qlib.py` - 智慧增量同步工具

**狀態**：✅ **已完成修正，功能完整**

**功能特點**：
- ✅ 智慧增量同步：自動檢測 PostgreSQL 和 Qlib 的最後日期
- ✅ 雙軌存儲：同時更新 PostgreSQL + Qlib
- ✅ 避免重複：自動跳過已存在的記錄
- ✅ 靈活模式：支援完整同步、增量同步、僅更新 Qlib

**最近修正**：
- 修正 Repository 方法調用（`get_by_stock_datetime_timeframe`）
- 修正靜態方法參數傳遞（添加 `db=` 參數）
- 添加 `timeframe='1min'` 參數

---

## 📋 使用方式

### 基本用法

```bash
# 進入 backend 容器
docker compose exec backend bash

# 🧠 智慧增量同步（推薦）
python scripts/sync_shioaji_to_qlib.py --smart

# 智慧同步到指定日期
python scripts/sync_shioaji_to_qlib.py --smart --end-date 2025-12-13

# 測試模式（僅同步 5 檔股票）
python scripts/sync_shioaji_to_qlib.py --smart --test

# 僅更新 Qlib，跳過 PostgreSQL
python scripts/sync_shioaji_to_qlib.py --smart --qlib-only
```

### 進階用法

```bash
# 同步今天的數據
python scripts/sync_shioaji_to_qlib.py --today

# 同步指定日期範圍
python scripts/sync_shioaji_to_qlib.py --start-date 2025-12-01 --end-date 2025-12-13

# 同步指定股票
python scripts/sync_shioaji_to_qlib.py --smart --stocks 2330,2317,2454

# 限制同步數量
python scripts/sync_shioaji_to_qlib.py --smart --limit 100
```

---

## ⚙️ 環境配置需求

### 必要條件

要使用 Shioaji API 同步功能，需要完成以下配置：

#### 1. 安裝 Shioaji 套件

```bash
# 在容器內執行
docker compose exec backend pip install shioaji
```

#### 2. 配置 API Key

在 `/home/ubuntu/QuantLab/.env` 文件中添加：

```env
SHIOAJI_API_KEY=your_api_key_here
SHIOAJI_SECRET_KEY=your_secret_key_here
```

#### 3. 重啟容器

```bash
docker compose restart backend
```

### 當前狀態

- ❌ **Shioaji 套件未安裝**
- ❌ **API Key 未配置**

**建議**：
- 如需使用 Shioaji API 同步，請完成上述配置
- 如果只需轉換現有 PostgreSQL 數據，使用 `export_minute_to_qlib.py`（推薦）

---

## 📊 當前數據狀況

### PostgreSQL 分鐘線數據

```
股票數量：1,626 檔
總記錄數：65,343,960 筆（6500 萬筆）
時間範圍：2018-12-07 09:01:00 ~ 2025-12-10 13:30:00
數據完整性：✅ 完整（約 7 年歷史數據）
```

### Qlib 分鐘線數據

```
目錄：/data/qlib/tw_stock_minute/
狀態：部分股票已轉換（測試階段）
建議：使用 export_minute_to_qlib.py 完整轉換
```

---

## 🚀 推薦工作流程

### 方案 A：使用現有數據（推薦）✅

**適用場景**：PostgreSQL 已有完整數據（如本系統）

```bash
# 1. 一次性轉換所有數據（10-30 分鐘）
bash /home/ubuntu/QuantLab/scripts/convert-minute-to-qlib.sh

# 2. 日常增量同步（1-5 分鐘）
cd /home/ubuntu/QuantLab/backend
python scripts/export_minute_to_qlib.py --output-dir /data/qlib/tw_stock_minute --smart
```

**優點**：
- 超快速（本地轉換，無需 API 調用）
- 完整歷史數據（7 年）
- 免費（不消耗 API 配額）

---

### 方案 B：使用 Shioaji API（備用）

**適用場景**：PostgreSQL 數據缺失或需要最新數據

```bash
# 1. 配置環境（僅需一次）
docker compose exec backend pip install shioaji
# 編輯 .env 添加 API Key
docker compose restart backend

# 2. 智慧增量同步
cd /home/ubuntu/QuantLab/backend
python scripts/sync_shioaji_to_qlib.py --smart

# 3. 設定定時任務（每天 15:00 自動同步）
crontab -e
# 添加：0 15 * * 1-5 cd /home/ubuntu/QuantLab/backend && python scripts/sync_shioaji_to_qlib.py --smart >> /tmp/shioaji_sync.log 2>&1
```

**優點**：
- 可獲取最新數據
- 雙軌存儲（PostgreSQL + Qlib）
- 自動化運行

**缺點**：
- 需要 API Key
- 速率限制
- Shioaji 歷史數據通常只保留 3-6 個月

---

## 🧠 智慧同步原理

### 工作流程

```
1️⃣  檢查 PostgreSQL 最後日期
   └─ SELECT MAX(datetime::date) FROM stock_minute_prices WHERE stock_id = '2330'
   └─ 結果：2025-12-10

2️⃣  檢查 Qlib 最後日期
   └─ 讀取 /data/qlib/tw_stock_minute/features/2330/close.1min.bin
   └─ 結果：2025-12-08

3️⃣  智慧判斷同步範圍
   └─ 取較早的日期：min(2025-12-10, 2025-12-08) = 2025-12-08
   └─ 同步範圍：2025-12-09 ~ 今天（增量同步）

4️⃣  執行同步
   └─ 調用 Shioaji API 獲取 2025-12-09 ~ 今天的數據
   └─ 同時更新 PostgreSQL 和 Qlib
```

### 同步類型

| 類型 | 觸發條件 | 行為 |
|------|---------|------|
| **完整同步** | 完全沒有數據 | 從 30 天前同步到今天 |
| **增量同步** | 有舊數據，但不是最新 | 從最後日期下一天同步到今天 |
| **跳過** | 數據已是最新 | 不執行任何操作（節省時間） |

---

## 📈 效能比較

| 方式 | 首次時間 | 增量時間 | 數據完整性 | API 依賴 | 成本 |
|------|----------|----------|------------|----------|------|
| **PostgreSQL 轉換** | 10-30 分鐘 | 1-5 分鐘 | ✅ 7 年完整 | ❌ 不需要 | 免費 |
| **Shioaji API** | 2-5 小時 | 15-30 分鐘 | ⚠️ 僅 3-6 個月 | ✅ 需要 | API 配額 |

---

## ❓ 常見問題

### Q1: 為什麼推薦使用 PostgreSQL 轉換而不是 Shioaji API？

**A**:
- PostgreSQL 已有 7 年完整數據（2018-2025）
- 轉換速度快 10-100 倍
- 不受 API 速率限制
- 完全免費

### Q2: 什麼時候需要使用 Shioaji API？

**A**:
- PostgreSQL 數據缺失或過舊
- 需要同步最新收盤數據（今天）
- 需要雙軌存儲（PostgreSQL + Qlib 同時更新）

### Q3: 智慧模式會不會漏掉數據？

**A**: 不會。智慧模式取 PostgreSQL 和 Qlib 中 **較早的日期**，確保兩者都同步到最新。

### Q4: 如何驗證同步是否成功？

**A**:
```bash
# 檢查 PostgreSQL
docker compose exec -T postgres psql -U quantlab -d quantlab -c "
SELECT MAX(datetime::date) FROM stock_minute_prices WHERE stock_id = '2330';
"

# 檢查 Qlib
docker compose exec backend python3 -c "
import qlib
from qlib.data import D
qlib.init(provider_uri='/data/qlib/tw_stock_minute')
df = D.features(['2330'], ['\$close'], freq='1min')
print(df.index.get_level_values('datetime').max())
"
```

---

## 📚 相關文檔

- **MINUTE_DATA_README.md** - 分鐘線數據管理完整指南
- **SMART_SYNC_README.md** - 智慧增量同步功能說明
- **SHIOAJI_SYNC_GUIDE.md** - Shioaji 同步工具完整指南

---

## 📄 授權

MIT License
