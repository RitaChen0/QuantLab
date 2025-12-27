"""
StockPrice repository for database operations
"""

from typing import Optional, List, Tuple
from datetime import date as DateType
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from app.models.stock_price import StockPrice
from app.schemas.stock_price import StockPriceCreate, StockPriceUpdate
from app.utils.price_validator import PriceValidator, PriceValidationError
from loguru import logger


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
    def get_date_range_for_stock(
        db: Session,
        stock_id: str
    ) -> Optional[Tuple[DateType, DateType]]:
        """
        Get date range (min, max) for a specific stock

        Args:
            db: Database session
            stock_id: Stock ID

        Returns:
            Tuple of (min_date, max_date) or None if no data
        """
        result = (
            db.query(
                func.min(StockPrice.date).label('min_date'),
                func.max(StockPrice.date).label('max_date')
            )
            .filter(StockPrice.stock_id == stock_id)
            .first()
        )

        if result and result.min_date:
            return (result.min_date, result.max_date)
        return None

    @staticmethod
    def get_by_stock(
        db: Session,
        stock_id: str,
        start_date: Optional[DateType] = None,
        end_date: Optional[DateType] = None,
        skip: int = 0,
        limit: int = 100,
        ascending: bool = False
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
            ascending: Sort order (True=oldest first, False=newest first)

        Returns:
            List of stock prices
        """
        query = db.query(StockPrice).filter(StockPrice.stock_id == stock_id)

        if start_date:
            query = query.filter(StockPrice.date >= start_date)

        if end_date:
            query = query.filter(StockPrice.date <= end_date)

        # Apply ordering
        if ascending:
            query = query.order_by(StockPrice.date)
        else:
            query = query.order_by(desc(StockPrice.date))

        return query.offset(skip).limit(limit).all()

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
    def create(db: Session, price_create: StockPriceCreate, skip_validation: bool = False) -> StockPrice:
        """
        Create new stock price

        Args:
            db: Database session
            price_create: Stock price creation data
            skip_validation: 跳過價格驗證（預設 False，不建議使用）

        Returns:
            Created stock price object

        Raises:
            PriceValidationError: 如果價格數據無效
        """
        # 應用層驗證（第一層防護）
        if not skip_validation:
            is_valid, error_msg = PriceValidator.validate_price_data(
                open=price_create.open,
                high=price_create.high,
                low=price_create.low,
                close=price_create.close,
                volume=price_create.volume,
                stock_id=price_create.stock_id,
                date=str(price_create.date),
                allow_zero_placeholder=True
            )

            if not is_valid:
                logger.error(f"❌ [VALIDATION] {error_msg}")
                raise PriceValidationError(error_msg)

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
    def create_bulk(db: Session, prices: List[StockPriceCreate], skip_validation: bool = False) -> dict:
        """
        Bulk create stock prices

        Args:
            db: Database session
            prices: List of stock price creation data
            skip_validation: 跳過價格驗證（預設 False，不建議使用）

        Returns:
            包含統計信息的字典：
            - created: 成功創建的記錄數
            - skipped: 因驗證失敗而跳過的記錄數
            - total: 總輸入記錄數
        """
        valid_prices = []
        skipped_count = 0

        for price in prices:
            # 應用層驗證（第一層防護）
            if not skip_validation:
                is_valid, error_msg = PriceValidator.validate_price_data(
                    open=price.open,
                    high=price.high,
                    low=price.low,
                    close=price.close,
                    volume=price.volume,
                    stock_id=price.stock_id,
                    date=str(price.date),
                    allow_zero_placeholder=True
                )

                if not is_valid:
                    logger.warning(f"⚠️  [BULK_VALIDATION] 跳過無效記錄: {error_msg}")
                    skipped_count += 1
                    continue

            valid_prices.append(price)

        # 批量插入有效記錄
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
            for price in valid_prices
        ]

        if db_prices:
            db.bulk_save_objects(db_prices)
            db.commit()

        created_count = len(db_prices)
        if skipped_count > 0:
            logger.warning(
                f"⚠️  [BULK_VALIDATION] 批量插入完成: "
                f"{created_count} 成功, {skipped_count} 跳過, "
                f"{len(prices)} 總計"
            )

        return {
            "created": created_count,
            "skipped": skipped_count,
            "total": len(prices)
        }

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
    def upsert(db: Session, price_create: StockPriceCreate, skip_validation: bool = False) -> StockPrice:
        """
        Upsert (insert or update) stock price

        Args:
            db: Database session
            price_create: Stock price data
            skip_validation: 跳過價格驗證（預設 False，不建議使用）

        Returns:
            Stock price object

        Raises:
            PriceValidationError: 如果價格數據無效
        """
        # 應用層驗證（第一層防護）
        if not skip_validation:
            is_valid, error_msg = PriceValidator.validate_price_data(
                open=price_create.open,
                high=price_create.high,
                low=price_create.low,
                close=price_create.close,
                volume=price_create.volume,
                stock_id=price_create.stock_id,
                date=str(price_create.date),
                allow_zero_placeholder=True
            )

            if not is_valid:
                logger.error(f"❌ [VALIDATION] {error_msg}")
                raise PriceValidationError(error_msg)

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
            # Create new record (skip_validation=True 因為已經驗證過了)
            return StockPriceRepository.create(db, price_create, skip_validation=True)

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
