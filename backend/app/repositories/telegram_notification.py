"""
Telegram Notification repository for database operations
"""

from typing import Optional, List
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.telegram_notification import TelegramNotification, TelegramNotificationPreference
from app.schemas.telegram import (
    TelegramNotificationCreate,
    TelegramNotificationPreferencesUpdate
)


class TelegramNotificationRepository:
    """Repository for telegram notification database operations"""

    @staticmethod
    def get_by_id(db: Session, notification_id: int) -> Optional[TelegramNotification]:
        """Get notification by ID"""
        return db.query(TelegramNotification).filter(
            TelegramNotification.id == notification_id
        ).first()

    @staticmethod
    def get_by_user(
        db: Session,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[TelegramNotification]:
        """
        Get notifications by user ID

        Args:
            db: Database session
            user_id: User ID
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of notifications (newest first)
        """
        return (
            db.query(TelegramNotification)
            .filter(TelegramNotification.user_id == user_id)
            .order_by(desc(TelegramNotification.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

    @staticmethod
    def get_by_status(
        db: Session,
        status: str,
        limit: int = 100
    ) -> List[TelegramNotification]:
        """
        Get notifications by status

        Args:
            db: Database session
            status: Notification status (pending, sent, failed)
            limit: Maximum number of results

        Returns:
            List of notifications
        """
        return (
            db.query(TelegramNotification)
            .filter(TelegramNotification.status == status)
            .order_by(TelegramNotification.created_at)
            .limit(limit)
            .all()
        )

    @staticmethod
    def count_by_user(db: Session, user_id: int) -> int:
        """Count total notifications for a user"""
        return (
            db.query(TelegramNotification)
            .filter(TelegramNotification.user_id == user_id)
            .count()
        )

    @staticmethod
    def create(
        db: Session,
        user_id: int,
        notification_create: TelegramNotificationCreate
    ) -> TelegramNotification:
        """
        Create new notification

        Args:
            db: Database session
            user_id: User ID
            notification_create: Notification creation data

        Returns:
            Created notification object
        """
        db_notification = TelegramNotification(
            user_id=user_id,
            notification_type=notification_create.notification_type,
            title=notification_create.title,
            message=notification_create.message,
            has_image=notification_create.has_image,
            related_object_type=notification_create.related_object_type,
            related_object_id=notification_create.related_object_id,
            status="pending"
        )

        db.add(db_notification)
        db.commit()
        db.refresh(db_notification)

        return db_notification

    @staticmethod
    def update_status(
        db: Session,
        notification: TelegramNotification,
        status: str,
        telegram_message_id: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> TelegramNotification:
        """
        Update notification status

        Args:
            db: Database session
            notification: Notification object
            status: New status (sent, failed)
            telegram_message_id: Telegram message ID (if sent)
            error_message: Error message (if failed)

        Returns:
            Updated notification object
        """
        notification.status = status

        if telegram_message_id:
            notification.telegram_message_id = telegram_message_id

        if error_message:
            notification.error_message = error_message

        if status == "sent":
            notification.sent_at = datetime.now(timezone.utc)

        db.add(notification)
        db.commit()
        db.refresh(notification)

        return notification

    @staticmethod
    def delete(db: Session, notification: TelegramNotification) -> None:
        """Delete notification"""
        db.delete(notification)
        db.commit()

    @staticmethod
    def delete_old_notifications(
        db: Session,
        user_id: int,
        days: int = 90
    ) -> int:
        """
        Delete notifications older than specified days

        Args:
            db: Database session
            user_id: User ID
            days: Number of days to keep

        Returns:
            Number of deleted notifications
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        deleted_count = (
            db.query(TelegramNotification)
            .filter(
                TelegramNotification.user_id == user_id,
                TelegramNotification.created_at < cutoff_date
            )
            .delete()
        )

        db.commit()
        return deleted_count


class TelegramNotificationPreferenceRepository:
    """Repository for telegram notification preferences"""

    @staticmethod
    def get_by_user(db: Session, user_id: int) -> Optional[TelegramNotificationPreference]:
        """Get preferences by user ID"""
        return db.query(TelegramNotificationPreference).filter(
            TelegramNotificationPreference.user_id == user_id
        ).first()

    @staticmethod
    def get_or_create(
        db: Session,
        user_id: int
    ) -> TelegramNotificationPreference:
        """
        Get preferences or create default if not exists

        Args:
            db: Database session
            user_id: User ID

        Returns:
            User's notification preferences
        """
        preferences = TelegramNotificationPreferenceRepository.get_by_user(db, user_id)

        if not preferences:
            preferences = TelegramNotificationPreference(
                user_id=user_id,
                notifications_enabled=True,
                backtest_completed_enabled=True,
                rdagent_completed_enabled=True,
                market_alert_enabled=False,
                quiet_hours_enabled=False,
                include_charts=True
            )
            db.add(preferences)
            db.commit()
            db.refresh(preferences)

        return preferences

    @staticmethod
    def update(
        db: Session,
        preferences: TelegramNotificationPreference,
        preferences_update: TelegramNotificationPreferencesUpdate
    ) -> TelegramNotificationPreference:
        """
        Update preferences

        Args:
            db: Database session
            preferences: Existing preferences object
            preferences_update: Update data

        Returns:
            Updated preferences object
        """
        update_data = preferences_update.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(preferences, field, value)

        db.add(preferences)
        db.commit()
        db.refresh(preferences)

        return preferences

    @staticmethod
    def delete(db: Session, preferences: TelegramNotificationPreference) -> None:
        """Delete preferences (resets to default)"""
        db.delete(preferences)
        db.commit()
