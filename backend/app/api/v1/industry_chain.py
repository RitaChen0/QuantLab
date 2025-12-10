"""
Industry Chain API Routes

提供 FinMind 產業鏈和自定義產業分類的 API 端點
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.services.industry_chain_service import (
    IndustryChainService,
    CustomIndustryCategoryService
)
from app.schemas.industry_chain import (
    IndustryChainResponse,
    IndustryChainWithStocks,
    IndustryChainCreate,
    IndustryChainUpdate,
    StockIndustryChainCreate,
    StockIndustryChainBulkCreate,
    IndustryChainSearchRequest,
    IndustryChainStatistics,
    CustomIndustryCategoryCreate,
    CustomIndustryCategoryUpdate,
    CustomIndustryCategoryResponse,
    CustomIndustryCategoryWithStocks,
    CustomIndustryCategoryTree,
    StockCustomCategoryCreate,
    StockCustomCategoryBulkCreate,
    CustomCategorySearchRequest,
)
from app.core.rate_limit import limiter, RateLimits
from app.utils.logging import api_log
from loguru import logger


router = APIRouter(prefix="/industry-chain", tags=["Industry Chain"])


def _handle_error(operation: str, e: Exception, default_msg: str) -> HTTPException:
    """統一錯誤處理"""
    if isinstance(e, HTTPException):
        raise e
    logger.error(f"{operation} error: {str(e)}")
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=default_msg
    )


# ========== FinMind Industry Chain Endpoints ==========

@router.post("/sync", status_code=status.HTTP_200_OK)
@limiter.limit("10/hour")
async def sync_finmind_data(
    request: Request,
    force_refresh: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    從 FinMind API 同步產業鏈數據

    - **force_refresh**: 是否強制刷新（清除現有數據）
    """
    try:
        service = IndustryChainService(db)
        result = service.sync_finmind_industry_chains(force_refresh)

        api_log.log_operation(
            "sync", "industry_chain", None, current_user.id,
            success=True, details=result
        )

        return result
    except Exception as e:
        api_log.log_operation("sync", "industry_chain", None, current_user.id, success=False)
        raise _handle_error("Sync FinMind data", e, "Failed to sync industry chain data")


@router.get("/", response_model=List[IndustryChainResponse])
async def get_all_chains(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """獲取所有產業鏈列表"""
    try:
        service = IndustryChainService(db)
        chains = service.get_all_chains()
        return chains
    except Exception as e:
        raise _handle_error("Get all chains", e, "Failed to retrieve industry chains")


@router.get("/statistics", response_model=IndustryChainStatistics)
async def get_chain_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """獲取產業鏈統計信息"""
    try:
        service = IndustryChainService(db)
        stats = service.get_statistics()
        return stats
    except Exception as e:
        raise _handle_error("Get statistics", e, "Failed to retrieve statistics")


@router.post("/search", response_model=List[IndustryChainResponse])
async def search_chains(
    search_request: IndustryChainSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    搜尋產業鏈

    - **keyword**: 搜尋關鍵字
    - **stock_id**: 根據股票代號篩選
    """
    try:
        service = IndustryChainService(db)
        chains = service.search_chains(
            keyword=search_request.keyword,
            stock_id=search_request.stock_id
        )
        return chains
    except Exception as e:
        raise _handle_error("Search chains", e, "Failed to search industry chains")


@router.get("/{chain_name}", response_model=IndustryChainWithStocks)
async def get_chain_detail(
    chain_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """獲取產業鏈詳細信息（含股票列表）"""
    try:
        service = IndustryChainService(db)
        chain = service.get_chain_by_name(chain_name)

        if not chain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Industry chain '{chain_name}' not found"
            )

        return chain
    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error("Get chain detail", e, "Failed to retrieve chain details")


@router.get("/{chain_name}/stocks", response_model=List[str])
async def get_chain_stocks(
    chain_name: str,
    primary_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    獲取產業鏈中的股票列表

    - **primary_only**: 是否只返回主要產業鏈的股票
    """
    try:
        service = IndustryChainService(db)
        stocks = service.get_stocks_by_chain(chain_name, primary_only)
        return stocks
    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error("Get chain stocks", e, "Failed to retrieve stocks")


@router.post("/stocks/add", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def add_stock_to_chain(
    request: Request,
    stock_chain: StockIndustryChainCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """將股票添加到產業鏈"""
    try:
        service = IndustryChainService(db)
        result = service.add_stock_to_chain(
            stock_chain.stock_id,
            stock_chain.chain_name,
            stock_chain.is_primary
        )

        api_log.log_operation(
            "add_stock", "industry_chain", stock_chain.chain_name,
            current_user.id, success=True
        )

        return result
    except Exception as e:
        api_log.log_operation(
            "add_stock", "industry_chain", stock_chain.chain_name,
            current_user.id, success=False
        )
        raise _handle_error("Add stock to chain", e, "Failed to add stock")


# ========== Custom Industry Category Endpoints ==========

@router.get("/custom/categories", response_model=List[CustomIndustryCategoryResponse])
async def get_user_categories(
    parent_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    獲取當前用戶的所有自定義分類

    - **parent_id**: 父分類 ID（可選，用於獲取子分類）
    """
    try:
        service = CustomIndustryCategoryService(db)
        categories = service.get_user_categories(current_user.id, parent_id)
        return categories
    except Exception as e:
        raise _handle_error("Get user categories", e, "Failed to retrieve categories")


@router.get("/custom/categories/tree", response_model=List[CustomIndustryCategoryTree])
async def get_category_tree(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """獲取當前用戶的分類樹狀結構"""
    try:
        service = CustomIndustryCategoryService(db)
        tree = service.get_category_tree(current_user.id)
        return tree
    except Exception as e:
        raise _handle_error("Get category tree", e, "Failed to retrieve category tree")


@router.post("/custom/categories", response_model=CustomIndustryCategoryResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def create_category(
    request: Request,
    category_create: CustomIndustryCategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """創建新的自定義產業分類"""
    try:
        service = CustomIndustryCategoryService(db)
        category = service.create_category(
            user_id=current_user.id,
            category_name=category_create.category_name,
            description=category_create.description,
            parent_id=category_create.parent_id
        )

        api_log.log_operation(
            "create", "custom_category", category['id'],
            current_user.id, success=True
        )

        return category
    except HTTPException:
        raise
    except Exception as e:
        api_log.log_operation("create", "custom_category", None, current_user.id, success=False)
        raise _handle_error("Create category", e, "Failed to create category")


@router.get("/custom/categories/{category_id}", response_model=CustomIndustryCategoryWithStocks)
async def get_category_detail(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """獲取自定義分類詳細信息（含股票列表）"""
    try:
        service = CustomIndustryCategoryService(db)
        category = service.get_category_by_id(category_id, current_user.id)

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category {category_id} not found"
            )

        return category
    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error("Get category detail", e, "Failed to retrieve category")


@router.put("/custom/categories/{category_id}", response_model=CustomIndustryCategoryWithStocks)
@limiter.limit("30/hour")
async def update_category(
    request: Request,
    category_id: int,
    category_update: CustomIndustryCategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新自定義分類"""
    try:
        service = CustomIndustryCategoryService(db)
        category = service.update_category(
            category_id=category_id,
            user_id=current_user.id,
            category_name=category_update.category_name,
            description=category_update.description,
            parent_id=category_update.parent_id
        )

        api_log.log_operation(
            "update", "custom_category", category_id,
            current_user.id, success=True
        )

        return category
    except HTTPException:
        raise
    except Exception as e:
        api_log.log_operation("update", "custom_category", category_id, current_user.id, success=False)
        raise _handle_error("Update category", e, "Failed to update category")


@router.delete("/custom/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    cascade: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    刪除自定義分類

    - **cascade**: 是否級聯刪除子分類
    """
    try:
        service = CustomIndustryCategoryService(db)
        success = service.delete_category(category_id, current_user.id, cascade)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category {category_id} not found"
            )

        api_log.log_operation(
            "delete", "custom_category", category_id,
            current_user.id, success=True
        )

        return None
    except HTTPException:
        raise
    except Exception as e:
        api_log.log_operation("delete", "custom_category", category_id, current_user.id, success=False)
        raise _handle_error("Delete category", e, "Failed to delete category")


@router.post("/custom/categories/search", response_model=List[CustomIndustryCategoryResponse])
async def search_categories(
    search_request: CustomCategorySearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    搜尋自定義分類

    - **keyword**: 搜尋關鍵字
    - **stock_id**: 根據股票代號篩選
    """
    try:
        service = CustomIndustryCategoryService(db)
        categories = service.search_categories(
            user_id=current_user.id,
            keyword=search_request.keyword,
            stock_id=search_request.stock_id
        )
        return categories
    except Exception as e:
        raise _handle_error("Search categories", e, "Failed to search categories")


@router.get("/custom/categories/{category_id}/stocks", response_model=List[str])
async def get_category_stocks(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """獲取自定義分類中的股票列表"""
    try:
        service = CustomIndustryCategoryService(db)
        stocks = service.get_stocks_in_category(category_id)
        return stocks
    except Exception as e:
        raise _handle_error("Get category stocks", e, "Failed to retrieve stocks")


@router.post("/custom/stocks/add", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def add_stock_to_category(
    request: Request,
    stock_category: StockCustomCategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """將股票添加到自定義分類"""
    try:
        service = CustomIndustryCategoryService(db)
        result = service.add_stock_to_category(
            category_id=stock_category.category_id,
            stock_id=stock_category.stock_id,
            user_id=current_user.id
        )

        api_log.log_operation(
            "add_stock", "custom_category", stock_category.category_id,
            current_user.id, success=True
        )

        return result
    except HTTPException:
        raise
    except Exception as e:
        api_log.log_operation(
            "add_stock", "custom_category", stock_category.category_id,
            current_user.id, success=False
        )
        raise _handle_error("Add stock to category", e, "Failed to add stock")


@router.post("/custom/stocks/bulk-add", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def bulk_add_stocks_to_category(
    request: Request,
    bulk_create: StockCustomCategoryBulkCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """批量添加股票到自定義分類"""
    try:
        service = CustomIndustryCategoryService(db)
        result = service.bulk_add_stocks(
            category_id=bulk_create.category_id,
            stock_ids=bulk_create.stock_ids,
            user_id=current_user.id
        )

        api_log.log_operation(
            "bulk_add_stocks", "custom_category", bulk_create.category_id,
            current_user.id, success=True, details=result
        )

        return result
    except HTTPException:
        raise
    except Exception as e:
        api_log.log_operation(
            "bulk_add_stocks", "custom_category", bulk_create.category_id,
            current_user.id, success=False
        )
        raise _handle_error("Bulk add stocks", e, "Failed to add stocks")


@router.delete("/custom/stocks/remove", status_code=status.HTTP_204_NO_CONTENT)
async def remove_stock_from_category(
    category_id: int,
    stock_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """從自定義分類中移除股票"""
    try:
        service = CustomIndustryCategoryService(db)
        success = service.remove_stock_from_category(category_id, stock_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stock not found in category"
            )

        api_log.log_operation(
            "remove_stock", "custom_category", category_id,
            current_user.id, success=True
        )

        return None
    except HTTPException:
        raise
    except Exception as e:
        api_log.log_operation(
            "remove_stock", "custom_category", category_id,
            current_user.id, success=False
        )
        raise _handle_error("Remove stock from category", e, "Failed to remove stock")
