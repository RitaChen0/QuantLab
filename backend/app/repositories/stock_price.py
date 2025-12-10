"""
StockPrice repository for database operations
"""

from typing import Optional, List
from datetime import date as DateType
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.models.stock_price import StockPrice
from app.schemas.stock_price import StockPriceCreate, StockPriceUpdate


class StockPriceRepository:
    """Repository for stock price database operations"""

    @staticmethod
    def get_by_stock_and_date(
        db: Session,
        stock_id: str,
        date: DateType
    ) -> Optional[StockPrice]:
        """Get stock price by stock_id and date"""
        return (
            db.query(StockPrice)
            .filter(
                and_(
                    StockPrice.stock_id == stock_id,
                    StockPrice.date == date
                )
            )
            .first()
        )

    @staticmethod
    def get_by_stock(
        db: Session,
        stock_id: str,
        start_date: Optional[DateType] = None,
        end_date: Optional[DateType] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[StockPrice]:
        """
        Get stock prices for a specific stock

        Args:
            db: Database session
            stock_id: Stock ID
            start_date: Start date (optional)
            end_date: End date (optional)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of stock prices
        """
        query = db.query(StockPrice).filter(StockPrice.stock_id == stock_id)

        if start_date:
            query = query.filter(StockPrice.date >= start_date)

        if end_date:
            query = query.filter(StockPrice.date <= end_date)

        return query.order_by(desc(StockPrice.date)).offset(skip).limit(limit).all()

    @staticmethod
    def get_latest(db: Session, stock_id: str) -> Optional[StockPrice]:
        """Get latest stock price for a stock"""
        return (
            db.query(StockPrice)
            .filter(StockPrice.stock_id == stock_id)
            .order_by(desc(StockPrice.date))
            .first()
        )

    @staticmethod
    def get_by_date_range(
        db: Session,
        start_date: DateType,
        end_date: DateType,
        stock_ids: Optional[List[str]] = None
    ) -> List[StockPrice]:
        """
        Get stock prices within a date range

        Args:
            db: Database session
            start_date: Start date
            end_date: End date
            stock_ids: Optional list of stock IDs to filter

        Returns:
            List of stock prices
        """
        query = db.query(StockPrice).filter(
            and_(
                StockPrice.date >= start_date,
                StockPrice.date <= end_date
            )
        )

        if stock_ids:
            query = query.filter(StockPrice.stock_id.in_(stock_ids))

        return query.order_by(StockPrice.date).all()

    @staticmethod
    def create(db: Session, price_create: StockPriceCreate) -> StockPrice:
        """
        Create new stock price

        Args:
            db: Database session
            price_create: Stock price creation data

        Returns:
            Created stock price object
        """
        db_price = StockPrice(
            stock_id=price_create.stock_id,
            date=price_create.date,
            open=price_create.open,
            high=price_create.high,
            low=price_create.low,
            close=price_create.close,
            volume=price_create.volume,
            adj_close=price_create.adj_close,
        )

        db.add(db_price)
        db.commit()
        db.refresh(db_price)

        return db_price

    @staticmethod
    def create_bulk(db: Session, prices: List[StockPriceCreate]) -> int:
        """
        Bulk create stock prices

        Args:
            db: Database session
            prices: List of stock price creation data

        Returns:
            Number of records created
        """
        db_prices = [
            StockPrice(
                stock_id=price.stock_id,
                date=price.date,
                open=price.open,
                high=price.high,
                low=price.low,
                close=price.close,
                volume=price.volume,
                adj_close=price.adj_close,
            )
            for price in prices
        ]

        db.bulk_save_objects(db_prices)
        db.commit()

        return len(db_prices)

    @staticmethod
    def update(
        db: Session,
        stock_price: StockPrice,
        price_update: StockPriceUpdate
    ) -> StockPrice:
        """
        Update stock price

        Args:
            db: Database session
            stock_price: Existing stock price object
            price_update: Update data

        Returns:
            Updated stock price object
        """
        update_data = price_update.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(stock_price, field, value)

        db.add(stock_price)
        db.commit()
        db.refresh(stock_price)

        return stock_price

    @staticmethod
    def upsert(db: Session, price_create: StockPriceCreate) -> StockPrice:
        """
        Upsert (insert or update) stock price

        Args:
            db: Database session
            price_create: Stock price data

        Returns:
            Stock price object
        """
        existing = StockPriceRepository.get_by_stock_and_date(
            db, price_create.stock_id, price_create.date
        )

        if existing:
            # Update existing record
            for field, value in price_create.model_dump().items():
                if field not in ['stock_id', 'date']:  # Skip primary keys
                    setattr(existing, field, value)
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # Create new record
            return StockPriceRepository.create(db, price_create)

    @staticmethod
    def delete(db: Session, stock_price: StockPrice) -> None:
        """
        Delete stock price

        Args:
            db: Database session
            stock_price: Stock price to delete
        """
        db.delete(stock_price)
        db.commit()

    @staticmethod
    def delete_by_stock(db: Session, stock_id: str) -> int:
        """
        Delete all prices for a stock

        Args:
            db: Database session
            stock_id: Stock ID

        Returns:
            Number of records deleted
        """
        count = db.query(StockPrice).filter(StockPrice.stock_id == stock_id).delete()
        db.commit()
        return count
