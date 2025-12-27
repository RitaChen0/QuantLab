"""
RDAgentTask repository for database operations
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.models.rdagent import RDAgentTask, TaskType, TaskStatus


class RDAgentTaskRepository:
    """Repository for RDAgentTask database operations"""

    @staticmethod
    def get_by_id(db: Session, task_id: int) -> Optional[RDAgentTask]:
        """
        Get task by ID

        Args:
            db: Database session
            task_id: Task ID

        Returns:
            RDAgentTask object or None
        """
        return db.query(RDAgentTask).filter(RDAgentTask.id == task_id).first()

    @staticmethod
    def get_by_id_and_user(
        db: Session,
        task_id: int,
        user_id: int
    ) -> Optional[RDAgentTask]:
        """
        Get task by ID and user ID (ownership check)

        Args:
            db: Database session
            task_id: Task ID
            user_id: User ID

        Returns:
            RDAgentTask object or None
        """
        return (
            db.query(RDAgentTask)
            .filter(
                and_(
                    RDAgentTask.id == task_id,
                    RDAgentTask.user_id == user_id
                )
            )
            .first()
        )

    @staticmethod
    def get_by_user(
        db: Session,
        user_id: int,
        task_type: Optional[TaskType] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[RDAgentTask]:
        """
        Get tasks by user ID

        Args:
            db: Database session
            user_id: User ID
            task_type: Filter by task type (optional)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of RDAgentTask objects
        """
        query = db.query(RDAgentTask).filter(RDAgentTask.user_id == user_id)

        if task_type:
            query = query.filter(RDAgentTask.task_type == task_type)

        return query.order_by(desc(RDAgentTask.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def create(db: Session, task: RDAgentTask) -> RDAgentTask:
        """
        Create new task

        Args:
            db: Database session
            task: RDAgentTask object to create

        Returns:
            Created RDAgentTask object
        """
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def update(db: Session, task: RDAgentTask) -> RDAgentTask:
        """
        Update task

        Args:
            db: Database session
            task: RDAgentTask object to update

        Returns:
            Updated RDAgentTask object
        """
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def delete(db: Session, task: RDAgentTask) -> None:
        """
        Delete task

        Args:
            db: Database session
            task: RDAgentTask object to delete
        """
        db.delete(task)
        db.commit()

    @staticmethod
    def count_by_user(
        db: Session,
        user_id: int,
        task_type: Optional[TaskType] = None,
        status: Optional[TaskStatus] = None
    ) -> int:
        """
        Count tasks by user

        Args:
            db: Database session
            user_id: User ID
            task_type: Filter by task type (optional)
            status: Filter by status (optional)

        Returns:
            Number of tasks
        """
        query = db.query(RDAgentTask).filter(RDAgentTask.user_id == user_id)

        if task_type:
            query = query.filter(RDAgentTask.task_type == task_type)

        if status:
            query = query.filter(RDAgentTask.status == status)

        return query.count()

    @staticmethod
    def get_by_status(
        db: Session,
        status: TaskStatus,
        limit: int = 100
    ) -> List[RDAgentTask]:
        """
        Get tasks by status

        Args:
            db: Database session
            status: Task status
            limit: Maximum number of records to return

        Returns:
            List of RDAgentTask objects
        """
        return (
            db.query(RDAgentTask)
            .filter(RDAgentTask.status == status)
            .order_by(desc(RDAgentTask.created_at))
            .limit(limit)
            .all()
        )
