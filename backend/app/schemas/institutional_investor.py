"""
Institutional Investor Schemas
法人買賣超資料的 Pydantic schemas
"""

from pydantic import BaseModel, Field, ConfigDict
import datetime
from typing import Optional, List
from enum import Enum


class InvestorType(str, Enum):
    """法人類型枚舉"""
    FOREIGN_INVESTOR = "Foreign_Investor"
    INVESTMENT_TRUST = "Investment_Trust"
    DEALER_SELF = "Dealer_self"
    DEALER_HEDGING = "Dealer_Hedging"
    FOREIGN_DEALER_SELF = "Foreign_Dealer_Self"


# ============ Base Schemas ============

class InstitutionalInvestorBase(BaseModel):
    """法人買賣超基礎 Schema"""
    date: datetime.date = Field(description="日期")
    stock_id: str = Field(max_length=10, description="股票代碼")
    investor_type: InvestorType = Field(description="法人類型")
    buy_volume: int = Field(ge=0, description="買進股數")
    sell_volume: int = Field(ge=0, description="賣出股數")


# ============ Request Schemas ============

class InstitutionalInvestorCreate(InstitutionalInvestorBase):
    """創建法人買賣超資料的 Schema"""
    pass


class InstitutionalInvestorUpdate(BaseModel):
    """更新法人買賣超資料的 Schema"""
    buy_volume: Optional[int] = Field(None, ge=0, description="買進股數")
    sell_volume: Optional[int] = Field(None, ge=0, description="賣出股數")


class InstitutionalInvestorQuery(BaseModel):
    """查詢法人買賣超的參數"""
    stock_id: Optional[str] = Field(None, max_length=10, description="股票代碼")
    start_date: Optional[datetime.date] = Field(None, description="開始日期")
    end_date: Optional[datetime.date] = Field(None, description="結束日期")
    investor_type: Optional[InvestorType] = Field(None, description="法人類型")
    limit: int = Field(default=100, ge=1, le=1000, description="返回記錄數量")
    offset: int = Field(default=0, ge=0, description="跳過記錄數量")


class InstitutionalInvestorBulkCreate(BaseModel):
    """批量創建法人買賣超資料"""
    records: List[InstitutionalInvestorCreate] = Field(description="法人買賣超記錄列表")


# ============ Response Schemas ============

class InstitutionalInvestorInDB(InstitutionalInvestorBase):
    """資料庫中的法人買賣超資料"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    net_buy_sell: Optional[int] = Field(None, description="買賣超（正數=買超，負數=賣超）")
    created_at: datetime.datetime
    updated_at: datetime.datetime


class InstitutionalInvestorResponse(InstitutionalInvestorInDB):
    """API 返回的法人買賣超資料"""
    pass


class InstitutionalInvestorSummary(BaseModel):
    """法人買賣超統計摘要"""
    model_config = ConfigDict(from_attributes=True)

    date: datetime.date
    stock_id: str
    foreign_net: Optional[int] = Field(None, description="外資買賣超")
    trust_net: Optional[int] = Field(None, description="投信買賣超")
    dealer_self_net: Optional[int] = Field(None, description="自營商買賣超")
    dealer_hedging_net: Optional[int] = Field(None, description="自營商避險買賣超")
    total_net: Optional[int] = Field(None, description="三大法人合計買賣超")


class InstitutionalInvestorStats(BaseModel):
    """法人買賣超統計數據"""
    model_config = ConfigDict(from_attributes=True)

    stock_id: str
    investor_type: InvestorType
    period_start: datetime.date
    period_end: datetime.date
    total_buy: int = Field(description="期間總買進股數")
    total_sell: int = Field(description="期間總賣出股數")
    total_net: int = Field(description="期間淨買賣超")
    avg_daily_net: float = Field(description="日均買賣超")
    buy_days: int = Field(description="買超天數")
    sell_days: int = Field(description="賣超天數")


# ============ Task Schemas ============

class SyncTaskResponse(BaseModel):
    """同步任務響應"""
    task_id: str = Field(description="Celery 任務 ID")
    status: str = Field(description="任務狀態")
    message: str = Field(description="訊息")
