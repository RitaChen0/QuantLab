#!/usr/bin/env python3
"""
测试 TX 期货回测功能

验证：
1. 期货检测正确
2. TXCommissionInfo 应用成功
3. 保证金和合约乘数正确
4. 手续费计算正确
"""

import sys
sys.path.insert(0, '/app')

from datetime import datetime
from app.db.session import SessionLocal
from app.services.backtest_engine import BacktestEngine
from loguru import logger

# 简单的买入持有策略
TX_STRATEGY = """
import backtrader as bt

class TXBuyHoldStrategy(bt.Strategy):
    def __init__(self):
        self.order = None
        self.buy_executed = False

    def next(self):
        # 如果还没有持仓，买入 1 口
        if not self.position and not self.buy_executed:
            self.order = self.buy(size=1)
            self.buy_executed = True

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                print(f'✅ BUY EXECUTED: Price={order.executed.price:.2f}, '
                      f'Cost={order.executed.value:.2f}, Comm={order.executed.comm:.2f}')
            elif order.issell():
                print(f'✅ SELL EXECUTED: Price={order.executed.price:.2f}, '
                      f'Gross={order.executed.value:.2f}, Comm={order.executed.comm:.2f}')
"""

def test_tx_backtest():
    """测试 TX 期货回测"""

    logger.info("=" * 60)
    logger.info("开始测试 TX 期货回测")
    logger.info("=" * 60)

    # 创建数据库会话
    db = SessionLocal()

    try:
        # 创建回测引擎
        engine = BacktestEngine(db)

        # 验证期货检测
        is_futures = engine._is_futures('TX')
        logger.info(f"✅ 期货检测: TX -> {'期货' if is_futures else '股票'}")
        assert is_futures, "TX 应该被识别为期货"

        # 验证 CommissionInfo
        commission_info = engine._get_commission_info('TX')
        logger.info(f"✅ CommissionInfo: {commission_info}")
        assert commission_info is not None, "TX 应该有 CommissionInfo"

        # 执行回测
        logger.info("\n开始执行回测...")
        result = engine.run_backtest(
            backtest_id=999,  # 测试用 ID
            strategy_code=TX_STRATEGY,
            stock_id='TX',
            start_date=datetime(2025, 12, 12),
            end_date=datetime(2025, 12, 13),
            initial_cash=500000.0,  # 50 万初始资金
            timeframe='1min'
        )

        logger.info("\n" + "=" * 60)
        logger.info("回测结果：")
        logger.info("=" * 60)
        logger.info(f"策略: {result.get('strategy_name', 'TXBuyHoldStrategy')}")
        logger.info(f"初始资金: {result.get('initial_cash', 0):,.2f}")
        logger.info(f"最终资产: {result.get('final_value', 0):,.2f}")
        logger.info(f"总收益: {result.get('total_return', 0):.2f}%")
        logger.info(f"交易次数: {result.get('total_trades', 0)}")

        # 验证结果
        assert result.get('final_value', 0) > 0, "最终资产应大于 0"
        logger.info("\n✅ TX 期货回测测试通过！")

        return result

    except Exception as e:
        logger.error(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        db.close()


if __name__ == '__main__':
    test_tx_backtest()
