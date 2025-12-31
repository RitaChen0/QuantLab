"""
Strategy Signal Repository for database operations
"""

from typing import List, Optional
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc, or_
from app.models.strategy_signal import StrategySignal


class StrategySignalRepository:
    """Repository for strategy signal database operations"""

    @staticmethod
    def get_by_id(db: Session, signal_id: int) -> Optional[StrategySignal]:
        """
        Get strategy signal by ID

        Args:
            db: Database session
            signal_id: Signal ID

        Returns:
            Strategy signal object or None
        """
        return db.query(StrategySignal).filter(StrategySignal.id == signal_id).first()

    @staticmethod
    def get_by_user(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
        signal_type: Optional[str] = None
    ) -> List[StrategySignal]:
        """
        Get strategy signals by user

        Args:
            db: Database session
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            signal_type: Filter by signal type (BUY/SELL)

        Returns:
            List of strategy signals
        """
        query = db.query(StrategySignal).filter(StrategySignal.user_id == user_id)

        if signal_type:
            query = query.filter(StrategySignal.signal_type == signal_type)

        return query.order_by(desc(StrategySignal.detected_at)).offset(skip).limit(limit).all()

    @staticmethod
    def get_by_strategy(
        db: Session,
        strategy_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> List[StrategySignal]:
        """
        Get strategy signals by strategy ID

        Args:
            db: Database session
            strategy_id: Strategy ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of strategy signals
        """
        return (
            db.query(StrategySignal)
            .filter(StrategySignal.strategy_id == strategy_id)
            .order_by(desc(StrategySignal.detected_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def count_by_date(db: Session, target_date: date) -> int:
        """
        Count signals by date

        Args:
            db: Database session
            target_date: Target date

        Returns:
            Number of signals detected on the date
        """
        return (
            db.query(StrategySignal)
            .filter(func.date(StrategySignal.detected_at) == target_date)
            .count()
        )

    @staticmethod
    def count_by_type_and_date(
        db: Session,
        target_date: date,
        signal_type: str
    ) -> int:
        """
        Count signals by type and date

        Args:
            db: Database session
            target_date: Target date
            signal_type: Signal type (BUY/SELL)

        Returns:
            Number of signals of the type detected on the date
        """
        return (
            db.query(StrategySignal)
            .filter(
                and_(
                    func.date(StrategySignal.detected_at) == target_date,
                    StrategySignal.signal_type == signal_type
                )
            )
            .count()
        )

    @staticmethod
    def count_by_date_range(
        db: Session,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        Count signals in date range

        Args:
            db: Database session
            start_date: Start datetime
            end_date: End datetime (optional, defaults to now)

        Returns:
            Number of signals in the range
        """
        query = db.query(StrategySignal).filter(
            StrategySignal.detected_at >= start_date
        )

        if end_date:
            query = query.filter(StrategySignal.detected_at <= end_date)

        return query.count()

    @staticmethod
    def get_latest(db: Session, limit: int = 10) -> List[StrategySignal]:
        """
        Get latest signals

        Args:
            db: Database session
            limit: Maximum number of records to return

        Returns:
            List of latest strategy signals
        """
        return (
            db.query(StrategySignal)
            .order_by(desc(StrategySignal.detected_at))
            .limit(limit)
            .all()
        )

    @staticmethod
    def create(
        db: Session,
        strategy_id: int,
        user_id: int,
        stock_id: str,
        signal_type: str,
        price: Optional[float] = None,
        reason: Optional[str] = None
    ) -> StrategySignal:
        """
        Create new strategy signal

        Args:
            db: Database session
            strategy_id: Strategy ID
            user_id: User ID
            stock_id: Stock symbol
            signal_type: Signal type (BUY/SELL)
            price: Price when signal detected
            reason: Reason for the signal

        Returns:
            Created strategy signal object
        """
        signal = StrategySignal(
            strategy_id=strategy_id,
            user_id=user_id,
            stock_id=stock_id,
            signal_type=signal_type,
            price=price,
            reason=reason,
            notified=False
        )

        db.add(signal)
        db.commit()
        db.refresh(signal)

        return signal

    @staticmethod
    def mark_notified(db: Session, signal: StrategySignal) -> StrategySignal:
        """
        Mark signal as notified

        Args:
            db: Database session
            signal: Strategy signal object

        Returns:
            Updated strategy signal object
        """
        from app.utils.timezone_helpers import now_utc

        signal.notified = True
        signal.notified_at = now_utc()

        db.add(signal)
        db.commit()
        db.refresh(signal)

        return signal

    @staticmethod
    def check_duplicate(
        db: Session,
        strategy_id: int,
        stock_id: str,
        signal_type: str,
        time_threshold: datetime
    ) -> bool:
        """
        Check if a duplicate signal exists within time threshold

        Args:
            db: Database session
            strategy_id: Strategy ID
            stock_id: Stock symbol
            signal_type: Signal type (BUY/SELL)
            time_threshold: Time threshold (signals after this time are considered duplicates)

        Returns:
            True if duplicate exists, False otherwise
        """
        duplicate = (
            db.query(StrategySignal)
            .filter(
                and_(
                    StrategySignal.strategy_id == strategy_id,
                    StrategySignal.stock_id == stock_id,
                    StrategySignal.signal_type == signal_type,
                    StrategySignal.detected_at >= time_threshold
                )
            )
            .first()
        )

        return duplicate is not None

    @staticmethod
    def get_unnotified(db: Session, limit: int = 100) -> List[StrategySignal]:
        """
        Get unnotified signals

        Args:
            db: Database session
            limit: Maximum number of records to return

        Returns:
            List of unnotified strategy signals
        """
        return (
            db.query(StrategySignal)
            .filter(StrategySignal.notified == False)
            .order_by(desc(StrategySignal.detected_at))
            .limit(limit)
            .all()
        )

    @staticmethod
    def mark_as_notified(db: Session, signal: StrategySignal) -> StrategySignal:
        """
        Mark signal as notified (alias for mark_notified)

        Args:
            db: Database session
            signal: Strategy signal object

        Returns:
            Updated strategy signal object
        """
        return StrategySignalRepository.mark_notified(db, signal)

    @staticmethod
    def count(
        db: Session,
        strategy_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> int:
        """
        Count strategy signals with optional filters

        Args:
            db: Database session
            strategy_id: Filter by strategy ID (optional)
            user_id: Filter by user ID (optional)

        Returns:
            Number of signals matching the filters
        """
        query = db.query(StrategySignal)

        if strategy_id is not None:
            query = query.filter(StrategySignal.strategy_id == strategy_id)

        if user_id is not None:
            query = query.filter(StrategySignal.user_id == user_id)

        return query.count()

    @staticmethod
    def delete(db: Session, signal: StrategySignal) -> None:
        """
        Delete a strategy signal

        Args:
            db: Database session
            signal: Strategy signal object to delete
        """
        db.delete(signal)
        db.commit()

    @staticmethod
    def count_by_user(db: Session, user_id: int) -> int:
        """
        Count signals by user

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Number of signals for the user
        """
        return StrategySignalRepository.count(db, user_id=user_id)

    @staticmethod
    def delete_old_signals(db: Session, days: int = 30) -> int:
        """
        Delete signals older than specified days

        Args:
            db: Database session
            days: Number of days to keep

        Returns:
            Number of deleted signals
        """
        from datetime import timedelta
        from app.utils.timezone_helpers import now_utc

        cutoff_date = now_utc() - timedelta(days=days)

        deleted_count = (
            db.query(StrategySignal)
            .filter(StrategySignal.detected_at < cutoff_date)
            .delete()
        )

        db.commit()

        return deleted_count
