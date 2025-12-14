"""
Unified Notification Service

統一的通知服務接口，支持多種通知渠道 (Telegram, Email等)。
"""

import asyncio
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from loguru import logger

from app.services.telegram_notification_service import TelegramNotificationService
from app.schemas.telegram import NotificationType, NotificationChannel


class NotificationService:
    """
    統一通知服務

    支持多種通知渠道：
    - Telegram Bot
    - Email (未來實現)
    - SMS (未來實現)
    """

    def __init__(self, db: Session):
        self.db = db
        self.telegram_service = TelegramNotificationService(db)

    async def send_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        channels: List[NotificationChannel] = None,
        image_path: Optional[str] = None,
        related_object_type: Optional[str] = None,
        related_object_id: Optional[int] = None
    ) -> Dict[str, any]:
        """
        發送通知到指定渠道

        Args:
            user_id: 用戶 ID
            notification_type: 通知類型
            title: 標題
            message: 消息內容
            channels: 通知渠道列表 (默認: [TELEGRAM])
            image_path: 圖片路徑 (可選)
            related_object_type: 關聯對象類型
            related_object_id: 關聯對象 ID

        Returns:
            {
                "telegram_sent": bool,
                "email_sent": bool,
                "errors": List[str]
            }
        """
        if channels is None:
            channels = [NotificationChannel.TELEGRAM]

        results = {
            "telegram_sent": False,
            "email_sent": False,
            "notification_ids": {},
            "errors": []
        }

        # Send to Telegram
        if NotificationChannel.TELEGRAM in channels:
            try:
                telegram_result = await self.telegram_service.send_notification(
                    user_id=user_id,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    image_path=image_path,
                    related_object_type=related_object_type,
                    related_object_id=related_object_id
                )

                results["telegram_sent"] = telegram_result["success"]
                results["notification_ids"]["telegram"] = telegram_result.get("notification_id")

                if not telegram_result["success"]:
                    results["errors"].append(f"Telegram: {telegram_result.get('error', 'Unknown error')}")

            except Exception as e:
                logger.error(f"Failed to send Telegram notification: {str(e)}")
                results["errors"].append(f"Telegram: {str(e)}")

        # Send to Email (未來實現)
        if NotificationChannel.EMAIL in channels:
            logger.info("Email notifications not yet implemented")
            results["errors"].append("Email: Not implemented")

        return results

    def send_notification_sync(
        self,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        channels: List[NotificationChannel] = None,
        image_path: Optional[str] = None,
        related_object_type: Optional[str] = None,
        related_object_id: Optional[int] = None
    ) -> Dict[str, any]:
        """
        同步發送通知（內部會啟動 asyncio event loop）

        此方法用於在同步環境中調用，例如 Celery 任務。

        Args: (與 send_notification 相同)

        Returns: (與 send_notification 相同)
        """
        try:
            # 嘗試獲取當前事件循環
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已有運行中的循環，創建新任務
                logger.warning("Event loop already running, creating new task")
                # 在這種情況下，我們需要在新的線程中運行
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.send_notification(
                            user_id, notification_type, title, message,
                            channels, image_path, related_object_type, related_object_id
                        )
                    )
                    return future.result()
            else:
                # 沒有運行中的循環，直接運行
                return loop.run_until_complete(
                    self.send_notification(
                        user_id, notification_type, title, message,
                        channels, image_path, related_object_type, related_object_id
                    )
                )
        except RuntimeError:
            # 沒有事件循環，創建新的
            return asyncio.run(
                self.send_notification(
                    user_id, notification_type, title, message,
                    channels, image_path, related_object_type, related_object_id
                )
            )

    def get_user_notifications(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, any]:
        """
        獲取用戶的通知歷史（Telegram）

        Args:
            user_id: 用戶 ID
            limit: 每頁數量
            offset: 偏移量

        Returns:
            {total, notifications}
        """
        return self.telegram_service.get_user_notifications(
            user_id, limit, offset
        )

    def get_user_preferences(self, user_id: int):
        """獲取用戶通知偏好（Telegram）"""
        return self.telegram_service.get_user_preferences(user_id)

    def update_user_preferences(self, user_id: int, preferences_update):
        """更新用戶通知偏好（Telegram）"""
        return self.telegram_service.update_user_preferences(
            user_id, preferences_update
        )


# Helper function for quick notifications
async def send_quick_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notification_type: NotificationType = NotificationType.SYSTEM_ALERT
) -> Dict[str, any]:
    """
    快速發送通知的輔助函數

    Args:
        db: Database session
        user_id: 用戶 ID
        title: 標題
        message: 消息內容
        notification_type: 通知類型 (默認: SYSTEM_ALERT)

    Returns:
        發送結果
    """
    service = NotificationService(db)
    return await service.send_notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message
    )
