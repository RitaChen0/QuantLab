"""
Telegram Notification Service

處理 Telegram 通知的業務邏輯，包括偏好檢查、模板渲染等。
"""

import asyncio
from typing import Optional, Dict
from datetime import datetime, time as datetime_time, timezone
from sqlalchemy.orm import Session
from loguru import logger

from app.clients.telegram_client import telegram_client
from app.repositories.telegram_notification import (
    TelegramNotificationRepository,
    TelegramNotificationPreferenceRepository
)
from app.repositories.user import UserRepository
from app.schemas.telegram import TelegramNotificationCreate, NotificationType


class TelegramNotificationService:
    """Telegram 通知服務"""

    def __init__(self, db: Session):
        self.db = db
        self.notification_repo = TelegramNotificationRepository()
        self.preference_repo = TelegramNotificationPreferenceRepository()
        self.user_repo = UserRepository()

    def should_send_notification(
        self,
        user_id: int,
        notification_type: NotificationType
    ) -> tuple[bool, Optional[str]]:
        """
        檢查是否應該發送通知

        Args:
            user_id: 用戶 ID
            notification_type: 通知類型

        Returns:
            (should_send, reason) 元組
        """
        # 1. 檢查用戶是否綁定 Telegram
        user = self.user_repo.get_by_id(self.db, user_id)
        if not user or not user.telegram_id:
            return False, "User not bound to Telegram"

        # 2. 檢查 Telegram Bot 是否可用
        if not telegram_client.is_available():
            return False, "Telegram Bot not available"

        # 3. 獲取用戶通知偏好
        preferences = self.preference_repo.get_or_create(self.db, user_id)

        # 4. 檢查全局開關
        if not preferences.notifications_enabled:
            return False, "Notifications disabled by user"

        # 5. 檢查特定類型開關
        type_enabled_map = {
            NotificationType.BACKTEST_COMPLETED: preferences.backtest_completed_enabled,
            NotificationType.RDAGENT_COMPLETED: preferences.rdagent_completed_enabled,
            NotificationType.MARKET_ALERT: preferences.market_alert_enabled,
        }

        if notification_type in type_enabled_map:
            if not type_enabled_map[notification_type]:
                return False, f"{notification_type.value} notifications disabled"

        # 6. 檢查靜默時段
        if preferences.quiet_hours_enabled and self._is_in_quiet_hours(
            preferences.quiet_hours_start,
            preferences.quiet_hours_end
        ):
            return False, "In quiet hours"

        return True, None

    def _is_in_quiet_hours(
        self,
        start_time: Optional[datetime_time],
        end_time: Optional[datetime_time]
    ) -> bool:
        """
        檢查當前時間是否在靜默時段內

        Args:
            start_time: 靜默開始時間 (e.g., 23:00)
            end_time: 靜默結束時間 (e.g., 08:00)

        Returns:
            是否在靜默時段
        """
        if not start_time or not end_time:
            return False

        now = datetime.now(timezone.utc).time()

        # 跨日情況 (e.g., 23:00 - 08:00)
        if start_time > end_time:
            return now >= start_time or now <= end_time
        else:
            # 不跨日 (e.g., 13:00 - 14:00)
            return start_time <= now <= end_time

    async def send_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        image_path: Optional[str] = None,
        related_object_type: Optional[str] = None,
        related_object_id: Optional[int] = None
    ) -> Dict[str, any]:
        """
        發送 Telegram 通知

        Args:
            user_id: 用戶 ID
            notification_type: 通知類型
            title: 標題
            message: 消息內容 (支持 HTML)
            image_path: 圖片路徑 (可選)
            related_object_type: 關聯對象類型 (可選)
            related_object_id: 關聯對象 ID (可選)

        Returns:
            結果字典 {success, notification_id, telegram_message_id, error}
        """
        # 檢查是否應該發送
        should_send, reason = self.should_send_notification(user_id, notification_type)

        if not should_send:
            logger.info(f"Skipping notification for user {user_id}: {reason}")
            return {
                "success": False,
                "notification_id": None,
                "telegram_message_id": None,
                "error": reason
            }

        # 創建通知記錄
        notification_create = TelegramNotificationCreate(
            notification_type=notification_type,
            title=title,
            message=message,
            has_image=bool(image_path),
            related_object_type=related_object_type,
            related_object_id=related_object_id
        )

        notification = self.notification_repo.create(
            self.db,
            user_id,
            notification_create
        )

        # 獲取用戶 Telegram ID
        user = self.user_repo.get_by_id(self.db, user_id)
        chat_id = user.telegram_id

        try:
            # 發送消息
            telegram_message_id = None

            # 組合消息（標題 + 內容）
            full_message = f"<b>{title}</b>\n\n{message}"

            if image_path:
                # 發送圖片 + 標題
                telegram_message_id = await telegram_client.send_photo(
                    chat_id=chat_id,
                    photo_path=image_path,
                    caption=full_message,
                    parse_mode="HTML"
                )
            else:
                # 僅發送文字
                telegram_message_id = await telegram_client.send_message(
                    chat_id=chat_id,
                    text=full_message,
                    parse_mode="HTML"
                )

            if telegram_message_id:
                # 更新通知狀態為已發送
                self.notification_repo.update_status(
                    self.db,
                    notification,
                    status="sent",
                    telegram_message_id=telegram_message_id
                )

                logger.info(
                    f"✅ Notification sent to user {user_id}: "
                    f"notification_id={notification.id}, "
                    f"telegram_message_id={telegram_message_id}"
                )

                return {
                    "success": True,
                    "notification_id": notification.id,
                    "telegram_message_id": telegram_message_id,
                    "error": None
                }
            else:
                # 發送失敗
                self.notification_repo.update_status(
                    self.db,
                    notification,
                    status="failed",
                    error_message="Failed to send Telegram message"
                )

                return {
                    "success": False,
                    "notification_id": notification.id,
                    "telegram_message_id": None,
                    "error": "Failed to send Telegram message"
                }

        except Exception as e:
            error_message = str(e)
            logger.error(f"❌ Failed to send notification to user {user_id}: {error_message}")

            # 更新通知狀態為失敗
            self.notification_repo.update_status(
                self.db,
                notification,
                status="failed",
                error_message=error_message
            )

            return {
                "success": False,
                "notification_id": notification.id,
                "telegram_message_id": None,
                "error": error_message
            }

    def get_user_notifications(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, any]:
        """
        獲取用戶的通知歷史

        Args:
            user_id: 用戶 ID
            limit: 每頁數量
            offset: 偏移量

        Returns:
            {total, notifications}
        """
        notifications = self.notification_repo.get_by_user(
            self.db,
            user_id,
            limit=limit,
            offset=offset
        )

        total = self.notification_repo.count_by_user(self.db, user_id)

        return {
            "total": total,
            "notifications": notifications
        }

    def get_user_preferences(self, user_id: int):
        """獲取用戶通知偏好"""
        return self.preference_repo.get_or_create(self.db, user_id)

    def update_user_preferences(self, user_id: int, preferences_update):
        """更新用戶通知偏好"""
        preferences = self.preference_repo.get_or_create(self.db, user_id)
        return self.preference_repo.update(self.db, preferences, preferences_update)
