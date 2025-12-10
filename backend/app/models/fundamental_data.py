from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint, Index
from sqlalchemy.sql import func
from app.db.base import Base


class FundamentalData(Base):
    """
    財務指標數據模型

    存儲股票的財務指標歷史數據，支持季度和年度數據
    """
    __tablename__ = "fundamental_data"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(String(10), nullable=False, index=True, comment="股票代號")
    indicator = Column(String(50), nullable=False, index=True, comment="財務指標名稱")
    date = Column(String(20), nullable=False, comment="數據日期 (e.g., 2024-Q1, 2024-Q2)")
    value = Column(Float, nullable=True, comment="指標數值")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="創建時間")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新時間")

    # 複合唯一約束：同一股票、同一指標、同一日期只能有一筆記錄
    __table_args__ = (
        UniqueConstraint('stock_id', 'indicator', 'date', name='uix_stock_indicator_date'),
        Index('ix_stock_indicator', 'stock_id', 'indicator'),
        Index('ix_indicator_date', 'indicator', 'date'),
    )

    def __repr__(self):
        return f"<FundamentalData(stock_id={self.stock_id}, indicator={self.indicator}, date={self.date}, value={self.value})>"
