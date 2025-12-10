"""
BacktestResult service for business logic
"""

from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.backtest_result import BacktestResult
from app.schemas.backtest_result import BacktestResultCreate, BacktestResultUpdate
from app.repositories.backtest_result import BacktestResultRepository
from app.repositories.backtest import BacktestRepository


class BacktestResultService:
    """Service for backtest result-related business logic"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = BacktestResultRepository()
        self.backtest_repo = BacktestRepository()

    def get_result(self, result_id: int, user_id: int) -> BacktestResult:
        """
        Get backtest result by ID

        Args:
            result_id: Result ID
            user_id: User ID (for ownership verification)

        Returns:
            BacktestResult object

        Raises:
            HTTPException: If result not found or user is not owner
        """
        result = self.repo.get_by_id(self.db, result_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Backtest result not found",
            )

        # Verify ownership through backtest
        if not self.backtest_repo.is_owner(self.db, result.backtest_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this backtest result",
            )

        return result

    def get_result_by_backtest(self, backtest_id: int, user_id: int) -> BacktestResult:
        """
        Get backtest result by backtest_id

        Args:
            backtest_id: Backtest ID
            user_id: User ID (for ownership verification)

        Returns:
            BacktestResult object

        Raises:
            HTTPException: If result not found or user is not owner
        """
        # Verify backtest exists and user owns it
        if not self.backtest_repo.is_owner(self.db, backtest_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this backtest result",
            )

        result = self.repo.get_by_backtest(self.db, backtest_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No result found for this backtest",
            )

        return result

    def create_result(
        self,
        backtest_id: int,
        result_create: BacktestResultCreate
    ) -> BacktestResult:
        """
        Create new backtest result (internal use, typically by backtest engine)

        Args:
            backtest_id: Backtest ID
            result_create: Backtest result creation data

        Returns:
            Created backtest result object

        Raises:
            HTTPException: If backtest not found or result already exists
        """
        # Verify backtest exists
        backtest = self.backtest_repo.get_by_id(self.db, backtest_id)
        if not backtest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Backtest not found",
            )

        # Check if result already exists
        existing = self.repo.get_by_backtest(self.db, backtest_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Result already exists for this backtest",
            )

        # Validate metrics
        self._validate_result_metrics(result_create)

        return self.repo.create(self.db, backtest_id, result_create)

    def update_result(
        self,
        result_id: int,
        user_id: int,
        result_update: BacktestResultUpdate
    ) -> BacktestResult:
        """
        Update backtest result

        Args:
            result_id: Result ID
            user_id: User ID (for ownership verification)
            result_update: Update data

        Returns:
            Updated backtest result object

        Raises:
            HTTPException: If result not found or user is not owner
        """
        result = self.repo.get_by_id(self.db, result_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Backtest result not found",
            )

        # Verify ownership through backtest
        if not self.backtest_repo.is_owner(self.db, result.backtest_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this backtest result",
            )

        # Validate metrics if being updated
        if any([
            result_update.total_return is not None,
            result_update.sharpe_ratio is not None,
            result_update.win_rate is not None,
        ]):
            # Create a temporary object with updated values for validation
            temp_data = BacktestResultCreate(
                total_return=result_update.total_return or result.total_return,
                annual_return=result_update.annual_return or result.annual_return,
                sharpe_ratio=result_update.sharpe_ratio or result.sharpe_ratio,
                max_drawdown=result_update.max_drawdown or result.max_drawdown,
                win_rate=result_update.win_rate or result.win_rate,
                profit_factor=result_update.profit_factor or result.profit_factor,
                total_trades=result_update.total_trades or result.total_trades,
                winning_trades=result_update.winning_trades or result.winning_trades,
                losing_trades=result_update.losing_trades or result.losing_trades,
                avg_win=result_update.avg_win or result.avg_win,
                avg_loss=result_update.avg_loss or result.avg_loss,
                largest_win=result_update.largest_win or result.largest_win,
                largest_loss=result_update.largest_loss or result.largest_loss,
                final_capital=result_update.final_capital or result.final_capital,
            )
            self._validate_result_metrics(temp_data)

        return self.repo.update(self.db, result, result_update)

    def upsert_result(
        self,
        backtest_id: int,
        result_create: BacktestResultCreate
    ) -> BacktestResult:
        """
        Upsert (insert or update) backtest result

        Args:
            backtest_id: Backtest ID
            result_create: Backtest result data

        Returns:
            BacktestResult object

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

        # Validate metrics
        self._validate_result_metrics(result_create)

        return self.repo.upsert(self.db, backtest_id, result_create)

    def delete_result(self, result_id: int, user_id: int) -> None:
        """
        Delete backtest result

        Args:
            result_id: Result ID
            user_id: User ID (for ownership verification)

        Raises:
            HTTPException: If result not found or user is not owner
        """
        result = self.repo.get_by_id(self.db, result_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Backtest result not found",
            )

        # Verify ownership through backtest
        if not self.backtest_repo.is_owner(self.db, result.backtest_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this backtest result",
            )

        self.repo.delete(self.db, result)

    def delete_result_by_backtest(self, backtest_id: int, user_id: int) -> bool:
        """
        Delete backtest result by backtest_id

        Args:
            backtest_id: Backtest ID
            user_id: User ID (for ownership verification)

        Returns:
            True if deleted, False if not found

        Raises:
            HTTPException: If user is not owner
        """
        # Verify ownership through backtest
        if not self.backtest_repo.is_owner(self.db, backtest_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this backtest result",
            )

        return self.repo.delete_by_backtest(self.db, backtest_id)

    def _validate_result_metrics(self, result_data: BacktestResultCreate) -> None:
        """
        Validate backtest result metrics

        Args:
            result_data: Backtest result data

        Raises:
            HTTPException: If validation fails
        """
        # Validate win rate (0-100%)
        if result_data.win_rate < 0 or result_data.win_rate > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Win rate must be between 0 and 100",
            )

        # Validate trade counts
        if result_data.total_trades < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Total trades cannot be negative",
            )

        if result_data.winning_trades < 0 or result_data.losing_trades < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Winning/losing trades cannot be negative",
            )

        if result_data.winning_trades + result_data.losing_trades != result_data.total_trades:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sum of winning and losing trades must equal total trades",
            )

        # Validate profit factor (must be non-negative)
        if result_data.profit_factor < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profit factor cannot be negative",
            )

        # Validate max drawdown (should be non-positive, representing a loss)
        if result_data.max_drawdown > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Max drawdown should be zero or negative",
            )

        # Validate final capital (must be non-negative)
        if result_data.final_capital < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Final capital cannot be negative",
            )
