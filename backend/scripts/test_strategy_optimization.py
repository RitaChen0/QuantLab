"""
測試策略優化功能

此腳本測試 RD-Agent 策略優化邏輯
"""

import sys
import os

# 添加 app 目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 先導入 Base 並確保所有模型都被註冊
from app.db.base import Base  # noqa
from app.db.session import SessionLocal

# 導入所有模型（確保 relationships 可以解析）
from app.models.user import User  # noqa
from app.models.strategy import Strategy
from app.models.backtest import Backtest, BacktestStatus
from app.models.backtest_result import BacktestResult
from app.models.rdagent import RDAgentTask  # noqa
from app.models.telegram_notification import TelegramNotification  # noqa

from app.services.strategy_optimizer import StrategyOptimizer
from loguru import logger


def test_strategy_optimization():
    """測試策略優化功能"""
    db = SessionLocal()

    try:
        logger.info("========== 策略優化功能測試 ==========")

        # 步驟 1: 查找一個已完成回測的策略
        logger.info("\n步驟 1: 查找測試策略...")

        backtest_with_result = db.query(Backtest).filter(
            Backtest.status == BacktestStatus.COMPLETED
        ).order_by(
            Backtest.completed_at.desc()
        ).first()

        if not backtest_with_result:
            logger.error("❌ 未找到已完成的回測記錄")
            logger.info("請先執行一次策略回測，然後再測試優化功能")
            return False

        strategy = backtest_with_result.strategy
        logger.info(f"✅ 找到測試策略:")
        logger.info(f"   ID: {strategy.id}")
        logger.info(f"   名稱: {strategy.name}")
        logger.info(f"   引擎: {strategy.engine_type}")
        logger.info(f"   最近回測 ID: {backtest_with_result.id}")

        # 檢查是否有回測結果
        if not backtest_with_result.result:
            logger.error("❌ 回測沒有結果數據")
            return False

        result = backtest_with_result.result
        logger.info(f"   回測績效:")
        logger.info(f"     - Sharpe Ratio: {result.sharpe_ratio}")
        logger.info(f"     - Annual Return: {result.annual_return}")
        logger.info(f"     - Max Drawdown: {result.max_drawdown}")
        logger.info(f"     - Win Rate: {result.win_rate}")

        # 步驟 2: 初始化優化器
        logger.info("\n步驟 2: 初始化策略優化器...")
        optimizer = StrategyOptimizer(db)
        logger.info("✅ 優化器初始化完成")

        # 步驟 3: 執行優化分析
        logger.info("\n步驟 3: 執行策略優化分析...")
        logger.info(f"   優化目標: 提升 Sharpe Ratio 至 2.0 以上")

        optimization_goal = "提升 Sharpe Ratio 至 2.0 以上，同時降低最大回撤"

        analysis_result = optimizer.analyze_strategy(
            strategy_id=strategy.id,
            optimization_goal=optimization_goal,
            llm_model="gpt-4-turbo"
        )

        # 步驟 4: 顯示分析結果
        logger.info("\n步驟 4: 分析結果:")
        logger.info(f"✅ 策略優化分析完成")

        # 4.1 當前績效
        logger.info("\n📊 當前績效指標:")
        current_perf = analysis_result["current_performance"]
        for key, value in current_perf.items():
            if key != "backtest_id":
                logger.info(f"   {key}: {value}")

        # 4.2 問題診斷
        logger.info("\n🔍 問題診斷:")
        issues = analysis_result["issues_diagnosed"]
        if issues:
            for i, issue in enumerate(issues, 1):
                logger.info(f"   [{i}] [{issue['severity'].upper()}] {issue['type']}")
                logger.info(f"       問題: {issue['description']}")
                logger.info(f"       當前值: {issue['current_value']}")
                logger.info(f"       目標值: {issue['target_value']}")
                logger.info(f"       建議: {issue['recommendation']}")
        else:
            logger.info("   ✅ 未發現明顯問題")

        # 4.3 優化建議
        logger.info("\n💡 優化建議:")
        suggestions = analysis_result["optimization_suggestions"]
        for i, suggestion in enumerate(suggestions, 1):
            logger.info(f"\n   【建議 {i}】 [{suggestion.get('priority', 'medium').upper()}]")
            logger.info(f"   類型: {suggestion.get('type', 'N/A')}")
            logger.info(f"   問題: {suggestion.get('problem', 'N/A')}")
            logger.info(f"   方案: {suggestion.get('solution', 'N/A')}")
            logger.info(f"   預期效果: {suggestion.get('expected_improvement', 'N/A')}")

            if suggestion.get('code_changes'):
                logger.info(f"   代碼修改: {suggestion['code_changes']}")

        # 4.4 LLM 使用統計
        logger.info("\n🤖 LLM 使用統計:")
        llm_metadata = analysis_result["llm_metadata"]
        logger.info(f"   模型: {llm_metadata['model']}")
        logger.info(f"   API 調用: {llm_metadata['calls']} 次")
        logger.info(f"   成本: ${llm_metadata['cost']}")

        # 步驟 5: 驗證結果結構
        logger.info("\n步驟 5: 驗證結果結構...")
        required_keys = [
            "strategy_info",
            "current_performance",
            "issues_diagnosed",
            "optimization_suggestions",
            "llm_metadata"
        ]

        missing_keys = [key for key in required_keys if key not in analysis_result]
        if missing_keys:
            logger.error(f"❌ 結果缺少必要欄位: {missing_keys}")
            return False

        logger.info("✅ 結果結構驗證通過")

        # 總結
        logger.info("\n========== 測試總結 ==========")
        logger.info(f"✅ 策略優化功能測試通過")
        logger.info(f"   策略 ID: {strategy.id}")
        logger.info(f"   診斷問題數: {len(issues)}")
        logger.info(f"   優化建議數: {len(suggestions)}")
        logger.info(f"   LLM 調用: {llm_metadata['calls']} 次")
        logger.info(f"   LLM 成本: ${llm_metadata['cost']}")

        return True

    except Exception as e:
        logger.error(f"❌ 測試失敗: {e}")
        import traceback
        logger.error(f"完整錯誤:\n{traceback.format_exc()}")
        return False

    finally:
        db.close()


if __name__ == "__main__":
    success = test_strategy_optimization()
    sys.exit(0 if success else 1)
