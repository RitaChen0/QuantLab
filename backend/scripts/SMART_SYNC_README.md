# 🧠 智慧增量同步功能說明

## 功能概述

`sync_shioaji_to_qlib.py` 現在支援 **智慧增量同步** 模式，能夠自動檢測現有數據的最後日期，僅同步缺失的部分，大幅節省時間和 API 配額。

## 核心原理

### 1. 自動檢測最後日期

對於每檔股票，工具會檢查兩個來源的最後日期：
- **PostgreSQL**: `stock_minute_prices` 表
- **Qlib**: `/data/qlib/tw_stock_minute/` 二進制文件

### 2. 智慧判斷同步範圍

| 情境 | 行為 | 說明 |
|------|------|------|
| **首次同步** | 從 30 天前開始 → 今天 | 完整同步 |
| **增量同步** | 從最後日期下一天 → 今天 | 僅同步缺失部分 |
| **已是最新** | 跳過 | 節省時間 |

**範例**：
```
股票 2330:
  PostgreSQL 最後日期: 2025-12-10
  Qlib 最後日期: 2025-12-12
  今天: 2025-12-13

  → 取較早的日期: 2025-12-10
  → 同步範圍: 2025-12-11 ~ 2025-12-13（3 天）
```

### 3. 雙重保護機制

取 PostgreSQL 和 Qlib 中 **較早的日期**，確保兩者都是最新的：

```python
if db_last_date and qlib_last_date:
    last_date = min(db_last_date, qlib_last_date)  # 取較早的日期
```

這樣可以避免某一方數據缺失的問題。

## 使用方式

### 方式一：使用 Shell 腳本（推薦）

```bash
bash /home/ubuntu/QuantLab/scripts/sync-shioaji-today.sh
```

### 方式二：直接執行 Python 腳本

```bash
cd /home/ubuntu/QuantLab/backend
python scripts/sync_shioaji_to_qlib.py --smart
```

### 方式三：配置定時任務

```bash
# 每個交易日 15:00 自動智慧同步
crontab -e

# 添加以下行
0 15 * * 1-5 cd /home/ubuntu/QuantLab && bash scripts/sync-shioaji-today.sh >> /tmp/shioaji_cron.log 2>&1
```

## 參數選項

| 參數 | 說明 |
|------|------|
| `--smart` | 啟用智慧增量同步（推薦） |
| `--smart --end-date 2025-12-13` | 智慧同步到指定日期 |
| `--smart --test` | 測試模式（僅 5 檔） |
| `--smart --stocks 2330,2317` | 僅同步指定股票 |
| `--smart --qlib-only` | 僅更新 Qlib |

## 效能比較

### 傳統模式（--today）
```
1,700 檔股票 × 1 天 = 15-30 分鐘
```

### 智慧模式（--smart）

| 情境 | 時間 | 原因 |
|------|------|------|
| 全部已是最新 | **< 1 分鐘** | 僅檢查，全部跳過 |
| 500 檔需要更新 | **5-10 分鐘** | 僅同步 500 檔 |
| 全部需要更新 | 15-30 分鐘 | 與傳統模式相同 |

**節省時間：最高 95%+**

## 輸出範例

```
============================================================
開始同步: 1700 檔股票
🧠 智慧模式: 自動檢測每檔股票的最後日期
   目標日期: 2025-12-13
============================================================

  📦 2330: 完整同步 (2025-11-13 ~ 2025-12-13)
  ✅ 2330: DB +7020, Qlib ✓

  ➕ 2317: 增量同步 (2025-12-11 ~ 2025-12-13)
  ✅ 2317: DB +810, Qlib ✓

  ⏭️  2454: 已是最新，跳過

  ...

============================================================
同步完成！
📦 完整同步: 150 檔
➕ 增量同步: 500 檔
⏭️  已最新跳過: 1050 檔
❌ 失敗: 0 檔
📊 PostgreSQL: 插入 125,400 筆
📊 Qlib: 更新 650 檔
============================================================
```

## 實作細節

### get_db_last_date()
```python
def get_db_last_date(self, stock_id: str) -> Optional[date]:
    """獲取 PostgreSQL 中該股票的最後日期"""
    result = conn.execute(text("""
        SELECT MAX(datetime::date) as last_date
        FROM stock_minute_prices
        WHERE stock_id = :stock_id
    """), {"stock_id": stock_id})
    return row[0] if row else None
```

### get_qlib_last_date()
```python
def get_qlib_last_date(self, stock_id: str) -> Optional[date]:
    """獲取 Qlib 中該股票的最後日期"""
    df = D.features([stock_id], ['$close'], freq='1min')
    if df is None or df.empty:
        return None
    last_datetime = df.index.get_level_values('datetime').max()
    return last_datetime.date()
```

### determine_sync_range()
```python
def determine_sync_range(
    self, stock_id: str, user_end_date: date, smart_mode: bool = False
) -> Tuple[Optional[date], Optional[date], str]:
    """智慧判斷需要同步的日期範圍"""

    db_last_date = self.get_db_last_date(stock_id)
    qlib_last_date = self.get_qlib_last_date(stock_id)

    # 取較早的日期
    if db_last_date and qlib_last_date:
        last_date = min(db_last_date, qlib_last_date)
    elif db_last_date:
        last_date = db_last_date
    elif qlib_last_date:
        last_date = qlib_last_date
    else:
        # 首次同步，回溯 30 天
        return (user_end_date - timedelta(days=30), user_end_date, 'full')

    # 檢查是否已是最新
    if last_date >= user_end_date:
        return (None, None, 'skip')

    # 增量同步
    start_date = last_date + timedelta(days=1)
    return (start_date, user_end_date, 'incremental')
```

## 常見問題

### Q: 智慧模式會不會漏掉數據？

**A**: 不會。智慧模式取 PostgreSQL 和 Qlib 中 **較早的日期**，確保兩者都同步到最新。

### Q: 第一次使用智慧模式會回溯多久？

**A**: 預設回溯 30 天。如需更長時間，可使用傳統模式指定日期範圍。

### Q: 智慧模式適合什麼場景？

**A**:
- ✅ 每日定時同步（收盤後）
- ✅ 補齊歷史缺失數據
- ✅ 避免重複下載已有數據

### Q: 傳統模式還需要嗎？

**A**: 需要。以下情況建議使用傳統模式：
- 首次導入大量歷史數據（指定明確日期範圍）
- 重建特定時間段的數據
- 驗證特定日期的數據正確性

## 總結

🧠 **智慧增量同步** 是收盤後自動同步的最佳選擇：
- ✅ 自動化程度高
- ✅ 節省時間和資源
- ✅ 避免重複下載
- ✅ 雙重保護機制

建議配置為每日定時任務，每天 15:00 自動運行。
