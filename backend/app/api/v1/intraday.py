"""
Intraday Data API

分鐘級股票數據的 API 端點
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.stock_minute_price_service import StockMinutePriceService
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.core.rate_limit import limiter, RateLimits
from app.utils.logging import api_log
from loguru import logger

router = APIRouter(prefix="/intraday", tags=["Intraday Data"])


def _handle_error(operation: str, error: Exception, default_message: str) -> HTTPException:
    """統一錯誤處理"""
    logger.error(f"{operation} failed: {str(error)}")
    if isinstance(error, HTTPException):
        raise error
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=default_message
    )


@router.get("/ohlcv/{stock_id}")
@limiter.limit(RateLimits.DATA_FETCH)
async def get_intraday_ohlcv(
    request: Request,
    stock_id: str,
    start_datetime: Optional[str] = Query(None, description="開始時間 (YYYY-MM-DD HH:MM:SS)"),
    end_datetime: Optional[str] = Query(None, description="結束時間 (YYYY-MM-DD HH:MM:SS)"),
    timeframe: str = Query('1min', description="時間粒度（1min/5min/15min/30min/60min/1day）"),
    limit: int = Query(10000, le=10000, description="最大筆數"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    獲取分鐘級 OHLCV 數據

    - **stock_id**: 股票代碼（如 '2330'）
    - **start_datetime**: 開始時間（可選，格式：YYYY-MM-DD HH:MM:SS）
    - **end_datetime**: 結束時間（可選，格式：YYYY-MM-DD HH:MM:SS）
    - **timeframe**: 時間粒度（1min/5min/15min/30min/60min/1day）
    - **limit**: 最大筆數（預設 10000，最大 10000）

    Returns:
        {
            "stock_id": "2330",
            "timeframe": "1min",
            "data": {
                "2024-01-01 09:00:00": {
                    "open": 590.0,
                    "high": 592.0,
                    "low": 589.0,
                    "close": 591.0,
                    "volume": 1000000
                },
                ...
            },
            "count": 100
        }
    """
    try:
        service = StockMinutePriceService(db)

        # 驗證時間粒度
        if not service.validate_timeframe(timeframe):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid timeframe. Must be one of: 1min, 5min, 15min, 30min, 60min, 1day"
            )

        # 解析時間參數
        start_dt = None
        end_dt = None

        if start_datetime:
            try:
                start_dt = datetime.fromisoformat(start_datetime)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_datetime format. Use YYYY-MM-DD HH:MM:SS"
                )

        if end_datetime:
            try:
                end_dt = datetime.fromisoformat(end_datetime)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_datetime format. Use YYYY-MM-DD HH:MM:SS"
                )

        # 查詢數據
        result = service.get_intraday_ohlcv(
            stock_id, start_dt, end_dt, timeframe, limit
        )

        if result["count"] == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for {stock_id} ({timeframe})"
            )

        api_log.log_operation(
            "read", "intraday_ohlcv", stock_id, current_user.id,
            success=True,
            metadata={"timeframe": timeframe, "count": result["count"]}
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error("Get OHLCV", e, "Failed to fetch OHLCV data")


@router.get("/latest/{stock_id}")
@limiter.limit(RateLimits.DATA_FETCH)
async def get_latest_intraday_price(
    request: Request,
    stock_id: str,
    timeframe: str = Query('1min', description="時間粒度"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    獲取最新分鐘價格

    - **stock_id**: 股票代碼
    - **timeframe**: 時間粒度（預設 1min）

    Returns:
        {
            "stock_id": "2330",
            "datetime": "2024-01-01 13:30:00",
            "timeframe": "1min",
            "open": 590.0,
            "high": 592.0,
            "low": 589.0,
            "close": 591.0,
            "volume": 1000000,
            "created_at": "2024-01-01 13:31:00"
        }
    """
    try:
        service = StockMinutePriceService(db)

        # 驗證時間粒度
        if not service.validate_timeframe(timeframe):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid timeframe. Must be one of: 1min, 5min, 15min, 30min, 60min, 1day"
            )

        price = service.get_latest_price(stock_id, timeframe)

        if not price:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No latest price found for {stock_id} ({timeframe})"
            )

        api_log.log_operation(
            "read", "latest_intraday_price", stock_id, current_user.id,
            success=True,
            metadata={"timeframe": timeframe}
        )

        return price

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error("Get latest price", e, "Failed to fetch latest price")


@router.get("/coverage/{stock_id}")
@limiter.limit(RateLimits.DATA_FETCH)
async def get_data_coverage(
    request: Request,
    stock_id: str,
    timeframe: str = Query('1min', description="時間粒度"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    獲取股票數據覆蓋範圍

    - **stock_id**: 股票代碼
    - **timeframe**: 時間粒度

    Returns:
        {
            "stock_id": "2330",
            "timeframe": "1min",
            "min_date": "2024-01-01 09:00:00",
            "max_date": "2024-01-10 13:30:00",
            "count": 5000
        }
    """
    try:
        service = StockMinutePriceService(db)

        coverage = service.get_data_coverage(stock_id, timeframe)

        if not coverage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for {stock_id} ({timeframe})"
            )

        api_log.log_operation(
            "read", "data_coverage", stock_id, current_user.id,
            success=True
        )

        return coverage

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error("Get coverage", e, "Failed to fetch data coverage")


@router.post("/sync")
@limiter.limit("5/hour")  # 嚴格限制同步請求
async def sync_intraday_data(
    request: Request,
    stock_id: str = Query(..., description="股票代碼"),
    timeframe: str = Query('1min', description="時間粒度"),
    days_back: int = Query(7, ge=1, le=30, description="回溯天數（1-30）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    手動觸發數據同步（需登入）

    ⚠️ 此端點受嚴格速率限制：5 requests/hour

    - **stock_id**: 股票代碼
    - **timeframe**: 時間粒度
    - **days_back**: 回溯天數（預設 7 天，最多 30 天）

    Returns:
        {
            "status": "success",
            "stock_id": "2330",
            "timeframe": "1min",
            "records_synced": 100,
            "timestamp": "2024-01-01 14:00:00"
        }
    """
    try:
        service = StockMinutePriceService(db)

        # 驗證時間粒度
        if not service.validate_timeframe(timeframe):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid timeframe. Must be one of: 1min, 5min, 15min, 30min, 60min, 1day"
            )

        # 計算同步範圍
        end_datetime = datetime.now(timezone.utc)
        start_datetime = end_datetime - timedelta(days=days_back)

        logger.info(
            f"Manual sync triggered by user {current_user.id}: "
            f"{stock_id} ({timeframe}), {days_back} days back"
        )

        # 執行同步
        count = service.sync_stock_minute_data(
            stock_id, start_datetime, end_datetime, timeframe
        )

        api_log.log_operation(
            "create", "sync_intraday_data", stock_id, current_user.id,
            success=True,
            metadata={"timeframe": timeframe, "days_back": days_back, "count": count}
        )

        return {
            "status": "success",
            "stock_id": stock_id,
            "timeframe": timeframe,
            "records_synced": count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        api_log.log_operation(
            "create", "sync_intraday_data", stock_id, current_user.id,
            success=False,
            error=str(e)
        )
        raise _handle_error("Sync data", e, "Failed to sync intraday data")


@router.get("/statistics")
@limiter.limit(RateLimits.DATA_FETCH)
async def get_statistics(
    request: Request,
    stock_id: Optional[str] = Query(None, description="股票代碼（可選）"),
    timeframe: Optional[str] = Query(None, description="時間粒度（可選）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    獲取統計資訊

    - **stock_id**: 股票代碼（可選，不提供則統計所有股票）
    - **timeframe**: 時間粒度（可選，不提供則統計所有粒度）

    Returns:
        {
            "total_records": 1000000,
            "stock_id": "2330" (if provided),
            "timeframe": "1min" (if provided)
        }
    """
    try:
        service = StockMinutePriceService(db)

        # 驗證時間粒度
        if timeframe and not service.validate_timeframe(timeframe):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid timeframe. Must be one of: 1min, 5min, 15min, 30min, 60min, 1day"
            )

        stats = service.get_statistics(stock_id, timeframe)

        api_log.log_operation(
            "read", "intraday_statistics", None, current_user.id,
            success=True
        )

        return stats

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error("Get statistics", e, "Failed to fetch statistics")
