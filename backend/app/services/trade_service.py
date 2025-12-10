"""
Trade service for business logic
"""

from typing import Optional, List
from datetime import date as DateType
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.trade import Trade, TradeAction
from app.schemas.trade import TradeCreate, TradeUpdate
from app.repositories.trade import TradeRepository
from app.repositories.backtest import BacktestRepository
from app.repositories.stock import StockRepository


class TradeService:
    """Service for trade-related business logic"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = TradeRepository()
        self.backtest_repo = BacktestRepository()
        self.stock_repo = StockRepository()

    def get_trade(self, trade_id: int, user_id: int) -> Trade:
        """
        Get trade by ID

        Args:
            trade_id: Trade ID
            user_id: User ID (for ownership verification)

        Returns:
            Trade object

        Raises:
            HTTPException: If trade not found or user is not owner
        """
        trade = self.repo.get_by_id(self.db, trade_id)
        if not trade:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trade not found",
            )

        # Verify ownership through backtest
        if not self.backtest_repo.is_owner(self.db, trade.backtest_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this trade",
            )

        return trade

    def get_backtest_trades(
        self,
        backtest_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Trade], int]:
        """
        Get trades by backtest

        Args:
            backtest_id: Backtest ID
            user_id: User ID (for ownership verification)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (trades list, total count)

        Raises:
            HTTPException: If backtest not found or user is not owner
        """
        # Verify backtest exists and user owns it
        if not self.backtest_repo.is_owner(self.db, backtest_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access trades for this backtest",
            )

        trades = self.repo.get_by_backtest(self.db, backtest_id, skip=skip, limit=limit)
        total = self.repo.count_by_backtest(self.db, backtest_id)
        return trades, total

    def get_stock_trades(
        self,
        backtest_id: int,
        stock_id: str,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Trade]:
        """
        Get trades for a specific stock in a backtest

        Args:
            backtest_id: Backtest ID
            stock_id: Stock ID
            user_id: User ID (for ownership verification)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of trades

        Raises:
            HTTPException: If backtest not found or user is not owner
        """
        # Verify backtest exists and user owns it
        if not self.backtest_repo.is_owner(self.db, backtest_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access trades for this backtest",
            )

        # Verify stock exists
        if not self.stock_repo.exists(self.db, stock_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock {stock_id} not found",
            )

        return self.repo.get_by_stock(
            self.db,
            backtest_id,
            stock_id,
            skip=skip,
            limit=limit
        )

    def get_trades_by_action(
        self,
        backtest_id: int,
        action: TradeAction,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Trade]:
        """
        Get trades by action type (buy/sell)

        Args:
            backtest_id: Backtest ID
            action: Trade action (buy or sell)
            user_id: User ID (for ownership verification)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of trades

        Raises:
            HTTPException: If backtest not found or user is not owner
        """
        # Verify backtest exists and user owns it
        if not self.backtest_repo.is_owner(self.db, backtest_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access trades for this backtest",
            )

        return self.repo.get_by_action(
            self.db,
            backtest_id,
            action,
            skip=skip,
            limit=limit
        )

    def get_trades_by_date_range(
        self,
        backtest_id: int,
        start_date: DateType,
        end_date: DateType,
        user_id: int
    ) -> List[Trade]:
        """
        Get trades within a date range

        Args:
            backtest_id: Backtest ID
            start_date: Start date
            end_date: End date
            user_id: User ID (for ownership verification)

        Returns:
            List of trades

        Raises:
            HTTPException: If backtest not found, user is not owner, or date range invalid
        """
        # Verify backtest exists and user owns it
        if not self.backtest_repo.is_owner(self.db, backtest_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access trades for this backtest",
            )

        # Validate date range
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before or equal to end date",
            )

        return self.repo.get_by_date_range(
            self.db,
            backtest_id,
            start_date,
            end_date
        )

    def get_latest_trades(
        self,
        backtest_id: int,
        user_id: int,
        limit: int = 10
    ) -> List[Trade]:
        """
        Get latest trades for a backtest

        Args:
            backtest_id: Backtest ID
            user_id: User ID (for ownership verification)
            limit: Maximum number of records to return

        Returns:
            List of latest trades

        Raises:
            HTTPException: If backtest not found or user is not owner
        """
        # Verify backtest exists and user owns it
        if not self.backtest_repo.is_owner(self.db, backtest_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access trades for this backtest",
            )

        return self.repo.get_latest(self.db, backtest_id, limit=limit)

    def get_trade_summary(self, backtest_id: int, user_id: int) -> dict:
        """
        Get trade summary statistics for a backtest

        Args:
            backtest_id: Backtest ID
            user_id: User ID (for ownership verification)

        Returns:
            Dictionary with summary statistics

        Raises:
            HTTPException: If backtest not found or user is not owner
        """
        # Verify backtest exists and user owns it
        if not self.backtest_repo.is_owner(self.db, backtest_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access trades for this backtest",
            )

        return self.repo.get_summary(self.db, backtest_id)

    def create_trade(
        self,
        backtest_id: int,
        trade_create: TradeCreate
    ) -> Trade:
        """
        Create new trade (internal use, typically by backtest engine)

        Args:
            backtest_id: Backtest ID
            trade_create: Trade creation data

        Returns:
            Created trade object

        Raises:
            HTTPException: If backtest or stock not found, or validation fails
        """
        # Verify backtest exists
        backtest = self.backtest_repo.get_by_id(self.db, backtest_id)
        if not backtest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Backtest not found",
            )

        # Verify stock exists
        if not self.stock_repo.exists(self.db, trade_create.stock_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock {trade_create.stock_id} not found",
            )

        # Validate trade data
        self._validate_trade(trade_create)

        # Validate trade date is within backtest date range
        if not (backtest.start_date <= trade_create.trade_date <= backtest.end_date):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trade date must be within backtest date range",
            )

        return self.repo.create(self.db, backtest_id, trade_create)

    def create_trades_bulk(
        self,
        backtest_id: int,
        trades: List[TradeCreate]
    ) -> int:
        """
        Bulk create trades (internal use, typically by backtest engine)

        Args:
            backtest_id: Backtest ID
            trades: List of trade creation data

        Returns:
            Number of records created

        Raises:
            HTTPException: If backtest not found or validation fails
        """
        # Verify backtest exists
        backtest = self.backtest_repo.get_by_id(self.db, backtest_id)
        if not backtest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Backtest not found",
            )

        # Validate all trades
        for trade in trades:
            # Verify stock exists
            if not self.stock_repo.exists(self.db, trade.stock_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Stock {trade.stock_id} not found",
                )

            # Validate trade data
            self._validate_trade(trade)

            # Validate trade date is within backtest date range
            if not (backtest.start_date <= trade.trade_date <= backtest.end_date):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Trade date {trade.trade_date} must be within backtest date range",
                )

        return self.repo.create_bulk(self.db, backtest_id, trades)

    def update_trade(
        self,
        trade_id: int,
        user_id: int,
        trade_update: TradeUpdate
    ) -> Trade:
        """
        Update trade

        Args:
            trade_id: Trade ID
            user_id: User ID (for ownership verification)
            trade_update: Update data

        Returns:
            Updated trade object

        Raises:
            HTTPException: If trade not found or user is not owner
        """
        trade = self.repo.get_by_id(self.db, trade_id)
        if not trade:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trade not found",
            )

        # Verify ownership through backtest
        if not self.backtest_repo.is_owner(self.db, trade.backtest_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this trade",
            )

        # Validate updated trade data
        if any([
            trade_update.quantity is not None,
            trade_update.price is not None,
            trade_update.commission is not None,
            trade_update.tax is not None,
        ]):
            # Create a temporary object with updated values for validation
            temp_data = TradeCreate(
                stock_id=trade.stock_id,
                action=trade_update.action or trade.action,
                quantity=trade_update.quantity or trade.quantity,
                price=trade_update.price or trade.price,
                commission=trade_update.commission or trade.commission,
                tax=trade_update.tax or trade.tax,
                trade_date=trade_update.trade_date or trade.trade_date,
            )
            self._validate_trade(temp_data)

        return self.repo.update(self.db, trade, trade_update)

    def delete_trade(self, trade_id: int, user_id: int) -> None:
        """
        Delete trade

        Args:
            trade_id: Trade ID
            user_id: User ID (for ownership verification)

        Raises:
            HTTPException: If trade not found or user is not owner
        """
        trade = self.repo.get_by_id(self.db, trade_id)
        if not trade:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trade not found",
            )

        # Verify ownership through backtest
        if not self.backtest_repo.is_owner(self.db, trade.backtest_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this trade",
            )

        self.repo.delete(self.db, trade)

    def delete_backtest_trades(self, backtest_id: int, user_id: int) -> int:
        """
        Delete all trades for a backtest

        Args:
            backtest_id: Backtest ID
            user_id: User ID (for ownership verification)

        Returns:
            Number of records deleted

        Raises:
            HTTPException: If backtest not found or user is not owner
        """
        # Verify backtest exists and user owns it
        if not self.backtest_repo.is_owner(self.db, backtest_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete trades for this backtest",
            )

        return self.repo.delete_by_backtest(self.db, backtest_id)

    def _validate_trade(self, trade_data: TradeCreate) -> None:
        """
        Validate trade data

        Args:
            trade_data: Trade data

        Raises:
            HTTPException: If validation fails
        """
        # Quantity must be positive
        if trade_data.quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be greater than 0",
            )

        # Price must be positive
        if trade_data.price <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Price must be greater than 0",
            )

        # Commission must be non-negative
        if trade_data.commission < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Commission cannot be negative",
            )

        # Tax must be non-negative
        if trade_data.tax < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tax cannot be negative",
            )
