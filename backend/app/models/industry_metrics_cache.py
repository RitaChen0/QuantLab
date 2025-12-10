from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.sql import func
from app.db.base import Base


class IndustryMetricsCache(Base):
    """
    產業聚合指標快取表

    存儲計算好的產業平均指標（如平均ROE、平均EPS等）
    避免每次請求都重新計算
    """
    __tablename__ = "industry_metrics_cache"

    id = Column(Integer, primary_key=True, index=True)
    industry_code = Column(String(20), ForeignKey('industries.code'), nullable=False, comment="產業代碼")
    date = Column(Date, nullable=False, comment="數據日期")
    metric_name = Column(String(50), nullable=False, comment="指標名稱 (如 avg_roe, avg_eps)")
    value = Column(Numeric, comment="指標值")
    stocks_count = Column(Integer, comment="計算基礎的股票數量")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 唯一約束和索引
    __table_args__ = (
        UniqueConstraint('industry_code', 'date', 'metric_name', name='uix_industry_metric'),
        Index('ix_industry_metrics_code_date', 'industry_code', 'date'),
        Index('ix_industry_metrics_name', 'metric_name'),
    )

    def __repr__(self):
        return f"<IndustryMetricsCache(industry_code={self.industry_code}, metric={self.metric_name}, date={self.date}, value={self.value})>"
