"""
Institutional Investor API Endpoints
法人買賣超 API 端點
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, timedelta

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.services.institutional_investor_service import InstitutionalInvestorService
from app.schemas.institutional_investor import (
    InstitutionalInvestorResponse,
    InstitutionalInvestorSummary,
    InstitutionalInvestorStats,
    InvestorType,
    SyncTaskResponse
)
from app.tasks.institutional_investor_sync import (
    sync_single_stock_institutional,
    sync_institutional_investors
)
from app.core.rate_limit import limiter, RateLimits
from app.utils.logging import api_log

router = APIRouter(prefix="/institutional", tags=["Institutional Investors"])


@router.get("/stocks/{stock_id}/data", response_model=List[InstitutionalInvestorResponse])
@limiter.limit(RateLimits.DATA_FETCH)
async def get_stock_institutional_data(
    request: Request,
    stock_id: str,
    start_date: date = Query(..., description="開始日期"),
    end_date: date = Query(..., description="結束日期"),
    investor_type: Optional[InvestorType] = Query(None, description="法人類型"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查詢指定股票的法人買賣超數據

    - **stock_id**: 股票代碼（如 2330）
    - **start_date**: 開始日期
    - **end_date**: 結束日期
    - **investor_type**: 法人類型（可選）
    """
    try:
        service = InstitutionalInvestorService(db)

        data = service.get_stock_data(
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date,
            investor_type=investor_type
        )

        api_log.log_operation(
            "read", "institutional_data", stock_id, current_user.id, success=True
        )

        return data

    except Exception as e:
        api_log.log_operation(
            "read", "institutional_data", stock_id, current_user.id, success=False
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch institutional data: {str(e)}"
        )


@router.get("/stocks/{stock_id}/summary", response_model=InstitutionalInvestorSummary)
@limiter.limit(RateLimits.GENERAL_READ)
async def get_stock_institutional_summary(
    request: Request,
    stock_id: str,
    target_date: date = Query(..., description="目標日期"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查詢指定日期的法人買賣超摘要

    返回該日期所有法人類型的買賣超統計
    """
    try:
        service = InstitutionalInvestorService(db)

        summary = service.get_summary(stock_id, target_date)

        api_log.log_operation(
            "read", "institutional_summary", stock_id, current_user.id, success=True
        )

        return summary

    except Exception as e:
        api_log.log_operation(
            "read", "institutional_summary", stock_id, current_user.id, success=False
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch summary: {str(e)}"
        )


@router.get("/stocks/{stock_id}/stats", response_model=InstitutionalInvestorStats)
@limiter.limit(RateLimits.GENERAL_READ)
async def get_stock_institutional_stats(
    request: Request,
    stock_id: str,
    investor_type: InvestorType = Query(..., description="法人類型"),
    start_date: date = Query(..., description="開始日期"),
    end_date: date = Query(..., description="結束日期"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查詢指定期間的法人買賣超統計

    返回期間內的總買進、總賣出、淨買賣超、買超天數等統計
    """
    try:
        service = InstitutionalInvestorService(db)

        stats = service.get_stats(
            stock_id=stock_id,
            investor_type=investor_type,
            start_date=start_date,
            end_date=end_date
        )

        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data found for the specified period"
            )

        api_log.log_operation(
            "read", "institutional_stats", stock_id, current_user.id, success=True
        )

        return stats

    except HTTPException:
        raise
    except Exception as e:
        api_log.log_operation(
            "read", "institutional_stats", stock_id, current_user.id, success=False
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch stats: {str(e)}"
        )


@router.get("/rankings/{target_date}", response_model=List[InstitutionalInvestorResponse])
@limiter.limit(RateLimits.GENERAL_READ)
async def get_institutional_rankings(
    request: Request,
    target_date: date,
    investor_type: InvestorType = Query(..., description="法人類型"),
    limit: int = Query(50, ge=1, le=200, description="返回數量"),
    order: str = Query("desc", regex="^(asc|desc)$", description="排序方式"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查詢指定日期的法人買賣超排行

    - **target_date**: 目標日期
    - **investor_type**: 法人類型
    - **limit**: 返回數量（1-200）
    - **order**: 排序方式（desc=買超在前，asc=賣超在前）
    """
    try:
        service = InstitutionalInvestorService(db)

        rankings = service.get_top_stocks(
            target_date=target_date,
            investor_type=investor_type,
            limit=limit,
            order=order
        )

        api_log.log_operation(
            "read", "institutional_rankings", None, current_user.id, success=True
        )

        return rankings

    except Exception as e:
        api_log.log_operation(
            "read", "institutional_rankings", None, current_user.id, success=False
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch rankings: {str(e)}"
        )


@router.post("/sync/{stock_id}", response_model=SyncTaskResponse)
@limiter.limit(RateLimits.GENERAL_WRITE)
async def sync_stock_institutional_data(
    request: Request,
    stock_id: str,
    start_date: Optional[str] = Query(None, description="開始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="結束日期 (YYYY-MM-DD)"),
    force: bool = Query(False, description="是否強制覆蓋現有數據"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    觸發單一股票的法人買賣超數據同步（異步）

    - **stock_id**: 股票代碼
    - **start_date**: 開始日期（可選，默認為最新數據日期的下一天）
    - **end_date**: 結束日期（可選，默認為今天）
    - **force**: 是否強制覆蓋現有數據

    **限制**: 每小時最多 10 次
    """
    try:
        # 觸發 Celery 異步任務
        task = sync_single_stock_institutional.apply_async(
            kwargs={
                'stock_id': stock_id,
                'start_date': start_date,
                'end_date': end_date,
                'force': force
            }
        )

        api_log.log_operation(
            "sync", "institutional_data", stock_id, current_user.id, success=True
        )

        return SyncTaskResponse(
            task_id=task.id,
            status="pending",
            message=f"Sync task started for {stock_id}"
        )

    except Exception as e:
        api_log.log_operation(
            "sync", "institutional_data", stock_id, current_user.id, success=False
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start sync task: {str(e)}"
        )


@router.post("/sync/batch", response_model=SyncTaskResponse)
@limiter.limit("3/hour")
async def sync_batch_institutional_data(
    request: Request,
    stock_ids: List[str] = Query(..., description="股票代碼列表"),
    days: int = Query(7, ge=1, le=90, description="同步最近 N 天"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    批量同步多個股票的法人買賣超數據（異步）

    - **stock_ids**: 股票代碼列表
    - **days**: 同步最近 N 天（1-90）

    **限制**: 每小時最多 3 次（避免過度使用 API）
    """
    try:
        # 觸發 Celery 異步任務
        task = sync_institutional_investors.apply_async(
            kwargs={
                'stock_ids': stock_ids,
                'days': days
            }
        )

        api_log.log_operation(
            "sync", "institutional_batch", None, current_user.id, success=True
        )

        return SyncTaskResponse(
            task_id=task.id,
            status="pending",
            message=f"Batch sync task started for {len(stock_ids)} stocks"
        )

    except Exception as e:
        api_log.log_operation(
            "sync", "institutional_batch", None, current_user.id, success=False
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start batch sync: {str(e)}"
        )


@router.get("/status/latest-date")
@limiter.limit(RateLimits.GENERAL_READ)
async def get_latest_data_date(
    request: Request,
    stock_id: Optional[str] = Query(None, description="股票代碼（可選）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查詢最新數據日期

    - **stock_id**: 股票代碼（可選，如果不提供則返回全局最新日期）
    """
    try:
        service = InstitutionalInvestorService(db)
        latest_date = service.get_latest_date(stock_id)

        return {
            "stock_id": stock_id or "all",
            "latest_date": latest_date.strftime('%Y-%m-%d') if latest_date else None
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get latest date: {str(e)}"
        )
