"""
Telegram-related Pydantic schemas for request/response validation
"""

from typing import Optional
from datetime import datetime, time
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class NotificationChannel(str, Enum):
    """通知渠道枚举"""
    TELEGRAM = "telegram"
    EMAIL = "email"


class NotificationType(str, Enum):
    """通知類型枚舉"""
    BACKTEST_COMPLETED = "backtest_completed"
    RDAGENT_COMPLETED = "rdagent_completed"
    MARKET_ALERT = "market_alert"
    SYSTEM_ALERT = "system_alert"
    TRADING_SIGNAL = "trading_signal"  # 交易信號


class NotificationStatus(str, Enum):
    """通知狀態枚舉"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


# ===== Telegram Binding =====

class TelegramBindingRequest(BaseModel):
    """請求生成 Telegram 綁定驗證碼"""
    pass  # No input needed, just needs authentication


class TelegramBindingResponse(BaseModel):
    """Telegram 綁定驗證碼響應"""
    verification_code: str = Field(..., description="6位驗證碼")
    expires_in: int = Field(default=600, description="過期時間（秒）")
    bot_username: str = Field(..., description="Bot 用戶名")
    instructions: str = Field(
        default="請在 Telegram 中搜尋 @{bot_username}，發送 /bind {code}",
        description="綁定說明"
    )


class TelegramBindingCheckResponse(BaseModel):
    """Telegram 綁定狀態檢查響應"""
    is_bound: bool = Field(..., description="是否已綁定")
    telegram_id: Optional[str] = Field(None, description="Telegram Chat ID")
    bound_at: Optional[datetime] = Field(None, description="綁定時間")


class TelegramUnbindResponse(BaseModel):
    """Telegram 解綁響應"""
    success: bool
    message: str


# ===== Telegram Notifications =====

class TelegramNotificationCreate(BaseModel):
    """創建 Telegram 通知"""
    notification_type: NotificationType
    title: str = Field(..., max_length=200)
    message: str
    has_image: bool = False
    related_object_type: Optional[str] = Field(None, max_length=50)
    related_object_id: Optional[int] = None


class TelegramNotificationBase(BaseModel):
    """Telegram 通知基礎 Schema"""
    notification_type: str
    title: str
    message: str
    status: NotificationStatus
    has_image: bool = False
    related_object_type: Optional[str] = None
    related_object_id: Optional[int] = None


class TelegramNotification(TelegramNotificationBase):
    """Telegram 通知完整 Schema（響應）"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    telegram_message_id: Optional[int] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class TelegramNotificationList(BaseModel):
    """Telegram 通知列表響應"""
    total: int
    notifications: list[TelegramNotification]


# ===== Notification Preferences =====

class TelegramNotificationPreferencesBase(BaseModel):
    """通知偏好基礎 Schema"""
    notifications_enabled: bool = True
    backtest_completed_enabled: bool = True
    rdagent_completed_enabled: bool = True
    market_alert_enabled: bool = False
    quiet_hours_enabled: bool = False
    quiet_hours_start: Optional[time] = None
    quiet_hours_end: Optional[time] = None
    include_charts: bool = True


class TelegramNotificationPreferencesUpdate(BaseModel):
    """更新通知偏好"""
    notifications_enabled: Optional[bool] = None
    backtest_completed_enabled: Optional[bool] = None
    rdagent_completed_enabled: Optional[bool] = None
    market_alert_enabled: Optional[bool] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[time] = None
    quiet_hours_end: Optional[time] = None
    include_charts: Optional[bool] = None


class TelegramNotificationPreferences(TelegramNotificationPreferencesBase):
    """通知偏好完整 Schema（響應）"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


# ===== Test Notification =====

class TestNotificationRequest(BaseModel):
    """測試通知請求"""
    include_image: bool = Field(default=False, description="是否包含測試圖片")


class TestNotificationResponse(BaseModel):
    """測試通知響應"""
    success: bool
    message: str
    notification_id: Optional[int] = None
    telegram_message_id: Optional[int] = None


# ===== Notification Sending (Internal) =====

class SendNotificationRequest(BaseModel):
    """發送通知請求（內部使用）"""
    user_id: int
    notification_type: NotificationType
    title: str = Field(..., max_length=200)
    message: str
    channel: NotificationChannel = NotificationChannel.TELEGRAM
    related_object_type: Optional[str] = None
    related_object_id: Optional[int] = None
    image_path: Optional[str] = None


class SendNotificationResponse(BaseModel):
    """發送通知響應"""
    telegram_sent: bool = False
    email_sent: bool = False
    notification_id: Optional[int] = None
    errors: list[str] = []
