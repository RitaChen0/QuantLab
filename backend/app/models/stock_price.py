from sqlalchemy import Column, String, Date, Numeric, BigInteger, ForeignKey, Index, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base


class StockPrice(Base):
    """股票歷史價格模型（OHLCV 數據）

    使用 TimescaleDB hypertable 進行時序數據優化
    複合主鍵：(stock_id, date)
    """
    __tablename__ = "stock_prices"

    # 複合主鍵
    stock_id = Column(String(10), ForeignKey("stocks.stock_id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, comment="交易日期")

    # OHLCV 數據
    open = Column(Numeric(10, 2), nullable=False, comment="開盤價")
    high = Column(Numeric(10, 2), nullable=False, comment="最高價")
    low = Column(Numeric(10, 2), nullable=False, comment="最低價")
    close = Column(Numeric(10, 2), nullable=False, comment="收盤價")
    volume = Column(BigInteger, nullable=False, comment="成交量")

    # 額外數據
    adj_close = Column(Numeric(10, 2), nullable=True, comment="調整後收盤價（考慮除權息）")

    # Relationships
    stock = relationship("Stock", back_populates="prices")

    # 複合主鍵定義
    __table_args__ = (
        PrimaryKeyConstraint('stock_id', 'date', name='pk_stock_prices'),
        # 優化查詢的索引
        Index('idx_stock_prices_date', 'date'),
        Index('idx_stock_prices_stock_date', 'stock_id', 'date'),
    )

    def __repr__(self):
        return f"<StockPrice(stock_id={self.stock_id}, date={self.date}, close={self.close})>"
