"""
Strategy repository for database operations
"""

from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger
from app.models.strategy import Strategy, StrategyStatus
from app.schemas.strategy import StrategyCreate, StrategyUpdate
from app.utils.query_helpers import escape_like_pattern
from app.db.session import transaction_scope


class StrategyRepository:
    """Repository for strategy database operations"""

    @staticmethod
    def get_by_id(db: Session, strategy_id: int, load_user: bool = False) -> Optional[Strategy]:
        """Get strategy by ID with optional user preloading"""
        query = db.query(Strategy)

        if load_user:
            query = query.options(joinedload(Strategy.user))

        return query.filter(Strategy.id == strategy_id).first()

    @staticmethod
    def get_by_user(
        db: Session,
        user_id: int,
        status: Optional[StrategyStatus] = None,
        skip: int = 0,
        limit: int = 20,
        load_user: bool = False
    ) -> List[Strategy]:
        """
        Get strategies by user

        Args:
            db: Database session
            user_id: User ID
            status: Filter by status (optional)
            skip: Number of records to skip
            limit: Maximum number of records to return
            load_user: Whether to preload user relationship

        Returns:
            List of strategies with optional user relationship loaded
        """
        query = db.query(Strategy)

        if load_user:
            query = query.options(joinedload(Strategy.user))

        query = query.filter(Strategy.user_id == user_id)

        if status:
            query = query.filter(Strategy.status == status)

        return query.order_by(desc(Strategy.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def count_by_user(
        db: Session,
        user_id: int,
        status: Optional[StrategyStatus] = None
    ) -> int:
        """Count strategies by user"""
        query = db.query(Strategy).filter(Strategy.user_id == user_id)

        if status:
            query = query.filter(Strategy.status == status)

        return query.count()

    @staticmethod
    def get_all(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        status: Optional[StrategyStatus] = None,
        load_user: bool = True
    ) -> List[Strategy]:
        """
        Get all strategies (admin function)

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by status (optional)
            load_user: Whether to preload user relationship (default True for admin view)

        Returns:
            List of strategies with user relationship loaded
        """
        query = db.query(Strategy)

        if load_user:
            query = query.options(joinedload(Strategy.user))

        if status:
            query = query.filter(Strategy.status == status)

        return query.order_by(desc(Strategy.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def search_by_user(
        db: Session,
        user_id: int,
        keyword: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[Strategy]:
        """
        Search strategies by name

        Args:
            db: Database session
            user_id: User ID
            keyword: Search keyword
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of matching strategies
        """
        # 轉義特殊字符，防止萬用字元注入
        safe_keyword = escape_like_pattern(keyword)
        search_pattern = f"%{safe_keyword}%"

        return (
            db.query(Strategy)
            .filter(
                and_(
                    Strategy.user_id == user_id,
                    Strategy.name.ilike(search_pattern)
                )
            )
            .order_by(desc(Strategy.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def create(db: Session, user_id: int, strategy_create: StrategyCreate) -> Strategy:
        """
        Create new strategy with automatic rollback on error

        Args:
            db: Database session
            user_id: Owner user ID
            strategy_create: Strategy creation data

        Returns:
            Created strategy object

        Raises:
            SQLAlchemyError: Database error (rolled back automatically)
        """
        try:
            with transaction_scope(db):
                db_strategy = Strategy(
                    user_id=user_id,
                    name=strategy_create.name,
                    description=strategy_create.description,
                    code=strategy_create.code,
                    parameters=strategy_create.parameters,
                    status=strategy_create.status,
                    engine_type=strategy_create.engine_type,
                )

                db.add(db_strategy)
                # commit 自動執行於 transaction_scope

            db.refresh(db_strategy)
            return db_strategy

        except SQLAlchemyError as e:
            logger.error(f"建立策略失敗：{str(e)}")
            raise
        except Exception as e:
            logger.error(f"建立策略時發生未預期錯誤：{str(e)}")
            raise

    @staticmethod
    def update(
        db: Session,
        strategy: Strategy,
        strategy_update: StrategyUpdate
    ) -> Strategy:
        """
        Update strategy with automatic rollback on error

        Args:
            db: Database session
            strategy: Existing strategy object
            strategy_update: Update data

        Returns:
            Updated strategy object

        Raises:
            SQLAlchemyError: Database error (rolled back automatically)
        """
        try:
            with transaction_scope(db):
                update_data = strategy_update.model_dump(exclude_unset=True)

                for field, value in update_data.items():
                    setattr(strategy, field, value)

                db.add(strategy)
                # commit 自動執行於 transaction_scope

            db.refresh(strategy)
            return strategy

        except SQLAlchemyError as e:
            logger.error(f"更新策略失敗：{str(e)}")
            raise
        except Exception as e:
            logger.error(f"更新策略時發生未預期錯誤：{str(e)}")
            raise

    @staticmethod
    def delete(db: Session, strategy: Strategy) -> None:
        """
        Delete strategy with automatic rollback on error

        Args:
            db: Database session
            strategy: Strategy to delete

        Raises:
            SQLAlchemyError: Database error (rolled back automatically)
        """
        try:
            with transaction_scope(db):
                db.delete(strategy)
                # commit 自動執行於 transaction_scope

        except SQLAlchemyError as e:
            logger.error(f"刪除策略失敗：{str(e)}")
            raise
        except Exception as e:
            logger.error(f"刪除策略時發生未預期錯誤：{str(e)}")
            raise

    @staticmethod
    def update_status(
        db: Session,
        strategy: Strategy,
        status: StrategyStatus
    ) -> Strategy:
        """
        Update strategy status with automatic rollback on error

        Args:
            db: Database session
            strategy: Strategy object
            status: New status

        Returns:
            Updated strategy object

        Raises:
            SQLAlchemyError: Database error (rolled back automatically)
        """
        try:
            with transaction_scope(db):
                strategy.status = status
                db.add(strategy)
                # commit 自動執行於 transaction_scope

            db.refresh(strategy)
            return strategy

        except SQLAlchemyError as e:
            logger.error(f"更新策略狀態失敗：{str(e)}")
            raise
        except Exception as e:
            logger.error(f"更新策略狀態時發生未預期錯誤：{str(e)}")
            raise

    @staticmethod
    def is_owner(db: Session, strategy_id: int, user_id: int) -> bool:
        """
        Check if user owns the strategy

        Args:
            db: Database session
            strategy_id: Strategy ID
            user_id: User ID

        Returns:
            True if user owns the strategy
        """
        return (
            db.query(Strategy)
            .filter(
                and_(
                    Strategy.id == strategy_id,
                    Strategy.user_id == user_id
                )
            )
            .count() > 0
        )
