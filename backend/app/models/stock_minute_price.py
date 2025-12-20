"""
Stock Minute Price Model

分鐘級股票價格數據模型，支援多種時間粒度（1min, 5min, 15min, 30min, 60min）

IMPORTANT: Timezone Strategy
-----------------------------
This table uses TIMESTAMP WITHOUT TIME ZONE (naive datetime) with Taiwan time.
- datetime: Taiwan time (no timezone info)
- created_at: Taiwan time (no timezone info)

This is a design decision due to TimescaleDB limitations (60M+ rows, compressed).
See TIMEZONE_STRATEGY.md for details.
"""
from sqlalchemy import Column, String, TIMESTAMP, Numeric, BigInteger, Integer, Index, PrimaryKeyConstraint, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class StockMinutePrice(Base):
    """分鐘級股票價格資料表（TimescaleDB hypertable）"""

    __tablename__ = "stock_minute_prices"

    # 複合主鍵
    stock_id = Column(String(10), ForeignKey("stocks.stock_id"), nullable=False)
    datetime = Column(TIMESTAMP, nullable=False)
    timeframe = Column(String(10), nullable=False, default='1min')

    # OHLCV 數據
    open = Column(Numeric(10, 2), nullable=False)
    high = Column(Numeric(10, 2), nullable=False)
    low = Column(Numeric(10, 2), nullable=False)
    close = Column(Numeric(10, 2), nullable=False)
    volume = Column(BigInteger, nullable=False)

    # 可選欄位
    adj_close = Column(Numeric(10, 2), nullable=True, comment="調整後收盤價")
    trades_count = Column(Integer, nullable=True, comment="成交筆數")

    # 時間戳記（使用資料庫當前時間，即台灣時間）
    # 注意：PostgreSQL 設定為 UTC，但此表儲存台灣時間（設計決策）
    # 實際插入時會由應用層提供台灣時間，此 server_default 僅作為備用
    created_at = Column(TIMESTAMP, server_default=func.now())

    # 關聯（移除 back_populates 避免循環參考）
    stock = relationship("Stock")

    # 表設定
    __table_args__ = (
        PrimaryKeyConstraint('stock_id', 'datetime', 'timeframe', name='pk_stock_minute_prices'),
        Index('idx_stock_minute_prices_datetime', 'datetime'),
        Index('idx_stock_minute_prices_stock_datetime', 'stock_id', 'datetime'),
        Index('idx_stock_minute_prices_timeframe', 'timeframe'),
        Index('idx_stock_minute_prices_stock_timeframe_datetime', 'stock_id', 'timeframe', 'datetime'),
        {'comment': '分鐘級股票價格資料表（支援 TimescaleDB hypertable）'}
    )

    def __repr__(self):
        return f"<StockMinutePrice(stock_id='{self.stock_id}', datetime={self.datetime}, timeframe='{self.timeframe}', close={self.close})>"
