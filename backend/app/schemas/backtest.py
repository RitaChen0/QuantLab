"""
Backtest-related Pydantic schemas for request/response validation
"""

from typing import Optional, List, Dict, Any, ForwardRef
from datetime import date as DateType, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator
from enum import Enum


class BacktestStatus(str, Enum):
    """Backtest status enumeration"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ============ Nested Schemas ============

class StrategyInBacktest(BaseModel):
    """Minimal strategy info for backtest response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    status: str


class BacktestResultInResponse(BaseModel):
    """Backtest result for response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    total_return: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal
    win_rate: Decimal
    total_trades: int
    winning_trades: int
    losing_trades: int
    average_profit: Decimal


# ============ Backtest Schemas ============

class BacktestBase(BaseModel):
    """Base backtest schema with common fields"""
    name: str = Field(..., min_length=1, max_length=200, description="回測名稱")
    description: Optional[str] = Field(None, description="回測描述")
    symbol: str = Field(..., min_length=1, max_length=20, description="股票代碼")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="策略參數")
    start_date: DateType = Field(..., description="回測開始日期")
    end_date: DateType = Field(..., description="回測結束日期")

    # 資金設定
    initial_capital: Decimal = Field(
        default=Decimal("1000000"),
        ge=0,
        description="初始資金"
    )

    # 交易成本設定
    commission: Optional[Decimal] = Field(
        default=Decimal("0.001425"),
        ge=0,
        le=1,
        description="手續費率（預設 0.001425 = 0.1425%）"
    )
    tax: Optional[Decimal] = Field(
        default=Decimal("0.003"),
        ge=0,
        le=1,
        description="交易稅率（預設 0.003 = 0.3%，僅賣出時收取）"
    )
    slippage: Optional[Decimal] = Field(
        default=Decimal("0.0"),
        ge=0,
        le=1,
        description="滑點率（預設 0）"
    )

    # 倉位設定
    position_size: Optional[int] = Field(
        default=None,
        ge=1,
        description="每次交易的股數（None 表示全倉）"
    )
    max_position_pct: Optional[Decimal] = Field(
        default=Decimal("1.0"),
        ge=0,
        le=1,
        description="最大倉位比例（0-1，預設 1.0 = 100%）"
    )

    # 引擎設定
    engine_type: Optional[str] = Field(
        default=None,
        description="回測引擎類型（留空則繼承策略設定）：backtrader 或 qlib"
    )

    # 時間粒度設定
    timeframe: str = Field(
        default='1day',
        description="時間粒度：1min, 5min, 15min, 30min, 60min, 1day"
    )

    @field_validator('timeframe')
    @classmethod
    def validate_timeframe(cls, v: str) -> str:
        """驗證 timeframe 是否為有效值"""
        valid_timeframes = ['1min', '5min', '15min', '30min', '60min', '1day']
        if v not in valid_timeframes:
            raise ValueError(
                f'timeframe must be one of {valid_timeframes}, got: {v}'
            )
        return v


class BacktestCreate(BacktestBase):
    """Schema for creating a new backtest"""
    strategy_id: int = Field(..., gt=0, description="策略 ID")


class BacktestUpdate(BaseModel):
    """Schema for updating backtest"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[BacktestStatus] = None


class BacktestInDB(BacktestBase):
    """Schema for backtest as stored in database"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy_id: int
    user_id: int
    status: BacktestStatus
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class Backtest(BaseModel):
    """Schema for backtest response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy_id: int
    user_id: int
    name: str
    description: Optional[str]
    symbol: str
    start_date: DateType
    end_date: DateType
    initial_capital: Decimal
    status: BacktestStatus
    engine_type: str
    timeframe: str
    created_at: datetime
    updated_at: datetime
    strategy: Optional[StrategyInBacktest] = None  # Strategy relationship


class BacktestDetail(BacktestInDB):
    """Schema for detailed backtest response"""
    strategy: Optional[StrategyInBacktest] = None  # Strategy relationship
    result: Optional[BacktestResultInResponse] = None  # BacktestResult relationship


# Additional utility schemas
class BacktestListResponse(BaseModel):
    """Backtest list response"""
    backtests: List[Backtest]
    total: int
    page: int = 1
    page_size: int = 20


class BacktestRunRequest(BaseModel):
    """Request to run a backtest"""
    backtest_id: int = Field(..., gt=0, description="回測 ID")


class BacktestProgress(BaseModel):
    """Backtest execution progress"""
    backtest_id: int
    status: BacktestStatus
    progress: float = Field(..., ge=0, le=100, description="進度百分比")
    current_date: Optional[DateType] = None
    message: Optional[str] = None
