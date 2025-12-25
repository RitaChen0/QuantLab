# RD-Agent 策略優化實現指南

**目標**：實現 RD-Agent 的策略優化功能，自動改進現有交易策略

**當前狀態**：僅有 API 框架，核心邏輯未實現
**預計工作量**：2-3 週（80-120 小時）
**難度等級**：🔴 高

---

## 📋 功能概述

### 輸入
- **策略 ID**：要優化的現有策略
- **優化目標**：例如「提升夏普比率至 2.0」「降低最大回撤至 15% 以下」
- **LLM 模型**：`gpt-4-turbo` 或 `gpt-4`
- **最大迭代次數**：5-20 次

### 輸出
- **優化後的策略代碼**
- **優化前後對比**
  - Sharpe Ratio: 1.2 → 1.8 (+50%)
  - Max Drawdown: 25% → 18% (-28%)
  - Annual Return: 15% → 22% (+47%)
- **改進建議說明**
  - 修改了哪些參數
  - 增加了哪些邏輯
  - 為什麼這樣改進

### 工作原理（CoSTEER）

```
1. 分析原始策略
   ↓
2. 識別弱點（回測結果差的部分）
   ↓
3. LLM 生成改進假設
   ↓
4. 生成改進後的策略代碼
   ↓
5. 執行回測並評估
   ↓
6. 對比原始策略 vs 改進策略
   ↓
7. 如果改進不足，重複步驟 3-6
   ↓
8. 返回最佳版本
```

---

## 🏗️ 實現步驟

### 階段 1：基礎框架（1-2 天）

#### 1.1 擴展 RDAgentService

**文件**：`backend/app/services/rdagent_service.py`

新增方法：

```python
def execute_strategy_optimization(
    self,
    task_id: int,
    strategy_id: int,
    optimization_goal: str,
    max_iterations: int = 5,
    llm_model: str = "gpt-4-turbo"
) -> str:
    """執行策略優化

    Args:
        task_id: RD-Agent 任務 ID
        strategy_id: 要優化的策略 ID
        optimization_goal: 優化目標描述
        max_iterations: 最大迭代次數
        llm_model: LLM 模型

    Returns:
        log_dir: 日誌目錄路徑
    """
    logger.info(f"Starting strategy optimization for strategy {strategy_id}")

    # Step 1: 獲取原始策略
    strategy = self.db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise ValueError(f"Strategy {strategy_id} not found")

    # Step 2: 回測原始策略（獲取基準指標）
    baseline_metrics = self._backtest_strategy(strategy)

    # Step 3: 構建優化 Prompt
    optimization_prompt = self._build_optimization_prompt(
        strategy=strategy,
        baseline_metrics=baseline_metrics,
        optimization_goal=optimization_goal
    )

    # Step 4: 執行 RD-Agent 優化循環
    log_dir = self._run_rdagent_optimization(
        strategy_id=strategy_id,
        prompt=optimization_prompt,
        max_iterations=max_iterations,
        llm_model=llm_model
    )

    return log_dir


def _backtest_strategy(self, strategy: Strategy) -> Dict[str, float]:
    """回測策略並返回績效指標

    Args:
        strategy: 策略物件

    Returns:
        metrics: {
            "sharpe_ratio": 1.2,
            "annual_return": 0.15,
            "max_drawdown": -0.25,
            "win_rate": 0.55,
            "total_trades": 120
        }
    """
    from app.services.backtest_service import BacktestService
    from app.schemas.backtest import BacktestCreate

    # 創建回測請求
    backtest_request = BacktestCreate(
        strategy_id=strategy.id,
        start_datetime="2024-01-01",
        end_datetime="2024-12-31",
        initial_capital=100000.0,
        stock_ids=["TXCONT"]  # 使用台指期貨連續合約
    )

    # 執行回測
    backtest_service = BacktestService(self.db)
    backtest = backtest_service.create_backtest(
        user_id=strategy.user_id,
        data=backtest_request
    )

    # 執行並等待結果
    result = backtest_service.execute_backtest(backtest.id)

    # 提取指標
    return {
        "sharpe_ratio": result.sharpe_ratio or 0.0,
        "annual_return": result.annual_return or 0.0,
        "max_drawdown": result.max_drawdown or 0.0,
        "win_rate": result.win_rate or 0.0,
        "total_trades": result.total_trades or 0
    }


def _build_optimization_prompt(
    self,
    strategy: Strategy,
    baseline_metrics: Dict[str, float],
    optimization_goal: str
) -> str:
    """構建策略優化的 LLM Prompt

    Args:
        strategy: 原始策略
        baseline_metrics: 基準績效指標
        optimization_goal: 優化目標

    Returns:
        prompt: 完整的優化 Prompt
    """
    prompt = f"""
# 策略優化任務

## 原始策略

**名稱**: {strategy.name}
**描述**: {strategy.description or "無描述"}
**引擎**: {strategy.engine_type}

**代碼**:
```python
{strategy.code}
```

## 當前績效（基準）

- **Sharpe Ratio**: {baseline_metrics['sharpe_ratio']:.2f}
- **Annual Return**: {baseline_metrics['annual_return']:.2%}
- **Max Drawdown**: {baseline_metrics['max_drawdown']:.2%}
- **Win Rate**: {baseline_metrics['win_rate']:.2%}
- **Total Trades**: {baseline_metrics['total_trades']}

## 優化目標

{optimization_goal}

## 要求

1. **分析策略弱點**：識別當前策略的問題（例如：過度交易、止損不當、參數不佳）
2. **提出改進方案**：給出具體的改進建議（例如：優化參數、增加過濾條件、改進止損邏輯）
3. **生成優化後代碼**：輸出完整的改進後策略代碼（保持 {strategy.engine_type} 格式）
4. **預期改進效果**：說明預期在哪些指標上有改進

## 可用技術

### Backtrader 策略常用優化方向

1. **參數優化**
   - 均線週期（5-200 日）
   - RSI 門檻（20-80）
   - MACD 參數（快線、慢線、信號線）

2. **進出場邏輯**
   - 增加確認信號（多個指標共振）
   - 過濾噪音（成交量確認、ATR 過濾）
   - 避免假突破（回測確認、時間過濾）

3. **風險管理**
   - 固定止損（百分比或 ATR 倍數）
   - 動態止盈（追蹤止盈）
   - 倉位管理（凱利公式、固定比例）

4. **交易成本**
   - 減少過度交易（持倉最低時間）
   - 考慮滑點和手續費

### Qlib 策略常用優化方向

1. **因子優化**
   - 增加新因子
   - 因子組合加權
   - 因子標準化

2. **模型優化**
   - 調整模型參數（GBDT 深度、學習率）
   - 特徵工程（因子衍生、交互項）
   - 訓練窗口調整

3. **風險控制**
   - 最大持倉限制
   - 行業中性
   - 換手率控制

## 輸出格式

請按以下格式輸出：

### 1. 策略分析

（描述當前策略的問題）

### 2. 改進方案

（列出具體的改進建議）

### 3. 優化後代碼

```python
# 完整的策略代碼
```

### 4. 預期改進

- Sharpe Ratio: X.XX → X.XX (+XX%)
- Annual Return: XX% → XX% (+XX%)
- Max Drawdown: -XX% → -XX% (改善 XX%)
"""
    return prompt


def _run_rdagent_optimization(
    self,
    strategy_id: int,
    prompt: str,
    max_iterations: int,
    llm_model: str
) -> str:
    """執行 RD-Agent 優化循環

    這是核心邏輯，需要整合 RD-Agent 的 CoSTEER 機制

    Args:
        strategy_id: 策略 ID
        prompt: 優化 Prompt
        max_iterations: 最大迭代次數
        llm_model: LLM 模型

    Returns:
        log_dir: 日誌目錄路徑
    """
    import os
    from pathlib import Path

    # TODO: 整合 RD-Agent 核心邏輯
    # 參考：https://github.com/microsoft/RD-Agent/blob/main/rdagent/scenarios/qlib/model/

    # 暫時返回模擬路徑
    log_dir = Path(f"/app/log/strategy_opt_{strategy_id}")
    log_dir.mkdir(parents=True, exist_ok=True)

    return str(log_dir)
```

#### 1.2 更新 Celery 任務

**文件**：`backend/app/tasks/rdagent_tasks.py`

修改 `run_strategy_optimization_task` 函數：

```python
@celery_app.task(bind=True, name="app.tasks.run_strategy_optimization_task")
def run_strategy_optimization_task(self: Task, task_id: int):
    """執行策略優化任務"""
    db: Session = SessionLocal()

    try:
        service = RDAgentService(db)
        task = db.query(RDAgentTask).filter(RDAgentTask.id == task_id).first()

        if not task:
            logger.error(f"Task {task_id} not found")
            return {"status": "error", "message": "Task not found"}

        # 更新為執行中
        service.update_task_status(task_id, TaskStatus.RUNNING)

        logger.info(f"Starting strategy optimization task {task_id}")
        logger.info(f"Task parameters: {task.input_params}")

        # 提取任務參數
        strategy_id = task.input_params.get("strategy_id")
        optimization_goal = task.input_params.get("optimization_goal")
        max_iterations = task.input_params.get("max_iterations", 5)
        llm_model = task.input_params.get("llm_model", "gpt-4-turbo")

        # ========== 步驟 1: 執行策略優化 ==========
        logger.info(f"Step 1: Executing RD-Agent optimization with {max_iterations} iterations...")
        log_dir = service.execute_strategy_optimization(
            task_id=task_id,
            strategy_id=strategy_id,
            optimization_goal=optimization_goal,
            max_iterations=max_iterations,
            llm_model=llm_model
        )
        logger.info(f"RD-Agent optimization completed. Log directory: {log_dir}")

        # ========== 步驟 2: 解析優化結果 ==========
        logger.info("Step 2: Parsing optimization results...")
        optimized_strategies = service.parse_optimization_results(log_dir)
        logger.info(f"Parsed {len(optimized_strategies)} optimized versions")

        # ========== 步驟 3: 回測最佳版本 ==========
        logger.info("Step 3: Backtesting best optimized version...")
        best_strategy = optimized_strategies[0]  # 取第一個（應該是最佳）

        # 保存優化後的策略到資料庫
        from app.models.strategy import Strategy, StrategyStatus
        original_strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()

        optimized_strategy_obj = Strategy(
            user_id=original_strategy.user_id,
            name=f"{original_strategy.name} (Optimized v1)",
            description=best_strategy.get("description"),
            code=best_strategy.get("code"),
            engine_type=original_strategy.engine_type,
            status=StrategyStatus.DRAFT,
            parameters=best_strategy.get("parameters")
        )
        db.add(optimized_strategy_obj)
        db.commit()
        db.refresh(optimized_strategy_obj)

        # 回測優化後的策略
        optimized_metrics = service._backtest_strategy(optimized_strategy_obj)

        # ========== 步驟 4: 計算 LLM 成本 ==========
        llm_calls, llm_cost = service.calculate_llm_costs(log_dir)

        # ========== 步驟 5: 更新任務為完成 ==========
        service.update_task_status(
            task_id,
            TaskStatus.COMPLETED,
            result={
                "original_strategy_id": strategy_id,
                "optimized_strategy_id": optimized_strategy_obj.id,
                "baseline_metrics": service._backtest_strategy(original_strategy),
                "optimized_metrics": optimized_metrics,
                "improvements": {
                    "sharpe_ratio": optimized_metrics["sharpe_ratio"] - baseline["sharpe_ratio"],
                    "annual_return": optimized_metrics["annual_return"] - baseline["annual_return"],
                    "max_drawdown": optimized_metrics["max_drawdown"] - baseline["max_drawdown"]
                },
                "log_directory": log_dir,
                "message": "Strategy optimization completed successfully"
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

### 階段 2：RD-Agent 整合（5-7 天）

這是最複雜的部分，需要深入研究 RD-Agent 源碼。

#### 2.1 研究 RD-Agent 官方實現

**參考**：
- https://github.com/microsoft/RD-Agent/tree/main/rdagent/scenarios/qlib
- https://github.com/microsoft/RD-Agent/blob/main/rdagent/core/evolving_framework.py

**關鍵模組**：
1. **Evolving Framework**：CoSTEER 進化框架
2. **Scenario**：定義場景（Qlib vs Backtrader）
3. **Hypothesis**：假設生成
4. **Experiment**：實驗執行
5. **Feedback**：反饋分析

#### 2.2 創建 Backtrader Scenario

RD-Agent 預設支援 Qlib，需要為 Backtrader 創建自訂 Scenario。

**新建文件**：`backend/app/rdagent/backtrader_scenario.py`

```python
"""RD-Agent Backtrader Scenario

定義 RD-Agent 如何優化 Backtrader 策略
"""

from rdagent.core.scenario import Scenario
from rdagent.core.evolving_framework import Hypothesis, Experiment, Feedback
from typing import Dict, Any, List


class BacktraderScenario(Scenario):
    """Backtrader 策略優化場景"""

    def generate_hypothesis(
        self,
        baseline_code: str,
        baseline_metrics: Dict[str, float],
        optimization_goal: str,
        previous_feedback: List[Feedback] = None
    ) -> Hypothesis:
        """生成優化假設

        Args:
            baseline_code: 原始策略代碼
            baseline_metrics: 基準績效指標
            optimization_goal: 優化目標
            previous_feedback: 上一輪的反饋

        Returns:
            hypothesis: 優化假設
        """
        # TODO: 構建 Prompt 並調用 LLM
        # 生成改進建議和預期效果
        pass

    def create_experiment(self, hypothesis: Hypothesis) -> Experiment:
        """基於假設創建實驗

        Args:
            hypothesis: 優化假設

        Returns:
            experiment: 實驗物件（包含優化後的策略代碼）
        """
        # TODO: 將假設轉換為可執行的策略代碼
        pass

    def run_experiment(self, experiment: Experiment) -> Dict[str, Any]:
        """執行實驗（回測優化後的策略）

        Args:
            experiment: 實驗物件

        Returns:
            results: 回測結果
        """
        # TODO: 執行 Backtrader 回測
        # 返回績效指標
        pass

    def analyze_feedback(
        self,
        experiment: Experiment,
        results: Dict[str, Any],
        baseline_metrics: Dict[str, float]
    ) -> Feedback:
        """分析實驗反饋

        Args:
            experiment: 實驗物件
            results: 實驗結果
            baseline_metrics: 基準指標

        Returns:
            feedback: 反饋物件（包含改進建議）
        """
        # TODO: 對比實驗結果與基準
        # 分析改進或惡化的部分
        # 生成下一輪優化方向
        pass
```

#### 2.3 整合 CoSTEER 進化循環

**修改**：`backend/app/services/rdagent_service.py`

```python
def _run_rdagent_optimization(
    self,
    strategy_id: int,
    prompt: str,
    max_iterations: int,
    llm_model: str
) -> str:
    """執行 RD-Agent 優化循環"""

    from rdagent.core.evolving_framework import EvolvingFramework
    from app.rdagent.backtrader_scenario import BacktraderScenario

    # 創建進化框架
    framework = EvolvingFramework(
        scenario=BacktraderScenario(),
        max_iterations=max_iterations,
        llm_model=llm_model
    )

    # 獲取原始策略
    strategy = self.db.query(Strategy).filter(Strategy.id == strategy_id).first()
    baseline_metrics = self._backtest_strategy(strategy)

    # 執行進化循環
    results = framework.evolve(
        baseline_code=strategy.code,
        baseline_metrics=baseline_metrics,
        optimization_goal=prompt
    )

    # 保存日誌
    log_dir = self._save_optimization_logs(strategy_id, results)

    return log_dir
```

---

### 階段 3：結果解析與展示（2-3 天）

#### 3.1 解析優化結果

**新增方法**：`RDAgentService.parse_optimization_results()`

```python
def parse_optimization_results(self, log_dir: str) -> List[Dict[str, Any]]:
    """解析策略優化結果

    從日誌中提取所有優化版本的策略代碼和績效指標

    Args:
        log_dir: RD-Agent 日誌目錄

    Returns:
        strategies: 優化後的策略列表，按績效排序
    """
    from pathlib import Path
    import pickle

    log_path = Path(log_dir)
    strategies = []

    # 遍歷所有迭代目錄
    for loop_dir in sorted(log_path.glob("Loop_*")):
        # 讀取優化後的策略代碼
        strategy_file = loop_dir / "optimized_strategy.pkl"
        if strategy_file.exists():
            with open(strategy_file, "rb") as f:
                strategy_data = pickle.load(f)
                strategies.append(strategy_data)

    # 按 Sharpe Ratio 排序
    strategies.sort(
        key=lambda x: x.get("metrics", {}).get("sharpe_ratio", 0),
        reverse=True
    )

    return strategies
```

#### 3.2 前端展示（前端開發）

**新建頁面**：`frontend/pages/rdagent/strategy-optimization.vue`

展示內容：
- 原始策略 vs 優化後策略（代碼對比）
- 績效指標對比（圖表）
- 改進說明（文字）
- 一鍵應用優化（按鈕）

---

### 階段 4：測試與優化（3-5 天）

#### 4.1 單元測試

**新建文件**：`backend/tests/services/test_strategy_optimization.py`

```python
import pytest
from app.services.rdagent_service import RDAgentService
from app.models.strategy import Strategy

def test_backtest_strategy():
    """測試策略回測功能"""
    # TODO: 創建測試策略
    # TODO: 執行回測
    # TODO: 驗證結果格式

def test_build_optimization_prompt():
    """測試優化 Prompt 構建"""
    # TODO: 創建測試數據
    # TODO: 生成 Prompt
    # TODO: 驗證 Prompt 內容

def test_optimization_cycle():
    """測試完整優化循環"""
    # TODO: 創建簡單策略
    # TODO: 執行優化
    # TODO: 驗證改進效果
```

#### 4.2 整合測試

**測試流程**：
1. 創建簡單的均線策略
2. 執行優化（max_iterations=2）
3. 驗證生成新策略
4. 驗證回測執行成功
5. 驗證績效指標改善

#### 4.3 性能優化

**關鍵問題**：
- 回測可能很慢（每次迭代 1-2 分鐘）
- LLM 調用成本高

**優化方案**：
- 使用快速回測窗口（6 個月而非 1 年）
- 限制迭代次數（5-10 次）
- 快取回測結果
- 使用 GPT-4-turbo（更便宜）

---

## 📊 預期效果

### 輸入範例

```json
{
  "strategy_id": 2,
  "optimization_goal": "提升夏普比率至 2.0 以上，同時降低最大回撤至 15% 以下",
  "llm_model": "gpt-4-turbo",
  "max_iterations": 5
}
```

### 輸出範例

```json
{
  "task_id": 25,
  "status": "COMPLETED",
  "result": {
    "original_strategy_id": 2,
    "optimized_strategy_id": 156,
    "baseline_metrics": {
      "sharpe_ratio": 1.2,
      "annual_return": 0.15,
      "max_drawdown": -0.25,
      "win_rate": 0.52
    },
    "optimized_metrics": {
      "sharpe_ratio": 1.85,
      "annual_return": 0.22,
      "max_drawdown": -0.14,
      "win_rate": 0.58
    },
    "improvements": {
      "sharpe_ratio": +0.65,
      "annual_return": +0.07,
      "max_drawdown": +0.11,
      "win_rate": +0.06
    },
    "optimization_summary": "優化重點：1) 將短均線週期從 5 調整為 8，2) 增加 RSI < 30 的確認條件避免假突破，3) 加入 ATR 止損降低最大回撤"
  },
  "llm_calls": 42,
  "llm_cost": 3.25
}
```

---

## 🚧 技術挑戰

### 挑戰 1：RD-Agent 不原生支援 Backtrader

**問題**：RD-Agent 預設為 Qlib 設計

**解決方案**：
1. 研究 RD-Agent 的 Qlib Scenario 實現
2. 抽象出通用介面
3. 實現 Backtrader Scenario
4. 測試兼容性

**預計時間**：3-4 天

### 挑戰 2：回測耗時

**問題**：每次迭代需要完整回測（1-2 分鐘）

**解決方案**：
1. 使用較短的回測窗口（6 個月）
2. 平行執行多個候選策略
3. 快取不變的部分（數據載入）

**預計時間**：1-2 天

### 挑戰 3：LLM 生成代碼品質

**問題**：LLM 可能生成語法錯誤或邏輯錯誤的代碼

**解決方案**：
1. 在 Prompt 中提供完整的策略模板
2. 增加代碼驗證步驟（語法檢查）
3. 提供錯誤反饋給 LLM 讓其修正
4. 限制允許修改的部分（只改參數或邏輯）

**預計時間**：2-3 天

### 挑戰 4：優化目標多樣化

**問題**：不同用戶有不同優化目標

**解決方案**：
1. 支援多目標優化（Pareto 前沿）
2. 允許用戶指定權重（例如 Sharpe 60%, Drawdown 40%）
3. 提供預設優化模板（穩健型、激進型）

**預計時間**：2 天

---

## 📁 實現檢查清單

### 第 1 週

- [ ] 研究 RD-Agent 官方文檔和源碼
- [ ] 實現 `_backtest_strategy()` 方法
- [ ] 實現 `_build_optimization_prompt()` 方法
- [ ] 實現基礎的 `execute_strategy_optimization()` 框架
- [ ] 更新 Celery 任務（`run_strategy_optimization_task`）

### 第 2 週

- [ ] 實現 `BacktraderScenario` 類
- [ ] 整合 RD-Agent CoSTEER 進化框架
- [ ] 實現 `_run_rdagent_optimization()` 核心邏輯
- [ ] 實現 `parse_optimization_results()` 方法
- [ ] 測試單輪優化循環

### 第 3 週

- [ ] 編寫單元測試
- [ ] 執行整合測試
- [ ] 性能優化（快取、平行化）
- [ ] 前端頁面開發
- [ ] 文檔撰寫
- [ ] 上線部署

---

## 💰 成本估算

### 開發成本

- **開發時間**：80-120 小時（2-3 週）
- **人力成本**：假設時薪 $50，總計 $4,000-$6,000

### 運營成本（每次優化）

- **LLM 成本**：$2-5 USD（5-10 次迭代）
- **運算成本**：忽略不計（回測在本地執行）
- **總計**：約 $3-5 USD/次

### ROI 分析

**假設**：
- 月活用戶 100 人
- 平均每人每月優化 2 次策略
- 每次收費 $10 USD（Level 4+ 會員）

**收入**：100 * 2 * $10 = $2,000/月

**成本**：100 * 2 * $3 = $600/月（LLM）

**淨利**：$1,400/月

**投資回收期**：$5,000 / $1,400 ≈ 3.6 個月

---

## 🎯 總結

### 可行性

✅ **技術可行**：RD-Agent 提供完整框架，主要工作是適配 Backtrader

✅ **成本可控**：LLM 成本 $3-5/次，可轉嫁給用戶

⚠️ **開發複雜**：需 2-3 週全職開發，需熟悉 RD-Agent 源碼

### 優先級建議

**如果要實現策略優化，建議順序**：

1. **優先實現因子挖掘的自動評估**（1 週）
   - 生成因子後自動計算 IC
   - 自動回測並排序
   - ROI 更高，風險更低

2. **再實現簡化版策略優化**（2 週）
   - 僅支援參數優化（不改邏輯）
   - 使用窮舉法而非 RD-Agent
   - 降低複雜度

3. **最後實現完整版策略優化**（3 週）
   - 整合 RD-Agent CoSTEER
   - 支援邏輯優化
   - 完整功能

### 立即可做的事

**無需等待完整實現，現在就可以做**：

1. **手動策略優化服務**
   - 用戶提交策略和優化目標
   - 人工分析並優化
   - 測試市場需求

2. **簡單的 A/B 測試功能**
   - 允許用戶創建策略變體
   - 平行回測對比
   - 選擇最佳版本

---

**文檔版本**：v1.0
**創建時間**：2025-12-25 21:30
**預計實現時間**：2-3 週（80-120 小時）
