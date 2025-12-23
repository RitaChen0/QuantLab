"""
系統維護相關的 Celery 任務

包含清理過期資料、revoked tasks 等系統維護功能
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from celery import Task
from redis.exceptions import RedisError

from app.core.celery_app import celery_app
from app.core.config import settings
from app.utils.cache import cache
from app.utils.task_history import record_task_history
from app.utils.task_deduplication import skip_if_recently_executed

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.cleanup_celery_metadata")
@skip_if_recently_executed(min_interval_hours=24)
@record_task_history
def cleanup_celery_metadata(
    self: Task,
    max_age_hours: int = 24,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    清理 Celery 元數據（過期結果、revoked tasks 等）

    此任務定期清理 Redis 中的 Celery 元數據，防止：
    1. revoked task IDs 無限積累導致 Worker 拒絕新任務
    2. 過期的任務結果佔用 Redis 內存
    3. 舊的任務狀態記錄造成混亂

    Args:
        max_age_hours: 保留多少小時內的結果（預設 24 小時）
        dry_run: 僅檢查不實際刪除（預設 False）

    Returns:
        Dict 包含清理統計資訊
    """
    logger.info("🧹 開始清理 Celery 元數據...")

    stats = {
        "revoked_tasks_cleared": 0,
        "expired_results_deleted": 0,
        "task_states_cleaned": 0,
        "errors": []
    }

    if not cache.is_available():
        logger.warning("⚠️  Redis 不可用，跳過清理")
        stats["errors"].append("Redis unavailable")
        return stats

    try:
        redis_client = cache.redis_client
        if not redis_client:
            logger.warning("⚠️  Redis 客戶端不可用，跳過清理")
            stats["errors"].append("Redis client unavailable")
            return stats

        # 1. 智慧清理 revoked task IDs
        # 問題：過期的任務 ID 會永久留在 Worker 內存中，擋住未來的任務
        # 解決：通過重啟 Worker 進程池來清空 revoked 列表
        logger.info("🗑️  智慧清理 revoked tasks...")

        from celery import current_app
        control = current_app.control

        # 1.1 檢查當前 revoked 列表
        try:
            inspect = control.inspect()
            revoked_info = inspect.revoked()

            if revoked_info:
                total_revoked = sum(len(tasks) for tasks in revoked_info.values())
                logger.info(f"📊 當前 revoked 任務數量: {total_revoked}")

                # 如果有 revoked 任務，通過重啟進程池來清空
                if total_revoked > 0 and not dry_run:
                    logger.info("🔄 檢測到 revoked 任務，重啟 Worker 進程池以清空...")

                    # 使用 pool_restart 命令重啟所有 Worker 的進程池
                    # 這會清空內存中的 revoked 列表，但不影響正在執行的任務
                    control.broadcast('pool_restart', arguments={'reload': False})

                    logger.info("✅ 已通知所有 Worker 重啟進程池")
                    stats["revoked_tasks_cleared"] = total_revoked
                elif total_revoked > 0:
                    logger.info(f"🔍 [DRY RUN] 將重啟 Worker 進程池以清空 {total_revoked} 個 revoked 任務")
                else:
                    logger.info("✅ Revoked 列表已空，無需清理")
            else:
                logger.warning("⚠️  無法獲取 revoked 列表資訊")

        except Exception as e:
            logger.warning(f"⚠️  清理 revoked 列表時出錯: {e}")
            stats["errors"].append(f"Revoked cleanup error: {str(e)}")

        # 1.2 清空隊列中未執行的過期任務（可選）
        if not dry_run:
            try:
                purged = control.purge()  # 清空所有隊列中未執行的任務
                if purged:
                    logger.info(f"🗑️  已清空 {purged} 個隊列中的未執行任務")
            except Exception as e:
                logger.warning(f"⚠️  清空隊列時出錯: {e}")

        # 2. 清理過期的任務結果
        # Celery 結果存儲在 Redis 中，key pattern: celery-task-meta-<task_id>
        logger.info(f"🗑️  清理 {max_age_hours} 小時前的任務結果...")

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        result_pattern = "celery-task-meta-*"

        cursor = 0
        deleted_count = 0

        while True:
            cursor, keys = redis_client.scan(
                cursor=cursor,
                match=result_pattern,
                count=100
            )

            for key in keys:
                try:
                    # 檢查 TTL，如果已有過期時間則跳過
                    ttl = redis_client.ttl(key)
                    if ttl > 0:
                        continue  # 已設置 TTL，Redis 會自動清理

                    # 獲取任務結果並檢查時間
                    result_data = redis_client.get(key)
                    if result_data:
                        # 簡單方式：直接刪除沒有 TTL 的舊結果
                        if not dry_run:
                            redis_client.delete(key)
                            deleted_count += 1
                except Exception as e:
                    logger.warning(f"⚠️  處理 key {key} 時出錯: {e}")
                    stats["errors"].append(f"Key {key}: {str(e)}")

            if cursor == 0:
                break

        stats["expired_results_deleted"] = deleted_count
        logger.info(f"✅ 已刪除 {deleted_count} 個過期結果")

        # 3. 清理過期的任務狀態（如果有自定義狀態存儲）
        state_pattern = "celery-task-state-*"
        cursor = 0
        state_deleted = 0

        while True:
            cursor, keys = redis_client.scan(
                cursor=cursor,
                match=state_pattern,
                count=100
            )

            for key in keys:
                try:
                    ttl = redis_client.ttl(key)
                    if ttl == -1:  # 沒有過期時間
                        if not dry_run:
                            redis_client.expire(key, max_age_hours * 3600)
                            state_deleted += 1
                except Exception as e:
                    logger.warning(f"⚠️  處理狀態 key {key} 時出錯: {e}")

            if cursor == 0:
                break

        stats["task_states_cleaned"] = state_deleted
        logger.info(f"✅ 已設置 {state_deleted} 個狀態 key 過期時間")

    except RedisError as e:
        logger.error(f"❌ Redis 錯誤: {e}")
        stats["errors"].append(f"Redis error: {str(e)}")
    except Exception as e:
        logger.error(f"❌ 清理過程中發生錯誤: {e}")
        stats["errors"].append(f"Cleanup error: {str(e)}")

    # 記錄統計結果
    logger.info(f"📊 清理完成統計:")
    logger.info(f"  - Revoked tasks 清理: {stats['revoked_tasks_cleared']}")
    logger.info(f"  - 過期結果刪除: {stats['expired_results_deleted']}")
    logger.info(f"  - 狀態 key 清理: {stats['task_states_cleaned']}")

    if stats["errors"]:
        logger.warning(f"  - 錯誤數量: {len(stats['errors'])}")

    return stats
