"""
BacktestResult repository for database operations
"""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.backtest_result import BacktestResult
from app.schemas.backtest_result import BacktestResultCreate, BacktestResultUpdate


class BacktestResultRepository:
    """Repository for backtest result database operations"""

    @staticmethod
    def get_by_id(db: Session, result_id: int) -> Optional[BacktestResult]:
        """Get backtest result by ID"""
        return db.query(BacktestResult).filter(BacktestResult.id == result_id).first()

    @staticmethod
    def get_by_backtest(db: Session, backtest_id: int) -> Optional[BacktestResult]:
        """
        Get backtest result by backtest_id

        Args:
            db: Database session
            backtest_id: Backtest ID

        Returns:
            Backtest result if exists
        """
        return (
            db.query(BacktestResult)
            .filter(BacktestResult.backtest_id == backtest_id)
            .first()
        )

    @staticmethod
    def create(
        db: Session,
        backtest_id: int,
        result_create: BacktestResultCreate
    ) -> BacktestResult:
        """
        Create new backtest result

        Args:
            db: Database session
            backtest_id: Backtest ID
            result_create: Backtest result creation data

        Returns:
            Created backtest result object
        """
        db_result = BacktestResult(
            backtest_id=backtest_id,
            total_return=result_create.total_return,
            annual_return=result_create.annual_return,
            sharpe_ratio=result_create.sharpe_ratio,
            max_drawdown=result_create.max_drawdown,
            win_rate=result_create.win_rate,
            profit_factor=result_create.profit_factor,
            total_trades=result_create.total_trades,
            winning_trades=result_create.winning_trades,
            losing_trades=result_create.losing_trades,
            avg_win=result_create.avg_win,
            avg_loss=result_create.avg_loss,
            largest_win=result_create.largest_win,
            largest_loss=result_create.largest_loss,
            final_capital=result_create.final_capital,
        )

        db.add(db_result)
        db.commit()
        db.refresh(db_result)

        return db_result

    @staticmethod
    def update(
        db: Session,
        result: BacktestResult,
        result_update: BacktestResultUpdate
    ) -> BacktestResult:
        """
        Update backtest result

        Args:
            db: Database session
            result: Existing backtest result object
            result_update: Update data

        Returns:
            Updated backtest result object
        """
        update_data = result_update.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(result, field, value)

        db.add(result)
        db.commit()
        db.refresh(result)

        return result

    @staticmethod
    def upsert(
        db: Session,
        backtest_id: int,
        result_create: BacktestResultCreate
    ) -> BacktestResult:
        """
        Upsert (insert or update) backtest result

        Args:
            db: Database session
            backtest_id: Backtest ID
            result_create: Backtest result data

        Returns:
            Backtest result object
        """
        existing = BacktestResultRepository.get_by_backtest(db, backtest_id)

        if existing:
            # Update existing record
            for field, value in result_create.model_dump().items():
                setattr(existing, field, value)
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # Create new record
            return BacktestResultRepository.create(db, backtest_id, result_create)

    @staticmethod
    def delete(db: Session, result: BacktestResult) -> None:
        """
        Delete backtest result

        Args:
            db: Database session
            result: Backtest result to delete
        """
        db.delete(result)
        db.commit()

    @staticmethod
    def delete_by_backtest(db: Session, backtest_id: int) -> bool:
        """
        Delete backtest result by backtest_id

        Args:
            db: Database session
            backtest_id: Backtest ID

        Returns:
            True if deleted, False if not found
        """
        result = BacktestResultRepository.get_by_backtest(db, backtest_id)
        if result:
            db.delete(result)
            db.commit()
            return True
        return False
