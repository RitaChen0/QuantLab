"""
Qlib 數據適配器

此模組負責從 Qlib 本地數據讀取或 FinLab API 獲取數據。
"""
from datetime import date, datetime, timedelta
from typing import Optional, Dict, List
import pandas as pd
import numpy as np
from loguru import logger
from sqlalchemy.orm import Session
from pathlib import Path

from app.services.finlab_client import FinLabClient
from app.utils.cache import cached_method
from app.core.qlib_config import qlib_config


class QlibDataAdapter:
    """
    Qlib 數據適配器

    優先從 Qlib 本地數據讀取，不存在時才從 FinLab API 獲取：
    - OHLCV 數據（使用 D.features() 讀取）
    - 技術指標因子（使用 Qlib 表達式自動計算）
    - 基本面數據
    """

    def __init__(self):
        self.finlab_client = FinLabClient()
        self.qlib_initialized = False

        # 嘗試初始化 qlib
        if qlib_config.is_qlib_available():
            try:
                qlib_config.init_qlib()
                self.qlib_initialized = True
                logger.info("✅ Qlib initialized for data adapter")
            except Exception as e:
                logger.warning(f"Failed to initialize Qlib: {e}, will fallback to FinLab API")
                self.qlib_initialized = False

    def _check_qlib_data_exists(self, symbol: str) -> bool:
        """
        檢查 Qlib 本地數據是否存在

        Args:
            symbol: 股票代碼

        Returns:
            bool: 數據是否存在
        """
        if not self.qlib_initialized:
            return False

        try:
            # Qlib 官方格式 v2: features/<instrument>/close.day.bin
            data_path = Path(qlib_config.get_data_path()) / 'features' / symbol.lower()
            close_file = data_path / 'close.day.bin'
            exists = close_file.exists()

            if not exists:
                logger.debug(f"Qlib data not found for {symbol} at {close_file}")

            return exists
        except Exception as e:
            logger.debug(f"Failed to check Qlib data for {symbol}: {e}")
            return False

    @cached_method(
        key_prefix="qlib_ohlcv",
        expiry=3600,
        key_func=lambda symbol, start_date, end_date, fields=None: (
            f"{symbol}:{start_date if isinstance(start_date, str) else start_date.isoformat()}:{end_date if isinstance(end_date, str) else end_date.isoformat()}:UTC"
        )
    )
    def get_qlib_ohlcv(
        self,
        symbol: str,
        start_date,  # Union[date, str]
        end_date,    # Union[date, str]
        fields: Optional[List[str]] = None
    ) -> Optional[pd.DataFrame]:
        """
        獲取 Qlib 格式的 OHLCV 數據

        優先從 Qlib 本地數據讀取，不存在時從 FinLab API 獲取。

        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期
            fields: 要獲取的欄位（Qlib 表達式），預設為基礎 OHLCV

        Returns:
            DataFrame: Qlib 格式的 OHLCV 數據
                - 索引: datetime
                - 欄位: $open, $high, $low, $close, $volume, $factor
        """
        # 預設欄位
        if fields is None:
            fields = ['$open', '$high', '$low', '$close', '$volume']

        try:
            # 方法 1: 優先從 Qlib 本地數據讀取
            if self.qlib_initialized and self._check_qlib_data_exists(symbol):
                try:
                    from qlib.data import D

                    logger.info(f"📂 Reading {symbol} from Qlib local data")

                    # 處理日期參數：支援 str 和 date/datetime 兩種格式
                    start_str = start_date if isinstance(start_date, str) else start_date.isoformat()
                    end_str = end_date if isinstance(end_date, str) else end_date.isoformat()

                    df = D.features(
                        instruments=[symbol],
                        fields=fields,
                        start_time=start_str,
                        end_time=end_str
                    )

                    if df is not None and not df.empty:
                        # D.features() 返回 MultiIndex (instrument, datetime)
                        # 提取單一股票的數據
                        if isinstance(df.index, pd.MultiIndex):
                            df = df.xs(symbol, level=0)

                        # 添加 $factor（如果不存在）
                        if '$factor' not in df.columns:
                            df['$factor'] = 1.0

                        logger.info(f"✅ Loaded {len(df)} rows from Qlib for {symbol}")
                        return df

                except Exception as e:
                    logger.warning(f"Failed to read from Qlib: {e}, fallback to FinLab API")

            # 方法 2: Fallback 到 FinLab API
            logger.info(f"📡 Fetching {symbol} from FinLab API (Qlib data not available)")

            # 處理日期參數：支援 str 和 date/datetime 兩種格式
            start_str = start_date if isinstance(start_date, str) else start_date.isoformat()
            end_str = end_date if isinstance(end_date, str) else end_date.isoformat()

            df = self.finlab_client.get_ohlcv(
                stock_id=symbol,
                start_date=start_str,
                end_date=end_str
            )

            if df is None or df.empty:
                logger.warning(f"No OHLCV data found for {symbol}")
                return None

            # 轉換為 Qlib 格式
            qlib_df = pd.DataFrame()
            qlib_df['$open'] = df['open']
            qlib_df['$high'] = df['high']
            qlib_df['$low'] = df['low']
            qlib_df['$close'] = df['close']
            qlib_df['$volume'] = df['volume']
            qlib_df['$factor'] = 1.0  # 暫時設為 1（未復權）

            # 確保索引是 datetime
            if not isinstance(qlib_df.index, pd.DatetimeIndex):
                qlib_df.index = pd.to_datetime(qlib_df.index)

            logger.info(f"✅ Converted {len(qlib_df)} rows from FinLab API for {symbol}")
            return qlib_df

        except Exception as e:
            logger.error(f"Failed to get OHLCV data for {symbol}: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return None

    def get_qlib_features(
        self,
        symbol: str,
        start_date,  # Union[date, str]
        end_date,    # Union[date, str]
        fields: Optional[List[str]] = None
    ) -> Optional[pd.DataFrame]:
        """
        使用 Qlib 表達式獲取數據和技術指標

        此方法完全使用 Qlib 引擎計算技術指標，不需要手動用 pandas 計算。

        Args:
            symbol: 股票代碼
            start_date: 開始日期 (date 或 str)
            end_date: 結束日期 (date 或 str)
            fields: Qlib 表達式列表（預設為常用技術指標）

        Returns:
            DataFrame: 包含 OHLCV 和技術指標的數據

        Examples:
            常用 Qlib 表達式：
            - '$close', '$volume'  # 基礎欄位
            - 'Mean($close, 5)'  # 5 日均線
            - 'Std($close, 20)'  # 20 日標準差
            - 'Ref($close, 1)'  # 昨日收盤價
            - '($close - Mean($close, 20)) / Std($close, 20)'  # Z-score
            - 'Corr($close, $volume, 10)'  # 價量相關性
        """
        # 預設技術指標（使用 Qlib 表達式）
        if fields is None:
            fields = [
                # 基礎 OHLCV
                '$open', '$high', '$low', '$close', '$volume',

                # 移動平均
                'Mean($close, 5)', 'Mean($close, 10)',
                'Mean($close, 20)', 'Mean($close, 60)',

                # 均線比率
                '$close / Mean($close, 5)',
                '$close / Mean($close, 20)',

                # 波動率
                'Std($close, 5)', 'Std($close, 20)',

                # 動量
                'Ref($close, 5) / $close - 1',
                'Ref($close, 10) / $close - 1',

                # 價量關係
                '$volume / Mean($volume, 20)',
                'Corr($close, $volume, 10)',

                # 價格範圍
                '$high / $low',
                '$close / $open',
            ]

        try:
            # 使用 Qlib D.features() 一次性獲取所有數據和指標
            if self.qlib_initialized and self._check_qlib_data_exists(symbol):
                try:
                    from qlib.data import D

                    logger.info(f"📊 Computing features with Qlib expressions for {symbol}")

                    # 處理日期參數：支援 str 和 date/datetime 兩種格式
                    start_str = start_date if isinstance(start_date, str) else start_date.isoformat()
                    end_str = end_date if isinstance(end_date, str) else end_date.isoformat()

                    df = D.features(
                        instruments=[symbol],
                        fields=fields,
                        start_time=start_str,
                        end_time=end_str,
                        freq='day'  # 指定日線數據頻率
                    )

                    if df is not None and not df.empty:
                        # 提取單一股票數據
                        if isinstance(df.index, pd.MultiIndex):
                            df = df.xs(symbol, level=0)

                        logger.info(f"✅ Computed {len(df.columns)} features, {len(df)} rows")
                        return df

                except Exception as e:
                    logger.warning(f"Failed to use Qlib expressions: {e}")
                    logger.info("Fallback: using basic OHLCV without technical indicators")

            # Fallback: 只獲取基礎 OHLCV
            return self.get_qlib_ohlcv(symbol, start_date, end_date)

        except Exception as e:
            logger.error(f"Failed to get Qlib features for {symbol}: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return None

    def calculate_technical_factors(
        self,
        ohlcv_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        計算技術指標因子（已棄用，建議使用 get_qlib_features）

        ⚠️ DEPRECATED: 此方法使用 pandas 手動計算技術指標。
        建議改用 get_qlib_features() 直接使用 Qlib 表達式引擎。

        Args:
            ohlcv_df: OHLCV DataFrame

        Returns:
            DataFrame: 包含技術指標的 DataFrame
        """
        logger.warning(
            "calculate_technical_factors() is deprecated. "
            "Use get_qlib_features() with Qlib expressions instead."
        )

        try:
            df = ohlcv_df.copy()

            # 計算常用技術指標
            # 價格變化
            df['$return'] = df['$close'].pct_change()
            df['$log_return'] = (df['$close'] / df['$close'].shift(1)).apply(
                lambda x: np.log(x) if pd.notna(x) and x > 0 else 0
            )

            # 移動平均
            for period in [5, 10, 20, 60]:
                df[f'$ma_{period}'] = df['$close'].rolling(window=period).mean()
                df[f'$ma_{period}_ratio'] = df['$close'] / df[f'$ma_{period}']

            # 波動率
            df['$volatility_20'] = df['$return'].rolling(window=20).std()

            # 成交量相關
            df['$volume_ratio'] = df['$volume'] / df['$volume'].rolling(window=20).mean()

            # 價格範圍
            df['$high_low_ratio'] = df['$high'] / df['$low']
            df['$close_open_ratio'] = df['$close'] / df['$open']

            # 動量指標
            for period in [5, 10, 20]:
                df[f'$momentum_{period}'] = df['$close'] / df['$close'].shift(period) - 1

            logger.info(f"Calculated {len(df.columns)} technical factors with pandas")
            return df

        except Exception as e:
            logger.error(f"Failed to calculate technical factors: {str(e)}")
            return ohlcv_df

    def prepare_qlib_dataset(
        self,
        symbols: List[str],
        start_date,  # Union[date, str]
        end_date,    # Union[date, str]
        include_factors: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        為多個股票準備 Qlib 數據集

        Args:
            symbols: 股票代碼列表
            start_date: 開始日期
            end_date: 結束日期
            include_factors: 是否包含技術指標因子

        Returns:
            Dict: {symbol: DataFrame} 映射
        """
        dataset = {}

        for symbol in symbols:
            try:
                # 獲取 OHLCV 數據
                df = self.get_qlib_ohlcv(symbol, start_date, end_date)

                if df is not None and not df.empty:
                    # 計算技術指標
                    if include_factors:
                        df = self.calculate_technical_factors(df)

                    dataset[symbol] = df
                    logger.info(f"Prepared Qlib dataset for {symbol}: {len(df)} rows")

            except Exception as e:
                logger.error(f"Failed to prepare dataset for {symbol}: {str(e)}")
                continue

        logger.info(f"Prepared Qlib dataset for {len(dataset)}/{len(symbols)} symbols")
        return dataset

    def save_to_qlib_format(
        self,
        symbol: str,
        df: pd.DataFrame,
        data_path: str
    ) -> bool:
        """
        將數據保存為 Qlib 磁盤格式

        Args:
            symbol: 股票代碼
            df: 數據 DataFrame
            data_path: Qlib 數據路徑

        Returns:
            bool: 是否保存成功

        Note:
            這需要 Qlib 的 dump_bin.py 工具，目前暫時不實作
            可以使用 Qlib 的 DatasetD 直接從 DataFrame 加載
        """
        try:
            # TODO: 實作保存為 Qlib 二進制格式
            # 目前可以使用記憶體中的 DataFrame
            logger.warning(
                "Saving to Qlib binary format not implemented. "
                "Using in-memory DataFrame instead."
            )
            return False

        except Exception as e:
            logger.error(f"Failed to save Qlib data for {symbol}: {str(e)}")
            return False

    def get_stock_pool(
        self,
        start_date,  # Union[date, str]
        end_date,    # Union[date, str]
        filters: Optional[Dict] = None
    ) -> List[str]:
        """
        獲取股票池（可交易的股票列表）

        Args:
            start_date: 開始日期
            end_date: 結束日期
            filters: 過濾條件（例如市值、產業）

        Returns:
            List[str]: 股票代碼列表
        """
        try:
            # 從 FinLab 獲取股票清單
            stocks_df = self.finlab_client.get_stock_list()

            if stocks_df is None or stocks_df.empty:
                logger.warning("No stocks found in FinLab")
                return []

            # 提取股票代碼
            stock_pool = stocks_df['stock_id'].tolist()

            # TODO: 應用過濾條件
            # - 市值篩選
            # - 產業篩選
            # - 流動性篩選

            logger.info(f"Got stock pool with {len(stock_pool)} symbols")
            return stock_pool

        except Exception as e:
            logger.error(f"Failed to get stock pool: {str(e)}")
            return []

    def get_alpha158_data(
        self,
        symbol: str,
        start_date,  # Union[date, str]
        end_date,    # Union[date, str]
    ) -> Optional[pd.DataFrame]:
        """
        獲取 Alpha158+ 因子數據（179 個因子）

        使用自定義的 Alpha158Calculator，與訓練時保持一致。
        包含 158 個標準 Alpha158 因子 + 21 個增強成交量因子。

        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            DataFrame: 包含 Alpha158+ 因子的數據（179 個特徵）
        """
        try:
            if not self.qlib_initialized or not self._check_qlib_data_exists(symbol):
                logger.warning(f"Qlib data not available for {symbol}, cannot compute Alpha158+")
                return None

            from qlib.data import D
            from app.services.alpha158_factors import alpha158_calculator

            # 處理日期參數
            start_str = start_date if isinstance(start_date, str) else start_date.isoformat()
            end_str = end_date if isinstance(end_date, str) else end_date.isoformat()

            logger.info(f"📊 Computing Alpha158+ features for {symbol}")

            # 先獲取原始 OHLCV 數據
            raw_fields = ['$open', '$high', '$low', '$close', '$volume']
            df_raw = D.features(
                instruments=[symbol],
                fields=raw_fields,
                start_time=start_str,
                end_time=end_str,
                freq='day'
            )

            if df_raw is None or df_raw.empty:
                logger.warning(f"No raw OHLCV data for {symbol}")
                return None

            # 提取單一股票數據（Qlib 返回的是 MultiIndex）
            if isinstance(df_raw.index, pd.MultiIndex):
                df_raw = df_raw.xs(symbol, level=0)

            # 使用 Alpha158Calculator 計算因子
            df_factors, _ = alpha158_calculator.compute_all_factors(df_raw)

            logger.info(f"✅ Computed Alpha158+: {len(df_factors.columns)} features, {len(df_factors)} rows")
            return df_factors

        except Exception as e:
            logger.error(f"Failed to get Alpha158+ data for {symbol}: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return None

    def create_qlib_handler_config(
        self,
        symbols: List[str],
        start_date,  # Union[date, str]
        end_date,    # Union[date, str]
        features: Optional[List[str]] = None
    ) -> Dict:
        """
        創建 Qlib DataHandler 配置

        Args:
            symbols: 股票代碼列表
            start_date: 開始日期
            end_date: 結束日期
            features: 特徵列表（Qlib 表達式）

        Returns:
            Dict: DataHandler 配置
        """
        if features is None:
            # 預設特徵：常用技術指標
            features = [
                "$close",
                "$volume",
                "$open / $close",
                "$high / $close",
                "$low / $close",
                "Mean($close, 5) / $close",
                "Mean($close, 10) / $close",
                "Mean($close, 20) / $close",
                "Std($close, 5)",
                "Std($close, 10)",
                "Std($close, 20)",
                "$volume / Mean($volume, 20)",
            ]

        # 處理日期參數：支援 str 和 date/datetime 兩種格式
        start_str = start_date if isinstance(start_date, str) else start_date.isoformat()
        end_str = end_date if isinstance(end_date, str) else end_date.isoformat()

        config = {
            "start_time": start_str,
            "end_time": end_str,
            "fit_start_time": start_str,
            "fit_end_time": end_str,
            "instruments": symbols,
            "infer_processors": [
                {
                    "class": "FilterCol",
                    "kwargs": {"fields_group": "feature", "col_list": features},
                },
                {
                    "class": "RobustZScoreNorm",
                    "kwargs": {"fields_group": "feature", "clip_outlier": True},
                },
                {
                    "class": "Fillna",
                    "kwargs": {"fields_group": "feature"},
                },
            ],
            "learn_processors": [
                {"class": "DropnaLabel"},
                {"class": "CSRankNorm", "kwargs": {"fields_group": "label"}},
            ],
        }

        return config
