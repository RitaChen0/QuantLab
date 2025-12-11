"""
Stock Minute Price Schemas

分鐘級股票價格數據的 Pydantic 驗證模型
"""
from __future__ import annotations

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class StockMinutePriceBase(BaseModel):
    """分鐘級股票價格基礎 Schema"""
    stock_id: str
    datetime: datetime
    timeframe: str = '1min'
    open: float
    high: float
    low: float
    close: float
    volume: int
    adj_close: Optional[float] = None
    trades_count: Optional[int] = None


class StockMinutePriceCreate(StockMinutePriceBase):
    """創建分鐘級股票價格的 Schema"""
    pass


class StockMinutePriceUpdate(BaseModel):
    """更新分鐘級股票價格的 Schema（可選欄位）"""
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None
    adj_close: Optional[float] = None
    trades_count: Optional[int] = None


class StockMinutePriceResponse(StockMinutePriceBase):
    """分鐘級股票價格響應 Schema"""
    created_at: datetime


class StockMinutePriceListResponse(BaseModel):
    """分鐘級股票價格列表響應 Schema"""
    stock_id: str
    timeframe: str
    data: dict
    count: int
