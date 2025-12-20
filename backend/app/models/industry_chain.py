"""
FinMind Industry Chain Models

存儲 FinMind API 提供的產業鏈數據
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone

from app.db.base import Base


class IndustryChain(Base):
    """
    FinMind 產業鏈分類模型

    FinMind 使用不同於 TWSE 的產業分類體系，
    這個模型用於存儲 FinMind 的產業鏈數據
    """
    __tablename__ = "industry_chains"

    id = Column(Integer, primary_key=True, index=True)
    chain_name = Column(String(100), unique=True, nullable=False, index=True,
                       comment="產業鏈名稱")
    description = Column(String(500), comment="產業鏈描述")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    stocks = relationship("StockIndustryChain", back_populates="industry_chain")


class StockIndustryChain(Base):
    """
    股票與 FinMind 產業鏈的關聯表

    一個股票可以屬於多個產業鏈
    """
    __tablename__ = "stock_industry_chains"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(String(10), nullable=False, index=True, comment="股票代號")
    chain_name = Column(String(100), ForeignKey('industry_chains.chain_name'),
                       nullable=False, comment="產業鏈名稱")
    is_primary = Column(Boolean, default=False, comment="是否為主要產業鏈")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    industry_chain = relationship("IndustryChain", back_populates="stocks")

    # Constraints
    __table_args__ = (
        UniqueConstraint('stock_id', 'chain_name', name='uix_stock_chain'),
    )

    def __repr__(self):
        return f"<StockIndustryChain {self.stock_id} - {self.chain_name}>"


class CustomIndustryCategory(Base):
    """
    自定義產業分類模型

    允許用戶創建自己的產業分類體系
    """
    __tablename__ = "custom_industry_categories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False,
                    comment="創建者用戶 ID")
    category_name = Column(String(100), nullable=False, index=True,
                          comment="分類名稱")
    description = Column(String(500), comment="分類描述")
    parent_id = Column(Integer, ForeignKey('custom_industry_categories.id'),
                      comment="父分類 ID（支援階層結構）")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    parent = relationship("CustomIndustryCategory", remote_side=[id],
                         backref="children")
    stocks = relationship("StockCustomCategory", back_populates="category")

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'category_name', name='uix_user_category'),
    )

    def __repr__(self):
        return f"<CustomIndustryCategory {self.category_name}>"


class StockCustomCategory(Base):
    """
    股票與自定義產業分類的關聯表
    """
    __tablename__ = "stock_custom_categories"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey('custom_industry_categories.id'),
                        nullable=False, comment="自定義分類 ID")
    stock_id = Column(String(10), nullable=False, index=True, comment="股票代號")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    category = relationship("CustomIndustryCategory", back_populates="stocks")

    # Constraints
    __table_args__ = (
        UniqueConstraint('category_id', 'stock_id', name='uix_category_stock'),
    )

    def __repr__(self):
        return f"<StockCustomCategory {self.category_id} - {self.stock_id}>"
