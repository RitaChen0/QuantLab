"""
Industry Schemas

Pydantic models for industry API request/response validation.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# Base Industry Schema
class IndustryBase(BaseModel):
    code: str = Field(..., description="產業代碼")
    name_zh: str = Field(..., description="中文名稱")
    name_en: Optional[str] = Field(None, description="英文名稱")
    level: int = Field(..., description="產業層級 (1=大類, 2=中類, 3=小類)")
    parent_code: Optional[str] = Field(None, description="父產業代碼")
    description: Optional[str] = Field(None, description="產業描述")


class IndustryResponse(IndustryBase):
    """Industry response with stock count."""
    stock_count: int = Field(0, description="歸類股票數量")
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class IndustryTreeNode(IndustryBase):
    """Industry tree node with nested children."""
    stock_count: int = Field(0, description="歸類股票數量")
    children: List['IndustryTreeNode'] = Field(default_factory=list)

    class Config:
        from_attributes = True


# Stock-Industry Relationship Schemas
class StockIndustryBase(BaseModel):
    stock_id: str = Field(..., description="股票代號")
    industry_code: str = Field(..., description="產業代碼")
    is_primary: bool = Field(False, description="是否為主要產業")


class StockIndustryResponse(StockIndustryBase):
    """Stock-industry relationship response."""
    created_at: datetime

    class Config:
        from_attributes = True


class StockWithIndustries(BaseModel):
    """Stock with its industries."""
    stock_id: str
    industries: List[IndustryResponse]


class StockInfo(BaseModel):
    """Stock information."""
    stock_id: str = Field(..., description="股票代號")
    stock_name: str = Field(..., description="股票名稱")


class IndustryWithStocks(BaseModel):
    """Industry with its stocks."""
    industry: IndustryResponse
    stocks: List[StockInfo] = Field(..., description="股票列表（含名稱）")


# Industry Metrics Schemas
class MetricValue(BaseModel):
    """Metric value with sample size."""
    average: float = Field(..., description="平均值")
    sample_size: int = Field(..., description="樣本數量")
    previous_value: Optional[float] = Field(None, description="上季度平均值")
    change_percent: Optional[float] = Field(None, description="與上季度變化百分比")
    trend_data: Optional[List[float]] = Field(None, description="最近10季趨勢數據")


class IndustryMetricsResponse(BaseModel):
    """Industry aggregated metrics response."""
    industry_code: str = Field(..., description="產業代碼")
    date: str = Field(..., description="數據日期")
    stocks_count: int = Field(..., description="計算基礎股票數")
    metrics: Dict[str, MetricValue] = Field(
        ...,
        description="財務指標 (ROE稅後, ROA稅後息前, 營業毛利率, etc.)"
    )


class HistoricalMetricPoint(BaseModel):
    """Single historical metric data point."""
    date: str
    value: Optional[float]
    stocks_count: Optional[int]


class IndustryMetricsHistoricalResponse(BaseModel):
    """Historical industry metrics response."""
    industry_code: str
    metric_name: str
    data: List[HistoricalMetricPoint]


class IndustryPerformanceSummary(BaseModel):
    """Industry performance summary."""
    code: str
    name_zh: str
    name_en: Optional[str]
    level: int
    parent_code: Optional[str]
    stocks_count: int
    latest_metrics: Dict[str, Dict[str, Any]] = Field(
        ...,
        description="最新財務指標數據"
    )


# List Response Schemas
class IndustryListResponse(BaseModel):
    """List of industries response."""
    total: int = Field(..., description="總數")
    industries: List[IndustryResponse]


class IndustryTreeResponse(BaseModel):
    """Industry tree structure response."""
    total: int = Field(..., description="根節點數量")
    tree: List[IndustryTreeNode]


# Statistics Schema
class IndustryStatistics(BaseModel):
    """Industry database statistics."""
    total_industries: int
    by_level: Dict[str, int]
    total_stock_mappings: int


# Industry Comparison Schema
class IndustryComparisonMetric(BaseModel):
    """Single industry's metric value for comparison."""
    industry_code: str = Field(..., description="產業代碼")
    industry_name: str = Field(..., description="產業名稱")
    value: Optional[float] = Field(None, description="指標值")
    sample_size: int = Field(0, description="樣本數量")


class IndustryComparisonResponse(BaseModel):
    """Industry comparison response."""
    metric_name: str = Field(..., description="指標名稱")
    date: str = Field(..., description="數據日期")
    industries: List[IndustryComparisonMetric] = Field(..., description="產業對比數據")


# Update forward references for nested models
IndustryTreeNode.model_rebuild()
