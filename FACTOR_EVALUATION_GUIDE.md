# 因子評估功能實作指南

## 📋 概述

本文檔說明因子評估功能的實作，包括：
- 使用 Qlib 計算因子 IC/ICIR
- 計算 Sharpe Ratio、年化報酬率等回測指標
- 儲存評估結果到 `factor_evaluations` 表

## 🏗️ 架構設計

### 1. 資料庫模型 (`app/models/rdagent.py`)

#### FactorEvaluation 表結構

```python
class FactorEvaluation(Base):
    """因子評估結果"""
    __tablename__ = "factor_evaluations"

    # 主鍵和外鍵
    id = Column(Integer, primary_key=True)
    factor_id = Column(Integer, ForeignKey("generated_factors.id"))

    # 評估參數
    stock_pool = Column(String(255))  # 股票池
    start_date = Column(String(20))   # 開始日期
    end_date = Column(String(20))     # 結束日期

    # 因子指標
    ic = Column(Float)                # Information Coefficient
    icir = Column(Float)              # IC Information Ratio
    rank_ic = Column(Float)           # Rank IC (Spearman)
    rank_icir = Column(Float)         # Rank ICIR

    # 回測指標
    sharpe_ratio = Column(Float)      # Sharpe Ratio
    annual_return = Column(Float)     # 年化報酬率
    max_drawdown = Column(Float)      # 最大回撤
    win_rate = Column(Float)          # 勝率

    # 詳細結果（JSON）
    detailed_results = Column(JSON)   # 時間序列、詳細統計等

    # 時間戳
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 2. 因子評估服務 (`app/services/factor_evaluation_service.py`)

#### 核心功能

1. **因子值計算**
   - 使用 Qlib D.features() API 讀取本地數據
   - 支援 Qlib 表達式（如 `Mean($close, 5)`）
   - Fallback 到 FinLab API（當 Qlib 數據不可用時）

2. **IC/ICIR 計算**
   - Pearson IC：因子值與未來收益的相關性
   - Rank IC：因子排名與收益排名的相關性（Spearman）
   - ICIR：IC 的均值除以標準差（資訊比率）

3. **回測策略**
   - 多空對沖策略：
     - 做多因子值最高的 20% 股票
     - 做空因子值最低的 20% 股票
   - 每日重平衡
   - 計算組合收益率

4. **績效指標**
   - Sharpe Ratio：年化超額報酬 / 年化波動率
   - 年化報酬率：複利計算
   - 最大回撤：最大淨值回落幅度
   - 勝率：收益為正的交易日佔比

#### 使用範例

```python
from app.services.factor_evaluation_service import FactorEvaluationService

service = FactorEvaluationService(db)

results = service.evaluate_factor(
    factor_id=1,
    stock_pool="all",           # or "top100"
    start_date="2024-01-01",
    end_date="2024-12-31",
    save_to_db=True
)

# 結果包含
print(f"IC: {results['ic']:.4f}")
print(f"ICIR: {results['icir']:.4f}")
print(f"Sharpe: {results['sharpe_ratio']:.4f}")
print(f"Annual Return: {results['annual_return']:.2%}")
```

### 3. API 端點 (`app/api/v1/factor_evaluation.py`)

#### 可用端點

| 方法 | 端點 | 說明 | 速率限制 |
|------|------|------|----------|
| POST | `/api/v1/factor-evaluation/evaluate` | 評估單個因子 | 5/hour |
| GET | `/api/v1/factor-evaluation/factor/{factor_id}/evaluations` | 獲取評估歷史 | 無 |
| GET | `/api/v1/factor-evaluation/evaluation/{evaluation_id}` | 獲取評估詳情 | 無 |
| DELETE | `/api/v1/factor-evaluation/evaluation/{evaluation_id}` | 刪除評估記錄 | 無 |

#### API 使用範例

```bash
# 1. 登入獲取 token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user","password":"pass"}' \
  | jq -r '.access_token')

# 2. 評估因子
curl -X POST http://localhost:8000/api/v1/factor-evaluation/evaluate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "factor_id": 1,
    "stock_pool": "all",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  }'

# 3. 獲取評估歷史
curl -X GET http://localhost:8000/api/v1/factor-evaluation/factor/1/evaluations \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Celery 異步任務 (`app/tasks/factor_evaluation_tasks.py`)

#### 可用任務

1. **`evaluate_factor_async`** - 異步評估單個因子
   ```python
   from app.tasks.factor_evaluation_tasks import evaluate_factor_async

   # 觸發異步評估
   task = evaluate_factor_async.delay(
       factor_id=1,
       stock_pool="all",
       start_date="2024-01-01",
       end_date="2024-12-31"
   )

   # 檢查任務狀態
   print(task.state)  # PENDING, STARTED, SUCCESS, FAILURE
   result = task.get()  # 阻塞等待結果
   ```

2. **`batch_evaluate_factors`** - 批量評估多個因子
   ```python
   from app.tasks.factor_evaluation_tasks import batch_evaluate_factors

   # 批量評估
   task = batch_evaluate_factors.delay(
       factor_ids=[1, 2, 3, 4, 5],
       stock_pool="top100",
       start_date="2024-01-01",
       end_date="2024-12-31"
   )
   ```

3. **`update_factor_metrics`** - 更新因子表中的指標
   ```python
   from app.tasks.factor_evaluation_tasks import update_factor_metrics

   # 從最新評估記錄更新 generated_factors 表
   task = update_factor_metrics.delay(factor_id=1)
   ```

## 📊 評估指標說明

### IC (Information Coefficient)

- **定義**：因子值與未來收益的 Pearson 相關係數
- **計算公式**：
  ```
  IC_t = Corr(factor_values_t, returns_{t+1})
  Mean IC = mean(IC_t for all t)
  ```
- **解讀**：
  - IC > 0：因子有正向預測能力
  - IC < 0：因子有反向預測能力
  - |IC| > 0.05：通常被認為是有效因子
  - |IC| > 0.10：強因子

### ICIR (IC Information Ratio)

- **定義**：IC 的均值除以標準差
- **計算公式**：
  ```
  ICIR = Mean(IC) / Std(IC)
  ```
- **解讀**：
  - ICIR > 0.5：穩定的因子
  - ICIR > 1.0：非常穩定的因子

### Rank IC / Rank ICIR

- **定義**：使用 Spearman 秩相關（對異常值更穩健）
- **優點**：不受極端值影響
- **使用場景**：因子值或收益分佈不均勻時

### Sharpe Ratio

- **定義**：年化超額報酬除以年化波動率
- **計算公式**：
  ```
  Sharpe = (Annual Return - Risk Free Rate) / Annual Volatility
  ```
- **解讀**：
  - Sharpe > 1.0：良好
  - Sharpe > 2.0：優秀
  - Sharpe > 3.0：卓越

### 年化報酬率

- **計算公式**：
  ```
  Annual Return = (1 + Total Return)^(1 / n_years) - 1
  ```

### 最大回撤

- **定義**：從峰值到谷底的最大跌幅
- **計算方式**：
  ```
  Drawdown_t = (NAV_t - Max(NAV_{0:t})) / Max(NAV_{0:t})
  Max Drawdown = min(Drawdown_t for all t)
  ```

### 勝率

- **定義**：收益為正的交易日佔比
- **計算公式**：
  ```
  Win Rate = Count(returns > 0) / Count(all returns)
  ```

## 🧪 測試

### 1. 基礎測試

```bash
# 運行簡單測試（檢查 API 端點）
./test_factor_evaluation_simple.sh
```

### 2. 完整測試

```bash
# 運行完整測試（需要有因子數據）
./test_factor_evaluation.sh
```

### 3. 手動測試

1. 打開 API 文檔：http://localhost:8000/docs
2. 導航到「因子評估」分類
3. 測試 POST /factor-evaluation/evaluate 端點

## 📝 使用流程

### 標準工作流程

1. **生成因子**（使用 RD-Agent）
   ```bash
   POST /api/v1/rdagent/factor-mining
   ```

2. **評估因子**
   ```bash
   POST /api/v1/factor-evaluation/evaluate
   {
     "factor_id": 1,
     "stock_pool": "all",
     "start_date": "2024-01-01",
     "end_date": "2024-12-31"
   }
   ```

3. **查看結果**
   ```bash
   GET /api/v1/factor-evaluation/factor/1/evaluations
   ```

4. **批量評估**（使用 Celery）
   ```python
   from app.tasks.factor_evaluation_tasks import batch_evaluate_factors

   batch_evaluate_factors.delay(
       factor_ids=[1, 2, 3, 4, 5],
       stock_pool="all"
   )
   ```

5. **更新因子指標**
   ```python
   from app.tasks.factor_evaluation_tasks import update_factor_metrics

   update_factor_metrics.delay(factor_id=1)
   ```

## ⚠️ 注意事項

1. **評估時間**
   - 單個因子評估約需 5-30 秒（取決於股票數量和時間範圍）
   - 建議使用異步任務進行批量評估

2. **資料依賴**
   - 需要 Qlib 本地數據或 FinLab API
   - 確保 `QLIB_DATA_PATH` 正確設定

3. **速率限制**
   - 評估端點：5 requests/hour
   - 其他端點：無限制

4. **記憶體使用**
   - 大規模評估（2000+ 股票 × 2 年數據）可能需要 2-4 GB 記憶體
   - 建議分批評估

5. **錯誤處理**
   - Celery 任務自動重試 3 次
   - 失敗的因子會被跳過，不影響其他因子

## 🔍 調試

### 查看 Celery 任務日誌

```bash
# 實時查看 worker 日誌
docker compose logs -f celery-worker

# 搜尋評估相關日誌
docker compose logs celery-worker | grep "factor evaluation"
```

### 查看資料庫記錄

```bash
# 連接到資料庫
docker compose exec postgres psql -U quantlab -d quantlab

# 查詢評估記錄
SELECT id, factor_id, ic, icir, sharpe_ratio, annual_return, created_at
FROM factor_evaluations
ORDER BY created_at DESC
LIMIT 10;
```

### 檢查 API 日誌

```bash
# 查看後端日誌
docker compose logs -f backend | grep "factor_evaluation"
```

## 📚 相關文件

- `CLAUDE.md` - 專案開發指南
- `RDAGENT_INTEGRATION_GUIDE.md` - RD-Agent 整合文件
- `DATABASE_SCHEMA_REPORT.md` - 資料庫架構報告

## 🚀 未來改進

1. **更多評估指標**
   - Turnover Rate（換手率）
   - Information Ratio（資訊比率）
   - Alpha / Beta

2. **視覺化**
   - IC 時間序列圖表
   - 累積報酬曲線
   - 回撤圖

3. **因子組合**
   - 多因子組合評估
   - 因子權重優化

4. **行業中性**
   - 行業中性化處理
   - 市值中性化

5. **交易成本**
   - 考慮手續費和滑價
   - 更真實的回測結果
