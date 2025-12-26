"""
Celery tasks for institutional investor data synchronization
法人買賣超數據同步任務
"""

from celery import Task
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.institutional_investor_service import InstitutionalInvestorService
from app.repositories.stock import StockRepository
from app.utils.task_history import record_task_history
from app.utils.task_deduplication import skip_if_recently_executed
from app.utils.cache import cache
from loguru import logger
from datetime import datetime, timedelta, timezone
from typing import List, Optional


@celery_app.task(bind=True, name="app.tasks.sync_institutional_investors")
@record_task_history
def sync_institutional_investors(
    self: Task,
    stock_ids: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: int = 7
) -> dict:
    """
    同步法人買賣超數據

    Args:
        stock_ids: 股票代碼列表，如果為 None 則同步所有股票
        start_date: 開始日期 (YYYY-MM-DD)
        end_date: 結束日期 (YYYY-MM-DD)
        days: 如果未指定日期範圍，同步最近 N 天（默認 7 天）

    Returns:
        同步結果統計
    """
    # 🔒 Distributed lock - prevent concurrent execution
    redis_client = cache.redis_client
    lock_key = f"task_lock:{self.name}"
    # 60 分鐘超時（任務預計執行時間：20-30 分鐘，取決於股票數量）
    lock = redis_client.lock(lock_key, timeout=3600)

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
        logger.info("Starting institutional investor data synchronization...")

        # 如果沒有指定股票，獲取所有活躍股票
        if not stock_ids:
            stocks = StockRepository.get_all(db, is_active='active')
            stock_ids = [stock.stock_id for stock in stocks]
            logger.info(f"Syncing all {len(stock_ids)} active stocks")
        else:
            logger.info(f"Syncing {len(stock_ids)} specified stocks")

        # 如果沒有指定日期範圍，使用最近 N 天
        if not start_date:
            start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        logger.info(f"Date range: {start_date} ~ {end_date}")

        # 初始化服務
        service = InstitutionalInvestorService(db)

        # 批量同步
        result = service.sync_multiple_stocks(
            stock_ids=stock_ids,
            start_date=start_date,
            end_date=end_date,
            force=False  # 不強制覆蓋現有數據
        )

        logger.info(
            f"Sync completed: "
            f"stocks={result['total_stocks']}, "
            f"inserted={result['total_inserted']}, "
            f"updated={result['total_updated']}, "
            f"errors={result['total_errors']}"
        )

        return {
            "status": "success",
            "period": f"{start_date} ~ {end_date}",
            **result
        }

    except Exception as e:
        logger.error(f"Failed to sync institutional investor data: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

    finally:
        db.close()
        # 確保釋放鎖
        try:
            lock.release()
            logger.info("🔓 任務鎖已釋放")
        except Exception as e:
            logger.error(f"Failed to release lock: {e}")


@celery_app.task(bind=True, name="app.tasks.sync_single_stock_institutional")
@record_task_history
def sync_single_stock_institutional(
    self: Task,
    stock_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    force: bool = False
) -> dict:
    """
    同步單一股票的法人買賣超數據

    Args:
        stock_id: 股票代碼
        start_date: 開始日期 (YYYY-MM-DD)
        end_date: 結束日期 (YYYY-MM-DD)
        force: 是否強制覆蓋現有數據

    Returns:
        同步結果
    """
    db = SessionLocal()

    try:
        logger.info(f"Starting institutional investor sync for {stock_id}")

        service = InstitutionalInvestorService(db)

        result = service.sync_stock_data(
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date,
            force=force
        )

        logger.info(f"Sync completed for {stock_id}: {result}")

        return result

    except Exception as e:
        logger.error(f"Failed to sync {stock_id}: {str(e)}")
        return {
            "stock_id": stock_id,
            "status": "error",
            "message": str(e)
        }

    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.sync_top_stocks_institutional")
@skip_if_recently_executed(min_interval_hours=24)
@record_task_history
def sync_top_stocks_institutional(
    self: Task,
    limit: Optional[int] = None,
    days: int = 7
) -> dict:
    """
    同步股票的法人買賣超數據

    Args:
        limit: 股票數量限制（None = 全部股票）
        days: 同步最近 N 天

    Returns:
        同步結果統計
    """
    db = SessionLocal()

    try:
        if limit is None:
            logger.info("Starting institutional investor sync for ALL active stocks")
        else:
            logger.info(f"Starting institutional investor sync for top {limit} stocks")

        # 獲取股票列表
        stocks = StockRepository.get_all(db, is_active='active', limit=limit)
        stock_ids = [stock.stock_id for stock in stocks]

        if limit is None:
            logger.info(f"Selected ALL {len(stock_ids)} active stocks for sync")
        else:
            logger.info(f"Selected {len(stock_ids)} stocks for sync")

        # 直接調用同步邏輯（避免在任務內部等待其他任務）
        service = InstitutionalInvestorService(db)

        # 計算日期範圍
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        logger.info(f"Date range: {start_date} ~ {end_date}")

        # 批量同步
        result = service.sync_multiple_stocks(
            stock_ids=stock_ids,
            start_date=start_date,
            end_date=end_date,
            force=False
        )

        logger.info(
            f"Sync completed: "
            f"stocks={result['total_stocks']}, "
            f"inserted={result['total_inserted']}, "
            f"updated={result['total_updated']}, "
            f"errors={result['total_errors']}"
        )

        return {
            "status": "success",
            "period": f"{start_date} ~ {end_date}",
            **result
        }

    except Exception as e:
        logger.error(f"Failed to sync top stocks: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.cleanup_old_institutional_data")
@skip_if_recently_executed(min_interval_hours=168)  # 週任務：7 天 = 168 小時
@record_task_history
def cleanup_old_institutional_data(
    self: Task,
    days_to_keep: int = 365
) -> dict:
    """
    清理舊的法人買賣超數據

    Args:
        days_to_keep: 保留最近 N 天的數據（默認 365 天）

    Returns:
        清理結果
    """
    db = SessionLocal()

    try:
        logger.info(f"Starting cleanup of institutional data older than {days_to_keep} days")

        service = InstitutionalInvestorService(db)
        deleted_count = service.delete_old_data(days_to_keep)

        logger.info(f"Cleanup completed: deleted {deleted_count} records")

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "days_kept": days_to_keep
        }

    except Exception as e:
        logger.error(f"Failed to cleanup old data: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

    finally:
        db.close()
