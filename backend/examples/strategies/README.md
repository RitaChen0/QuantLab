# 選擇權策略範例 (Option Strategy Examples)

本目錄包含使用選擇權因子的交易策略範例。

## 📋 策略列表

### 1. PCR Contrarian Strategy (PCR 反向策略)

**檔案**: `option_pcr_contrarian.py`

**策略邏輯**:
- 利用選擇權的 Put/Call Ratio (PCR) 作為市場情緒指標
- 當 PCR > 1.2 時，表示市場過度看跌 → 做多（逢低買進）
- 當 PCR < 0.8 時，表示市場過度看漲 → 做空（逢高賣出）
- 基於反向操作邏輯：當大眾恐慌時買進，當大眾貪婪時賣出

**數據來源**:
- 選擇權因子：從 `option_daily_factors` 表匯出到 Qlib
- 標的價格：Qlib 二進制文件（日線資料）

**使用方式**:

```bash
# 基本用法（預設參數：TX, 2024 年全年）
python examples/strategies/option_pcr_contrarian.py

# 自訂參數
python examples/strategies/option_pcr_contrarian.py \
  --symbol TX \
  --start_date 2024-01-01 \
  --end_date 2024-12-31 \
  --pcr_high 1.3 \
  --pcr_low 0.7 \
  --save_chart /tmp/pcr_backtest.png
```

**參數說明**:
- `--symbol`: 標的代碼（TX, MTX）
- `--start_date`: 回測開始日期（YYYY-MM-DD）
- `--end_date`: 回測結束日期（YYYY-MM-DD）
- `--pcr_high`: PCR 高閾值（預設 1.2）
- `--pcr_low`: PCR 低閾值（預設 0.8）
- `--save_chart`: 儲存圖表路徑（可選）

**輸出結果**:
```
[PCR_STRATEGY] Backtest results:
  Total Return: 15.23%
  Annualized Return: 15.50%
  Buy & Hold Return: 8.45%
  Sharpe Ratio: 1.35
  Max Drawdown: -8.20%
  Win Rate: 58.3%
  Total Trades: 42
```

**圖表說明**:
策略會生成三張圖表：
1. **價格與信號圖**: 顯示標的價格和買賣信號點位
2. **PCR 指標圖**: 顯示 PCR 隨時間變化和閾值線
3. **累積收益圖**: 比較策略收益和買入持有收益

---

## 🚀 快速開始

### 前置條件

1. **確保選擇權數據已同步**:
   ```bash
   # 檢查資料庫是否有選擇權因子
   docker compose exec postgres psql -U quantlab quantlab -c \
     "SELECT * FROM option_daily_factors ORDER BY date DESC LIMIT 5;"
   ```

2. **確保數據已匯出到 Qlib**:
   ```bash
   # 執行匯出腳本
   docker compose exec backend python scripts/export_option_to_qlib.py

   # 驗證 Qlib 數據
   docker compose exec backend python -c "
   from qlib.data import D
   import qlib
   qlib.init(provider_uri='/data/qlib/tw_stock_v2')
   df = D.features(['TX'], ['\$pcr'], freq='day')
   print(df.head())
   "
   ```

### 執行策略

```bash
# 進入 Docker 容器
docker compose exec backend bash

# 執行策略
python examples/strategies/option_pcr_contrarian.py --symbol TX --start_date 2024-01-01
```

---

## 📊 選擇權因子說明

### 階段一因子（已可用）

| 因子名稱 | Qlib 欄位 | 說明 | 適用策略 |
|----------|-----------|------|----------|
| PCR Volume | `$pcr` | Put/Call 成交量比值 | 反向策略、情緒指標 |
| PCR OI | `$pcr_oi` | Put/Call 未平倉量比值 | 部位分析 |
| ATM IV | `$atm_iv` | 價平隱含波動率 | 波動率交易 |

### 階段二因子（規劃中）

| 因子名稱 | Qlib 欄位 | 說明 | 適用策略 |
|----------|-----------|------|----------|
| IV Skew | `$iv_skew` | 隱含波動率偏斜 | 尾部風險策略 |
| Max Pain | `$max_pain` | 最大痛苦履約價 | 市場預測 |

### 階段三因子（規劃中）

| 因子名稱 | Qlib 欄位 | 說明 | 適用策略 |
|----------|-----------|------|----------|
| Gamma Exposure | `$gamma_exp` | 造市商 Gamma 曝險 | 流動性預測 |
| Vanna Exposure | `$vanna_exp` | 波動率-價格聯動 | 進階避險 |

---

## 🔧 自訂策略範例

### 1. 使用 PCR + ATM IV 雙因子策略

```python
from qlib.data import D
import qlib

qlib.init(provider_uri='/data/qlib/tw_stock_v2')

# 讀取多個因子
data = D.features(
    instruments=['TX'],
    fields=['$close', '$pcr', '$atm_iv'],
    start_time='2024-01-01',
    end_time='2024-12-31',
    freq='day'
)

# 策略邏輯
# 1. PCR > 1.2 且 ATM IV 升高 → 強烈做多信號
# 2. PCR < 0.8 且 ATM IV 降低 → 強烈做空信號
```

### 2. 在 Backtrader 中使用選擇權因子

```python
import backtrader as bt

class PCRStrategy(bt.Strategy):
    params = (
        ('pcr_high', 1.2),
        ('pcr_low', 0.8),
    )

    def __init__(self):
        # 從外部數據源載入 PCR
        # (需要先用 Qlib 讀取並轉換為 Backtrader feed)
        self.pcr = self.datas[1]  # 假設 PCR 數據在第二個 data feed

    def next(self):
        if self.pcr[0] > self.params.pcr_high:
            if not self.position:
                self.buy()
        elif self.pcr[0] < self.params.pcr_low:
            if self.position:
                self.close()
```

---

## 📈 回測最佳實踐

### 1. 數據驗證

使用策略前先驗證數據品質：

```bash
docker compose exec backend python -c "
from app.repositories.option import OptionDailyFactorRepository
from app.db.base import get_db

db = next(get_db())
factors = OptionDailyFactorRepository.get_by_underlying(
    db, 'TX', limit=30
)

for f in factors:
    print(f'Date: {f.date}, PCR: {f.pcr_volume}, Quality: {f.data_quality_score}')
"
```

### 2. 避免過度擬合

- 使用固定參數（如 PCR 閾值 1.2 / 0.8）
- 不要在同一數據集上反覆優化參數
- 使用滾動窗口驗證（walk-forward analysis）

### 3. 考慮交易成本

範例策略未包含交易成本，實際使用時需加入：
- 期貨手續費（約 0.01%）
- 滑價（約 1-2 ticks）
- 資金成本

### 4. 風險管理

- 設定最大部位限制
- 使用停損（如 -5%）
- 避免在非交易時段下單

---

## 🐛 常見問題

### Q1: 執行策略時出現 "No data found"

**可能原因**:
1. 選擇權數據未同步到資料庫
2. 數據未匯出到 Qlib

**解決方法**:
```bash
# 檢查資料庫
docker compose exec postgres psql -U quantlab quantlab -c \
  "SELECT COUNT(*) FROM option_daily_factors WHERE underlying_id = 'TX';"

# 如果為 0，執行同步任務
docker compose exec backend celery -A app.core.celery_app call \
  app.tasks.sync_option_daily_factors \
  --kwargs '{"underlying_ids": ["TX"], "target_date": "2024-12-15"}'

# 匯出到 Qlib
docker compose exec backend python scripts/export_option_to_qlib.py
```

### Q2: PCR 值為 None

**可能原因**:
- 非交易時段獲取數據
- 選擇權無成交量

**解決方法**:
- 使用歷史日期測試（如 2024-12-13）
- 檢查數據品質評分（quality_score < 0.7 表示數據可能不完整）

### Q3: 圖表無法顯示

**可能原因**:
- Docker 容器內無法顯示 GUI

**解決方法**:
```bash
# 使用 --save_chart 參數儲存為圖片
python examples/strategies/option_pcr_contrarian.py --save_chart /tmp/chart.png

# 從容器複製圖片到本機
docker compose cp backend:/tmp/chart.png ./chart.png
```

---

## 📚 延伸閱讀

- [選擇權功能 - 快速啟動指南](/tmp/option_quickstart_guide.md)
- [階段一完成總結](/tmp/option_stage1_complete_summary.md)
- [Qlib 官方文檔](https://qlib.readthedocs.io/)
- [選擇權交易策略理論](https://www.investopedia.com/options-basics-tutorial-4583012)

---

**文檔版本**: 2025-12-15
**適用階段**: 階段一
**維護者**: 開發團隊
