"""
Generated Factor Repository for database operations
自動生成因子的資料訪問層
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.models.rdagent import GeneratedFactor


class GeneratedFactorRepository:
    """Repository for generated factor database operations"""

    @staticmethod
    def get_by_id(db: Session, factor_id: int) -> Optional[GeneratedFactor]:
        """
        Get factor by ID

        Args:
            db: Database session
            factor_id: Factor ID

        Returns:
            GeneratedFactor object or None
        """
        return db.query(GeneratedFactor).filter(GeneratedFactor.id == factor_id).first()

    @staticmethod
    def get_by_id_and_user(
        db: Session,
        factor_id: int,
        user_id: int
    ) -> Optional[GeneratedFactor]:
        """
        Get factor by ID and user ID (ownership check)

        Args:
            db: Database session
            factor_id: Factor ID
            user_id: User ID

        Returns:
            GeneratedFactor object or None if not found or not owned by user
        """
        return (
            db.query(GeneratedFactor)
            .filter(
                and_(
                    GeneratedFactor.id == factor_id,
                    GeneratedFactor.user_id == user_id
                )
            )
            .first()
        )

    @staticmethod
    def get_by_ids(
        db: Session,
        factor_ids: List[int]
    ) -> List[GeneratedFactor]:
        """
        Get factors by IDs

        Args:
            db: Database session
            factor_ids: List of factor IDs

        Returns:
            List of GeneratedFactor objects
        """
        return (
            db.query(GeneratedFactor)
            .filter(GeneratedFactor.id.in_(factor_ids))
            .all()
        )

    @staticmethod
    def get_by_user(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> List[GeneratedFactor]:
        """
        Get factors by user

        Args:
            db: Database session
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of GeneratedFactor objects
        """
        return (
            db.query(GeneratedFactor)
            .filter(GeneratedFactor.user_id == user_id)
            .order_by(desc(GeneratedFactor.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_task(
        db: Session,
        task_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> List[GeneratedFactor]:
        """
        Get factors by task ID

        Args:
            db: Database session
            task_id: RDAgent task ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of GeneratedFactor objects
        """
        return (
            db.query(GeneratedFactor)
            .filter(GeneratedFactor.task_id == task_id)
            .order_by(desc(GeneratedFactor.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def is_owner(db: Session, factor_id: int, user_id: int) -> bool:
        """
        Check if user owns the factor

        Args:
            db: Database session
            factor_id: Factor ID
            user_id: User ID

        Returns:
            True if user owns the factor
        """
        return (
            db.query(GeneratedFactor)
            .filter(
                and_(
                    GeneratedFactor.id == factor_id,
                    GeneratedFactor.user_id == user_id
                )
            )
            .count() > 0
        )

    @staticmethod
    def create(
        db: Session,
        task_id: int,
        user_id: int,
        name: str,
        formula: str,
        description: Optional[str] = None,
        code: Optional[str] = None,
        category: Optional[str] = None,
        ic: Optional[float] = None,
        icir: Optional[float] = None,
        sharpe_ratio: Optional[float] = None,
        annual_return: Optional[float] = None,
        factor_metadata: Optional[dict] = None
    ) -> GeneratedFactor:
        """
        Create new generated factor

        Args:
            db: Database session
            task_id: RDAgent task ID
            user_id: User ID
            name: Factor name
            formula: Qlib expression formula
            description: Factor description (optional)
            code: Python implementation code (optional)
            category: Factor category (optional)
            ic: Information Coefficient (optional)
            icir: IC Information Ratio (optional)
            sharpe_ratio: Sharpe Ratio (optional)
            annual_return: Annual return (optional)
            factor_metadata: Additional metadata (optional)

        Returns:
            Created GeneratedFactor object
        """
        factor = GeneratedFactor(
            task_id=task_id,
            user_id=user_id,
            name=name,
            formula=formula,
            description=description,
            code=code,
            category=category,
            ic=ic,
            icir=icir,
            sharpe_ratio=sharpe_ratio,
            annual_return=annual_return,
            factor_metadata=factor_metadata
        )

        db.add(factor)
        db.commit()
        db.refresh(factor)

        return factor

    @staticmethod
    def update(
        db: Session,
        factor: GeneratedFactor,
        **kwargs
    ) -> GeneratedFactor:
        """
        Update generated factor

        Args:
            db: Database session
            factor: GeneratedFactor object to update
            **kwargs: Fields to update

        Returns:
            Updated GeneratedFactor object
        """
        for key, value in kwargs.items():
            if hasattr(factor, key):
                setattr(factor, key, value)

        db.add(factor)
        db.commit()
        db.refresh(factor)

        return factor

    @staticmethod
    def delete(db: Session, factor: GeneratedFactor) -> None:
        """
        Delete generated factor

        Args:
            db: Database session
            factor: GeneratedFactor to delete
        """
        db.delete(factor)
        db.commit()

    @staticmethod
    def count_by_user(db: Session, user_id: int) -> int:
        """
        Count factors by user

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Total factor count for user
        """
        return db.query(GeneratedFactor).filter(GeneratedFactor.user_id == user_id).count()

    @staticmethod
    def count_by_task(db: Session, task_id: int) -> int:
        """
        Count factors by task

        Args:
            db: Database session
            task_id: RDAgent task ID

        Returns:
            Total factor count for task
        """
        return db.query(GeneratedFactor).filter(GeneratedFactor.task_id == task_id).count()

    @staticmethod
    def delete_by_task(db: Session, task_id: int) -> int:
        """
        Delete all factors associated with a task

        Args:
            db: Database session
            task_id: RDAgent task ID

        Returns:
            Number of factors deleted
        """
        count = db.query(GeneratedFactor).filter(GeneratedFactor.task_id == task_id).delete()
        db.commit()
        return count
