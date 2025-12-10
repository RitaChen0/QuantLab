from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Index, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base


class StrategyStatus(str, enum.Enum):
    """策略狀態枚舉"""
    DRAFT = "draft"          # 草稿
    ACTIVE = "active"        # 已啟用
    ARCHIVED = "archived"    # 已封存


class Strategy(Base):
    """交易策略模型"""
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # 策略基本資訊
    name = Column(String(200), nullable=False, comment="策略名稱")
    description = Column(Text, nullable=True, comment="策略描述")
    code = Column(Text, nullable=False, comment="策略代碼（Python）")

    # 策略參數（JSON 格式，用於存儲策略配置）
    parameters = Column(JSON, nullable=True, comment="策略參數")

    # 回測引擎類型
    engine_type = Column(
        String(20),
        default='backtrader',
        nullable=False,
        comment="回測引擎類型：backtrader 或 qlib"
    )

    # 狀態
    status = Column(
        Enum(StrategyStatus, native_enum=False, length=20),
        default=StrategyStatus.DRAFT,
        nullable=False,
        comment="策略狀態"
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="strategies")
    backtests = relationship("Backtest", back_populates="strategy", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_strategy_user_id', 'user_id'),
        Index('idx_strategy_status', 'status'),
        Index('idx_strategy_created_at', 'created_at'),
        # Composite indexes for common queries
        Index('idx_strategy_user_status', 'user_id', 'status'),
        Index('idx_strategy_user_created', 'user_id', 'created_at'),
        # GIN index for name search (PostgreSQL ILIKE optimization)
        Index('idx_strategy_name_gin', 'name', postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'}),
    )

    def __repr__(self):
        return f"<Strategy(id={self.id}, name={self.name}, status={self.status})>"
