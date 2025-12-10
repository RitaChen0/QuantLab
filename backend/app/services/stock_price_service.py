"""
StockPrice service for business logic
"""

from typing import Optional, List
from datetime import date as DateType
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.stock_price import StockPrice
from app.schemas.stock_price import StockPriceCreate, StockPriceUpdate
from app.repositories.stock_price import StockPriceRepository
from app.repositories.stock import StockRepository


class StockPriceService:
    """Service for stock price-related business logic"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = StockPriceRepository()
        self.stock_repo = StockRepository()

    def get_price(self, stock_id: str, date: DateType) -> StockPrice:
        """
        Get stock price by stock_id and date

        Args:
            stock_id: Stock ID
            date: Trade date

        Returns:
            Stock price object

        Raises:
            HTTPException: If price not found
        """
        price = self.repo.get_by_stock_and_date(self.db, stock_id, date)
        if not price:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Price for stock {stock_id} on {date} not found",
            )
        return price

    def get_prices_by_stock(
        self,
        stock_id: str,
        start_date: Optional[DateType] = None,
        end_date: Optional[DateType] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[StockPrice]:
        """
        Get stock prices for a specific stock

        Args:
            stock_id: Stock ID
            start_date: Start date (optional)
            end_date: End date (optional)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of stock prices

        Raises:
            HTTPException: If stock not found or date range invalid
        """
        # Verify stock exists
        if not self.stock_repo.exists(self.db, stock_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock {stock_id} not found",
            )

        # Validate date range
        if start_date and end_date and start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before or equal to end date",
            )

        return self.repo.get_by_stock(
            self.db,
            stock_id,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit
        )

    def get_latest_price(self, stock_id: str) -> StockPrice:
        """
        Get latest stock price for a stock

        Args:
            stock_id: Stock ID

        Returns:
            Latest stock price

        Raises:
            HTTPException: If stock not found or no price data available
        """
        # Verify stock exists
        if not self.stock_repo.exists(self.db, stock_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock {stock_id} not found",
            )

        price = self.repo.get_latest(self.db, stock_id)
        if not price:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No price data available for stock {stock_id}",
            )

        return price

    def get_prices_by_date_range(
        self,
        start_date: DateType,
        end_date: DateType,
        stock_ids: Optional[List[str]] = None
    ) -> List[StockPrice]:
        """
        Get stock prices within a date range

        Args:
            start_date: Start date
            end_date: End date
            stock_ids: Optional list of stock IDs to filter

        Returns:
            List of stock prices

        Raises:
            HTTPException: If date range invalid
        """
        # Validate date range
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before or equal to end date",
            )

        # Verify all stocks exist if stock_ids provided
        if stock_ids:
            for stock_id in stock_ids:
                if not self.stock_repo.exists(self.db, stock_id):
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Stock {stock_id} not found",
                    )

        return self.repo.get_by_date_range(
            self.db,
            start_date,
            end_date,
            stock_ids=stock_ids
        )

    def create_price(self, price_create: StockPriceCreate) -> StockPrice:
        """
        Create new stock price

        Args:
            price_create: Stock price creation data

        Returns:
            Created stock price object

        Raises:
            HTTPException: If stock not found or price already exists
        """
        # Verify stock exists
        if not self.stock_repo.exists(self.db, price_create.stock_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock {price_create.stock_id} not found",
            )

        # Check if price already exists
        existing = self.repo.get_by_stock_and_date(
            self.db,
            price_create.stock_id,
            price_create.date
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Price for stock {price_create.stock_id} on {price_create.date} already exists",
            )

        # Validate OHLCV data
        self._validate_ohlcv(price_create)

        return self.repo.create(self.db, price_create)

    def create_prices_bulk(self, prices: List[StockPriceCreate]) -> int:
        """
        Bulk create stock prices

        Args:
            prices: List of stock price creation data

        Returns:
            Number of records created

        Raises:
            HTTPException: If validation fails
        """
        # Validate all prices
        for price in prices:
            # Verify stock exists
            if not self.stock_repo.exists(self.db, price.stock_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Stock {price.stock_id} not found",
                )

            # Validate OHLCV data
            self._validate_ohlcv(price)

        return self.repo.create_bulk(self.db, prices)

    def update_price(
        self,
        stock_id: str,
        date: DateType,
        price_update: StockPriceUpdate
    ) -> StockPrice:
        """
        Update stock price

        Args:
            stock_id: Stock ID
            date: Trade date
            price_update: Update data

        Returns:
            Updated stock price object

        Raises:
            HTTPException: If price not found
        """
        price = self.repo.get_by_stock_and_date(self.db, stock_id, date)
        if not price:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Price for stock {stock_id} on {date} not found",
            )

        # Validate OHLCV data if being updated
        if any([
            price_update.open is not None,
            price_update.high is not None,
            price_update.low is not None,
            price_update.close is not None
        ]):
            # Create a temporary object with updated values for validation
            temp_data = StockPriceCreate(
                stock_id=stock_id,
                date=date,
                open=price_update.open or price.open,
                high=price_update.high or price.high,
                low=price_update.low or price.low,
                close=price_update.close or price.close,
                volume=price_update.volume or price.volume,
                adj_close=price_update.adj_close or price.adj_close,
            )
            self._validate_ohlcv(temp_data)

        return self.repo.update(self.db, price, price_update)

    def upsert_price(self, price_create: StockPriceCreate) -> StockPrice:
        """
        Upsert (insert or update) stock price

        Args:
            price_create: Stock price data

        Returns:
            Stock price object

        Raises:
            HTTPException: If stock not found or validation fails
        """
        # Verify stock exists
        if not self.stock_repo.exists(self.db, price_create.stock_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock {price_create.stock_id} not found",
            )

        # Validate OHLCV data
        self._validate_ohlcv(price_create)

        return self.repo.upsert(self.db, price_create)

    def delete_price(self, stock_id: str, date: DateType) -> None:
        """
        Delete stock price

        Args:
            stock_id: Stock ID
            date: Trade date

        Raises:
            HTTPException: If price not found
        """
        price = self.repo.get_by_stock_and_date(self.db, stock_id, date)
        if not price:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Price for stock {stock_id} on {date} not found",
            )

        self.repo.delete(self.db, price)

    def delete_prices_by_stock(self, stock_id: str) -> int:
        """
        Delete all prices for a stock

        Args:
            stock_id: Stock ID

        Returns:
            Number of records deleted

        Raises:
            HTTPException: If stock not found
        """
        # Verify stock exists
        if not self.stock_repo.exists(self.db, stock_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock {stock_id} not found",
            )

        return self.repo.delete_by_stock(self.db, stock_id)

    def _validate_ohlcv(self, price_data: StockPriceCreate) -> None:
        """
        Validate OHLCV data

        Args:
            price_data: Stock price data

        Raises:
            HTTPException: If validation fails
        """
        # High should be >= Low
        if price_data.high < price_data.low:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="High price must be greater than or equal to low price",
            )

        # Open, High, Low, Close should all be >= 0
        if any(p < 0 for p in [price_data.open, price_data.high, price_data.low, price_data.close]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prices cannot be negative",
            )

        # High should be the highest value
        if price_data.high < max(price_data.open, price_data.close):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="High price must be the highest among OHLC values",
            )

        # Low should be the lowest value
        if price_data.low > min(price_data.open, price_data.close):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Low price must be the lowest among OHLC values",
            )

        # Volume should be >= 0
        if price_data.volume < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Volume cannot be negative",
            )
