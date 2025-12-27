"""
Stock-related Pydantic schemas for request/response validation
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.utils.timezone_helpers import now_utc


# ============ Stock Schemas ============

class StockBase(BaseModel):
    """Base stock schema with common fields"""
    stock_id: str = Field(..., min_length=1, max_length=10, description="股票代碼（如 2330）")
    name: str = Field(..., min_length=1, max_length=100, description="股票名稱")
    category: Optional[str] = Field(None, max_length=50, description="產業分類")
    market: Optional[str] = Field(None, max_length=20, description="市場別（上市/上櫃/興櫃）")


class StockCreate(StockBase):
    """Schema for creating a new stock"""
    is_active: str = Field(default="active", max_length=10, description="狀態")


class StockUpdate(BaseModel):
    """Schema for updating stock"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, max_length=50)
    market: Optional[str] = Field(None, max_length=20)
    is_active: Optional[str] = Field(None, max_length=10)


class StockInDB(StockBase):
    """Schema for stock as stored in database"""
    model_config = ConfigDict(from_attributes=True)

    is_active: str
    created_at: datetime
    updated_at: datetime


class Stock(StockBase):
    """Schema for stock response"""
    model_config = ConfigDict(from_attributes=True)

    is_active: str
    created_at: datetime


# Additional utility schemas

# ============ Data API Schemas (for FinLab integration) ============

class StockInfo(BaseModel):
    """Stock basic information (for data API)"""
    stock_id: str
    name: str
    industry: Optional[str] = None
    market: Optional[str] = None


class StockSearchRequest(BaseModel):
    """Stock search request"""
    keyword: str = Field(..., min_length=1, description="搜尋關鍵字")


class StockSearchResult(BaseModel):
    """Stock search result"""
    results: List[StockInfo]
    count: int


class StockListResponse(BaseModel):
    """Stock list response"""
    stocks: List[Stock]
    total: int
    page: int = 1
    page_size: int = 50


class StockDataResponse(BaseModel):
    """Generic stock data response"""
    stock_id: Optional[str] = None
    data: Dict[str, Any]
    cached: bool = False
    timestamp: datetime = Field(default_factory=now_utc)


class LatestPriceResponse(BaseModel):
    """Latest price response"""
    stock_id: str
    price: Optional[float]
    timestamp: datetime = Field(default_factory=now_utc)
