from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Stock(Base):
    """股票基本資料模型"""
    __tablename__ = "stocks"

    # 使用股票代碼作為主鍵（如 "2330"）
    stock_id = Column(String(10), primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="股票名稱")
    category = Column(String(50), nullable=True, comment="產業分類")
    market = Column(String(20), nullable=True, comment="市場別（上市/上櫃/興櫃）")

    # 額外資訊
    is_active = Column(String(10), default="active", nullable=False, comment="狀態（active/delisted）")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    prices = relationship("StockPrice", back_populates="stock", cascade="all, delete-orphan")
    # minute_prices relationship temporarily disabled to avoid Pydantic recursion during OpenAPI schema generation
    # minute_prices = relationship("StockMinutePrice", back_populates="stock", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="stock")
    stock_industries = relationship("StockIndustry", back_populates="stock", cascade="all, delete-orphan")
    institutional_investors = relationship("InstitutionalInvestor", back_populates="stock", cascade="all, delete-orphan")
    option_daily_factors = relationship("OptionDailyFactor", back_populates="underlying", cascade="all, delete-orphan")

    # Indexes for better query performance
    __table_args__ = (
        Index('idx_stock_name', 'name'),
        Index('idx_stock_category', 'category'),
        Index('idx_stock_market', 'market'),
    )

    def __repr__(self):
        return f"<Stock(stock_id={self.stock_id}, name={self.name})>"
