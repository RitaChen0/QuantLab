"""
StockPrice-related Pydantic schemas for request/response validation
"""

from typing import Optional, List
from datetime import date as DateType
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


# ============ StockPrice Schemas ============

class StockPriceBase(BaseModel):
    """Base stock price schema with common fields"""
    stock_id: str = Field(..., max_length=10, description="股票代碼")
    date: DateType = Field(..., description="交易日期")
    open: Decimal = Field(..., ge=0, description="開盤價")
    high: Decimal = Field(..., ge=0, description="最高價")
    low: Decimal = Field(..., ge=0, description="最低價")
    close: Decimal = Field(..., ge=0, description="收盤價")
    volume: int = Field(..., ge=0, description="成交量")
    adj_close: Optional[Decimal] = Field(None, ge=0, description="調整後收盤價")


class StockPriceCreate(StockPriceBase):
    """Schema for creating a new stock price record"""
    pass


class StockPriceUpdate(BaseModel):
    """Schema for updating stock price"""
    open: Optional[Decimal] = Field(None, ge=0)
    high: Optional[Decimal] = Field(None, ge=0)
    low: Optional[Decimal] = Field(None, ge=0)
    close: Optional[Decimal] = Field(None, ge=0)
    volume: Optional[int] = Field(None, ge=0)
    adj_close: Optional[Decimal] = Field(None, ge=0)


class StockPrice(StockPriceBase):
    """Schema for stock price response"""
    model_config = ConfigDict(from_attributes=True)


# Additional utility schemas
class StockPriceQuery(BaseModel):
    """Query parameters for stock price data"""
    stock_id: str = Field(..., description="股票代碼")
    start_date: Optional[DateType] = Field(None, description="開始日期")
    end_date: Optional[DateType] = Field(None, description="結束日期")
    limit: Optional[int] = Field(100, ge=1, le=1000, description="返回筆數限制")


class StockPriceListResponse(BaseModel):
    """Stock price list response"""
    stock_id: str
    prices: List[StockPrice]
    count: int


class OHLCVData(BaseModel):
    """OHLCV data format"""
    date: DateType
    open: float
    high: float
    low: float
    close: float
    volume: int
