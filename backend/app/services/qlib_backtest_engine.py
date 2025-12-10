"""
Qlib 回測引擎

此模組負責使用 Qlib 執行量化策略回測。
支援機器學習模型和傳統策略。
"""
from datetime import date, datetime
from typing import Dict, List, Optional, Any
import pandas as pd
from loguru import logger
from sqlalchemy.orm import Session

from app.services.qlib_data_adapter import QlibDataAdapter
from app.core.qlib_config import qlib_config
from app.services.alpha158_factors import alpha158_calculator


class QlibBacktestEngine:
    """
    Qlib 回測引擎

    支援：
    - 機器學習策略
    - 因子策略
    - 組合優化策略
    """

    def __init__(self, db: Session):
        self.db = db
        self.data_adapter = QlibDataAdapter()

        # 確保 Qlib 已初始化
        if not qlib_config.is_qlib_available():
            logger.warning("Qlib is not available")
            self.qlib_available = False
        else:
            self.qlib_available = True
            qlib_config.init_qlib()

    def _compute_qlib_expressions(
        self,
        df: pd.DataFrame,
        fields: List[str]
    ) -> pd.DataFrame:
        """
        計算 Qlib 表達式（使用 pandas 實作）- 已棄用

        ⚠️ DEPRECATED: 此方法使用 pandas 手動模擬 Qlib 表達式計算。
        現已改用 QlibDataAdapter.get_qlib_features() 直接使用 Qlib 引擎。

        此方法保留作為 fallback，當 Qlib 本地數據不可用時使用。

        Args:
            df: 原始 OHLCV DataFrame（必須包含 $open, $high, $low, $close, $volume 欄位）
            fields: Qlib 表達式列表

        Returns:
            DataFrame: 包含計算結果的數據
        """
        logger.warning(
            "_compute_qlib_expressions() is deprecated. "
            "Using Qlib native engine instead (via QlibDataAdapter.get_qlib_features())."
        )
        import re
        import numpy as np

        result_df = df.copy()

        for field in fields:
            try:
                # 跳過基礎字段（已經存在）
                if field in ['$open', '$high', '$low', '$close', '$volume']:
                    continue

                # Mean($close, N) - N 日移動平均
                match = re.match(r'Mean\(\$(\w+),\s*(\d+)\)', field)
                if match:
                    col_name, window = match.groups()
                    window = int(window)
                    result_df[field] = df[f'${col_name}'].rolling(window=window, min_periods=1).mean()
                    continue

                # Std($close, N) - N 日標準差
                match = re.match(r'Std\(\$(\w+),\s*(\d+)\)', field)
                if match:
                    col_name, window = match.groups()
                    window = int(window)
                    result_df[field] = df[f'${col_name}'].rolling(window=window, min_periods=1).std()
                    continue

                # Ref($close, N) - N 日前的值
                match = re.match(r'Ref\(\$(\w+),\s*(\d+)\)', field)
                if match:
                    col_name, periods = match.groups()
                    periods = int(periods)
                    result_df[field] = df[f'${col_name}'].shift(periods)
                    continue

                # Max($high, N) - N 日最大值
                match = re.match(r'Max\(\$(\w+),\s*(\d+)\)', field)
                if match:
                    col_name, window = match.groups()
                    window = int(window)
                    result_df[field] = df[f'${col_name}'].rolling(window=window, min_periods=1).max()
                    continue

                # Min($low, N) - N 日最小值
                match = re.match(r'Min\(\$(\w+),\s*(\d+)\)', field)
                if match:
                    col_name, window = match.groups()
                    window = int(window)
                    result_df[field] = df[f'${col_name}'].rolling(window=window, min_periods=1).min()
                    continue

                # Corr($close, $volume, N) - N 日相關係數
                match = re.match(r'Corr\(\$(\w+),\s*\$(\w+),\s*(\d+)\)', field)
                if match:
                    col1, col2, window = match.groups()
                    window = int(window)
                    result_df[field] = df[f'${col1}'].rolling(window=window, min_periods=1).corr(df[f'${col2}'])
                    continue

                # 複雜表達式：($close - Mean($close, N)) / Std($close, N)
                match = re.match(r'\(\$(\w+)\s*-\s*Mean\(\$\w+,\s*(\d+)\)\)\s*/\s*Std\(\$\w+,\s*(\d+)\)', field)
                if match:
                    col_name, mean_window, std_window = match.groups()
                    mean_window = int(mean_window)
                    std_window = int(std_window)
                    mean_val = df[f'${col_name}'].rolling(window=mean_window, min_periods=1).mean()
                    std_val = df[f'${col_name}'].rolling(window=std_window, min_periods=1).std()
                    result_df[field] = (df[f'${col_name}'] - mean_val) / (std_val + 1e-8)
                    continue

                # 複雜表達式：Ref($close, N) / $close - 1
                match = re.match(r'Ref\(\$(\w+),\s*(\d+)\)\s*/\s*\$\w+\s*-\s*1', field)
                if match:
                    col_name, periods = match.groups()
                    periods = int(periods)
                    result_df[field] = df[f'${col_name}'].shift(periods) / df[f'${col_name}'] - 1
                    continue

                # 複雜表達式：Mean($close, N1) / Mean($close, N2)
                match = re.match(r'Mean\(\$(\w+),\s*(\d+)\)\s*/\s*Mean\(\$\w+,\s*(\d+)\)', field)
                if match:
                    col_name, window1, window2 = match.groups()
                    window1 = int(window1)
                    window2 = int(window2)
                    ma1 = df[f'${col_name}'].rolling(window=window1, min_periods=1).mean()
                    ma2 = df[f'${col_name}'].rolling(window=window2, min_periods=1).mean()
                    result_df[field] = ma1 / (ma2 + 1e-8)
                    continue

                # 複雜表達式：Max($high, N) - Min($low, N)
                match = re.match(r'Max\(\$(\w+),\s*(\d+)\)\s*-\s*Min\(\$(\w+),\s*(\d+)\)', field)
                if match:
                    high_col, high_window, low_col, low_window = match.groups()
                    high_window = int(high_window)
                    low_window = int(low_window)
                    max_high = df[f'${high_col}'].rolling(window=high_window, min_periods=1).max()
                    min_low = df[f'${low_col}'].rolling(window=low_window, min_periods=1).min()
                    result_df[field] = max_high - min_low
                    continue

                logger.warning(f"Unsupported Qlib expression: {field}")

            except Exception as e:
                logger.error(f"Failed to compute expression '{field}': {str(e)}")

        return result_df

    def _get_alpha158_data(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        config: Optional[Dict] = None
    ) -> Optional[pd.DataFrame]:
        """
        使用 Alpha158 因子庫獲取數據

        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期
            config: Alpha158 配置（可選）

        Returns:
            DataFrame: 包含 Alpha158 因子的數據
        """
        try:
            logger.info(f"Computing Alpha158 factors for {symbol}")

            # 1. 獲取基礎 OHLCV 數據
            base_df = self.data_adapter.get_qlib_ohlcv(symbol, start_date, end_date)

            if base_df is None or base_df.empty:
                logger.warning(f"No base data available for {symbol}")
                return None

            # 2. 計算 Alpha158 因子
            result_df, factor_names = alpha158_calculator.compute_all_factors(base_df, config)

            logger.info(f"Computed {len(factor_names)} Alpha158 factors with {len(result_df)} rows")
            logger.debug(f"Sample factors: {factor_names[:10]}")

            return result_df

        except Exception as e:
            logger.error(f"Failed to compute Alpha158 factors: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return None

    def _get_qlib_data_with_expressions(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        fields: Optional[List[str]] = None
    ) -> Optional[pd.DataFrame]:
        """
        使用 Qlib 表達式獲取數據（直接使用 D.features() API）

        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期
            fields: Qlib 表達式字段列表（如 ['$close', 'Mean($close, 5)']）

        Returns:
            DataFrame: 包含計算結果的數據
        """
        try:
            logger.info(f"Using Qlib expressions engine for {symbol}")

            # 直接使用 QlibDataAdapter 的 get_qlib_features() 方法
            # 這會優先從本地 qlib 數據讀取，並使用 qlib 表達式引擎計算指標
            result_df = self.data_adapter.get_qlib_features(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                fields=fields
            )

            if result_df is None or result_df.empty:
                logger.warning(f"No data available for {symbol}")
                return None

            logger.info(f"✅ Got {len(result_df)} rows with {len(result_df.columns)} fields from Qlib")
            logger.debug(f"Fields: {list(result_df.columns)[:10]}")

            return result_df

        except Exception as e:
            logger.error(f"Failed to get Qlib expressions data: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return None

    async def run_backtest(
        self,
        strategy_code: str,
        symbol: str,
        start_date: date,
        end_date: date,
        initial_capital: float,
        parameters: dict
    ) -> dict:
        """
        執行 Qlib 回測

        Args:
            strategy_code: 策略代碼或配置
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期
            initial_capital: 初始資金
            parameters: 策略參數

        Returns:
            dict: 回測結果（標準格式）
        """
        if not self.qlib_available:
            raise RuntimeError("Qlib is not available. Please install it first.")

        try:
            logger.info(f"Starting Qlib backtest for {symbol} from {start_date} to {end_date}")

            # 1. 準備數據
            logger.info("Preparing data...")

            # 檢查是否使用 Qlib 表達式
            use_qlib_expressions = parameters.get('use_qlib_expressions', False)
            qlib_fields = parameters.get('qlib_fields', None)

            # 嘗試從策略代碼中提取 QLIB_FIELDS（使用正則表達式，不執行代碼）
            if not qlib_fields and 'QLIB_FIELDS' in strategy_code:
                try:
                    import re
                    import ast

                    # 使用正則表達式提取 QLIB_FIELDS = [...] 定義
                    # 支援多行列表定義
                    pattern = r'QLIB_FIELDS\s*=\s*\[(.*?)\]'
                    match = re.search(pattern, strategy_code, re.DOTALL)

                    if match:
                        # 提取列表內容並使用 ast.literal_eval 安全解析
                        list_content = '[' + match.group(1) + ']'
                        qlib_fields = ast.literal_eval(list_content)
                        logger.info(f"Extracted QLIB_FIELDS from strategy code: {qlib_fields}")
                        use_qlib_expressions = True
                    else:
                        logger.warning("QLIB_FIELDS pattern not found in strategy code")
                except Exception as e:
                    logger.warning(f"Failed to extract QLIB_FIELDS from strategy code: {e}")

            # 優先使用 Qlib 表達式（從本地 qlib 數據讀取 + 自動計算指標）
            if use_qlib_expressions or qlib_fields:
                logger.info("Using Qlib expressions engine...")

                # ⚠️ 重要：確保包含基礎 OHLCV 欄位，用於交易模擬
                # 因為 _simulate_trading 需要 $close 來計算權益和執行交易
                base_fields = ['$open', '$high', '$low', '$close', '$volume', '$factor']

                if qlib_fields:
                    # 合併基礎欄位和自定義因子欄位，避免重複
                    all_fields = base_fields + [f for f in qlib_fields if f not in base_fields]
                else:
                    all_fields = base_fields

                dataset = self._get_qlib_data_with_expressions(
                    symbol, start_date, end_date, fields=all_fields
                )
            else:
                # Fallback: 使用 get_qlib_features()，它會優先從本地讀取
                logger.info("Using Qlib features with default technical indicators...")
                dataset = self.data_adapter.get_qlib_features(
                    symbol, start_date, end_date
                )

            if dataset is None or dataset.empty:
                raise ValueError(f"No data available for {symbol}")

            # 2. 解析策略
            logger.info("Parsing strategy...")
            strategy_type = parameters.get('strategy_type', 'simple')

            if strategy_type == 'ml_model':
                # 機器學習策略
                result = await self._run_ml_backtest(
                    strategy_code, dataset, symbol, start_date, end_date,
                    initial_capital, parameters
                )
            else:
                # 簡單策略（基於信號）
                result = await self._run_simple_backtest(
                    strategy_code, dataset, symbol, start_date, end_date,
                    initial_capital, parameters
                )

            logger.info(f"Qlib backtest completed for {symbol}")
            return result

        except Exception as e:
            logger.error(f"Qlib backtest failed: {str(e)}")
            raise

    async def _run_simple_backtest(
        self,
        strategy_code: str,
        dataset: pd.DataFrame,
        symbol: str,
        start_date: date,
        end_date: date,
        initial_capital: float,
        parameters: dict
    ) -> dict:
        """
        執行簡單策略回測（基於技術指標信號）

        Args:
            strategy_code: 策略代碼
            dataset: 數據 DataFrame
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期
            initial_capital: 初始資金
            parameters: 策略參數

        Returns:
            dict: 回測結果
        """
        try:
            # 執行策略代碼生成信號
            signals = self._execute_strategy_code(strategy_code, dataset, parameters)

            # 模擬交易
            trades, equity_curve = self._simulate_trading(
                signals, dataset, initial_capital, symbol
            )

            # 計算績效指標
            metrics = self._calculate_metrics(
                equity_curve, trades, initial_capital
            )

            return {
                'trades': trades,
                'equity_curve': equity_curve,
                'metrics': metrics,
                'engine': 'qlib',
                'strategy_type': 'simple'
            }

        except Exception as e:
            logger.error(f"Simple backtest failed: {str(e)}")
            raise

    async def _run_ml_backtest(
        self,
        strategy_code: str,
        dataset: pd.DataFrame,
        symbol: str,
        start_date: date,
        end_date: date,
        initial_capital: float,
        parameters: dict
    ) -> dict:
        """
        執行機器學習策略回測

        使用 LightGBM 預測未來收益率，根據預測結果生成交易信號

        Args:
            strategy_code: 模型配置或訓練代碼
            dataset: 數據 DataFrame（含技術指標）
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期
            initial_capital: 初始資金
            parameters: 策略參數

        Returns:
            dict: 回測結果
        """
        try:
            logger.info("Starting ML model backtest...")

            # 1. 特徵工程：創建目標變數（未來 N 日收益率）
            prediction_days = parameters.get('prediction_days', 5)
            dataset = dataset.copy()  # 避免修改原始數據
            dataset['target'] = dataset['$close'].shift(-prediction_days) / dataset['$close'] - 1

            # 2. 準備訓練/測試數據
            train_ratio = parameters.get('train_ratio', 0.7)
            split_index = int(len(dataset) * train_ratio)

            train_data = dataset.iloc[:split_index]
            test_data = dataset.iloc[split_index:]

            logger.info(f"Train: {len(train_data)} days, Test: {len(test_data)} days")

            # 3. 選擇特徵（排除基礎價格欄位和目標）
            feature_cols = [col for col in dataset.columns
                          if col not in ['$open', '$high', '$low', '$close', '$volume', '$factor', 'target']
                          and not dataset[col].isna().all()]

            if len(feature_cols) == 0:
                raise ValueError("No valid features found for ML model")

            logger.info(f"Using {len(feature_cols)} features: {feature_cols[:5]}...")

            # 4. 訓練 LightGBM 模型
            try:
                import lightgbm as lgb
            except ImportError:
                logger.error("LightGBM not installed, using simple linear model")
                # 使用簡單線性模型作為替代
                signals = self._simple_ml_predict(dataset, test_data, feature_cols)
                return await self._run_simple_backtest(
                    "",  # 無需策略代碼
                    dataset,
                    symbol,
                    start_date,
                    end_date,
                    initial_capital,
                    parameters,
                    signals  # 使用預測信號
                )

            # 準備訓練數據
            X_train = train_data[feature_cols].fillna(0)
            y_train = train_data['target'].fillna(0)

            # 移除無效數據
            valid_mask = ~y_train.isna()
            X_train = X_train[valid_mask]
            y_train = y_train[valid_mask]

            # 訓練模型
            model = lgb.LGBMRegressor(
                n_estimators=parameters.get('n_estimators', 100),
                learning_rate=parameters.get('learning_rate', 0.05),
                max_depth=parameters.get('max_depth', 5),
                num_leaves=parameters.get('num_leaves', 31),
                random_state=42,
                verbose=-1
            )

            logger.info("Training LightGBM model...")
            model.fit(X_train, y_train)

            # 5. 生成預測和交易信號
            X_test = test_data[feature_cols].fillna(0)
            predictions = model.predict(X_test)

            # 根據預測收益率生成信號
            threshold = parameters.get('signal_threshold', 0.02)  # 2% 閾值

            signals = pd.Series(0, index=dataset.index)
            test_indices = test_data.index

            for i, (idx, pred) in enumerate(zip(test_indices, predictions)):
                if pred > threshold:
                    signals.loc[idx] = 1  # 買入
                elif pred < -threshold:
                    signals.loc[idx] = -1  # 賣出

            logger.info(f"Generated {(signals == 1).sum()} buy and {(signals == -1).sum()} sell signals")

            # 6. 執行回測
            trades, equity_curve = self._simulate_trading(
                signals,
                dataset,
                initial_capital,
                parameters
            )

            # 7. 計算績效
            metrics = self._calculate_metrics(
                equity_curve,
                trades,
                initial_capital
            )

            # 添加 ML 模型特定指標
            metrics['model_type'] = 'LightGBM'
            metrics['train_samples'] = len(X_train)
            metrics['test_samples'] = len(X_test)
            metrics['feature_count'] = len(feature_cols)
            metrics['prediction_days'] = prediction_days

            logger.info(f"ML backtest completed: {len(trades)} trades, Return: {metrics.get('total_return', 0):.2%}")

            return {
                'trades': trades,
                'equity_curve': equity_curve,
                'metrics': metrics,
                'engine': 'qlib',
                'strategy_type': 'ml_model',
                'model_info': {
                    'type': 'LightGBM',
                    'features': feature_cols[:10],  # 前 10 個特徵
                    'train_size': len(X_train),
                    'test_size': len(X_test)
                }
            }

        except Exception as e:
            logger.error(f"ML backtest failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def _simple_ml_predict(
        self,
        dataset: pd.DataFrame,
        test_data: pd.DataFrame,
        feature_cols: list
    ) -> pd.Series:
        """
        簡單 ML 預測（當 LightGBM 不可用時使用）
        使用動量和均值回歸的組合
        """
        signals = pd.Series(0, index=dataset.index)

        # 使用簡單規則：動量 + 均值回歸
        if '$return' in dataset.columns and '$ma_20' in dataset.columns:
            momentum = dataset['$return'].rolling(5).mean()
            ma_ratio = dataset['$close'] / dataset['$ma_20'] - 1

            for idx in test_data.index:
                if momentum.loc[idx] > 0.01 and ma_ratio.loc[idx] > -0.05:
                    signals.loc[idx] = 1
                elif momentum.loc[idx] < -0.01 and ma_ratio.loc[idx] < 0.05:
                    signals.loc[idx] = -1

        return signals

    def _execute_strategy_code(
        self,
        code: str,
        dataset: pd.DataFrame,
        parameters: dict
    ) -> pd.Series:
        """
        執行策略代碼生成交易信號

        Args:
            code: 策略代碼
            dataset: 數據 DataFrame
            parameters: 策略參數

        Returns:
            pd.Series: 交易信號（1=買入, -1=賣出, 0=持有）
        """
        try:
            # 導入 Qlib 模組（預先導入以避免在策略代碼中需要 __import__）
            try:
                from qlib.data import D
                import numpy as np
                import lightgbm as lgb
            except ImportError as e:
                logger.warning(f"Import error: {e}, using pandas only")
                D = None
                import numpy as np
                lgb = None

            # 創建受限的安全命名空間（完全隔離 __builtins__）
            # 與 backtest_engine.py 保持一致的安全策略
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
            }

            # 創建執行環境（使用受限的 __builtins__）
            env = {
                '__builtins__': safe_builtins,  # 🔒 安全限制：防止代碼注入攻擊
                'pd': pd,
                'np': np,
                'D': D,  # Qlib data API
                'lgb': lgb,  # LightGBM for ML strategies
                'df': dataset,
                'params': parameters,
                'signals': pd.Series(0, index=dataset.index)
            }

            # 移除策略代碼中的 import 語句（因為我們已預先導入所需模組）
            import re
            cleaned_code = re.sub(r'^\s*from\s+[\w.]+\s+import\s+.*$', '', code, flags=re.MULTILINE)
            cleaned_code = re.sub(r'^\s*import\s+[\w., ]+\s*$', '', cleaned_code, flags=re.MULTILINE)

            logger.info(f"📊 Executing strategy code...")
            logger.info(f"   Dataset shape: {dataset.shape}")
            logger.info(f"   Date range: {dataset.index[0]} to {dataset.index[-1]}")
            logger.info(f"   Parameters: {parameters}")

            # 執行策略代碼
            exec(cleaned_code, env)

            signals = env.get('signals', pd.Series(0, index=dataset.index))

            # 詳細信號統計
            buy_signals = len(signals[signals == 1])
            sell_signals = len(signals[signals == -1])
            hold_signals = len(signals[signals == 0])
            total_signals = len(signals)

            logger.info(f"✅ Signal generation completed:")
            logger.info(f"   📈 BUY signals:  {buy_signals} ({buy_signals/total_signals*100:.1f}%)")
            logger.info(f"   📉 SELL signals: {sell_signals} ({sell_signals/total_signals*100:.1f}%)")
            logger.info(f"   ⏸️  HOLD signals: {hold_signals} ({hold_signals/total_signals*100:.1f}%)")
            logger.info(f"   📊 Total days:   {total_signals}")

            return signals

        except Exception as e:
            logger.error(f"Failed to execute strategy code: {str(e)}")
            raise

    def _simulate_trading(
        self,
        signals: pd.Series,
        dataset: pd.DataFrame,
        initial_capital: float,
        symbol: str
    ) -> tuple[List[dict], List[dict]]:
        """
        模擬交易執行

        Args:
            signals: 交易信號
            dataset: 價格數據
            initial_capital: 初始資金
            symbol: 股票代碼

        Returns:
            tuple: (交易記錄列表, 資金曲線列表)
        """
        logger.info(f"💰 Starting trade simulation...")
        logger.info(f"   Initial capital: ${initial_capital:,.2f}")
        logger.info(f"   Symbol: {symbol}")

        trades = []
        equity_curve = []

        cash = initial_capital
        position = 0
        entry_price = 0
        buy_count = 0
        sell_count = 0

        for idx in dataset.index:
            signal = signals.get(idx, 0)
            price = dataset.loc[idx, '$close']

            # 計算當前權益
            equity = cash + position * price
            equity_curve.append({
                'date': idx.strftime('%Y-%m-%d'),
                'equity': float(equity)
            })

            # 執行交易
            if signal == 1 and position == 0:  # 買入信號
                shares = int(cash / price)
                if shares > 0:
                    position = shares
                    entry_price = price
                    cash -= shares * price
                    buy_count += 1

                    trade_value = shares * price
                    logger.debug(f"   📈 BUY  {idx.strftime('%Y-%m-%d')}: {shares} shares @ ${price:.2f} = ${trade_value:,.2f}")

                    trades.append({
                        'date': idx.strftime('%Y-%m-%d'),
                        'action': 'BUY',
                        'price': float(price),
                        'shares': shares,
                        'symbol': symbol
                    })

            elif signal == -1 and position > 0:  # 賣出信號
                cash += position * price
                pnl = (price - entry_price) * position
                sell_count += 1

                trade_value = position * price
                pnl_pct = (price / entry_price - 1) * 100
                logger.debug(f"   📉 SELL {idx.strftime('%Y-%m-%d')}: {position} shares @ ${price:.2f} = ${trade_value:,.2f} (PnL: ${pnl:+,.2f} / {pnl_pct:+.2f}%)")

                trades.append({
                    'date': idx.strftime('%Y-%m-%d'),
                    'action': 'SELL',
                    'price': float(price),
                    'shares': position,
                    'symbol': symbol,
                    'pnl': float(pnl)
                })

                position = 0
                entry_price = 0

        # 最終結算
        if position > 0:
            final_price = dataset.iloc[-1]['$close']
            final_pnl = (final_price - entry_price) * position
            cash += position * final_price
            sell_count += 1

            logger.info(f"   🔚 Final settlement: Selling {position} shares @ ${final_price:.2f} (PnL: ${final_pnl:+,.2f})")

            trades.append({
                'date': dataset.index[-1].strftime('%Y-%m-%d'),
                'action': 'SELL',
                'price': float(final_price),
                'shares': position,
                'symbol': symbol,
                'pnl': float(final_pnl)
            })

        # 計算總體統計
        final_equity = cash
        total_return = (final_equity / initial_capital - 1) * 100
        total_trades = len(trades)

        logger.info(f"✅ Trade simulation completed:")
        logger.info(f"   📊 Total trades:    {total_trades} ({buy_count} BUY + {sell_count} SELL)")
        logger.info(f"   💵 Initial capital: ${initial_capital:,.2f}")
        logger.info(f"   💰 Final equity:    ${final_equity:,.2f}")
        logger.info(f"   📈 Total return:    {total_return:+.2f}%")

        return trades, equity_curve

    def _calculate_metrics(
        self,
        equity_curve: List[dict],
        trades: List[dict],
        initial_capital: float
    ) -> dict:
        """
        計算績效指標

        Args:
            equity_curve: 資金曲線
            trades: 交易記錄
            initial_capital: 初始資金

        Returns:
            dict: 績效指標
        """
        if not equity_curve:
            return {}

        equities = [item['equity'] for item in equity_curve]
        final_equity = equities[-1]
        num_days = len(equity_curve)

        # 計算報酬
        total_return = (final_equity - initial_capital) / initial_capital

        # 計算年化報酬率
        # 公式：(1 + total_return) ^ (365 / days) - 1
        if num_days > 0:
            annual_return = (1 + total_return) ** (365.0 / num_days) - 1
        else:
            annual_return = 0

        # 計算每日報酬率
        daily_returns = []
        for i in range(1, len(equities)):
            daily_return = (equities[i] - equities[i-1]) / equities[i-1] if equities[i-1] != 0 else 0
            daily_returns.append(daily_return)

        # 計算波動率（日報酬率標準差的年化值）
        if len(daily_returns) > 1:
            import numpy as np
            volatility = float(np.std(daily_returns) * np.sqrt(252))  # 年化波動率
        else:
            volatility = 0

        # 計算夏普比率
        # 公式：(年化報酬率 - 無風險利率) / 年化波動率
        risk_free_rate = 0.02  # 假設無風險利率 2%
        if volatility != 0:
            sharpe_ratio = (annual_return - risk_free_rate) / volatility
        else:
            sharpe_ratio = 0

        # 計算最大回撤
        peak = equities[0]
        max_drawdown = 0
        for equity in equities:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # 計算勝率
        winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
        win_rate = len(winning_trades) / len(trades) if trades else 0

        # 計算平均獲利/虧損
        profits = [t['pnl'] for t in trades if t.get('pnl', 0) > 0]
        losses = [t['pnl'] for t in trades if t.get('pnl', 0) < 0]

        avg_profit = sum(profits) / len(profits) if profits else 0
        avg_loss = sum(losses) / len(losses) if losses else 0

        return {
            'total_return': float(total_return),
            'annual_return': float(annual_return),
            'final_equity': float(final_equity),
            'max_drawdown': float(max_drawdown),
            'volatility': float(volatility),
            'sharpe_ratio': float(sharpe_ratio),
            'win_rate': float(win_rate),
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losses),  # 修復：使用實際虧損交易數
            'avg_profit': float(avg_profit),
            'avg_loss': float(avg_loss),
            'profit_factor': abs(avg_profit / avg_loss) if avg_loss != 0 else 0
        }

    def convert_to_standard_result(
        self,
        qlib_result: dict
    ) -> dict:
        """
        將 Qlib 結果轉換為標準格式（與 Backtrader 兼容）

        Args:
            qlib_result: Qlib 回測結果

        Returns:
            dict: 標準格式的結果（包含 metrics 和 trades）
        """
        metrics = qlib_result.get('metrics', {})

        return {
            'metrics': {
                'final_value': metrics.get('final_equity', 0),
                'total_return': metrics.get('total_return', 0),
                'annual_return': metrics.get('annual_return', 0),  # 新增：年化報酬率
                'max_drawdown_pct': metrics.get('max_drawdown', 0),  # 百分比格式
                'volatility': metrics.get('volatility', 0),  # 新增：波動率
                'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                'win_rate': metrics.get('win_rate', 0),
                'total_trades': metrics.get('total_trades', 0),
                'winning_trades': metrics.get('winning_trades', 0),
                'losing_trades': metrics.get('losing_trades', 0),
                'avg_win': metrics.get('avg_profit', 0),  # 修復：使用正確的鍵名
                'avg_loss': metrics.get('avg_loss', 0),
                'profit_factor': metrics.get('profit_factor', 0),
            },
            'trades': qlib_result.get('trades', []),
            'engine': 'qlib',
            'strategy_type': qlib_result.get('strategy_type', 'unknown')
        }
