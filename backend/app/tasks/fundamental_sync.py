"""
財務指標定時同步任務

定期從 FinLab API 同步財務數據到 PostgreSQL
"""
from celery import Task
from sqlalchemy.orm import Session
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.fundamental_service import FundamentalService
from app.services.finlab_client import FinLabClient
from app.utils.task_history import record_task_history
from app.utils.task_deduplication import skip_if_recently_executed
from app.utils.cache import cache
from loguru import logger
from datetime import datetime, timezone
from typing import List


@celery_app.task(bind=True, name="app.tasks.sync_fundamental_data")
@skip_if_recently_executed(min_interval_hours=168)  # 週任務：7 天 = 168 小時
@record_task_history
def sync_fundamental_data(
    self: Task,
    stock_ids: List[str] = None,
    indicators: List[str] = None
) -> dict:
    """
    同步財務指標數據

    Args:
        stock_ids: 要同步的股票列表（None = 熱門股票）
        indicators: 要同步的指標列表（None = 所有18個指標）

    Returns:
        同步結果統計
    """
    # 🔒 Distributed lock - prevent concurrent execution
    redis_client = cache.redis_client
    lock_key = f"task_lock:{self.name}"
    # 2 小時超時（任務預計執行時間：30-60 分鐘，取決於股票和指標數量）
    lock = redis_client.lock(lock_key, timeout=7200)

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

    db: Session = SessionLocal()

    try:
        logger.info("=" * 60)
        logger.info("開始同步財務指標數據")
        logger.info("=" * 60)

        # 使用熱門股票如果未指定
        if stock_ids is None:
            stock_ids = [
                "2330",  # 台積電
                "2317",  # 鴻海
                "2454",  # 聯發科
                "2412",  # 中華電
                "2882",  # 國泰金
                "2881",  # 富邦金
                "2308",  # 台達電
                "2303",  # 聯電
            ]

        # 使用所有指標如果未指定
        if indicators is None:
            indicators = FinLabClient.get_common_fundamental_indicators()

        service = FundamentalService(db)
        total_synced = 0
        failed = []

        for stock_id in stock_ids:
            for indicator in indicators:
                try:
                    count = service.sync_indicator_data(
                        stock_id=stock_id,
                        indicator=indicator,
                        start_date=None,  # Sync all available data
                        end_date=None
                    )
                    total_synced += count
                    logger.info(f"✅ {stock_id} - {indicator}: {count} points")

                except Exception as e:
                    logger.warning(f"❌ Failed {stock_id} - {indicator}: {str(e)}")
                    failed.append(f"{stock_id}:{indicator}")
                    continue

        logger.info("=" * 60)
        logger.info(f"同步完成: {total_synced} 個數據點")
        logger.info(f"失敗: {len(failed)} 個指標")
        logger.info("=" * 60)

        return {
            "status": "success",
            "total_synced": total_synced,
            "stocks_count": len(stock_ids),
            "indicators_count": len(indicators),
            "failed_count": len(failed),
            "failed_items": failed[:10],  # Only return first 10 failures
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"同步任務失敗: {str(e)}")
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


@celery_app.task(bind=True, name="app.tasks.sync_fundamental_latest")
@skip_if_recently_executed(min_interval_hours=24)
@record_task_history
def sync_fundamental_latest(self: Task) -> dict:
    """
    快速同步最新季度的財務數據

    只同步熱門股票的最新一季數據（用於頻繁更新）

    Returns:
        同步結果統計
    """
    db: Session = SessionLocal()

    try:
        logger.info("開始快速同步最新財務數據")

        # 熱門股票前 5 名
        hot_stocks = ["2330", "2317", "2454", "2412", "2882"]

        # 只同步最重要的指標
        important_indicators = [
            "ROE稅後",
            "每股稅後淨利",
            "營業利益率",
            "營收成長率",
        ]

        service = FundamentalService(db)
        total_synced = 0

        # 只同步最近1年的數據
        from datetime import datetime, timedelta
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")

        for stock_id in hot_stocks:
            for indicator in important_indicators:
                try:
                    count = service.sync_indicator_data(
                        stock_id=stock_id,
                        indicator=indicator,
                        start_date=start_date,
                        end_date=end_date
                    )
                    total_synced += count

                except Exception as e:
                    logger.warning(f"Failed {stock_id} - {indicator}: {str(e)}")
                    continue

        logger.info(f"快速同步完成: {total_synced} 個數據點")

        return {
            "status": "success",
            "total_synced": total_synced,
            "stocks": hot_stocks,
            "indicators": important_indicators,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"快速同步失敗: {str(e)}")
        # 使用指數退避：3m, 6m, 12m
        retry_count = self.request.retries
        countdown = 180 * (2 ** retry_count)
        raise self.retry(exc=e, countdown=countdown, max_retries=3)

    finally:
        db.close()
