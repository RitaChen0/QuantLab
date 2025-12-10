"""
Trade-related Pydantic schemas for request/response validation
"""

from typing import Optional, List
from datetime import date as DateType, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class TradeAction(str, Enum):
    """Trade action enumeration"""
    BUY = "BUY"
    SELL = "SELL"


# ============ Trade Schemas ============

class TradeBase(BaseModel):
    """Base trade schema with common fields"""
    stock_id: str = Field(..., max_length=10, description="股票代碼")
    date: DateType = Field(..., description="交易日期")
    action: TradeAction = Field(..., description="交易動作（buy/sell）")
    quantity: int = Field(..., gt=0, description="交易數量（股數）")
    price: Decimal = Field(..., gt=0, description="交易價格")
    commission: Decimal = Field(default=Decimal("0"), ge=0, description="手續費")
    tax: Decimal = Field(default=Decimal("0"), ge=0, description="交易稅")


class TradeCreate(TradeBase):
    """Schema for creating a new trade"""
    backtest_id: int = Field(..., gt=0, description="回測 ID")
    total_amount: Decimal = Field(..., description="交易總額")
    profit_loss: Optional[Decimal] = Field(None, description="獲利/虧損")


class TradeUpdate(BaseModel):
    """Schema for updating trade"""
    quantity: Optional[int] = Field(None, gt=0)
    price: Optional[Decimal] = Field(None, gt=0)
    commission: Optional[Decimal] = Field(None, ge=0)
    tax: Optional[Decimal] = Field(None, ge=0)
    total_amount: Optional[Decimal] = None
    profit_loss: Optional[Decimal] = None


class TradeInDB(TradeBase):
    """Schema for trade as stored in database"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    backtest_id: int
    total_amount: Decimal
    profit_loss: Optional[Decimal]
    created_at: datetime


class Trade(TradeBase):
    """Schema for trade response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    backtest_id: int
    total_amount: Decimal
    profit_loss: Optional[Decimal]
    created_at: datetime


# Additional utility schemas
class TradeListResponse(BaseModel):
    """Trade list response"""
    trades: List[Trade]
    total: int
    page: int = 1
    page_size: int = 50


class TradeQuery(BaseModel):
    """Query parameters for trades"""
    backtest_id: int = Field(..., gt=0, description="回測 ID")
    stock_id: Optional[str] = Field(None, description="股票代碼")
    action: Optional[TradeAction] = Field(None, description="交易動作")
    start_date: Optional[DateType] = Field(None, description="開始日期")
    end_date: Optional[DateType] = Field(None, description="結束日期")
    limit: Optional[int] = Field(100, ge=1, le=1000, description="返回筆數限制")


class TradeSummary(BaseModel):
    """Trade summary statistics"""
    backtest_id: int
    total_trades: int
    total_buy_amount: Decimal
    total_sell_amount: Decimal
    total_commission: Decimal
    total_tax: Decimal
    total_profit_loss: Optional[Decimal]


class TradePerformance(BaseModel):
    """Trade performance by stock"""
    stock_id: str
    stock_name: Optional[str] = None
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_profit_loss: Decimal
    win_rate: Decimal
