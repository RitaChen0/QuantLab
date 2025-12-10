from sqlalchemy import Column, Integer, String, Date, Numeric, DateTime, ForeignKey, Enum, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base


class TradeAction(str, enum.Enum):
    """交易動作枚舉"""
    BUY = "BUY"      # 買入
    SELL = "SELL"    # 賣出


class Trade(Base):
    """回測交易記錄模型"""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    backtest_id = Column(Integer, ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False)
    stock_id = Column(String(10), ForeignKey("stocks.stock_id", ondelete="CASCADE"), nullable=False)

    # 交易資訊
    date = Column(Date, nullable=False, comment="交易日期")
    action = Column(
        Enum(TradeAction, native_enum=False, length=10),
        nullable=False,
        comment="交易動作（buy/sell）"
    )

    quantity = Column(Integer, nullable=False, comment="交易數量（股數）")
    price = Column(Numeric(10, 2), nullable=False, comment="交易價格")

    # 交易成本
    commission = Column(Numeric(10, 2), default=0, nullable=False, comment="手續費")
    tax = Column(Numeric(10, 2), default=0, nullable=False, comment="交易稅")

    # 交易結果
    total_amount = Column(Numeric(15, 2), nullable=False, comment="交易總額")
    profit_loss = Column(Numeric(15, 2), nullable=True, comment="獲利/虧損（僅 sell 時計算）")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    backtest = relationship("Backtest", back_populates="trades")
    stock = relationship("Stock", back_populates="trades")

    # Indexes
    __table_args__ = (
        Index('idx_trade_backtest_id', 'backtest_id'),
        Index('idx_trade_stock_id', 'stock_id'),
        Index('idx_trade_date', 'date'),
        Index('idx_trade_backtest_date', 'backtest_id', 'date'),
    )

    def __repr__(self):
        return f"<Trade(id={self.id}, stock_id={self.stock_id}, action={self.action}, quantity={self.quantity})>"
