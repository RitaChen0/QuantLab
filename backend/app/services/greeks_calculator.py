"""
Black-Scholes Greeks Calculator

使用 Black-Scholes 模型計算選擇權 Greeks
支援：Delta, Gamma, Theta, Vega, Rho, Vanna
"""

import numpy as np
from scipy.stats import norm
from decimal import Decimal
from typing import Dict, Optional
from datetime import date, datetime
from loguru import logger


class BlackScholesGreeksCalculator:
    """Black-Scholes Greeks 計算器"""

    def __init__(self, risk_free_rate: float = 0.01):
        """
        初始化計算器

        Args:
            risk_free_rate: 無風險利率（年化，預設 1%）
        """
        self.risk_free_rate = risk_free_rate

    def calculate_greeks(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        volatility: float,
        option_type: str = "CALL"
    ) -> Dict[str, Optional[float]]:
        """
        計算選擇權 Greeks

        Args:
            spot_price: 標的現價
            strike_price: 履約價
            time_to_expiry: 到期時間（年）
            volatility: 波動率（年化）
            option_type: 選擇權類型（CALL/PUT）

        Returns:
            Greeks 字典 {delta, gamma, theta, vega, rho, vanna}
        """
        try:
            # 輸入驗證
            if spot_price <= 0 or strike_price <= 0:
                logger.error(
                    f"[GREEKS] Invalid prices: spot={spot_price}, strike={strike_price}"
                )
                return self._empty_greeks()

            if time_to_expiry <= 0:
                logger.warning(
                    f"[GREEKS] Option expired (time_to_expiry={time_to_expiry})"
                )
                return self._empty_greeks()

            if volatility <= 0:
                logger.error(f"[GREEKS] Invalid volatility: {volatility}")
                return self._empty_greeks()

            # 計算 d1 和 d2
            d1 = self._calculate_d1(
                spot_price, strike_price, time_to_expiry, volatility
            )
            d2 = d1 - volatility * np.sqrt(time_to_expiry)

            # 計算 Greeks
            greeks = {
                'delta': self._calculate_delta(d1, option_type),
                'gamma': self._calculate_gamma(spot_price, d1, time_to_expiry, volatility),
                'theta': self._calculate_theta(
                    spot_price, strike_price, d1, d2, time_to_expiry, volatility, option_type
                ),
                'vega': self._calculate_vega(spot_price, d1, time_to_expiry),
                'rho': self._calculate_rho(strike_price, d2, time_to_expiry, option_type),
                'vanna': self._calculate_vanna(spot_price, d1, d2, time_to_expiry, volatility)
            }

            logger.debug(
                f"[GREEKS] Calculated: delta={greeks['delta']:.4f}, "
                f"gamma={greeks['gamma']:.6f}, vega={greeks['vega']:.4f}"
            )

            return greeks

        except Exception as e:
            logger.error(
                f"[GREEKS] Calculation failed: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return self._empty_greeks()

    def _calculate_d1(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        volatility: float
    ) -> float:
        """
        計算 Black-Scholes d1

        d1 = [ln(S/K) + (r + σ²/2)T] / (σ√T)
        """
        numerator = (
            np.log(spot_price / strike_price) +
            (self.risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry
        )
        denominator = volatility * np.sqrt(time_to_expiry)
        return numerator / denominator

    def _calculate_delta(self, d1: float, option_type: str) -> float:
        """
        計算 Delta

        Call Delta = N(d1)
        Put Delta = N(d1) - 1
        """
        call_delta = norm.cdf(d1)
        if option_type == "CALL":
            return call_delta
        else:  # PUT
            return call_delta - 1

    def _calculate_gamma(
        self,
        spot_price: float,
        d1: float,
        time_to_expiry: float,
        volatility: float
    ) -> float:
        """
        計算 Gamma

        Gamma = φ(d1) / (S * σ * √T)
        其中 φ(x) 是標準常態分佈的機率密度函數
        """
        pdf_d1 = norm.pdf(d1)
        denominator = spot_price * volatility * np.sqrt(time_to_expiry)
        return pdf_d1 / denominator

    def _calculate_theta(
        self,
        spot_price: float,
        strike_price: float,
        d1: float,
        d2: float,
        time_to_expiry: float,
        volatility: float,
        option_type: str
    ) -> float:
        """
        計算 Theta（每日時間衰減）

        Call Theta = -[S*φ(d1)*σ/(2√T)] - r*K*e^(-rT)*N(d2)
        Put Theta = -[S*φ(d1)*σ/(2√T)] + r*K*e^(-rT)*N(-d2)

        注意：返回每日 Theta（除以 365）
        """
        pdf_d1 = norm.pdf(d1)
        sqrt_t = np.sqrt(time_to_expiry)

        # 第一項（對 Call 和 Put 相同）
        term1 = -(spot_price * pdf_d1 * volatility) / (2 * sqrt_t)

        # 第二項（Call 和 Put 符號不同）
        discount_factor = np.exp(-self.risk_free_rate * time_to_expiry)
        if option_type == "CALL":
            term2 = -self.risk_free_rate * strike_price * discount_factor * norm.cdf(d2)
        else:  # PUT
            term2 = self.risk_free_rate * strike_price * discount_factor * norm.cdf(-d2)

        # 年化 Theta 轉為每日
        annual_theta = term1 + term2
        daily_theta = annual_theta / 365.0

        return daily_theta

    def _calculate_vega(
        self,
        spot_price: float,
        d1: float,
        time_to_expiry: float
    ) -> float:
        """
        計算 Vega

        Vega = S * φ(d1) * √T

        注意：返回對 1% 波動率變化的敏感度（除以 100）
        """
        pdf_d1 = norm.pdf(d1)
        sqrt_t = np.sqrt(time_to_expiry)
        vega = spot_price * pdf_d1 * sqrt_t
        # 轉為對 1% 波動率變化的敏感度
        return vega / 100.0

    def _calculate_rho(
        self,
        strike_price: float,
        d2: float,
        time_to_expiry: float,
        option_type: str
    ) -> float:
        """
        計算 Rho

        Call Rho = K * T * e^(-rT) * N(d2)
        Put Rho = -K * T * e^(-rT) * N(-d2)

        注意：返回對 1% 利率變化的敏感度（除以 100）
        """
        discount_factor = np.exp(-self.risk_free_rate * time_to_expiry)
        if option_type == "CALL":
            rho = strike_price * time_to_expiry * discount_factor * norm.cdf(d2)
        else:  # PUT
            rho = -strike_price * time_to_expiry * discount_factor * norm.cdf(-d2)

        # 轉為對 1% 利率變化的敏感度
        return rho / 100.0

    def _calculate_vanna(
        self,
        spot_price: float,
        d1: float,
        d2: float,
        time_to_expiry: float,
        volatility: float
    ) -> float:
        """
        計算 Vanna（二階 Greek）

        Vanna = ∂Delta/∂σ = -φ(d1) * d2 / σ
        """
        pdf_d1 = norm.pdf(d1)
        vanna = -(pdf_d1 * d2) / volatility
        return vanna

    def _empty_greeks(self) -> Dict[str, Optional[float]]:
        """返回空 Greeks 字典"""
        return {
            'delta': None,
            'gamma': None,
            'theta': None,
            'vega': None,
            'rho': None,
            'vanna': None
        }


def calculate_time_to_expiry(expiry_date: date, current_date: date) -> float:
    """
    計算到期時間（年）

    Args:
        expiry_date: 到期日
        current_date: 當前日期

    Returns:
        到期時間（年）
    """
    days_to_expiry = (expiry_date - current_date).days
    if days_to_expiry <= 0:
        return 0.0
    return days_to_expiry / 365.0


def estimate_volatility_from_option_prices(
    spot_price: float,
    strike_price: float,
    option_price: float,
    time_to_expiry: float,
    option_type: str = "CALL",
    risk_free_rate: float = 0.01,
    max_iterations: int = 100,
    tolerance: float = 0.0001
) -> Optional[float]:
    """
    使用 Newton-Raphson 方法從選擇權價格反推隱含波動率

    Args:
        spot_price: 標的現價
        strike_price: 履約價
        option_price: 選擇權市價
        time_to_expiry: 到期時間（年）
        option_type: 選擇權類型
        risk_free_rate: 無風險利率
        max_iterations: 最大迭代次數
        tolerance: 收斂容忍度

    Returns:
        隱含波動率（如果收斂）或 None
    """
    try:
        from scipy.optimize import newton

        def black_scholes_price(volatility):
            """Black-Scholes 定價公式"""
            if volatility <= 0:
                return float('inf')

            d1 = (np.log(spot_price / strike_price) +
                  (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry) / \
                 (volatility * np.sqrt(time_to_expiry))
            d2 = d1 - volatility * np.sqrt(time_to_expiry)

            if option_type == "CALL":
                price = (spot_price * norm.cdf(d1) -
                        strike_price * np.exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2))
            else:  # PUT
                price = (strike_price * np.exp(-risk_free_rate * time_to_expiry) * norm.cdf(-d2) -
                        spot_price * norm.cdf(-d1))

            return price

        def objective(volatility):
            """目標函數：理論價格 - 市價"""
            return black_scholes_price(volatility) - option_price

        # 初始猜測：使用 ATM 近似公式
        initial_guess = option_price / (spot_price * np.sqrt(time_to_expiry / (2 * np.pi)))
        initial_guess = max(0.01, min(initial_guess, 2.0))  # 限制在 1%-200%

        # Newton-Raphson 求解
        implied_vol = newton(
            objective,
            initial_guess,
            maxiter=max_iterations,
            tol=tolerance
        )

        # 合理性檢查
        if 0.01 <= implied_vol <= 2.0:
            return implied_vol
        else:
            logger.warning(
                f"[GREEKS] Implied volatility out of range: {implied_vol:.4f}"
            )
            return None

    except Exception as e:
        logger.debug(
            f"[GREEKS] IV calculation failed: {type(e).__name__}: {str(e)}"
        )
        return None
