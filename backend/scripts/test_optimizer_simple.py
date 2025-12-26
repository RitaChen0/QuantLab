"""
簡單測試策略優化器 - 直接使用策略 ID
"""

import sys
import os

# 添加路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 設置環境變數
os.environ.setdefault("DATABASE_URL", "postgresql://quantlab:quantlab2025@postgres:5432/quantlab")
os.environ.setdefault("REDIS_URL", "redis://redis:6379/0")

from loguru import logger


def test_with_strategy_id():
    """使用已知的策略 ID 進行測試"""

    # 延遲導入，避免循環依賴
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from app.services.strategy_optimizer import StrategyOptimizer

    logger.info("========== 策略優化器簡單測試 ==========")

    # 創建資料庫連接
    engine = create_engine(os.environ["DATABASE_URL"])
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # 步驟 1: 查找有效的策略 ID
        logger.info("\n步驟 1: 查找測試策略...")

        result = db.execute(text("""
            SELECT b.id as backtest_id, b.strategy_id, s.name as strategy_name,
                   br.sharpe_ratio, br.annual_return, br.max_drawdown
            FROM backtests b
            JOIN strategies s ON b.strategy_id = s.id
            LEFT JOIN backtest_results br ON b.id = br.backtest_id
            WHERE b.status = 'COMPLETED' AND br.id IS NOT NULL
            ORDER BY b.completed_at DESC
            LIMIT 1
        """))

        row = result.fetchone()
        if not row:
            logger.error("❌ 未找到有效的回測記錄")
            return False

        backtest_id, strategy_id, strategy_name, sharpe, annual_return, max_dd = row

        logger.info(f"✅ 找到測試策略:")
        logger.info(f"   策略 ID: {strategy_id}")
        logger.info(f"   策略名稱: {strategy_name}")
        logger.info(f"   回測 ID: {backtest_id}")
        logger.info(f"   Sharpe Ratio: {sharpe}")
        logger.info(f"   Annual Return: {annual_return}")
        logger.info(f"   Max Drawdown: {max_dd}")

        # 步驟 2: 初始化優化器
        logger.info("\n步驟 2: 初始化策略優化器...")
        optimizer = StrategyOptimizer(db)
        logger.info("✅ 優化器初始化完成")

        # 步驟 3: 執行優化分析
        logger.info("\n步驟 3: 執行策略優化分析...")
        logger.info(f"   優化目標: 提升 Sharpe Ratio 至 2.0 以上")

        analysis_result = optimizer.analyze_strategy(
            strategy_id=strategy_id,
            optimization_goal="提升 Sharpe Ratio 至 2.0 以上，同時降低最大回撤",
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
            logger.info(f"   方案: {suggestion.get('solution', 'N/A')[:200]}...")  # 限制長度
            logger.info(f"   預期效果: {suggestion.get('expected_improvement', 'N/A')}")

        # 4.4 LLM 使用統計
        logger.info("\n🤖 LLM 使用統計:")
        llm_metadata = analysis_result["llm_metadata"]
        logger.info(f"   模型: {llm_metadata['model']}")
        logger.info(f"   API 調用: {llm_metadata['calls']} 次")
        logger.info(f"   成本: ${llm_metadata['cost']}")

        # 總結
        logger.info("\n========== 測試總結 ==========")
        logger.info(f"✅ 策略優化功能測試通過")
        logger.info(f"   策略 ID: {strategy_id}")
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
    success = test_with_strategy_id()
    sys.exit(0 if success else 1)
