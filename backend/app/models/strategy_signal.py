"""
策略信號模型

記錄實盤監控中檢測到的買賣信號
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Index, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class StrategySignal(Base):
    """策略信號記錄"""
    __tablename__ = "strategy_signals"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # 信號基本資訊
    stock_id = Column(String(20), nullable=False, comment="股票代碼")
    signal_type = Column(String(10), nullable=False, comment="信號類型：BUY 或 SELL")

    # 價格資訊
    price = Column(Numeric(12, 2), nullable=True, comment="檢測時的價格")

    # 信號原因（可選，用於顯示策略邏輯）
    reason = Column(Text, nullable=True, comment="信號產生原因")

    # 通知狀態
    notified = Column(Boolean, default=False, nullable=False, comment="是否已通知用戶")
    notified_at = Column(DateTime(timezone=True), nullable=True, comment="通知時間")

    # Timestamps
    detected_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="信號檢測時間"
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    strategy = relationship("Strategy", backref="signals")
    user = relationship("User", backref="strategy_signals")

    # Indexes
    __table_args__ = (
        # 查詢用戶的所有信號
        Index('idx_signal_user_id', 'user_id'),
        # 查詢策略的所有信號
        Index('idx_signal_strategy_id', 'strategy_id'),
        # 查詢特定股票的信號
        Index('idx_signal_stock_id', 'stock_id'),
        # 查詢未通知的信號
        Index('idx_signal_notified', 'notified'),
        # 查詢信號時間
        Index('idx_signal_detected_at', 'detected_at'),
        # 複合索引：用於重複信號檢測（15分鐘內相同股票相同方向）
        Index('idx_signal_dedup', 'strategy_id', 'stock_id', 'signal_type', 'detected_at'),
        # 複合索引：用戶 + 時間範圍查詢
        Index('idx_signal_user_time', 'user_id', 'detected_at'),
    )

    def __repr__(self):
        return (
            f"<StrategySignal(id={self.id}, strategy_id={self.strategy_id}, "
            f"stock={self.stock_id}, type={self.signal_type}, price={self.price})>"
        )
