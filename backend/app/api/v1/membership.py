"""
會員等級管理 API

提供會員等級、現金、信用點數的管理功能。
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.api.dependencies import get_current_user, get_current_superuser
from app.models.user import User
from app.repositories.user import UserRepository
from app.core.member_limits import (
    MEMBER_LEVELS,
    MIN_LEVEL,
    MAX_LEVEL,
    get_level_name,
    get_all_limits,
    is_level_valid,
)
from app.core.rate_limit import limiter, RateLimits
from loguru import logger

router = APIRouter(prefix="/membership", tags=["會員管理"])


# ==================== Schemas ====================

class MemberLevelUpdate(BaseModel):
    """更新會員等級請求"""
    user_id: int
    member_level: int = Field(..., ge=MIN_LEVEL, le=MAX_LEVEL, description=f"會員等級 ({MIN_LEVEL}-{MAX_LEVEL})")


class BalanceUpdate(BaseModel):
    """更新餘額請求"""
    user_id: int
    cash: Optional[Decimal] = Field(None, ge=0, description="現金餘額")
    credit: Optional[Decimal] = Field(None, ge=0, description="信用點數")


class MemberInfo(BaseModel):
    """會員資訊回應"""
    user_id: int
    username: str
    email: str
    member_level: int
    level_name: str
    cash: Decimal
    credit: Decimal
    rate_limits: dict  # 各項操作的限制


class RateLimitStatus(BaseModel):
    """Rate Limit 狀態"""
    user_id: int
    member_level: int
    level_name: str
    limits: dict  # 各項操作的限制詳情


# ==================== API Endpoints ====================

@router.get("/me", response_model=MemberInfo)
@limiter.limit(RateLimits.GENERAL_READ)
async def get_my_membership_info(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查看自己的會員資訊

    包含等級、餘額、Rate Limit 等資訊。
    """
    # Get level name
    level_name = get_level_name(current_user.member_level)

    # Get all rate limits for this user
    rate_limits = get_all_limits(current_user.member_level)

    return MemberInfo(
        user_id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        member_level=current_user.member_level,
        level_name=level_name,
        cash=current_user.cash,
        credit=current_user.credit,
        rate_limits=rate_limits,
    )


@router.get("/limits", response_model=RateLimitStatus)
@limiter.limit(RateLimits.GENERAL_READ)
async def get_my_rate_limits(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    查看自己的 Rate Limit 詳情

    顯示當前等級下各項操作的限制。
    """
    level_name = get_level_name(current_user.member_level)

    # Get all rate limits for this user
    rate_limits = get_all_limits(current_user.member_level)

    # Format as detailed response
    limits_detail = {
        name: {
            "limit": limit,
            "description": f"{name}限制"
        }
        for name, limit in rate_limits.items()
    }

    return RateLimitStatus(
        user_id=current_user.id,
        member_level=current_user.member_level,
        level_name=level_name,
        limits=limits_detail,
    )


@router.patch("/level", response_model=dict)
@limiter.limit(RateLimits.GENERAL_WRITE)
async def update_member_level(
    request: Request,
    update_data: MemberLevelUpdate,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    更新用戶會員等級（僅管理員）

    允許的等級 (0-9)：
    - 0: 註冊會員
    - 1: 普通會員
    - 2: 中階會員
    - 3: 高階會員
    - 4: VIP會員
    - 5: 系統推廣會員
    - 6: 系統管理員1
    - 7: 系統管理員2
    - 8: 系統管理員3
    - 9: 創造者等級
    """
    user_repo = UserRepository()

    # Get target user
    target_user = user_repo.get_by_id(db, update_data.user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {update_data.user_id} not found"
        )

    # Validate level
    if not is_level_valid(update_data.member_level):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid member level. Valid levels: {MIN_LEVEL}-{MAX_LEVEL}"
        )

    # Update level
    old_level = target_user.member_level
    target_user.member_level = update_data.member_level
    db.commit()
    db.refresh(target_user)

    old_level_name = get_level_name(old_level)
    new_level_name = get_level_name(update_data.member_level)

    logger.info(
        f"Admin {current_user.username} updated user {target_user.username}'s "
        f"level from {old_level} ({old_level_name}) to "
        f"{update_data.member_level} ({new_level_name})"
    )

    return {
        "success": True,
        "message": f"User level updated from {old_level_name} to {new_level_name}",
        "user_id": target_user.id,
        "username": target_user.username,
        "old_level": old_level,
        "new_level": update_data.member_level,
    }


@router.patch("/balance", response_model=dict)
@limiter.limit(RateLimits.GENERAL_WRITE)
async def update_user_balance(
    request: Request,
    update_data: BalanceUpdate,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    更新用戶餘額（僅管理員）

    可以更新 cash（現金）和 credit（信用點數）。
    """
    user_repo = UserRepository()

    # Get target user
    target_user = user_repo.get_by_id(db, update_data.user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {update_data.user_id} not found"
        )

    # Update balances
    changes = []
    if update_data.cash is not None:
        old_cash = target_user.cash
        target_user.cash = update_data.cash
        changes.append(f"cash: {old_cash} → {update_data.cash}")

    if update_data.credit is not None:
        old_credit = target_user.credit
        target_user.credit = update_data.credit
        changes.append(f"credit: {old_credit} → {update_data.credit}")

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No balance fields provided to update"
        )

    db.commit()
    db.refresh(target_user)

    logger.info(
        f"Admin {current_user.username} updated user {target_user.username}'s "
        f"balance: {', '.join(changes)}"
    )

    return {
        "success": True,
        "message": f"User balance updated: {', '.join(changes)}",
        "user_id": target_user.id,
        "username": target_user.username,
        "cash": target_user.cash,
        "credit": target_user.credit,
    }


@router.get("/all-levels", response_model=list)
async def get_all_member_levels(request: Request):
    """
    獲取所有會員等級資訊

    返回各等級的名稱等資訊。
    """
    levels = []
    for level in range(MIN_LEVEL, MAX_LEVEL + 1):
        level_name = get_level_name(level)
        limits = get_all_limits(level)

        levels.append({
            "level": level,
            "name": level_name,
            "limits": limits,
            "description": f"Level {level} - {level_name}",
        })

    return levels
