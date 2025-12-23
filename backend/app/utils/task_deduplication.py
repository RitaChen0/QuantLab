"""
任務去重與執行時機檢查工具

用於防止 Celery Beat 重啟後補發大量任務導致的重複執行問題
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import logging
from redis import Redis
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_redis_client() -> Redis:
    """獲取 Redis 客戶端"""
    from app.utils.cache import cache
    return cache.redis_client


def should_skip_task(
    task_name: str,
    min_interval_hours: int = 24,
    redis_client: Optional[Redis] = None
) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    檢查任務是否應該跳過（避免重複執行）

    Args:
        task_name: 任務名稱（例如：app.tasks.sync_stock_list）
        min_interval_hours: 最小執行間隔（小時），預設 24 小時
        redis_client: Redis 客戶端（可選）

    Returns:
        (should_skip, info):
        - should_skip: True 表示應該跳過，False 表示應該執行
        - info: 包含執行資訊的字典（如果應該跳過）

    Examples:
        >>> should_skip, info = should_skip_task("app.tasks.sync_stock_list", 24)
        >>> if should_skip:
        >>>     logger.info(f"Skipping task: {info}")
        >>>     return info
        >>> # 繼續執行任務...
    """
    if redis_client is None:
        redis_client = get_redis_client()

    # Redis key
    last_run_key = f"task_last_run:{task_name}"

    try:
        # 獲取最後執行時間
        last_run_str = redis_client.get(last_run_key)

        if last_run_str:
            # 解析時間
            last_run = datetime.fromisoformat(last_run_str.decode())

            # 計算經過時間
            now = datetime.now(timezone.utc)
            elapsed_seconds = (now - last_run).total_seconds()
            elapsed_hours = elapsed_seconds / 3600
            min_interval_seconds = min_interval_hours * 3600

            # 如果在最小間隔內，跳過執行
            if elapsed_seconds < min_interval_seconds:
                info = {
                    "status": "skipped",
                    "reason": "already_executed_recently",
                    "task_name": task_name,
                    "last_run": last_run.isoformat(),
                    "elapsed_hours": round(elapsed_hours, 2),
                    "min_interval_hours": min_interval_hours,
                    "next_run_allowed_at": (last_run + timedelta(hours=min_interval_hours)).isoformat()
                }

                logger.info(
                    f"Task {task_name} already executed {elapsed_hours:.1f} hours ago "
                    f"(min interval: {min_interval_hours}h), skipping"
                )

                return True, info

        # 不跳過，應該執行
        return False, None

    except Exception as e:
        logger.error(f"Error checking task execution time for {task_name}: {e}")
        # 發生錯誤時，不跳過（寧可重複執行也不要漏執行）
        return False, None


def mark_task_executed(
    task_name: str,
    ttl_hours: int = 48,
    redis_client: Optional[Redis] = None
) -> None:
    """
    標記任務已執行

    Args:
        task_name: 任務名稱
        ttl_hours: Redis key 過期時間（小時），預設 48 小時
        redis_client: Redis 客戶端（可選）

    Examples:
        >>> mark_task_executed("app.tasks.sync_stock_list", ttl_hours=48)
    """
    if redis_client is None:
        redis_client = get_redis_client()

    last_run_key = f"task_last_run:{task_name}"
    now = datetime.now(timezone.utc)

    try:
        # 記錄當前時間，並設置過期時間
        redis_client.set(
            last_run_key,
            now.isoformat(),
            ex=ttl_hours * 3600  # 轉換為秒
        )

        logger.info(f"Marked task {task_name} as executed at {now.isoformat()}")

    except Exception as e:
        logger.error(f"Error marking task {task_name} as executed: {e}")


def get_task_last_run(
    task_name: str,
    redis_client: Optional[Redis] = None
) -> Optional[datetime]:
    """
    獲取任務最後執行時間

    Args:
        task_name: 任務名稱
        redis_client: Redis 客戶端（可選）

    Returns:
        最後執行時間（datetime），如果不存在則返回 None

    Examples:
        >>> last_run = get_task_last_run("app.tasks.sync_stock_list")
        >>> if last_run:
        >>>     print(f"Last run: {last_run.isoformat()}")
    """
    if redis_client is None:
        redis_client = get_redis_client()

    last_run_key = f"task_last_run:{task_name}"

    try:
        last_run_str = redis_client.get(last_run_key)

        if last_run_str:
            return datetime.fromisoformat(last_run_str.decode())

        return None

    except Exception as e:
        logger.error(f"Error getting last run time for {task_name}: {e}")
        return None


def skip_if_recently_executed(min_interval_hours: int = 24):
    """
    裝飾器：自動檢查任務是否最近執行過，如果是則跳過

    Args:
        min_interval_hours: 最小執行間隔（小時）

    Examples:
        >>> @celery_app.task(bind=True)
        >>> @skip_if_recently_executed(min_interval_hours=24)
        >>> def sync_stock_list(self):
        >>>     # 任務邏輯
        >>>     return {"status": "success"}
    """
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            task_name = self.name

            # 檢查是否應該跳過
            should_skip, info = should_skip_task(task_name, min_interval_hours)

            if should_skip:
                return info

            # 執行任務
            try:
                result = func(self, *args, **kwargs)

                # 執行成功後標記
                mark_task_executed(task_name, ttl_hours=min_interval_hours * 2)

                return result

            except Exception as e:
                # 執行失敗不標記，下次重試
                logger.error(f"Task {task_name} failed: {e}")
                raise

        return wrapper
    return decorator
