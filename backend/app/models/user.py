from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
from app.utils.encryption import EncryptedText


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    # Member Level and Balance
    member_level = Column(Integer, default=0, nullable=False)  # 0=免費, 3=付費, 6=VIP
    cash = Column(Numeric(15, 2), default=0.00, nullable=False)  # 現金餘額
    credit = Column(Numeric(15, 2), default=0.00, nullable=False)  # 信用點數

    # Telegram Integration
    telegram_id = Column(String(255), nullable=True, index=True)  # Telegram 用戶 ID 或用戶名
    telegram_channel_id = Column(String(255), nullable=True)  # TG 頻道/群組 ID

    # Email Verification
    email_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255), nullable=True, unique=True)
    verification_token_expires = Column(DateTime(timezone=True), nullable=True)
    last_verification_token = Column(String(255), nullable=True)  # 記錄最後一次驗證的 token（用於友善錯誤處理）

    # FinLab API Token (optional, encrypted with Fernet)
    finlab_api_token = Column(EncryptedText(), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    strategies = relationship("Strategy", back_populates="user", cascade="all, delete-orphan")
    rdagent_tasks = relationship("RDAgentTask", back_populates="user", cascade="all, delete-orphan")
    telegram_notifications = relationship("TelegramNotification", back_populates="user", cascade="all, delete-orphan")
    telegram_notification_preferences = relationship("TelegramNotificationPreference", back_populates="user", cascade="all, delete-orphan", uselist=False)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"
