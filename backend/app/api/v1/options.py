"""
Option API Endpoints
選擇權 API 端點

提供選擇權相關數據查詢功能：
- 選擇權因子查詢
- 合約列表查詢
- Option Chain 構建
- 市場情緒指標
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.option import (
    OptionContractRepository,
    OptionDailyFactorRepository,
    OptionSyncConfigRepository
)
from app.schemas.option import (
    OptionContract,
    OptionDailyFactor,
    OptionChainResponse,
    OptionFactorSummary,
    OptionStageInfo,
    OptionSyncStatus,
    OptionChainItem
)
from app.core.rate_limit import limiter, RateLimits
from app.utils.logging import api_log
from app.services.shioaji_client import ShioajiClient
from app.services.option_service import OptionService
from loguru import logger

router = APIRouter(prefix="/options", tags=["Options"])


def get_option_service(db: Session = Depends(get_db)) -> OptionService:
    """Dependency to get OptionService instance"""
    return OptionService(db)


@router.get("/stage", response_model=OptionStageInfo)
@limiter.limit(RateLimits.GENERAL_READ)
async def get_stage_info(
    request: Request,
    current_user: User = Depends(get_current_user),
    option_service: OptionService = Depends(get_option_service)
):
    """
    獲取當前階段資訊

    返回：
    - 當前階段（1/2/3）
    - 啟用的標的物列表
    - 功能狀態（分鐘線、Greeks）
    - 可用因子列表
    """
    try:
        return option_service.get_stage_info()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stage info: {str(e)}"
        )


@router.get("/contracts", response_model=List[OptionContract])
@limiter.limit(RateLimits.DATA_FETCH)
async def get_contracts(
    request: Request,
    underlying_id: Optional[str] = Query(None, description="標的代碼（如 TX）"),
    option_type: Optional[str] = Query(None, description="選擇權類型（CALL/PUT）"),
    is_active: Optional[str] = Query("active", description="狀態篩選"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查詢選擇權合約列表

    參數：
    - **underlying_id**: 標的代碼（可選）
    - **option_type**: CALL 或 PUT（可選）
    - **is_active**: active/expired/exercised
    - **skip**: 分頁偏移
    - **limit**: 每頁數量（最多 1000）
    """
    try:
        contracts = OptionContractRepository.get_all(
            db=db,
            skip=skip,
            limit=limit,
            underlying_id=underlying_id,
            is_active=is_active,
            option_type=option_type
        )

        api_log.log_operation(
            "read", "option_contracts", underlying_id or "all", current_user.id, success=True
        )

        return contracts

    except Exception as e:
        api_log.log_operation(
            "read", "option_contracts", underlying_id or "all", current_user.id, success=False
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch contracts: {str(e)}"
        )


@router.get("/contracts/{underlying_id}/expiries", response_model=List[date])
@limiter.limit(RateLimits.GENERAL_READ)
async def get_expiry_dates(
    request: Request,
    underlying_id: str,
    is_active: Optional[str] = Query("active", description="狀態篩選"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    獲取標的物的所有到期日

    返回該標的物所有可用的選擇權到期日列表
    """
    try:
        expiry_dates = OptionContractRepository.get_expiry_dates(
            db=db,
            underlying_id=underlying_id,
            is_active=is_active
        )

        return expiry_dates

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch expiry dates: {str(e)}"
        )


@router.get("/chain/{underlying_id}", response_model=OptionChainResponse)
@limiter.limit(RateLimits.DATA_FETCH)
async def get_option_chain(
    request: Request,
    underlying_id: str,
    expiry_date: date = Query(..., description="到期日"),
    current_user: User = Depends(get_current_user),
    option_service: OptionService = Depends(get_option_service)
):
    """
    獲取 Option Chain

    返回指定標的物和到期日的所有選擇權合約（CALL 和 PUT）

    Option Chain 格式：
    - calls: CALL 合約列表（按履約價排序）
    - puts: PUT 合約列表（按履約價排序）
    - spot_price: 標的現價（如有）
    """
    try:
        # 使用 Service 層構建 Option Chain
        result = option_service.get_option_chain(
            underlying_id=underlying_id,
            expiry_date=expiry_date
        )

        api_log.log_operation(
            "read", "option_chain", f"{underlying_id}_{expiry_date}", current_user.id, success=True
        )

        return result

    except ValueError as e:
        # Service 層拋出的業務邏輯錯誤
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        api_log.log_operation(
            "read", "option_chain", f"{underlying_id}_{expiry_date}", current_user.id, success=False
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch option chain: {str(e)}"
        )


@router.get("/factors/{underlying_id}", response_model=List[OptionDailyFactor])
@limiter.limit(RateLimits.DATA_FETCH)
async def get_daily_factors(
    request: Request,
    underlying_id: str,
    start_date: Optional[date] = Query(None, description="開始日期"),
    end_date: Optional[date] = Query(None, description="結束日期"),
    limit: int = Query(100, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查詢選擇權每日因子

    返回指定標的物的每日因子數據（PCR、ATM IV 等）

    參數：
    - **underlying_id**: 標的代碼（如 TX）
    - **start_date**: 開始日期（可選）
    - **end_date**: 結束日期（可選）
    - **limit**: 最多返回筆數（預設 100，最多 365）
    """
    try:
        factors = OptionDailyFactorRepository.get_by_underlying(
            db=db,
            underlying_id=underlying_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        api_log.log_operation(
            "read", "option_factors", underlying_id, current_user.id, success=True
        )

        return factors

    except Exception as e:
        api_log.log_operation(
            "read", "option_factors", underlying_id, current_user.id, success=False
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch daily factors: {str(e)}"
        )


@router.get("/factors/{underlying_id}/latest", response_model=OptionDailyFactor)
@limiter.limit(RateLimits.GENERAL_READ)
async def get_latest_factor(
    request: Request,
    underlying_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    獲取最新的選擇權因子

    返回該標的物最新一筆因子數據
    """
    try:
        factor = OptionDailyFactorRepository.get_latest(db, underlying_id)

        if not factor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No factor data found for {underlying_id}"
            )

        return factor

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch latest factor: {str(e)}"
        )


@router.get("/factors/{underlying_id}/summary", response_model=OptionFactorSummary)
@limiter.limit(RateLimits.GENERAL_READ)
async def get_factor_summary(
    request: Request,
    underlying_id: str,
    target_date: Optional[date] = Query(None, description="目標日期（預設為最新）"),
    current_user: User = Depends(get_current_user),
    option_service: OptionService = Depends(get_option_service)
):
    """
    獲取選擇權因子摘要（含市場情緒）

    返回：
    - 基礎因子（PCR、ATM IV）
    - 進階因子（IV Skew、Max Pain，如有）
    - 市場情緒指標（基於 PCR 自動判斷）
    """
    try:
        result = option_service.get_factor_summary(
            underlying_id=underlying_id,
            target_date=target_date
        )
        return result

    except ValueError as e:
        # Service 層拋出的業務邏輯錯誤
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch factor summary: {str(e)}"
        )


@router.get("/sync-status", response_model=List[OptionSyncStatus])
@limiter.limit(RateLimits.GENERAL_READ)
async def get_sync_status(
    request: Request,
    current_user: User = Depends(get_current_user),
    option_service: OptionService = Depends(get_option_service)
):
    """
    獲取選擇權數據同步狀態

    返回所有啟用標的物的同步狀態
    """
    try:
        return option_service.get_sync_status()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch sync status: {str(e)}"
        )
