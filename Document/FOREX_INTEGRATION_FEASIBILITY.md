# QuantLab 外匯（Forex）交易支援可行性分析報告

**報告日期**: 2025-12-26
**分析範圍**: 系統架構、數據源、技術實現、風險評估
**結論**: ✅ **高度可行**，建議分三階段實施

---

## 📊 執行摘要

### 可行性評估：8.5/10 ✅

**核心發現**：
- ✅ 現有架構可復用 **80%** 的代碼
- ✅ 數據庫表結構無需大改（僅需價格精度調整）
- ✅ Backtrader 原生支援外匯交易
- ✅ 免費數據源可用（OANDA、Alpha Vantage）

**預估工作量**：2-3 個月（45-60 天）

**建議方案**：分三階段迭代開發

---

## 1. 資料結構兼容性分析

### 1.1 現有表結構檢查

#### ✅ stocks 表 - **完全兼容**

```sql
stock_id    VARCHAR(10)   -- 可存 "EURUSD", "USDJPY"
name        VARCHAR(100)  -- "歐元/美元"
category    VARCHAR(50)   -- 新增 "FOREX" 枚舉值 ✅
market      VARCHAR(20)   -- "SPOT" (現貨) 或 "FUTURES"
is_active   VARCHAR(10)   -- "active"
```

#### ⚠️ stock_prices 表 - **需小幅調整**

**問題**：
- `NUMERIC(10,2)` 精度不足（外匯需 4-5 位小數）
- 例如：EUR/USD = 1.08234 需存為 1.08234

**解決方案（推薦）**：
```python
# 方案：使用縮放因子
# 存儲時：1.08234 × 10000 = 10823.4 ✅
# 讀取時：10823.4 / 10000 = 1.08234

# 優點：
# - 不影響現有股票/期貨數據
# - 不需修改資料庫 schema
# - Repository 層透明處理
```

#### ✅ stock_minute_prices 表 - **可復用**

**調整點**：
- 時區處理：外匯使用 UTC（24/5 交易）
- volume 欄位：外匯現貨設為 0 或 tick 數量

### 1.2 外匯 vs 股票數據差異

| 特性 | 台股 | 外匯現貨 | 調整方案 |
|------|------|----------|----------|
| **交易時間** | 09:00-13:30 | 24/5 全球 | 擴展 Celery 調度時間 ✅ |
| **價格精度** | 2 位小數 | 4-5 位小數 | 縮放因子 × 10000 ✅ |
| **成交量** | 真實成交量 | 現貨無 volume | volume = 0 或 tick 數 ✅ |
| **交易成本** | 手續費 + 稅 | 點差 (spread) | 新 ForexCommissionInfo ✅ |
| **槓桿** | 融資 1.5x | 10-500x | Backtrader margin 配置 ✅ |

---

## 2. 數據源選項

### 2.1 推薦：OANDA API ⭐⭐⭐⭐⭐

**選擇理由**：
1. ✅ **免費 Demo 帳戶** 無限制存取歷史數據（5 年）
2. ✅ **高頻數據**：支援 5 秒至 1 天級別
3. ✅ **真實點差**：提供 bid/ask 價格
4. ✅ **Python SDK**：官方 `oandapyV20` 函式庫
5. ✅ **台灣可用**：無地理限制

**實施代碼範例**：
```python
# backend/app/services/oanda_client.py
from oandapyV20 import API
from oandapyV20.endpoints.instruments import InstrumentsCandles

class OandaClient:
    def __init__(self):
        self.api = API(access_token=settings.OANDA_API_KEY)

    def get_forex_data(self, pair: str, start: datetime, end: datetime):
        """
        獲取外匯歷史數據

        Args:
            pair: 貨幣對，如 "EUR_USD"
            granularity: M1, M5, M15, M30, H1, D
        """
        params = {
            "from": start.isoformat(),
            "to": end.isoformat(),
            "granularity": "M5",  # 5 分鐘線
        }
        request = InstrumentsCandles(instrument=pair, params=params)
        return self.api.request(request)['candles']
```

### 2.2 備選方案

| 數據源 | 評分 | 優點 | 缺點 |
|--------|------|------|------|
| **Alpha Vantage** | ⭐⭐⭐⭐ | 免費，20年歷史 | 25 req/天限制 |
| **Twelve Data** | ⭐⭐⭐⭐ | 800 req/天 | 免費版功能受限 |
| **台灣央行** | ⭐⭐ | 官方數據 | 僅 TWD/USD 日線 |

---

## 3. 回測引擎支援

### 3.1 Backtrader - ✅ 完全支援

**外匯佣金配置**（新增）：
```python
# backend/app/services/backtest_engine.py
class ForexCommissionInfo(bt.CommInfoBase):
    """
    外匯交易成本配置（點差模型）
    """
    params = (
        ('stocklike', False),       # 外匯，非股票
        ('commtype', bt.CommInfoBase.COMM_FIXED),
        ('commission', 0.0002),     # 2 pips = 0.0002 (EUR/USD)
        ('mult', 100000.0),         # 標準手 = 100,000 基礎貨幣
        ('margin', 1000.0),         # 保證金 = $100,000 / 100 (1:100 槓桿)
        ('leverage', 100),
    )

    def _getcommission(self, size, price, pseudoexec):
        """計算點差成本"""
        # 點差 = 合約價值 × 點差比例
        return abs(size) * self.p.mult * self.p.commission
```

**使用範例**：
```python
# 在回測策略中配置
cerebro.broker.addcommissioninfo(ForexCommissionInfo())
cerebro.adddata(eurusd_data)  # 外匯數據
cerebro.run()
```

### 3.2 Qlib - ⚠️ 需要適配

**問題**：
- Qlib 主要為股票設計（假設有成交量）
- Alpha158 因子集不適用於外匯

**解決方案**：
```python
# 創建外匯專屬因子集
class ForexAlpha(ExpressionOps):
    """外匯技術指標因子"""

    def __init__(self):
        self.fields = [
            "RSI14",                    # RSI(14)
            "MACD_DIFF",                # MACD 差值
            "BB_WIDTH",                 # 布林通道寬度
            "ATR14",                    # 平均真實波幅
            "STOCH_K",                  # 隨機指標 K
            "MA_CROSS_5_20",            # MA 交叉信號
        ]
```

---

## 4. 系統架構調整

### 4.1 Models 層（最小變更）

#### 方案：復用現有 models ✅

```python
# 無需修改 Stock 模型，只需在數據導入時：
Stock(
    stock_id="EURUSD",
    name="歐元/美元",
    category="FOREX",        # 新增枚舉值
    market="SPOT",           # 現貨外匯
    is_active="active"
)
```

#### 可選：新增 forex_pairs 配置表

```python
# backend/app/models/forex_pair.py
class ForexPair(Base):
    """外匯特定元數據"""
    __tablename__ = "forex_pairs"

    pair_id = Column(String(10), primary_key=True)  # EUR_USD
    base_currency = Column(String(3))                # EUR
    quote_currency = Column(String(3))               # USD
    pip_location = Column(Integer, default=4)        # 小數點位置
    typical_spread = Column(Numeric(6, 5))           # 典型點差（2 pips）
    leverage = Column(Integer, default=100)          # 1:100
    swap_long = Column(Numeric(8, 5))                # 隔夜利息（多頭）
    swap_short = Column(Numeric(8, 5))               # 隔夜利息（空頭）
```

### 4.2 Repository 層（擴展價格轉換）

```python
# backend/app/repositories/stock_price.py
class StockPriceRepository:

    def _scale_forex_price(self, price: Decimal, stock_id: str) -> Decimal:
        """
        外匯價格縮放（存儲時）
        - FOREX: × 10000 (1.08234 → 10823.4)
        - 股票/期貨: 不變
        """
        if self._is_forex(stock_id):
            return price * Decimal('10000')
        return price

    def _descale_forex_price(self, price: Decimal, stock_id: str) -> Decimal:
        """外匯價格反縮放（讀取時）"""
        if self._is_forex(stock_id):
            return price / Decimal('10000')
        return price
```

### 4.3 Service 層（新增外匯服務）

```python
# backend/app/services/forex_data_service.py (新增)
class ForexDataService:
    """外匯數據服務"""

    def sync_forex_pair(self, pair: str, start_date: date, end_date: date):
        """
        同步外匯數據到 PostgreSQL

        流程:
        1. 從 OANDA API 獲取數據
        2. 轉換為 StockPrice 格式（價格 × 10000）
        3. 批量插入 stock_prices
        """
        ohlcv_data = self.oanda_client.get_forex_data(pair, start_date, end_date)

        for candle in ohlcv_data:
            price_create = StockPriceCreate(
                stock_id=pair.replace('_', ''),  # EUR_USD → EURUSD
                date=candle['time'].date(),
                open=Decimal(candle['mid']['o']) * 10000,   # 縮放
                high=Decimal(candle['mid']['h']) * 10000,
                low=Decimal(candle['mid']['l']) * 10000,
                close=Decimal(candle['mid']['c']) * 10000,
                volume=0  # 外匯現貨無成交量
            )
            StockPriceRepository.upsert(db, price_create)
```

### 4.4 Celery 同步任務（新增外匯任務）

```python
# backend/app/tasks/forex_sync.py (新增)
from celery import shared_task

@shared_task(name="app.tasks.sync_forex_daily")
def sync_forex_daily():
    """
    每日同步主要外匯對（日線數據）

    貨幣對: EUR/USD, USD/JPY, GBP/USD, AUD/USD, USD/CNH
    """
    service = ForexDataService()
    pairs = ["EUR_USD", "USD_JPY", "GBP_USD", "AUD_USD", "USD_CNH"]

    for pair in pairs:
        service.sync_forex_pair(pair, date.today() - timedelta(days=7), date.today())
```

**排程配置**：
```python
# backend/app/core/celery_app.py (修改)
celery_app.conf.beat_schedule.update({
    "sync-forex-daily": {
        "task": "app.tasks.sync_forex_daily",
        "schedule": crontab(hour=0, minute=0),  # UTC 00:00 = 台灣 08:00
        "options": {"expires": 82800},
    },
})
```

---

## 5. 技術挑戰與解決方案

### 5.1 24/5 交易時間處理

**問題**：
- 外匯市場週日 21:00 UTC 開盤，週五 21:00 UTC 收盤
- 跨越多個時區

**解決方案**：
```python
# backend/app/utils/timezone_helpers.py (擴展)
def is_forex_trading_time(dt: datetime) -> bool:
    """
    檢查是否為外匯交易時間（24/5）

    開盤: 週日 21:00 UTC (週一 05:00 台灣)
    收盤: 週五 21:00 UTC (週六 05:00 台灣)
    """
    weekday = dt.weekday()  # 0=週一, 6=週日
    hour = dt.hour

    # 週六 21:00 - 週日 20:59: 休市
    if (weekday == 5 and hour >= 21) or (weekday == 6 and hour < 21):
        return False

    return True
```

### 5.2 隔夜利息（Swap）

**問題**：
- Backtrader 預設不支援隔夜利息
- 外匯持倉過夜需支付或收取利息

**解決方案**：
```python
class ForexStrategy(bt.Strategy):
    def next(self):
        # 檢查是否跨日持倉
        if self.position:
            # 計算隔夜利息（從 forex_pairs 表查詢）
            swap = self.calculate_swap(self.position.size)
            self.broker.add_cash(swap)  # 正利息或負利息

    def calculate_swap(self, size):
        """
        隔夜利息計算
        EUR/USD long: +0.5 pips/day (示例)
        """
        pair_config = db.query(ForexPair).filter_by(pair_id="EUR_USD").first()
        if size > 0:
            return size * 100000 * pair_config.swap_long
        else:
            return size * 100000 * pair_config.swap_short
```

### 5.3 點差（Spread）處理

**方案 1：使用中間價 + 固定點差** ✅ 推薦
```python
# 在 OANDA API 返回的 candle 中:
# mid.o, mid.h, mid.l, mid.c - 中間價（(bid + ask) / 2）

# ForexCommissionInfo 自動扣除點差
commission = 0.0002  # 2 pips
```

**方案 2：使用 bid/ask 價格** (更精確但複雜)
```python
# 需要雙數據源（bid data + ask data）
# 買入使用 ask 價格，賣出使用 bid 價格
```

---

## 6. 分階段實施方案

### 📅 第一階段：基礎架構（2-3 週）

**目標**：支援外匯日線數據回測

#### 任務清單

**1. 資料庫擴展** (3 天)
- [ ] `stocks.category` 新增 `"FOREX"` 枚舉值
- [ ] 創建 `forex_pairs` 配置表
- [ ] Alembic 遷移腳本
- [ ] 測試價格精度轉換（× 10000）

**2. OANDA 客戶端** (4 天)
- [ ] 實現 `OandaClient`（參考 `ShioajiClient`）
- [ ] 支援日線數據獲取
- [ ] 單元測試（Mock API）
- [ ] 整合測試（真實 Demo 帳戶）

**3. Repository/Service 層** (5 天)
- [ ] 擴展 `StockPriceRepository` 支援精度轉換
- [ ] 實現 `ForexDataService`
- [ ] 註冊 5 個主要貨幣對
- [ ] 回填 1 年歷史數據

**4. Backtrader 整合** (3 天)
- [ ] 實現 `ForexCommissionInfo`
- [ ] 創建範例策略（MA Cross）
- [ ] 運行回測驗證

#### 可交付成果 ✅
- 外匯日線數據存儲在 PostgreSQL
- 前端可查看外匯價格圖表
- 可運行簡單外匯策略回測

---

### 📅 第二階段：分鐘線支援（2-3 週）

**目標**：支援外匯分鐘線數據和盤中同步

#### 任務清單

**1. 分鐘線數據同步** (5 天)
- [ ] 擴展 `OandaClient` 支援 M1, M5, M15, M30, H1
- [ ] 創建 Celery 任務 `sync_forex_intraday`
- [ ] 配置 24/5 調度邏輯
- [ ] 回填 6 個月分鐘線數據

**2. Qlib 整合** (4 天)
- [ ] 擴展 `QlibDataAdapter` 支援外匯
- [ ] 導出外匯數據到 `/data/qlib/forex/`
- [ ] 創建 `ForexAlpha` 因子集
- [ ] 測試 Qlib 策略回測

**3. 前端擴展** (3 天)
- [ ] 新增外匯類別篩選器
- [ ] 顯示實時點差信息
- [ ] 顯示 24/5 交易時段標識

**4. 高級佣金模型** (3 天)
- [ ] 實現 swap（隔夜利息）計算
- [ ] 從配置表動態加載點差
- [ ] 支援 bid/ask 價格

#### 可交付成果 ✅
- 外匯分鐘線實時同步
- Qlib 支援外匯策略
- 前端完整展示外匯數據

---

### 📅 第三階段：高級功能（2-3 週）

**目標**：完整外匯交易平台功能

#### 任務清單

**1. 多貨幣對組合策略** (5 天)
- [ ] 支援跨貨幣對套利策略
- [ ] 貨幣籃子（如 DXY 美元指數）
- [ ] 相關性分析工具

**2. 風險管理** (4 天)
- [ ] 動態槓桿調整
- [ ] Margin Call 警告
- [ ] VaR (Value at Risk) 計算

**3. 實時交易介面（可選）** (6 天)
- [ ] OANDA 實盤/模擬下單
- [ ] 訂單管理（OCO, Trailing Stop）
- [ ] 實時持倉監控

**4. ML 因子挖掘** (5 天)
- [ ] 擴展 RD-Agent 支援外匯
- [ ] 生成外匯專屬技術指標因子
- [ ] 訓練 LightGBM 模型

#### 可交付成果 ✅
- 完整的外匯量化交易平台
- 支援實盤/模擬交易（可選）
- AI 驅動的外匯策略生成

---

## 7. 工作量與時程預估

| 階段 | 工作量 | 複雜度 | 風險 | 人力需求 |
|------|--------|--------|------|----------|
| **第一階段** | 15-20 天 | 中 | 低 | 1 名全職開發者 |
| **第二階段** | 15-20 天 | 中-高 | 中 | 1 名全職開發者 |
| **第三階段** | 15-20 天 | 高 | 中-高 | 1-2 名開發者 |
| **總計** | **45-60 天** | | | **2-3 個月** |

**前提假設**：
- 開發者熟悉 QuantLab 架構
- 有 Backtrader/Qlib 使用經驗
- 有外匯交易基礎知識

---

## 8. 風險評估與緩解

### 8.1 技術風險

| 風險 | 影響 | 機率 | 緩解措施 |
|------|------|------|----------|
| **OANDA API 限制** | 中 | 低 | ✅ 使用多個 Demo 帳戶輪詢 |
| **數據精度損失** | 高 | 中 | ✅ 使用縮放因子（× 10000）驗證無損 |
| **時區處理錯誤** | 高 | 中 | ✅ 統一使用 UTC，充分測試 |
| **Backtrader swap** | 中 | 低 | ✅ 策略層手動計算 |
| **Qlib 兼容性** | 低 | 低 | ✅ 創建外匯專屬因子集 |

### 8.2 業務風險

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| **外匯法規** | 高 | ✅ 僅提供回測功能，不提供實盤交易建議 |
| **數據品質** | 中 | ✅ 對比多個數據源驗證 |
| **用戶需求** | 中 | ✅ 先做市場調研，驗證需求 |

### 8.3 維護風險

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| **系統複雜度增加** | 中 | ✅ 嚴格遵循四層架構，充分測試 |
| **資料庫膨脹** | 中 | ✅ 復用 TimescaleDB 壓縮策略 |
| **API 依賴** | 中 | ✅ 實現降級方案（Alpha Vantage 備用）|

---

## 9. 結論與建議

### ✅ 可行性評估：8.5/10

**優勢**：
- ✅ 現有架構設計良好，可復用 80% 代碼
- ✅ 數據源豐富且免費（OANDA, Alpha Vantage）
- ✅ Backtrader 原生支援外匯交易
- ✅ TimescaleDB 可處理大量時序數據

**挑戰**：
- ⚠️ 需處理 24/5 交易時間
- ⚠️ 價格精度需特殊處理
- ⚠️ Qlib 需適配外匯因子

### 🎯 建議方案

**立即採用**：
1. ✅ **第一階段** 作為 MVP（最小可行產品）
2. ✅ 復用現有表結構（使用縮放因子）
3. ✅ OANDA API 作為主要數據源
4. ✅ 分三階段迭代開發

**優先級排序**：
1. 🔥 **第一階段（核心功能）** - 立即啟動
2. 🌟 **第二階段（完整功能）** - 驗證第一階段後啟動
3. 💡 **第三階段（高級功能）** - 根據用戶反饋決定

### 🚀 Next Steps

**立即行動**：
1. ✅ 註冊 OANDA Demo 帳戶，驗證 API 可用性
2. ✅ 創建資料庫遷移腳本（`forex_pairs` 表）
3. ✅ 實現 `OandaClient` 最小原型（1-2 天）
4. ✅ 運行一次完整的外匯策略回測驗證

**決策點**：
- 如第一階段成功，可在 **3 個月內** 上線完整外匯交易支援
- 如遇到技術障礙，可降級為僅支援日線數據（工作量減半）

---

## 附錄：參考資料

### 數據源
- [Alpha Vantage API Documentation](https://www.alphavantage.co/documentation/)
- [OANDA API (Demo Account)](https://developer.oanda.com/rest-live-v20/introduction/)
- [台灣央行匯率 API](https://data.gov.tw/en/datasets/7232)

### 技術文檔
- [Backtrader Commission Schemes](https://www.backtrader.com/docu/commission-schemes/commission-schemes/)
- [Backtrader Forex Community](https://community.backtrader.com/topic/525/forex-commission-scheme)
- [Qlib RL in Forex Markets](https://qlib.readthedocs.io/en/latest/component/rl/overall.html)

### Python 套件
- `oandapyV20` - OANDA API Python SDK
- `alpha_vantage` - Alpha Vantage Python 包裝器
- `twelvedata` - Twelve Data Python 客戶端

---

**報告作者**: Claude Code
**報告版本**: 1.0
**最後更新**: 2025-12-26
**狀態**: ✅ 可行性確認，待決策啟動
