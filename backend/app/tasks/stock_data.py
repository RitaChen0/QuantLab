"""
Celery tasks for stock data synchronization
"""

from celery import Task
from app.core.celery_app import celery_app
from app.services.finlab_client import FinLabClient
from app.utils.cache import cache
from app.utils.task_history import record_task_history
from app.db.session import SessionLocal
from app.repositories.stock import StockRepository
from app.repositories.stock_price import StockPriceRepository
from app.schemas.stock import StockCreate
from app.schemas.stock_price import StockPriceCreate
from loguru import logger
from datetime import datetime, timezone, timedelta, date as date_type
from decimal import Decimal
import pandas as pd


@celery_app.task(bind=True, name="app.tasks.sync_stock_list")
@record_task_history
def sync_stock_list(self: Task) -> dict:
    """
    Sync stock list from FinLab API to database
    Runs daily to update the list of available stocks
    """
    db = SessionLocal()
    try:
        logger.info("Starting stock list synchronization...")

        # Initialize FinLab client
        client = FinLabClient()

        if not client.is_available():
            logger.error("FinLab client not available")
            return {
                "status": "error",
                "message": "FinLab client not available"
            }

        # Get stock list from FinLab
        stocks_df = client.get_stock_list()
        stock_count = len(stocks_df)

        # Save to database
        db_saved = 0
        db_updated = 0

        for idx, row in stocks_df.iterrows():
            stock_id = str(idx)

            # Check if stock exists
            existing_stock = StockRepository.get_by_id(db, stock_id)

            if existing_stock:
                # Update existing stock
                existing_stock.name = row.get('stock_name', stock_id)
                existing_stock.category = row.get('industry_category', '')
                existing_stock.market = row.get('market', '')
                db.commit()
                db_updated += 1
            else:
                # Create new stock
                stock_create = StockCreate(
                    stock_id=stock_id,
                    name=row.get('stock_name', stock_id),
                    category=row.get('industry_category', ''),
                    market=row.get('market', ''),
                    is_active='active'
                )
                StockRepository.create(db, stock_create)
                db_saved += 1

        # Store in cache (cache for 24 hours)
        stock_list = [
            {
                "stock_id": idx,
                "name": row.get('stock_name', idx),
                "industry": row.get('industry_category', ''),
                "market": row.get('market', ''),
            }
            for idx, row in stocks_df.iterrows()
        ]

        cache.set("stock_list:all", stock_list, expiry=86400)

        logger.info(f"Stock list synchronized: {stock_count} total, {db_saved} new, {db_updated} updated")

        return {
            "status": "success",
            "message": f"Synchronized {stock_count} stocks (new: {db_saved}, updated: {db_updated})",
            "stock_count": stock_count,
            "new_count": db_saved,
            "updated_count": db_updated,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to sync stock list: {str(e)}")
        db.rollback()
        # 使用指數退避：5m, 10m, 20m（300 * 2^retry_count）
        retry_count = self.request.retries
        countdown = 300 * (2 ** retry_count)
        raise self.retry(exc=e, countdown=countdown, max_retries=3)
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.sync_daily_prices")
@record_task_history
def sync_daily_prices(self: Task, stock_ids: list = None, days: int = 7) -> dict:
    """
    Sync daily price data for stocks

    Args:
        stock_ids: List of stock IDs to sync (if None, syncs popular stocks)
        days: Number of days to sync (default: 7)

    Returns:
        Task result with sync statistics
    """
    try:
        logger.info(f"Starting daily price synchronization (last {days} days)...")

        # Initialize FinLab client
        client = FinLabClient()

        if not client.is_available():
            logger.error("FinLab client not available")
            return {
                "status": "error",
                "message": "FinLab client not available"
            }

        # If no stock_ids provided, sync popular stocks
        if not stock_ids:
            # List of popular Taiwan stocks
            stock_ids = [
                "2330",  # 台積電
                "2317",  # 鴻海
                "2454",  # 聯發科
                "2412",  # 中華電
                "2882",  # 國泰金
                "2881",  # 富邦金
                "2886",  # 兆豐金
                "2891",  # 中信金
                "2892",  # 第一金
                "2002",  # 中鋼
                "1301",  # 台塑
                "1303",  # 南亞
                "2308",  # 台達電
                "2357",  # 華碩
                "3008",  # 大立光
            ]

        # Calculate date range
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

        synced_count = 0
        failed_count = 0

        for stock_id in stock_ids:
            try:
                # Get price data
                price_df = client.get_price(
                    stock_id=stock_id,
                    start_date=start_date,
                    end_date=end_date
                )

                # Convert to dict and cache
                data = {
                    str(date): float(price)
                    for date, price in price_df[stock_id].items()
                    if pd.notna(price)
                }

                # Cache for 10 minutes
                cache_key = f"price:{stock_id}:{start_date}:{end_date}"
                cache.set(cache_key, data, expiry=600)

                synced_count += 1
                logger.debug(f"Synced price data for {stock_id}: {len(data)} days")

            except Exception as e:
                logger.warning(f"Failed to sync {stock_id}: {str(e)}")
                failed_count += 1
                continue

        logger.info(f"Daily price sync completed: {synced_count} success, {failed_count} failed")

        return {
            "status": "success",
            "message": f"Synced {synced_count} stocks",
            "synced_count": synced_count,
            "failed_count": failed_count,
            "date_range": f"{start_date} to {end_date}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to sync daily prices: {str(e)}")
        # 使用指數退避：5m, 10m, 20m
        retry_count = self.request.retries
        countdown = 300 * (2 ** retry_count)
        raise self.retry(exc=e, countdown=countdown, max_retries=3)


@celery_app.task(bind=True, name="app.tasks.sync_ohlcv_data")
@record_task_history
def sync_ohlcv_data(self: Task, stock_ids: list = None, days: int = 30) -> dict:
    """
    Sync OHLCV data for stocks to database

    Args:
        stock_ids: List of stock IDs to sync (if None, syncs top stocks)
        days: Number of days to sync (default: 30)

    Returns:
        Task result with sync statistics
    """
    db = SessionLocal()
    try:
        logger.info(f"Starting OHLCV synchronization (last {days} days)...")

        # Initialize FinLab client
        client = FinLabClient()

        if not client.is_available():
            logger.error("FinLab client not available")
            return {
                "status": "error",
                "message": "FinLab client not available"
            }

        # If no stock_ids provided, use top 5 stocks
        if not stock_ids:
            stock_ids = ["2330", "2317", "2454", "2412", "2882"]

        # Calculate date range
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

        synced_count = 0
        failed_count = 0
        total_days = 0
        db_saved = 0

        for stock_id in stock_ids:
            try:
                # Get OHLCV data from FinLab
                ohlcv_df = client.get_ohlcv(
                    stock_id=stock_id,
                    start_date=start_date,
                    end_date=end_date
                )

                # Save to database using upsert
                for date, row in ohlcv_df.iterrows():
                    try:
                        price_create = StockPriceCreate(
                            stock_id=stock_id,
                            date=date.date() if hasattr(date, 'date') else date,
                            open=Decimal(str(row['open'])) if pd.notna(row['open']) else Decimal('0'),
                            high=Decimal(str(row['high'])) if pd.notna(row['high']) else Decimal('0'),
                            low=Decimal(str(row['low'])) if pd.notna(row['low']) else Decimal('0'),
                            close=Decimal(str(row['close'])) if pd.notna(row['close']) else Decimal('0'),
                            volume=int(row['volume']) if pd.notna(row['volume']) else 0,
                            adj_close=None
                        )
                        StockPriceRepository.upsert(db, price_create)
                        db_saved += 1
                    except Exception as e:
                        logger.warning(f"Failed to save {stock_id} on {date}: {str(e)}")
                        continue

                # Convert to dict for caching
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

                # Cache for 10 minutes
                cache_key = f"ohlcv:{stock_id}:{start_date}:{end_date}"
                cache.set(cache_key, data, expiry=600)

                synced_count += 1
                total_days += len(data)
                logger.debug(f"Synced OHLCV data for {stock_id}: {len(data)} days")

            except Exception as e:
                logger.warning(f"Failed to sync OHLCV for {stock_id}: {str(e)}")
                failed_count += 1
                continue

        logger.info(f"OHLCV sync completed: {synced_count} stocks, {total_days} total days, {db_saved} DB records")

        return {
            "status": "success",
            "message": f"Synced OHLCV for {synced_count} stocks",
            "synced_count": synced_count,
            "failed_count": failed_count,
            "total_days": total_days,
            "db_records": db_saved,
            "date_range": f"{start_date} to {end_date}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to sync OHLCV data: {str(e)}")
        db.rollback()
        # 使用指數退避：5m, 10m, 20m
        retry_count = self.request.retries
        countdown = 300 * (2 ** retry_count)
        raise self.retry(exc=e, countdown=countdown, max_retries=3)
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.sync_latest_prices")
@record_task_history
def sync_latest_prices(self: Task, stock_ids: list = None) -> dict:
    """
    Sync latest prices for stocks
    Runs frequently to keep prices up-to-date

    Args:
        stock_ids: List of stock IDs to sync (if None, syncs popular stocks)

    Returns:
        Task result with sync statistics
    """
    try:
        logger.info("Starting latest price synchronization...")

        # Initialize FinLab client
        client = FinLabClient()

        if not client.is_available():
            logger.error("FinLab client not available")
            return {
                "status": "error",
                "message": "FinLab client not available"
            }

        # If no stock_ids provided, sync popular stocks
        if not stock_ids:
            stock_ids = [
                "2330", "2317", "2454", "2412", "2882",
                "2881", "2886", "2891", "2892", "2002"
            ]

        synced_count = 0
        failed_count = 0

        for stock_id in stock_ids:
            try:
                # Get latest price
                price = client.get_latest_price(stock_id)

                if price is not None:
                    # Cache for 5 minutes
                    cache_key = f"latest_price:{stock_id}"
                    cache.set(cache_key, price, expiry=300)

                    synced_count += 1
                    logger.debug(f"Synced latest price for {stock_id}: {price}")
                else:
                    failed_count += 1

            except Exception as e:
                logger.warning(f"Failed to sync latest price for {stock_id}: {str(e)}")
                failed_count += 1
                continue

        logger.info(f"Latest price sync completed: {synced_count} success, {failed_count} failed")

        return {
            "status": "success",
            "message": f"Synced latest prices for {synced_count} stocks",
            "synced_count": synced_count,
            "failed_count": failed_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to sync latest prices: {str(e)}")
        # 使用指數退避：1m, 2m, 4m, 8m, 16m
        retry_count = self.request.retries
        countdown = 60 * (2 ** retry_count)
        raise self.retry(exc=e, countdown=countdown, max_retries=5)


@celery_app.task(bind=True, name="app.tasks.cleanup_old_cache")
@record_task_history
def cleanup_old_cache(self: Task) -> dict:
    """
    Clean up old cache entries
    Runs daily to prevent cache from growing too large
    """
    try:
        logger.info("Starting cache cleanup...")

        # Redis automatically handles expiry, but we can clear specific patterns if needed
        # For now, just log the cleanup

        logger.info("Cache cleanup completed")

        return {
            "status": "success",
            "message": "Cache cleanup completed",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to cleanup cache: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }
