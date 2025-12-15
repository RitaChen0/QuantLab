"""
Option-related Pydantic schemas for request/response validation

支援三階段演進式架構：
- 階段一：基礎因子（PCR, ATM IV）
- 階段二：進階因子（IV Skew, Max Pain）
- 階段三：Greeks 摘要
"""

from __future__ import annotations

from typing import Optional, List, Dict
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


# ============ OptionContract Schemas ============

class OptionContractBase(BaseModel):
    """Base option contract schema with common fields"""
    contract_id: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="合約代碼（如 TXO202512C23000）"
    )
    underlying_id: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="標的物代碼（如 TX202512、2330）"
    )
    underlying_type: str = Field(
        ...,
        pattern="^(STOCK|FUTURES)$",
        description="標的物類型（STOCK/FUTURES）"
    )
    option_type: str = Field(
        ...,
        pattern="^(CALL|PUT)$",
        description="選擇權類型（CALL/PUT）"
    )
    strike_price: Decimal = Field(
        ...,
        ge=0,
        description="履約價格"
    )
    expiry_date: date = Field(
        ...,
        description="到期日"
    )


class OptionContractCreate(OptionContractBase):
    """Schema for creating a new option contract"""
    is_active: str = Field(
        default='active',
        pattern="^(active|expired|exercised)$",
        description="狀態"
    )
    contract_size: Optional[int] = Field(
        default=1,
        ge=1,
        description="合約乘數"
    )
    tick_size: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="最小跳動單位"
    )


class OptionContractUpdate(BaseModel):
    """Schema for updating option contract"""
    is_active: Optional[str] = Field(
        None,
        pattern="^(active|expired|exercised)$"
    )
    settlement_price: Optional[Decimal] = Field(None, ge=0)
    contract_size: Optional[int] = Field(None, ge=1)
    tick_size: Optional[Decimal] = Field(None, ge=0)


class OptionContract(OptionContractBase):
    """Schema for option contract response"""
    model_config = ConfigDict(from_attributes=True)

    is_active: str
    settlement_price: Optional[Decimal] = None
    contract_size: Optional[int] = None
    tick_size: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime


class OptionContractInDB(OptionContract):
    """Schema for option contract as stored in database"""
    pass


# ============ OptionDailyFactor Schemas ============

class OptionDailyFactorBase(BaseModel):
    """Base option daily factor schema"""
    model_config = ConfigDict(populate_by_name=True)

    underlying_id: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="標的物代碼"
    )
    factor_date: date = Field(
        ...,
        description="資料日期",
        serialization_alias="date",
        validation_alias="date"
    )


class OptionDailyFactorStage1(OptionDailyFactorBase):
    """階段一：基礎因子（必填）"""
    pcr_volume: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Put/Call Ratio (成交量)"
    )
    pcr_open_interest: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Put/Call Ratio (未平倉量)"
    )
    atm_iv: Optional[Decimal] = Field(
        None,
        ge=0,
        le=5,
        description="ATM 隱含波動率"
    )


class OptionDailyFactorStage2(OptionDailyFactorStage1):
    """階段二：進階因子"""
    iv_skew: Optional[Decimal] = Field(
        None,
        description="IV Skew (25 Delta)"
    )
    iv_term_structure: Optional[Decimal] = Field(
        None,
        ge=0,
        description="近月/遠月 IV 比值"
    )
    max_pain_strike: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Max Pain 履約價"
    )
    total_call_oi: Optional[int] = Field(
        None,
        ge=0,
        description="Call 總未平倉量"
    )
    total_put_oi: Optional[int] = Field(
        None,
        ge=0,
        description="Put 總未平倉量"
    )


class OptionDailyFactorStage3(OptionDailyFactorStage2):
    """階段三：Greeks 摘要"""
    avg_call_delta: Optional[Decimal] = Field(
        None,
        ge=-1,
        le=1,
        description="ATM Call Delta 均值"
    )
    avg_put_delta: Optional[Decimal] = Field(
        None,
        ge=-1,
        le=1,
        description="ATM Put Delta 均值"
    )
    gamma_exposure: Optional[Decimal] = Field(
        None,
        description="Gamma 總曝險"
    )
    vanna_exposure: Optional[Decimal] = Field(
        None,
        description="Vanna 曝險"
    )


class OptionDailyFactorCreate(OptionDailyFactorStage3):
    """Schema for creating option daily factor (supports all stages)"""
    data_quality_score: Optional[Decimal] = Field(
        None,
        ge=0,
        le=1,
        description="資料品質評分"
    )
    calculation_version: Optional[str] = Field(
        None,
        max_length=10,
        description="計算版本"
    )


class OptionDailyFactor(OptionDailyFactorStage3):
    """Schema for option daily factor response"""
    model_config = ConfigDict(from_attributes=True)

    data_quality_score: Optional[Decimal] = None
    calculation_version: Optional[str] = None
    created_at: datetime


class OptionDailyFactorInDB(OptionDailyFactor):
    """Schema for option daily factor as stored in database"""
    pass


# ============ OptionMinutePrice Schemas ============

class OptionMinutePriceBase(BaseModel):
    """Base option minute price schema"""
    model_config = ConfigDict(populate_by_name=True)

    contract_id: str = Field(..., max_length=20)
    dt: datetime = Field(..., serialization_alias="datetime", validation_alias="datetime")
    open: Decimal = Field(..., ge=0)
    high: Decimal = Field(..., ge=0)
    low: Decimal = Field(..., ge=0)
    close: Decimal = Field(..., ge=0)
    volume: int = Field(..., ge=0)


class OptionMinutePriceCreate(OptionMinutePriceBase):
    """Schema for creating option minute price"""
    open_interest: Optional[int] = Field(None, ge=0)
    bid_price: Optional[Decimal] = Field(None, ge=0)
    ask_price: Optional[Decimal] = Field(None, ge=0)
    implied_volatility: Optional[Decimal] = Field(None, ge=0)


class OptionMinutePrice(OptionMinutePriceBase):
    """Schema for option minute price response"""
    model_config = ConfigDict(from_attributes=True)

    open_interest: Optional[int] = None
    bid_price: Optional[Decimal] = None
    ask_price: Optional[Decimal] = None
    implied_volatility: Optional[Decimal] = None


# ============ OptionGreeks Schemas ============

class OptionGreeksBase(BaseModel):
    """Base option Greeks schema"""
    model_config = ConfigDict(populate_by_name=True)

    contract_id: str = Field(..., max_length=20)
    dt: datetime = Field(..., serialization_alias="datetime", validation_alias="datetime")


class OptionGreeksCreate(OptionGreeksBase):
    """Schema for creating option Greeks"""
    delta: Optional[Decimal] = Field(None, ge=-1, le=1)
    gamma: Optional[Decimal] = Field(None, ge=0)
    theta: Optional[Decimal] = Field(None)
    vega: Optional[Decimal] = Field(None, ge=0)
    rho: Optional[Decimal] = Field(None)
    vanna: Optional[Decimal] = Field(None)
    charm: Optional[Decimal] = Field(None)
    spot_price: Optional[Decimal] = Field(None, ge=0)
    volatility: Optional[Decimal] = Field(None, ge=0)
    risk_free_rate: Optional[Decimal] = Field(None)


class OptionGreeks(OptionGreeksBase):
    """Schema for option Greeks response"""
    model_config = ConfigDict(from_attributes=True)

    delta: Optional[Decimal] = None
    gamma: Optional[Decimal] = None
    theta: Optional[Decimal] = None
    vega: Optional[Decimal] = None
    rho: Optional[Decimal] = None
    vanna: Optional[Decimal] = None
    charm: Optional[Decimal] = None
    spot_price: Optional[Decimal] = None
    volatility: Optional[Decimal] = None
    risk_free_rate: Optional[Decimal] = None


# ============ OptionSyncConfig Schemas ============

class OptionSyncConfigBase(BaseModel):
    """Base option sync config schema"""
    key: str = Field(..., max_length=50)
    value: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=500)


class OptionSyncConfigCreate(OptionSyncConfigBase):
    """Schema for creating option sync config"""
    pass


class OptionSyncConfigUpdate(BaseModel):
    """Schema for updating option sync config"""
    value: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=500)


class OptionSyncConfig(OptionSyncConfigBase):
    """Schema for option sync config response"""
    model_config = ConfigDict(from_attributes=True)

    updated_at: datetime


class OptionSyncConfigInDB(OptionSyncConfig):
    """Schema for option sync config as stored in database"""
    pass


# ============ Utility Schemas ============

class OptionChainItem(BaseModel):
    """單一選擇權合約資訊（用於 Option Chain 顯示）"""
    contract_id: str
    option_type: str
    strike_price: Decimal
    last_price: Optional[Decimal] = None
    bid_price: Optional[Decimal] = None
    ask_price: Optional[Decimal] = None
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    implied_volatility: Optional[Decimal] = None
    delta: Optional[Decimal] = None
    gamma: Optional[Decimal] = None
    theta: Optional[Decimal] = None
    vega: Optional[Decimal] = None


class OptionChainResponse(BaseModel):
    """Option Chain 回應（特定到期日的所有履約價）"""
    underlying_id: str
    expiry_date: date
    spot_price: Optional[Decimal] = None
    calls: List[OptionChainItem] = Field(default_factory=list)
    puts: List[OptionChainItem] = Field(default_factory=list)


class OptionFactorSummary(BaseModel):
    """選擇權因子摘要（用於儀表板）"""
    model_config = ConfigDict(populate_by_name=True)

    underlying_id: str
    factor_date: date = Field(..., serialization_alias="date", validation_alias="date")

    # 階段一因子
    pcr_volume: Optional[Decimal] = None
    pcr_open_interest: Optional[Decimal] = None
    atm_iv: Optional[Decimal] = None

    # 階段二因子
    iv_skew: Optional[Decimal] = None
    max_pain_strike: Optional[Decimal] = None
    total_oi: Optional[int] = None  # total_call_oi + total_put_oi

    # 市場情緒指標
    sentiment: Optional[str] = None  # bullish/bearish/neutral (基於 PCR)


class OptionStageInfo(BaseModel):
    """當前階段資訊"""
    stage: int = Field(..., ge=1, le=3, description="當前階段（1/2/3）")
    enabled_underlyings: List[str] = Field(default_factory=list)
    sync_minute_data: bool = False
    calculate_greeks: bool = False
    available_factors: List[str] = Field(default_factory=list)


class OptionSyncStatus(BaseModel):
    """同步狀態回應"""
    underlying_id: str
    last_sync_date: Optional[date] = None
    total_contracts: int = 0
    active_contracts: int = 0
    data_quality_score: Optional[Decimal] = None
    stage: int
