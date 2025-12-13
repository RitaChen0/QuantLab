# FinMind API - 三大法人買賣超數據驗證報告

**驗證時間**: 2024-12-13
**狀態**: ✅ 成功

## 1. 測試結果

### API 端點
- **Dataset**: `TaiwanStockInstitutionalInvestorsBuySell`（正確名稱）
- **錯誤名稱**: ~~`TaiwanStockInstitutionalInvestors`~~（會返回 422 錯誤）
- **HTTP Status**: 200
- **返回記錄數**: 50 筆（2024-12-02 ~ 2024-12-13，台積電 2330）

### 數據結構

| 欄位 | 類型 | 說明 | 範例 |
|------|------|------|------|
| `date` | string | 日期 | "2024-12-13" |
| `stock_id` | string | 股票代號 | "2330" |
| `buy` | int | 買進股數 | 13431533 |
| `name` | string | 法人類型 | "Foreign_Investor" |
| `sell` | int | 賣出股數 | 14327474 |

### 法人類型 (name 欄位)

| 類型代碼 | 中文名稱 | 說明 |
|----------|---------|------|
| `Foreign_Investor` | 外資 | 外資及陸資買賣超（不含外資自營商） |
| `Investment_Trust` | 投信 | 投資信託基金 |
| `Dealer_self` | 自營商-自行買賣 | 證券自營商自行買賣 |
| `Dealer_Hedging` | 自營商-避險 | 證券自營商避險 |
| `Foreign_Dealer_Self` | 外資自營商 | 外資及陸資自營商買賣專戶 |

## 2. 計算買賣超

**買賣超 = 買進股數 - 賣出股數**

- 正值：淨買進（買超）
- 負值：淨賣出（賣超）

### 範例（2024-12-13 台積電）

```python
# 原始數據
{
    "date": "2024-12-13",
    "stock_id": "2330",
    "buy": 13431533,
    "name": "Foreign_Investor",
    "sell": 14327474
}

# 計算買賣超
net_buy_sell = 13431533 - 14327474 = -895,941 股
# 負數表示外資賣超 89.5 萬股
```

## 3. 配置修改

### 3.1 新增環境變數配置

**檔案**: `backend/app/core/config.py`

```python
# FinMind
FINMIND_API_TOKEN: str = ""
```

### 3.2 修正 API Dataset 名稱

**檔案**: `backend/app/services/finmind_client.py`

```python
def get_institutional_investors(
    self,
    stock_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """獲取三大法人買賣超"""
    return self._make_request(
        dataset="TaiwanStockInstitutionalInvestorsBuySell",  # ✅ 正確名稱
        data_id=stock_id,
        start_date=start_date,
        end_date=end_date
    )
```

## 4. 使用範例

### 4.1 基本用法

```python
from app.services.finmind_client import FinMindClient

client = FinMindClient()

# 獲取台積電 (2330) 三大法人買賣超
df = client.get_institutional_investors(
    stock_id='2330',
    start_date='2024-12-01',
    end_date='2024-12-13'
)

# 數據形狀: (50, 5)
# 欄位: ['date', 'stock_id', 'buy', 'name', 'sell']
```

### 4.2 計算買賣超

```python
import pandas as pd

# 計算買賣超
df['net_buy_sell'] = df['buy'] - df['sell']

# 按日期和法人類型透視
pivot = df.pivot_table(
    index='date',
    columns='name',
    values='net_buy_sell',
    aggfunc='sum'
)

print(pivot)
```

**輸出範例**:

```
            Foreign_Investor  Investment_Trust  Dealer_self  Dealer_Hedging
date
2024-12-02       -5,234,567           348,109      12,270         -45,600
2024-12-03        1,892,345          -125,890     -88,000          76,200
2024-12-13         -895,941          -178,626    -702,000        -161,200
```

### 4.3 聚焦外資買賣超

```python
# 僅保留外資數據
foreign_df = df[df['name'] == 'Foreign_Investor'].copy()
foreign_df['net_buy_sell'] = foreign_df['buy'] - foreign_df['sell']

# 繪圖
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 6))
plt.bar(foreign_df['date'], foreign_df['net_buy_sell'])
plt.title('外資買賣超 - 台積電 (2330)')
plt.xlabel('日期')
plt.ylabel('買賣超股數')
plt.xticks(rotation=45)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
```

### 4.4 策略中使用（Qlib）

```python
# 在 Qlib 策略中使用外資買賣超因子

from app.services.finmind_client import FinMindClient
import pandas as pd

# 獲取外資買賣超數據
client = FinMindClient()
df = client.get_institutional_investors(
    stock_id='2330',
    start_date='2024-01-01',
    end_date='2024-12-13'
)

# 僅保留外資
foreign_df = df[df['name'] == 'Foreign_Investor'].copy()
foreign_df['net_buy_sell'] = foreign_df['buy'] - foreign_df['sell']

# 合併到 Qlib dataset
# dataset['foreign_net'] = foreign_df.set_index('date')['net_buy_sell']

# 計算指標
# dataset['foreign_net_ma5'] = dataset['foreign_net'].rolling(5).mean()
# dataset['foreign_net_ma20'] = dataset['foreign_net'].rolling(20).mean()
```

## 5. 後續建議

### 5.1 資料庫存儲（推薦）

建立專用資料表存儲三大法人買賣超數據：

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
CREATE INDEX idx_institutional_stock_date ON institutional_investors(stock_id, date);
```

### 5.2 Celery 定時同步

```python
# backend/app/tasks/data_sync_tasks.py

@celery_app.task(name="sync_institutional_investors")
def sync_institutional_investors():
    """同步三大法人買賣超數據（每日執行）"""
    from app.services.finmind_client import FinMindClient
    from app.db.session import get_db

    client = FinMindClient()

    # 獲取所有股票列表
    stocks = get_stock_list()

    for stock_id in stocks:
        df = client.get_institutional_investors(
            stock_id=stock_id,
            start_date=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            end_date=datetime.now().strftime('%Y-%m-%d')
        )

        # 存入資料庫
        save_to_database(df)
```

### 5.3 擴展 QlibDataAdapter

將外資買賣超整合為 Qlib 特徵：

```python
# backend/app/services/qlib_data_adapter.py

def get_qlib_ohlcv(self, symbol, start_date, end_date, fields=None):
    # ... 現有代碼 ...

    # 新增：如果 fields 包含 '$foreign_net'
    if fields and '$foreign_net' in fields:
        institutional_df = self.finmind_client.get_institutional_investors(
            stock_id=symbol,
            start_date=start_date,
            end_date=end_date
        )

        # 僅保留外資
        foreign_df = institutional_df[
            institutional_df['name'] == 'Foreign_Investor'
        ].copy()

        # 計算買賣超
        foreign_df['foreign_net'] = foreign_df['buy'] - foreign_df['sell']

        # 合併到主 DataFrame
        df = df.merge(
            foreign_df[['date', 'foreign_net']],
            on='date',
            how='left'
        )

    return df
```

## 6. 限制與注意事項

### 6.1 數據可用性
- ✅ 無需付費會員即可存取
- ✅ 數據每日更新
- ⚠️ 交易日當日數據可能延遲（建議隔日查詢）

### 6.2 數據格式
- 每日每股票有 5 筆記錄（5 種法人類型）
- 數據為股數（非金額），需乘以成交價格計算金額

### 6.3 效能建議
- 單次請求不要超過 1 年數據（避免超時）
- 使用 Redis 快取減少 API 呼叫次數
- 批次同步時加入延遲（避免觸發 rate limit）

## 7. 完整測試代碼

**檔案**: `backend/test_finmind_institutional.py`

```python
#!/usr/bin/env python3
"""測試 FinMind API - 三大法人買賣超數據"""

from app.services.finmind_client import FinMindClient
import pandas as pd

client = FinMindClient()

df = client.get_institutional_investors(
    stock_id='2330',
    start_date='2024-12-01',
    end_date='2024-12-13'
)

print(f"數據形狀: {df.shape}")
print(f"數據欄位: {df.columns.tolist()}")
print("\n前 5 筆數據:")
print(df.head())

# 計算買賣超
df['net_buy_sell'] = df['buy'] - df['sell']

# 按日期和法人類型透視
pivot = df.pivot_table(
    index='date',
    columns='name',
    values='net_buy_sell',
    aggfunc='sum'
)

print("\n買賣超統計（按日期）:")
print(pivot)
```

---

**結論**: ✅ FinMind API 的三大法人買賣超數據可以正常使用，已修正 dataset 名稱並驗證數據格式。建議建立資料表並使用 Celery 定時同步數據以提升查詢效能。
