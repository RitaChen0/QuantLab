"""
Celery tasks for stock data synchronization
"""

from celery import Task
from app.core.celery_app import celery_app
from app.services.finlab_client import FinLabClient
from app.utils.cache import cache
from app.utils.task_history import record_task_history
from app.utils.task_deduplication import skip_if_recently_executed
from app.db.session import SessionLocal
from app.repositories.stock import StockRepository
from app.repositories.stock_price import StockPriceRepository
from app.schemas.stock import StockCreate
from app.schemas.stock_price import StockPriceCreate
from app.utils.price_validator import PriceValidationError
from loguru import logger
from datetime import datetime, timezone, timedelta, date as date_type
from decimal import Decimal
import pandas as pd


@celery_app.task(bind=True, name="app.tasks.sync_stock_list")
@skip_if_recently_executed(min_interval_hours=24)
@record_task_history
def sync_stock_list(self: Task) -> dict:
    """
    Sync stock list from FinLab API to database
    Runs daily to update the list of available stocks
    """
    # 🔒 Distributed lock - prevent concurrent execution
    redis_client = cache.redis_client
    lock_key = f"task_lock:{self.name}"
    # 5 分鐘超時（任務預計執行時間：1-2 分鐘）
    lock = redis_client.lock(lock_key, timeout=300)

    # 嘗試獲取鎖（非阻塞）
    if not lock.acquire(blocking=False):
        logger.warning(f"⚠️  任務 {self.name} 已在執行中，跳過此次觸發")
        logger.info(f"   鎖定 Key: {lock_key}")
        return {
            "status": "skipped",
            "reason": "task_already_running",
            "message": f"Task {self.name} is already running, skipped duplicate execution",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    logger.info(f"🔐 已獲取任務鎖: {lock_key}")

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
        # 確保釋放鎖
        try:
            lock.release()
            logger.info("🔓 任務鎖已釋放")
        except Exception as e:
            logger.error(f"Failed to release lock: {e}")


@celery_app.task(bind=True, name="app.tasks.sync_daily_prices")
@skip_if_recently_executed(min_interval_hours=24)
@record_task_history
def sync_daily_prices(self: Task, stock_ids: list = None, days: int = 7) -> dict:
    """
    Sync daily price data for stocks (writes to database AND cache)

    Args:
        stock_ids: List of stock IDs to sync (if None, syncs popular stocks)
        days: Number of days to sync (default: 7)

    Returns:
        Task result with sync statistics
    """
    from app.db.session import SessionLocal
    from app.repositories.stock_price import StockPriceRepository
    from app.schemas.stock_price import StockPriceCreate
    from datetime import date as DateType

    # 🔒 Distributed lock - prevent concurrent execution
    redis_client = cache.redis_client
    lock_key = f"task_lock:{self.name}"
    # 30 分鐘超時（任務預計執行時間：5-10 分鐘）
    lock = redis_client.lock(lock_key, timeout=1800)

    # 嘗試獲取鎖（非阻塞）
    if not lock.acquire(blocking=False):
        logger.warning(f"⚠️  任務 {self.name} 已在執行中，跳過此次觸發")
        logger.info(f"   鎖定 Key: {lock_key}")
        return {
            "status": "skipped",
            "reason": "task_already_running",
            "message": f"Task {self.name} is already running, skipped duplicate execution",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    logger.info(f"🔐 已獲取任務鎖: {lock_key}")

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
        db_records_count = 0

        db = SessionLocal()
        try:
            for stock_id in stock_ids:
                try:
                    # Get price data from FinLab
                    price_df = client.get_price(
                        stock_id=stock_id,
                        start_date=start_date,
                        end_date=end_date
                    )

                    # Convert to dict for cache
                    data = {
                        str(date): float(price)
                        for date, price in price_df[stock_id].items()
                        if pd.notna(price)
                    }

                    # Write to database (IMPORTANT!) 帶驗證
                    validation_errors = 0
                    for date_str, price_value in data.items():
                        try:
                            # Extract date part only (remove time if present)
                            date_only = date_str.split()[0] if ' ' in date_str else date_str
                            # FinLab price API只有收盤價，其他欄位用 close 填充（資料庫不允許 NULL）
                            price_create = StockPriceCreate(
                                stock_id=stock_id,
                                date=DateType.fromisoformat(date_only),
                                close=price_value,
                                open=price_value,   # 使用 close 作為 open
                                high=price_value,   # 使用 close 作為 high
                                low=price_value,    # 使用 close 作為 low
                                volume=0,           # 無成交量數據
                                adj_close=None
                            )
                            StockPriceRepository.upsert(db, price_create)  # 預設會驗證
                            db_records_count += 1
                        except PriceValidationError as e:
                            # 價格驗證失敗 - 記錄但不中斷同步
                            validation_errors += 1
                            logger.warning(f"⚠️  [VALIDATION] {stock_id} {date_only if 'date_only' in locals() else date_str}: {str(e)}")
                            continue
                        except Exception as e:
                            logger.warning(f"Failed to write {stock_id} {date_only if 'date_only' in locals() else date_str} to DB: {e}")
                            continue

                    if validation_errors > 0:
                        logger.warning(
                            f"⚠️  {stock_id} 驗證失敗: {validation_errors} 筆記錄被拒絕"
                        )

                    # Cache for 10 minutes (for API performance)
                    cache_key = f"price:{stock_id}:{start_date}:{end_date}"
                    cache.set(cache_key, data, expiry=600)

                    synced_count += 1
                    logger.debug(f"Synced price data for {stock_id}: {len(data)} days ({db_records_count} DB records)")

                except Exception as e:
                    logger.warning(f"Failed to sync {stock_id}: {str(e)}")
                    failed_count += 1
                    continue
        finally:
            db.close()

        logger.info(f"Daily price sync completed: {synced_count} success, {failed_count} failed, {db_records_count} DB records")

        return {
            "status": "success",
            "message": f"Synced {synced_count} stocks to DB",
            "synced_count": synced_count,
            "failed_count": failed_count,
            "db_records": db_records_count,
            "date_range": f"{start_date} to {end_date}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to sync daily prices: {str(e)}")
        # 使用指數退避：5m, 10m, 20m
        retry_count = self.request.retries
        countdown = 300 * (2 ** retry_count)
        raise self.retry(exc=e, countdown=countdown, max_retries=3)
    finally:
        # 確保釋放鎖
        try:
            lock.release()
            logger.info("🔓 任務鎖已釋放")
        except Exception as e:
            logger.error(f"Failed to release lock: {e}")


@celery_app.task(bind=True, name="app.tasks.sync_ohlcv_data")
@skip_if_recently_executed(min_interval_hours=24)
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
    # 🔒 Distributed lock - prevent concurrent execution
    redis_client = cache.redis_client
    lock_key = f"task_lock:{self.name}"
    # 30 分鐘超時（任務預計執行時間：10-15 分鐘）
    lock = redis_client.lock(lock_key, timeout=1800)

    # 嘗試獲取鎖（非阻塞）
    if not lock.acquire(blocking=False):
        logger.warning(f"⚠️  任務 {self.name} 已在執行中，跳過此次觸發")
        logger.info(f"   鎖定 Key: {lock_key}")
        return {
            "status": "skipped",
            "reason": "task_already_running",
            "message": f"Task {self.name} is already running, skipped duplicate execution",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    logger.info(f"🔐 已獲取任務鎖: {lock_key}")

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

                # Save to database using upsert（帶驗證）
                validation_errors = 0
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
                        StockPriceRepository.upsert(db, price_create)  # 預設會驗證
                        db_saved += 1
                    except PriceValidationError as e:
                        # 價格驗證失敗 - 記錄但不中斷同步
                        validation_errors += 1
                        logger.warning(f"⚠️  [VALIDATION] {stock_id} {date}: {str(e)}")
                        continue
                    except Exception as e:
                        logger.warning(f"Failed to save {stock_id} on {date}: {str(e)}")
                        continue

                if validation_errors > 0:
                    logger.warning(
                        f"⚠️  {stock_id} 驗證失敗: {validation_errors} 筆記錄被拒絕"
                    )

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
        # 確保釋放鎖
        try:
            lock.release()
            logger.info("🔓 任務鎖已釋放")
        except Exception as e:
            logger.error(f"Failed to release lock: {e}")


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


@celery_app.task(bind=True, name="app.tasks.sync_latest_prices_shioaji")
@record_task_history
def sync_latest_prices_shioaji(self: Task, stock_ids: list = None) -> dict:
    """
    Sync latest prices using Shioaji API (no quota limit)
    Runs frequently to keep prices up-to-date

    注意：此任務只更新即時報價快取，完整 OHLCV 數據由 sync_ohlcv_data 負責

    Args:
        stock_ids: List of stock IDs to sync (if None, syncs popular stocks)

    Returns:
        Task result with sync statistics
    """
    try:
        logger.info("Starting latest price synchronization (Shioaji)...")

        # Initialize Shioaji client
        from app.services.shioaji_client import ShioajiClient

        # If no stock_ids provided, sync popular stocks
        if not stock_ids:
            stock_ids = [
                "2330", "2317", "2454", "2412", "2882",
                "2881", "2886", "2891", "2892", "2002"
            ]

        synced_count = 0
        failed_count = 0

        # Use context manager for automatic login/logout
        with ShioajiClient() as client:
            if not client.is_available():
                logger.error("Shioaji client not available")
                return {
                    "status": "error",
                    "message": "Shioaji client not available"
                }

            for stock_id in stock_ids:
                try:
                    # Get latest quote from Shioaji
                    quote_data = client.get_quote(stock_id)

                    if quote_data and quote_data.get('price'):
                        price = quote_data['price']

                        # Cache for 5 minutes
                        cache_key = f"latest_price:{stock_id}"
                        cache.set(cache_key, price, expiry=300)

                        synced_count += 1
                        logger.debug(f"Synced latest price for {stock_id}: {price} (Shioaji)")
                    else:
                        failed_count += 1
                        logger.warning(f"No quote data for {stock_id}")

                except Exception as e:
                    logger.warning(f"Failed to sync latest price for {stock_id}: {str(e)}")
                    failed_count += 1
                    continue

        logger.info(f"Latest price sync completed (Shioaji): {synced_count} success, {failed_count} failed")

        return {
            "status": "success",
            "message": f"Synced latest prices for {synced_count} stocks (Shioaji)",
            "synced_count": synced_count,
            "failed_count": failed_count,
            "data_source": "shioaji",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to sync latest prices (Shioaji): {str(e)}")
        # 使用指數退避：1m, 2m, 4m, 8m, 16m
        retry_count = self.request.retries
        countdown = 60 * (2 ** retry_count)
        raise self.retry(exc=e, countdown=countdown, max_retries=5)


@celery_app.task(bind=True, name="app.tasks.cleanup_old_cache")
@skip_if_recently_executed(min_interval_hours=24)
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
