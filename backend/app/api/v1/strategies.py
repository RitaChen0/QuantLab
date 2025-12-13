"""
Strategies API Routes
Handles trading strategy CRUD operations
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Request
from typing import Optional
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.strategy import StrategyStatus
from app.schemas.strategy import (
    Strategy,
    StrategyDetail,
    StrategyCreate,
    StrategyUpdate,
    StrategyListResponse,
    StrategyCodeValidationRequest,
    StrategyCodeValidationResponse,
)
from app.services.strategy_service import StrategyService
from app.core.config import settings
from app.core.rate_limit import limiter, RateLimits
from app.utils.logging import api_log
from loguru import logger

router = APIRouter()


def _handle_error(operation: str, error: Exception, user_message: str) -> HTTPException:
    """
    Handle errors with appropriate logging and user-friendly messages

    Args:
        operation: Description of the operation that failed
        error: The caught exception
        user_message: User-friendly error message

    Returns:
        HTTPException with appropriate status and message
    """
    # Log detailed error for debugging
    logger.error(f"{operation} failed: {str(error)}", exc_info=settings.DEBUG)

    # Return user-friendly message in production, detailed in development
    detail = str(error) if settings.DEBUG else user_message

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=detail
    )


@router.get("/", response_model=StrategyListResponse)
async def list_strategies(
    status_filter: Optional[StrategyStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    取得當前用戶的策略列表

    Args:
        status_filter: 依狀態過濾（draft, active, archived）
        page: 頁碼
        page_size: 每頁筆數

    Returns:
        策略列表與分頁資訊
    """
    try:
        service = StrategyService(db)
        skip = (page - 1) * page_size

        strategies, total = service.get_user_strategies(
            user_id=current_user.id,
            status_filter=status_filter,
            skip=skip,
            limit=page_size
        )

        api_log.log_operation(
            "list",
            "strategy",
            user_id=current_user.id,
            success=True,
            count=len(strategies),
            total=total,
            page=page
        )

        return StrategyListResponse(
            strategies=strategies,
            total=total,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        raise _handle_error(
            "List strategies",
            e,
            "Failed to retrieve strategies. Please try again later."
        )


@router.post("/", response_model=StrategyDetail, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.STRATEGY_CREATE)
async def create_strategy(
    request: Request,
    strategy_create: StrategyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    建立新策略

    Args:
        strategy_create: 策略建立資料

    Returns:
        已建立的策略詳情
    """
    try:
        service = StrategyService(db)
        strategy = service.create_strategy(
            user_id=current_user.id,
            strategy_create=strategy_create
        )

        api_log.log_operation(
            "create",
            "strategy",
            entity_id=strategy.id,
            user_id=current_user.id,
            success=True,
            name=strategy.name
        )

        return strategy

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error(
            "Create strategy",
            e,
            "Failed to create strategy. Please try again later."
        )


@router.get("/{strategy_id}", response_model=StrategyDetail)
async def get_strategy(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    取得策略詳情

    Args:
        strategy_id: 策略 ID

    Returns:
        策略完整資訊（包含代碼）
    """
    try:
        service = StrategyService(db)
        strategy = service.get_strategy(
            strategy_id=strategy_id,
            user_id=current_user.id
        )

        api_log.log_operation(
            "retrieve",
            "strategy",
            entity_id=strategy_id,
            user_id=current_user.id,
            success=True
        )

        return strategy

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error(
            f"Get strategy {strategy_id}",
            e,
            "Failed to retrieve strategy. Please try again later."
        )


@router.put("/{strategy_id}", response_model=StrategyDetail)
@limiter.limit(RateLimits.STRATEGY_UPDATE)
async def update_strategy(
    request: Request,
    strategy_id: int,
    strategy_update: StrategyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新策略

    Args:
        strategy_id: 策略 ID
        strategy_update: 更新資料

    Returns:
        更新後的策略詳情
    """
    try:
        service = StrategyService(db)
        strategy = service.update_strategy(
            strategy_id=strategy_id,
            user_id=current_user.id,
            strategy_update=strategy_update
        )

        api_log.log_operation(
            "update",
            "strategy",
            entity_id=strategy_id,
            user_id=current_user.id,
            success=True
        )

        return strategy

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error(
            f"Update strategy {strategy_id}",
            e,
            "Failed to update strategy. Please try again later."
        )


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    刪除策略

    Args:
        strategy_id: 策略 ID

    Returns:
        無內容（204）
    """
    try:
        service = StrategyService(db)
        service.delete_strategy(
            strategy_id=strategy_id,
            user_id=current_user.id
        )

        api_log.log_operation(
            "delete",
            "strategy",
            entity_id=strategy_id,
            user_id=current_user.id,
            success=True
        )

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error(
            f"Delete strategy {strategy_id}",
            e,
            "Failed to delete strategy. Please try again later."
        )


@router.post("/{strategy_id}/clone", response_model=StrategyDetail, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.STRATEGY_CREATE)
async def clone_strategy(
    request: Request,
    strategy_id: int,
    name: Optional[str] = Body(None, embed=True, description="New strategy name"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    複製策略

    Args:
        strategy_id: 要複製的策略 ID
        name: 新策略名稱（選填，預設為 "Copy of {原策略名稱}"）

    Returns:
        新建立的策略詳情
    """
    try:
        service = StrategyService(db)

        # Get original strategy
        original = service.get_strategy(
            strategy_id=strategy_id,
            user_id=current_user.id
        )

        # Create new strategy from original
        new_name = name or f"Copy of {original.name}"
        strategy_create = StrategyCreate(
            name=new_name,
            description=original.description,
            code=original.code,
            parameters=original.parameters,
            engine_type=original.engine_type,  # 複製引擎類型（確保驗證正確）
            status=StrategyStatus.DRAFT
        )

        # create_strategy 會自動驗證代碼安全性
        # 即使原策略代碼包含後來被禁止的函數，克隆時會重新驗證
        cloned = service.create_strategy(
            user_id=current_user.id,
            strategy_create=strategy_create
        )

        api_log.log_operation(
            "clone",
            "strategy",
            entity_id=cloned.id,
            user_id=current_user.id,
            success=True,
            source_id=strategy_id,
            name=cloned.name
        )

        return cloned

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error(
            f"Clone strategy {strategy_id}",
            e,
            "Failed to clone strategy. Please try again later."
        )


@router.post("/validate", response_model=StrategyCodeValidationResponse)
@limiter.limit(RateLimits.STRATEGY_VALIDATE)
async def validate_strategy_code(
    request: Request,
    validation_request: StrategyCodeValidationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    驗證策略代碼

    Args:
        request: 驗證請求（包含策略代碼）

    Returns:
        驗證結果
    """
    try:
        service = StrategyService(db)
        engine_type = validation_request.engine_type or 'backtrader'
        result = service.validate_strategy_code(validation_request.code, engine_type=engine_type)

        return StrategyCodeValidationResponse(
            valid=result["valid"],
            errors=[result["message"]] if not result["valid"] else None,
            warnings=None
        )

    except Exception as e:
        logger.error(f"Code validation error: {str(e)}")
        return StrategyCodeValidationResponse(
            valid=False,
            errors=[str(e)],
            warnings=None
        )
