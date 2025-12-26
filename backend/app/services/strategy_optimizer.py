"""
策略優化服務

使用 LLM 分析策略代碼和回測結果，提供優化建議
"""

from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from loguru import logger
import json
import os

# 導入所有相關模型（確保 SQLAlchemy relationships 可以解析）
from app.db.base import Base  # noqa
from app.models.user import User  # noqa
from app.models.strategy import Strategy
from app.models.backtest import Backtest, BacktestStatus
from app.models.backtest_result import BacktestResult
from app.models.rdagent import RDAgentTask  # noqa
from app.models.telegram_notification import TelegramNotification  # noqa
from app.models.stock import Stock  # noqa
from app.models.stock_industry import StockIndustry  # noqa


class StrategyOptimizer:
    """策略優化器 - 基於 LLM 的策略分析和優化建議"""

    def __init__(self, db: Session):
        self.db = db
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")

    def analyze_strategy(
        self,
        strategy_id: int,
        optimization_goal: str,
        llm_model: str = "gpt-4-turbo"
    ) -> Dict[str, Any]:
        """分析策略並生成優化建議

        Args:
            strategy_id: 策略 ID
            optimization_goal: 優化目標（如："提升 Sharpe Ratio 至 2.0 以上"）
            llm_model: LLM 模型名稱

        Returns:
            analysis_result: 包含問題診斷、優化建議、優化代碼等
        """
        logger.info(f"Analyzing strategy {strategy_id} with goal: {optimization_goal}")

        # 步驟 1: 讀取策略
        strategy = self.db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise ValueError(f"Strategy {strategy_id} not found")

        # 步驟 2: 讀取最近的回測結果
        recent_backtest = self._get_latest_backtest(strategy_id)
        if not recent_backtest:
            raise ValueError(f"No completed backtest found for strategy {strategy_id}")

        backtest_result = recent_backtest.result
        if not backtest_result:
            raise ValueError(f"No backtest result found for strategy {strategy_id}")

        # 步驟 3: 問題診斷
        issues = self._diagnose_issues(backtest_result)
        logger.info(f"Diagnosed {len(issues)} issues: {[i['type'] for i in issues]}")

        # 步驟 4: 使用 LLM 生成優化建議
        llm_suggestions, llm_calls, llm_cost = self._generate_llm_suggestions(
            strategy=strategy,
            backtest_result=backtest_result,
            issues=issues,
            optimization_goal=optimization_goal,
            llm_model=llm_model
        )

        # 步驟 5: 生成優化後的策略代碼（可選）
        optimized_code = self._generate_optimized_code(
            original_code=strategy.code,
            suggestions=llm_suggestions,
            engine_type=strategy.engine_type,
            llm_model=llm_model
        )

        # 步驟 6: 構建分析結果
        analysis_result = {
            "strategy_info": {
                "id": strategy.id,
                "name": strategy.name,
                "engine_type": strategy.engine_type,
                "code_length": len(strategy.code)
            },
            "current_performance": {
                "sharpe_ratio": float(backtest_result.sharpe_ratio) if backtest_result.sharpe_ratio else None,
                "annual_return": float(backtest_result.annual_return) if backtest_result.annual_return else None,
                "max_drawdown": float(backtest_result.max_drawdown) if backtest_result.max_drawdown else None,
                "win_rate": float(backtest_result.win_rate) if backtest_result.win_rate else None,
                "total_trades": backtest_result.total_trades,
                "backtest_id": recent_backtest.id
            },
            "issues_diagnosed": issues,
            "optimization_suggestions": llm_suggestions,
            "optimized_code": optimized_code,
            "llm_metadata": {
                "model": llm_model,
                "calls": llm_calls,
                "cost": llm_cost
            }
        }

        return analysis_result

    def _get_latest_backtest(self, strategy_id: int) -> Optional[Backtest]:
        """獲取策略的最新完成回測

        Args:
            strategy_id: 策略 ID

        Returns:
            最新的已完成回測，如果沒有則返回 None
        """
        return self.db.query(Backtest).filter(
            Backtest.strategy_id == strategy_id,
            Backtest.status == BacktestStatus.COMPLETED
        ).order_by(
            Backtest.completed_at.desc()
        ).first()

    def _diagnose_issues(self, result: BacktestResult) -> List[Dict[str, Any]]:
        """診斷回測結果的問題

        Args:
            result: 回測結果

        Returns:
            問題列表，每個問題包含 type, severity, description, current_value, target_value
        """
        issues = []

        # 診斷 1: Sharpe Ratio 過低
        if result.sharpe_ratio is not None and result.sharpe_ratio < 1.0:
            issues.append({
                "type": "low_sharpe_ratio",
                "severity": "high" if result.sharpe_ratio < 0.5 else "medium",
                "description": "風險調整後收益率過低",
                "current_value": float(result.sharpe_ratio),
                "target_value": 1.5,
                "recommendation": "需要提高收益或降低波動率"
            })

        # 診斷 2: Max Drawdown 過大
        if result.max_drawdown is not None and abs(result.max_drawdown) > 0.20:
            issues.append({
                "type": "high_drawdown",
                "severity": "high" if abs(result.max_drawdown) > 0.30 else "medium",
                "description": "最大回撤過大，風險控制不足",
                "current_value": float(result.max_drawdown),
                "target_value": -0.15,
                "recommendation": "需要增加停損機制或減小倉位"
            })

        # 診斷 3: Win Rate 過低
        if result.win_rate is not None and result.win_rate < 0.40:
            issues.append({
                "type": "low_win_rate",
                "severity": "medium",
                "description": "勝率過低",
                "current_value": float(result.win_rate),
                "target_value": 0.50,
                "recommendation": "需要改進進場條件或持倉時間"
            })

        # 診斷 4: Annual Return 過低
        if result.annual_return is not None and result.annual_return < 0.10:
            issues.append({
                "type": "low_return",
                "severity": "high" if result.annual_return < 0.05 else "medium",
                "description": "年化收益率過低",
                "current_value": float(result.annual_return),
                "target_value": 0.15,
                "recommendation": "需要提高交易頻率或改進選股邏輯"
            })

        # 診斷 5: 交易次數異常
        if result.total_trades is not None:
            if result.total_trades < 10:
                issues.append({
                    "type": "too_few_trades",
                    "severity": "medium",
                    "description": "交易次數過少，樣本不足",
                    "current_value": result.total_trades,
                    "target_value": 30,
                    "recommendation": "放寬進場條件或縮短持倉週期"
                })
            elif result.total_trades > 500:
                issues.append({
                    "type": "too_many_trades",
                    "severity": "low",
                    "description": "交易次數過多，手續費成本高",
                    "current_value": result.total_trades,
                    "target_value": 200,
                    "recommendation": "提高進場門檻或延長持倉週期"
                })

        # 診斷 6: Profit Factor 過低
        if result.profit_factor is not None and result.profit_factor < 1.2:
            issues.append({
                "type": "low_profit_factor",
                "severity": "high",
                "description": "盈虧比過低",
                "current_value": float(result.profit_factor),
                "target_value": 1.5,
                "recommendation": "需要改進停利停損策略"
            })

        return issues

    def _generate_llm_suggestions(
        self,
        strategy: Strategy,
        backtest_result: BacktestResult,
        issues: List[Dict[str, Any]],
        optimization_goal: str,
        llm_model: str
    ) -> Tuple[List[Dict[str, Any]], int, float]:
        """使用 LLM 生成優化建議

        Args:
            strategy: 策略對象
            backtest_result: 回測結果
            issues: 診斷的問題列表
            optimization_goal: 優化目標
            llm_model: LLM 模型名稱

        Returns:
            (suggestions, llm_calls, llm_cost): 優化建議、LLM 調用次數、成本
        """
        logger.info(f"Generating LLM suggestions with {llm_model}...")

        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY not set, returning rule-based suggestions")
            return self._generate_rule_based_suggestions(issues), 0, 0.0

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)

            # 構建 prompt
            prompt = self._build_optimization_prompt(
                strategy=strategy,
                backtest_result=backtest_result,
                issues=issues,
                optimization_goal=optimization_goal
            )

            logger.info(f"Calling OpenAI API with model {llm_model}...")
            logger.info(f"Prompt length: {len(prompt)} characters")

            # 調用 LLM
            response = client.chat.completions.create(
                model=llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位專業的量化交易策略優化專家。你的任務是分析交易策略代碼和回測結果，提供具體可行的優化建議。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=2000
            )

            # 提取建議
            suggestions_text = response.choices[0].message.content

            # 解析建議（嘗試提取 JSON，如果失敗則使用純文本）
            suggestions = self._parse_llm_response(suggestions_text)

            # 計算成本
            usage = response.usage
            llm_calls = 1
            input_cost = (usage.prompt_tokens / 1000) * 0.01  # GPT-4-turbo input
            output_cost = (usage.completion_tokens / 1000) * 0.03  # GPT-4-turbo output
            llm_cost = round(input_cost + output_cost, 4)

            logger.info(f"✅ LLM suggestions generated")
            logger.info(f"   Tokens: {usage.prompt_tokens} input + {usage.completion_tokens} output")
            logger.info(f"   Cost: ${llm_cost}")

            return suggestions, llm_calls, llm_cost

        except Exception as e:
            logger.error(f"LLM suggestion generation failed: {e}")
            logger.warning("Falling back to rule-based suggestions")
            return self._generate_rule_based_suggestions(issues), 0, 0.0

    def _build_optimization_prompt(
        self,
        strategy: Strategy,
        backtest_result: BacktestResult,
        issues: List[Dict[str, Any]],
        optimization_goal: str
    ) -> str:
        """構建優化 prompt

        Args:
            strategy: 策略對象
            backtest_result: 回測結果
            issues: 問題列表
            optimization_goal: 優化目標

        Returns:
            完整的 prompt 字符串
        """
        # 格式化績效指標
        performance_summary = f"""
當前績效指標：
- Sharpe Ratio: {backtest_result.sharpe_ratio:.2f if backtest_result.sharpe_ratio else 'N/A'}
- 年化收益率: {backtest_result.annual_return * 100:.2f if backtest_result.annual_return else 'N/A'}%
- 最大回撤: {backtest_result.max_drawdown * 100:.2f if backtest_result.max_drawdown else 'N/A'}%
- 勝率: {backtest_result.win_rate * 100:.2f if backtest_result.win_rate else 'N/A'}%
- 總交易次數: {backtest_result.total_trades or 'N/A'}
- 盈虧比: {backtest_result.profit_factor:.2f if backtest_result.profit_factor else 'N/A'}
"""

        # 格式化問題清單
        issues_summary = "\n".join([
            f"- [{issue['severity'].upper()}] {issue['description']} (當前: {issue['current_value']}, 目標: {issue['target_value']})"
            for issue in issues
        ])

        prompt = f"""
# 策略優化任務

## 優化目標
{optimization_goal}

## 策略資訊
- 名稱: {strategy.name}
- 引擎類型: {strategy.engine_type}
- 描述: {strategy.description or '無'}

{performance_summary}

## 問題診斷
{issues_summary if issues else '未發現明顯問題'}

## 策略代碼
```python
{strategy.code[:2000]}  # 限制長度避免 token 溢出
{'...(代碼已截斷)' if len(strategy.code) > 2000 else ''}
```

## 請提供優化建議

請分析以上策略代碼和回測結果，提供 3-5 個具體可行的優化建議。每個建議應包含：

1. **優化類型**（參數調整/邏輯改進/風險控制/其他）
2. **問題描述**（指出當前存在的問題）
3. **優化方案**（具體的修改建議）
4. **預期效果**（優化後的預期改善）
5. **優先級**（高/中/低）

請以 JSON 格式返回建議：

```json
[
  {{
    "type": "參數調整",
    "problem": "移動平均線週期過短，導致過度交易",
    "solution": "將 MA 週期從 10 調整為 20，減少假突破",
    "expected_improvement": "預期交易次數減少 30%，Sharpe Ratio 提升至 1.5",
    "priority": "high",
    "code_changes": "self.sma = bt.indicators.SMA(period=20)  # 原本 10"
  }}
]
```
"""
        return prompt

    def _parse_llm_response(self, response_text: str) -> List[Dict[str, Any]]:
        """解析 LLM 返回的優化建議

        Args:
            response_text: LLM 返回的文本

        Returns:
            優化建議列表
        """
        try:
            # 嘗試提取 JSON
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                suggestions = json.loads(json_str)
                if isinstance(suggestions, list):
                    return suggestions

            # 如果沒有 JSON，嘗試直接解析
            suggestions = json.loads(response_text)
            if isinstance(suggestions, list):
                return suggestions

        except Exception as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")

        # 解析失敗，返回純文本建議
        return [{
            "type": "general",
            "problem": "自動解析失敗",
            "solution": response_text[:500],
            "expected_improvement": "請參考建議手動優化",
            "priority": "medium"
        }]

    def _generate_rule_based_suggestions(
        self,
        issues: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """基於規則生成優化建議（LLM 不可用時的後備方案）

        Args:
            issues: 問題列表

        Returns:
            優化建議列表
        """
        suggestions = []

        # 規則映射表
        rule_mapping = {
            "low_sharpe_ratio": {
                "type": "風險控制",
                "solution": "增加停損機制，限制單筆虧損不超過 2%；或調整倉位大小，降低波動率",
                "expected_improvement": "預期 Sharpe Ratio 提升 30-50%"
            },
            "high_drawdown": {
                "type": "風險控制",
                "solution": "實施動態停損（如跟蹤停損），在趨勢反轉時及時出場；或添加資金管理規則，限制最大持倉比例",
                "expected_improvement": "預期最大回撤降低至 15% 以內"
            },
            "low_win_rate": {
                "type": "邏輯改進",
                "solution": "優化進場條件，添加趨勢確認指標（如 ADX）；或延長持倉時間，避免頻繁止損",
                "expected_improvement": "預期勝率提升至 50% 以上"
            },
            "low_return": {
                "type": "參數調整",
                "solution": "提高倉位比例（如從 50% 提升至 80%）；或放寬進場條件，增加交易機會",
                "expected_improvement": "預期年化收益提升 50-100%"
            },
            "too_few_trades": {
                "type": "參數調整",
                "solution": "放寬進場條件（降低指標門檻）；或縮短持倉週期，提高資金周轉率",
                "expected_improvement": "預期交易次數增加至 30+ 筆"
            },
            "too_many_trades": {
                "type": "參數調整",
                "solution": "提高進場門檻（增加確認條件）；或延長持倉週期，減少過度交易",
                "expected_improvement": "預期交易次數降低 40%，手續費成本減半"
            },
            "low_profit_factor": {
                "type": "停利停損優化",
                "solution": "調整停利停損比例（如從 1:1 改為 2:1）；或使用動態停利，讓盈利單跑得更遠",
                "expected_improvement": "預期盈虧比提升至 1.5 以上"
            }
        }

        for issue in issues:
            issue_type = issue["type"]
            if issue_type in rule_mapping:
                rule = rule_mapping[issue_type]
                suggestions.append({
                    "type": rule["type"],
                    "problem": issue["description"],
                    "solution": rule["solution"],
                    "expected_improvement": rule["expected_improvement"],
                    "priority": issue["severity"]
                })

        # 如果沒有找到問題，提供通用建議
        if not suggestions:
            suggestions.append({
                "type": "一般優化",
                "problem": "策略表現良好，可進行微調",
                "solution": "考慮回測更長時間週期，驗證策略穩定性；或測試不同市場條件下的表現",
                "expected_improvement": "進一步驗證策略魯棒性",
                "priority": "low"
            })

        return suggestions

    def _generate_optimized_code(
        self,
        original_code: str,
        suggestions: List[Dict[str, Any]],
        engine_type: str,
        llm_model: str
    ) -> Optional[str]:
        """生成優化後的策略代碼（可選功能）

        Args:
            original_code: 原始策略代碼
            suggestions: 優化建議
            engine_type: 引擎類型（backtrader 或 qlib）
            llm_model: LLM 模型名稱

        Returns:
            優化後的代碼，如果失敗則返回 None
        """
        # 提取所有包含 code_changes 的建議
        code_changes = [
            s.get("code_changes", "")
            for s in suggestions
            if s.get("code_changes")
        ]

        if not code_changes:
            logger.info("No code changes suggested, skipping code generation")
            return None

        # 簡單實現：返回代碼修改建議的註解版本
        # 完整實現需要調用 LLM 生成完整代碼
        optimized_code = f"""# ========== 優化建議 ==========
# 以下是基於分析結果的代碼修改建議：
#
"""
        for i, change in enumerate(code_changes, 1):
            optimized_code += f"# 建議 {i}: {change}\n"

        optimized_code += f"""#
# ========== 原始代碼 ==========
{original_code}
"""

        logger.info("Generated optimized code with suggestions as comments")
        return optimized_code
