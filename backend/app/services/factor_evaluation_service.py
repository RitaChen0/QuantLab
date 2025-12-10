"""
因子評估服務

提供因子績效評估功能：
- IC (Information Coefficient)
- ICIR (IC Information Ratio)
- Sharpe Ratio
- 年化報酬率
- 最大回撤
- 勝率

使用 Qlib 進行因子評估和回測
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from loguru import logger

try:
    from qlib.data import D
    from qlib.data.dataset import DatasetH
    from qlib.data.dataset.handler import DataHandlerLP
    QLIB_AVAILABLE = True
except ImportError:
    logger.warning("Qlib not available, factor evaluation will use fallback methods")
    QLIB_AVAILABLE = False

from app.models.rdagent import GeneratedFactor, FactorEvaluation
from app.services.qlib_data_adapter import QlibDataAdapter


class FactorEvaluationService:
    """因子評估服務"""

    def __init__(self, db: Session):
        self.db = db
        self.qlib_adapter = QlibDataAdapter()

    def evaluate_factor(
        self,
        factor_id: int,
        stock_pool: str = "all",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        save_to_db: bool = True
    ) -> Dict:
        """
        評估單個因子的績效

        Args:
            factor_id: 因子 ID
            stock_pool: 股票池（all, top100, etc.）
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
            save_to_db: 是否保存到資料庫

        Returns:
            評估結果字典
        """
        logger.info(f"Starting factor evaluation for factor_id={factor_id}")

        # 1. 獲取因子資訊
        factor = self.db.query(GeneratedFactor).filter(
            GeneratedFactor.id == factor_id
        ).first()

        if not factor:
            raise ValueError(f"Factor {factor_id} not found")

        # 2. 設定預設日期範圍（過去 2 年）
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_dt = datetime.now() - timedelta(days=730)  # 2 年
            start_date = start_dt.strftime("%Y-%m-%d")

        logger.info(f"Evaluating factor '{factor.name}' from {start_date} to {end_date}")

        # 3. 獲取股票池
        stock_list = self._get_stock_pool(stock_pool)
        logger.info(f"Stock pool: {len(stock_list)} stocks")

        # 4. 計算因子值和未來收益
        factor_data, returns_data = self._calculate_factor_and_returns(
            factor.formula,
            stock_list,
            start_date,
            end_date
        )

        if factor_data is None or returns_data is None:
            raise ValueError("Failed to calculate factor data or returns")

        # 5. 計算評估指標
        evaluation_results = self._calculate_metrics(factor_data, returns_data)

        # 6. 執行簡單回測（計算 Sharpe、年化報酬等）
        backtest_results = self._simple_backtest(factor_data, returns_data)

        # 7. 合併結果
        final_results = {
            **evaluation_results,
            **backtest_results,
            "stock_pool": stock_pool,
            "start_date": start_date,
            "end_date": end_date,
            "n_stocks": len(stock_list),
            "n_periods": len(factor_data),
        }

        logger.info(f"Evaluation complete: IC={final_results.get('ic', 'N/A'):.4f}, "
                   f"Sharpe={final_results.get('sharpe_ratio', 'N/A'):.4f}")

        # 8. 保存到資料庫
        if save_to_db:
            self._save_evaluation(factor_id, final_results)

        return final_results

    def _get_stock_pool(self, pool_name: str) -> List[str]:
        """獲取股票池列表"""
        # 簡化版：返回所有台股或前 100 大
        # 實際應用中應從資料庫或 FinLab API 獲取
        try:
            from app.services.finlab_client import FinLabClient
            client = FinLabClient()
            stocks_df = client.get_stock_list()

            if pool_name == "top100":
                # 可以根據市值排序取前 100
                return stocks_df['stock_id'].head(100).tolist()
            else:  # all
                return stocks_df['stock_id'].tolist()
        except Exception as e:
            logger.error(f"Failed to get stock pool: {e}")
            # Fallback: 使用一些常見股票
            return ["2330", "2317", "2454", "2308", "2412", "2882", "2881", "1301", "1303", "2886"]

    def _calculate_factor_and_returns(
        self,
        factor_formula: str,
        stock_list: List[str],
        start_date: str,
        end_date: str
    ) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """
        計算因子值和未來收益

        Returns:
            (factor_data, returns_data) - 兩個 DataFrame，index 為日期，columns 為股票代碼
        """
        try:
            if not QLIB_AVAILABLE:
                logger.warning("Qlib not available, using fallback calculation")
                return self._fallback_calculate(stock_list, start_date, end_date)

            # 使用 Qlib 計算因子值
            instruments = [f"SH{s}" if s.startswith("6") else f"SZ{s}" for s in stock_list]

            # 解析因子公式（假設是 Qlib 表達式）
            fields = [factor_formula, "$close"]  # 因子值 + 收盤價計算報酬

            # 使用 QlibDataAdapter 獲取數據
            factor_values_list = []
            close_prices_list = []

            for stock_id in stock_list:
                try:
                    # 獲取因子數據
                    df = self.qlib_adapter.get_qlib_features(
                        stock_id,
                        start_date,
                        end_date,
                        fields=[factor_formula, "$close"]
                    )

                    if df is not None and not df.empty:
                        factor_values_list.append(df.iloc[:, 0].rename(stock_id))
                        close_prices_list.append(df.iloc[:, 1].rename(stock_id))
                except Exception as e:
                    logger.warning(f"Failed to get data for {stock_id}: {e}")
                    continue

            if not factor_values_list:
                logger.error("No factor data available")
                return None, None

            # 合併成 DataFrame
            factor_data = pd.concat(factor_values_list, axis=1)
            close_data = pd.concat(close_prices_list, axis=1)

            # 計算未來收益（1 日報酬率）
            returns_data = close_data.pct_change(1).shift(-1)  # shift(-1) 表示未來報酬

            logger.info(f"Factor data shape: {factor_data.shape}, Returns data shape: {returns_data.shape}")

            return factor_data, returns_data

        except Exception as e:
            logger.error(f"Error calculating factor and returns: {e}")
            return None, None

    def _fallback_calculate(
        self,
        stock_list: List[str],
        start_date: str,
        end_date: str
    ) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """當 Qlib 不可用時的備用計算方法"""
        try:
            from app.services.finlab_client import FinLabClient
            client = FinLabClient()

            factor_values = {}
            returns_values = {}

            for stock_id in stock_list[:10]:  # 限制數量避免過載
                try:
                    df = client.get_ohlcv(stock_id, start_date, end_date)
                    if df is not None and not df.empty:
                        # 簡單動量因子作為示例
                        factor_values[stock_id] = df['close'].pct_change(20)  # 20 日報酬率
                        returns_values[stock_id] = df['close'].pct_change(1).shift(-1)
                except Exception as e:
                    logger.warning(f"Failed to get fallback data for {stock_id}: {e}")
                    continue

            if not factor_values:
                return None, None

            factor_data = pd.DataFrame(factor_values)
            returns_data = pd.DataFrame(returns_values)

            return factor_data, returns_data

        except Exception as e:
            logger.error(f"Fallback calculation failed: {e}")
            return None, None

    def _calculate_metrics(
        self,
        factor_data: pd.DataFrame,
        returns_data: pd.DataFrame
    ) -> Dict:
        """
        計算評估指標

        Returns:
            包含 IC, ICIR, Rank IC, Rank ICIR 的字典
        """
        try:
            # 確保兩個 DataFrame 對齊
            aligned_factor, aligned_returns = factor_data.align(returns_data, join='inner')

            # 計算每個時間點的截面 IC
            ic_series = []
            rank_ic_series = []

            for date in aligned_factor.index:
                factor_values = aligned_factor.loc[date].dropna()
                return_values = aligned_returns.loc[date].dropna()

                # 只保留兩者都有的股票
                common_stocks = factor_values.index.intersection(return_values.index)

                if len(common_stocks) < 5:  # 至少需要 5 支股票
                    continue

                f = factor_values[common_stocks]
                r = return_values[common_stocks]

                # Pearson IC
                ic = f.corr(r)
                if not np.isnan(ic):
                    ic_series.append(ic)

                # Rank IC (Spearman correlation)
                rank_ic = f.rank().corr(r.rank())
                if not np.isnan(rank_ic):
                    rank_ic_series.append(rank_ic)

            # 計算 IC 的均值和標準差
            if ic_series:
                mean_ic = np.mean(ic_series)
                std_ic = np.std(ic_series)
                icir = mean_ic / std_ic if std_ic > 0 else 0
            else:
                mean_ic = 0
                icir = 0

            if rank_ic_series:
                mean_rank_ic = np.mean(rank_ic_series)
                std_rank_ic = np.std(rank_ic_series)
                rank_icir = mean_rank_ic / std_rank_ic if std_rank_ic > 0 else 0
            else:
                mean_rank_ic = 0
                rank_icir = 0

            logger.info(f"Calculated metrics - IC: {mean_ic:.4f}, ICIR: {icir:.4f}, "
                       f"Rank IC: {mean_rank_ic:.4f}, Rank ICIR: {rank_icir:.4f}")

            return {
                "ic": float(mean_ic),
                "icir": float(icir),
                "rank_ic": float(mean_rank_ic),
                "rank_icir": float(rank_icir),
                "ic_time_series": [float(x) for x in ic_series] if ic_series else [],
            }

        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {
                "ic": 0.0,
                "icir": 0.0,
                "rank_ic": 0.0,
                "rank_icir": 0.0,
            }

    def _simple_backtest(
        self,
        factor_data: pd.DataFrame,
        returns_data: pd.DataFrame
    ) -> Dict:
        """
        簡單回測：基於因子排名的多空策略

        策略：
        - 買入因子值最高的 20% 股票
        - 賣出因子值最低的 20% 股票
        - 每日重平衡

        Returns:
            包含 sharpe_ratio, annual_return, max_drawdown, win_rate 的字典
        """
        try:
            # 確保數據對齊
            aligned_factor, aligned_returns = factor_data.align(returns_data, join='inner')

            # 計算每日組合收益
            daily_returns = []

            for date in aligned_factor.index:
                factor_values = aligned_factor.loc[date].dropna()
                return_values = aligned_returns.loc[date].dropna()

                # 只保留兩者都有的股票
                common_stocks = factor_values.index.intersection(return_values.index)

                if len(common_stocks) < 10:
                    continue

                # 根據因子排名
                ranked = factor_values[common_stocks].sort_values(ascending=False)

                # 前 20% 做多，後 20% 做空
                n_long = max(1, int(len(ranked) * 0.2))
                n_short = max(1, int(len(ranked) * 0.2))

                long_stocks = ranked.head(n_long).index
                short_stocks = ranked.tail(n_short).index

                # 計算組合收益（多頭權重 +1，空頭權重 -1）
                long_return = return_values[long_stocks].mean()
                short_return = return_values[short_stocks].mean()

                portfolio_return = (long_return - short_return) / 2  # 多空對沖

                if not np.isnan(portfolio_return):
                    daily_returns.append(portfolio_return)

            if not daily_returns:
                logger.warning("No valid daily returns for backtest")
                return {
                    "sharpe_ratio": 0.0,
                    "annual_return": 0.0,
                    "max_drawdown": 0.0,
                    "win_rate": 0.0,
                }

            # 轉換為 Series
            returns_series = pd.Series(daily_returns)

            # 計算指標
            sharpe_ratio = self._calculate_sharpe_ratio(returns_series)
            annual_return = self._calculate_annual_return(returns_series)
            max_drawdown = self._calculate_max_drawdown(returns_series)
            win_rate = (returns_series > 0).sum() / len(returns_series)

            logger.info(f"Backtest results - Sharpe: {sharpe_ratio:.4f}, "
                       f"Annual Return: {annual_return:.2%}, "
                       f"Max DD: {max_drawdown:.2%}, "
                       f"Win Rate: {win_rate:.2%}")

            return {
                "sharpe_ratio": float(sharpe_ratio),
                "annual_return": float(annual_return),
                "max_drawdown": float(max_drawdown),
                "win_rate": float(win_rate),
            }

        except Exception as e:
            logger.error(f"Error in simple backtest: {e}")
            return {
                "sharpe_ratio": 0.0,
                "annual_return": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
            }

    def _calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """計算 Sharpe Ratio"""
        if len(returns) == 0:
            return 0.0

        # 假設日收益率
        mean_return = returns.mean()
        std_return = returns.std()

        if std_return == 0:
            return 0.0

        # 年化（假設 252 交易日）
        annual_mean = mean_return * 252
        annual_std = std_return * np.sqrt(252)

        sharpe = (annual_mean - risk_free_rate) / annual_std
        return sharpe

    def _calculate_annual_return(self, returns: pd.Series) -> float:
        """計算年化報酬率"""
        if len(returns) == 0:
            return 0.0

        # 累積報酬率
        cumulative_return = (1 + returns).prod() - 1

        # 年化
        n_days = len(returns)
        n_years = n_days / 252

        if n_years <= 0:
            return 0.0

        annual_return = (1 + cumulative_return) ** (1 / n_years) - 1
        return annual_return

    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """計算最大回撤"""
        if len(returns) == 0:
            return 0.0

        # 計算累積淨值
        cumulative = (1 + returns).cumprod()

        # 計算回撤
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max

        max_dd = drawdown.min()
        return abs(max_dd)

    def _save_evaluation(self, factor_id: int, results: Dict):
        """保存評估結果到資料庫"""
        try:
            evaluation = FactorEvaluation(
                factor_id=factor_id,
                stock_pool=results.get("stock_pool"),
                start_date=results.get("start_date"),
                end_date=results.get("end_date"),
                ic=results.get("ic"),
                icir=results.get("icir"),
                rank_ic=results.get("rank_ic"),
                rank_icir=results.get("rank_icir"),
                sharpe_ratio=results.get("sharpe_ratio"),
                annual_return=results.get("annual_return"),
                max_drawdown=results.get("max_drawdown"),
                win_rate=results.get("win_rate"),
                detailed_results=results,
            )

            self.db.add(evaluation)
            self.db.commit()
            self.db.refresh(evaluation)

            logger.info(f"Saved evaluation {evaluation.id} for factor {factor_id}")

        except Exception as e:
            logger.error(f"Failed to save evaluation: {e}")
            self.db.rollback()
            raise

    def get_factor_evaluations(self, factor_id: int) -> List[FactorEvaluation]:
        """獲取因子的所有評估記錄"""
        return self.db.query(FactorEvaluation).filter(
            FactorEvaluation.factor_id == factor_id
        ).order_by(FactorEvaluation.created_at.desc()).all()

    def analyze_ic_decay(
        self,
        factor_id: int,
        stock_pool: str = "all",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_lag: int = 20
    ) -> Dict:
        """
        分析因子 IC 衰減

        計算因子在不同持有期（滯後期）下的 IC 值，觀察因子預測能力的衰減情況。

        Args:
            factor_id: 因子 ID
            stock_pool: 股票池（all, top100, etc.）
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
            max_lag: 最大滯後期（天數），預設 20

        Returns:
            IC 衰減分析結果：
            {
                "lags": [1, 3, 5, 10, 15, 20],
                "ic_values": [...],
                "rank_ic_values": [...],
                "factor_name": "因子名稱",
                "n_stocks": 股票數量,
                "n_periods": 時間段數量
            }
        """
        logger.info(f"Starting IC decay analysis for factor_id={factor_id}, max_lag={max_lag}")

        # 1. 獲取因子資訊
        factor = self.db.query(GeneratedFactor).filter(
            GeneratedFactor.id == factor_id
        ).first()

        if not factor:
            raise ValueError(f"Factor {factor_id} not found")

        # 2. 設定預設日期範圍（過去 2 年）
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_dt = datetime.now() - timedelta(days=730)  # 2 年
            start_date = start_dt.strftime("%Y-%m-%d")

        logger.info(f"Analyzing IC decay for factor '{factor.name}' from {start_date} to {end_date}")

        # 3. 檢查 Qlib 數據是否可用（IC 衰減分析必須使用本地數據）
        if not QLIB_AVAILABLE or not self.qlib_adapter.qlib_initialized:
            error_msg = (
                "IC 衰減分析需要本地 Qlib 數據。請先執行數據同步：\n"
                "1. 使用腳本：./scripts/sync-qlib-smart.sh\n"
                "2. 或手動同步：docker compose exec backend python /app/scripts/export_to_qlib_v2.py --output-dir /data/qlib/tw_stock_v2 --stocks all --smart"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # 4. 獲取股票池
        stock_list = self._get_stock_pool(stock_pool)
        logger.info(f"Stock pool: {len(stock_list)} stocks")

        # 4. 計算因子值
        factor_data, _ = self._calculate_factor_and_returns(
            factor.formula,
            stock_list,
            start_date,
            end_date
        )

        if factor_data is None:
            raise ValueError("Failed to calculate factor data")

        # 5. 定義滯後期（lag periods）
        lag_periods = [1, 3, 5, 10, 15, 20]
        if max_lag < 20:
            lag_periods = [lag for lag in lag_periods if lag <= max_lag]

        # 6. 計算每個滯後期的 IC
        ic_by_lag = []
        rank_ic_by_lag = []

        for lag in lag_periods:
            logger.info(f"Calculating IC for lag={lag}")

            # 計算該滯後期的未來收益
            returns_data = self._calculate_future_returns(stock_list, start_date, end_date, lag)

            if returns_data is None:
                logger.warning(f"Failed to calculate returns for lag={lag}, skipping")
                ic_by_lag.append(0.0)
                rank_ic_by_lag.append(0.0)
                continue

            # 計算該滯後期的 IC
            metrics = self._calculate_metrics(factor_data, returns_data)

            ic_by_lag.append(metrics.get("ic", 0.0))
            rank_ic_by_lag.append(metrics.get("rank_ic", 0.0))

        logger.info(f"IC decay analysis completed. IC values: {ic_by_lag}")

        return {
            "lags": lag_periods,
            "ic_values": ic_by_lag,
            "rank_ic_values": rank_ic_by_lag,
            "factor_name": factor.name,
            "n_stocks": len(stock_list),
            "n_periods": len(factor_data),
            "start_date": start_date,
            "end_date": end_date
        }

    def _calculate_future_returns(
        self,
        stock_list: List[str],
        start_date: str,
        end_date: str,
        lag: int = 1
    ) -> Optional[pd.DataFrame]:
        """
        計算未來 N 天的收益率

        Args:
            stock_list: 股票列表
            start_date: 開始日期
            end_date: 結束日期
            lag: 滯後期（天數）

        Returns:
            DataFrame，索引為日期，列為股票代碼，值為未來 N 天的收益率
        """
        try:
            # 檢查 Qlib 是否可用
            if not QLIB_AVAILABLE:
                raise ValueError("Qlib not available. Please install Qlib and sync data.")

            # 使用 Qlib 獲取價格數據（僅使用本地數據，不使用 API fallback）
            instruments = [f"SH{s}" if s.startswith('6') else f"SZ{s}" for s in stock_list]

            # 獲取收盤價
            close_prices = D.features(
                instruments=instruments,
                fields=['$close'],
                start_time=start_date,
                end_time=end_date
            )

            if close_prices is None or close_prices.empty:
                error_msg = (
                    f"無法獲取 lag={lag} 天的價格數據。本地 Qlib 數據可能不完整或不存在。\n"
                    "請執行數據同步：./scripts/sync-qlib-smart.sh"
                )
                logger.warning(error_msg)
                raise ValueError(error_msg)

            # 重塑數據：轉換為 (date, stock) 的透視表
            close_prices = close_prices.reset_index()
            close_prices['stock'] = close_prices['instrument'].str[2:]  # 移除 SH/SZ 前綴

            pivot_df = close_prices.pivot_table(
                index='datetime',
                columns='stock',
                values='$close'
            )

            # 計算未來 N 天的收益率：(close[t+N] - close[t]) / close[t]
            returns_df = (pivot_df.shift(-lag) - pivot_df) / pivot_df

            # 移除 NaN（最後 N 天沒有未來收益）
            returns_df = returns_df.dropna(how='all')

            logger.info(f"Calculated {lag}-day forward returns: shape={returns_df.shape}")

            return returns_df

        except Exception as e:
            logger.error(f"Error calculating future returns for lag={lag}: {e}")
            return None
