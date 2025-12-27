"""
Factor Evaluation Repository for database operations
因子評估的資料訪問層
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.rdagent import FactorEvaluation


class FactorEvaluationRepository:
    """Repository for factor evaluation database operations"""

    @staticmethod
    def get_by_id(db: Session, evaluation_id: int) -> Optional[FactorEvaluation]:
        """
        Get evaluation by ID

        Args:
            db: Database session
            evaluation_id: Evaluation ID

        Returns:
            FactorEvaluation object or None
        """
        return db.query(FactorEvaluation).filter(FactorEvaluation.id == evaluation_id).first()

    @staticmethod
    def get_by_factor(
        db: Session,
        factor_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> List[FactorEvaluation]:
        """
        Get evaluations by factor ID

        Args:
            db: Database session
            factor_id: Factor ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of FactorEvaluation objects
        """
        return (
            db.query(FactorEvaluation)
            .filter(FactorEvaluation.factor_id == factor_id)
            .order_by(desc(FactorEvaluation.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_latest_by_factor(
        db: Session,
        factor_id: int
    ) -> Optional[FactorEvaluation]:
        """
        Get latest evaluation for a factor

        Args:
            db: Database session
            factor_id: Factor ID

        Returns:
            Latest FactorEvaluation object or None
        """
        return (
            db.query(FactorEvaluation)
            .filter(FactorEvaluation.factor_id == factor_id)
            .order_by(desc(FactorEvaluation.created_at))
            .first()
        )

    @staticmethod
    def create(
        db: Session,
        factor_id: int,
        stock_pool: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ic: Optional[float] = None,
        icir: Optional[float] = None,
        rank_ic: Optional[float] = None,
        rank_icir: Optional[float] = None,
        sharpe_ratio: Optional[float] = None,
        annual_return: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        win_rate: Optional[float] = None,
        detailed_results: Optional[dict] = None
    ) -> FactorEvaluation:
        """
        Create new factor evaluation

        Args:
            db: Database session
            factor_id: Factor ID
            stock_pool: Stock pool (optional)
            start_date: Start date (optional)
            end_date: End date (optional)
            ic: Information Coefficient (optional)
            icir: IC Information Ratio (optional)
            rank_ic: Rank IC (optional)
            rank_icir: Rank ICIR (optional)
            sharpe_ratio: Sharpe Ratio (optional)
            annual_return: Annual return (optional)
            max_drawdown: Maximum drawdown (optional)
            win_rate: Win rate (optional)
            detailed_results: Detailed results JSON (optional)

        Returns:
            Created FactorEvaluation object
        """
        evaluation = FactorEvaluation(
            factor_id=factor_id,
            stock_pool=stock_pool,
            start_date=start_date,
            end_date=end_date,
            ic=ic,
            icir=icir,
            rank_ic=rank_ic,
            rank_icir=rank_icir,
            sharpe_ratio=sharpe_ratio,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            detailed_results=detailed_results
        )

        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)

        return evaluation

    @staticmethod
    def update(
        db: Session,
        evaluation: FactorEvaluation,
        **kwargs
    ) -> FactorEvaluation:
        """
        Update factor evaluation

        Args:
            db: Database session
            evaluation: FactorEvaluation object to update
            **kwargs: Fields to update

        Returns:
            Updated FactorEvaluation object
        """
        for key, value in kwargs.items():
            if hasattr(evaluation, key):
                setattr(evaluation, key, value)

        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)

        return evaluation

    @staticmethod
    def delete(db: Session, evaluation: FactorEvaluation) -> None:
        """
        Delete factor evaluation

        Args:
            db: Database session
            evaluation: FactorEvaluation to delete
        """
        db.delete(evaluation)
        db.commit()

    @staticmethod
    def count_by_factor(db: Session, factor_id: int) -> int:
        """
        Count evaluations by factor

        Args:
            db: Database session
            factor_id: Factor ID

        Returns:
            Total evaluation count for factor
        """
        return db.query(FactorEvaluation).filter(FactorEvaluation.factor_id == factor_id).count()

    @staticmethod
    def delete_by_factor(db: Session, factor_id: int) -> int:
        """
        Delete all evaluations for a factor

        Args:
            db: Database session
            factor_id: Factor ID

        Returns:
            Number of deleted evaluations
        """
        deleted_count = (
            db.query(FactorEvaluation)
            .filter(FactorEvaluation.factor_id == factor_id)
            .delete()
        )
        db.commit()
        return deleted_count
