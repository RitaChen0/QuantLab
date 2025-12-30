"""
Alpha158+ 因子計算引擎

完整實現 Microsoft Qlib 的 Alpha158 因子庫並增強為 179 個因子
增強版包含額外的成交量分析因子（VSTD, WVMA, VSUMP, VSUMN, VSUMD）
使用 Pandas/NumPy 計算，無需依賴 Qlib 的數據格式
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from loguru import logger


class Alpha158Calculator:
    """
    Alpha158+ 因子計算器

    實現 179 個量化因子（基於 Qlib Alpha158 並增強）：
    - 9 個 KBar 因子
    - 20 個 Price 因子
    - 5 個 Volume 因子
    - 145 個 Rolling 因子（含增強版成交量分析）
    """

    def __init__(self):
        self.default_windows = [5, 10, 20, 30, 60]

    # ==================== 輔助函數 ====================

    @staticmethod
    def greater(a: pd.Series, b: pd.Series) -> pd.Series:
        """Greater($a, $b): 返回兩者中較大的值"""
        return pd.concat([a, b], axis=1).max(axis=1)

    @staticmethod
    def less(a: pd.Series, b: pd.Series) -> pd.Series:
        """Less($a, $b): 返回兩者中較小的值"""
        return pd.concat([a, b], axis=1).min(axis=1)

    @staticmethod
    def slope(series: pd.Series, window: int) -> pd.Series:
        """Slope($close, N): 計算 N 天線性回歸斜率"""
        def calc_slope(y):
            if len(y) < 2:
                return np.nan
            x = np.arange(len(y))
            # 使用最小二乘法計算斜率
            x_mean = x.mean()
            y_mean = y.mean()
            numerator = ((x - x_mean) * (y - y_mean)).sum()
            denominator = ((x - x_mean) ** 2).sum()
            return numerator / denominator if denominator != 0 else 0

        return series.rolling(window=window, min_periods=2).apply(calc_slope, raw=True)

    @staticmethod
    def rsquare(series: pd.Series, window: int) -> pd.Series:
        """Rsquare($close, N): 計算 N 天線性回歸 R²"""
        def calc_rsquare(y):
            if len(y) < 2:
                return np.nan
            x = np.arange(len(y))

            # 計算線性回歸
            x_mean = x.mean()
            y_mean = y.mean()

            numerator = ((x - x_mean) * (y - y_mean)).sum()
            denominator_x = ((x - x_mean) ** 2).sum()
            denominator_y = ((y - y_mean) ** 2).sum()

            if denominator_x == 0 or denominator_y == 0:
                return 0

            r = numerator / np.sqrt(denominator_x * denominator_y)
            return r ** 2

        return series.rolling(window=window, min_periods=2).apply(calc_rsquare, raw=True)

    @staticmethod
    def resi(series: pd.Series, window: int) -> pd.Series:
        """Resi($close, N): 計算 N 天線性回歸殘差"""
        def calc_residual(y):
            if len(y) < 2:
                return np.nan
            x = np.arange(len(y))

            # 計算斜率和截距
            x_mean = x.mean()
            y_mean = y.mean()
            numerator = ((x - x_mean) * (y - y_mean)).sum()
            denominator = ((x - x_mean) ** 2).sum()

            if denominator == 0:
                return 0

            slope = numerator / denominator
            intercept = y_mean - slope * x_mean

            # 預測值
            y_pred = slope * x[-1] + intercept
            # 殘差（實際值 - 預測值）
            return y[-1] - y_pred

        return series.rolling(window=window, min_periods=2).apply(calc_residual, raw=True)

    @staticmethod
    def rank(series: pd.Series, window: int) -> pd.Series:
        """Rank($close, N): 計算當前值在過去 N 天的百分位排名"""
        return series.rolling(window=window, min_periods=1).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=True
        )

    @staticmethod
    def idx_max(series: pd.Series, window: int) -> pd.Series:
        """IdxMax($high, N): 返回過去 N 天最大值距今的天數"""
        return series.rolling(window=window, min_periods=1).apply(
            lambda x: len(x) - np.argmax(x) - 1, raw=True
        )

    @staticmethod
    def idx_min(series: pd.Series, window: int) -> pd.Series:
        """IdxMin($low, N): 返回過去 N 天最小值距今的天數"""
        return series.rolling(window=window, min_periods=1).apply(
            lambda x: len(x) - np.argmin(x) - 1, raw=True
        )

    # ==================== KBar 因子 (9個) ====================

    def compute_kbar_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        計算 KBar 因子（K線形態因子）

        輸入需要：$open, $high, $low, $close
        輸出：9 個 KBar 因子
        """
        result = df.copy()

        open_p = df['$open']
        high = df['$high']
        low = df['$low']
        close = df['$close']

        # 1. KMID: (close-open)/open - 實體相對於開盤價的比例
        result['KMID'] = (close - open_p) / open_p

        # 2. KLEN: (high-low)/open - 影線長度相對於開盤價
        result['KLEN'] = (high - low) / open_p

        # 3. KMID2: (close-open)/(high-low+1e-12) - 實體佔總波動的比例
        result['KMID2'] = (close - open_p) / (high - low + 1e-12)

        # 4. KUP: (high-max(open,close))/open - 上影線
        result['KUP'] = (high - self.greater(open_p, close)) / open_p

        # 5. KUP2: (high-max(open,close))/(high-low+1e-12) - 上影線比例
        result['KUP2'] = (high - self.greater(open_p, close)) / (high - low + 1e-12)

        # 6. KLOW: (min(open,close)-low)/open - 下影線
        result['KLOW'] = (self.less(open_p, close) - low) / open_p

        # 7. KLOW2: (min(open,close)-low)/(high-low+1e-12) - 下影線比例
        result['KLOW2'] = (self.less(open_p, close) - low) / (high - low + 1e-12)

        # 8. KSFT: (2*close-high-low)/open - 收盤價位置
        result['KSFT'] = (2 * close - high - low) / open_p

        # 9. KSFT2: (2*close-high-low)/(high-low+1e-12) - 收盤價相對位置
        result['KSFT2'] = (2 * close - high - low) / (high - low + 1e-12)

        return result

    # ==================== Price 因子 (20個) ====================

    def compute_price_factors(
        self,
        df: pd.DataFrame,
        windows: List[int] = None,
        features: List[str] = None
    ) -> pd.DataFrame:
        """
        計算 Price 因子（歷史價格因子）

        輸入需要：$open, $high, $low, $close, $vwap (optional)
        輸出：window數量 × feature數量 個因子
        """
        if windows is None:
            windows = [0, 1, 2, 3, 4]
        if features is None:
            features = ['OPEN', 'HIGH', 'LOW', 'CLOSE']
            if '$vwap' in df.columns:
                features.append('VWAP')

        result = df.copy()
        close = df['$close']

        for feature in features:
            field = f'${feature.lower()}'
            if field not in df.columns:
                continue

            for d in windows:
                if d == 0:
                    # 當天價格 / 收盤價
                    result[f'{feature}{d}'] = df[field] / close
                else:
                    # d 天前價格 / 當天收盤價
                    result[f'{feature}{d}'] = df[field].shift(d) / close

        return result

    # ==================== Volume 因子 (5個) ====================

    def compute_volume_factors(
        self,
        df: pd.DataFrame,
        windows: List[int] = None
    ) -> pd.DataFrame:
        """
        計算 Volume 因子（成交量因子）

        輸入需要：$volume
        輸出：window數量 個因子
        """
        if windows is None:
            windows = [0, 1, 2, 3, 4]

        result = df.copy()
        volume = df['$volume']

        for d in windows:
            if d == 0:
                # 當天成交量 / (成交量+epsilon)
                result[f'VOLUME{d}'] = volume / (volume + 1e-12)
            else:
                # d 天前成交量 / (當天成交量+epsilon)
                result[f'VOLUME{d}'] = volume.shift(d) / (volume + 1e-12)

        return result

    # ==================== Rolling 因子 (145個，含增強版成交量分析) ====================

    def compute_rolling_factors(
        self,
        df: pd.DataFrame,
        windows: List[int] = None,
        include: List[str] = None,
        exclude: List[str] = None
    ) -> pd.DataFrame:
        """
        計算 Rolling 因子（滾動窗口技術指標）

        輸入需要：$close, $high, $low, $volume
        輸出：最多 145 個 rolling 因子（含增強版成交量分析）
        """
        if windows is None:
            windows = self.default_windows
        if exclude is None:
            exclude = []

        def use(name):
            return name not in exclude and (include is None or name in include)

        result = df.copy()
        close = df['$close']
        high = df['$high']
        low = df['$low']
        volume = df['$volume']

        for d in windows:
            # ROC: Rate of Change (變化率)
            if use('ROC'):
                result[f'ROC{d}'] = close.shift(d) / close

            # MA: Moving Average (移動平均)
            if use('MA'):
                result[f'MA{d}'] = close.rolling(window=d, min_periods=1).mean() / close

            # STD: Standard Deviation (標準差)
            if use('STD'):
                result[f'STD{d}'] = close.rolling(window=d, min_periods=1).std() / close

            # BETA: Slope (線性回歸斜率)
            if use('BETA'):
                result[f'BETA{d}'] = self.slope(close, d) / close

            # RSQR: R-square (R²)
            if use('RSQR'):
                result[f'RSQR{d}'] = self.rsquare(close, d)

            # RESI: Residual (殘差)
            if use('RESI'):
                result[f'RESI{d}'] = self.resi(close, d) / close

            # MAX: Maximum High (最高價)
            if use('MAX'):
                result[f'MAX{d}'] = high.rolling(window=d, min_periods=1).max() / close

            # MIN: Minimum Low (最低價)
            if use('MIN'):
                result[f'MIN{d}'] = low.rolling(window=d, min_periods=1).min() / close

            # QTLU: Upper Quantile (80% 分位數)
            if use('QTLU'):
                result[f'QTLU{d}'] = close.rolling(window=d, min_periods=1).quantile(0.8) / close

            # QTLD: Lower Quantile (20% 分位數)
            if use('QTLD'):
                result[f'QTLD{d}'] = close.rolling(window=d, min_periods=1).quantile(0.2) / close

            # RANK: Percentile Rank (百分位排名)
            if use('RANK'):
                result[f'RANK{d}'] = self.rank(close, d)

            # RSV: Relative Strength Value (相對強弱值)
            if use('RSV'):
                min_low = low.rolling(window=d, min_periods=1).min()
                max_high = high.rolling(window=d, min_periods=1).max()
                result[f'RSV{d}'] = (close - min_low) / (max_high - min_low + 1e-12)

            # IMAX: Index of Maximum (最高價距今天數)
            if use('IMAX'):
                result[f'IMAX{d}'] = self.idx_max(high, d) / d

            # IMIN: Index of Minimum (最低價距今天數)
            if use('IMIN'):
                result[f'IMIN{d}'] = self.idx_min(low, d) / d

            # IMXD: Max-Min Index Difference (最高最低價時間差)
            if use('IMXD'):
                result[f'IMXD{d}'] = (self.idx_max(high, d) - self.idx_min(low, d)) / d

            # CORR: Correlation (價格與成交量相關性)
            if use('CORR'):
                log_volume = np.log(volume + 1)
                result[f'CORR{d}'] = close.rolling(window=d, min_periods=1).corr(log_volume)

            # CORD: Change Correlation (變化率相關性)
            if use('CORD'):
                close_change = close / close.shift(1)
                volume_change = np.log(volume / volume.shift(1) + 1)
                result[f'CORD{d}'] = close_change.rolling(window=d, min_periods=1).corr(volume_change)

            # CNTP: Count Positive (上漲天數比例)
            if use('CNTP'):
                up_days = (close > close.shift(1)).astype(int)
                result[f'CNTP{d}'] = up_days.rolling(window=d, min_periods=1).mean()

            # CNTN: Count Negative (下跌天數比例)
            if use('CNTN'):
                down_days = (close < close.shift(1)).astype(int)
                result[f'CNTN{d}'] = down_days.rolling(window=d, min_periods=1).mean()

            # CNTD: Count Difference (漲跌天數差)
            if use('CNTD'):
                up_days = (close > close.shift(1)).astype(int)
                down_days = (close < close.shift(1)).astype(int)
                result[f'CNTD{d}'] = (up_days - down_days).rolling(window=d, min_periods=1).mean()

            # SUMP: Sum Positive (總上漲/總變化)
            if use('SUMP'):
                change = close - close.shift(1)
                positive = np.maximum(change, 0)
                abs_change = np.abs(change)
                result[f'SUMP{d}'] = positive.rolling(window=d, min_periods=1).sum() / (
                    abs_change.rolling(window=d, min_periods=1).sum() + 1e-12
                )

            # SUMN: Sum Negative (總下跌/總變化)
            if use('SUMN'):
                change = close - close.shift(1)
                negative = np.maximum(-change, 0)
                abs_change = np.abs(change)
                result[f'SUMN{d}'] = negative.rolling(window=d, min_periods=1).sum() / (
                    abs_change.rolling(window=d, min_periods=1).sum() + 1e-12
                )

            # SUMD: Sum Difference (漲跌差/總變化)
            if use('SUMD'):
                change = close - close.shift(1)
                positive = np.maximum(change, 0)
                negative = np.maximum(-change, 0)
                abs_change = np.abs(change)
                result[f'SUMD{d}'] = (positive - negative).rolling(window=d, min_periods=1).sum() / (
                    abs_change.rolling(window=d, min_periods=1).sum() + 1e-12
                )

            # VMA: Volume Moving Average (成交量移動平均)
            if use('VMA'):
                result[f'VMA{d}'] = volume.rolling(window=d, min_periods=1).mean() / (volume + 1e-12)

            # VSTD: Volume Standard Deviation (成交量標準差)
            if use('VSTD'):
                result[f'VSTD{d}'] = volume.rolling(window=d, min_periods=1).std() / (volume + 1e-12)

            # WVMA: Weighted Volume Moving Average (加權成交量移動平均)
            if use('WVMA'):
                price_change = np.abs(close / close.shift(1) - 1)
                weighted = price_change * volume
                result[f'WVMA{d}'] = weighted.rolling(window=d, min_periods=1).std() / (
                    weighted.rolling(window=d, min_periods=1).mean() + 1e-12
                )

            # VSUMP: Volume Sum Positive (成交量總增加/總變化)
            if use('VSUMP'):
                volume_change = volume - volume.shift(1)
                positive = np.maximum(volume_change, 0)
                abs_change = np.abs(volume_change)
                result[f'VSUMP{d}'] = positive.rolling(window=d, min_periods=1).sum() / (
                    abs_change.rolling(window=d, min_periods=1).sum() + 1e-12
                )

            # VSUMN: Volume Sum Negative (成交量總減少/總變化)
            if use('VSUMN'):
                volume_change = volume - volume.shift(1)
                negative = np.maximum(-volume_change, 0)
                abs_change = np.abs(volume_change)
                result[f'VSUMN{d}'] = negative.rolling(window=d, min_periods=1).sum() / (
                    abs_change.rolling(window=d, min_periods=1).sum() + 1e-12
                )

            # VSUMD: Volume Sum Difference (成交量漲跌差/總變化)
            if use('VSUMD'):
                volume_change = volume - volume.shift(1)
                positive = np.maximum(volume_change, 0)
                negative = np.maximum(-volume_change, 0)
                abs_change = np.abs(volume_change)
                result[f'VSUMD{d}'] = (positive - negative).rolling(window=d, min_periods=1).sum() / (
                    abs_change.rolling(window=d, min_periods=1).sum() + 1e-12
                )

        return result

    # ==================== 完整 Alpha158+ 計算（179 個因子） ====================

    def compute_all_factors(
        self,
        df: pd.DataFrame,
        config: Dict = None
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        計算完整的 Alpha158+ 因子集（179 個因子）

        Args:
            df: 原始 OHLCV DataFrame（需包含 $open, $high, $low, $close, $volume）
            config: 配置字典，可選參數：
                - kbar: {} - 是否計算 KBar 因子（9個）
                - price: {windows: [...], feature: [...]} - Price 因子配置（20個）
                - volume: {windows: [...]} - Volume 因子配置（5個）
                - rolling: {windows: [...], include: [...], exclude: [...]} - Rolling 因子配置（145個）

        Returns:
            (result_df, factor_names): 包含所有因子的 DataFrame 和因子名稱列表
        """
        if config is None:
            config = {
                'kbar': {},
                'price': {'windows': [0, 1, 2, 3, 4], 'feature': ['OPEN', 'HIGH', 'LOW', 'CLOSE']},
                'volume': {'windows': [0, 1, 2, 3, 4]},
                'rolling': {'windows': [5, 10, 20, 30, 60]}
            }

        result = df.copy()
        factor_names = []

        # 1. KBar 因子
        if 'kbar' in config:
            logger.info("Computing KBar factors...")
            result = self.compute_kbar_factors(result)
            factor_names.extend(['KMID', 'KLEN', 'KMID2', 'KUP', 'KUP2', 'KLOW', 'KLOW2', 'KSFT', 'KSFT2'])

        # 2. Price 因子
        if 'price' in config:
            logger.info("Computing Price factors...")
            result = self.compute_price_factors(
                result,
                windows=config['price'].get('windows', [0, 1, 2, 3, 4]),
                features=config['price'].get('feature', ['OPEN', 'HIGH', 'LOW', 'CLOSE'])
            )
            # 添加因子名稱
            for feat in config['price'].get('feature', ['OPEN', 'HIGH', 'LOW', 'CLOSE']):
                for w in config['price'].get('windows', [0, 1, 2, 3, 4]):
                    factor_names.append(f'{feat}{w}')

        # 3. Volume 因子
        if 'volume' in config:
            logger.info("Computing Volume factors...")
            result = self.compute_volume_factors(
                result,
                windows=config['volume'].get('windows', [0, 1, 2, 3, 4])
            )
            for w in config['volume'].get('windows', [0, 1, 2, 3, 4]):
                factor_names.append(f'VOLUME{w}')

        # 4. Rolling 因子
        if 'rolling' in config:
            logger.info("Computing Rolling factors...")
            result = self.compute_rolling_factors(
                result,
                windows=config['rolling'].get('windows', [5, 10, 20, 30, 60]),
                include=config['rolling'].get('include', None),
                exclude=config['rolling'].get('exclude', [])
            )
            # Rolling 因子名稱會根據配置動態生成
            # 這裡簡化處理，實際使用時可以從 result.columns 提取

        logger.info(f"Computed {len([col for col in result.columns if col not in df.columns])} Alpha158+ factors")

        return result, factor_names


# 全局實例
alpha158_calculator = Alpha158Calculator()
