"""
Stock service for business logic
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.stock import Stock
from app.schemas.stock import StockCreate, StockUpdate
from app.repositories.stock import StockRepository


class StockService:
    """Service for stock-related business logic"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = StockRepository()

    def get_stock(self, stock_id: str) -> Stock:
        """
        Get stock by ID

        Args:
            stock_id: Stock ID

        Returns:
            Stock object

        Raises:
            HTTPException: If stock not found
        """
        stock = self.repo.get_by_id(self.db, stock_id)
        if not stock:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock {stock_id} not found",
            )
        return stock

    def get_all_stocks(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[str] = None
    ) -> tuple[List[Stock], int]:
        """
        Get all stocks with pagination

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            is_active: Filter by active status

        Returns:
            Tuple of (stocks list, total count)
        """
        stocks = self.repo.get_all(self.db, skip=skip, limit=limit, is_active=is_active)
        total = self.repo.count(self.db, is_active=is_active)
        return stocks, total

    def search_stocks(
        self,
        keyword: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Stock]:
        """
        Search stocks by keyword (stock_id or name)

        Args:
            keyword: Search keyword
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of matching stocks
        """
        if not keyword or len(keyword.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search keyword cannot be empty",
            )

        return self.repo.search(self.db, keyword, skip=skip, limit=limit)

    def get_stocks_by_category(
        self,
        category: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Stock]:
        """
        Get stocks by category

        Args:
            category: Stock category
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of stocks in category
        """
        return self.repo.get_by_category(self.db, category, skip=skip, limit=limit)

    def get_stocks_by_market(
        self,
        market: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Stock]:
        """
        Get stocks by market

        Args:
            market: Stock market
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of stocks in market
        """
        return self.repo.get_by_market(self.db, market, skip=skip, limit=limit)

    def create_stock(self, stock_create: StockCreate) -> Stock:
        """
        Create new stock

        Args:
            stock_create: Stock creation data

        Returns:
            Created stock object

        Raises:
            HTTPException: If stock already exists
        """
        # Check if stock already exists
        if self.repo.exists(self.db, stock_create.stock_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock {stock_create.stock_id} already exists",
            )

        return self.repo.create(self.db, stock_create)

    def create_stocks_bulk(self, stocks: List[StockCreate]) -> List[Stock]:
        """
        Bulk create stocks

        Args:
            stocks: List of stock creation data

        Returns:
            List of created stocks

        Raises:
            HTTPException: If any stock already exists
        """
        # Check for duplicates in the input
        stock_ids = [s.stock_id for s in stocks]
        if len(stock_ids) != len(set(stock_ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duplicate stock IDs in input",
            )

        # Check if any stocks already exist
        for stock in stocks:
            if self.repo.exists(self.db, stock.stock_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Stock {stock.stock_id} already exists",
                )

        return self.repo.create_bulk(self.db, stocks)

    def update_stock(self, stock_id: str, stock_update: StockUpdate) -> Stock:
        """
        Update stock

        Args:
            stock_id: Stock ID
            stock_update: Update data

        Returns:
            Updated stock object

        Raises:
            HTTPException: If stock not found
        """
        stock = self.repo.get_by_id(self.db, stock_id)
        if not stock:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock {stock_id} not found",
            )

        return self.repo.update(self.db, stock, stock_update)

    def delete_stock(self, stock_id: str) -> None:
        """
        Delete stock

        Args:
            stock_id: Stock ID

        Raises:
            HTTPException: If stock not found
        """
        stock = self.repo.get_by_id(self.db, stock_id)
        if not stock:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock {stock_id} not found",
            )

        self.repo.delete(self.db, stock)

    def stock_exists(self, stock_id: str) -> bool:
        """
        Check if stock exists

        Args:
            stock_id: Stock ID

        Returns:
            True if stock exists
        """
        return self.repo.exists(self.db, stock_id)
