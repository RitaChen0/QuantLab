from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Industry(Base):
    """
    產業分類模型

    支持層級結構的產業分類（大類 → 中類 → 小類）
    """
    __tablename__ = "industries"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True, comment="產業代碼")
    name_zh = Column(String(100), nullable=False, comment="中文名稱")
    name_en = Column(String(100), comment="英文名稱")
    parent_code = Column(String(20), ForeignKey('industries.code'), comment="父產業代碼")
    level = Column(Integer, default=1, comment="產業層級 (1=大類, 2=中類, 3=小類)")
    description = Column(Text, comment="產業描述")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 關聯
    parent = relationship("Industry", remote_side=[code], backref="children")
    stock_industries = relationship("StockIndustry", back_populates="industry")

    def __repr__(self):
        return f"<Industry(code={self.code}, name_zh={self.name_zh}, level={self.level})>"
