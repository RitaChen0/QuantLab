from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class StockIndustry(Base):
    """
    股票-產業關聯表

    支持多對多關係：一檔股票可屬於多個產業
    """
    __tablename__ = "stock_industries"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(String(10), ForeignKey('stocks.stock_id'), nullable=False, comment="股票代號")
    industry_code = Column(String(20), ForeignKey('industries.code'), nullable=False, comment="產業代碼")
    is_primary = Column(Boolean, default=False, comment="是否為主要產業")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 關聯
    stock = relationship("Stock", back_populates="stock_industries")
    industry = relationship("Industry", back_populates="stock_industries")

    # 唯一約束：同一股票不能重複歸類到同一產業
    __table_args__ = (
        UniqueConstraint('stock_id', 'industry_code', name='uix_stock_industry'),
    )

    def __repr__(self):
        return f"<StockIndustry(stock_id={self.stock_id}, industry_code={self.industry_code}, is_primary={self.is_primary})>"
