# Qlib 引擎完整指南

本文檔整合了 QuantLab 中 Qlib (Microsoft) 引擎的完整使用、配置和數據管理指南。

## 目錄

- [Qlib 簡介](#qlib-簡介)
- [數據結構](#數據結構)
- [數據同步](#數據同步)
- [策略開發](#策略開發)
- [vs PostgreSQL](#vs-postgresql)
- [故障排查](#故障排查)

---

## Qlib 簡介

### 什麼是 Qlib？

**Qlib** (Quantitative Investment Platform) 是 Microsoft Research 開發的 AI 量化投資平台，專為機器學習驅動的量化策略設計。

**核心優勢**：
- 🚀 **高效能**：二進制數據格式，讀取速度比 pandas 快 3-10 倍
- 🧠 **AI 原生**：內建 LightGBM、XGBoost、Neural Networks 支援
- 📊 **表達式引擎**：強大的因子表達式語言
- 🏭 **企業級**：支援分散式計算和 GPU 加速
- 📚 **豐富因子庫**：內建 Alpha158 等 158 個量化因子

### 在 QuantLab 中的定位

- **雙引擎架構**：與 Backtrader 互補，滿足不同需求
- **數據層**：使用 Qlib v2 官方格式儲存台股歷史數據
- **策略層**：支援 Qlib 表達式策略和機器學習模型
- **整合層**：RD-Agent 生成的因子可直接用於 Qlib 策略

---

## 數據結構

### Qlib v2 官方格式

**目錄結構**：
```
/data/qlib/tw_stock_v2/
├── features/
│   ├── 2330/
│   │   ├── close.day.bin      # 收盤價
│   │   ├── open.day.bin       # 開盤價
│   │   ├── high.day.bin       # 最高價
│   │   ├── low.day.bin        # 最低價
│   │   ├── volume.day.bin     # 成交量
│   │   └── factor.day.bin     # 調整因子
│   ├── 2317/
│   └── ...（2,671 檔股票）
└── calendars/
    └── day.txt                # 交易日曆
```

**檔案格式**：
- **類型**：二進制 `.bin` 檔案（高效壓縮）
- **API**：使用 Qlib `FileFeatureStorage` 讀取
- **欄位**：6 個基本欄位（open, high, low, close, volume, factor）

### 數據特性

**優勢**：
- ✅ 讀取速度快 3-10 倍（相比 pandas CSV）
- ✅ 儲存空間小（二進制壓縮）
- ✅ 支援增量更新
- ✅ 完全兼容 Qlib 官方 API

**限制**：
- ⚠️ 僅支援 OHLCV 基本數據
- ⚠️ 財務指標需從 PostgreSQL 獲取
- ⚠️ 首次同步時間較長（2-4 小時）

### Qlib 表達式範例

```python
# 基本價格數據
'$close'                           # 收盤價
'$open'                            # 開盤價
'$volume'                          # 成交量

# 技術指標
'Mean($close, 5)'                  # 5 日均線
'Std($close, 20)'                  # 20 日標準差
'Max($high, 10)'                   # 10 日最高價
'Min($low, 10)'                    # 10 日最低價

# 時間序列操作
'Ref($close, 1)'                   # 前一日收盤價
'Ref($close, 5)'                   # 5 日前收盤價
'$close / Ref($close, 1) - 1'     # 日報酬率

# 複雜因子
'($close - Mean($close, 20)) / Std($close, 20)'  # Z-score
'Corr($close, $volume, 10)'                       # 價量相關性
'$volume / Mean($volume, 20)'                     # 成交量比率
'Mean($close, 5) / Mean($close, 20) - 1'         # 雙均線比率
```

---

## 數據同步

### 智慧同步（推薦）

**特點**：自動判斷增量/完整/跳過，節省 95%+ 時間

```bash
# 推薦：智慧同步所有股票
./scripts/sync-qlib-smart.sh

# 測試模式（僅 10 檔）
./scripts/sync-qlib-smart.sh --test

# 同步單一股票
./scripts/sync-qlib-smart.sh --stock 2330
```

**智慧同步邏輯**：
```
1. 檢查 Qlib 已有數據
   └─ 無數據 → 📦 完整同步

2. Qlib 最後日期 >= 資料庫最後日期
   └─ ⏭️ 跳過（已是最新）

3. 有新數據
   └─ ➕ 增量同步（只同步新增日期）
```

### 手動同步

```bash
# 完整同步所有股票
docker compose exec backend python /app/scripts/export_to_qlib_v2.py \
  --output-dir /data/qlib/tw_stock_v2 \
  --stocks all \
  --smart

# 限制處理數量（測試用）
docker compose exec backend python /app/scripts/export_to_qlib_v2.py \
  --output-dir /data/qlib/tw_stock_v2 \
  --stocks all \
  --smart \
  --limit 100

# 強制完整重新同步（不使用智慧模式）
docker compose exec backend python /app/scripts/export_to_qlib_v2.py \
  --output-dir /data/qlib/tw_stock_v2 \
  --stocks all
```

### 效能對比

| 同步類型 | 處理數量 | 耗時 | 節省時間 |
|---------|---------|------|---------|
| 首次完整同步 | 2,671 檔 | 2-4 小時 | - |
| 日常增量同步 | ~10 筆新數據 | 2-5 分鐘 | ~95% |
| 已是最新 | 0 筆 | < 30 秒 | ~99% |

### 環境配置

**.env 配置**：
```bash
QLIB_DATA_PATH=/data/qlib/tw_stock_v2
```

**Docker volume 掛載**：
```yaml
volumes:
  - /data/qlib:/data/qlib  # 持久化儲存
```

**Qlib 快取路徑**：
- 容器內：`/tmp/qlib_cache`
- 自動清理舊快取

---

## 策略開發

### Qlib 表達式策略範例

```python
"""
Qlib 表達式策略：均線交叉
"""

import pandas as pd
import numpy as np
from qlib.data import D

# 定義 Qlib 表達式字段
QLIB_FIELDS = [
    'Mean($close, 5)',   # 快線（5 日均線）
    'Mean($close, 20)',  # 慢線（20 日均線）
]

def generate_signals(stock_id: str, start_date: str, end_date: str):
    """生成交易信號"""

    # 使用 Qlib 的 D.features() 獲取數據
    df = D.features(
        instruments=[stock_id],
        fields=QLIB_FIELDS,
        start_time=start_date,
        end_time=end_date
    )

    if df is None or df.empty:
        return pd.DataFrame()

    # 重命名列
    df.columns = ['ma_fast', 'ma_slow']

    # 生成交易信號
    df['signal'] = 0
    df.loc[df['ma_fast'] > df['ma_slow'], 'signal'] = 1   # 買入
    df.loc[df['ma_fast'] < df['ma_slow'], 'signal'] = -1  # 賣出

    return df
```

### Qlib ML 策略範例

```python
"""
Qlib 機器學習策略：LightGBM 多因子
"""

import pandas as pd
import numpy as np
from qlib.data import D
from lightgbm import LGBMRegressor
from sklearn.model_selection import train_test_split

# Alpha158 因子子集
QLIB_FIELDS = [
    # 動量因子
    '$close / Ref($close, 5) - 1',
    '$close / Ref($close, 10) - 1',
    '$close / Ref($close, 20) - 1',

    # 波動率因子
    'Std($close, 5)',
    'Std($close, 10)',
    'Std($close, 20)',

    # 成交量因子
    '$volume / Mean($volume, 5)',
    '$volume / Mean($volume, 20)',

    # 價量相關性
    'Corr($close, $volume, 10)',
]

def train_model(stock_id: str, train_start: str, train_end: str):
    """訓練 LightGBM 模型"""

    # 獲取訓練數據
    df = D.features(
        instruments=[stock_id],
        fields=QLIB_FIELDS + ['Ref($close, -5) / $close - 1'],  # 目標：5 日未來收益
        start_time=train_start,
        end_time=train_end
    )

    # 準備特徵和標籤
    X = df.iloc[:, :-1]
    y = df.iloc[:, -1]

    # 訓練模型
    model = LGBMRegressor(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.05,
        random_state=42
    )
    model.fit(X, y)

    return model

def generate_predictions(model, stock_id: str, pred_start: str, pred_end: str):
    """生成預測信號"""

    # 獲取預測數據
    df = D.features(
        instruments=[stock_id],
        fields=QLIB_FIELDS,
        start_time=pred_start,
        end_time=pred_end
    )

    # 預測未來收益
    df['pred_return'] = model.predict(df)

    # 生成交易信號
    df['signal'] = 0
    df.loc[df['pred_return'] > 0.02, 'signal'] = 1   # 預期上漲 > 2%，買入
    df.loc[df['pred_return'] < -0.02, 'signal'] = -1  # 預期下跌 > 2%，賣出

    return df
```

### 在 QuantLab 中使用

1. **策略編輯頁面**（`/strategies`）：選擇 "Qlib ML" 引擎
2. **使用範本**：點擊 "策略模板" 選擇預設範本
3. **RD-Agent 因子**：從 RD-Agent 生成的因子中選擇並插入
4. **回測執行**：保存策略後執行回測

---

## vs PostgreSQL

### 數據分工

| 數據類型 | 儲存位置 | 用途 | 優勢 |
|---------|---------|------|------|
| **OHLCV 歷史數據** | Qlib `.bin` | 技術分析、回測 | 高速讀取、表達式引擎 |
| **財務指標** | PostgreSQL | 基本面分析 | 結構化查詢、關聯分析 |
| **產業分類** | PostgreSQL | 產業研究 | 關聯查詢、聚合統計 |
| **用戶數據** | PostgreSQL | 策略、回測記錄 | 事務支援、數據一致性 |

### Fallback 機制

**Qlib 數據適配器** (`app/services/qlib_data_adapter.py`)：

```python
def get_qlib_ohlcv(symbol, start_date, end_date):
    """優先使用本地 Qlib 數據，失敗時自動降級到 FinLab API"""

    # 1. 嘗試從 Qlib 本地數據讀取
    if self.qlib_initialized and self._check_qlib_data_exists(symbol):
        df = D.features(instruments=[symbol], fields=fields, ...)
        if df is not None:
            return df  # ✅ 使用本地數據（快 3-10 倍）

    # 2. Fallback: 從 FinLab API 獲取
    df = self.finlab_client.get_ohlcv(symbol, ...)
    return df  # ⚠️ API 調用（較慢但可靠）
```

**效能對比**：
- **本地 Qlib 數據**：0.1-0.3 秒/檔
- **FinLab API**：1-3 秒/檔（HTTP 請求 + 網路延遲）

### 何時使用 Qlib？

✅ **適合使用 Qlib**：
- 大量歷史 OHLCV 數據讀取
- 技術指標計算（使用表達式引擎）
- 機器學習特徵工程
- 全市場回測（2,671 檔股票）

❌ **不適合使用 Qlib**：
- 財務指標查詢（ROE、營業利益率等）
- 產業分類與聚合統計
- 複雜的多表關聯查詢
- 實時數據寫入

---

## 故障排查

### 常見問題

#### 1. Qlib 初始化失敗

**症狀**：
```
qlib.config.C is not initialized
```

**解決方案**：
```python
# 確保在 app/core/qlib_config.py 中正確初始化
import qlib
qlib.init(provider_uri='/data/qlib/tw_stock_v2', region='cn')
```

#### 2. 找不到股票數據

**症狀**：
```
D.features() returns None
```

**檢查步驟**：
```bash
# 1. 確認數據檔案存在
ls /data/qlib/tw_stock_v2/features/2330/

# 2. 檢查檔案權限
ls -la /data/qlib/tw_stock_v2/features/2330/close.day.bin

# 3. 驗證 Qlib 配置
docker compose exec backend python -c "import qlib; qlib.init(provider_uri='/data/qlib/tw_stock_v2'); print('✅ Qlib initialized')"
```

#### 3. 表達式語法錯誤

**常見錯誤**：
```python
# ❌ 錯誤：缺少 $ 符號
'close / Ref(close, 5)'

# ✅ 正確：基本欄位需要 $ 前綴
'$close / Ref($close, 5)'

# ❌ 錯誤：函數名稱錯誤
'Average($close, 5)'

# ✅ 正確：使用 Mean
'Mean($close, 5)'
```

#### 4. 數據同步失敗

**症狀**：
```
ValueError: cannot convert float NaN to integer
```

**解決方案**：
```bash
# 1. 檢查資料庫數據完整性
docker compose exec postgres psql -U quantlab quantlab -c \
  "SELECT COUNT(*) FROM stock_price_daily WHERE stock_id = '2330';"

# 2. 清除舊的 Qlib 數據並重新同步
rm -rf /data/qlib/tw_stock_v2/features/2330/
./scripts/sync-qlib-smart.sh --stock 2330
```

#### 5. 回測速度慢

**優化建議**：
1. 確保使用 Qlib 本地數據（而非 API fallback）
2. 減少不必要的表達式計算
3. 使用批次處理而非逐檔處理
4. 考慮使用 Qlib 的多線程支援

### 日誌調試

```bash
# 查看 Qlib 數據同步日誌
docker compose logs backend | grep -i qlib

# 查看回測執行日誌
docker compose logs celery-worker | grep -i qlib

# 查看數據讀取錯誤
docker compose logs backend | grep -i "D.features"
```

---

## 相關文檔

- [CLAUDE.md](../CLAUDE.md) - 開發指南（Qlib 架構說明）
- [README.md](../README.md) - 量化引擎對比表
- [docs/GUIDES.md](./GUIDES.md) - 使用指南
- [docs/RDAGENT.md](./RDAGENT.md) - RD-Agent 與 Qlib 整合
- [Qlib 官方文檔](https://qlib.readthedocs.io/) - Microsoft Qlib 完整文檔
