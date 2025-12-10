from sqlalchemy import Column, Integer, String, Date, Numeric, DateTime, ForeignKey, Enum, Index, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base


class BacktestStatus(str, enum.Enum):
    """回測狀態枚舉"""
    PENDING = "PENDING"      # 待執行
    RUNNING = "RUNNING"      # 執行中
    COMPLETED = "COMPLETED"  # 已完成
    FAILED = "FAILED"        # 失敗
    CANCELLED = "CANCELLED"  # 已取消


class Backtest(Base):
    """回測記錄模型"""
    __tablename__ = "backtests"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # 回測配置
    name = Column(String(200), nullable=False, comment="回測名稱")
    description = Column(Text, nullable=True, comment="回測描述")
    symbol = Column(String(20), nullable=False, comment="股票代碼")
    parameters = Column(JSON, nullable=True, default={}, comment="策略參數")

    start_date = Column(Date, nullable=False, comment="回測開始日期")
    end_date = Column(Date, nullable=False, comment="回測結束日期")
    initial_capital = Column(Numeric(15, 2), nullable=False, default=1000000, comment="初始資金")

    # 回測引擎類型
    engine_type = Column(
        String(20),
        nullable=False,
        comment="使用的回測引擎：backtrader 或 qlib"
    )

    # 狀態與執行資訊
    status = Column(
        Enum(BacktestStatus, native_enum=False, length=20),
        default=BacktestStatus.PENDING,
        nullable=False,
        comment="回測狀態"
    )
    error_message = Column(Text, nullable=True, comment="錯誤訊息（如果失敗）")

    # 執行時間記錄
    started_at = Column(DateTime(timezone=True), nullable=True, comment="開始執行時間")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="完成執行時間")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    strategy = relationship("Strategy", back_populates="backtests")
    user = relationship("User", backref="backtests")
    result = relationship("BacktestResult", back_populates="backtest", uselist=False, cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="backtest", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_backtest_strategy_id', 'strategy_id'),
        Index('idx_backtest_user_id', 'user_id'),
        Index('idx_backtest_status', 'status'),
        Index('idx_backtest_created_at', 'created_at'),
        Index('idx_backtest_dates', 'start_date', 'end_date'),
        Index('idx_backtest_symbol', 'symbol'),
        # Composite indexes for common queries
        Index('idx_backtest_user_status', 'user_id', 'status'),
        Index('idx_backtest_user_created', 'user_id', 'created_at'),
        Index('idx_backtest_strategy_created', 'strategy_id', 'created_at'),
    )

    def __repr__(self):
        return f"<Backtest(id={self.id}, name={self.name}, status={self.status})>"
