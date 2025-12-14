"""
Telegram Notification Models
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    BigInteger,
    DateTime,
    Time,
    ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class TelegramNotification(Base):
    """Telegram 通知歷史記錄"""

    __tablename__ = "telegram_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Notification content
    notification_type = Column(String(50), nullable=False, index=True)  # backtest_completed, rdagent_completed, market_alert
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)

    # Status tracking
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending, sent, failed
    telegram_message_id = Column(BigInteger, nullable=True)  # Telegram API返回的消息ID
    has_image = Column(Boolean, nullable=False, default=False)

    # Related object (for linking to backtest, strategy, etc.)
    related_object_type = Column(String(50), nullable=True)  # backtest, strategy, market
    related_object_id = Column(Integer, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)

    # Timestamps
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="telegram_notifications")

    def __repr__(self):
        return f"<TelegramNotification(id={self.id}, user_id={self.user_id}, type={self.notification_type}, status={self.status})>"


class TelegramNotificationPreference(Base):
    """用戶 Telegram 通知偏好設置"""

    __tablename__ = "telegram_notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Global notification switch
    notifications_enabled = Column(Boolean, nullable=False, default=True)

    # Notification type switches
    backtest_completed_enabled = Column(Boolean, nullable=False, default=True)
    rdagent_completed_enabled = Column(Boolean, nullable=False, default=True)
    market_alert_enabled = Column(Boolean, nullable=False, default=False)

    # Quiet hours
    quiet_hours_enabled = Column(Boolean, nullable=False, default=False)
    quiet_hours_start = Column(Time, nullable=True)  # e.g., 23:00
    quiet_hours_end = Column(Time, nullable=True)    # e.g., 08:00

    # Content preferences
    include_charts = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="telegram_notification_preferences")

    def __repr__(self):
        return f"<TelegramNotificationPreference(user_id={self.user_id}, enabled={self.notifications_enabled})>"
