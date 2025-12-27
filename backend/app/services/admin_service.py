"""
Admin Service for administrative operations
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from loguru import logger

from app.repositories.user import UserRepository
from app.repositories.strategy import StrategyRepository
from app.repositories.backtest import BacktestRepository
from app.repositories.strategy_signal import StrategySignalRepository
from app.models.user import User
from app.models.strategy import Strategy


class AdminService:
    """Service for administrative operations"""

    def __init__(self, db: Session):
        self.db = db

    # ============ User Management ============

    def list_users(
        self,
        skip: int = 0,
        limit: int = 50
    ) -> List[User]:
        """
        List all users with pagination

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of users
        """
        return UserRepository.get_all(self.db, skip=skip, limit=limit)

    def get_user(self, user_id: int) -> Optional[User]:
        """
        Get user by ID

        Args:
            user_id: User ID

        Returns:
            User object or None
        """
        return UserRepository.get_by_id(self.db, user_id)

    def update_user(
        self,
        user_id: int,
        user_update: Any
    ) -> Optional[User]:
        """
        Update user (admin only)

        Args:
            user_id: User ID
            user_update: Update data

        Returns:
            Updated user object or None if not found
        """
        user = UserRepository.get_by_id(self.db, user_id)
        if not user:
            return None

        # Update fields
        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def delete_user(self, user_id: int, current_user_id: int) -> bool:
        """
        Delete user (admin only)

        Args:
            user_id: User ID to delete
            current_user_id: Current admin user ID

        Returns:
            True if deleted successfully, False if user not found or trying to delete self
        """
        # Cannot delete yourself
        if user_id == current_user_id:
            return False

        user = UserRepository.get_by_id(self.db, user_id)
        if not user:
            return False

        UserRepository.delete(self.db, user)
        return True

    # ============ System Stats ============

    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get system statistics

        Returns:
            Dictionary with system stats
        """
        # Count users
        total_users = UserRepository.count(self.db)
        active_users = UserRepository.count_active(self.db)

        # Count strategies and backtests
        total_strategies = StrategyRepository.count(self.db)
        total_backtests = BacktestRepository.count(self.db)

        # Get database size
        from sqlalchemy import text
        db_size_result = self.db.execute(
            text("SELECT pg_size_pretty(pg_database_size('quantlab'))")
        ).fetchone()
        database_size = db_size_result[0] if db_size_result else "Unknown"

        # Get cache info (Redis)
        cache_size = self._get_cache_size()

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_strategies": total_strategies,
            "total_backtests": total_backtests,
            "database_size": database_size,
            "cache_size": cache_size,
        }

    def _get_cache_size(self) -> str:
        """Get Redis cache size"""
        from app.utils.cache import cache

        try:
            if cache.is_available():
                cache_info = cache.redis_client.info("memory")
                return f"{cache_info.get('used_memory_human', 'Unknown')}"
            else:
                return "Unavailable"
        except Exception as e:
            logger.error(f"Failed to get cache size: {str(e)}")
            return "Unknown"

    # ============ Monitoring Stats ============

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """
        Get strategy monitoring statistics

        Returns:
            Dictionary with monitoring stats
        """
        from app.utils.timezone_helpers import now_utc

        now = now_utc()
        today = now.date()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)

        # Convert to datetime for comparison
        today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=now.tzinfo)
        yesterday_start = datetime.combine(yesterday, datetime.min.time()).replace(tzinfo=now.tzinfo)
        week_ago_start = datetime.combine(week_ago, datetime.min.time()).replace(tzinfo=now.tzinfo)

        # Count active strategies
        from app.models.strategy import StrategyStatus
        active_strategies = StrategyRepository.count(self.db, status=StrategyStatus.ACTIVE)

        # Count signals
        signals_today = StrategySignalRepository.count_by_date(self.db, today)
        signals_yesterday = StrategySignalRepository.count_by_date(self.db, yesterday)
        signals_week = StrategySignalRepository.count_by_date_range(self.db, week_ago_start)

        # Count by signal type today
        buy_signals_today = StrategySignalRepository.count_by_type_and_date(
            self.db, today, "BUY"
        )
        sell_signals_today = StrategySignalRepository.count_by_type_and_date(
            self.db, today, "SELL"
        )

        # Get latest signals
        latest_signals_raw = StrategySignalRepository.get_latest(self.db, limit=5)

        # Get monitored stocks from ACTIVE strategies
        monitored_stocks = self._get_monitored_stocks()

        # Format latest signals
        latest_signals = [
            {
                "stock_id": sig.stock_id,
                "signal_type": sig.signal_type,
                "price": float(sig.price) if sig.price else None,
                "detected_at": sig.detected_at.isoformat(),
            }
            for sig in latest_signals_raw
        ]

        return {
            "active_strategies": active_strategies,
            "signals_today": signals_today,
            "signals_yesterday": signals_yesterday,
            "signals_week": signals_week,
            "buy_signals_today": buy_signals_today,
            "sell_signals_today": sell_signals_today,
            "monitored_stocks": sorted(list(monitored_stocks)),
            "latest_signals": latest_signals
        }

    def _get_monitored_stocks(self) -> set:
        """
        Get set of monitored stocks from active strategies

        Returns:
            Set of stock IDs
        """
        from app.models.strategy import StrategyStatus

        monitored_stocks = set()

        # Get active Backtrader strategies (only Backtrader supports monitoring)
        active_strategies = StrategyRepository.get_active_backtrader_strategies(self.db)

        for strategy in active_strategies:
            if strategy.parameters and isinstance(strategy.parameters, dict):
                stocks = strategy.parameters.get("stocks")
                if stocks and isinstance(stocks, list):
                    monitored_stocks.update(stocks)

        return monitored_stocks
