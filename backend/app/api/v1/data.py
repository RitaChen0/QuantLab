"""
Stock Data API Routes
Handles stock data fetching from database and FinLab API
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, date as date_type
from decimal import Decimal
from app.schemas.stock import (
    StockInfo,
    StockSearchRequest,
    StockSearchResult,
    StockDataResponse,
    LatestPriceResponse,
)
from app.schemas.fundamental import (
    FundamentalIndicatorResponse,
    FundamentalIndicatorBatchRequest,
    FundamentalIndicatorBatchResponse,
    FundamentalIndicatorListResponse,
    FundamentalIndicatorCategoryResponse,
    FundamentalIndicatorInfo,
    FundamentalDataPoint,
    FundamentalSummary,
    FundamentalComparisonRequest,
    FundamentalComparisonResponse,
)
from app.schemas.stock_price import StockPriceCreate
from app.services.finlab_client import FinLabClient
from app.repositories.stock import StockRepository
from app.repositories.stock_price import StockPriceRepository
from app.db.session import get_db
from app.utils.cache import cache
from loguru import logger
import pandas as pd

router = APIRouter()


def get_finlab_client() -> FinLabClient:
    """
    Get FinLab client instance

    Uses the global token from settings
    """
    client = FinLabClient()

    if not client.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FinLab API service is not available. Please check API token configuration.",
        )

    return client


@router.get("/stocks", response_model=List[StockInfo])
async def get_stock_list(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=10000),
):
    """
    取得所有台股列表（從資料庫讀取）

    Returns:
        所有台股的基本資訊列表
    """
    try:
        # Try cache first
        cache_key = f"stock_list:db:{skip}:{limit}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            logger.info("Returning cached stock list from database")
            return cached_data

        # Fetch from database
        stocks = StockRepository.get_all(db, skip=skip, limit=limit, is_active='active')

        # Convert to response format
        result = [
            StockInfo(
                stock_id=stock.stock_id,
                name=stock.name,
                industry=stock.category,
                market=stock.market,
            )
            for stock in stocks
        ]

        # Cache for 1 hour
        cache.set(cache_key, result, expiry=3600)

        logger.info(f"Returned {len(result)} stocks from database")
        return result

    except Exception as e:
        logger.error(f"Failed to get stock list: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch stock list: {str(e)}",
        )


@router.post("/stocks/search", response_model=StockSearchResult)
async def search_stocks(
    request: StockSearchRequest,
    db: Session = Depends(get_db),
):
    """
    搜尋股票（從資料庫搜尋）

    Args:
        request: 搜尋請求（包含關鍵字）

    Returns:
        符合條件的股票列表
    """
    try:
        # Search in database
        stocks = StockRepository.search(db, request.keyword, skip=0, limit=50)

        stock_infos = [
            StockInfo(
                stock_id=stock.stock_id,
                name=stock.name,
                industry=stock.category,
                market=stock.market,
            )
            for stock in stocks
        ]

        logger.info(f"Found {len(stock_infos)} stocks matching '{request.keyword}'")

        return StockSearchResult(
            results=stock_infos,
            count=len(stock_infos),
        )

    except Exception as e:
        logger.error(f"Failed to search stocks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stock search failed: {str(e)}",
        )


@router.get("/price/{stock_id}", response_model=StockDataResponse)
async def get_stock_price(
    stock_id: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    finlab_client: FinLabClient = Depends(get_finlab_client),
):
    """
    取得股票價格資料

    Args:
        stock_id: 股票代碼
        start_date: 開始日期
        end_date: 結束日期

    Returns:
        股票價格資料
    """
    try:
        # Try cache first
        cache_key = f"price:{stock_id}:{start_date}:{end_date}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            logger.info(f"Returning cached price data for {stock_id}")
            return StockDataResponse(
                stock_id=stock_id,
                data=cached_data,
                cached=True,
            )

        # Fetch from FinLab
        price_df = finlab_client.get_price(
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Convert DataFrame to dict
        data = {
            str(date): float(price)
            for date, price in price_df[stock_id].items()
            if pd.notna(price)
        }

        # Cache for 10 minutes
        cache.set(cache_key, data, expiry=600)

        return StockDataResponse(
            stock_id=stock_id,
            data=data,
            cached=False,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to get price data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch price data: {str(e)}",
        )


@router.get("/ohlcv/{stock_id}", response_model=StockDataResponse)
async def get_stock_ohlcv(
    stock_id: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    finlab_client: FinLabClient = Depends(get_finlab_client),
):
    """
    取得股票 OHLCV 資料（優先從資料庫讀取）

    Args:
        stock_id: 股票代碼
        start_date: 開始日期
        end_date: 結束日期

    Returns:
        OHLCV 資料 (開盤/最高/最低/收盤/成交量)
    """
    try:
        # Try cache first
        cache_key = f"ohlcv:{stock_id}:{start_date}:{end_date}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            logger.info(f"Returning cached OHLCV data for {stock_id}")
            return StockDataResponse(
                stock_id=stock_id,
                data=cached_data,
                cached=True,
            )

        # Try database
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
            end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

            prices = StockPriceRepository.get_by_stock(
                db, stock_id, start_date=start, end_date=end, skip=0, limit=10000
            )

            if prices:
                # Convert to dict
                data = {
                    str(price.date): {
                        'open': float(price.open),
                        'high': float(price.high),
                        'low': float(price.low),
                        'close': float(price.close),
                        'volume': int(price.volume),
                    }
                    for price in prices
                }

                # Cache for 10 minutes
                cache.set(cache_key, data, expiry=600)

                logger.info(f"Returned {len(data)} OHLCV records from database for {stock_id}")
                return StockDataResponse(
                    stock_id=stock_id,
                    data=data,
                    cached=False,
                )
        except Exception as db_error:
            logger.warning(f"Database query failed, falling back to FinLab: {str(db_error)}")

        # Fallback to FinLab if database is empty
        ohlcv_df = finlab_client.get_ohlcv(
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Convert DataFrame to dict
        data = {
            str(date): {
                'open': float(row['open']) if pd.notna(row['open']) else None,
                'high': float(row['high']) if pd.notna(row['high']) else None,
                'low': float(row['low']) if pd.notna(row['low']) else None,
                'close': float(row['close']) if pd.notna(row['close']) else None,
                'volume': int(row['volume']) if pd.notna(row['volume']) else None,
            }
            for date, row in ohlcv_df.iterrows()
        }

        # Save to database for future use
        try:
            for date, row_data in data.items():
                price_create = StockPriceCreate(
                    stock_id=stock_id,
                    date=datetime.strptime(date, "%Y-%m-%d").date(),
                    open=Decimal(str(row_data['open'])) if row_data['open'] else Decimal('0'),
                    high=Decimal(str(row_data['high'])) if row_data['high'] else Decimal('0'),
                    low=Decimal(str(row_data['low'])) if row_data['low'] else Decimal('0'),
                    close=Decimal(str(row_data['close'])) if row_data['close'] else Decimal('0'),
                    volume=row_data['volume'] if row_data['volume'] else 0,
                    adj_close=None
                )
                StockPriceRepository.upsert(db, price_create)
            logger.info(f"Saved {len(data)} OHLCV records to database for {stock_id}")
        except Exception as save_error:
            logger.warning(f"Failed to save to database: {str(save_error)}")

        # Cache for 10 minutes
        cache.set(cache_key, data, expiry=600)

        logger.info(f"Returned {len(data)} OHLCV records from FinLab for {stock_id}")
        return StockDataResponse(
            stock_id=stock_id,
            data=data,
            cached=False,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to get OHLCV data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch OHLCV data: {str(e)}",
        )


@router.get("/latest-price/{stock_id}", response_model=LatestPriceResponse)
async def get_latest_price(
    stock_id: str,
    finlab_client: FinLabClient = Depends(get_finlab_client),
):
    """
    取得股票最新價格

    Args:
        stock_id: 股票代碼

    Returns:
        最新收盤價
    """
    try:
        # Try cache first (cache for 5 minutes)
        cache_key = f"latest_price:{stock_id}"
        cached_price = cache.get(cache_key)

        if cached_price is not None:
            logger.info(f"Returning cached latest price for {stock_id}")
            return LatestPriceResponse(
                stock_id=stock_id,
                price=cached_price,
            )

        # Fetch from FinLab
        price = finlab_client.get_latest_price(stock_id)

        if price is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock {stock_id} not found or no price data available",
            )

        # Cache for 5 minutes
        cache.set(cache_key, price, expiry=300)

        return LatestPriceResponse(
            stock_id=stock_id,
            price=price,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get latest price: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch latest price: {str(e)}",
        )


@router.delete("/cache/clear")
async def clear_cache(
    pattern: Optional[str] = Query(None, description="Cache key pattern to clear (e.g., 'price:*')"),
):
    """
    清除快取

    Args:
        pattern: 要清除的快取鍵模式（可選）

    Returns:
        清除的快取數量
    """
    try:
        if pattern:
            count = cache.clear_pattern(pattern)
        else:
            # Clear all stock data cache
            count = cache.clear_pattern("stock:*")
            count += cache.clear_pattern("price:*")
            count += cache.clear_pattern("ohlcv:*")
            count += cache.clear_pattern("latest_price:*")
            count += cache.clear_pattern("fundamental:*")

        return {
            "message": f"Cleared {count} cache entries",
            "count": count,
        }

    except Exception as e:
        logger.error(f"Failed to clear cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}",
        )


# ============ Fundamental Analysis Endpoints ============


@router.get("/fundamental/indicators", response_model=FundamentalIndicatorListResponse)
async def list_fundamental_indicators():
    """
    列出所有可用的財務指標

    Returns:
        財務指標列表，按類別分組
    """
    try:
        # Get indicators by category
        categories = FinLabClient.get_fundamental_indicator_categories()

        # Create indicator info list
        indicator_infos = []
        category_map = {
            "profitability": "獲利能力",
            "growth": "成長性",
            "efficiency": "經營效率",
            "financial_structure": "財務結構",
            "per_share": "每股指標",
        }

        name_en_map = {
            "ROE稅後": "ROE (After Tax)",
            "ROA稅後息前": "ROA (After Tax, Before Interest)",
            "營業毛利率": "Operating Gross Margin",
            "營業利益率": "Operating Profit Margin",
            "稅前淨利率": "Pre-tax Net Profit Margin",
            "稅後淨利率": "After-tax Net Profit Margin",
            "營收成長率": "Revenue Growth Rate",
            "稅前淨利成長率": "Pre-tax Net Profit Growth Rate",
            "稅後淨利成長率": "After-tax Net Profit Growth Rate",
            "應收帳款週轉率": "Accounts Receivable Turnover",
            "存貨週轉率": "Inventory Turnover",
            "總資產週轉率": "Total Asset Turnover",
            "負債比率": "Debt Ratio",
            "流動比率": "Current Ratio",
            "速動比率": "Quick Ratio",
            "每股淨值": "Book Value Per Share",
            "每股盈餘": "Earnings Per Share (EPS)",
            "每股營業額": "Revenue Per Share",
        }

        for category, indicators in categories.items():
            for indicator in indicators:
                indicator_infos.append(
                    FundamentalIndicatorInfo(
                        name=indicator,
                        name_en=name_en_map.get(indicator, indicator),
                        category=category_map.get(category, category),
                    )
                )

        # Calculate category counts
        category_counts = {
            category_map.get(cat, cat): len(indicators)
            for cat, indicators in categories.items()
        }

        logger.info(f"Returned {len(indicator_infos)} fundamental indicators")

        return FundamentalIndicatorListResponse(
            indicators=indicator_infos,
            count=len(indicator_infos),
            categories=category_counts,
        )

    except Exception as e:
        logger.error(f"Failed to list fundamental indicators: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list indicators: {str(e)}",
        )


@router.get("/fundamental/indicators/categories", response_model=FundamentalIndicatorCategoryResponse)
async def get_fundamental_indicator_categories():
    """
    取得按類別分組的財務指標

    Returns:
        分類與指標的映射
    """
    try:
        categories = FinLabClient.get_fundamental_indicator_categories()
        total_count = sum(len(indicators) for indicators in categories.values())

        logger.info(f"Returned {total_count} indicators in {len(categories)} categories")

        return FundamentalIndicatorCategoryResponse(
            categories=categories,
            total_count=total_count,
        )

    except Exception as e:
        logger.error(f"Failed to get indicator categories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get categories: {str(e)}",
        )


@router.get("/fundamental/{stock_id}/{indicator}", response_model=FundamentalIndicatorResponse)
async def get_fundamental_indicator(
    stock_id: str,
    indicator: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """
    取得股票的特定財務指標數據

    使用三層緩存架構:
    L1: Redis (24小時) - 最快
    L2: PostgreSQL (永久) - 持久化
    L3: FinLab API - 數據源

    Args:
        stock_id: 股票代號
        indicator: 財務指標名稱（如 'ROE稅後'）
        start_date: 開始日期
        end_date: 結束日期

    Returns:
        財務指標時間序列數據
    """
    try:
        # L1 Cache: Try Redis first
        cache_key = f"fundamental:{stock_id}:{indicator}:{start_date}:{end_date}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            logger.info(f"✅ L1 Cache HIT (Redis): {stock_id} - {indicator}")
            return cached_data

        # L2 Cache + L3 Source: Use FundamentalService
        from app.services.fundamental_service import FundamentalService
        service = FundamentalService(db)

        data_points = service.get_indicator_data(
            stock_id=stock_id,
            indicator=indicator,
            start_date=start_date,
            end_date=end_date,
            force_refresh=False  # Allow DB cache
        )

        response = FundamentalIndicatorResponse(
            indicator=indicator,
            stock_id=stock_id,
            data=data_points,
            count=len(data_points),
            start_date=data_points[0].date if data_points else None,
            end_date=data_points[-1].date if data_points else None,
        )

        # Cache in Redis for 24 hours (financial data changes quarterly)
        cache.set(cache_key, response, expiry=86400)
        logger.info(f"💾 Cached in Redis: {stock_id} - {indicator} ({len(data_points)} points)")

        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to get fundamental indicator: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch fundamental data: {str(e)}",
        )


@router.post("/fundamental/{stock_id}/batch", response_model=FundamentalIndicatorBatchResponse)
async def get_fundamental_indicators_batch(
    stock_id: str,
    request: FundamentalIndicatorBatchRequest,
    db: Session = Depends(get_db),
):
    """
    批量取得股票的多個財務指標

    使用三層緩存架構:
    L1: Redis (24小時) - 最快
    L2: PostgreSQL (永久) - 持久化
    L3: FinLab API - 數據源

    Args:
        stock_id: 股票代號
        request: 批量請求參數（包含指標列表、日期範圍）

    Returns:
        多個財務指標的數據
    """
    try:
        # L1 Cache: Try Redis first
        indicators_str = ",".join(sorted(request.indicators)) if request.indicators else "default"
        cache_key = f"fundamental_batch:{stock_id}:{indicators_str}:{request.start_date}:{request.end_date}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            logger.info(f"✅ L1 Cache HIT (Redis) for batch: {stock_id}")
            return cached_data

        # L2 Cache + L3 Source: Use FundamentalService
        from app.services.fundamental_service import FundamentalService
        service = FundamentalService(db)

        # Determine which indicators to fetch
        indicators_to_fetch = request.indicators if request.indicators else FinLabClient.get_common_fundamental_indicators()

        indicators_dict = service.get_indicators_batch(
            stock_id=stock_id,
            indicators=indicators_to_fetch,
            start_date=request.start_date,
            end_date=request.end_date,
            force_refresh=False  # Allow DB cache
        )

        requested_count = len(indicators_to_fetch)

        response = FundamentalIndicatorBatchResponse(
            stock_id=stock_id,
            indicators=indicators_dict,
            count=len(indicators_dict),
            requested_count=requested_count,
            start_date=request.start_date,
            end_date=request.end_date,
        )

        # Cache in Redis for 24 hours
        cache.set(cache_key, response, expiry=86400)
        logger.info(f"💾 Cached batch in Redis: {stock_id} ({len(indicators_dict)}/{requested_count} indicators)")

        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to get batch fundamental indicators: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch batch fundamental data: {str(e)}",
        )


@router.get("/fundamental/{stock_id}/summary", response_model=FundamentalSummary)
async def get_fundamental_summary(
    stock_id: str,
    finlab_client: FinLabClient = Depends(get_finlab_client),
):
    """
    取得股票的財務指標摘要（最新數據）

    Args:
        stock_id: 股票代號

    Returns:
        財務指標摘要
    """
    try:
        # Try cache first
        cache_key = f"fundamental_summary:{stock_id}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            logger.info(f"Returning cached fundamental summary for {stock_id}")
            return cached_data

        # Fetch common indicators
        indicators_data = finlab_client.get_fundamental_indicators_batch(
            stock_id=stock_id,
            indicators=None,  # Use default common indicators
        )

        # Extract latest values
        latest_date = None
        summary_data = {
            "stock_id": stock_id,
        }

        indicator_mapping = {
            "ROE稅後": "roe",
            "ROA稅後息前": "roa",
            "營業毛利率": "gross_margin",
            "營業利益率": "operating_margin",
            "稅後淨利率": "net_margin",
            "營收成長率": "revenue_growth",
            "稅後淨利成長率": "profit_growth",
            "應收帳款週轉率": "receivable_turnover",
            "存貨週轉率": "inventory_turnover",
            "總資產週轉率": "asset_turnover",
            "負債比率": "debt_ratio",
            "流動比率": "current_ratio",
            "速動比率": "quick_ratio",
            "每股淨值": "book_value_per_share",
            "每股盈餘": "eps",
            "每股營業額": "revenue_per_share",
        }

        for indicator_name, data_df in indicators_data.items():
            if stock_id in data_df.columns:
                # Get latest non-null value
                latest_value = data_df[stock_id].dropna().iloc[-1] if len(data_df[stock_id].dropna()) > 0 else None
                latest_idx = data_df[stock_id].dropna().index[-1] if len(data_df[stock_id].dropna()) > 0 else None

                if latest_idx and (latest_date is None or latest_idx > latest_date):
                    latest_date = latest_idx

                # Map to summary field
                field_name = indicator_mapping.get(indicator_name)
                if field_name and latest_value is not None:
                    summary_data[field_name] = float(latest_value)

        summary_data["latest_date"] = str(latest_date) if latest_date else None

        response = FundamentalSummary(**summary_data)

        # Cache for 1 hour
        cache.set(cache_key, response, expiry=3600)

        logger.info(f"Returned fundamental summary for {stock_id}")
        return response

    except Exception as e:
        logger.error(f"Failed to get fundamental summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch fundamental summary: {str(e)}",
        )


@router.post("/fundamental/compare", response_model=FundamentalComparisonResponse)
async def compare_fundamental_indicators(
    request: FundamentalComparisonRequest,
    finlab_client: FinLabClient = Depends(get_finlab_client),
):
    """
    比較多個股票的特定財務指標

    Args:
        request: 比較請求參數（股票列表、指標、日期範圍）

    Returns:
        各股票的指標數據對比
    """
    try:
        # Try cache first
        stock_ids_str = ",".join(sorted(request.stock_ids))
        cache_key = f"fundamental_compare:{stock_ids_str}:{request.indicator}:{request.start_date}:{request.end_date}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            logger.info(f"Returning cached fundamental comparison")
            return cached_data

        # Fetch data for each stock
        stocks_data = {}
        for stock_id in request.stock_ids:
            try:
                data_df = finlab_client.get_fundamental_indicator(
                    indicator=request.indicator,
                    stock_id=stock_id,
                    start_date=request.start_date,
                    end_date=request.end_date,
                )

                data_points = [
                    FundamentalDataPoint(
                        date=str(date),
                        value=float(value) if pd.notna(value) else None
                    )
                    for date, value in data_df[stock_id].items()
                ]

                stocks_data[stock_id] = data_points

            except Exception as e:
                logger.warning(f"Failed to get {request.indicator} for {stock_id}: {str(e)}")
                continue

        response = FundamentalComparisonResponse(
            indicator=request.indicator,
            stocks=stocks_data,
            count=len(stocks_data),
            start_date=request.start_date,
            end_date=request.end_date,
        )

        # Cache for 1 hour
        cache.set(cache_key, response, expiry=3600)

        logger.info(f"Returned comparison for {len(stocks_data)}/{len(request.stock_ids)} stocks")
        return response

    except Exception as e:
        logger.error(f"Failed to compare fundamental indicators: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare fundamental data: {str(e)}",
        )
