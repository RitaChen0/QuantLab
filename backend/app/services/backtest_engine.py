"""
Backtrader 回測引擎核心

提供完整的回測功能，包括：
- 策略執行
- 績效指標計算
- 交易記錄追蹤
- 結果儲存
"""

import backtrader as bt
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import io
import sys
from loguru import logger
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.backtest import Backtest
from app.models.backtest_result import BacktestResult
from app.models.trade import Trade, TradeAction
from app.models.stock_price import StockPrice
from app.repositories.stock_minute_price import StockMinutePriceRepository


class DailyValueAnalyzer(bt.Analyzer):
    """
    自定義 Analyzer 用於記錄每日資產淨值、現金、股票價值

    使用 Analyzer 而非 Observer，因為 Analyzer 有標準的訪問方式：
    - strategy.analyzers.<name>.get_analysis()
    - 更可靠，更容易提取數據
    """

    def __init__(self):
        super().__init__()
        self.daily_records = []  # 儲存每日記錄

    def next(self):
        """每個 bar 結束時記錄當前淨值"""
        # 獲取當前日期
        current_date = self.strategy.datetime.date(0)

        # 記錄淨值
        value = self.strategy.broker.getvalue()
        cash = self.strategy.broker.getcash()
        stock_value = value - cash

        # 儲存到列表
        self.daily_records.append({
            'date': current_date.isoformat(),
            'value': float(value),
            'cash': float(cash),
            'stock_value': float(stock_value)
        })

    def get_analysis(self):
        """返回每日淨值記錄"""
        return self.daily_records


class TrackingStrategy(bt.Strategy):
    """
    追蹤交易的基礎策略類
    記錄每筆交易的詳細信息
    """

    def __init__(self):
        super().__init__()
        self._init_tracking_attributes()

    def _init_tracking_attributes(self):
        """初始化交易追蹤屬性（防禦性編程）"""
        if not hasattr(self, 'trade_records'):
            self.trade_records = []  # 存儲所有交易記錄
        if not hasattr(self, 'open_positions'):
            self.open_positions = {}  # 追蹤開倉位置 {data: (entry_date, entry_price, size)}

    def notify_order(self, order):
        """訂單狀態變化通知"""
        # 確保屬性已初始化（防止用戶策略未調用 super().__init__()）
        self._init_tracking_attributes()

        if order.status in [order.Completed]:
            if order.isbuy():
                logger.debug(
                    f'BUY EXECUTED, Price: {order.executed.price:.2f}, '
                    f'Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}'
                )
                # 記錄開倉信息
                data_name = order.data._name if hasattr(order.data, '_name') else 'unknown'
                self.open_positions[data_name] = {
                    'entry_date': bt.num2date(order.executed.dt),
                    'entry_price': order.executed.price,
                    'size': order.executed.size,
                    'commission': order.executed.comm,
                }
            elif order.issell():
                logger.debug(
                    f'SELL EXECUTED, Price: {order.executed.price:.2f}, '
                    f'Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}'
                )

    def notify_trade(self, trade):
        """交易完成通知（一買一賣構成一筆完整交易）"""
        # 確保屬性已初始化（防止用戶策略未調用 super().__init__()）
        self._init_tracking_attributes()

        if trade.isclosed:
            # 獲取開倉信息
            data_name = trade.data._name if hasattr(trade.data, '_name') else 'unknown'
            position_info = self.open_positions.get(data_name, {})

            # 記錄交易詳情
            trade_record = {
                'entry_date': position_info.get('entry_date', bt.num2date(trade.dtopen)),
                'exit_date': bt.num2date(trade.dtclose),
                'entry_price': position_info.get('entry_price', trade.price),
                'exit_price': trade.price,
                'size': position_info.get('size', abs(trade.size)),  # 使用開倉時記錄的數量
                'pnl': trade.pnl,
                'pnl_net': trade.pnlcomm,  # 扣除手續費後的淨利潤
                'commission': position_info.get('commission', 0) + abs(trade.commission),
                'holding_days': (bt.num2date(trade.dtclose) - position_info.get('entry_date', bt.num2date(trade.dtopen))).days,
            }

            self.trade_records.append(trade_record)

            # 清除已平倉位置
            if data_name in self.open_positions:
                del self.open_positions[data_name]

            logger.info(
                f'TRADE CLOSED - Entry: {trade_record["entry_date"].strftime("%Y-%m-%d")} @ {trade_record["entry_price"]:.2f}, '
                f'Exit: {trade_record["exit_date"].strftime("%Y-%m-%d")} @ {trade_record["exit_price"]:.2f}, '
                f'PnL: {trade_record["pnl"]:.2f}, Days: {trade_record["holding_days"]}'
            )


class DatabaseDataFeed(bt.feeds.PandasData):
    """從資料庫載入的資料饋送器"""

    params = (
        ('datetime', None),
        ('open', 'open'),
        ('high', 'high'),
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
        ('openinterest', -1),
    )


class PerformanceAnalyzer:
    """績效分析器 - 計算各種績效指標"""

    @staticmethod
    def calculate_metrics(
        initial_cash: float,
        final_value: float,
        trades: List[Dict],
        equity_curve: List[Tuple[datetime, float]]
    ) -> Dict[str, Any]:
        """
        計算完整的績效指標

        Args:
            initial_cash: 初始資金
            final_value: 最終資產
            trades: 交易記錄
            equity_curve: 權益曲線 [(日期, 價值), ...]

        Returns:
            包含所有績效指標的字典
        """

        # 基本指標
        total_return = ((final_value - initial_cash) / initial_cash) * 100
        total_pnl = final_value - initial_cash

        # 交易統計
        total_trades = len(trades)
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] < 0]

        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

        # 盈虧統計
        avg_win = sum(t['pnl'] for t in winning_trades) / win_count if win_count > 0 else 0
        avg_loss = sum(t['pnl'] for t in losing_trades) / loss_count if loss_count > 0 else 0

        # 盈虧比
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0

        # 最大獲利/虧損交易
        max_win = max([t['pnl'] for t in trades], default=0)
        max_loss = min([t['pnl'] for t in trades], default=0)

        # 計算最大回撤
        max_drawdown, max_drawdown_pct = PerformanceAnalyzer._calculate_max_drawdown(equity_curve)

        # 計算夏普率（假設年化，無風險利率 2%）
        sharpe_ratio = PerformanceAnalyzer._calculate_sharpe_ratio(equity_curve, initial_cash)

        # 計算持有時間統計
        avg_holding_days = sum(t.get('holding_days', 0) for t in trades) / total_trades if total_trades > 0 else 0

        return {
            "total_return": round(total_return, 2),
            "total_pnl": round(total_pnl, 2),
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "max_drawdown": round(max_drawdown, 2),
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "total_trades": total_trades,
            "winning_trades": win_count,
            "losing_trades": loss_count,
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "max_win": round(max_win, 2),
            "max_loss": round(max_loss, 2),
            "avg_holding_days": round(avg_holding_days, 1),
            "final_value": round(final_value, 2),
        }

    @staticmethod
    def _calculate_max_drawdown(equity_curve: List[Tuple[datetime, float]]) -> Tuple[float, float]:
        """計算最大回撤（絕對值與百分比）"""
        if not equity_curve:
            return 0.0, 0.0

        peak = equity_curve[0][1]
        max_dd = 0.0
        max_dd_pct = 0.0

        for date, value in equity_curve:
            if value > peak:
                peak = value

            drawdown = peak - value
            drawdown_pct = (drawdown / peak * 100) if peak > 0 else 0

            if drawdown > max_dd:
                max_dd = drawdown
                max_dd_pct = drawdown_pct

        return max_dd, max_dd_pct

    @staticmethod
    def _calculate_sharpe_ratio(
        equity_curve: List[Tuple[datetime, float]],
        initial_cash: float,
        risk_free_rate: float = 0.02
    ) -> float:
        """計算夏普率（年化）"""
        if len(equity_curve) < 2:
            return 0.0

        # 計算每日收益率
        returns = []
        for i in range(1, len(equity_curve)):
            prev_value = equity_curve[i-1][1]
            curr_value = equity_curve[i][1]
            daily_return = (curr_value - prev_value) / prev_value if prev_value > 0 else 0
            returns.append(daily_return)

        if not returns:
            return 0.0

        # 計算平均收益率與標準差
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5

        if std_dev == 0:
            return 0.0

        # 年化（假設 252 個交易日）
        annualized_return = avg_return * 252
        annualized_std = std_dev * (252 ** 0.5)

        sharpe = (annualized_return - risk_free_rate) / annualized_std
        return sharpe


class BacktestEngine:
    """
    回測引擎核心

    負責執行策略回測、收集交易記錄、計算績效指標
    """

    def __init__(self, db: Session):
        self.db = db
        self.cerebro = None
        self.strategy_instance = None

    def load_data(
        self,
        stock_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[pd.DataFrame]:
        """
        從資料庫載入股票 OHLCV 資料

        Args:
            stock_id: 股票代碼
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            包含 OHLCV 資料的 DataFrame
        """
        try:
            # 處理日期格式：統一轉換為 date 對象
            from datetime import date

            if start_date is not None:
                if isinstance(start_date, str):
                    start_date = datetime.fromisoformat(start_date).date()
                elif isinstance(start_date, datetime):
                    start_date = start_date.date()
                elif not isinstance(start_date, date):
                    raise ValueError(f"Invalid start_date type: {type(start_date)}")

            if end_date is not None:
                if isinstance(end_date, str):
                    end_date = datetime.fromisoformat(end_date).date()
                elif isinstance(end_date, datetime):
                    end_date = end_date.date()
                elif not isinstance(end_date, date):
                    raise ValueError(f"Invalid end_date type: {type(end_date)}")

            # 先查詢該股票在資料庫中的實際日期範圍
            date_range = self.db.query(
                func.min(StockPrice.date).label('min_date'),
                func.max(StockPrice.date).label('max_date')
            ).filter(
                StockPrice.stock_id == stock_id
            ).first()

            if not date_range or not date_range.min_date:
                logger.error(f"No data available in database for stock {stock_id}")
                return None

            db_start_date = date_range.min_date
            db_end_date = date_range.max_date

            # 自動調整日期範圍到資料庫實際範圍
            original_start = start_date
            original_end = end_date

            if start_date < db_start_date:
                start_date = db_start_date
                logger.warning(
                    f"Start date {original_start} is before earliest data {db_start_date}. "
                    f"Automatically adjusted to {start_date}"
                )

            if end_date > db_end_date:
                end_date = db_end_date
                logger.warning(
                    f"End date {original_end} is after latest data {db_end_date}. "
                    f"Automatically adjusted to {end_date}"
                )

            if start_date > db_end_date or end_date < db_start_date:
                logger.error(
                    f"Date range {original_start} to {original_end} does not overlap with "
                    f"available data {db_start_date} to {db_end_date}"
                )
                return None

            # 查詢調整後的日期範圍內的數據
            prices = self.db.query(StockPrice).filter(
                StockPrice.stock_id == stock_id,
                StockPrice.date >= start_date,
                StockPrice.date <= end_date
            ).order_by(StockPrice.date).all()

            if not prices:
                logger.warning(f"No data found for {stock_id} in adjusted range {start_date} to {end_date}")
                return None

            # 記錄調整信息
            if original_start != start_date or original_end != end_date:
                logger.info(
                    f"Date range auto-adjusted: {original_start}~{original_end} → {start_date}~{end_date} "
                    f"(DB range: {db_start_date}~{db_end_date})"
                )

            # 轉換為 DataFrame
            data = []
            for price in prices:
                data.append({
                    'date': pd.Timestamp(price.date),
                    'open': float(price.open),
                    'high': float(price.high),
                    'low': float(price.low),
                    'close': float(price.close),
                    'volume': int(price.volume),
                })

            df = pd.DataFrame(data)
            df.set_index('date', inplace=True)

            logger.info(f"Loaded {len(df)} records for {stock_id}")
            return df

        except Exception as e:
            logger.error(f"Error loading data for {stock_id}: {str(e)}")
            return None

    def load_minute_data(
        self,
        stock_id: str,
        start_datetime: datetime,
        end_datetime: datetime,
        timeframe: str = '1min',
        limit: int = 100000
    ) -> Optional[pd.DataFrame]:
        """
        從資料庫載入分鐘級 OHLCV 資料

        Args:
            stock_id: 股票代碼
            start_datetime: 開始時間
            end_datetime: 結束時間
            timeframe: 時間粒度 ('1min', '5min', '15min', '30min', '60min')
            limit: 最大記錄數（防止資料量過大）

        Returns:
            包含 OHLCV 資料的 DataFrame（index 為 datetime）
        """
        try:
            # 確保 datetime 類型正確
            if isinstance(start_datetime, str):
                start_datetime = datetime.fromisoformat(start_datetime)
            if isinstance(end_datetime, str):
                end_datetime = datetime.fromisoformat(end_datetime)

            logger.info(
                f"Loading minute data for {stock_id}: "
                f"{start_datetime} to {end_datetime} ({timeframe})"
            )

            # 總是查詢 1 分鐘資料（數據庫中只存儲 1 分鐘原始數據）
            prices = StockMinutePriceRepository.get_by_stock(
                self.db,
                stock_id,
                start_datetime,
                end_datetime,
                '1min',  # 總是查詢 1 分鐘資料
                limit
            )

            if not prices:
                logger.warning(
                    f"No minute data found for {stock_id} "
                    f"(1min, {start_datetime} to {end_datetime})"
                )
                return None

            # 轉換為 DataFrame
            data = []
            for price in prices:
                data.append({
                    'datetime': pd.Timestamp(price.datetime),
                    'open': float(price.open),
                    'high': float(price.high),
                    'low': float(price.low),
                    'close': float(price.close),
                    'volume': int(price.volume),
                })

            df = pd.DataFrame(data)
            df.set_index('datetime', inplace=True)

            logger.info(
                f"Loaded {len(df)} 1-minute bars for {stock_id}"
            )

            # 如果需要的不是 1 分鐘資料，進行重採樣
            if timeframe != '1min':
                df = self._resample_ohlcv(df, timeframe)
                logger.info(
                    f"Resampled to {len(df)} {timeframe} bars for {stock_id}"
                )

            return df

        except Exception as e:
            logger.error(f"Error loading minute data for {stock_id}: {str(e)}")
            return None

    def _resample_ohlcv(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        將 OHLCV 資料重採樣到指定時間粒度

        Args:
            df: 原始資料（index 為 datetime）
            timeframe: 目標時間粒度 ('5min', '15min', '30min', '60min')

        Returns:
            重採樣後的 DataFrame
        """
        # 時間粒度映射（Pandas resample 格式）
        timeframe_map = {
            '1min': '1T',
            '5min': '5T',
            '15min': '15T',
            '30min': '30T',
            '60min': '60T',
        }

        if timeframe not in timeframe_map:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        rule = timeframe_map[timeframe]

        # OHLCV 重採樣規則
        resampled = df.resample(rule).agg({
            'open': 'first',    # 開盤價取第一個
            'high': 'max',      # 最高價取最大值
            'low': 'min',       # 最低價取最小值
            'close': 'last',    # 收盤價取最後一個
            'volume': 'sum'     # 成交量加總
        }).dropna()  # 移除空值（沒有交易的時間段）

        return resampled

    def create_strategy_class(self, strategy_code: str, strategy_name: str = "UserStrategy") -> type:
        """
        從字符串代碼創建策略類（自動替換基類為 TrackingStrategy）

        Args:
            strategy_code: 策略 Python 代碼
            strategy_name: 策略名稱

        Returns:
            策略類（繼承自 TrackingStrategy，自動追蹤交易）

        Raises:
            ValueError: 如果策略代碼無效或包含危險操作
        """
        # 安全檢查：在執行前驗證策略代碼
        self._validate_strategy_code_security(strategy_code)

        # 創建安全的 __import__ 包裝器（只允許白名單模組）
        def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            """
            安全的導入函數，只允許白名單模組
            """
            allowed_modules = {
                'backtrader', 'bt',
                'pandas', 'pd',
                'numpy', 'np',
                'datetime',
                'talib',
                'math',
                'collections',
                'itertools',
            }

            # 提取頂層模組名稱（例如 "pandas.core" -> "pandas"）
            top_level_module = name.split('.')[0]

            if top_level_module not in allowed_modules:
                raise ImportError(f"導入模組 '{name}' 不被允許（僅允許: {', '.join(allowed_modules)}）")

            # 使用原生 __import__ 導入
            return __import__(name, globals, locals, fromlist, level)

        # 創建受限的安全命名空間（完全隔離 __builtins__）
        safe_builtins = {
            # 只允許安全的內建函數
            'len': len,
            'range': range,
            'enumerate': enumerate,
            'zip': zip,
            'map': map,
            'filter': filter,
            'sum': sum,
            'min': min,
            'max': max,
            'abs': abs,
            'round': round,
            'int': int,
            'float': float,
            'str': str,
            'bool': bool,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            'print': print,  # 允許 print() 用於調試
            'True': True,
            'False': False,
            'None': None,
            '__import__': safe_import,  # 允許安全的 import
            '__build_class__': __build_class__,  # 允許定義類別（class 語句需要）
        }

        namespace = {
            '__builtins__': safe_builtins,  # 限制內建函數
            '__name__': '__main__',
            '__doc__': None,
            'bt': bt,
            'backtrader': bt,
            'pd': pd,
            'datetime': datetime,
            'TrackingStrategy': TrackingStrategy,
        }

        try:
            # 替換策略代碼中的基類，將 bt.Strategy 替換為 TrackingStrategy
            # 這樣用戶策略會自動繼承交易追蹤功能
            modified_code = strategy_code.replace('bt.Strategy', 'TrackingStrategy')
            modified_code = modified_code.replace('backtrader.Strategy', 'TrackingStrategy')

            logger.debug(f"Modified strategy code to use TrackingStrategy")

            # 執行修改後的策略代碼
            exec(modified_code, namespace)

            # 尋找策略類（繼承自 TrackingStrategy 的類）
            strategy_class = None
            for name, obj in namespace.items():
                if (isinstance(obj, type) and
                    issubclass(obj, TrackingStrategy) and
                    obj is not TrackingStrategy):
                    strategy_class = obj
                    break

            if strategy_class is None:
                raise ValueError("No strategy class found in code (must inherit from bt.Strategy)")

            logger.info(f"Successfully created tracking strategy class: {strategy_class.__name__}")
            return strategy_class

        except Exception as e:
            logger.error(f"Error creating strategy class: {str(e)}")
            raise ValueError(f"Invalid strategy code: {str(e)}")

    def _validate_strategy_code_security(self, code: str) -> None:
        """
        雙重驗證策略代碼安全性（使用 AST 解析）

        這是回測執行前的額外安全檢查，防止數據庫被直接修改繞過初始驗證。

        Args:
            code: 策略代碼

        Raises:
            ValueError: 如果代碼包含危險操作
        """
        import ast

        # 危險函數黑名單
        dangerous_functions = {
            'eval', 'exec', 'compile', '__import__',
            'open', 'file', 'input',
            'globals', 'locals', 'vars', 'dir',
            'getattr', 'setattr', 'delattr', 'hasattr',
            'breakpoint', 'exit', 'quit',
        }

        # 危險屬性黑名單
        dangerous_attributes = {
            '__globals__', '__code__', '__builtins__',
            '__dict__', '__class__', '__bases__',
            '__subclasses__', '__import__',
        }

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"策略代碼語法錯誤: {str(e)}")

        # 檢查 AST 節點
        for node in ast.walk(tree):
            # 檢查函數調用
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in dangerous_functions:
                        raise ValueError(
                            f"策略代碼包含危險函數調用: {node.func.id}"
                        )

            # 檢查屬性訪問
            elif isinstance(node, ast.Attribute):
                if node.attr in dangerous_attributes:
                    raise ValueError(
                        f"策略代碼包含危險屬性訪問: {node.attr}"
                    )

        logger.info("Strategy code security validation passed")

    def run_backtest(
        self,
        backtest_id: int,
        strategy_code: str,
        stock_id: str,
        start_date: datetime,
        end_date: datetime,
        initial_cash: float = 1000000.0,
        commission: float = 0.001425,
        tax: float = 0.003,
        slippage: float = 0.0,
        position_size: Optional[int] = None,
        max_position_pct: float = 1.0,
        strategy_params: Optional[Dict] = None,
        timeframe: str = '1day'
    ) -> Dict[str, Any]:
        """
        執行回測

        Args:
            backtest_id: 回測 ID
            strategy_code: 策略代碼
            stock_id: 股票代碼
            start_date: 開始日期（日線）或開始時間（分鐘線）
            end_date: 結束日期（日線）或結束時間（分鐘線）
            initial_cash: 初始資金
            commission: 手續費率（買賣都收取）
            tax: 交易稅率（僅賣出時收取）
            slippage: 滑點率
            position_size: 每次交易的固定股數（None 表示全倉）
            max_position_pct: 最大倉位比例（0-1）
            strategy_params: 策略參數
            timeframe: 時間粒度 ('1day', '1min', '5min', '15min', '30min', '60min')

        Returns:
            回測結果字典
        """
        logger.info(f"Starting backtest {backtest_id} for {stock_id} ({timeframe})")

        # 1. 根據 timeframe 載入資料
        if timeframe == '1day':
            # 日線回測：使用原有的 load_data 方法
            data_df = self.load_data(stock_id, start_date, end_date)
        else:
            # 分鐘線回測：使用新的 load_minute_data 方法
            data_df = self.load_minute_data(stock_id, start_date, end_date, timeframe)

        if data_df is None or len(data_df) == 0:
            raise ValueError(
                f"No data available for {stock_id} ({timeframe}, "
                f"{start_date} to {end_date})"
            )

        # 2. 創建策略類
        strategy_class = self.create_strategy_class(strategy_code)

        # 3. 初始化 Cerebro
        self.cerebro = bt.Cerebro()

        # 4. 添加資料饋送
        data_feed = DatabaseDataFeed(dataname=data_df)
        self.cerebro.adddata(data_feed)

        # 5. 添加策略
        if strategy_params:
            self.cerebro.addstrategy(strategy_class, **strategy_params)
        else:
            self.cerebro.addstrategy(strategy_class)

        # 6. 設定初始資金
        self.cerebro.broker.setcash(initial_cash)

        # 7. 設定交易成本（手續費 + 交易稅）
        # Backtrader 的 commission 參數會同時應用於買入和賣出
        # 台股交易稅只在賣出時收取，需要特殊處理
        total_commission = commission  # 買入時的成本
        # 注意：Backtrader 不直接支援單向稅率，這裡簡化為總成本
        # 實際應用中可以通過自定義 CommissionInfo 類別來實現
        self.cerebro.broker.setcommission(commission=total_commission)

        # 8. 設定滑點（如果有）
        if slippage > 0:
            # Backtrader 滑點以百分比形式設定
            self.cerebro.broker.set_slippage_perc(slippage)

        # 9. 添加分析器
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

        # 9.5. 添加自定義 Analyzer（記錄每日淨值）
        self.cerebro.addanalyzer(DailyValueAnalyzer, _name='daily_value')

        # 10. 記錄初始資金
        start_value = self.cerebro.broker.getvalue()
        logger.info(f"Starting Portfolio Value: {start_value:.2f}")

        # 11. 執行回測
        try:
            results = self.cerebro.run()
            strategy_instance = results[0]
        except Exception as e:
            logger.error(f"Backtest execution failed: {str(e)}")
            raise ValueError(f"Backtest execution failed: {str(e)}")

        # 12. 記錄最終資金
        final_value = self.cerebro.broker.getvalue()
        logger.info(f"Final Portfolio Value: {final_value:.2f}")

        # 13. 提取交易記錄
        trades = self._extract_trades(strategy_instance)

        # 14. 提取每日淨值數據（從 DailyValueAnalyzer）
        daily_nav_data = self._extract_daily_nav(strategy_instance)

        # 13.5. 轉換為權益曲線格式（用於計算指標）
        equity_curve = [
            (datetime.fromisoformat(record['date']), record['value'])
            for record in daily_nav_data
        ]

        # 如果沒有每日數據，使用簡化版本
        if not equity_curve:
            logger.warning("No daily nav data available, using simplified equity curve")
            equity_curve = [
                (start_date, start_value),
                (end_date, final_value)
            ]

        # 14. 計算績效指標
        metrics = PerformanceAnalyzer.calculate_metrics(
            initial_cash=initial_cash,
            final_value=final_value,
            trades=trades,
            equity_curve=equity_curve
        )

        # 15. 計算詳細視覺化數據
        detailed_results = self._calculate_detailed_results(
            daily_nav_data=daily_nav_data,
            trades=trades,
            initial_cash=initial_cash
        )

        logger.info(f"Backtest completed. Total Return: {metrics['total_return']}%")

        return {
            "metrics": metrics,
            "trades": trades,
            "initial_cash": initial_cash,
            "final_value": final_value,
            "detailed_results": detailed_results,  # 新增詳細結果
        }

    def _extract_trades(self, strategy_instance) -> List[Dict]:
        """
        從策略實例提取交易記錄

        優先使用 TrackingStrategy 的 trade_records（包含完整的進出場信息）
        如果不可用，回退到使用 TradeAnalyzer 的統計摘要
        """
        trades = []

        try:
            # 檢查策略實例是否有 trade_records 屬性（來自 TrackingStrategy）
            if hasattr(strategy_instance, 'trade_records') and strategy_instance.trade_records:
                logger.info(f"Extracting {len(strategy_instance.trade_records)} detailed trade records from TrackingStrategy")
                return strategy_instance.trade_records

            # 如果沒有 trade_records，回退到使用 TradeAnalyzer
            logger.warning("Strategy instance does not have trade_records, using TradeAnalyzer fallback")

            trade_analyzer = strategy_instance.analyzers.trades.get_analysis()

            # Backtrader 的 TradeAnalyzer 提供統計信息
            # 但不提供詳細的每筆交易記錄
            # 這裡我們使用統計信息來構造交易摘要

            if hasattr(trade_analyzer, 'total') and trade_analyzer.total.total > 0:
                total_trades = trade_analyzer.total.total
                won_total = trade_analyzer.won.total if hasattr(trade_analyzer, 'won') else 0
                lost_total = trade_analyzer.lost.total if hasattr(trade_analyzer, 'lost') else 0

                won_pnl_total = trade_analyzer.won.pnl.total if hasattr(trade_analyzer, 'won') else 0
                lost_pnl_total = trade_analyzer.lost.pnl.total if hasattr(trade_analyzer, 'lost') else 0

                logger.info(f"Trade Analysis - Total: {total_trades}, Won: {won_total}, Lost: {lost_total}")

                # 生成交易摘要（注意：這不是實際的逐筆交易記錄）
                if won_total > 0:
                    avg_won_pnl = won_pnl_total / won_total
                    for i in range(min(won_total, 10)):  # 最多顯示 10 筆獲利交易
                        trades.append({
                            'entry_date': None,
                            'exit_date': None,
                            'entry_price': 0,
                            'exit_price': 0,
                            'shares': 0,
                            'pnl': avg_won_pnl,
                            'commission': 0,
                            'holding_days': 0,
                            'direction': 'long',
                        })

                if lost_total > 0:
                    avg_lost_pnl = lost_pnl_total / lost_total
                    for i in range(min(lost_total, 10)):  # 最多顯示 10 筆虧損交易
                        trades.append({
                            'entry_date': None,
                            'exit_date': None,
                            'entry_price': 0,
                            'exit_price': 0,
                            'shares': 0,
                            'pnl': avg_lost_pnl,
                            'commission': 0,
                            'holding_days': 0,
                            'direction': 'long',
                        })

        except Exception as e:
            logger.warning(f"Could not extract trades: {str(e)}")

        return trades

    def _extract_daily_nav(self, strategy_instance) -> List[Dict]:
        """
        從 DailyValueAnalyzer 中提取每日淨值數據

        Returns:
            每日淨值記錄列表: [{'date': '2024-01-01', 'value': 1000000, 'cash': 500000, 'stock_value': 500000}, ...]
        """
        try:
            # Backtrader Analyzer 有標準的訪問方式：strategy.analyzers.<name>
            if hasattr(strategy_instance, 'analyzers'):
                # 獲取 daily_value analyzer
                if hasattr(strategy_instance.analyzers, 'daily_value'):
                    daily_value_analyzer = strategy_instance.analyzers.daily_value
                    daily_records = daily_value_analyzer.get_analysis()
                    logger.info(f"✅ Extracted {len(daily_records)} daily nav records from DailyValueAnalyzer")
                    return daily_records
                else:
                    logger.warning("⚠️ DailyValueAnalyzer not found in strategy.analyzers")
                    logger.debug(f"Available analyzers: {list(strategy_instance.analyzers.__dict__.keys())}")
            else:
                logger.warning("⚠️ Strategy instance does not have analyzers attribute")

            return []

        except Exception as e:
            logger.error(f"❌ Error extracting daily nav: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def _calculate_detailed_results(
        self,
        daily_nav_data: List[Dict],
        trades: List[Dict],
        initial_cash: float
    ) -> Dict[str, Any]:
        """
        計算詳細的視覺化數據

        Args:
            daily_nav_data: 每日淨值數據
            trades: 交易記錄
            initial_cash: 初始資金

        Returns:
            包含詳細視覺化數據的字典
        """
        try:
            detailed_results = {}

            # 1. 每日淨值（已經在 daily_nav_data 中）
            detailed_results['daily_nav'] = daily_nav_data

            # 2. 月度報酬
            detailed_results['monthly_returns'] = self._calculate_monthly_returns(daily_nav_data)

            # 3. 滾動夏普率（30 天窗口）
            detailed_results['rolling_sharpe'] = self._calculate_rolling_sharpe(daily_nav_data, window=30)

            # 4. 回撤時間序列
            detailed_results['drawdown_series'] = self._calculate_drawdown_series(daily_nav_data)

            # 5. 交易分佈統計
            detailed_results['trade_distribution'] = self._calculate_trade_distribution(trades)

            logger.info("Successfully calculated detailed visualization data")
            return detailed_results

        except Exception as e:
            logger.error(f"Error calculating detailed results: {str(e)}")
            return {}

    def _calculate_monthly_returns(self, daily_nav_data: List[Dict]) -> List[Dict]:
        """計算月度報酬率"""
        if not daily_nav_data:
            return []

        monthly_returns = []
        current_month = None
        month_start_value = None

        for record in daily_nav_data:
            date_str = record['date']
            value = record['value']
            month = date_str[:7]  # 'YYYY-MM'

            if current_month is None:
                # 第一個月
                current_month = month
                month_start_value = value
            elif month != current_month:
                # 月份變更，計算上個月的報酬率
                if month_start_value and month_start_value > 0:
                    prev_value = daily_nav_data[daily_nav_data.index(record) - 1]['value']
                    return_pct = ((prev_value - month_start_value) / month_start_value) * 100

                    monthly_returns.append({
                        'month': current_month,
                        'return_pct': round(return_pct, 2)
                    })

                # 開始新月份
                current_month = month
                month_start_value = value

        # 處理最後一個月
        if current_month and month_start_value and month_start_value > 0 and daily_nav_data:
            final_value = daily_nav_data[-1]['value']
            return_pct = ((final_value - month_start_value) / month_start_value) * 100
            monthly_returns.append({
                'month': current_month,
                'return_pct': round(return_pct, 2)
            })

        return monthly_returns

    def _calculate_rolling_sharpe(self, daily_nav_data: List[Dict], window: int = 30) -> List[Dict]:
        """計算滾動夏普率"""
        if len(daily_nav_data) < window + 1:
            return []

        rolling_sharpe = []

        for i in range(window, len(daily_nav_data)):
            # 取最近 window 天的數據
            window_data = daily_nav_data[i-window:i+1]

            # 計算日報酬率
            returns = []
            for j in range(1, len(window_data)):
                prev_value = window_data[j-1]['value']
                curr_value = window_data[j]['value']
                if prev_value > 0:
                    daily_return = (curr_value - prev_value) / prev_value
                    returns.append(daily_return)

            if returns:
                # 計算平均報酬率和標準差
                avg_return = sum(returns) / len(returns)
                variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
                std_dev = variance ** 0.5

                if std_dev > 0:
                    # 年化（假設 252 個交易日）
                    annualized_return = avg_return * 252
                    annualized_std = std_dev * (252 ** 0.5)
                    sharpe = annualized_return / annualized_std

                    rolling_sharpe.append({
                        'date': window_data[-1]['date'],
                        'sharpe': round(sharpe, 2)
                    })

        return rolling_sharpe

    def _calculate_drawdown_series(self, daily_nav_data: List[Dict]) -> List[Dict]:
        """計算回撤時間序列"""
        if not daily_nav_data:
            return []

        drawdown_series = []
        peak = daily_nav_data[0]['value']

        for record in daily_nav_data:
            value = record['value']

            # 更新峰值
            if value > peak:
                peak = value

            # 計算回撤百分比
            if peak > 0:
                drawdown_pct = ((value - peak) / peak) * 100
            else:
                drawdown_pct = 0

            drawdown_series.append({
                'date': record['date'],
                'drawdown_pct': round(drawdown_pct, 2)
            })

        return drawdown_series

    def _calculate_trade_distribution(self, trades: List[Dict]) -> Dict[str, Any]:
        """計算交易分佈統計"""
        if not trades:
            return {
                'profit_bins': [],
                'loss_bins': [],
                'holding_days_dist': {}
            }

        # 分離獲利和虧損交易
        profits = [t['pnl'] for t in trades if t.get('pnl', 0) > 0]
        losses = [t['pnl'] for t in trades if t.get('pnl', 0) < 0]

        # 創建直方圖 bins（使用簡單分組）
        def create_bins(values, num_bins=10):
            if not values:
                return []
            min_val = min(values)
            max_val = max(values)
            if min_val == max_val:
                return [len(values)]
            bin_width = (max_val - min_val) / num_bins
            bins = [0] * num_bins
            for v in values:
                bin_idx = min(int((v - min_val) / bin_width), num_bins - 1)
                bins[bin_idx] += 1
            return bins

        # 持倉天數分佈
        holding_days_dist = defaultdict(int)
        for t in trades:
            days = t.get('holding_days', 0)
            # 分組：0-1天, 2-5天, 6-10天, 11-20天, 21+天
            if days <= 1:
                key = '0-1 days'
            elif days <= 5:
                key = '2-5 days'
            elif days <= 10:
                key = '6-10 days'
            elif days <= 20:
                key = '11-20 days'
            else:
                key = '21+ days'
            holding_days_dist[key] += 1

        return {
            'profit_bins': create_bins(profits),
            'loss_bins': create_bins(losses),
            'holding_days_dist': dict(holding_days_dist)
        }

    def save_results(
        self,
        backtest_id: int,
        results: Dict[str, Any]
    ) -> bool:
        """
        儲存回測結果到資料庫

        Args:
            backtest_id: 回測 ID
            results: 回測結果字典（包含 metrics 和 trades）

        Returns:
            是否成功
        """
        try:
            metrics = results['metrics']
            trades = results.get('trades', [])

            # 1. 創建 BacktestResult 記錄
            result = BacktestResult(
                backtest_id=backtest_id,
                total_return=Decimal(str(metrics['total_return'])),
                annual_return=Decimal(str(metrics.get('annual_return', 0))),  # 新增：年化報酬率
                sharpe_ratio=Decimal(str(metrics['sharpe_ratio'])),
                max_drawdown=Decimal(str(metrics['max_drawdown_pct'])),  # 使用百分比
                volatility=Decimal(str(metrics.get('volatility', 0))),  # 新增：波動率
                win_rate=Decimal(str(metrics['win_rate'])),
                profit_factor=Decimal(str(metrics['profit_factor'])),
                total_trades=metrics['total_trades'],
                winning_trades=metrics['winning_trades'],
                losing_trades=metrics['losing_trades'],
                average_profit=Decimal(str(metrics['avg_win'])),
                average_loss=Decimal(str(metrics['avg_loss'])),
                final_portfolio_value=Decimal(str(metrics['final_value'])),
                detailed_results=results.get('detailed_results'),  # 新增：詳細視覺化數據
            )

            self.db.add(result)
            self.db.flush()  # 獲取 result.id

            # 2. 獲取 Backtest 記錄以取得 stock_id
            backtest = self.db.query(Backtest).filter(Backtest.id == backtest_id).first()
            if not backtest:
                raise ValueError(f"Backtest {backtest_id} not found")

            stock_id = backtest.symbol

            # 3. 儲存交易記錄
            saved_trade_count = 0

            # 檢測交易格式：Qlib 格式 (date + action) 或 Backtrader 格式 (entry_date + exit_date)
            is_qlib_format = trades and 'action' in trades[0] and 'date' in trades[0]

            if is_qlib_format:
                # === Qlib 格式：單筆交易（date + action） ===
                logger.info(f"💾 Detected Qlib trade format (individual buy/sell actions)")
                logger.info(f"   Total trades to save: {len(trades)}")

                for i, trade_data in enumerate(trades):
                    try:
                        if not trade_data.get('date'):
                            logger.warning(f"   ⚠️  Trade {i+1}: Missing date, skipping")
                            continue

                        trade_date = trade_data['date']
                        # 確保日期是 date 對象
                        if isinstance(trade_date, str):
                            from datetime import datetime
                            trade_date = datetime.strptime(trade_date, '%Y-%m-%d').date()
                        elif hasattr(trade_date, 'date'):
                            trade_date = trade_date.date()

                        action = trade_data['action']
                        price = float(trade_data['price'])
                        quantity = int(trade_data.get('shares', 0))
                        pnl = float(trade_data.get('pnl', 0))

                        # 簡化手續費計算（0.1425%）
                        commission = price * quantity * 0.001425
                        total_amount = price * quantity + (commission if action == 'BUY' else -commission)

                        # 創建單筆交易記錄
                        trade = Trade(
                            backtest_id=backtest_id,
                            stock_id=stock_id,
                            date=trade_date,
                            action=TradeAction.BUY if action == 'BUY' else TradeAction.SELL,
                            quantity=quantity,
                            price=Decimal(str(price)),
                            commission=Decimal(str(commission)),
                            tax=Decimal('0'),
                            total_amount=Decimal(str(total_amount)),
                            profit_loss=Decimal(str(pnl)) if action == 'SELL' and pnl != 0 else None,
                        )
                        self.db.add(trade)
                        saved_trade_count += 1

                        if (i + 1) % 50 == 0:
                            logger.debug(f"   Progress: {i+1}/{len(trades)} trades saved...")

                    except Exception as e:
                        logger.error(f"   ❌ Failed to save trade {i+1}: {str(e)}")
                        logger.error(f"      Trade data: {trade_data}")
                        # Continue to save other trades
                        continue

                logger.info(f"✅ Successfully saved {saved_trade_count}/{len(trades)} Qlib trade records for backtest {backtest_id}")

            else:
                # === Backtrader 格式：配對交易（entry_date + exit_date） ===
                logger.info(f"Detected Backtrader trade format (paired entry/exit)")
                for trade_data in trades:
                    # 只保存有效的交易記錄（有日期和價格的）
                    if not trade_data.get('entry_date') or not trade_data.get('exit_date'):
                        continue

                    entry_date = trade_data['entry_date']
                    exit_date = trade_data['exit_date']

                    # 確保日期是 date 對象
                    if hasattr(entry_date, 'date'):
                        entry_date = entry_date.date()
                    if hasattr(exit_date, 'date'):
                        exit_date = exit_date.date()

                    entry_price = float(trade_data['entry_price'])
                    exit_price = float(trade_data['exit_price'])
                    size = int(trade_data.get('size', 0))
                    commission = float(trade_data.get('commission', 0))
                    pnl = float(trade_data['pnl'])

                    # 計算交易總額
                    buy_amount = entry_price * size
                    sell_amount = exit_price * size

                    # 手續費分配到買入和賣出（簡化：各一半）
                    buy_commission = commission / 2
                    sell_commission = commission / 2

                    # 創建 BUY 記錄
                    buy_trade = Trade(
                        backtest_id=backtest_id,
                        stock_id=stock_id,
                        date=entry_date,
                        action=TradeAction.BUY,
                        quantity=size,
                        price=Decimal(str(entry_price)),
                        commission=Decimal(str(buy_commission)),
                        tax=Decimal('0'),  # 買入無交易稅
                        total_amount=Decimal(str(buy_amount + buy_commission)),
                        profit_loss=None,  # 買入時無盈虧
                    )
                    self.db.add(buy_trade)

                    # 創建 SELL 記錄
                    sell_trade = Trade(
                        backtest_id=backtest_id,
                        stock_id=stock_id,
                        date=exit_date,
                        action=TradeAction.SELL,
                        quantity=size,
                        price=Decimal(str(exit_price)),
                        commission=Decimal(str(sell_commission)),
                        tax=Decimal('0'),  # 簡化：暫不計算交易稅
                        total_amount=Decimal(str(sell_amount - sell_commission)),
                        profit_loss=Decimal(str(pnl)),  # 賣出時記錄盈虧
                    )
                    self.db.add(sell_trade)

                    saved_trade_count += 2  # BUY + SELL = 2 筆記錄

                logger.info(f"Saved {saved_trade_count} Backtrader trade records ({saved_trade_count // 2} complete trades) for backtest {backtest_id}")

            # 4. 更新 Backtest 狀態
            backtest.status = 'COMPLETED'  # 使用大寫

            self.db.commit()

            logger.info(f"Successfully saved results for backtest {backtest_id}")
            return True

        except Exception as e:
            logger.error(f"Error saving results: {str(e)}")
            self.db.rollback()
            return False
