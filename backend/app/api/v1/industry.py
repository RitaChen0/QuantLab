"""
Industry API Endpoints

Provides industry classification and analysis endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import date

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.services.industry_service import IndustryService
from app.schemas.industry import (
    IndustryResponse,
    IndustryListResponse,
    IndustryTreeResponse,
    IndustryWithStocks,
    IndustryMetricsResponse,
    IndustryMetricsHistoricalResponse,
    IndustryPerformanceSummary,
    IndustryStatistics,
    HistoricalMetricPoint,
    IndustryComparisonResponse
)
from app.utils.logging import api_log
from loguru import logger

router = APIRouter(prefix="/industry", tags=["產業分析"])


def _handle_error(operation: str, error: Exception, user_message: str) -> HTTPException:
    """Centralized error handler."""
    logger.error(f"{operation} failed: {str(error)}", exc_info=True)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=user_message
    )


@router.get("/", response_model=IndustryListResponse)
async def get_industries(
    level: Optional[int] = Query(None, description="產業層級 (1=大類, 2=中類, 3=小類)"),
    parent_code: Optional[str] = Query(None, description="父產業代碼"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    獲取產業列表

    - **level**: 可選，篩選產業層級
    - **parent_code**: 可選，篩選父產業代碼

    返回所有符合條件的產業分類。
    """
    try:
        service = IndustryService(db)
        industries = service.get_all_industries(level=level, parent_code=parent_code)

        # Batch query stock counts to avoid N+1 problem
        industry_codes = [ind.code for ind in industries]
        stock_counts = service.repo.get_stock_counts_bulk(db, industry_codes)

        # Build response with stock counts
        response_industries = []
        for industry in industries:
            industry_dict = {
                "code": industry.code,
                "name_zh": industry.name_zh,
                "name_en": industry.name_en,
                "level": industry.level,
                "parent_code": industry.parent_code,
                "description": industry.description,
                "stock_count": stock_counts.get(industry.code, 0),
                "created_at": industry.created_at,
                "updated_at": industry.updated_at
            }
            response_industries.append(IndustryResponse(**industry_dict))

        api_log.log_operation(
            "list", "industries", None, current_user.id, success=True,
            metadata={"count": len(industries), "level": level, "parent_code": parent_code}
        )

        return IndustryListResponse(
            total=len(response_industries),
            industries=response_industries
        )

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error("Get industries", e, "Failed to retrieve industries")


@router.get("/tree", response_model=IndustryTreeResponse)
async def get_industry_tree(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    獲取產業樹狀結構

    返回完整的產業分類樹，包含所有層級和關係。
    """
    try:
        service = IndustryService(db)
        tree = service.get_industry_tree()

        api_log.log_operation(
            "get_tree", "industries", None, current_user.id, success=True
        )

        return IndustryTreeResponse(
            total=len(tree),
            tree=tree
        )

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error("Get industry tree", e, "Failed to retrieve industry tree")


@router.get("/{code}", response_model=IndustryResponse)
async def get_industry_detail(
    code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    獲取產業詳情

    返回指定產業代碼的詳細資訊。
    """
    try:
        service = IndustryService(db)
        industry = service.get_industry_by_code(code)

        if not industry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Industry {code} not found"
            )

        stock_count = service.repo.get_stock_count_by_industry(db, code)

        industry_dict = {
            "code": industry.code,
            "name_zh": industry.name_zh,
            "name_en": industry.name_en,
            "level": industry.level,
            "parent_code": industry.parent_code,
            "description": industry.description,
            "stock_count": stock_count,
            "created_at": industry.created_at,
            "updated_at": industry.updated_at
        }

        api_log.log_operation(
            "get", "industry", code, current_user.id, success=True
        )

        return IndustryResponse(**industry_dict)

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error("Get industry detail", e, f"Failed to retrieve industry {code}")


@router.get("/{code}/stocks", response_model=IndustryWithStocks)
async def get_industry_stocks(
    code: str,
    primary_only: bool = Query(False, description="只返回將此產業設為主要產業的股票"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    獲取產業的所有股票

    返回歸類到指定產業的所有股票代號。
    """
    try:
        service = IndustryService(db)
        industry = service.get_industry_by_code(code)

        if not industry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Industry {code} not found"
            )

        stocks = service.get_stocks_by_industry(code, primary_only=primary_only)

        stock_count = len(stocks)
        industry_dict = {
            "code": industry.code,
            "name_zh": industry.name_zh,
            "name_en": industry.name_en,
            "level": industry.level,
            "parent_code": industry.parent_code,
            "description": industry.description,
            "stock_count": stock_count,
            "created_at": industry.created_at,
            "updated_at": industry.updated_at
        }

        api_log.log_operation(
            "get_stocks", "industry", code, current_user.id, success=True,
            metadata={"stocks_count": stock_count, "primary_only": primary_only}
        )

        return IndustryWithStocks(
            industry=IndustryResponse(**industry_dict),
            stocks=stocks
        )

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error(
            "Get industry stocks", e, f"Failed to retrieve stocks for industry {code}"
        )


@router.get("/{code}/metrics", response_model=IndustryMetricsResponse)
async def get_industry_metrics(
    code: str,
    metric_date: Optional[str] = Query(None, description="數據日期 (YYYY-MM-DD)，默認為今天"),
    force_refresh: bool = Query(False, description="強制重新計算（跳過快取）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    獲取產業聚合財務指標

    計算並返回產業內所有股票的平均財務指標（ROE、EPS等）。
    """
    try:
        service = IndustryService(db)
        industry = service.get_industry_by_code(code)

        if not industry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Industry {code} not found"
            )

        # Parse date
        target_date = None
        if metric_date:
            try:
                target_date = date.fromisoformat(metric_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date format. Use YYYY-MM-DD"
                )

        # Calculate metrics
        metrics = service.calculate_industry_fundamental_metrics(
            code, metric_date=target_date, force_refresh=force_refresh
        )

        api_log.log_operation(
            "calculate_metrics", "industry", code, current_user.id, success=True,
            metadata={"date": metric_date, "force_refresh": force_refresh}
        )

        return IndustryMetricsResponse(**metrics)

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error(
            "Calculate industry metrics", e, f"Failed to calculate metrics for industry {code}"
        )


@router.get("/{code}/metrics/historical", response_model=IndustryMetricsHistoricalResponse)
async def get_industry_metrics_historical(
    code: str,
    metric_name: str = Query(..., description="指標名稱 (e.g., avg_ROE稅後)"),
    start_date: Optional[str] = Query(None, description="開始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="結束日期 (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    獲取產業歷史指標數據

    返回指定時間範圍內的產業聚合指標歷史數據。
    """
    try:
        service = IndustryService(db)
        industry = service.get_industry_by_code(code)

        if not industry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Industry {code} not found"
            )

        # Get historical data
        data = service.get_industry_metrics_historical(
            code, metric_name, start_date, end_date
        )

        api_log.log_operation(
            "get_historical_metrics", "industry", code, current_user.id, success=True,
            metadata={
                "metric_name": metric_name,
                "start_date": start_date,
                "end_date": end_date,
                "data_points": len(data)
            }
        )

        return IndustryMetricsHistoricalResponse(
            industry_code=code,
            metric_name=metric_name,
            data=[HistoricalMetricPoint(**d) for d in data]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error(
            "Get historical metrics", e,
            f"Failed to retrieve historical metrics for industry {code}"
        )


@router.get("/{code}/performance", response_model=IndustryPerformanceSummary)
async def get_industry_performance(
    code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    獲取產業績效摘要

    返回產業的完整績效摘要，包含最新財務指標。
    """
    try:
        service = IndustryService(db)
        performance = service.get_industry_performance_summary(code)

        if not performance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Industry {code} not found"
            )

        api_log.log_operation(
            "get_performance", "industry", code, current_user.id, success=True
        )

        return IndustryPerformanceSummary(**performance)

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error(
            "Get industry performance", e,
            f"Failed to retrieve performance for industry {code}"
        )


@router.get("/statistics/overview", response_model=IndustryStatistics)
async def get_industry_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    獲取產業資料庫統計

    返回產業分類資料庫的統計資訊。
    """
    try:
        service = IndustryService(db)
        stats = service.get_industry_statistics()

        api_log.log_operation(
            "get_statistics", "industry", None, current_user.id, success=True
        )

        return IndustryStatistics(**stats)

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error("Get industry statistics", e, "Failed to retrieve industry statistics")


@router.post("/compare", response_model=IndustryComparisonResponse)
async def compare_industries(
    industry_codes: List[str] = Query(..., description="產業代碼列表"),
    metric_name: str = Query(..., description="指標名稱"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    比較多個產業的指標

    比較多個產業在同一指標上的表現。
    """
    try:
        service = IndustryService(db)
        comparison = service.compare_industries(industry_codes, metric_name)

        api_log.log_operation(
            "compare", "industries", None, current_user.id, success=True,
            metadata={"industries": industry_codes, "metric": metric_name}
        )

        return IndustryComparisonResponse(**comparison)

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error(
            "Compare industries", e, f"Failed to compare industries on {metric_name}"
        )
