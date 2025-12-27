"""
GeneratedModel repository for database operations
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.models.rdagent import GeneratedModel


class GeneratedModelRepository:
    """Repository for GeneratedModel database operations"""

    @staticmethod
    def get_by_id(db: Session, model_id: int) -> Optional[GeneratedModel]:
        """
        Get model by ID

        Args:
            db: Database session
            model_id: Model ID

        Returns:
            GeneratedModel object or None
        """
        return db.query(GeneratedModel).filter(GeneratedModel.id == model_id).first()

    @staticmethod
    def get_by_id_and_user(
        db: Session,
        model_id: int,
        user_id: int
    ) -> Optional[GeneratedModel]:
        """
        Get model by ID and user ID (ownership check)

        Args:
            db: Database session
            model_id: Model ID
            user_id: User ID

        Returns:
            GeneratedModel object or None
        """
        return (
            db.query(GeneratedModel)
            .filter(
                and_(
                    GeneratedModel.id == model_id,
                    GeneratedModel.user_id == user_id
                )
            )
            .first()
        )

    @staticmethod
    def get_by_user(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[GeneratedModel]:
        """
        Get models by user ID

        Args:
            db: Database session
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of GeneratedModel objects
        """
        return (
            db.query(GeneratedModel)
            .filter(GeneratedModel.user_id == user_id)
            .order_by(desc(GeneratedModel.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_task(
        db: Session,
        task_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[GeneratedModel]:
        """
        Get models by task ID

        Args:
            db: Database session
            task_id: Task ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of GeneratedModel objects
        """
        return (
            db.query(GeneratedModel)
            .filter(GeneratedModel.task_id == task_id)
            .order_by(desc(GeneratedModel.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def create(db: Session, model: GeneratedModel) -> GeneratedModel:
        """
        Create new model

        Args:
            db: Database session
            model: GeneratedModel object to create

        Returns:
            Created GeneratedModel object
        """
        db.add(model)
        db.commit()
        db.refresh(model)
        return model

    @staticmethod
    def update(db: Session, model: GeneratedModel) -> GeneratedModel:
        """
        Update model

        Args:
            db: Database session
            model: GeneratedModel object to update

        Returns:
            Updated GeneratedModel object
        """
        db.add(model)
        db.commit()
        db.refresh(model)
        return model

    @staticmethod
    def delete(db: Session, model: GeneratedModel) -> None:
        """
        Delete model

        Args:
            db: Database session
            model: GeneratedModel object to delete
        """
        db.delete(model)
        db.commit()

    @staticmethod
    def count_by_user(db: Session, user_id: int) -> int:
        """
        Count models by user

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Number of models
        """
        return db.query(GeneratedModel).filter(GeneratedModel.user_id == user_id).count()

    @staticmethod
    def count_by_task(db: Session, task_id: int) -> int:
        """
        Count models by task

        Args:
            db: Database session
            task_id: Task ID

        Returns:
            Number of models
        """
        return db.query(GeneratedModel).filter(GeneratedModel.task_id == task_id).count()
