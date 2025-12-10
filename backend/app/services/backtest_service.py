"""
Backtest service for business logic
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.backtest import Backtest, BacktestStatus
from app.schemas.backtest import BacktestCreate, BacktestUpdate
from app.repositories.backtest import BacktestRepository
from app.repositories.strategy import StrategyRepository
from app.core.config import settings


class BacktestService:
    """Service for backtest-related business logic"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = BacktestRepository()
        self.strategy_repo = StrategyRepository()

    def get_backtest(self, backtest_id: int, user_id: int) -> Backtest:
        """
        Get backtest by ID

        Args:
            backtest_id: Backtest ID
            user_id: User ID (for ownership verification)

        Returns:
            Backtest object

        Raises:
            HTTPException: If backtest not found or user is not owner
        """
        backtest = self.repo.get_by_id(self.db, backtest_id)
        if not backtest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Backtest not found",
            )

        # Verify ownership
        if not self.repo.is_owner(self.db, backtest_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this backtest",
            )

        return backtest

    def get_backtest_with_result(self, backtest_id: int, user_id: int) -> Backtest:
        """
        Get backtest by ID with result preloaded

        Args:
            backtest_id: Backtest ID
            user_id: User ID (for ownership verification)

        Returns:
            Backtest object with result

        Raises:
            HTTPException: If backtest not found or user is not owner
        """
        backtest = self.repo.get_by_id_with_result(self.db, backtest_id)
        if not backtest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Backtest not found",
            )

        # Verify ownership
        if not self.repo.is_owner(self.db, backtest_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this backtest",
            )

        return backtest

    def get_user_backtests(
        self,
        user_id: int,
        status_filter: Optional[BacktestStatus] = None,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[Backtest], int]:
        """
        Get backtests by user

        Args:
            user_id: User ID
            status_filter: Filter by status (optional)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (backtests list, total count)
        """
        backtests = self.repo.get_by_user(
            self.db,
            user_id,
            status=status_filter,
            skip=skip,
            limit=limit
        )
        total = self.repo.count_by_user(self.db, user_id, status=status_filter)
        return backtests, total

    def get_strategy_backtests(
        self,
        strategy_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[Backtest], int]:
        """
        Get backtests by strategy

        Args:
            strategy_id: Strategy ID
            user_id: User ID (for ownership verification)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (backtests list, total count)

        Raises:
            HTTPException: If strategy not found or user is not owner
        """
        # Verify strategy exists and user owns it
        if not self.strategy_repo.is_owner(self.db, strategy_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access backtests for this strategy",
            )

        backtests = self.repo.get_by_strategy(self.db, strategy_id, skip=skip, limit=limit)
        total = self.repo.count_by_strategy(self.db, strategy_id)

        return backtests, total

    def get_latest_strategy_backtests(
        self,
        strategy_id: int,
        user_id: int,
        limit: int = 5
    ) -> List[Backtest]:
        """
        Get latest backtests for a strategy

        Args:
            strategy_id: Strategy ID
            user_id: User ID (for ownership verification)
            limit: Maximum number of records to return

        Returns:
            List of latest backtests

        Raises:
            HTTPException: If strategy not found or user is not owner
        """
        # Verify strategy exists and user owns it
        if not self.strategy_repo.is_owner(self.db, strategy_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access backtests for this strategy",
            )

        return self.repo.get_latest_by_strategy(self.db, strategy_id, limit=limit)

    def get_pending_backtests(self, limit: int = 10) -> List[Backtest]:
        """
        Get pending backtests (for processing queue)

        Args:
            limit: Maximum number of records to return

        Returns:
            List of pending backtests
        """
        return self.repo.get_pending(self.db, limit=limit)

    def create_backtest(self, user_id: int, backtest_create: BacktestCreate) -> Backtest:
        """
        Create new backtest

        Args:
            user_id: User ID
            backtest_create: Backtest creation data

        Returns:
            Created backtest object

        Raises:
            HTTPException: If strategy not found, validation fails, quota exceeded, or user is not owner
        """
        # Verify strategy exists and user owns it
        strategy = self.strategy_repo.get_by_id(self.db, backtest_create.strategy_id)
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found",
            )

        if not self.strategy_repo.is_owner(self.db, backtest_create.strategy_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to create backtest for this strategy",
            )

        # Check quotas
        self._check_backtest_quota(user_id, backtest_create.strategy_id)

        # Validate date range
        if backtest_create.start_date >= backtest_create.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after start date",
            )

        # Validate initial capital
        if backtest_create.initial_capital <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Initial capital must be greater than 0",
            )

        # Determine engine type: use request override or inherit from strategy
        engine_type = backtest_create.engine_type or strategy.engine_type

        return self.repo.create(self.db, user_id, backtest_create, engine_type=engine_type)

    def update_backtest(
        self,
        backtest_id: int,
        user_id: int,
        backtest_update: BacktestUpdate
    ) -> Backtest:
        """
        Update backtest

        Args:
            backtest_id: Backtest ID
            user_id: User ID (for ownership verification)
            backtest_update: Update data

        Returns:
            Updated backtest object

        Raises:
            HTTPException: If backtest not found, user is not owner, or validation fails
        """
        backtest = self.repo.get_by_id(self.db, backtest_id)
        if not backtest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Backtest not found",
            )

        # Verify ownership
        if not self.repo.is_owner(self.db, backtest_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this backtest",
            )

        # Don't allow updates to running or completed backtests
        if backtest.status in [BacktestStatus.RUNNING, BacktestStatus.COMPLETED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update backtest with status {backtest.status.value}",
            )

        return self.repo.update(self.db, backtest, backtest_update)

    def update_backtest_status(
        self,
        backtest_id: int,
        new_status: BacktestStatus,
        error_message: Optional[str] = None
    ) -> Backtest:
        """
        Update backtest status (internal use, e.g., by backtest engine)

        Args:
            backtest_id: Backtest ID
            new_status: New status
            error_message: Error message if failed

        Returns:
            Updated backtest object

        Raises:
            HTTPException: If backtest not found
        """
        backtest = self.repo.get_by_id(self.db, backtest_id)
        if not backtest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Backtest not found",
            )

        # Validate status transition
        self._validate_status_transition(backtest.status, new_status)

        return self.repo.update_status(self.db, backtest, new_status, error_message)

    def delete_backtest(self, backtest_id: int, user_id: int) -> None:
        """
        Delete backtest

        Args:
            backtest_id: Backtest ID
            user_id: User ID (for ownership verification)

        Raises:
            HTTPException: If backtest not found or user is not owner
        """
        backtest = self.repo.get_by_id(self.db, backtest_id)
        if not backtest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Backtest not found",
            )

        # Verify ownership
        if not self.repo.is_owner(self.db, backtest_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this backtest",
            )

        # Don't allow deletion of running backtests
        if backtest.status == BacktestStatus.RUNNING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a running backtest",
            )

        self.repo.delete(self.db, backtest)

    def _validate_status_transition(
        self,
        current_status: BacktestStatus,
        new_status: BacktestStatus
    ) -> None:
        """
        Validate backtest status transition

        Args:
            current_status: Current status
            new_status: New status

        Raises:
            HTTPException: If transition is invalid
        """
        # Define valid transitions
        valid_transitions = {
            BacktestStatus.PENDING: [BacktestStatus.RUNNING, BacktestStatus.FAILED],
            BacktestStatus.RUNNING: [BacktestStatus.COMPLETED, BacktestStatus.FAILED],
            BacktestStatus.COMPLETED: [],  # Terminal state
            BacktestStatus.FAILED: [],  # Terminal state
        }

        if new_status not in valid_transitions.get(current_status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from {current_status.value} to {new_status.value}",
            )

    def _check_backtest_quota(self, user_id: int, strategy_id: int) -> None:
        """
        Check if user has exceeded backtest quotas

        Args:
            user_id: User ID
            strategy_id: Strategy ID

        Raises:
            HTTPException: If quota exceeded
        """
        # Check user's total backtest count
        user_backtest_count = self.repo.count_by_user(self.db, user_id)
        if user_backtest_count >= settings.MAX_BACKTESTS_PER_USER:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Backtest quota exceeded. Maximum {settings.MAX_BACKTESTS_PER_USER} backtests allowed per user. "
                       f"Current count: {user_backtest_count}. Please delete some backtests before creating new ones."
            )

        # Check backtests per strategy
        strategy_backtest_count = self.repo.count_by_strategy(self.db, strategy_id)
        if strategy_backtest_count >= settings.MAX_BACKTESTS_PER_STRATEGY:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Backtest quota exceeded for this strategy. Maximum {settings.MAX_BACKTESTS_PER_STRATEGY} backtests allowed per strategy. "
                       f"Current count: {strategy_backtest_count}. Please delete some backtests for this strategy before creating new ones."
            )
