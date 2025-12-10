"""
Stock data Pydantic schemas
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field


class StockInfo(BaseModel):
    """Stock basic information"""
    stock_id: str
    name: str
    industry: Optional[str] = None
    market: Optional[str] = None


class StockSearchRequest(BaseModel):
    """Stock search request"""
    keyword: str


class StockSearchResult(BaseModel):
    """Stock search result"""
    results: List[StockInfo]
    count: int


class StockDataResponse(BaseModel):
    """Generic stock data response"""
    stock_id: Optional[str] = None
    data: Dict[str, Any]
    cached: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LatestPriceResponse(BaseModel):
    """Latest price response"""
    stock_id: str
    price: Optional[float]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
