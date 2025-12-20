#!/usr/bin/env python3
"""
測試回測引擎功能

執行一個簡單的均線交叉策略回測來驗證引擎是否正常運作
"""

import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from datetime import datetime, timedelta, timezone
from app.db.session import SessionLocal
from app.services.backtest_engine import BacktestEngine
from loguru import logger


# 簡單的均線交叉策略
SAMPLE_STRATEGY = """
import backtrader as bt

class MovingAverageCrossStrategy(bt.Strategy):
    '''
    均線交叉策略
    - 快線上穿慢線：買入
    - 快線下穿慢線：賣出
    '''
    params = (
        ('fast_period', 5),
        ('slow_period', 20),
    )

    def __init__(self):
        # 計算快線和慢線
        self.fast_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.fast_period
        )
        self.slow_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.slow_period
        )

        # 交叉信號
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)

    def next(self):
        # 如果沒有持倉
        if not self.position:
            # 快線上穿慢線 -> 買入
            if self.crossover > 0:
                self.buy()

        # 如果有持倉
        else:
            # 快線下穿慢線 -> 賣出
            if self.crossover < 0:
                self.sell()

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')
"""


def test_backtest_engine():
    """測試回測引擎"""

    logger.info("=" * 80)
    logger.info("開始測試回測引擎")
    logger.info("=" * 80)

    # 初始化資料庫連接
    db = SessionLocal()

    try:
        # 1. 初始化回測引擎
        engine = BacktestEngine(db)
        logger.info("✓ 回測引擎初始化成功")

        # 2. 設定測試參數
        stock_id = "2330"  # 台積電
        end_date = datetime.now(timezone.utc)  # ✅ Use timezone-aware UTC time
        start_date = end_date - timedelta(days=180)  # 最近 6 個月
        initial_cash = 1000000.0  # 100 萬

        logger.info(f"測試股票: {stock_id}")
        logger.info(f"回測期間: {start_date.date()} ~ {end_date.date()}")
        logger.info(f"初始資金: {initial_cash:,.0f}")

        # 3. 載入資料
        logger.info("\n載入歷史資料...")
        data_df = engine.load_data(stock_id, start_date, end_date)

        if data_df is None or len(data_df) == 0:
            logger.error(f"✗ 無法載入 {stock_id} 的資料")
            logger.error("請確認資料庫中有該股票的歷史資料")
            logger.error("可以執行: docker compose exec backend python scripts/sync_all_stocks_history.py --stocks 2330 --auto-fix")
            return False

        logger.info(f"✓ 成功載入 {len(data_df)} 筆資料")
        logger.info(f"  資料範圍: {data_df.index[0]} ~ {data_df.index[-1]}")

        # 4. 創建策略類
        logger.info("\n創建策略類...")
        try:
            strategy_class = engine.create_strategy_class(SAMPLE_STRATEGY)
            logger.info(f"✓ 策略類創建成功: {strategy_class.__name__}")
        except Exception as e:
            logger.error(f"✗ 策略類創建失敗: {str(e)}")
            return False

        # 5. 執行回測
        logger.info("\n執行回測...")
        logger.info("-" * 80)

        try:
            results = engine.run_backtest(
                backtest_id=999,  # 測試用 ID
                strategy_code=SAMPLE_STRATEGY,
                stock_id=stock_id,
                start_date=start_date,
                end_date=end_date,
                initial_cash=initial_cash,
                commission=0.001425,
                strategy_params={'fast_period': 5, 'slow_period': 20}
            )

            logger.info("-" * 80)
            logger.info("✓ 回測執行成功")

            # 6. 顯示結果
            metrics = results['metrics']

            logger.info("\n" + "=" * 80)
            logger.info("回測績效報告")
            logger.info("=" * 80)

            logger.info(f"\n💰 資金狀況:")
            logger.info(f"  初始資金: {initial_cash:,.2f}")
            logger.info(f"  最終資產: {metrics['final_value']:,.2f}")
            logger.info(f"  總損益:   {metrics['total_pnl']:+,.2f}")
            logger.info(f"  報酬率:   {metrics['total_return']:+.2f}%")

            logger.info(f"\n📊 交易統計:")
            logger.info(f"  總交易次數: {metrics['total_trades']}")
            logger.info(f"  獲利交易:   {metrics['winning_trades']}")
            logger.info(f"  虧損交易:   {metrics['losing_trades']}")
            logger.info(f"  勝率:       {metrics['win_rate']:.2f}%")

            logger.info(f"\n💵 盈虧分析:")
            logger.info(f"  平均獲利:   {metrics['avg_win']:+,.2f}")
            logger.info(f"  平均虧損:   {metrics['avg_loss']:+,.2f}")
            logger.info(f"  最大獲利:   {metrics['max_win']:+,.2f}")
            logger.info(f"  最大虧損:   {metrics['max_loss']:+,.2f}")
            logger.info(f"  盈虧比:     {metrics['profit_factor']:.2f}")

            logger.info(f"\n📉 風險指標:")
            logger.info(f"  最大回撤:   {metrics['max_drawdown']:,.2f} ({metrics['max_drawdown_pct']:.2f}%)")
            logger.info(f"  夏普率:     {metrics['sharpe_ratio']:.2f}")

            logger.info(f"\n⏱ 其他:")
            logger.info(f"  平均持有天數: {metrics['avg_holding_days']:.1f} 天")

            logger.info("\n" + "=" * 80)

            # 7. 判斷測試結果
            if metrics['total_trades'] > 0:
                logger.info("✓ 回測引擎功能正常")
                logger.info(f"  策略產生了 {metrics['total_trades']} 筆交易")
                logger.info(f"  最終報酬率: {metrics['total_return']:+.2f}%")
                return True
            else:
                logger.warning("⚠ 警告: 策略沒有產生任何交易")
                logger.warning("  可能原因：資料期間太短、策略參數不合適")
                return True  # 引擎功能正常，只是策略沒有交易

        except Exception as e:
            logger.error(f"✗ 回測執行失敗: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    except Exception as e:
        logger.error(f"✗ 測試失敗: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

    finally:
        db.close()


if __name__ == "__main__":
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    success = test_backtest_engine()

    logger.info("\n" + "=" * 80)
    if success:
        logger.info("✓ 測試通過")
        sys.exit(0)
    else:
        logger.error("✗ 測試失敗")
        sys.exit(1)
