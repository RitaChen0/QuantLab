"""
Fundamental Analysis Schemas
Pydantic schemas for financial indicators and fundamental data
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class FundamentalIndicatorRequest(BaseModel):
    """Request schema for getting fundamental indicator data"""

    indicator: str = Field(
        ...,
        description="財務指標名稱 (e.g., 'ROE稅後', 'ROA稅後息前')",
        examples=["ROE稅後", "營業毛利率"]
    )
    stock_id: Optional[str] = Field(
        None,
        description="股票代號 (若未指定則返回所有股票)",
        examples=["2330"]
    )
    start_date: Optional[str] = Field(
        None,
        description="起始日期 (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        examples=["2024-01-01"]
    )
    end_date: Optional[str] = Field(
        None,
        description="結束日期 (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        examples=["2024-12-31"]
    )


class FundamentalIndicatorBatchRequest(BaseModel):
    """Request schema for getting multiple fundamental indicators"""

    stock_id: str = Field(
        ...,
        description="股票代號",
        examples=["2330"]
    )
    indicators: Optional[List[str]] = Field(
        None,
        description="指標列表 (若未指定則返回常用指標)",
        examples=[["ROE稅後", "ROA稅後息前", "營業毛利率"]]
    )
    start_date: Optional[str] = Field(
        None,
        description="起始日期 (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        examples=["2024-01-01"]
    )
    end_date: Optional[str] = Field(
        None,
        description="結束日期 (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        examples=["2024-12-31"]
    )


class FundamentalDataPoint(BaseModel):
    """Single data point in fundamental indicator time series"""

    date: str = Field(..., description="日期")
    value: Optional[float] = Field(None, description="指標值")


class FundamentalIndicatorResponse(BaseModel):
    """Response schema for fundamental indicator data"""

    indicator: str = Field(..., description="指標名稱")
    stock_id: Optional[str] = Field(None, description="股票代號")
    data: List[FundamentalDataPoint] = Field(..., description="時間序列數據")
    count: int = Field(..., description="數據點數量")
    start_date: Optional[str] = Field(None, description="數據起始日期")
    end_date: Optional[str] = Field(None, description="數據結束日期")


class FundamentalIndicatorBatchResponse(BaseModel):
    """Response schema for batch fundamental indicators"""

    stock_id: str = Field(..., description="股票代號")
    indicators: Dict[str, List[FundamentalDataPoint]] = Field(
        ...,
        description="指標數據字典 (指標名稱 -> 時間序列)"
    )
    count: int = Field(..., description="成功獲取的指標數量")
    requested_count: int = Field(..., description="請求的指標數量")
    start_date: Optional[str] = Field(None, description="數據起始日期")
    end_date: Optional[str] = Field(None, description="數據結束日期")


class FundamentalIndicatorInfo(BaseModel):
    """Information about a fundamental indicator"""

    name: str = Field(..., description="指標名稱")
    name_en: str = Field(..., description="英文名稱")
    category: str = Field(..., description="分類")
    description: Optional[str] = Field(None, description="說明")


class FundamentalIndicatorListResponse(BaseModel):
    """Response schema for listing available indicators"""

    indicators: List[FundamentalIndicatorInfo] = Field(..., description="可用指標列表")
    count: int = Field(..., description="指標數量")
    categories: Dict[str, int] = Field(..., description="各分類的指標數量")


class FundamentalIndicatorCategoryResponse(BaseModel):
    """Response schema for indicators grouped by category"""

    categories: Dict[str, List[str]] = Field(
        ...,
        description="分類與指標映射"
    )
    total_count: int = Field(..., description="總指標數量")


class FundamentalSummary(BaseModel):
    """Summary of fundamental indicators for a stock"""

    stock_id: str = Field(..., description="股票代號")
    latest_date: Optional[str] = Field(None, description="最新數據日期")

    # Profitability
    roe: Optional[float] = Field(None, description="ROE稅後 (%)")
    roa: Optional[float] = Field(None, description="ROA稅後息前 (%)")
    gross_margin: Optional[float] = Field(None, description="營業毛利率 (%)")
    operating_margin: Optional[float] = Field(None, description="營業利益率 (%)")
    net_margin: Optional[float] = Field(None, description="稅後淨利率 (%)")

    # Growth
    revenue_growth: Optional[float] = Field(None, description="營收成長率 (%)")
    profit_growth: Optional[float] = Field(None, description="稅後淨利成長率 (%)")

    # Efficiency
    receivable_turnover: Optional[float] = Field(None, description="應收帳款週轉率")
    inventory_turnover: Optional[float] = Field(None, description="存貨週轉率")
    asset_turnover: Optional[float] = Field(None, description="總資產週轉率")

    # Financial Structure
    debt_ratio: Optional[float] = Field(None, description="負債比率 (%)")
    current_ratio: Optional[float] = Field(None, description="流動比率")
    quick_ratio: Optional[float] = Field(None, description="速動比率")

    # Per Share
    book_value_per_share: Optional[float] = Field(None, description="每股淨值")
    eps: Optional[float] = Field(None, description="每股盈餘 (EPS)")
    revenue_per_share: Optional[float] = Field(None, description="每股營業額")


class FundamentalComparisonRequest(BaseModel):
    """Request schema for comparing fundamentals across stocks"""

    stock_ids: List[str] = Field(
        ...,
        description="股票代號列表",
        min_length=2,
        max_length=10,
        examples=[["2330", "2317", "2454"]]
    )
    indicator: str = Field(
        ...,
        description="要比較的指標",
        examples=["ROE稅後"]
    )
    start_date: Optional[str] = Field(
        None,
        description="起始日期 (YYYY-MM-DD)",
        examples=["2024-01-01"]
    )
    end_date: Optional[str] = Field(
        None,
        description="結束日期 (YYYY-MM-DD)",
        examples=["2024-12-31"]
    )


class FundamentalComparisonResponse(BaseModel):
    """Response schema for fundamental comparison"""

    indicator: str = Field(..., description="指標名稱")
    stocks: Dict[str, List[FundamentalDataPoint]] = Field(
        ...,
        description="各股票的指標數據"
    )
    count: int = Field(..., description="成功比較的股票數量")
    start_date: Optional[str] = Field(None, description="數據起始日期")
    end_date: Optional[str] = Field(None, description="數據結束日期")
