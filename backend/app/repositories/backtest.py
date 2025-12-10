"""
Backtest repository for database operations
"""

from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc
from app.models.backtest import Backtest, BacktestStatus
from app.schemas.backtest import BacktestCreate, BacktestUpdate


class BacktestRepository:
    """Repository for backtest database operations"""

    @staticmethod
    def get_by_id(db: Session, backtest_id: int) -> Optional[Backtest]:
        """Get backtest by ID with strategy preloaded"""
        return (
            db.query(Backtest)
            .options(joinedload(Backtest.strategy))
            .filter(Backtest.id == backtest_id)
            .first()
        )

    @staticmethod
    def get_by_id_with_result(db: Session, backtest_id: int) -> Optional[Backtest]:
        """Get backtest by ID with result and strategy preloaded"""
        return (
            db.query(Backtest)
            .options(joinedload(Backtest.result))
            .options(joinedload(Backtest.strategy))
            .filter(Backtest.id == backtest_id)
            .first()
        )

    @staticmethod
    def get_by_user(
        db: Session,
        user_id: int,
        status: Optional[BacktestStatus] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Backtest]:
        """
        Get backtests by user

        Args:
            db: Database session
            user_id: User ID
            status: Filter by status (optional)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of backtests with strategy relationship loaded
        """
        query = db.query(Backtest).options(joinedload(Backtest.strategy)).filter(Backtest.user_id == user_id)

        if status:
            query = query.filter(Backtest.status == status)

        return query.order_by(desc(Backtest.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def get_by_strategy(
        db: Session,
        strategy_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> List[Backtest]:
        """
        Get backtests by strategy

        Args:
            db: Database session
            strategy_id: Strategy ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of backtests with strategy relationship loaded
        """
        return (
            db.query(Backtest)
            .options(joinedload(Backtest.strategy))
            .filter(Backtest.strategy_id == strategy_id)
            .order_by(desc(Backtest.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def count_by_user(
        db: Session,
        user_id: int,
        status: Optional[BacktestStatus] = None
    ) -> int:
        """Count backtests by user"""
        query = db.query(Backtest).filter(Backtest.user_id == user_id)

        if status:
            query = query.filter(Backtest.status == status)

        return query.count()

    @staticmethod
    def count_by_strategy(
        db: Session,
        strategy_id: int
    ) -> int:
        """
        Count backtests by strategy

        Args:
            db: Database session
            strategy_id: Strategy ID

        Returns:
            Total count of backtests for the strategy
        """
        return db.query(Backtest).filter(Backtest.strategy_id == strategy_id).count()

    @staticmethod
    def get_pending(db: Session, limit: int = 10) -> List[Backtest]:
        """Get pending backtests (for processing queue)"""
        return (
            db.query(Backtest)
            .filter(Backtest.status == BacktestStatus.PENDING)
            .order_by(Backtest.created_at)
            .limit(limit)
            .all()
        )

    @staticmethod
    def create(
        db: Session,
        user_id: int,
        backtest_create: BacktestCreate,
        engine_type: str = 'backtrader'
    ) -> Backtest:
        """
        Create new backtest

        Args:
            db: Database session
            user_id: User ID
            backtest_create: Backtest creation data
            engine_type: Backtest engine type (backtrader or qlib)

        Returns:
            Created backtest object
        """
        # 結構化參數：分離策略參數和回測配置
        structured_params = {
            'strategy_params': backtest_create.parameters or {},
            'backtest_config': {
                'commission': float(backtest_create.commission) if backtest_create.commission else 0.001425,
                'tax': float(backtest_create.tax) if backtest_create.tax else 0.003,
                'slippage': float(backtest_create.slippage) if backtest_create.slippage else 0.0,
                'position_size': backtest_create.position_size,
                'max_position_pct': float(backtest_create.max_position_pct) if backtest_create.max_position_pct else 1.0,
            }
        }

        db_backtest = Backtest(
            strategy_id=backtest_create.strategy_id,
            user_id=user_id,
            name=backtest_create.name,
            description=backtest_create.description,
            symbol=backtest_create.symbol,
            parameters=structured_params,
            start_date=backtest_create.start_date,
            end_date=backtest_create.end_date,
            initial_capital=backtest_create.initial_capital,
            engine_type=engine_type,
            status=BacktestStatus.PENDING,
        )

        db.add(db_backtest)
        db.commit()
        db.refresh(db_backtest)

        return db_backtest

    @staticmethod
    def update(
        db: Session,
        backtest: Backtest,
        backtest_update: BacktestUpdate
    ) -> Backtest:
        """
        Update backtest

        Args:
            db: Database session
            backtest: Existing backtest object
            backtest_update: Update data

        Returns:
            Updated backtest object
        """
        update_data = backtest_update.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(backtest, field, value)

        db.add(backtest)
        db.commit()
        db.refresh(backtest)

        return backtest

    @staticmethod
    def update_status(
        db: Session,
        backtest: Backtest,
        status: BacktestStatus,
        error_message: Optional[str] = None
    ) -> Backtest:
        """
        Update backtest status

        Args:
            db: Database session
            backtest: Backtest object
            status: New status
            error_message: Error message if failed

        Returns:
            Updated backtest object
        """
        backtest.status = status

        if status == BacktestStatus.RUNNING:
            backtest.started_at = datetime.now(timezone.utc)
        elif status in [BacktestStatus.COMPLETED, BacktestStatus.FAILED]:
            backtest.completed_at = datetime.now(timezone.utc)

        if error_message:
            backtest.error_message = error_message

        db.add(backtest)
        db.commit()
        db.refresh(backtest)

        return backtest

    @staticmethod
    def delete(db: Session, backtest: Backtest) -> None:
        """
        Delete backtest

        Args:
            db: Database session
            backtest: Backtest to delete
        """
        db.delete(backtest)
        db.commit()

    @staticmethod
    def is_owner(db: Session, backtest_id: int, user_id: int) -> bool:
        """
        Check if user owns the backtest

        Args:
            db: Database session
            backtest_id: Backtest ID
            user_id: User ID

        Returns:
            True if user owns the backtest
        """
        return (
            db.query(Backtest)
            .filter(
                and_(
                    Backtest.id == backtest_id,
                    Backtest.user_id == user_id
                )
            )
            .count() > 0
        )

    @staticmethod
    def get_latest_by_strategy(
        db: Session,
        strategy_id: int,
        limit: int = 5
    ) -> List[Backtest]:
        """Get latest backtests for a strategy with strategy relationship loaded"""
        return (
            db.query(Backtest)
            .options(joinedload(Backtest.strategy))
            .filter(Backtest.strategy_id == strategy_id)
            .order_by(desc(Backtest.created_at))
            .limit(limit)
            .all()
        )
