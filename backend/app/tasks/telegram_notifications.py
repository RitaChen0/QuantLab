"""
Celery Telegram Notification Tasks

異步發送 Telegram 通知，不阻塞主流程。
"""

from celery import Task
from typing import Optional, List
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.notification_service import NotificationService
from app.schemas.telegram import NotificationType, NotificationChannel
from loguru import logger


@celery_app.task(
    bind=True,
    name="app.tasks.send_telegram_notification",
    max_retries=3,
    default_retry_delay=60,  # 1 分鐘後重試
    acks_late=True,
    time_limit=300,  # 硬超時：5 分鐘
    soft_time_limit=240,  # 軟超時：4 分鐘
)
def send_telegram_notification(
    self: Task,
    user_id: int,
    notification_type: str,  # NotificationType enum value
    title: str,
    message: str,
    channels: Optional[List[str]] = None,
    image_path: Optional[str] = None,
    related_object_type: Optional[str] = None,
    related_object_id: Optional[int] = None
) -> dict:
    """
    異步發送 Telegram 通知

    Args:
        self: Celery Task 實例
        user_id: 用戶 ID
        notification_type: 通知類型 (backtest_completed, rdagent_completed, etc.)
        title: 通知標題
        message: 通知內容 (支持 HTML 格式)
        channels: 通知渠道列表 (默認: ["telegram"])
        image_path: 圖片路徑 (可選)
        related_object_type: 關聯對象類型 (backtest, strategy, etc.)
        related_object_id: 關聯對象 ID

    Returns:
        {
            "success": bool,
            "telegram_sent": bool,
            "notification_id": int,
            "errors": List[str]
        }
    """
    db = SessionLocal()

    try:
        logger.info(
            f"Celery task started: send_telegram_notification("
            f"user_id={user_id}, type={notification_type})"
        )

        # 轉換 channels 字符串列表為 NotificationChannel enum
        if channels:
            channel_enums = [
                NotificationChannel(ch) for ch in channels
            ]
        else:
            channel_enums = [NotificationChannel.TELEGRAM]

        # 轉換 notification_type 字符串為 NotificationType enum
        notification_type_enum = NotificationType(notification_type)

        # 創建通知服務
        notification_service = NotificationService(db)

        # 發送通知（同步調用，內部會處理 async）
        result = notification_service.send_notification_sync(
            user_id=user_id,
            notification_type=notification_type_enum,
            title=title,
            message=message,
            channels=channel_enums,
            image_path=image_path,
            related_object_type=related_object_type,
            related_object_id=related_object_id
        )

        success = result.get("telegram_sent", False) or result.get("email_sent", False)

        logger.info(
            f"✅ Telegram notification task completed: "
            f"user_id={user_id}, success={success}"
        )

        return {
            "success": success,
            "telegram_sent": result.get("telegram_sent", False),
            "email_sent": result.get("email_sent", False),
            "notification_ids": result.get("notification_ids", {}),
            "errors": result.get("errors", [])
        }

    except Exception as e:
        error_message = str(e)
        logger.error(
            f"❌ Failed to send Telegram notification: "
            f"user_id={user_id}, error={error_message}"
        )

        # 重試機制
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying... (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=self.default_retry_delay)

        # 達到最大重試次數，返回失敗結果
        return {
            "success": False,
            "telegram_sent": False,
            "email_sent": False,
            "notification_ids": {},
            "errors": [error_message]
        }

    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="app.tasks.send_bulk_telegram_notifications",
    max_retries=1,
    default_retry_delay=300,  # 5 分鐘後重試
    acks_late=True,
    time_limit=1800,  # 硬超時：30 分鐘
    soft_time_limit=1500,  # 軟超時：25 分鐘
)
def send_bulk_telegram_notifications(
    self: Task,
    user_ids: List[int],
    notification_type: str,
    title: str,
    message: str,
    image_path: Optional[str] = None
) -> dict:
    """
    批量發送 Telegram 通知

    用於市場提醒等需要向多個用戶發送相同通知的場景。

    Args:
        self: Celery Task 實例
        user_ids: 用戶 ID 列表
        notification_type: 通知類型
        title: 通知標題
        message: 通知內容
        image_path: 圖片路徑 (可選)

    Returns:
        {
            "total": int,
            "sent": int,
            "failed": int,
            "errors": List[str]
        }
    """
    logger.info(
        f"Celery task started: send_bulk_telegram_notifications("
        f"users={len(user_ids)}, type={notification_type})"
    )

    total = len(user_ids)
    sent = 0
    failed = 0
    errors = []

    # 逐個發送通知（避免速率限制）
    for user_id in user_ids:
        try:
            # 調用單個通知任務
            result = send_telegram_notification.apply_async(
                args=[user_id, notification_type, title, message],
                kwargs={
                    "image_path": image_path,
                    "related_object_type": "bulk_notification",
                    "related_object_id": None
                }
            )

            # 等待結果（最多 10 秒）
            task_result = result.get(timeout=10)

            if task_result.get("success"):
                sent += 1
            else:
                failed += 1
                errors.extend(task_result.get("errors", []))

        except Exception as e:
            failed += 1
            error_msg = f"User {user_id}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"Failed to send notification to user {user_id}: {str(e)}")

        # 更新任務進度
        self.update_state(
            state='PROGRESS',
            meta={
                'total': total,
                'sent': sent,
                'failed': failed,
                'current': sent + failed
            }
        )

    logger.info(
        f"✅ Bulk notification task completed: "
        f"total={total}, sent={sent}, failed={failed}"
    )

    return {
        "total": total,
        "sent": sent,
        "failed": failed,
        "errors": errors
    }
