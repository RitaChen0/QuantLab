"""
Institutional Investor Model
三大法人買賣超資料模型
"""

from sqlalchemy import Column, Integer, String, BigInteger, Date, DateTime, ForeignKey, Computed
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class InstitutionalInvestor(Base):
    """法人買賣超資料模型"""

    __tablename__ = "institutional_investors"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True, comment="日期")
    stock_id = Column(
        String(10),
        ForeignKey("stocks.stock_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="股票代碼"
    )
    investor_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="法人類型 (Foreign_Investor, Investment_Trust, Dealer_self, Dealer_Hedging, Foreign_Dealer_Self)"
    )
    buy_volume = Column(BigInteger, nullable=False, comment="買進股數")
    sell_volume = Column(BigInteger, nullable=False, comment="賣出股數")
    net_buy_sell = Column(
        BigInteger,
        Computed("buy_volume - sell_volume"),
        comment="買賣超（正數=買超，負數=賣超）"
    )
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # 關聯
    stock = relationship("Stock", back_populates="institutional_investors")

    def __repr__(self):
        return (
            f"<InstitutionalInvestor(date={self.date}, stock_id={self.stock_id}, "
            f"type={self.investor_type}, net={self.net_buy_sell})>"
        )
