# QuantLab 資料庫架構報告

**文檔版本**: 1.0
**建立日期**: 2025-12-05
**資料庫版本**: PostgreSQL 15 + TimescaleDB
**當前狀態**: 生產環境

---

## 目錄

1. [資料庫概述](#資料庫概述)
2. [資料表結構詳細說明](#資料表結構詳細說明)
3. [關聯關係圖](#關聯關係圖)
4. [索引策略](#索引策略)
5. [遷移歷史](#遷移歷史)
6. [資料完整性約束](#資料完整性約束)
7. [效能優化](#效能優化)
8. [新增資料表指南](#新增資料表指南)
9. [備份與維護](#備份與維護)
10. [資料驗證清單](#資料驗證清單)

---

## 資料庫概述

### 基本資訊

- **資料庫名稱**: `quantlab`
- **擁有者**: `quantlab`
- **字元集**: UTF-8
- **時區**: UTC
- **擴展功能**:
  - TimescaleDB（時序數據優化）
  - pg_trgm（文字搜尋最佳化）

### 當前狀態統計

```sql
-- 2025-12-05 統計數據
總資料表數: 16
總資料大小: ~437 MB
股票數量: 2,671 檔
財務指標記錄: 1,880,982 筆
產業分類: 41 個 (TWSE)
股票-產業映射: 1,935 筆 (72.5% 覆蓋率)
```

### 資料表大小排序

| 排名 | 資料表名稱 | 大小 | 用途 |
|------|-----------|------|------|
| 1 | `fundamental_data` | 435 MB | 財務指標數據（最大） |
| 2 | `stocks` | 832 KB | 股票基本資料 |
| 3 | `stock_industries` | 360 KB | 股票-產業映射 |
| 4 | `trades` | 248 KB | 回測交易記錄 |
| 5 | `backtests` | 192 KB | 回測配置 |
| 6 | `strategies` | 144 KB | 交易策略 |
| 7 | `users` | 80 KB | 使用者資料 |
| 8 | `industries` | 64 KB | 產業分類 |
| 9 | `backtest_results` | 56 KB | 回測績效結果 |
| 10 | `industry_metrics_cache` | 48 KB | 產業指標快取 |

---

## 資料表結構詳細說明

### 1. users（使用者）

**用途**: 存儲使用者帳號、權限、API Token

**主鍵**: `id` (Integer, Auto-increment)

**欄位列表**:

| 欄位名稱 | 資料型別 | 約束 | 說明 |
|---------|---------|------|------|
| `id` | Integer | PK, Index | 使用者 ID |
| `email` | String(255) | Unique, Not Null, Index | 電子郵件 |
| `username` | String(100) | Unique, Not Null, Index | 使用者名稱 |
| `hashed_password` | String(255) | Not Null | bcrypt 加密密碼 |
| `full_name` | String(255) | Nullable | 全名 |
| `is_active` | Boolean | Not Null, Default=True | 帳號啟用狀態 |
| `is_superuser` | Boolean | Not Null, Default=False | 超級管理員 |
| `finlab_api_token` | EncryptedText | Nullable | FinLab API Token（Fernet 加密） |
| `created_at` | DateTime(TZ) | Not Null, Server Default | 建立時間 |
| `updated_at` | DateTime(TZ) | Not Null, Auto Update | 更新時間 |
| `last_login` | DateTime(TZ) | Nullable | 最後登入時間 |

**索引**:
- `idx_users_email` (UNIQUE)
- `idx_users_username` (UNIQUE)

**關聯**:
- 一對多 → `strategies`（CASCADE DELETE）
- 一對多 → `backtests`（CASCADE DELETE）
- 一對多 → `custom_industry_categories`

**安全機制**:
- 密碼使用 bcrypt（cost factor 12）
- FinLab Token 使用 Fernet 對稱加密
- JWT Token 不存儲於資料庫（僅記憶體）

---

### 2. stocks（股票基本資料）

**用途**: 存儲所有台股基本資訊

**主鍵**: `stock_id` (String(10), 股票代碼如 "2330")

**欄位列表**:

| 欄位名稱 | 資料型別 | 約束 | 說明 |
|---------|---------|------|------|
| `stock_id` | String(10) | PK, Index | 股票代碼（如 "2330"） |
| `name` | String(100) | Not Null | 股票名稱（如 "台積電"） |
| `category` | String(50) | Nullable | 產業分類 |
| `market` | String(20) | Nullable | 市場別（上市/上櫃/興櫃） |
| `is_active` | String(10) | Not Null, Default='active' | 狀態（active/delisted） |
| `created_at` | DateTime(TZ) | Not Null, Server Default | 建立時間 |
| `updated_at` | DateTime(TZ) | Not Null, Auto Update | 更新時間 |

**索引**:
- `idx_stock_name` (B-tree)
- `idx_stock_category` (B-tree)
- `idx_stock_market` (B-tree)

**關聯**:
- 一對多 → `stock_prices`（CASCADE DELETE）
- 一對多 → `trades`（CASCADE DELETE）
- 一對多 → `stock_industries`（CASCADE DELETE）

**資料來源**: FinLab API `stock_list()`

---

### 3. stock_prices（股票歷史價格 - TimescaleDB Hypertable）

**用途**: 存儲股票 OHLCV 時序數據

**主鍵**: 複合主鍵 `(stock_id, date)`

**欄位列表**:

| 欄位名稱 | 資料型別 | 約束 | 說明 |
|---------|---------|------|------|
| `stock_id` | String(10) | PK, FK → stocks | 股票代碼 |
| `date` | Date | PK, Not Null | 交易日期 |
| `open` | Numeric(10,2) | Not Null | 開盤價 |
| `high` | Numeric(10,2) | Not Null | 最高價 |
| `low` | Numeric(10,2) | Not Null | 最低價 |
| `close` | Numeric(10,2) | Not Null | 收盤價 |
| `volume` | BigInteger | Not Null | 成交量 |
| `adj_close` | Numeric(10,2) | Nullable | 調整後收盤價（考慮除權息） |

**索引**:
- `pk_stock_prices` (PRIMARY KEY: stock_id, date)
- `idx_stock_prices_date` (B-tree on date)
- `idx_stock_prices_stock_date` (Composite: stock_id, date)

**TimescaleDB 配置**:
- **Hypertable**: 已啟用（Partition by `date`）
- **Chunk Interval**: 7 天
- **Compression**: 啟用（數據 > 30 天自動壓縮）
  - `compress_orderby`: date DESC
  - `compress_segmentby`: stock_id
- **Retention Policy**: 未設定（保留所有歷史數據）

**外鍵約束**:
- `stock_id` → `stocks.stock_id` (ON DELETE CASCADE)

**查詢優化**:
```sql
-- 優化範例查詢（利用 TimescaleDB 分區）
SELECT * FROM stock_prices
WHERE stock_id = '2330'
  AND date >= '2024-01-01'
  AND date <= '2024-12-31';
```

---

### 4. strategies（交易策略）

**用途**: 存儲使用者建立的 Backtrader 策略代碼

**主鍵**: `id` (Integer, Auto-increment)

**欄位列表**:

| 欄位名稱 | 資料型別 | 約束 | 說明 |
|---------|---------|------|------|
| `id` | Integer | PK, Index | 策略 ID |
| `user_id` | Integer | FK → users, Not Null | 使用者 ID |
| `name` | String(200) | Not Null | 策略名稱 |
| `description` | Text | Nullable | 策略描述 |
| `code` | Text | Not Null | Python 策略代碼 |
| `parameters` | JSON | Nullable | 策略參數（動態配置） |
| `status` | Enum | Not Null, Default='draft' | 狀態（draft/active/archived） |
| `created_at` | DateTime(TZ) | Not Null, Server Default | 建立時間 |
| `updated_at` | DateTime(TZ) | Not Null, Auto Update | 更新時間 |

**索引**:
- `idx_strategy_user_id` (B-tree)
- `idx_strategy_status` (B-tree)
- `idx_strategy_created_at` (B-tree)
- `idx_strategy_user_status` (Composite: user_id, status)
- `idx_strategy_user_created` (Composite: user_id, created_at)
- `idx_strategy_name_gin` (GIN with pg_trgm for ILIKE queries)

**外鍵約束**:
- `user_id` → `users.id` (ON DELETE CASCADE)

**Enum 定義**:
```python
class StrategyStatus(str, enum.Enum):
    DRAFT = "draft"          # 草稿
    ACTIVE = "active"        # 已啟用
    ARCHIVED = "archived"    # 已封存
```

**安全驗證**:
- 代碼提交前經過 AST 解析驗證（白名單模組、黑名單函數）
- 執行時使用受限 `__builtins__`

**配額限制**:
- 每位使用者最多 50 個策略（`MAX_STRATEGIES_PER_USER`）

---

### 5. backtests（回測配置）

**用途**: 存儲回測執行配置與狀態

**主鍵**: `id` (Integer, Auto-increment)

**欄位列表**:

| 欄位名稱 | 資料型別 | 約束 | 說明 |
|---------|---------|------|------|
| `id` | Integer | PK, Index | 回測 ID |
| `strategy_id` | Integer | FK → strategies, Not Null | 策略 ID |
| `user_id` | Integer | FK → users, Not Null | 使用者 ID |
| `name` | String(200) | Not Null | 回測名稱 |
| `description` | Text | Nullable | 回測描述 |
| `symbol` | String(20) | Not Null | 股票代碼 |
| `parameters` | JSON | Default={} | 策略參數覆寫 |
| `start_date` | Date | Not Null | 回測開始日期 |
| `end_date` | Date | Not Null | 回測結束日期 |
| `initial_capital` | Numeric(15,2) | Not Null, Default=1000000 | 初始資金 |
| `status` | Enum | Not Null, Default='PENDING' | 狀態 |
| `error_message` | Text | Nullable | 錯誤訊息 |
| `started_at` | DateTime(TZ) | Nullable | 開始執行時間 |
| `completed_at` | DateTime(TZ) | Nullable | 完成時間 |
| `created_at` | DateTime(TZ) | Not Null, Server Default | 建立時間 |
| `updated_at` | DateTime(TZ) | Not Null, Auto Update | 更新時間 |

**索引**:
- `idx_backtest_strategy_id` (B-tree)
- `idx_backtest_user_id` (B-tree)
- `idx_backtest_status` (B-tree)
- `idx_backtest_created_at` (B-tree)
- `idx_backtest_dates` (Composite: start_date, end_date)
- `idx_backtest_symbol` (B-tree)
- `idx_backtest_user_status` (Composite: user_id, status)
- `idx_backtest_user_created` (Composite: user_id, created_at)
- `idx_backtest_strategy_created` (Composite: strategy_id, created_at)

**外鍵約束**:
- `strategy_id` → `strategies.id` (ON DELETE CASCADE)
- `user_id` → `users.id` (ON DELETE CASCADE)

**Enum 定義**:
```python
class BacktestStatus(str, enum.Enum):
    PENDING = "PENDING"      # 待執行
    RUNNING = "RUNNING"      # 執行中
    COMPLETED = "COMPLETED"  # 已完成
    FAILED = "FAILED"        # 失敗
    CANCELLED = "CANCELLED"  # 已取消
```

**配額限制**:
- 每位使用者最多 200 個回測（`MAX_BACKTESTS_PER_USER`）
- 每個策略最多 50 個回測（`MAX_BACKTESTS_PER_STRATEGY`）

---

### 6. backtest_results（回測績效結果）

**用途**: 存儲回測執行後的績效指標

**主鍵**: `id` (Integer, Auto-increment)

**欄位列表**:

| 欄位名稱 | 資料型別 | 約束 | 說明 |
|---------|---------|------|------|
| `id` | Integer | PK, Index | 結果 ID |
| `backtest_id` | Integer | FK → backtests, Unique, Not Null | 回測 ID（一對一） |
| `total_return` | Numeric(10,4) | Nullable | 總報酬率（%） |
| `annual_return` | Numeric(10,4) | Nullable | 年化報酬率（%） |
| `final_portfolio_value` | Numeric(15,2) | Nullable | 最終資產淨值 |
| `sharpe_ratio` | Numeric(10,4) | Nullable | 夏普比率 |
| `max_drawdown` | Numeric(10,4) | Nullable | 最大回撤（%） |
| `volatility` | Numeric(10,4) | Nullable | 波動率（標準差） |
| `total_trades` | Integer | Nullable | 總交易次數 |
| `winning_trades` | Integer | Nullable | 獲利交易次數 |
| `losing_trades` | Integer | Nullable | 虧損交易次數 |
| `win_rate` | Numeric(10,4) | Nullable | 勝率（%） |
| `average_profit` | Numeric(15,2) | Nullable | 平均獲利 |
| `average_loss` | Numeric(15,2) | Nullable | 平均虧損 |
| `profit_factor` | Numeric(10,4) | Nullable | 獲利因子（總獲利/總虧損） |
| `sortino_ratio` | Numeric(10,4) | Nullable | 索提諾比率（進階） |
| `calmar_ratio` | Numeric(10,4) | Nullable | 卡瑪比率（進階） |
| `information_ratio` | Numeric(10,4) | Nullable | 信息比率（進階） |
| `created_at` | DateTime(TZ) | Not Null, Server Default | 建立時間 |
| `updated_at` | DateTime(TZ) | Not Null, Auto Update | 更新時間 |

**外鍵約束**:
- `backtest_id` → `backtests.id` (ON DELETE CASCADE, UNIQUE)

**資料完整性**:
- `backtest_id` 必須唯一（一個回測只有一個結果）
- 所有指標欄位允許 NULL（執行失敗或未計算時）

---

### 7. trades（交易記錄）

**用途**: 存儲回測過程中的每筆交易明細

**主鍵**: `id` (Integer, Auto-increment)

**欄位列表**:

| 欄位名稱 | 資料型別 | 約束 | 說明 |
|---------|---------|------|------|
| `id` | Integer | PK, Index | 交易 ID |
| `backtest_id` | Integer | FK → backtests, Not Null | 回測 ID |
| `stock_id` | String(10) | FK → stocks, Not Null | 股票代碼 |
| `date` | Date | Not Null | 交易日期 |
| `action` | Enum | Not Null | 動作（BUY/SELL） |
| `quantity` | Integer | Not Null | 交易數量（股數） |
| `price` | Numeric(10,2) | Not Null | 交易價格 |
| `commission` | Numeric(10,2) | Not Null, Default=0 | 手續費 |
| `tax` | Numeric(10,2) | Not Null, Default=0 | 交易稅 |
| `total_amount` | Numeric(15,2) | Not Null | 交易總額 |
| `profit_loss` | Numeric(15,2) | Nullable | 獲利/虧損（僅 SELL 計算） |
| `created_at` | DateTime(TZ) | Not Null, Server Default | 建立時間 |

**索引**:
- `idx_trade_backtest_id` (B-tree)
- `idx_trade_stock_id` (B-tree)
- `idx_trade_date` (B-tree)
- `idx_trade_backtest_date` (Composite: backtest_id, date)

**外鍵約束**:
- `backtest_id` → `backtests.id` (ON DELETE CASCADE)
- `stock_id` → `stocks.stock_id` (ON DELETE CASCADE)

**Enum 定義**:
```python
class TradeAction(str, enum.Enum):
    BUY = "BUY"      # 買入
    SELL = "SELL"    # 賣出
```

**資料生成**: 由 Backtrader 引擎自動生成

---

### 8. fundamental_data（財務指標數據）

**用途**: 存儲股票的財務指標歷史數據（季度/年度）

**主鍵**: `id` (Integer, Auto-increment)

**欄位列表**:

| 欄位名稱 | 資料型別 | 約束 | 說明 |
|---------|---------|------|------|
| `id` | Integer | PK, Index | 記錄 ID |
| `stock_id` | String(10) | Not Null, Index | 股票代碼 |
| `indicator` | String(50) | Not Null, Index | 財務指標名稱 |
| `date` | String(20) | Not Null | 數據日期（季度字串，如 "2024-Q4"） |
| `value` | Float | Nullable | 指標數值 |
| `created_at` | DateTime(TZ) | Server Default | 建立時間 |
| `updated_at` | DateTime(TZ) | Auto Update | 更新時間 |

**索引**:
- `ix_stock_indicator` (Composite: stock_id, indicator)
- `ix_indicator_date` (Composite: indicator, date)

**唯一約束**:
- `uix_stock_indicator_date` (Unique: stock_id, indicator, date)
  - 確保同一股票、同一指標、同一日期只有一筆記錄

**重要注意事項**:
- ⚠️ `date` 欄位使用**季度字串**格式（如 "2024-Q4"），**不是**日期型別
- 查詢時必須使用字串匹配：`WHERE date = '2024-Q4'`
- 不可使用日期比較：`WHERE date >= CURRENT_DATE` ❌

**支援的財務指標** (18 個):
1. `ROE稅後` - 股東權益報酬率
2. `ROA稅後息前` - 資產報酬率
3. `ROA稅後息前營業利益` - 營業資產報酬率
4. `營業毛利率` - 毛利率
5. `營業利益率` - 營業利益率
6. `稅後淨利率` - 淨利率
7. `每股稅後淨利` - EPS
8. `營收成長率` - 營收 YoY
9. `營業毛利成長率` - 毛利 YoY
10. `營業利益成長率` - 營業利益 YoY
11. `稅後淨利成長率` - 淨利 YoY
12. `總資產成長率` - 資產擴張
13. `負債比率` - 財務槓桿
14. `流動比率` - 短期償債能力
15. `速動比率` - 立即償債能力
16. `應收帳款週轉率` - 收款效率
17. `存貨週轉率` - 庫存管理
18. `總資產週轉率` - 資產使用效率

**資料來源**: FinLab API `fundamental_features()`

**當前狀態**:
- 總記錄數: 1,880,982 筆
- 資料表大小: 435 MB（最大資料表）
- 季度覆蓋: 51 個季度（2013-Q1 至 2025-Q3）

---

### 9. industries（產業分類 - TWSE）

**用途**: 存儲台證所 3 層階層式產業分類

**主鍵**: `id` (Integer, Auto-increment)

**欄位列表**:

| 欄位名稱 | 資料型別 | 約束 | 說明 |
|---------|---------|------|------|
| `id` | Integer | PK, Index | 產業 ID |
| `code` | String(20) | Unique, Not Null, Index | 產業代碼（如 "M15"） |
| `name_zh` | String(100) | Not Null | 中文名稱 |
| `name_en` | String(100) | Nullable | 英文名稱 |
| `parent_code` | String(20) | FK → industries.code | 父產業代碼 |
| `level` | Integer | Default=1 | 產業層級（1=大類, 2=中類, 3=小類） |
| `description` | Text | Nullable | 產業描述 |
| `created_at` | DateTime(TZ) | Server Default | 建立時間 |
| `updated_at` | DateTime(TZ) | Auto Update | 更新時間 |

**外鍵約束**:
- `parent_code` → `industries.code` (Self-referencing, NO ACTION)

**階層結構範例**:
```
M00 其他
├── M15 建材營造 (Level 1)
│   ├── M1500 水泥工業 (Level 2)
│   └── M1501 玻璃陶瓷 (Level 2)
└── M16 航運業 (Level 1)
    ├── M1600 航運業 (Level 2)
    └── M1601 觀光事業 (Level 2)
```

**資料來源**: FinLab `company_basic_info` 的「產業類別」欄位

**當前狀態**:
- 總產業數: 41 個
- 資料表大小: 64 KB

---

### 10. stock_industries（股票-產業映射）

**用途**: 多對多關聯表，連接股票與產業

**主鍵**: `id` (Integer, Auto-increment)

**欄位列表**:

| 欄位名稱 | 資料型別 | 約束 | 說明 |
|---------|---------|------|------|
| `id` | Integer | PK, Index | 映射 ID |
| `stock_id` | String(10) | FK → stocks, Not Null | 股票代碼 |
| `industry_code` | String(20) | FK → industries, Not Null | 產業代碼 |
| `is_primary` | Boolean | Default=False | 是否為主要產業 |
| `created_at` | DateTime(TZ) | Server Default | 建立時間 |

**外鍵約束**:
- `stock_id` → `stocks.stock_id` (NO ACTION)
- `industry_code` → `industries.code` (NO ACTION)

**唯一約束**:
- `uix_stock_industry` (Unique: stock_id, industry_code)
  - 防止重複映射

**當前狀態**:
- 總映射數: 1,935 筆
- 覆蓋率: 72.5% (1,935 / 2,671)
- 資料表大小: 360 KB

**資料匯入**: 使用 `backend/scripts/import_industries.py`

---

### 11. industry_metrics_cache（產業指標快取）

**用途**: 快取產業聚合指標計算結果

**主鍵**: `id` (Integer, Auto-increment)

**欄位列表**:

| 欄位名稱 | 資料型別 | 約束 | 說明 |
|---------|---------|------|------|
| `id` | Integer | PK, Index | 快取 ID |
| `industry_code` | String(20) | FK → industries, Not Null | 產業代碼 |
| `date` | Date | Not Null | 數據日期 |
| `metric_name` | String(50) | Not Null | 指標名稱（如 "avg_roe"） |
| `value` | Numeric | Nullable | 指標值 |
| `stocks_count` | Integer | Nullable | 計算基礎的股票數量 |
| `created_at` | DateTime(TZ) | Server Default | 建立時間 |

**索引**:
- `ix_industry_metrics_code_date` (Composite: industry_code, date)
- `ix_industry_metrics_name` (B-tree on metric_name)

**唯一約束**:
- `uix_industry_metric` (Unique: industry_code, date, metric_name)

**外鍵約束**:
- `industry_code` → `industries.code` (NO ACTION)

**快取策略**:
- TTL: 30 天
- 自動更新: 每次呼叫 `/api/v1/industry/{code}/metrics` 時檢查

**支援的聚合指標**:
1. `avg_roe` - 平均 ROE
2. `avg_roa` - 平均 ROA
3. `avg_gross_margin` - 平均毛利率
4. `avg_operating_margin` - 平均營業利益率
5. `avg_eps` - 平均 EPS
6. `avg_revenue_growth` - 平均營收成長率
7. `avg_profit_growth` - 平均淨利成長率

---

### 12. industry_chains（FinMind 產業鏈）

**用途**: 存儲 FinMind API 的產業鏈分類

**主鍵**: `id` (Integer, Auto-increment)

**欄位列表**:

| 欄位名稱 | 資料型別 | 約束 | 說明 |
|---------|---------|------|------|
| `id` | Integer | PK, Index | 產業鏈 ID |
| `chain_name` | String(100) | Unique, Not Null, Index | 產業鏈名稱 |
| `description` | String(500) | Nullable | 產業鏈描述 |
| `created_at` | DateTime | Default=utcnow | 建立時間 |
| `updated_at` | DateTime | Default=utcnow, Auto Update | 更新時間 |

**資料來源**: FinMind API `TaiwanStockIndustryChain`（需付費會員）

**當前狀態**: 資料表已建立，待同步資料

---

### 13. stock_industry_chains（股票-FinMind 產業鏈映射）

**用途**: 連接股票與 FinMind 產業鏈

**主鍵**: `id` (Integer, Auto-increment)

**欄位列表**:

| 欄位名稱 | 資料型別 | 約束 | 說明 |
|---------|---------|------|------|
| `id` | Integer | PK, Index | 映射 ID |
| `stock_id` | String(10) | Not Null, Index | 股票代碼 |
| `chain_name` | String(100) | FK → industry_chains, Not Null | 產業鏈名稱 |
| `is_primary` | Boolean | Default=False | 是否為主要產業鏈 |
| `created_at` | DateTime | Default=utcnow | 建立時間 |
| `updated_at` | DateTime | Default=utcnow, Auto Update | 更新時間 |

**外鍵約束**:
- `chain_name` → `industry_chains.chain_name` (NO ACTION)

**唯一約束**:
- `uix_stock_chain` (Unique: stock_id, chain_name)

---

### 14. custom_industry_categories（自定義產業分類）

**用途**: 允許使用者建立自訂產業分類

**主鍵**: `id` (Integer, Auto-increment)

**欄位列表**:

| 欄位名稱 | 資料型別 | 約束 | 說明 |
|---------|---------|------|------|
| `id` | Integer | PK, Index | 分類 ID |
| `user_id` | Integer | FK → users, Not Null | 創建者 ID |
| `category_name` | String(100) | Not Null, Index | 分類名稱 |
| `description` | String(500) | Nullable | 分類描述 |
| `parent_id` | Integer | FK → custom_industry_categories | 父分類 ID |
| `created_at` | DateTime | Default=utcnow | 建立時間 |
| `updated_at` | DateTime | Default=utcnow, Auto Update | 更新時間 |

**外鍵約束**:
- `user_id` → `users.id` (NO ACTION)
- `parent_id` → `custom_industry_categories.id` (Self-referencing, NO ACTION)

**唯一約束**:
- `uix_user_category` (Unique: user_id, category_name)
  - 同一使用者不能建立重複名稱的分類

**功能**: 支援階層結構（類似 TWSE 分類）

---

### 15. stock_custom_categories（股票-自定義分類映射）

**用途**: 連接股票與使用者自定義分類

**主鍵**: `id` (Integer, Auto-increment)

**欄位列表**:

| 欄位名稱 | 資料型別 | 約束 | 說明 |
|---------|---------|------|------|
| `id` | Integer | PK, Index | 映射 ID |
| `category_id` | Integer | FK → custom_industry_categories, Not Null | 分類 ID |
| `stock_id` | String(10) | Not Null, Index | 股票代碼 |
| `created_at` | DateTime | Default=utcnow | 建立時間 |

**外鍵約束**:
- `category_id` → `custom_industry_categories.id` (NO ACTION)

**唯一約束**:
- `uix_category_stock` (Unique: category_id, stock_id)

---

### 16. alembic_version（Alembic 遷移版本）

**用途**: 追蹤資料庫 schema 版本

**主鍵**: `version_num` (String, Primary Key)

**欄位列表**:

| 欄位名稱 | 資料型別 | 約束 | 說明 |
|---------|---------|------|------|
| `version_num` | String(32) | PK | 當前遷移版本號 |

**當前版本**: `3f228b8913bf`（加密 FinLab API Tokens）

---

## 關聯關係圖

### 核心關聯流程

```
users (1) ─────────────┬─────────── (N) strategies
                       │                    │ (1)
                       │                    │
                       │                    ▼ (N)
                       └─────────────────── backtests
                                             │ (1)
                                             ├───────── (1) backtest_results
                                             │
                                             └───────── (N) trades ──── (N) stocks
                                                                              │ (1)
                                                                              ▼ (N)
                                                                         stock_prices
```

### 產業分類關聯

```
industries (TWSE 3-層階層)
    │ (1)
    ▼ (N)
stock_industries ──────── (N) stocks
    │ (N)                      │ (1)
    │                          ▼ (N)
    └──────────────────── industry_chains (FinMind)
                               │ (1)
                               ▼ (N)
                          stock_industry_chains
```

### 自定義分類

```
users (1) ───────── (N) custom_industry_categories (階層)
                              │ (1)
                              ▼ (N)
                        stock_custom_categories ──── (N) stocks
```

### 外鍵級聯刪除規則

| 父資料表 | 子資料表 | 刪除規則 | 說明 |
|---------|---------|---------|------|
| `users` | `strategies` | CASCADE | 刪除使用者時刪除所有策略 |
| `users` | `backtests` | CASCADE | 刪除使用者時刪除所有回測 |
| `strategies` | `backtests` | CASCADE | 刪除策略時刪除所有回測 |
| `backtests` | `backtest_results` | CASCADE | 刪除回測時刪除結果 |
| `backtests` | `trades` | CASCADE | 刪除回測時刪除交易記錄 |
| `stocks` | `stock_prices` | CASCADE | 刪除股票時刪除價格數據 |
| `stocks` | `trades` | CASCADE | 刪除股票時刪除交易記錄 |
| `stocks` | `stock_industries` | CASCADE | 刪除股票時刪除產業映射 |
| `industries` | `stock_industries` | NO ACTION | 保護產業分類（不允許刪除已有映射的產業） |
| `industries` | `industry_metrics_cache` | NO ACTION | 保護產業分類 |

---

## 索引策略

### 索引分類

#### 1. 主鍵索引（Primary Key）
- 所有資料表的 `id` 或複合主鍵（自動建立）
- `stock_prices`: 複合主鍵 (stock_id, date)

#### 2. 唯一索引（Unique）
- `users.email`, `users.username`
- `stocks.stock_id`
- `industries.code`
- `fundamental_data`: (stock_id, indicator, date)
- `stock_industries`: (stock_id, industry_code)
- `industry_metrics_cache`: (industry_code, date, metric_name)

#### 3. 外鍵索引（Foreign Key）
- 所有 `user_id`, `strategy_id`, `backtest_id`, `stock_id` 欄位
- 自動優化 JOIN 查詢

#### 4. 複合索引（Composite）
- `strategies`:
  - (user_id, status) - 查詢使用者特定狀態的策略
  - (user_id, created_at) - 時間排序
- `backtests`:
  - (user_id, status) - 查詢使用者特定狀態的回測
  - (user_id, created_at) - 時間排序
  - (strategy_id, created_at) - 策略回測歷史
  - (start_date, end_date) - 日期範圍查詢
  - (backtest_id, date) - 交易記錄時間序列
- `fundamental_data`:
  - (stock_id, indicator) - 特定股票的指標查詢
  - (indicator, date) - 跨股票的指標比較

#### 5. GIN 索引（Generalized Inverted Index）
- `strategies.name` with `pg_trgm` - 支援模糊搜尋（ILIKE）
  ```sql
  -- 優化模糊搜尋查詢
  SELECT * FROM strategies WHERE name ILIKE '%均線%';
  ```

#### 6. TimescaleDB 專用索引
- `stock_prices` 的 hypertable 自動建立時間分區索引
- 針對時間範圍查詢優化

### 索引維護

**檢查索引使用率**:
```sql
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan ASC;
```

**重建索引**（如果碎片化）:
```sql
REINDEX TABLE strategies;
REINDEX INDEX idx_strategy_name_gin;
```

---

## 遷移歷史

### Alembic 遷移時間線

| 版本號 | 日期 | 說明 | 影響資料表 |
|-------|------|------|-----------|
| `705ff3e322a0` | 2025-12-01 | 建立 users 資料表 | `users` |
| `430c1561c808` | 2025-12-01 | 建立股票、策略、回測相關資料表 | `stocks`, `stock_prices`, `strategies`, `backtests`, `backtest_results`, `trades` |
| `0aa53eea675e` | 2025-12-01 | 啟用 TimescaleDB hypertable | `stock_prices` |
| `3c968b93aa95` | 2025-12-01 | 新增 `symbol` 欄位到 backtests | `backtests` |
| `3d0286303367` | 2025-12-01 | 新增 `parameters` 欄位到 backtests | `backtests` |
| `39969e96e640` | 2025-12-02 | 新增效能索引（複合索引、GIN 索引） | `strategies`, `backtests` |
| `26c9e76d37e8` | 2025-12-03 | 建立財務指標資料表 | `fundamental_data` |
| `73ff25835cf5` | 2025-12-03 | 建立產業分類資料表 | `industries`, `stock_industries`, `industry_metrics_cache` |
| `4f097a9131f3` | 2025-12-03 | 建立 FinMind 產業鏈與自定義分類 | `industry_chains`, `stock_industry_chains`, `custom_industry_categories`, `stock_custom_categories` |
| `3f228b8913bf` | 2025-12-04 | 加密 FinLab API Tokens | `users` (新增 `finlab_api_token` 欄位) |

### 遷移檢查指令

```bash
# 查看當前版本
docker compose exec backend alembic current

# 查看遷移歷史
docker compose exec backend alembic history

# 升級到最新版本
docker compose exec backend alembic upgrade head

# 回滾到上一版本
docker compose exec backend alembic downgrade -1

# 回滾到特定版本
docker compose exec backend alembic downgrade 705ff3e322a0
```

---

## 資料完整性約束

### 1. 主鍵約束（Primary Key）
- 確保每筆記錄唯一性
- 所有資料表都有主鍵

### 2. 外鍵約束（Foreign Key）
- 總計 15 個外鍵關係
- 7 個使用 CASCADE DELETE（核心業務流程）
- 8 個使用 NO ACTION（保護參考資料）

### 3. 唯一約束（Unique Constraint）
- `users`: email, username
- `stocks`: stock_id
- `industries`: code
- `fundamental_data`: (stock_id, indicator, date)
- `stock_industries`: (stock_id, industry_code)
- `industry_metrics_cache`: (industry_code, date, metric_name)
- `stock_industry_chains`: (stock_id, chain_name)
- `custom_industry_categories`: (user_id, category_name)
- `stock_custom_categories`: (category_id, stock_id)

### 4. NOT NULL 約束
- 關鍵欄位（如 email, username, code, price 等）強制非空
- 績效指標允許 NULL（執行失敗或未計算時）

### 5. 預設值（Default Values）
- `users.is_active`: True
- `users.is_superuser`: False
- `strategies.status`: 'draft'
- `backtests.status`: 'PENDING'
- `backtests.initial_capital`: 1000000
- 時間戳記使用 `func.now()` 自動填入

### 6. CHECK 約束（應用層實作）
- 策略配額: 每位使用者 ≤ 50 個策略
- 回測配額: 每位使用者 ≤ 200 個回測，每個策略 ≤ 50 個回測
- 回測日期: `end_date >= start_date`（在 Service 層驗證）
- 數值範圍: `initial_capital > 0`（在 Schema 層驗證）

---

## 效能優化

### 1. TimescaleDB 優化

**Hypertable 配置**:
```sql
-- stock_prices 已轉換為 hypertable
SELECT * FROM timescaledb_information.hypertables;
```

**壓縮策略**:
- 數據 > 30 天自動壓縮
- 壓縮率: 約 70-90%
- 查詢效能: 幾乎無影響

**查詢優化範例**:
```sql
-- ✅ 優化：使用時間分區
SELECT * FROM stock_prices
WHERE stock_id = '2330'
  AND date >= '2024-01-01'
  AND date < '2024-12-31';

-- ❌ 避免：跨分區的大範圍查詢
SELECT * FROM stock_prices
WHERE date >= '2000-01-01';  -- 會掃描所有分區
```

### 2. 索引優化

**避免索引失效**:
```sql
-- ✅ 正確：使用索引
SELECT * FROM strategies WHERE user_id = 1 AND status = 'active';

-- ❌ 錯誤：函數包裹欄位，索引失效
SELECT * FROM strategies WHERE LOWER(name) = 'test';

-- ✅ 正確：使用 GIN 索引模糊搜尋
SELECT * FROM strategies WHERE name ILIKE '%均線%';
```

### 3. JOIN 優化

**N+1 查詢修復**:
```python
# ❌ N+1 問題
backtests = db.query(Backtest).all()
for bt in backtests:
    print(bt.strategy.name)  # 每次迴圈執行一次 SQL

# ✅ 使用 joinedload
backtests = db.query(Backtest).options(
    joinedload(Backtest.strategy)
).all()
```

### 4. 批次操作

**批次插入財務數據**:
```python
# ✅ 批次插入（每批 1000 筆）
db.bulk_insert_mappings(FundamentalData, records)
db.commit()

# ❌ 單筆插入
for record in records:
    db.add(FundamentalData(**record))
    db.commit()  # 每次都 commit
```

### 5. Redis 快取

**快取策略**:
- 股票清單: 24 小時
- 每日價格: 10 分鐘
- 最新價格: 5 分鐘
- 產業指標: 30 天

**快取鍵命名規範**:
```
stock_list           # 股票清單
price:{stock_id}     # 歷史價格
latest:{stock_id}    # 最新價格
industry:{code}      # 產業指標
```

### 6. 查詢優化建議

**避免 SELECT ***:
```sql
-- ✅ 只選擇需要的欄位
SELECT id, name, status FROM strategies WHERE user_id = 1;

-- ❌ 選擇所有欄位（包括大型 Text 欄位）
SELECT * FROM strategies WHERE user_id = 1;
```

**使用分頁**:
```sql
-- ✅ 使用 LIMIT/OFFSET
SELECT * FROM backtests
ORDER BY created_at DESC
LIMIT 20 OFFSET 0;
```

### 7. 資料庫連線池

**SQLAlchemy 配置**:
```python
# backend/app/db/session.py
engine = create_engine(
    DATABASE_URL,
    pool_size=20,          # 連線池大小
    max_overflow=10,       # 最大溢出連線
    pool_timeout=30,       # 等待超時
    pool_recycle=3600,     # 連線回收時間（1 小時）
)
```

---

## 新增資料表指南

### 步驟 1: 建立 SQLAlchemy Model

**檔案位置**: `backend/app/models/your_model.py`

**模板**:
```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class YourModel(Base):
    """模型說明"""
    __tablename__ = "your_table"

    # 主鍵
    id = Column(Integer, primary_key=True, index=True)

    # 外鍵（如果需要）
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # 資料欄位
    name = Column(String(100), nullable=False, comment="名稱")
    value = Column(Integer, nullable=True, comment="數值")

    # 時間戳記（標準欄位）
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="your_models")

    # 索引
    __table_args__ = (
        Index('idx_your_table_user_id', 'user_id'),
        Index('idx_your_table_name', 'name'),
    )

    def __repr__(self):
        return f"<YourModel(id={self.id}, name={self.name})>"
```

### 步驟 2: 註冊模型到 Base

**檔案**: `backend/app/db/base.py`

```python
def import_models():
    from app.models.user import User  # noqa: F401
    # ... 其他模型
    from app.models.your_model import YourModel  # noqa: F401  # 新增這行
```

### 步驟 3: 建立 Alembic 遷移

```bash
# 自動生成遷移檔案
docker compose exec backend alembic revision --autogenerate -m "add your_table"

# 檢查生成的遷移檔案
cat backend/alembic/versions/{新版本號}_add_your_table.py
```

### 步驟 4: 檢查遷移檔案

**手動審查**:
- ✅ 檢查 `upgrade()` 函數是否正確
- ✅ 檢查 `downgrade()` 函數是否可回滾
- ✅ 檢查外鍵約束的 `ondelete` 規則
- ✅ 檢查索引是否完整
- ✅ 檢查預設值是否正確

**常見問題修正**:
```python
# ❌ Alembic 可能漏掉的索引
def upgrade():
    op.create_table('your_table', ...)
    # 手動加入複合索引
    op.create_index('idx_your_table_user_created', 'your_table', ['user_id', 'created_at'])
```

### 步驟 5: 執行遷移

```bash
# 執行遷移
docker compose exec backend alembic upgrade head

# 驗證資料表已建立
docker compose exec postgres psql -U quantlab quantlab -c "\d your_table"

# 檢查外鍵
docker compose exec postgres psql -U quantlab quantlab -c "\d+ your_table"
```

### 步驟 6: 建立 Repository 層

**檔案**: `backend/app/repositories/your_model.py`

```python
from sqlalchemy.orm import Session
from app.models.your_model import YourModel
from app.schemas.your_model import YourModelCreate

class YourModelRepository:
    def create(self, db: Session, user_id: int, obj_create: YourModelCreate) -> YourModel:
        obj = YourModel(user_id=user_id, **obj_create.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def get_by_id(self, db: Session, obj_id: int) -> YourModel | None:
        return db.query(YourModel).filter(YourModel.id == obj_id).first()
```

### 步驟 7: 建立 Schema

**檔案**: `backend/app/schemas/your_model.py`

```python
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class YourModelBase(BaseModel):
    name: str
    value: int | None = None

class YourModelCreate(YourModelBase):
    pass

class YourModelUpdate(BaseModel):
    name: str | None = None
    value: int | None = None

class YourModel(YourModelBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### 步驟 8: 更新此報告

**必須更新**:
- [資料表結構詳細說明](#資料表結構詳細說明) - 新增資料表文檔
- [關聯關係圖](#關聯關係圖) - 更新 ER 圖
- [索引策略](#索引策略) - 記錄新增的索引
- [遷移歷史](#遷移歷史) - 記錄新的遷移版本

---

## 備份與維護

### 自動備份

**使用自動化腳本**:
```bash
# 完整資料庫備份
./scripts/backup_database.sh

# 產業分類資料備份
./scripts/backup_industries.sh
```

**Cron 設定** (建議每日凌晨 2:00):
```cron
0 2 * * * /data/CCTest/QuantLab/scripts/backup_database.sh
```

### 手動備份

**完整備份**:
```bash
# 備份所有資料
docker compose exec -T postgres pg_dump -U quantlab quantlab | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# 僅備份 schema（不含數據）
docker compose exec -T postgres pg_dump -U quantlab quantlab --schema-only | gzip > schema_backup.sql.gz
```

**特定資料表備份**:
```bash
# 備份產業分類相關資料表
docker compose exec -T postgres pg_dump -U quantlab quantlab \
  -t industries \
  -t stock_industries \
  -t industry_metrics_cache \
  | gzip > industries_backup.sql.gz

# 備份使用者與策略
docker compose exec -T postgres pg_dump -U quantlab quantlab \
  -t users \
  -t strategies \
  | gzip > users_strategies_backup.sql.gz
```

### 還原備份

```bash
# 還原完整備份
gunzip < backup_20251205_020000.sql.gz | docker compose exec -T postgres psql -U quantlab quantlab

# 還原特定資料表（先刪除現有資料）
docker compose exec -T postgres psql -U quantlab quantlab -c "TRUNCATE industries CASCADE;"
gunzip < industries_backup.sql.gz | docker compose exec -T postgres psql -U quantlab quantlab
```

### 定期維護任務

**每日**:
- ✅ 自動備份（2:00 AM）
- ✅ 清理過期快取（Celery 任務 3:00 AM）

**每週**:
```bash
# 分析資料表統計資訊（週日凌晨）
docker compose exec postgres psql -U quantlab quantlab -c "ANALYZE;"

# 檢查資料表大小成長
docker compose exec postgres psql -U quantlab quantlab -c "
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

**每月**:
```bash
# VACUUM ANALYZE（重整資料表，回收空間）
docker compose exec postgres psql -U quantlab quantlab -c "VACUUM ANALYZE;"

# 重建索引（如果發現效能下降）
docker compose exec postgres psql -U quantlab quantlab -c "REINDEX DATABASE quantlab;"

# 檢查索引使用率
docker compose exec postgres psql -U quantlab quantlab -c "
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan ASC
LIMIT 20;
"
```

---

## 資料驗證清單

### 新增資料前檢查

#### 1. 外鍵存在性驗證

```sql
-- 檢查股票是否存在（新增 stock_prices 前）
SELECT stock_id FROM stocks WHERE stock_id = '2330';

-- 檢查使用者是否存在（新增 strategy 前）
SELECT id FROM users WHERE id = 1;

-- 檢查產業代碼是否存在（新增 stock_industries 前）
SELECT code FROM industries WHERE code = 'M15';
```

#### 2. 唯一約束驗證

```sql
-- 檢查股票-產業映射是否已存在
SELECT * FROM stock_industries
WHERE stock_id = '2330' AND industry_code = 'M15';

-- 檢查財務數據是否已存在
SELECT * FROM fundamental_data
WHERE stock_id = '2330' AND indicator = 'ROE稅後' AND date = '2024-Q4';
```

#### 3. 日期格式驗證

```python
# ✅ 正確：fundamental_data 使用季度字串
date = "2024-Q4"

# ❌ 錯誤：使用日期物件
date = datetime.now()  # 會轉成 "2025-12-05"，無法匹配季度數據
```

### 資料完整性檢查

#### 1. 孤兒記錄檢查

```sql
-- 檢查沒有對應股票的價格數據
SELECT DISTINCT sp.stock_id
FROM stock_prices sp
LEFT JOIN stocks s ON sp.stock_id = s.stock_id
WHERE s.stock_id IS NULL;

-- 檢查沒有對應回測的交易記錄
SELECT DISTINCT t.backtest_id
FROM trades t
LEFT JOIN backtests b ON t.backtest_id = b.id
WHERE b.id IS NULL;
```

#### 2. 產業映射覆蓋率

```sql
-- 檢查未映射到產業的股票
SELECT s.stock_id, s.name
FROM stocks s
LEFT JOIN stock_industries si ON s.stock_id = si.stock_id
WHERE si.id IS NULL
ORDER BY s.stock_id;

-- 計算覆蓋率
SELECT
    (SELECT COUNT(DISTINCT stock_id) FROM stock_industries) * 100.0 /
    (SELECT COUNT(*) FROM stocks) AS coverage_percentage;
```

#### 3. 資料一致性檢查

```sql
-- 檢查回測結果與交易記錄一致性
SELECT b.id, b.name,
       br.total_trades AS result_trades,
       (SELECT COUNT(*) FROM trades WHERE backtest_id = b.id) AS actual_trades
FROM backtests b
LEFT JOIN backtest_results br ON b.id = br.backtest_id
WHERE br.total_trades IS NOT NULL
  AND br.total_trades != (SELECT COUNT(*) FROM trades WHERE backtest_id = b.id);

-- 檢查策略與回測的使用者一致性
SELECT b.id, b.name, b.user_id AS backtest_user, s.user_id AS strategy_user
FROM backtests b
JOIN strategies s ON b.strategy_id = s.id
WHERE b.user_id != s.user_id;
```

#### 4. 財務數據季度連續性

```sql
-- 檢查特定股票的季度數據是否連續
SELECT stock_id, indicator, date
FROM fundamental_data
WHERE stock_id = '2330'
  AND indicator = 'ROE稅後'
ORDER BY date;

-- 統計每個股票有多少季度的數據
SELECT stock_id, COUNT(DISTINCT date) AS quarters_count
FROM fundamental_data
WHERE indicator = 'ROE稅後'
GROUP BY stock_id
ORDER BY quarters_count DESC;
```

### 效能檢查

#### 1. 慢查詢檢測

```sql
-- 檢查最慢的查詢（需啟用 pg_stat_statements）
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY mean_exec_time DESC
LIMIT 10;
```

#### 2. 資料表膨脹檢查

```sql
-- 檢查資料表 dead tuples 比例
SELECT
    schemaname,
    tablename,
    n_live_tup,
    n_dead_tup,
    ROUND(n_dead_tup * 100.0 / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_ratio
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY dead_ratio DESC;
```

#### 3. TimescaleDB 壓縮狀態

```sql
-- 檢查 stock_prices 的壓縮情況
SELECT
    chunk_schema,
    chunk_name,
    compression_status,
    compressed_total_bytes,
    uncompressed_total_bytes,
    ROUND(100.0 * compressed_total_bytes / NULLIF(uncompressed_total_bytes, 0), 2) AS compression_ratio
FROM timescaledb_information.compressed_chunk_stats
ORDER BY compression_ratio;
```

---

## 附錄

### A. 常用 SQL 查詢

**查看資料庫大小**:
```sql
SELECT pg_size_pretty(pg_database_size('quantlab'));
```

**查看連線數**:
```sql
SELECT COUNT(*) FROM pg_stat_activity WHERE datname = 'quantlab';
```

**殺掉閒置連線**:
```sql
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'quantlab'
  AND state = 'idle'
  AND state_change < NOW() - INTERVAL '1 hour';
```

**查看鎖定狀態**:
```sql
SELECT
    pid,
    usename,
    pg_blocking_pids(pid) AS blocked_by,
    query AS blocked_query
FROM pg_stat_activity
WHERE cardinality(pg_blocking_pids(pid)) > 0;
```

### B. 疑難排解

**問題: 遷移失敗**
```bash
# 檢查當前版本
docker compose exec backend alembic current

# 標記為特定版本（不執行 SQL）
docker compose exec backend alembic stamp head

# 手動修復後重新遷移
docker compose exec backend alembic upgrade head
```

**問題: TimescaleDB Hypertable 無法刪除**
```sql
-- 先移除壓縮策略
SELECT remove_compression_policy('stock_prices', if_exists => TRUE);

-- 將 hypertable 轉回普通資料表（需重建）
DROP TABLE stock_prices CASCADE;
-- 然後重新遷移
```

**問題: 外鍵約束違反**
```sql
-- 檢查哪些記錄違反外鍵
SELECT sp.stock_id
FROM stock_prices sp
LEFT JOIN stocks s ON sp.stock_id = s.stock_id
WHERE s.stock_id IS NULL;

-- 刪除孤兒記錄
DELETE FROM stock_prices
WHERE stock_id NOT IN (SELECT stock_id FROM stocks);
```

### C. 參考資料

- [PostgreSQL 官方文檔](https://www.postgresql.org/docs/15/)
- [TimescaleDB 文檔](https://docs.timescale.com/)
- [SQLAlchemy 2.0 文檔](https://docs.sqlalchemy.org/en/20/)
- [Alembic 文檔](https://alembic.sqlalchemy.org/)
- [FinLab API 文檔](https://ai.finlab.tw/)

---

## 文檔維護

**最後更新**: 2025-12-05
**下次審查日期**: 2026-01-05（每月一次）
**負責人**: Database Team

**變更記錄**:
- 2025-12-05: 初始版本建立（v1.0）
  - 記錄所有 16 個資料表結構
  - 記錄 10 個遷移版本
  - 建立完整的索引策略文檔
  - 建立資料驗證清單

**待辦事項**:
- [ ] 新增資料字典（每個欄位的詳細說明）
- [ ] 建立 ER 圖視覺化（使用 dbdiagram.io 或 draw.io）
- [ ] 記錄典型查詢範例與效能基準
- [ ] 建立災難復原計畫（DR Plan）
- [ ] 設定監控告警（資料表大小、查詢效能、連線數）

---

**重要提醒**:

1. ⚠️ 任何 schema 變更（新增/修改資料表）都必須更新此文檔
2. ⚠️ 新增遷移後，必須在「遷移歷史」章節記錄
3. ⚠️ 效能問題必須記錄在「效能優化」章節
4. ⚠️ 資料完整性問題必須更新「資料驗證清單」
5. ⚠️ 每月定期審查此文檔，確保與實際資料庫一致

---

**緊急聯絡資訊**:
- 資料庫問題: 查看 `DATABASE_MAINTENANCE.md`
- 備份還原: 查看 `scripts/backup_database.sh`
- Alembic 遷移: 查看 `CLAUDE.md` 的「資料庫管理」章節
