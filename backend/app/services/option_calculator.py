"""
Option Factor Calculator

選擇權因子計算器，支援三階段演進式架構：
- 階段一：基礎因子（PCR、ATM IV）
- 階段二：進階因子（IV Skew、Max Pain）
- 階段三：Greeks 摘要

設計原則：
1. 版本化計算（確保可複現）
2. 階段控制（根據配置動態啟用功能）
3. 資料品質評估
"""

from typing import Dict, Optional, Any
from datetime import date
from decimal import Decimal
import pandas as pd
import numpy as np
from loguru import logger
from sqlalchemy.orm import Session

from app.services.option_data_source import OptionDataSource
from app.repositories.option import OptionSyncConfigRepository


class OptionFactorCalculator:
    """選擇權因子計算器"""

    VERSION = "1.0.0"  # 計算版本

    def __init__(
        self,
        data_source: OptionDataSource,
        db: Optional[Session] = None
    ):
        """
        初始化計算器

        Args:
            data_source: 資料源（如 ShioajiOptionDataSource）
            db: 資料庫 Session（用於讀取配置）
        """
        self.data_source = data_source
        self.db = db

    def calculate_daily_factors(
        self,
        underlying_id: str,
        date: date
    ) -> Dict[str, Any]:
        """
        計算每日因子（支援多階段）

        階段一：只計算 pcr_volume, pcr_oi, atm_iv
        階段二：額外計算 iv_skew, max_pain
        階段三：額外計算 Greeks 摘要

        Args:
            underlying_id: 標的代碼（如 'TX', 'MTX'）
            date: 資料日期

        Returns:
            字典包含所有階段的因子（未啟用階段的因子為 None）
        """
        try:
            stage = self._get_current_stage()
            logger.info(
                f"[OPTION] 📊 Starting factor calculation: {underlying_id} | "
                f"Date: {date} | Stage: {stage}"
            )

            factors = {}

            # 獲取選擇權鏈數據
            try:
                option_chain = self.data_source.get_option_chain(underlying_id, date)
            except Exception as e:
                logger.error(
                    f"[OPTION] ❌ Failed to fetch option chain for {underlying_id}: "
                    f"{type(e).__name__}: {str(e)}",
                    exc_info=True
                )
                return self._empty_factors()

            if option_chain.empty:
                logger.warning(
                    f"[OPTION] ⚠️  No option chain data for {underlying_id} on {date}. "
                    f"This may indicate non-trading day or data sync issue."
                )
                return self._empty_factors()

            logger.debug(
                f"[OPTION] Retrieved {len(option_chain)} option contracts. "
                f"Columns: {list(option_chain.columns)}"
            )

            # 階段一：基礎因子（必算）
            logger.debug(f"[OPTION] Calculating Stage 1 factors (PCR, ATM IV)...")
            factors.update(self._calculate_pcr(option_chain))
            factors.update(self._calculate_atm_iv(option_chain))

            # 階段二：進階因子（條件計算）
            if stage >= 2:
                logger.debug(f"[OPTION] Calculating Stage 2 factors (IV Skew, Max Pain)...")
                factors.update(self._calculate_iv_skew(option_chain))
                factors.update(self._calculate_max_pain(option_chain))

            # 階段三：Greeks 摘要（條件計算）
            if stage >= 3:
                logger.debug(f"[OPTION] Calculating Stage 3 factors (Greeks)...")
                factors.update(self._calculate_greeks_summary(option_chain))

            # 記錄計算版本和品質評分
            factors['calculation_version'] = self.VERSION
            factors['data_quality_score'] = self._assess_quality(factors, option_chain)

            # 計算成功的因子數量
            calculated_factors = [k for k, v in factors.items()
                                  if v is not None and k not in ['calculation_version', 'data_quality_score']]

            logger.info(
                f"[OPTION] ✅ Factor calculation completed: {underlying_id} | "
                f"Calculated: {len(calculated_factors)}/{len([k for k in factors.keys() if k not in ['calculation_version', 'data_quality_score']])} factors | "
                f"Quality: {factors.get('data_quality_score', 'N/A')}"
            )

            # 詳細因子結果
            factor_summary = ", ".join([
                f"{k}={v}" for k, v in sorted(factors.items())
                if k not in ['calculation_version', 'data_quality_score'] and v is not None
            ])
            if factor_summary:
                logger.debug(f"[OPTION] Factor values: {factor_summary}")

            return factors

        except Exception as e:
            logger.error(
                f"[OPTION] ❌ Unexpected error in calculate_daily_factors for {underlying_id}: "
                f"{type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return self._empty_factors()

    def _calculate_pcr(self, option_chain: pd.DataFrame) -> Dict[str, Optional[Decimal]]:
        """
        計算 Put/Call Ratio（階段一）

        PCR = Put 成交量 / Call 成交量
        PCR OI = Put 未平倉量 / Call 未平倉量

        Args:
            option_chain: 選擇權鏈 DataFrame

        Returns:
            {'pcr_volume': Decimal, 'pcr_open_interest': Decimal}
        """
        try:
            # 數據驗證
            if 'option_type' not in option_chain.columns:
                logger.error("[OPTION] PCR calculation failed: missing 'option_type' column")
                return {'pcr_volume': None, 'pcr_open_interest': None}

            if 'volume' not in option_chain.columns:
                logger.error("[OPTION] PCR calculation failed: missing 'volume' column")
                return {'pcr_volume': None, 'pcr_open_interest': None}

            # 分離 Call 和 Put
            calls = option_chain[option_chain['option_type'] == 'CALL']
            puts = option_chain[option_chain['option_type'] == 'PUT']

            logger.debug(
                f"[OPTION] PCR calculation: {len(calls)} CALL contracts, {len(puts)} PUT contracts"
            )

            # 計算成交量 PCR
            call_volume = calls['volume'].sum()
            put_volume = puts['volume'].sum()

            logger.debug(
                f"[OPTION] Volumes: CALL={call_volume}, PUT={put_volume}"
            )

            if call_volume > 0:
                pcr_volume = Decimal(str(put_volume / call_volume))

                # 異常值警告
                if pcr_volume < Decimal('0.3') or pcr_volume > Decimal('3.0'):
                    logger.warning(
                        f"[OPTION] ⚠️  Unusual PCR Volume detected: {pcr_volume}. "
                        f"Expected range: 0.3-3.0. Please verify data quality."
                    )
            else:
                pcr_volume = None
                logger.warning(
                    f"[OPTION] Call volume is zero (PUT volume: {put_volume}), "
                    f"cannot calculate PCR volume. Possible data quality issue."
                )

            # 計算未平倉量 PCR
            call_oi = calls['open_interest'].sum() if 'open_interest' in calls.columns else 0
            put_oi = puts['open_interest'].sum() if 'open_interest' in puts.columns else 0

            if 'open_interest' in option_chain.columns:
                logger.debug(
                    f"[OPTION] Open Interest: CALL={call_oi}, PUT={put_oi}"
                )

            if call_oi > 0:
                pcr_open_interest = Decimal(str(put_oi / call_oi))

                # 異常值警告
                if pcr_open_interest < Decimal('0.3') or pcr_open_interest > Decimal('3.0'):
                    logger.warning(
                        f"[OPTION] ⚠️  Unusual PCR OI detected: {pcr_open_interest}. "
                        f"Expected range: 0.3-3.0."
                    )
            else:
                pcr_open_interest = None
                if 'open_interest' in option_chain.columns:
                    logger.warning(
                        f"[OPTION] Call OI is zero (PUT OI: {put_oi}), "
                        f"cannot calculate PCR OI"
                    )

            logger.info(
                f"[OPTION] ✅ PCR calculated - Volume: {pcr_volume}, OI: {pcr_open_interest}"
            )

            return {
                'pcr_volume': pcr_volume,
                'pcr_open_interest': pcr_open_interest
            }

        except KeyError as e:
            logger.error(
                f"[OPTION] ❌ PCR calculation failed: missing column {str(e)}. "
                f"Available columns: {list(option_chain.columns)}"
            )
            return {'pcr_volume': None, 'pcr_open_interest': None}
        except Exception as e:
            logger.error(
                f"[OPTION] ❌ Unexpected error in PCR calculation: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return {'pcr_volume': None, 'pcr_open_interest': None}

    def _calculate_atm_iv(self, option_chain: pd.DataFrame) -> Dict[str, Optional[Decimal]]:
        """
        計算 ATM 隱含波動率（階段一簡化版）

        階段一：使用近月合約的價平選擇權價格推估
        階段三：使用 Black-Scholes 模型計算精確 IV

        Args:
            option_chain: 選擇權鏈 DataFrame

        Returns:
            {'atm_iv': Decimal}
        """
        try:
            # 階段一簡化實作：使用價格/履約價比值作為 IV 代理指標
            # 注意：這不是真正的隱含波動率，僅用於階段一驗證

            # 數據驗證
            if 'close' not in option_chain.columns:
                logger.error("[OPTION] ATM IV calculation failed: missing 'close' column")
                return {'atm_iv': None}

            if option_chain['close'].isnull().all():
                logger.warning(
                    "[OPTION] ATM IV calculation skipped: all close prices are null. "
                    "This may indicate non-trading hours or data sync issue."
                )
                return {'atm_iv': None}

            if 'option_type' not in option_chain.columns:
                logger.error("[OPTION] ATM IV calculation failed: missing 'option_type' column")
                return {'atm_iv': None}

            if 'volume' not in option_chain.columns:
                logger.warning("[OPTION] Missing 'volume' column, using first CALL contract")

            # 找出價平合約（履約價最接近標的價格）
            # 簡化方法：假設成交量最大的合約接近 ATM
            calls = option_chain[option_chain['option_type'] == 'CALL']

            if calls.empty:
                logger.warning("[OPTION] No CALL contracts found for ATM IV calculation")
                return {'atm_iv': None}

            # 過濾有效價格的合約
            valid_calls = calls[calls['close'].notna() & (calls['close'] > 0)]

            if valid_calls.empty:
                logger.warning(
                    f"[OPTION] No valid CALL prices found. "
                    f"Total CALL contracts: {len(calls)}, with valid prices: 0"
                )
                return {'atm_iv': None}

            # 找出成交量最大的 Call（通常接近 ATM）
            if 'volume' in valid_calls.columns and valid_calls['volume'].sum() > 0:
                atm_call = valid_calls.loc[valid_calls['volume'].idxmax()]
                logger.debug(
                    f"[OPTION] Selected ATM contract by volume: "
                    f"Strike={atm_call['strike_price']}, Volume={atm_call['volume']}"
                )
            else:
                # 備用方法：使用第一個有效合約
                atm_call = valid_calls.iloc[0]
                logger.debug(
                    f"[OPTION] Selected first valid contract: Strike={atm_call['strike_price']}"
                )

            # 簡化 IV 計算（階段一）
            # IV ≈ (Option Price / Strike Price) * 100
            # 注意：這是粗略估計，階段三將使用 Black-Scholes 精確計算
            strike_price = float(atm_call['strike_price'])
            option_price = float(atm_call['close'])

            if strike_price <= 0:
                logger.error(
                    f"[OPTION] Invalid strike price: {strike_price}. Cannot calculate ATM IV."
                )
                return {'atm_iv': None}

            atm_iv_estimate = Decimal(str((option_price / strike_price) * 100))

            # 合理性檢查：IV 通常在 5% - 100% 之間
            if atm_iv_estimate < 0:
                logger.error(
                    f"[OPTION] ❌ Negative ATM IV detected: {atm_iv_estimate}. "
                    f"Option price: {option_price}, Strike: {strike_price}"
                )
                return {'atm_iv': None}

            if atm_iv_estimate > 100:
                logger.warning(
                    f"[OPTION] ⚠️  Unusually high ATM IV: {atm_iv_estimate}% (>100%). "
                    f"Option price: {option_price}, Strike: {strike_price}. "
                    f"This may indicate deep ITM option or data quality issue."
                )
                # 仍然返回值，但記錄警告
                # return {'atm_iv': None}

            if atm_iv_estimate < 5:
                logger.warning(
                    f"[OPTION] ⚠️  Unusually low ATM IV: {atm_iv_estimate}% (<5%). "
                    f"This may indicate deep OTM option or low volatility period."
                )

            logger.info(f"[OPTION] ✅ ATM IV calculated: {atm_iv_estimate}%")
            return {'atm_iv': atm_iv_estimate}

        except KeyError as e:
            logger.error(
                f"[OPTION] ❌ ATM IV calculation failed: missing field {str(e)}. "
                f"Available columns: {list(option_chain.columns)}"
            )
            return {'atm_iv': None}
        except Exception as e:
            logger.error(
                f"[OPTION] ❌ Unexpected error in ATM IV calculation: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return {'atm_iv': None}

    def _calculate_iv_skew(self, option_chain: pd.DataFrame) -> Dict[str, Optional[Decimal]]:
        """
        計算 IV Skew（階段二）

        IV Skew = OTM Put IV - ATM IV

        Args:
            option_chain: 選擇權鏈 DataFrame

        Returns:
            {'iv_skew': Decimal}
        """
        logger.debug("[OPTION] IV Skew calculation not implemented in Stage 1")
        return {'iv_skew': None}

    def _calculate_max_pain(self, option_chain: pd.DataFrame) -> Dict[str, Optional[Decimal]]:
        """
        計算 Max Pain 履約價（階段二）

        Max Pain = 履約時造成選擇權賣方最大損失的履約價

        Args:
            option_chain: 選擇權鏈 DataFrame

        Returns:
            {
                'max_pain_strike': Decimal,
                'total_call_oi': int,
                'total_put_oi': int
            }
        """
        logger.debug("[OPTION] Max Pain calculation not implemented in Stage 1")
        return {
            'max_pain_strike': None,
            'total_call_oi': None,
            'total_put_oi': None
        }

    def _calculate_greeks_summary(self, option_chain: pd.DataFrame) -> Dict[str, Optional[Decimal]]:
        """
        計算 Greeks 摘要（階段三）

        Args:
            option_chain: 選擇權鏈 DataFrame

        Returns:
            {
                'avg_call_delta': Decimal,
                'avg_put_delta': Decimal,
                'gamma_exposure': Decimal,
                'vanna_exposure': Decimal
            }
        """
        try:
            from app.services.greeks_calculator import (
                BlackScholesGreeksCalculator,
                calculate_time_to_expiry
            )

            # 驗證必要欄位
            required_fields = ['option_type', 'strike_price', 'expiry_date', 'close']
            missing_fields = [f for f in required_fields if f not in option_chain.columns]
            if missing_fields:
                logger.error(
                    f"[GREEKS] Missing required fields: {missing_fields}. "
                    f"Available: {list(option_chain.columns)}"
                )
                return {
                    'avg_call_delta': None,
                    'avg_put_delta': None,
                    'gamma_exposure': None,
                    'vanna_exposure': None
                }

            # 過濾有效數據
            valid_data = option_chain[
                option_chain['close'].notna() &
                (option_chain['close'] > 0) &
                option_chain['strike_price'].notna() &
                option_chain['expiry_date'].notna()
            ].copy()

            if valid_data.empty:
                logger.warning("[GREEKS] No valid option data for Greeks calculation")
                return {
                    'avg_call_delta': None,
                    'avg_put_delta': None,
                    'gamma_exposure': None,
                    'vanna_exposure': None
                }

            # 獲取標的現價（使用 ATM Call 的 strike 作為近似）
            if 'volume' in valid_data.columns:
                calls = valid_data[valid_data['option_type'] == 'CALL']
                if not calls.empty and calls['volume'].sum() > 0:
                    atm_call = calls.loc[calls['volume'].idxmax()]
                    spot_price = float(atm_call['strike_price'])
                else:
                    spot_price = float(valid_data['strike_price'].median())
            else:
                spot_price = float(valid_data['strike_price'].median())

            logger.debug(f"[GREEKS] Estimated spot price: {spot_price}")

            # 初始化計算器
            calculator = BlackScholesGreeksCalculator()

            # 計算當前日期
            current_date = date.today()

            # 儲存 Greeks 計算結果
            call_deltas = []
            put_deltas = []
            gamma_exposures = []
            vanna_exposures = []

            # 逐個合約計算 Greeks
            for _, row in valid_data.iterrows():
                try:
                    strike_price = float(row['strike_price'])
                    expiry_date = row['expiry_date']
                    option_type = row['option_type']
                    option_price = float(row['close'])

                    # 計算到期時間
                    time_to_expiry = calculate_time_to_expiry(expiry_date, current_date)
                    if time_to_expiry <= 0:
                        continue

                    # 估算隱含波動率（使用簡化方法）
                    volatility = (option_price / strike_price) * np.sqrt(2 * np.pi / time_to_expiry)
                    volatility = max(0.05, min(volatility, 1.0))  # 限制在 5%-100%

                    # 計算 Greeks
                    greeks = calculator.calculate_greeks(
                        spot_price=spot_price,
                        strike_price=strike_price,
                        time_to_expiry=time_to_expiry,
                        volatility=volatility,
                        option_type=option_type
                    )

                    if greeks['delta'] is not None:
                        if option_type == 'CALL':
                            call_deltas.append(greeks['delta'])
                        else:
                            put_deltas.append(greeks['delta'])

                    if greeks['gamma'] is not None:
                        # Gamma Exposure = Gamma × Open Interest × Contract Size
                        open_interest = float(row.get('open_interest', 0))
                        gamma_exposure = greeks['gamma'] * open_interest * spot_price
                        gamma_exposures.append(gamma_exposure)

                    if greeks['vanna'] is not None:
                        open_interest = float(row.get('open_interest', 0))
                        vanna_exposure = greeks['vanna'] * open_interest
                        vanna_exposures.append(vanna_exposure)

                except Exception as e:
                    logger.debug(
                        f"[GREEKS] Failed to calculate Greeks for contract: {str(e)}"
                    )
                    continue

            # 計算摘要統計
            avg_call_delta = Decimal(str(np.mean(call_deltas))) if call_deltas else None
            avg_put_delta = Decimal(str(np.mean(put_deltas))) if put_deltas else None
            gamma_exposure = Decimal(str(np.sum(gamma_exposures))) if gamma_exposures else None
            vanna_exposure = Decimal(str(np.sum(vanna_exposures))) if vanna_exposures else None

            logger.info(
                f"[GREEKS] ✅ Greeks summary calculated: "
                f"avg_call_delta={avg_call_delta}, avg_put_delta={avg_put_delta}, "
                f"gamma_exp={gamma_exposure}, vanna_exp={vanna_exposure}"
            )

            return {
                'avg_call_delta': avg_call_delta,
                'avg_put_delta': avg_put_delta,
                'gamma_exposure': gamma_exposure,
                'vanna_exposure': vanna_exposure
            }

        except ImportError as e:
            logger.error(f"[GREEKS] Failed to import Greeks calculator: {str(e)}")
            return {
                'avg_call_delta': None,
                'avg_put_delta': None,
                'gamma_exposure': None,
                'vanna_exposure': None
            }
        except Exception as e:
            logger.error(
                f"[GREEKS] Unexpected error in Greeks summary: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return {
                'avg_call_delta': None,
                'avg_put_delta': None,
                'gamma_exposure': None,
                'vanna_exposure': None
            }

    def _assess_quality(
        self,
        factors: Dict[str, Any],
        option_chain: pd.DataFrame
    ) -> Optional[Decimal]:
        """
        評估資料品質評分（0-1）

        評估指標：
        1. 因子計算成功率
        2. 資料完整性（有多少合約有價格）
        3. 異常值檢測

        Args:
            factors: 已計算的因子
            option_chain: 原始選擇權鏈數據

        Returns:
            品質評分（0-1）
        """
        try:
            scores = []

            # 指標 1：階段一因子計算成功率
            stage1_factors = ['pcr_volume', 'pcr_open_interest', 'atm_iv']
            calculated = sum(1 for f in stage1_factors if factors.get(f) is not None)
            total = len(stage1_factors)
            scores.append(calculated / total)

            # 指標 2：資料完整性
            if not option_chain.empty and 'close' in option_chain.columns:
                valid_prices = option_chain['close'].notna().sum()
                total_contracts = len(option_chain)
                scores.append(valid_prices / total_contracts if total_contracts > 0 else 0)

            # 指標 3：異常值檢測（PCR 應在合理範圍）
            pcr = factors.get('pcr_volume')
            if pcr is not None:
                # PCR 通常在 0.5 - 2.0 之間
                if 0.3 <= float(pcr) <= 3.0:
                    scores.append(1.0)
                else:
                    scores.append(0.5)  # 部分異常
            else:
                scores.append(0.0)

            # 計算平均分數
            quality_score = Decimal(str(np.mean(scores)))
            logger.debug(f"[OPTION] Data quality score: {quality_score}")

            return quality_score

        except Exception as e:
            logger.error(f"[OPTION] Error assessing quality: {str(e)}")
            return None

    def _empty_factors(self) -> Dict[str, Any]:
        """返回空因子字典"""
        return {
            # 階段一
            'pcr_volume': None,
            'pcr_open_interest': None,
            'atm_iv': None,
            # 階段二
            'iv_skew': None,
            'iv_term_structure': None,
            'max_pain_strike': None,
            'total_call_oi': None,
            'total_put_oi': None,
            # 階段三
            'avg_call_delta': None,
            'avg_put_delta': None,
            'gamma_exposure': None,
            'vanna_exposure': None,
            # 元數據
            'calculation_version': self.VERSION,
            'data_quality_score': Decimal('0.0')
        }

    def _get_current_stage(self) -> int:
        """
        獲取當前階段

        Returns:
            階段號（1/2/3）
        """
        if self.db:
            try:
                stage = OptionSyncConfigRepository.get_current_stage(self.db)
                return stage
            except Exception as e:
                logger.warning(f"[OPTION] Failed to get stage from config: {str(e)}")

        # 默認階段一
        return 1


# ============ 因子註冊表 ============

OPTION_FACTOR_REGISTRY = {
    # 階段一因子
    'pcr_volume': {
        'stage': 1,
        'qlib_field': '$pcr',
        'description': 'Put/Call Ratio (成交量)',
        'dependencies': ['volume'],
    },
    'pcr_open_interest': {
        'stage': 1,
        'qlib_field': '$pcr_oi',
        'description': 'Put/Call Ratio (未平倉量)',
        'dependencies': ['open_interest'],
    },
    'atm_iv': {
        'stage': 1,
        'qlib_field': '$atm_iv',
        'description': 'ATM 隱含波動率',
        'dependencies': ['close', 'strike_price'],
    },

    # 階段二因子
    'iv_skew': {
        'stage': 2,
        'qlib_field': '$iv_skew',
        'description': 'IV Skew (25 Delta)',
        'dependencies': ['atm_iv', 'otm_iv'],
    },
    'max_pain_strike': {
        'stage': 2,
        'qlib_field': '$max_pain',
        'description': 'Max Pain 履約價',
        'dependencies': ['open_interest', 'strike_price'],
    },

    # 階段三因子
    'gamma_exposure': {
        'stage': 3,
        'qlib_field': '$gamma_exp',
        'description': 'Gamma 總曝險',
        'dependencies': ['gamma', 'open_interest'],
    },
}


def get_available_factors(stage: int) -> list:
    """
    獲取當前階段可用的因子

    Args:
        stage: 階段號（1/2/3）

    Returns:
        因子名稱列表
    """
    return [
        name for name, config in OPTION_FACTOR_REGISTRY.items()
        if config['stage'] <= stage
    ]
