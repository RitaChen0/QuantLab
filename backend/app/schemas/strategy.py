"""
Strategy-related Pydantic schemas for request/response validation
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class StrategyStatus(str, Enum):
    """Strategy status enumeration"""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


# ============ Strategy Schemas ============

class StrategyBase(BaseModel):
    """Base strategy schema with common fields"""
    name: str = Field(..., min_length=1, max_length=200, description="策略名稱")
    description: Optional[str] = Field(None, description="策略描述")
    code: str = Field(..., min_length=1, description="策略代碼（Python）")
    parameters: Optional[Dict[str, Any]] = Field(None, description="策略參數（JSON）")
    engine_type: str = Field(
        default='backtrader',
        description="回測引擎類型：backtrader（技術指標策略）或 qlib（機器學習策略）"
    )


class StrategyCreate(StrategyBase):
    """Schema for creating a new strategy"""
    status: StrategyStatus = Field(default=StrategyStatus.DRAFT, description="策略狀態")


class StrategyUpdate(BaseModel):
    """Schema for updating strategy"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    code: Optional[str] = Field(None, min_length=1)
    parameters: Optional[Dict[str, Any]] = None
    status: Optional[StrategyStatus] = None
    engine_type: Optional[str] = Field(None, description="回測引擎類型")


class StrategyInDB(StrategyBase):
    """Schema for strategy as stored in database"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: StrategyStatus
    created_at: datetime
    updated_at: datetime


class Strategy(BaseModel):
    """Schema for strategy response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    description: Optional[str]
    status: StrategyStatus
    engine_type: str
    created_at: datetime
    updated_at: datetime


class StrategyDetail(StrategyInDB):
    """Schema for detailed strategy response (includes code)"""
    pass


# Additional utility schemas
class StrategyListResponse(BaseModel):
    """Strategy list response"""
    strategies: List[Strategy]
    total: int
    page: int = 1
    page_size: int = 20


class StrategyCodeValidationRequest(BaseModel):
    """Request to validate strategy code"""
    code: str = Field(..., description="策略代碼")
    engine_type: Optional[str] = Field('backtrader', description="策略引擎類型 (backtrader/qlib)")


class StrategyCodeValidationResponse(BaseModel):
    """Response from strategy code validation"""
    valid: bool
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
