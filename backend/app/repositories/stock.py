"""
Stock repository for database operations
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.stock import Stock
from app.utils.query_helpers import escape_like_pattern
from app.schemas.stock import StockCreate, StockUpdate


class StockRepository:
    """Repository for stock database operations"""

    @staticmethod
    def get_by_id(db: Session, stock_id: str) -> Optional[Stock]:
        """Get stock by stock_id"""
        return db.query(Stock).filter(Stock.stock_id == stock_id).first()

    @staticmethod
    def get_all(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[str] = None
    ) -> List[Stock]:
        """
        Get all stocks with pagination

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            is_active: Filter by active status

        Returns:
            List of stocks
        """
        query = db.query(Stock)

        if is_active:
            query = query.filter(Stock.is_active == is_active)

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def count(db: Session, is_active: Optional[str] = None) -> int:
        """Count total stocks"""
        query = db.query(Stock)

        if is_active:
            query = query.filter(Stock.is_active == is_active)

        return query.count()

    @staticmethod
    def search(
        db: Session,
        keyword: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Stock]:
        """
        Search stocks by stock_id or name

        Args:
            db: Database session
            keyword: Search keyword
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of matching stocks
        """
        # 轉義特殊字符，防止萬用字元注入
        safe_keyword = escape_like_pattern(keyword)
        search_pattern = f"%{safe_keyword}%"

        return (
            db.query(Stock)
            .filter(
                or_(
                    Stock.stock_id.ilike(search_pattern),
                    Stock.name.ilike(search_pattern)
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_category(
        db: Session,
        category: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Stock]:
        """Get stocks by category"""
        return (
            db.query(Stock)
            .filter(Stock.category == category)
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_market(
        db: Session,
        market: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Stock]:
        """Get stocks by market"""
        return (
            db.query(Stock)
            .filter(Stock.market == market)
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def create(db: Session, stock_create: StockCreate) -> Stock:
        """
        Create new stock

        Args:
            db: Database session
            stock_create: Stock creation data

        Returns:
            Created stock object
        """
        db_stock = Stock(
            stock_id=stock_create.stock_id,
            name=stock_create.name,
            category=stock_create.category,
            market=stock_create.market,
            is_active=stock_create.is_active,
        )

        db.add(db_stock)
        db.commit()
        db.refresh(db_stock)

        return db_stock

    @staticmethod
    def create_bulk(db: Session, stocks: List[StockCreate]) -> List[Stock]:
        """
        Bulk create stocks

        Args:
            db: Database session
            stocks: List of stock creation data

        Returns:
            List of created stocks
        """
        db_stocks = [
            Stock(
                stock_id=stock.stock_id,
                name=stock.name,
                category=stock.category,
                market=stock.market,
                is_active=stock.is_active,
            )
            for stock in stocks
        ]

        db.bulk_save_objects(db_stocks)
        db.commit()

        return db_stocks

    @staticmethod
    def update(db: Session, stock: Stock, stock_update: StockUpdate) -> Stock:
        """
        Update stock

        Args:
            db: Database session
            stock: Existing stock object
            stock_update: Update data

        Returns:
            Updated stock object
        """
        update_data = stock_update.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(stock, field, value)

        db.add(stock)
        db.commit()
        db.refresh(stock)

        return stock

    @staticmethod
    def delete(db: Session, stock: Stock) -> None:
        """
        Delete stock

        Args:
            db: Database session
            stock: Stock to delete
        """
        db.delete(stock)
        db.commit()

    @staticmethod
    def exists(db: Session, stock_id: str) -> bool:
        """Check if stock exists"""
        return db.query(Stock).filter(Stock.stock_id == stock_id).count() > 0
