# QuantLab 資料庫 ER 圖

## 視覺化工具

此 ER 圖可使用以下工具視覺化：
- [dbdiagram.io](https://dbdiagram.io/) - 線上 ER 圖工具
- [draw.io](https://app.diagrams.net/) - 通用圖表工具
- DBeaver - 資料庫管理工具（可自動生成 ER 圖）

---

## 核心業務流程

### 使用者 → 策略 → 回測 → 結果/交易

```
┌─────────────┐
│    users    │ 使用者資料表
│  (PK: id)   │
└──────┬──────┘
       │ 1
       │
       │ N
┌──────▼──────────┐
│   strategies    │ 交易策略
│  (PK: id)       │
│  FK: user_id    │ CASCADE DELETE (刪除使用者時刪除策略)
└──────┬──────────┘
       │ 1
       │
       │ N
┌──────▼──────────┐
│   backtests     │ 回測配置
│  (PK: id)       │
│  FK: strategy_id│ CASCADE DELETE (刪除策略時刪除回測)
│  FK: user_id    │ CASCADE DELETE (刪除使用者時刪除回測)
└──────┬──────────┘
       │ 1
       ├──────────────────────┐
       │ 1                    │ N
       │                      │
┌──────▼──────────────┐  ┌───▼──────┐
│ backtest_results    │  │  trades  │ 交易記錄
│  (PK: id)           │  │ (PK: id) │
│  FK: backtest_id    │  │ FK: backtest_id │ CASCADE DELETE
│  (UNIQUE)           │  │ FK: stock_id    │ CASCADE DELETE
└─────────────────────┘  └───┬──────┘
                             │ N
                             │
                             │ 1
                        ┌────▼─────┐
                        │  stocks  │ 股票基本資料
                        │(PK:stock_id)│
                        └──────────┘
```

**關鍵說明**:
- 1 個使用者可有多個策略（1:N）
- 1 個策略可有多個回測（1:N）
- 1 個回測有 1 個結果（1:1）
- 1 個回測有多筆交易（1:N）
- 多筆交易關聯到 1 個股票（N:1）

---

## 股票與價格數據

### 股票 → 歷史價格（TimescaleDB Hypertable）

```
┌──────────────┐
│   stocks     │ 股票基本資料（2,671 檔）
│(PK:stock_id) │ - stock_id (String): "2330", "2317"...
│              │ - name: "台積電", "鴻海"...
│              │ - category: 產業分類
│              │ - market: 上市/上櫃/興櫃
└──────┬───────┘
       │ 1
       │
       │ N
┌──────▼──────────────────┐
│   stock_prices          │ OHLCV 時序數據（TimescaleDB）
│(PK:stock_id,date)       │
│ FK: stock_id            │ CASCADE DELETE
│                         │
│ Hypertable 配置:        │
│ - Partition by: date    │
│ - Chunk interval: 7 days│
│ - Compression: > 30 days│
└─────────────────────────┘
```

**特性**:
- 複合主鍵: `(stock_id, date)`
- TimescaleDB 時序優化
- 自動壓縮（30 天後）
- 7 天為一個 chunk 分區

---

## 產業分類系統

### TWSE 3 層階層式分類

```
┌──────────────────┐
│   industries     │ 產業分類（41 個）
│  (PK: id)        │
│  UK: code        │ - code: "M15", "M1500"...
│  FK: parent_code │ - level: 1, 2, 3
└────┬─────────┬───┘
     │ 1       │ self-reference (NO ACTION)
     │         └──────┐
     │ N              │ 支援階層結構
     │                ▼
┌────▼─────────────────┐  ┌────────────┐
│ stock_industries     │  │industries  │
│  (PK: id)            ├──┤(parent_code)│
│  FK: stock_id        │  └────────────┘
│  FK: industry_code   │  範例:
│  UK: (stock_id,      │  - M00 (Level 1) 其他
│       industry_code) │    └─ M15 (Level 2) 建材營造
│  - is_primary: bool  │       ├─ M1500 (Level 3) 水泥工業
└────┬─────────────────┘       └─ M1501 (Level 3) 玻璃陶瓷
     │ N
     │
     │ 1
┌────▼─────┐
│  stocks  │
└──────────┘
```

**關聯特性**:
- `industries` 自我參考（parent_code → code）
- `stock_industries` 多對多關聯表
- 唯一約束: 同一股票不能重複歸類到同一產業
- 當前覆蓋率: 72.5% (1,935 / 2,671)

---

## 財務指標數據

### 股票 → 季度財務指標

```
┌──────────────┐
│   stocks     │
│(PK:stock_id) │
└──────┬───────┘
       │ 1
       │
       │ N
┌──────▼──────────────────────┐
│   fundamental_data          │ 財務指標（1,880,982 筆）
│  (PK: id)                   │
│  UK: (stock_id, indicator,  │
│       date)                 │
│                             │
│  - stock_id: "2330"         │
│  - indicator: "ROE稅後",    │
│                "每股稅後淨利"│
│  - date: "2024-Q4"          │ ⚠️ 季度字串格式
│  - value: 31.5              │
│                             │
│  支援 18 個財務指標          │
│  覆蓋 51 個季度              │
│  (2013-Q1 至 2025-Q3)       │
└─────────────────────────────┘
```

**重要特性**:
- ⚠️ `date` 欄位使用季度字串（如 "2024-Q4"），**不是日期型別**
- 唯一約束: `(stock_id, indicator, date)` 防止重複
- 複合索引: `(stock_id, indicator)`, `(indicator, date)`

---

## 產業聚合指標快取

### 產業分類 → 聚合指標快取

```
┌──────────────────┐
│   industries     │
│  (UK: code)      │
└────┬─────────────┘
     │ 1
     │
     │ N
┌────▼─────────────────────────┐
│ industry_metrics_cache       │ 快取計算結果
│  (PK: id)                    │
│  FK: industry_code           │ NO ACTION
│  UK: (industry_code, date,   │
│       metric_name)           │
│                              │
│  - date: 2024-12-05          │
│  - metric_name: "avg_roe",   │
│                 "avg_eps"... │
│  - value: 25.3               │
│  - stocks_count: 150         │
│                              │
│  快取策略:                    │
│  - TTL: 30 天                │
│  - 自動更新                   │
└──────────────────────────────┘
```

**支援的聚合指標**:
1. `avg_roe` - 平均 ROE稅後
2. `avg_roa` - 平均 ROA稅後息前
3. `avg_gross_margin` - 平均營業毛利率
4. `avg_operating_margin` - 平均營業利益率
5. `avg_eps` - 平均每股稅後淨利
6. `avg_revenue_growth` - 平均營收成長率
7. `avg_profit_growth` - 平均稅後淨利成長率

---

## FinMind 產業鏈系統

### FinMind 產業鏈（扁平化分類）

```
┌──────────────────┐
│ industry_chains  │ FinMind 產業鏈
│  (PK: id)        │
│  UK: chain_name  │ - chain_name: "半導體", "電動車"...
└────┬─────────────┘
     │ 1
     │
     │ N
┌────▼─────────────────────┐
│ stock_industry_chains    │ 股票-產業鏈映射
│  (PK: id)                │
│  FK: chain_name          │ NO ACTION
│  UK: (stock_id,          │
│       chain_name)        │
│  - is_primary: bool      │
└────┬─────────────────────┘
     │ N
     │
     │ 1
┌────▼─────┐
│  stocks  │
└──────────┘
```

**資料來源**: FinMind API `TaiwanStockIndustryChain`（需付費會員）

**與 TWSE 分類差異**:
- TWSE: 階層式（3 層）
- FinMind: 扁平化（單層）
- 可同時使用兩種分類系統

---

## 自定義產業分類

### 使用者自訂分類（階層式）

```
┌─────────────┐
│    users    │
└──────┬──────┘
       │ 1
       │
       │ N
┌──────▼──────────────────────┐
│ custom_industry_categories  │ 自定義分類
│  (PK: id)                   │
│  FK: user_id                │ NO ACTION
│  FK: parent_id              │ self-reference (NO ACTION)
│  UK: (user_id,              │
│       category_name)        │
└────┬─────────┬──────────────┘
     │ 1       │ self-reference
     │         └──────┐
     │ N              │ 支援階層結構
     │                ▼
┌────▼──────────────────┐  ┌─────────────────────┐
│ stock_custom_categories│  │custom_industry_     │
│  (PK: id)              ├──┤categories(parent_id)│
│  FK: category_id       │  └─────────────────────┘
│  UK: (category_id,     │
│       stock_id)        │  範例:
└────┬───────────────────┘  使用者 A 建立:
     │ N                    - AI 概念股 (Level 1)
     │                        ├─ AI 晶片 (Level 2)
     │ 1                      └─ AI 伺服器 (Level 2)
┌────▼─────┐
│  stocks  │
└──────────┘
```

**功能**:
- 每位使用者可建立自己的產業分類
- 支援階層結構（類似 TWSE）
- 唯一約束: 同一使用者不能建立重複名稱的分類

---

## 完整 ER 圖（所有關聯）

```
                    ┌─────────────┐
                    │    users    │ 使用者
                    │  (PK: id)   │
                    └─────┬───┬───┘
                          │   │ 1
                          │   │
                    ┌─────┘   └─────────┐
                    │ N                 │ N
            ┌───────▼──────┐    ┌───────▼──────────────────┐
            │ strategies   │    │custom_industry_categories│
            │  (PK: id)    │    │  (PK: id)                │
            └───────┬──────┘    └───────┬──────────────────┘
                    │ 1                 │ 1
                    │                   │
                    │ N                 │ N
            ┌───────▼──────┐    ┌───────▼──────────────┐
            │  backtests   │    │stock_custom_categories│
            │  (PK: id)    │    └───────┬──────────────┘
            └───┬──────────┘            │ N
                │ 1                     │
                ├──────────┐            │ 1
                │ 1        │ N      ┌───▼──────────┐
        ┌───────▼──┐   ┌───▼────┐  │   stocks     │ 股票基本資料
        │backtest_ │   │ trades │  │(PK:stock_id) │
        │results   │   │(PK: id)│  └───┬──────┬───┘
        └──────────┘   └───┬────┘      │ 1    │ 1
                           │ N          │      │
                           │            │      │ N
                           │ 1          │      │
                       ┌───▼────────┐   │  ┌───▼──────────────┐
                       │  stocks    ├───┘  │ stock_industries │
                       │            │      └───┬──────────────┘
                       └───┬────────┘          │ N
                           │ 1                 │
                           │                   │ 1
                           │ N             ┌───▼──────────┐
                       ┌───▼────────────┐  │ industries   │ TWSE 分類
                       │ stock_prices   │  │  (UK: code)  │
                       │(PK:stock_id,   │  └───┬──────────┘
                       │    date)       │      │ 1
                       │                │      │
                       │TimescaleDB     │      │ N
                       │Hypertable      │  ┌───▼──────────────────┐
                       └────────────────┘  │industry_metrics_cache│
                                           └──────────────────────┘

            ┌───────────────┐
            │  stocks       │
            │(PK:stock_id)  │
            └───┬───────┬───┘
                │ 1     │ 1
                │       │
                │ N     │ N
    ┌───────────▼──┐  ┌─▼────────────────────┐
    │fundamental_  │  │stock_industry_chains │
    │data          │  └─┬────────────────────┘
    │(季度財務指標)│    │ N
    └──────────────┘    │
                        │ 1
                    ┌───▼──────────────┐
                    │ industry_chains  │ FinMind 產業鏈
                    │  (UK:chain_name) │
                    └──────────────────┘
```

---

## 外鍵級聯規則總覽

### CASCADE DELETE（7 個）- 業務流程級聯

| 父資料表 | 子資料表 | 說明 |
|---------|---------|------|
| `users` | `strategies` | 刪除使用者 → 刪除所有策略 |
| `users` | `backtests` | 刪除使用者 → 刪除所有回測 |
| `strategies` | `backtests` | 刪除策略 → 刪除所有回測 |
| `backtests` | `backtest_results` | 刪除回測 → 刪除結果 |
| `backtests` | `trades` | 刪除回測 → 刪除交易記錄 |
| `stocks` | `stock_prices` | 刪除股票 → 刪除價格數據 |
| `stocks` | `trades` | 刪除股票 → 刪除交易記錄 |

**設計考量**: 這些是核心業務流程，刪除父物件應自動清理相關資料

### NO ACTION（8 個）- 參考資料保護

| 父資料表 | 子資料表 | 說明 |
|---------|---------|------|
| `stocks` | `stock_industries` | 保護股票基本資料 |
| `industries` | `stock_industries` | 保護產業分類 |
| `industries` | `industry_metrics_cache` | 保護產業分類 |
| `industry_chains` | `stock_industry_chains` | 保護產業鏈 |
| `custom_industry_categories` | `stock_custom_categories` | 保護自定義分類 |
| `custom_industry_categories` | `custom_industry_categories` | 保護分類階層 |
| `industries` | `industries` | 保護產業階層 |
| `users` | `custom_industry_categories` | 保護使用者資料 |

**設計考量**: 這些是參考資料，不允許直接刪除，必須先清理關聯資料

---

## 索引設計圖

### 策略資料表索引

```
strategies
├── 主鍵索引: id
├── 外鍵索引: user_id
├── 單欄索引: status, created_at
├── 複合索引:
│   ├── (user_id, status)      ← 查詢使用者特定狀態的策略
│   └── (user_id, created_at)  ← 時間排序
└── GIN 索引: name             ← 模糊搜尋 (ILIKE)
```

### 回測資料表索引

```
backtests
├── 主鍵索引: id
├── 外鍵索引: strategy_id, user_id
├── 單欄索引: status, created_at, symbol
├── 複合索引:
│   ├── (user_id, status)         ← 查詢使用者特定狀態的回測
│   ├── (user_id, created_at)     ← 時間排序
│   ├── (strategy_id, created_at) ← 策略回測歷史
│   └── (start_date, end_date)    ← 日期範圍查詢
└── GIN 索引: name                ← 模糊搜尋
```

### 財務數據索引

```
fundamental_data
├── 主鍵索引: id
├── 單欄索引: stock_id, indicator
├── 複合索引:
│   ├── (stock_id, indicator)  ← 特定股票的指標查詢
│   └── (indicator, date)      ← 跨股票的指標比較
└── 唯一約束: (stock_id, indicator, date)
```

---

## 資料流向圖

### 回測執行流程

```
1. 使用者建立回測
   │
   ▼
2. backtests (status: PENDING)
   │
   ▼
3. Backtrader 引擎執行
   │
   ├───► 讀取 stock_prices (OHLCV 數據)
   │
   ├───► 執行策略代碼 (strategies.code)
   │
   └───► 生成交易記錄
         │
         ▼
4. 寫入資料庫
   │
   ├───► backtest_results (績效指標)
   │
   ├───► trades (交易記錄)
   │
   └───► backtests (status: COMPLETED)
```

### 產業指標計算流程

```
1. API 請求 /api/v1/industry/{code}/metrics
   │
   ▼
2. 檢查快取 industry_metrics_cache
   │
   ├─[有效快取]──► 直接返回
   │
   └─[無快取/過期]
         │
         ▼
3. 查詢 stock_industries (取得該產業的所有股票)
   │
   ▼
4. 查詢 fundamental_data (取得最新季度財務指標)
   │
   ▼
5. 計算平均值 (avg_roe, avg_eps...)
   │
   ▼
6. 寫入快取 industry_metrics_cache
   │
   ▼
7. 返回結果
```

---

## 資料表依賴順序

### 建立順序（從無依賴到有依賴）

1. **第一層（無外鍵依賴）**:
   - `users`
   - `stocks`
   - `industries`
   - `industry_chains`

2. **第二層（依賴第一層）**:
   - `strategies` (依賴 users)
   - `stock_prices` (依賴 stocks)
   - `stock_industries` (依賴 stocks, industries)
   - `stock_industry_chains` (依賴 stocks, industry_chains)
   - `fundamental_data` (依賴 stocks - 僅邏輯關聯，無外鍵)
   - `industry_metrics_cache` (依賴 industries)
   - `custom_industry_categories` (依賴 users)

3. **第三層（依賴第二層）**:
   - `backtests` (依賴 strategies, users)
   - `stock_custom_categories` (依賴 custom_industry_categories)

4. **第四層（依賴第三層）**:
   - `backtest_results` (依賴 backtests)
   - `trades` (依賴 backtests, stocks)

### 刪除順序（相反）

刪除資料表時必須按照相反順序，避免外鍵約束錯誤：

1. `trades`, `backtest_results`
2. `backtests`, `stock_custom_categories`
3. `strategies`, `stock_prices`, `stock_industries`, `fundamental_data`, `industry_metrics_cache`, `custom_industry_categories`, `stock_industry_chains`
4. `users`, `stocks`, `industries`, `industry_chains`

---

## dbdiagram.io 程式碼

以下程式碼可直接貼到 [dbdiagram.io](https://dbdiagram.io/) 生成視覺化 ER 圖：

```dbml
// QuantLab Database Schema

Table users {
  id integer [pk, increment]
  email varchar(255) [unique, not null]
  username varchar(100) [unique, not null]
  hashed_password varchar(255) [not null]
  full_name varchar(255)
  is_active boolean [default: true]
  is_superuser boolean [default: false]
  finlab_api_token text [note: 'Encrypted with Fernet']
  created_at timestamp
  updated_at timestamp
  last_login timestamp
}

Table stocks {
  stock_id varchar(10) [pk]
  name varchar(100) [not null]
  category varchar(50)
  market varchar(20)
  is_active varchar(10) [default: 'active']
  created_at timestamp
  updated_at timestamp
}

Table stock_prices {
  stock_id varchar(10) [pk, ref: > stocks.stock_id]
  date date [pk]
  open decimal(10,2) [not null]
  high decimal(10,2) [not null]
  low decimal(10,2) [not null]
  close decimal(10,2) [not null]
  volume bigint [not null]
  adj_close decimal(10,2)

  Note: 'TimescaleDB Hypertable - Partitioned by date (7-day chunks)'
}

Table strategies {
  id integer [pk, increment]
  user_id integer [ref: > users.id]
  name varchar(200) [not null]
  description text
  code text [not null]
  parameters json
  status varchar(20) [default: 'draft']
  created_at timestamp
  updated_at timestamp

  indexes {
    (user_id, status)
    (user_id, created_at)
    name [type: gin, note: 'Full-text search']
  }
}

Table backtests {
  id integer [pk, increment]
  strategy_id integer [ref: > strategies.id]
  user_id integer [ref: > users.id]
  name varchar(200) [not null]
  description text
  symbol varchar(20) [not null]
  parameters json
  start_date date [not null]
  end_date date [not null]
  initial_capital decimal(15,2) [default: 1000000]
  status varchar(20) [default: 'PENDING']
  error_message text
  started_at timestamp
  completed_at timestamp
  created_at timestamp
  updated_at timestamp

  indexes {
    (user_id, status)
    (user_id, created_at)
    (strategy_id, created_at)
    (start_date, end_date)
  }
}

Table backtest_results {
  id integer [pk, increment]
  backtest_id integer [unique, ref: - backtests.id]
  total_return decimal(10,4)
  annual_return decimal(10,4)
  final_portfolio_value decimal(15,2)
  sharpe_ratio decimal(10,4)
  max_drawdown decimal(10,4)
  volatility decimal(10,4)
  total_trades integer
  winning_trades integer
  losing_trades integer
  win_rate decimal(10,4)
  average_profit decimal(15,2)
  average_loss decimal(15,2)
  profit_factor decimal(10,4)
  sortino_ratio decimal(10,4)
  calmar_ratio decimal(10,4)
  information_ratio decimal(10,4)
  created_at timestamp
  updated_at timestamp
}

Table trades {
  id integer [pk, increment]
  backtest_id integer [ref: > backtests.id]
  stock_id varchar(10) [ref: > stocks.stock_id]
  date date [not null]
  action varchar(10) [not null, note: 'BUY or SELL']
  quantity integer [not null]
  price decimal(10,2) [not null]
  commission decimal(10,2) [default: 0]
  tax decimal(10,2) [default: 0]
  total_amount decimal(15,2) [not null]
  profit_loss decimal(15,2)
  created_at timestamp

  indexes {
    (backtest_id, date)
  }
}

Table fundamental_data {
  id integer [pk, increment]
  stock_id varchar(10) [not null]
  indicator varchar(50) [not null]
  date varchar(20) [not null, note: 'Quarterly format: 2024-Q4']
  value float
  created_at timestamp
  updated_at timestamp

  indexes {
    (stock_id, indicator, date) [unique]
    (stock_id, indicator)
    (indicator, date)
  }
}

Table industries {
  id integer [pk, increment]
  code varchar(20) [unique, not null]
  name_zh varchar(100) [not null]
  name_en varchar(100)
  parent_code varchar(20) [ref: > industries.code]
  level integer [default: 1]
  description text
  created_at timestamp
  updated_at timestamp
}

Table stock_industries {
  id integer [pk, increment]
  stock_id varchar(10) [ref: > stocks.stock_id]
  industry_code varchar(20) [ref: > industries.code]
  is_primary boolean [default: false]
  created_at timestamp

  indexes {
    (stock_id, industry_code) [unique]
  }
}

Table industry_metrics_cache {
  id integer [pk, increment]
  industry_code varchar(20) [ref: > industries.code]
  date date [not null]
  metric_name varchar(50) [not null]
  value decimal
  stocks_count integer
  created_at timestamp

  indexes {
    (industry_code, date, metric_name) [unique]
  }
}

Table industry_chains {
  id integer [pk, increment]
  chain_name varchar(100) [unique, not null]
  description varchar(500)
  created_at timestamp
  updated_at timestamp
}

Table stock_industry_chains {
  id integer [pk, increment]
  stock_id varchar(10) [not null]
  chain_name varchar(100) [ref: > industry_chains.chain_name]
  is_primary boolean [default: false]
  created_at timestamp
  updated_at timestamp

  indexes {
    (stock_id, chain_name) [unique]
  }
}

Table custom_industry_categories {
  id integer [pk, increment]
  user_id integer [ref: > users.id]
  category_name varchar(100) [not null]
  description varchar(500)
  parent_id integer [ref: > custom_industry_categories.id]
  created_at timestamp
  updated_at timestamp

  indexes {
    (user_id, category_name) [unique]
  }
}

Table stock_custom_categories {
  id integer [pk, increment]
  category_id integer [ref: > custom_industry_categories.id]
  stock_id varchar(10) [not null]
  created_at timestamp

  indexes {
    (category_id, stock_id) [unique]
  }
}
```

---

**使用方式**:

1. 訪問 https://dbdiagram.io/
2. 點擊 "New Diagram"
3. 將上述程式碼貼到左側編輯器
4. 右側會自動生成視覺化 ER 圖
5. 可匯出為 PNG/PDF/SQL

---

**文檔維護**:
- 最後更新: 2025-12-05
- 新增資料表時，必須同步更新此 ER 圖文檔
- 變更外鍵關聯時，必須更新「外鍵級聯規則總覽」
