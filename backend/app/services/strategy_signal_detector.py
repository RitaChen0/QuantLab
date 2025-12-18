"""
策略信號檢測服務

輕量級執行策略並檢測買賣信號（不進行完整回測）
"""

import backtrader as bt
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from loguru import logger

# Ensure all models are imported to avoid SQLAlchemy relationship errors
from app.db.base import Base
from app.db.session import ensure_models_imported
ensure_models_imported()

from app.models.strategy import Strategy, StrategyStatus
from app.models.stock_price import StockPrice
from app.models.stock_minute_price import StockMinutePrice
from app.models.strategy_signal import StrategySignal
from app.repositories.stock_minute_price import StockMinutePriceRepository


class SignalDetectionStrategy(bt.Strategy):
    """
    信號檢測策略基類

    用於捕獲用戶策略中的買賣信號
    """

    def __init__(self):
        super().__init__()
        self.signals = []  # 存儲檢測到的信號

    def notify_order(self, order):
        """捕獲訂單創建事件"""
        if order.status in [order.Submitted, order.Accepted]:
            # 獲取股票代碼
            stock_id = order.data._name if hasattr(order.data, '_name') else 'unknown'

            # 記錄信號
            signal = {
                'stock_id': stock_id,
                'signal_type': 'BUY' if order.isbuy() else 'SELL',
                'price': order.data.close[0],  # 當前收盤價
                'datetime': bt.num2date(order.created.dt),
            }

            self.signals.append(signal)
            logger.debug(f"📊 檢測到信號: {signal}")


class StrategySignalDetector:
    """策略信號檢測器"""

    def __init__(self, db: Session):
        self.db = db
        self.minute_price_repo = StockMinutePriceRepository()

    def detect_signals_for_active_strategies(
        self,
        lookback_days: int = 60
    ) -> List[Dict]:
        """
        檢測所有 ACTIVE 狀態策略的信號

        Args:
            lookback_days: 回溯天數（用於獲取歷史數據）

        Returns:
            檢測到的信號列表
        """
        # 查詢所有 ACTIVE 策略
        active_strategies = (
            self.db.query(Strategy)
            .filter(Strategy.status == StrategyStatus.ACTIVE)
            .all()
        )

        if not active_strategies:
            logger.info("📊 沒有 ACTIVE 狀態的策略")
            return []

        logger.info(f"📊 找到 {len(active_strategies)} 個 ACTIVE 策略，開始檢測信號...")

        all_signals = []

        for strategy in active_strategies:
            try:
                signals = self.detect_signals_for_strategy(
                    strategy=strategy,
                    lookback_days=lookback_days
                )

                if signals:
                    logger.info(
                        f"✅ 策略 [{strategy.name}] 檢測到 {len(signals)} 個信號"
                    )
                    all_signals.extend(signals)

            except Exception as e:
                logger.error(
                    f"❌ 策略 [{strategy.name}] 信號檢測失敗: {str(e)}"
                )
                continue

        return all_signals

    def detect_signals_for_strategy(
        self,
        strategy: Strategy,
        lookback_days: int = 60
    ) -> List[Dict]:
        """
        檢測單個策略的信號

        Args:
            strategy: 策略對象
            lookback_days: 回溯天數

        Returns:
            檢測到的信號列表
        """
        # 只支援 Backtrader 引擎
        if strategy.engine_type != 'backtrader':
            logger.warning(
                f"策略 [{strategy.name}] 使用 {strategy.engine_type} 引擎，"
                "目前只支援 Backtrader 引擎的信號檢測"
            )
            return []

        # 解析策略參數
        parameters = strategy.parameters or {}
        stocks = parameters.get('stocks', [])

        if not stocks:
            logger.warning(f"策略 [{strategy.name}] 沒有配置股票清單")
            return []

        # 構建策略類
        try:
            strategy_class = self._build_strategy_class(strategy.code)
        except Exception as e:
            logger.error(f"策略代碼編譯失敗: {str(e)}")
            return []

        # 對每支股票檢測信號
        all_signals = []

        for stock_id in stocks:
            try:
                signals = self._detect_signals_for_stock(
                    strategy=strategy,
                    strategy_class=strategy_class,
                    stock_id=stock_id,
                    lookback_days=lookback_days
                )

                all_signals.extend(signals)

            except Exception as e:
                logger.error(
                    f"股票 {stock_id} 信號檢測失敗: {str(e)}"
                )
                continue

        return all_signals

    def _detect_signals_for_stock(
        self,
        strategy: Strategy,
        strategy_class: type,
        stock_id: str,
        lookback_days: int
    ) -> List[Dict]:
        """
        檢測單支股票的信號

        Args:
            strategy: 策略對象
            strategy_class: 編譯後的策略類
            stock_id: 股票代碼
            lookback_days: 回溯天數

        Returns:
            檢測到的信號列表
        """
        # 獲取歷史數據
        data = self._get_stock_data(stock_id, lookback_days)

        if data is None or data.empty:
            logger.warning(f"股票 {stock_id} 沒有足夠的歷史數據")
            return []

        # 創建 Cerebro 實例
        cerebro = bt.Cerebro()

        # 添加數據源
        data_feed = bt.feeds.PandasData(
            dataname=data,
            datetime=None,  # 使用 index 作為 datetime
            open='open',
            high='high',
            low='low',
            close='close',
            volume='volume',
            openinterest=-1
        )
        cerebro.adddata(data_feed, name=stock_id)

        # 添加策略
        cerebro.addstrategy(strategy_class)

        # 設置初始資金（不重要，只是為了運行）
        cerebro.broker.setcash(1000000)

        # 運行策略
        try:
            strategies = cerebro.run()
            strategy_instance = strategies[0]

            # 提取信號
            if hasattr(strategy_instance, 'signals'):
                signals = strategy_instance.signals

                # 只保留最近的信號（最後一個 bar 的信號）
                if signals:
                    # 獲取最後一個交易日
                    last_date = data.index[-1]

                    # 過濾出最後一個交易日的信號
                    recent_signals = [
                        s for s in signals
                        if s['datetime'].date() == last_date.date()
                    ]

                    # 添加策略和用戶信息
                    for signal in recent_signals:
                        signal['strategy_id'] = strategy.id
                        signal['user_id'] = strategy.user_id
                        signal['strategy_name'] = strategy.name

                    return recent_signals

        except Exception as e:
            logger.error(f"運行策略失敗: {str(e)}")
            return []

        return []

    def _get_stock_data(
        self,
        stock_id: str,
        lookback_days: int
    ) -> Optional[pd.DataFrame]:
        """
        獲取股票歷史數據

        Args:
            stock_id: 股票代碼
            lookback_days: 回溯天數

        Returns:
            DataFrame 或 None
        """
        # 計算起始日期
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=lookback_days)

        # 優先使用日線數據（更穩定）
        query = (
            self.db.query(StockPrice)
            .filter(
                StockPrice.stock_id == stock_id,
                StockPrice.date >= start_date,
                StockPrice.date <= end_date
            )
            .order_by(StockPrice.date)
        )

        rows = query.all()

        if not rows:
            logger.warning(f"股票 {stock_id} 沒有日線數據")
            return None

        # 轉換為 DataFrame
        data = pd.DataFrame([
            {
                'datetime': row.date,
                'open': float(row.open) if row.open else None,
                'high': float(row.high) if row.high else None,
                'low': float(row.low) if row.low else None,
                'close': float(row.close) if row.close else None,
                'volume': int(row.volume) if row.volume else 0,
            }
            for row in rows
        ])

        # 設置索引
        data['datetime'] = pd.to_datetime(data['datetime'])
        data.set_index('datetime', inplace=True)

        # 移除缺失值
        data = data.dropna(subset=['open', 'high', 'low', 'close'])

        return data

    def _build_strategy_class(self, code: str) -> type:
        """
        動態編譯用戶策略代碼

        Args:
            code: 策略代碼

        Returns:
            策略類
        """
        # 準備執行環境
        exec_globals = {
            'bt': bt,
            'pd': pd,
            'datetime': datetime,
            'timedelta': timedelta,
            'SignalDetectionStrategy': SignalDetectionStrategy,
        }

        # 執行用戶代碼
        exec(code, exec_globals)

        # 尋找策略類（假設用戶定義了一個繼承自 bt.Strategy 的類）
        strategy_class = None

        for name, obj in exec_globals.items():
            if (
                isinstance(obj, type) and
                issubclass(obj, bt.Strategy) and
                obj not in [bt.Strategy, SignalDetectionStrategy]
            ):
                # 找到用戶定義的策略類
                # 需要讓它繼承 SignalDetectionStrategy 以捕獲信號

                # 創建混合類
                class MixedStrategy(SignalDetectionStrategy, obj):
                    """混合策略：繼承信號檢測 + 用戶策略"""
                    pass

                strategy_class = MixedStrategy
                break

        if strategy_class is None:
            raise ValueError("未找到有效的策略類（應繼承自 bt.Strategy）")

        return strategy_class

    def save_signal(
        self,
        signal: Dict
    ) -> StrategySignal:
        """
        保存信號到資料庫

        Args:
            signal: 信號字典

        Returns:
            StrategySignal 對象
        """
        signal_record = StrategySignal(
            strategy_id=signal['strategy_id'],
            user_id=signal['user_id'],
            stock_id=signal['stock_id'],
            signal_type=signal['signal_type'],
            price=signal.get('price'),
            reason=signal.get('reason'),
            detected_at=signal.get('datetime', datetime.now()),
            notified=False
        )

        self.db.add(signal_record)
        self.db.commit()
        self.db.refresh(signal_record)

        return signal_record

    def is_duplicate_signal(
        self,
        strategy_id: int,
        stock_id: str,
        signal_type: str,
        minutes: int = 15
    ) -> bool:
        """
        檢查是否為重複信號

        在指定時間範圍內（預設 15 分鐘），相同策略、相同股票、相同方向的信號視為重複

        Args:
            strategy_id: 策略 ID
            stock_id: 股票代碼
            signal_type: 信號類型（BUY 或 SELL）
            minutes: 時間範圍（分鐘）

        Returns:
            True 表示重複，False 表示非重複
        """
        time_threshold = datetime.now() - timedelta(minutes=minutes)

        duplicate = (
            self.db.query(StrategySignal)
            .filter(
                StrategySignal.strategy_id == strategy_id,
                StrategySignal.stock_id == stock_id,
                StrategySignal.signal_type == signal_type,
                StrategySignal.detected_at >= time_threshold
            )
            .first()
        )

        return duplicate is not None
