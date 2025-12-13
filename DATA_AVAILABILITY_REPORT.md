# QuantLab 數據可用性報告

**生成時間**: 2025-12-13
**系統**: QuantLab v0.1.0

---

## 📊 數據可用性總覽

| 數據類型 | 狀態 | 來源 | 記錄數 | 時間範圍 |
|---------|------|------|--------|---------|
| **✅ 成交價量（日線）** | 已有 | FinLab | 12,230,549 筆 | 2007-04-23 ~ 2025-12-11 |
| **✅ 成交價量（分鐘線）** | 已有 | Shioaji | ~280M 筆（導入中） | 2018-12-07 ~ 2025-12-10 |
| **✅ 法人買賣超** | API 可用 | FinMind | - | 可查詢 |
| **❌ 選擇權** | 未實作 | FinMind | - | - |

---

## ✅ 1. 成交價量（已有完整數據）

### 1.1 日線數據 (stock_prices)

**狀態**: ✅ 已有完整數據

| 項目 | 詳情 |
|------|------|
| **資料表** | `stock_prices` |
| **記錄數** | **12,230,549 筆** |
| **股票數** | 約 2,671 檔 |
| **時間範圍** | 2007-04-23 ~ 2025-12-11（18 年） |
| **資料來源** | FinLab API |
| **更新頻率** | 每日自動同步（Celery 定時任務） |

**欄位結構**:
```sql
- stock_id    VARCHAR(10)   -- 股票代碼
- date        DATE          -- 日期
- open        NUMERIC(10,2) -- 開盤價
- high        NUMERIC(10,2) -- 最高價
- low         NUMERIC(10,2) -- 最低價
- close       NUMERIC(10,2) -- 收盤價
- volume      BIGINT        -- 成交量
- adj_close   NUMERIC(10,2) -- 還原權值收盤價
```

**使用範例**:
```python
# 查詢台積電 2024 年日線數據
SELECT * FROM stock_prices
WHERE stock_id = '2330'
  AND date >= '2024-01-01'
  AND date <= '2024-12-31'
ORDER BY date;
```

**API 端點**:
- `GET /api/v1/data/prices/{stock_id}` - 查詢日線數據
- `GET /api/v1/data/latest-prices` - 最新價格

---

### 1.2 分鐘線數據 (stock_minute_prices)

**狀態**: ✅ 正在導入（68% 完成）

| 項目 | 詳情 |
|------|------|
| **資料表** | `stock_minute_prices` |
| **已導入記錄** | ~159M 筆 → ~280M 筆（完成後） |
| **已導入股票** | 1,055 → 1,602 檔（完成後） |
| **時間範圍** | 2018-12-07 ~ 2025-12-10（7 年） |
| **資料來源** | Shioaji（永豐證券） |
| **更新狀態** | 🔄 重新導入中（預計 3.5 小時完成） |

**欄位結構**:
```sql
- stock_id    VARCHAR(10)       -- 股票代碼
- datetime    TIMESTAMP         -- 時間（分鐘級別）
- timeframe   VARCHAR(10)       -- 時間框架（1min）
- open        NUMERIC(10,2)     -- 開盤價
- high        NUMERIC(10,2)     -- 最高價
- low         NUMERIC(10,2)     -- 最低價
- close       NUMERIC(10,2)     -- 收盤價
- volume      BIGINT            -- 成交量
```

**TimescaleDB 優化**:
- Hypertable 分區（按 datetime）
- 自動壓縮（7 天後）
- 高效時序查詢

**API 端點**:
- `GET /api/v1/intraday/klines/{stock_id}` - 查詢分鐘線
- `GET /api/v1/intraday/coverage/{stock_id}` - 數據覆蓋範圍

**使用範例**:
```python
# 查詢台積電 2024-12-13 盤中分鐘線
SELECT * FROM stock_minute_prices
WHERE stock_id = '2330'
  AND datetime >= '2024-12-13 09:00:00'
  AND datetime <= '2024-12-13 13:30:00'
ORDER BY datetime;
```

---

## ✅ 2. 法人買賣超（API 可用，未存儲）

### 2.1 數據來源

**狀態**: ✅ FinMind API 已驗證可用

| 項目 | 詳情 |
|------|------|
| **數據集** | `TaiwanStockInstitutionalInvestorsBuySell` |
| **API 狀態** | ✅ 已測試通過 |
| **存儲狀態** | ❌ 未建立資料表 |
| **使用方式** | 透過 `FinMindClient.get_institutional_investors()` |

### 2.2 法人類型

| 類型代碼 | 中文名稱 | 說明 |
|----------|---------|------|
| `Foreign_Investor` | 外資 | 外資及陸資（不含自營商） |
| `Investment_Trust` | 投信 | 投資信託基金 |
| `Dealer_self` | 自營商-自行買賣 | 證券自營商自行買賣 |
| `Dealer_Hedging` | 自營商-避險 | 證券自營商避險 |
| `Foreign_Dealer_Self` | 外資自營商 | 外資及陸資自營商 |

### 2.3 數據結構

```json
{
    "date": "2024-12-13",
    "stock_id": "2330",
    "buy": 13431533,      // 買進股數
    "sell": 14327474,     // 賣出股數
    "name": "Foreign_Investor"
}
```

**計算買賣超**:
```python
net_buy_sell = buy - sell  # 正數=買超，負數=賣超
```

### 2.4 使用方式

**目前（直接 API 調用）**:
```python
from app.services.finmind_client import FinMindClient

client = FinMindClient()
df = client.get_institutional_investors(
    stock_id='2330',
    start_date='2024-12-01',
    end_date='2024-12-13'
)

# 計算外資買賣超
foreign_df = df[df['name'] == 'Foreign_Investor']
foreign_df['net_buy_sell'] = foreign_df['buy'] - foreign_df['sell']
```

### 2.5 實作建議

**❌ 當前限制**:
- 未存入資料庫
- 每次查詢需 API 請求
- 無法高效回測

**✅ 改進方案**:

#### 方案 A: 建立資料表（推薦）

```sql
CREATE TABLE institutional_investors (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    stock_id VARCHAR(10) NOT NULL,
    investor_type VARCHAR(50) NOT NULL,
    buy_volume BIGINT NOT NULL,
    sell_volume BIGINT NOT NULL,
    net_buy_sell BIGINT GENERATED ALWAYS AS (buy_volume - sell_volume) STORED,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, stock_id, investor_type)
);

CREATE INDEX idx_institutional_date_stock ON institutional_investors(date, stock_id);
```

#### 方案 B: Celery 定時同步

```python
@celery_app.task
def sync_institutional_investors():
    """每日同步三大法人買賣超"""
    client = FinMindClient()

    # 同步所有股票
    for stock_id in get_stock_list():
        df = client.get_institutional_investors(
            stock_id=stock_id,
            start_date=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            end_date=datetime.now().strftime('%Y-%m-%d')
        )
        save_to_database(df)
```

#### 方案 C: 整合為 Qlib 因子

```python
# 在策略中使用
QLIB_FIELDS = [
    '$close',
    '$volume',
    '$foreign_net',    # 外資買賣超（新增）
    '$trust_net',      # 投信買賣超（新增）
]
```

---

## ❌ 3. 選擇權（未實作）

### 3.1 數據來源

**FinMind API 支援的選擇權數據集**:

| 數據集名稱 | 說明 | 狀態 |
|-----------|------|------|
| `TaiwanOptionTick` | 選擇權逐筆交易 | ❌ 未實作 |
| `TaiwanOptionDaily` | 選擇權日線數據 | ❌ 未實作 |
| `TaiwanFutOptInstitutionalInvestors` | 期權法人買賣超 | ❌ 未實作 |
| `TaiwanOptionInstitutionalInvestors` | 選擇權法人買賣 | ❌ 未實作 |
| `TaiwanOptionOpenInterestLargeTraders` | 選擇權大戶持倉 | ❌ 未實作 |

### 3.2 實作建議

#### 步驟 1: 擴展 FinMindClient

```python
# backend/app/services/finmind_client.py

def get_option_daily(
    self,
    contract_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """獲取選擇權日線數據"""
    return self._make_request(
        dataset="TaiwanOptionDaily",
        data_id=contract_code,
        start_date=start_date,
        end_date=end_date
    )

def get_option_tick(
    self,
    contract_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """獲取選擇權逐筆交易"""
    return self._make_request(
        dataset="TaiwanOptionTick",
        data_id=contract_code,
        start_date=start_date,
        end_date=end_date
    )
```

#### 步驟 2: 建立資料表

```sql
-- 選擇權基本資料
CREATE TABLE options (
    contract_code VARCHAR(20) PRIMARY KEY,
    underlying_stock VARCHAR(10),
    strike_price NUMERIC(10,2),
    expiry_date DATE,
    option_type VARCHAR(10),  -- 'call' or 'put'
    contract_size INTEGER
);

-- 選擇權日線數據
CREATE TABLE option_prices (
    contract_code VARCHAR(20),
    date DATE,
    open NUMERIC(10,2),
    high NUMERIC(10,2),
    low NUMERIC(10,2),
    close NUMERIC(10,2),
    volume BIGINT,
    open_interest BIGINT,
    PRIMARY KEY (contract_code, date)
);
```

#### 步驟 3: 創建 API 端點

```python
# backend/app/api/v1/options.py

@router.get("/options/{contract_code}/daily")
async def get_option_daily_data(
    contract_code: str,
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """查詢選擇權日線數據"""
    pass
```

### 3.3 優先順序建議

**階段 1（高優先級）**:
1. ✅ 實作法人買賣超資料表（已驗證 API 可用）
2. ✅ Celery 定時同步法人數據

**階段 2（中優先級）**:
3. 選擇權日線數據（TaiwanOptionDaily）
4. 選擇權法人買賣（TaiwanOptionInstitutionalInvestors）

**階段 3（低優先級）**:
5. 選擇權逐筆交易（TaiwanOptionTick）
6. 選擇權大戶持倉（TaiwanOptionOpenInterestLargeTraders）

---

## 📈 數據統計總覽

### 當前數據量

| 數據類型 | 記錄數 | 時間跨度 | 更新頻率 |
|---------|--------|---------|---------|
| **股票日線** | 12,230,549 | 18 年 | 每日 |
| **股票分鐘線** | ~280M（導入中） | 7 年 | 靜態 |
| **基本面數據** | 1,880,982 | - | 每季 |
| **產業分類** | 1,935 | - | 手動 |
| **法人買賣超** | 0（API 可用） | - | 未同步 |
| **選擇權** | 0 | - | 未實作 |

### 儲存空間使用

```bash
# 查詢各表大小
docker compose exec -T postgres psql -U quantlab quantlab -c "
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
"
```

---

## 🚀 快速開始

### 查詢成交價量（日線）

```python
# 使用 API
GET /api/v1/data/prices/2330?start_date=2024-01-01&end_date=2024-12-31

# 直接查詢資料庫
from app.repositories.stock_price import StockPriceRepository

repo = StockPriceRepository()
prices = repo.get_prices(db, '2330', '2024-01-01', '2024-12-31')
```

### 查詢成交價量（分鐘線）

```python
# 使用 API
GET /api/v1/intraday/klines/2330?start=2024-12-13T09:00&end=2024-12-13T13:30

# 直接查詢資料庫
from app.repositories.stock_minute_price import StockMinutePriceRepository

repo = StockMinutePriceRepository()
klines = repo.get_klines(db, '2330', '2024-12-13 09:00', '2024-12-13 13:30')
```

### 查詢法人買賣超

```python
# 使用 FinMindClient（當前方式）
from app.services.finmind_client import FinMindClient

client = FinMindClient()
df = client.get_institutional_investors('2330', '2024-12-01', '2024-12-13')

# 計算外資買賣超
foreign = df[df['name'] == 'Foreign_Investor'].copy()
foreign['net'] = foreign['buy'] - foreign['sell']
```

---

## 📝 總結

### ✅ 已有數據

1. **成交價量（日線）** - 完整 18 年數據
2. **成交價量（分鐘線）** - 7 年數據（導入中）
3. **法人買賣超** - API 可用（未存儲）

### ❌ 缺少數據

1. **選擇權** - 完全未實作

### 🎯 建議行動

**短期（1-2 天）**:
1. ✅ 完成分鐘線數據導入（進行中）
2. 建立法人買賣超資料表
3. 實作法人數據定時同步

**中期（1-2 週）**:
4. 實作選擇權日線數據
5. 實作選擇權法人買賣
6. 創建選擇權 API 端點

**長期（1 個月）**:
7. 選擇權逐筆數據
8. 選擇權策略回測引擎
9. 整合到 Qlib 因子系統

---

**報告生成時間**: 2025-12-13 07:30 AM
**數據版本**: QuantLab v0.1.0
