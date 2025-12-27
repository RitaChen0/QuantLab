# RD-Agent Qlib 策略優化指南（簡化版）

**核心優勢**：RD-Agent 原生支援 Qlib，無需自訂 Scenario！

**當前狀態**：系統已有 5 個 Qlib 策略，可直接使用

**預計工作量**：1 週（40 小時）← 比 Backtrader 版本減少 60%

---

## 🎯 為何只用 Qlib？

### RD-Agent 原生支援

RD-Agent 就是為 Qlib 設計的：

```python
# RD-Agent 官方提供的 Qlib 場景
from rdagent.scenarios.qlib.experiment.model_experiment import QlibModelScenario

# 直接使用，無需自訂！
scenario = QlibModelScenario()
```

### 當前系統資源

**已有 Qlib 策略**（5 個）：
1. Qlib 均線交叉策略（ID: 41）
2. LightGBM 預測模型（ID: 45）
3. Alpha158 + LightGBM（ID: 49）
4. 其他 2 個

**已有 Qlib 數據**：
- 日線：`/data/qlib/tw_stock_v2/`（2007-至今）
- 分鐘線：`/data/qlib/tw_stock_minute/`（7 年）
- 期貨：TXCONT, MTXCONT

**已有 Qlib 因子**（17 個）：
- 從 `generated_factors` 表中的 Qlib 表達式
- 可直接插入策略優化

### 技術優勢對比

| 項目 | Backtrader 版本 | Qlib 版本 |
|------|----------------|-----------|
| **實現複雜度** | 高（需自訂 Scenario） | 低（官方支援） |
| **開發時間** | 2-3 週 | 1 週 |
| **測試難度** | 高（兩套系統） | 低（單一系統） |
| **維護成本** | 高 | 低 |
| **RD-Agent 整合** | 需自行實現 | 開箱即用 |

---

## 🚀 簡化實現方案

### 階段 1：RD-Agent Qlib 整合（2-3 天）

#### 1.1 安裝 RD-Agent Qlib 模組

**檢查當前版本**：

```bash
docker compose exec backend pip show rdagent
```

**確認 Qlib 場景可用**：

```python
# backend/test_rdagent_qlib.py
from rdagent.scenarios.qlib.experiment.model_experiment import QlibModelScenario

scenario = QlibModelScenario()
print("✅ RD-Agent Qlib 場景已就緒")
```

#### 1.2 實現策略優化服務

**文件**：`backend/app/services/rdagent_service.py`

```python
def execute_qlib_strategy_optimization(
    self,
    task_id: int,
    strategy_id: int,
    optimization_goal: str,
    max_iterations: int = 5,
    llm_model: str = "gpt-4-turbo"
) -> str:
    """執行 Qlib 策略優化

    Args:
        task_id: RD-Agent 任務 ID
        strategy_id: Qlib 策略 ID
        optimization_goal: 優化目標
        max_iterations: 最大迭代次數
        llm_model: LLM 模型

    Returns:
        log_dir: 日誌目錄路徑
    """
    from rdagent.scenarios.qlib.experiment.model_experiment import QlibModelScenario
    from rdagent.core.evolving_framework import EvolvingFramework

    logger.info(f"Starting Qlib strategy optimization for strategy {strategy_id}")

    # Step 1: 獲取原始策略
    strategy = self.db.query(Strategy).filter(
        Strategy.id == strategy_id,
        Strategy.engine_type == 'qlib'
    ).first()

    if not strategy:
        raise ValueError(f"Qlib strategy {strategy_id} not found")

    # Step 2: 回測原始策略（獲取基準）
    baseline_metrics = self._backtest_qlib_strategy(strategy)

    logger.info(f"Baseline metrics: {baseline_metrics}")

    # Step 3: 構建優化 Prompt
    prompt = self._build_qlib_optimization_prompt(
        strategy=strategy,
        baseline_metrics=baseline_metrics,
        optimization_goal=optimization_goal
    )

    # Step 4: 創建 RD-Agent 進化框架
    scenario = QlibModelScenario()
    framework = EvolvingFramework(
        scenario=scenario,
        max_iterations=max_iterations
    )

    # Step 5: 執行優化循環
    logger.info(f"Starting evolution with {max_iterations} iterations...")

    results = framework.evolve(
        baseline_code=strategy.code,
        baseline_metrics=baseline_metrics,
        optimization_goal=prompt,
        llm_config={
            "model": llm_model,
            "api_key": os.getenv("OPENAI_API_KEY")
        }
    )

    # Step 6: 保存日誌
    log_dir = self._save_qlib_optimization_logs(strategy_id, results)

    logger.info(f"Optimization completed. Log directory: {log_dir}")

    return log_dir


def _backtest_qlib_strategy(self, strategy: Strategy) -> Dict[str, float]:
    """回測 Qlib 策略

    Args:
        strategy: Qlib 策略物件

    Returns:
        metrics: 績效指標
    """
    import qlib
    from qlib.data import D
    from qlib.backtest import backtest
    from qlib.contrib.strategy import TopkDropoutStrategy

    # 初始化 Qlib
    qlib.init(provider_uri='/data/qlib/tw_stock_v2', region='tw')

    # 執行策略代碼獲取預測
    # （這裡需要根據策略類型動態執行）
    exec_globals = {}
    exec(strategy.code, exec_globals)

    # 假設策略會生成一個 predictions DataFrame
    predictions = exec_globals.get('predictions')

    if predictions is None:
        raise ValueError("Strategy code must generate 'predictions' DataFrame")

    # 執行回測
    strategy_obj = TopkDropoutStrategy(
        model=predictions,
        topk=10,
        n_drop=5
    )

    backtest_result = backtest(
        predictions,
        strategy=strategy_obj,
        executor_config={
            "time_per_step": "day",
            "generate_portfolio_metrics": True
        }
    )

    # 提取指標
    analysis = backtest_result['analysis']

    return {
        "sharpe_ratio": float(analysis.get('sharpe', 0)),
        "annual_return": float(analysis.get('annualized_return', 0)),
        "max_drawdown": float(analysis.get('max_drawdown', 0)),
        "information_ratio": float(analysis.get('information_ratio', 0)),
        "total_return": float(analysis.get('total_return', 0))
    }


def _build_qlib_optimization_prompt(
    self,
    strategy: Strategy,
    baseline_metrics: Dict[str, float],
    optimization_goal: str
) -> str:
    """構建 Qlib 策略優化 Prompt

    Args:
        strategy: 原始策略
        baseline_metrics: 基準指標
        optimization_goal: 優化目標

    Returns:
        prompt: 完整 Prompt
    """
    # 查詢可用的生成因子
    available_factors = self.db.query(GeneratedFactor).filter(
        GeneratedFactor.user_id == strategy.user_id
    ).limit(20).all()

    factors_list = "\n".join([
        f"  - {f.name}: {f.formula} (IC: {f.ic or 'N/A'})"
        for f in available_factors
    ])

    prompt = f"""
# Qlib 策略優化任務

## 原始策略

**名稱**: {strategy.name}
**描述**: {strategy.description or "無描述"}

**代碼**:
```python
{strategy.code}
```

## 當前績效（基準）

- **Sharpe Ratio**: {baseline_metrics.get('sharpe_ratio', 0):.3f}
- **Annual Return**: {baseline_metrics.get('annual_return', 0):.2%}
- **Max Drawdown**: {baseline_metrics.get('max_drawdown', 0):.2%}
- **Information Ratio**: {baseline_metrics.get('information_ratio', 0):.3f}

## 優化目標

{optimization_goal}

## 可用的生成因子

以下是 RD-Agent 之前生成的因子，可以加入策略中：

{factors_list}

## Qlib 策略優化方向

### 1. 因子優化

**增加新因子**:
```python
# 原始
QLIB_FIELDS = ['$close', 'Mean($close, 20)']

# 優化：增加波動率和成交量因子
QLIB_FIELDS = [
    '$close',
    'Mean($close, 20)',
    'Std($close, 20)',           # 新增：波動率
    'Correlation($close, $volume, 10)',  # 新增：價量相關性
]
```

**因子組合加權**:
```python
# 多因子組合
combined_factor = (
    0.4 * momentum_factor +
    0.3 * volatility_factor +
    0.3 * volume_factor
)
```

### 2. 模型優化（如果是 ML 策略）

**LightGBM 參數調整**:
```python
# 原始
model = lgb.LGBMRegressor(n_estimators=100, max_depth=5)

# 優化
model = lgb.LGBMRegressor(
    n_estimators=200,      # 增加樹數量
    max_depth=7,           # 增加深度
    learning_rate=0.05,    # 降低學習率
    num_leaves=63,         # 調整葉子數
    min_child_samples=30   # 防止過擬合
)
```

**特徵工程**:
```python
# 增加交互項
df['ma_cross'] = df['ma5'] - df['ma20']
df['price_volume'] = df['close'] * df['volume']
```

### 3. 風險控制

**持倉限制**:
```python
# 增加最大持倉限制
strategy = TopkDropoutStrategy(
    model=predictions,
    topk=10,              # 原始：20
    n_drop=5,
    method_sell="bottom",
    method_buy="top"
)
```

**換手率控制**:
```python
# 降低換手率
if abs(new_weight - old_weight) < 0.05:
    new_weight = old_weight  # 小於 5% 變動不調整
```

## 輸出格式

請提供：

### 1. 問題分析
（描述當前策略的主要問題）

### 2. 改進方案
（具體的優化建議，分點列出）

### 3. 優化後代碼
```python
# 完整的 Qlib 策略代碼
```

### 4. 預期改進
- Sharpe Ratio: X.XX → X.XX (+XX%)
- Annual Return: XX% → XX% (+XX%)
- Max Drawdown: XX% → XX% (改善 XX%)
"""

    return prompt


def _save_qlib_optimization_logs(
    self,
    strategy_id: int,
    results: Any
) -> str:
    """保存 Qlib 優化日誌

    Args:
        strategy_id: 策略 ID
        results: RD-Agent 優化結果

    Returns:
        log_dir: 日誌目錄路徑
    """
    from pathlib import Path
    import pickle
    import json
    from datetime import datetime

    # 創建日誌目錄
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(f"/app/log/qlib_strategy_opt_{strategy_id}_{timestamp}")
    log_dir.mkdir(parents=True, exist_ok=True)

    # 保存結果
    with open(log_dir / "results.pkl", "wb") as f:
        pickle.dump(results, f)

    # 保存摘要（JSON 格式）
    summary = {
        "strategy_id": strategy_id,
        "timestamp": timestamp,
        "iterations": len(results.get("iterations", [])),
        "best_metrics": results.get("best_metrics", {})
    }

    with open(log_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    return str(log_dir)
```

---

### 階段 2：結果解析與保存（1-2 天）

#### 2.1 解析優化結果

```python
def parse_qlib_optimization_results(
    self,
    log_dir: str
) -> List[Dict[str, Any]]:
    """解析 Qlib 策略優化結果

    Args:
        log_dir: 日誌目錄

    Returns:
        optimized_strategies: 優化後的策略列表
    """
    from pathlib import Path
    import pickle

    log_path = Path(log_dir)

    # 讀取結果
    with open(log_path / "results.pkl", "rb") as f:
        results = pickle.load(f)

    # 提取所有迭代的策略
    strategies = []

    for iteration in results.get("iterations", []):
        strategy_data = {
            "code": iteration.get("code"),
            "metrics": iteration.get("metrics"),
            "description": iteration.get("description"),
            "loop_num": iteration.get("loop_num")
        }
        strategies.append(strategy_data)

    # 按 Sharpe Ratio 排序
    strategies.sort(
        key=lambda x: x.get("metrics", {}).get("sharpe_ratio", 0),
        reverse=True
    )

    return strategies
```

#### 2.2 保存優化後的策略

```python
def save_optimized_qlib_strategy(
    self,
    task_id: int,
    original_strategy_id: int,
    optimized_code: str,
    optimized_metrics: Dict[str, float],
    description: str = None
) -> Strategy:
    """保存優化後的 Qlib 策略

    Args:
        task_id: RD-Agent 任務 ID
        original_strategy_id: 原始策略 ID
        optimized_code: 優化後的代碼
        optimized_metrics: 優化後的指標
        description: 優化說明

    Returns:
        strategy: 新策略物件
    """
    from app.models.strategy import Strategy, StrategyStatus

    # 獲取原始策略
    original = self.db.query(Strategy).filter(
        Strategy.id == original_strategy_id
    ).first()

    # 創建優化後的策略
    optimized_strategy = Strategy(
        user_id=original.user_id,
        name=f"{original.name} (RD-Agent 優化 v1)",
        description=description or f"RD-Agent 自動優化版本\n\n原始策略 ID: {original_strategy_id}\n\n{original.description}",
        code=optimized_code,
        engine_type='qlib',
        status=StrategyStatus.DRAFT,
        parameters={
            "rdagent_task_id": task_id,
            "original_strategy_id": original_strategy_id,
            "optimization_metrics": optimized_metrics
        }
    )

    self.db.add(optimized_strategy)
    self.db.commit()
    self.db.refresh(optimized_strategy)

    logger.info(f"Saved optimized strategy {optimized_strategy.id}")

    return optimized_strategy
```

---

### 階段 3：Celery 任務整合（1 天）

**更新**：`backend/app/tasks/rdagent_tasks.py`

```python
@celery_app.task(bind=True, name="app.tasks.run_strategy_optimization_task")
def run_strategy_optimization_task(self: Task, task_id: int):
    """執行策略優化任務（Qlib 版本）"""
    db: Session = SessionLocal()

    try:
        service = RDAgentService(db)
        task = db.query(RDAgentTask).filter(RDAgentTask.id == task_id).first()

        if not task:
            logger.error(f"Task {task_id} not found")
            return {"status": "error", "message": "Task not found"}

        # 更新為執行中
        service.update_task_status(task_id, TaskStatus.RUNNING)

        # 提取參數
        strategy_id = task.input_params.get("strategy_id")
        optimization_goal = task.input_params.get("optimization_goal")
        max_iterations = task.input_params.get("max_iterations", 5)
        llm_model = task.input_params.get("llm_model", "gpt-4-turbo")

        # 驗證是 Qlib 策略
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy or strategy.engine_type != 'qlib':
            raise ValueError(f"Strategy {strategy_id} is not a Qlib strategy")

        logger.info(f"Starting Qlib strategy optimization for strategy {strategy_id}")

        # Step 1: 執行優化
        log_dir = service.execute_qlib_strategy_optimization(
            task_id=task_id,
            strategy_id=strategy_id,
            optimization_goal=optimization_goal,
            max_iterations=max_iterations,
            llm_model=llm_model
        )

        # Step 2: 解析結果
        optimized_strategies = service.parse_qlib_optimization_results(log_dir)

        if not optimized_strategies:
            raise ValueError("No optimized strategies generated")

        # Step 3: 獲取最佳版本
        best_strategy = optimized_strategies[0]

        # Step 4: 保存優化後的策略
        optimized_strategy_obj = service.save_optimized_qlib_strategy(
            task_id=task_id,
            original_strategy_id=strategy_id,
            optimized_code=best_strategy["code"],
            optimized_metrics=best_strategy["metrics"],
            description=best_strategy.get("description")
        )

        # Step 5: 計算成本
        llm_calls, llm_cost = service.calculate_llm_costs(log_dir)

        # Step 6: 更新任務狀態
        baseline_metrics = service._backtest_qlib_strategy(strategy)
        optimized_metrics = best_strategy["metrics"]

        service.update_task_status(
            task_id,
            TaskStatus.COMPLETED,
            result={
                "original_strategy_id": strategy_id,
                "optimized_strategy_id": optimized_strategy_obj.id,
                "baseline_metrics": baseline_metrics,
                "optimized_metrics": optimized_metrics,
                "improvements": {
                    "sharpe_ratio": optimized_metrics["sharpe_ratio"] - baseline_metrics["sharpe_ratio"],
                    "annual_return": optimized_metrics["annual_return"] - baseline_metrics["annual_return"],
                    "max_drawdown": optimized_metrics["max_drawdown"] - baseline_metrics["max_drawdown"]
                },
                "total_iterations": len(optimized_strategies),
                "message": "Qlib strategy optimization completed successfully"
            },
            llm_calls=llm_calls,
            llm_cost=llm_cost
        )

        logger.info(f"Strategy optimization task {task_id} completed")
        return {"status": "success", "task_id": task_id}

    except Exception as e:
        logger.error(f"Strategy optimization task {task_id} failed: {str(e)}")
        service.update_task_status(task_id, TaskStatus.FAILED, error_message=str(e))
        return {"status": "error", "message": str(e)}

    finally:
        db.close()
```

---

## 🧪 測試計劃

### 測試策略 1：均線策略優化

**原始策略**（ID: 41）：
- 5 日均線 × 20 日均線交叉

**優化目標**：
```
提升夏普比率，建議方向：
1. 調整均線週期
2. 增加成交量確認
3. 增加波動率過濾
```

**預期結果**：
- Sharpe: 0.8 → 1.3
- Return: 12% → 18%

### 測試策略 2：LightGBM 模型優化

**原始策略**（ID: 45）：
- 18 個技術指標
- LightGBM 預測

**優化目標**：
```
提升預測準確度，建議方向：
1. 增加因子（從 generated_factors 選擇高 IC 因子）
2. 調整 LightGBM 超參數
3. 增加特徵工程（交互項）
```

**預期結果**：
- IC: 0.05 → 0.08
- Sharpe: 1.5 → 2.0

---

## 💰 成本估算（簡化版）

### 開發成本

| 階段 | 時間 | 說明 |
|------|------|------|
| RD-Agent 整合 | 2-3 天 | 使用官方 Qlib 場景 |
| 結果解析 | 1-2 天 | 提取優化結果 |
| Celery 任務 | 1 天 | 整合異步執行 |
| 測試與修正 | 2 天 | 測試與優化 |
| **總計** | **1 週** | **40 小時** |

**人力成本**：$2,000-$3,000（假設時薪 $50）

### 運營成本

| 項目 | 成本 |
|------|------|
| LLM API（5 次迭代） | $2-4 USD |
| Qlib 回測 | 忽略不計 |
| **總計** | **$2-4 USD/次** |

### ROI

**假設**：
- 月活用戶：50 人（只有 Qlib 用戶）
- 使用頻率：2 次/月
- 收費：$8 USD/次

**月收入**：50 × 2 × $8 = $800
**月成本**：50 × 2 × $3 = $300
**淨利**：$500/月

**投資回收期**：$2,500 / $500 = **5 個月**

---

## ✅ 實現檢查清單

### 第 1-2 天：RD-Agent 整合

- [ ] 驗證 RD-Agent Qlib 場景可用
- [ ] 實現 `execute_qlib_strategy_optimization()`
- [ ] 實現 `_backtest_qlib_strategy()`
- [ ] 實現 `_build_qlib_optimization_prompt()`
- [ ] 測試單輪優化

### 第 3-4 天：結果處理

- [ ] 實現 `parse_qlib_optimization_results()`
- [ ] 實現 `save_optimized_qlib_strategy()`
- [ ] 實現 `_save_qlib_optimization_logs()`
- [ ] 測試結果保存

### 第 5 天：Celery 整合

- [ ] 更新 `run_strategy_optimization_task()`
- [ ] 增加 Qlib 策略驗證
- [ ] 測試異步執行

### 第 6-7 天：測試與部署

- [ ] 測試均線策略優化
- [ ] 測試 ML 策略優化
- [ ] 修正 Bug
- [ ] 文檔撰寫
- [ ] 部署上線

---

## 🎯 立即可執行的測試

### 測試 RD-Agent Qlib 場景

```bash
# 進入容器
docker compose exec backend bash

# 測試 RD-Agent Qlib 模組
python << 'PYEOF'
from rdagent.scenarios.qlib.experiment.model_experiment import QlibModelScenario

try:
    scenario = QlibModelScenario()
    print("✅ RD-Agent Qlib 場景已就緒")
    print(f"📊 Scenario 類型：{type(scenario)}")
except Exception as e:
    print(f"❌ 錯誤：{e}")
PYEOF
```

### 測試 Qlib 回測

```bash
# 測試現有策略的回測
python << 'PYEOF'
import qlib
from qlib.data import D

# 初始化 Qlib
qlib.init(provider_uri='/data/qlib/tw_stock_v2', region='tw')

# 讀取台指期貨數據
data = D.features(
    ['TXCONT'],
    ['$close', 'Mean($close, 20)'],
    start_time='2024-01-01',
    end_time='2024-12-31'
)

print("✅ Qlib 數據讀取成功")
print(f"📊 數據形狀：{data.shape}")
print(data.tail())
PYEOF
```

---

## 📚 參考資源

### RD-Agent Qlib 文檔

- **官方範例**：https://github.com/microsoft/RD-Agent/tree/main/rdagent/scenarios/qlib
- **Qlib 策略優化**：https://github.com/microsoft/RD-Agent/blob/main/rdagent/scenarios/qlib/experiment/model_experiment.py
- **CoSTEER 框架**：https://github.com/microsoft/RD-Agent/blob/main/rdagent/core/evolving_framework.py

### Qlib 文檔

- **回測 API**：https://qlib.readthedocs.io/en/latest/component/backtest.html
- **策略 API**：https://qlib.readthedocs.io/en/latest/component/strategy.html
- **Alpha158**：https://qlib.readthedocs.io/en/latest/component/data.html#alpha158

---

## 🎉 總結

### 為何選擇 Qlib？

✅ **原生支援**：RD-Agent 為 Qlib 設計，無需自訂
✅ **已有數據**：完整的 Qlib 數據基礎設施
✅ **已有策略**：5 個現成的 Qlib 策略可優化
✅ **開發快速**：1 週 vs Backtrader 版本的 3 週
✅ **成本更低**：$2,500 vs $5,000

### 下一步

1. **測試 RD-Agent Qlib 場景**（10 分鐘）
2. **實現基礎優化功能**（2-3 天）
3. **測試均線策略優化**（1 天）
4. **完善功能並上線**（2-3 天）

**立即開始？還是先測試 RD-Agent Qlib 模組？**

---

**文檔版本**：v1.0
**創建時間**：2025-12-25 21:45
**預計實現時間**：1 週（40 小時）
