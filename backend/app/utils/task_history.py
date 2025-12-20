"""
Task History Tracking Utility

Records task execution history to Redis for monitoring and debugging
"""

import functools
import json
from datetime import datetime, timezone
from typing import Callable, Any
from loguru import logger
from app.utils.cache import cache


def record_task_history(func: Callable) -> Callable:
    """
    Decorator to record task execution history in Redis

    Usage:
        @celery_app.task(bind=True, name="app.tasks.my_task")
        @record_task_history
        def my_task(self: Task) -> dict:
            # Task implementation
            return {"status": "success", "message": "Task completed"}
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        task_self = args[0] if args else None
        task_name = getattr(task_self, 'name', func.__name__)

        # Use UTC timezone (unified timezone strategy)
        start_time = datetime.now(timezone.utc)

        try:
            # Execute the task
            result = func(*args, **kwargs)

            # Record success
            _save_task_history(
                task_name=task_name,
                status="success",
                result=result.get("message") if isinstance(result, dict) else str(result),
                start_time=start_time,
                error=None
            )

            return result

        except Exception as e:
            # Record failure
            _save_task_history(
                task_name=task_name,
                status="failed",
                result=None,
                start_time=start_time,
                error=str(e)
            )
            raise

    return wrapper


def _save_task_history(
    task_name: str,
    status: str,
    result: Any,
    start_time: datetime,
    error: str = None
) -> None:
    """
    Save task execution history to Redis

    Args:
        task_name: Full task name (e.g., "app.tasks.sync_stock_list")
        status: Task status ("success", "failed", "pending", "running")
        result: Task result message
        start_time: Task start timestamp
        error: Error message if failed
    """
    try:
        if not cache.is_available():
            logger.warning("Cache not available, cannot save task history")
            return

        history_key = f"task_history:{task_name}"

        history_data = {
            "task_name": task_name,
            "status": status,
            "result": result,
            "error": error,
            "last_run": start_time.isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        # Save to Redis with 30-day expiration
        cache.set(history_key, json.dumps(history_data), expiry=30 * 86400)

        logger.debug(f"Saved task history for {task_name}: status={status}")

    except Exception as e:
        logger.error(f"Failed to save task history for {task_name}: {str(e)}")


def get_task_history(task_name: str) -> dict:
    """
    Get task execution history from Redis

    Args:
        task_name: Full task name (e.g., "app.tasks.sync_stock_list")

    Returns:
        dict: Task history data or None if not found
    """
    try:
        if not cache.is_available():
            return None

        history_key = f"task_history:{task_name}"
        history_data = cache.get(history_key)

        if history_data:
            if isinstance(history_data, str):
                return json.loads(history_data)
            return history_data

        return None

    except Exception as e:
        logger.error(f"Failed to get task history for {task_name}: {str(e)}")
        return None
