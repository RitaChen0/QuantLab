# RD-Agent 模型優化 vs 策略優化 - 重要澄清

**發現時間**：2025-12-25 21:38
**重要程度**：⚠️ 高 - 影響實現方案

---

## 🔍 關鍵發現

### RD-Agent 的 `model.py` ≠ 策略優化

**之前的誤解**：
```python
# 我們以為
from rdagent.app.qlib_rd_loop.model import main
main(path="/path/to/strategy.py", step_n=5)  # 優化現有策略
```

**實際情況**：
```python
# 實際是
from rdagent.app.qlib_rd_loop.model import main
main(step_n=5)  # 從零生成新模型（不需要現有策略）
```

---

## 📊 RD-Agent 的三個主要功能

### 1. ✅ 因子挖掘（Factor Mining）

**用途**：生成 Qlib 表達式因子

**入口**：
```python
from rdagent.app.qlib_rd_loop.factor import main
main(step_n=5)
```

**輸出範例**：
```python
# 生成的因子
"Mean($close, 20)"
"Correlation($close, $volume, 10) * ($close / Ref($close, 5) - 1)"
```

**狀態**：✅ 已成功使用（生成了因子 #17）

---

### 2. ✅ 模型生成（Model Generation）

**用途**：從零生成新的 ML 模型架構

**入口**：
```python
from rdagent.app.qlib_rd_loop.model import main
main(step_n=5)
```

**輸出範例**：
```python
# 生成的模型架構
{
    "name": "GRUFinancialModel",
    "architecture": "GRU layer + FC layer",
    "hyperparameters": {
        "learning_rate": 0.001,
        "batch_size": 64,
        "hidden_size": 128
    }
}
```

**狀態**：✅ 已測試成功（生成了 GRU 模型）

**重要**：這**不是**優化現有策略，而是**創建新模型**！

---

### 3. ❓ 策略優化（Strategy Optimization）

**用途**：優化現有 Qlib 策略的參數和邏輯

**預期功能**：
```python
# 理想情況
from rdagent.app.qlib_rd_loop.??? import optimize_strategy

# 輸入現有策略
strategy_code = """
model = lgb.LGBMRegressor(
    n_estimators=100,
    max_depth=5
)
"""

# 執行優化
optimized_strategy = optimize_strategy(
    strategy_code=strategy_code,
    optimization_goal="improve_sharpe_ratio",
    step_n=5
)

# 輸出優化後的策略
# n_estimators=200, max_depth=7, learning_rate=0.05
```

**狀態**：❌ **可能不存在**

---

## 🎯 真相揭露

### RD-Agent `model.py` 的真實用途

**不是**：優化現有策略
**而是**：自動生成新的模型架構

#### 工作流程

```
1. 無需輸入現有策略
   ↓
2. LLM 根據數據特徵提出模型假設
   "金融數據是時間序列，建議使用 GRU"
   ↓
3. 生成模型架構定義
   {name: "GRU", layers: [...], hyperparams: {...}}
   ↓
4. 迭代改進架構
   "如果 GRU 有效，增加層數"
   ↓
5. 輸出最佳架構
```

#### 使用場景

✅ **適用**：
- 從零開始設計模型
- 探索新的模型架構
- AutoML 式的模型搜索

❌ **不適用**：
- 優化已有策略的參數
- 改進現有模型的性能
- 微調特定策略

---

## 💡 對策略優化需求的影響

### 之前的計劃（基於誤解）

```python
# 1. 獲取用戶的策略
strategy = get_strategy(strategy_id=123)

# 2. 用 RD-Agent 優化
optimized = rdagent_model_main(
    path=strategy.code,
    step_n=5
)

# 3. 返回優化後的策略
return optimized
```

### 實際情況

**RD-Agent `model.py` 不支持這個需求！**

---

## 🔄 替代方案

### 方案 A：使用 RD-Agent 生成新模型（已驗證可行）

**適用**：創建全新策略

```python
# 1. 用戶提供需求
user_goal = "創建一個用於台指期貨預測的時間序列模型"

# 2. RD-Agent 生成模型
from rdagent.app.qlib_rd_loop.model import main
main(step_n=5)

# 3. 獲取生成的模型架構
models = parse_generated_models(log_dir)

# 4. 轉換為 Qlib 策略代碼
strategy_code = convert_model_to_qlib_strategy(models[0])

# 5. 保存為新策略
save_strategy(user_id, strategy_code)
```

**優點**：
- ✅ RD-Agent 原生支持
- ✅ 已測試成功
- ✅ 實現簡單

**缺點**：
- ❌ 不是優化現有策略
- ❌ 無法保留用戶的邏輯

---

### 方案 B：手動實現參數優化

**適用**：優化現有策略的參數

```python
def optimize_strategy_parameters(
    strategy_id: int,
    optimization_goal: str
) -> Strategy:
    # 1. 解析策略代碼提取參數
    strategy = get_strategy(strategy_id)
    params = extract_parameters(strategy.code)
    # eg. {"n_estimators": 100, "max_depth": 5}

    # 2. 使用 LLM 建議參數範圍
    param_ranges = llm_suggest_param_ranges(
        current_params=params,
        optimization_goal=optimization_goal
    )
    # eg. {"n_estimators": [100, 200, 300], "max_depth": [5, 7, 10]}

    # 3. 網格搜索或貝葉斯優化
    best_params = grid_search(
        strategy=strategy,
        param_ranges=param_ranges,
        metric="sharpe_ratio"
    )

    # 4. 生成優化後的策略
    optimized_code = strategy.code.replace(
        "n_estimators=100",
        f"n_estimators={best_params['n_estimators']}"
    )

    return save_strategy(optimized_code)
```

**優點**：
- ✅ 保留用戶原始邏輯
- ✅ 參數優化明確
- ✅ 可解釋性強

**缺點**：
- ❌ 需要自己實現（1-2 週）
- ❌ 不使用 RD-Agent 框架
- ❌ 無法改進策略邏輯（只能調參）

---

### 方案 C：LLM 直接優化策略代碼

**適用**：改進策略邏輯和參數

```python
def llm_optimize_strategy(
    strategy_id: int,
    optimization_goal: str,
    max_iterations: int = 5
) -> Strategy:
    strategy = get_strategy(strategy_id)
    baseline_metrics = backtest(strategy)

    current_code = strategy.code

    for i in range(max_iterations):
        # 1. LLM 分析策略
        analysis = llm_analyze_strategy(
            code=current_code,
            metrics=baseline_metrics,
            goal=optimization_goal
        )

        # 2. LLM 生成改進建議
        improvements = llm_suggest_improvements(
            analysis=analysis,
            goal=optimization_goal
        )

        # 3. LLM 生成優化後的代碼
        optimized_code = llm_generate_optimized_code(
            current_code=current_code,
            improvements=improvements
        )

        # 4. 回測驗證
        new_metrics = backtest(optimized_code)

        # 5. 如果改進，保留；否則回退
        if new_metrics["sharpe_ratio"] > baseline_metrics["sharpe_ratio"]:
            current_code = optimized_code
            baseline_metrics = new_metrics
        else:
            break

    return save_strategy(current_code)
```

**優點**：
- ✅ 可改進邏輯和參數
- ✅ 靈活性高
- ✅ 類似 RD-Agent 但更簡單

**缺點**：
- ❌ 需要自己實現（3-5 天）
- ❌ 無 RD-Agent 的 CoSTEER 機制
- ❌ LLM 可能生成錯誤代碼

---

## 📋 結論與建議

### 核心發現

1. ❌ **RD-Agent `model.py` 不能優化現有策略**
2. ✅ **RD-Agent `model.py` 可以生成新模型**
3. ⚠️ **策略優化需求需要另尋方案**

### 建議的實現順序

#### 優先級 P0（1-2 天）

**功能**：AI 模型生成器（使用 RD-Agent）

```
用戶輸入：「為台指期貨創建一個時間序列預測模型」
         ↓
  RD-Agent 生成模型架構
         ↓
  轉換為 Qlib 策略代碼
         ↓
  保存為新策略
```

**優點**：
- 立即可實現
- 使用 RD-Agent 原生功能
- 技術風險低

#### 優先級 P1（3-5 天）

**功能**：LLM 策略優化（不使用 RD-Agent）

```
用戶輸入：優化策略 #123，目標：提升夏普比率
         ↓
  LLM 分析策略弱點
         ↓
  LLM 生成改進建議
         ↓
  LLM 生成優化後代碼
         ↓
  回測驗證
         ↓
  保存優化後策略
```

**優點**：
- 真正的策略優化
- 靈活可控
- 可解釋性強

#### 優先級 P2（1-2 週）

**功能**：參數網格搜索優化

```
用戶輸入：優化策略 #123 的參數
         ↓
  解析參數
         ↓
  LLM 建議搜索範圍
         ↓
  網格搜索或貝葉斯優化
         ↓
  返回最佳參數
```

**優點**：
- 穩定可靠
- 可重現
- 適合參數調優

---

## 🚀 立即行動

### 1. 澄清用戶需求

**問用戶**：

> 您需要的「策略優化」是指：
>
> A. **創建全新策略**
>    - RD-Agent 自動設計模型架構
>    - 從零開始，不基於現有策略
>    - ✅ 立即可實現（1-2 天）
>
> B. **優化現有策略**
>    - 改進現有策略的邏輯和參數
>    - 保留原有結構
>    - ⚠️ 需要自己實現（3-5 天）

### 2. 實現 AI 模型生成器（方案 A）

如果用戶接受「創建新策略」，立即實現：

```python
# backend/app/services/rdagent_service.py

def generate_qlib_model(
    self,
    task_id: int,
    user_goal: str,
    max_iterations: int = 5
) -> str:
    """使用 RD-Agent 生成 Qlib 模型"""
    from rdagent.app.qlib_rd_loop.model import main

    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    os.environ["QLIB_DATA_PATH"] = "/data/qlib/tw_stock_v2"

    # 執行 RD-Agent
    main(step_n=max_iterations)

    # 獲取日誌
    log_dir = self._find_latest_log_dir()

    return log_dir
```

### 3. 或實現 LLM 策略優化（方案 C）

如果用戶堅持優化現有策略：

```python
# backend/app/services/strategy_optimization_service.py

class StrategyOptimizationService:
    def optimize_strategy_with_llm(
        self,
        strategy_id: int,
        optimization_goal: str,
        max_iterations: int = 5
    ) -> Strategy:
        # 實現方案 C 的邏輯
        pass
```

---

## 📁 相關文檔

- **測試報告 1**：`/tmp/RDAGENT_QLIB_TEST_REPORT.md`
- **測試報告 2**：`/tmp/RDAGENT_MODEL_OPTIMIZATION_TEST_COMPLETE.md`
- **實現指南**：`/tmp/QLIB_STRATEGY_OPTIMIZATION_GUIDE.md`

---

**文檔版本**：v1.0
**創建時間**：2025-12-25 21:40
**重要性**：⚠️ 高 - 影響後續實現方向
