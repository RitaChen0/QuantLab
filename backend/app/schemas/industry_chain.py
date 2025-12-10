"""
Industry Chain and Custom Category Schemas

用於 FinMind 產業鏈和自定義分類的 API 驗證
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ========== IndustryChain Schemas ==========

class IndustryChainBase(BaseModel):
    """產業鏈基礎 Schema"""
    chain_name: str = Field(..., description="產業鏈名稱")
    description: Optional[str] = Field(None, description="產業鏈描述")


class IndustryChainCreate(IndustryChainBase):
    """創建產業鏈"""
    pass


class IndustryChainUpdate(BaseModel):
    """更新產業鏈"""
    description: Optional[str] = Field(None, description="產業鏈描述")


class IndustryChainResponse(IndustryChainBase):
    """產業鏈響應"""
    id: int
    created_at: datetime
    updated_at: datetime
    stock_count: Optional[int] = Field(None, description="包含的股票數量")

    class Config:
        from_attributes = True


class IndustryChainWithStocks(IndustryChainResponse):
    """產業鏈及其股票列表"""
    stocks: List[str] = Field(default_factory=list, description="股票代號列表")


# ========== StockIndustryChain Schemas ==========

class StockIndustryChainBase(BaseModel):
    """股票產業鏈關聯基礎 Schema"""
    stock_id: str = Field(..., description="股票代號")
    chain_name: str = Field(..., description="產業鏈名稱")
    is_primary: bool = Field(False, description="是否為主要產業鏈")


class StockIndustryChainCreate(StockIndustryChainBase):
    """創建股票產業鏈關聯"""
    pass


class StockIndustryChainBulkCreate(BaseModel):
    """批量創建股票產業鏈關聯"""
    chain_name: str = Field(..., description="產業鏈名稱")
    stock_ids: List[str] = Field(..., description="股票代號列表")
    primary_stock_id: Optional[str] = Field(None, description="主要股票代號")


class StockIndustryChainResponse(StockIndustryChainBase):
    """股票產業鏈關聯響應"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========== CustomIndustryCategory Schemas ==========

class CustomIndustryCategoryBase(BaseModel):
    """自定義產業分類基礎 Schema"""
    category_name: str = Field(..., min_length=1, max_length=100,
                              description="分類名稱")
    description: Optional[str] = Field(None, max_length=500,
                                      description="分類描述")
    parent_id: Optional[int] = Field(None, description="父分類 ID")


class CustomIndustryCategoryCreate(CustomIndustryCategoryBase):
    """創建自定義產業分類"""
    pass


class CustomIndustryCategoryUpdate(BaseModel):
    """更新自定義產業分類"""
    category_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    parent_id: Optional[int] = None


class CustomIndustryCategoryResponse(CustomIndustryCategoryBase):
    """自定義產業分類響應"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    stock_count: Optional[int] = Field(None, description="包含的股票數量")

    class Config:
        from_attributes = True


class CustomIndustryCategoryWithStocks(CustomIndustryCategoryResponse):
    """自定義產業分類及其股票列表"""
    stocks: List[str] = Field(default_factory=list, description="股票代號列表")


class CustomIndustryCategoryTree(BaseModel):
    """自定義產業分類樹狀結構"""
    id: int
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    stock_count: int = 0
    children: List['CustomIndustryCategoryTree'] = Field(default_factory=list)


# 為遞迴模型更新 forward refs
CustomIndustryCategoryTree.model_rebuild()


# ========== StockCustomCategory Schemas ==========

class StockCustomCategoryCreate(BaseModel):
    """添加股票到自定義分類"""
    category_id: int = Field(..., description="分類 ID")
    stock_id: str = Field(..., description="股票代號")


class StockCustomCategoryBulkCreate(BaseModel):
    """批量添加股票到自定義分類"""
    category_id: int = Field(..., description="分類 ID")
    stock_ids: List[str] = Field(..., description="股票代號列表")


class StockCustomCategoryResponse(BaseModel):
    """股票自定義分類關聯響應"""
    id: int
    category_id: int
    stock_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# ========== Search and Filter Schemas ==========

class IndustryChainSearchRequest(BaseModel):
    """產業鏈搜尋請求"""
    keyword: Optional[str] = Field(None, description="搜尋關鍵字")
    stock_id: Optional[str] = Field(None, description="根據股票代號篩選")


class CustomCategorySearchRequest(BaseModel):
    """自定義分類搜尋請求"""
    keyword: Optional[str] = Field(None, description="搜尋關鍵字")
    parent_id: Optional[int] = Field(None, description="父分類 ID")
    stock_id: Optional[str] = Field(None, description="根據股票代號篩選")


# ========== Statistics Schemas ==========

class IndustryChainStatistics(BaseModel):
    """產業鏈統計信息"""
    total_chains: int = Field(..., description="總產業鏈數")
    total_mappings: int = Field(..., description="總股票關聯數")
    chain_stock_counts: dict = Field(default_factory=dict,
                                    description="各產業鏈的股票數量")


class CustomCategoryStatistics(BaseModel):
    """自定義分類統計信息"""
    total_categories: int = Field(..., description="總分類數")
    total_mappings: int = Field(..., description="總股票關聯數")
    by_user: dict = Field(default_factory=dict,
                         description="各用戶的分類數量")
