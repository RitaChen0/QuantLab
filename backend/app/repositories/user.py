"""
User repository for database operations
"""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash


class UserRepository:
    """Repository for user database operations"""

    @staticmethod
    def get_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        """Get user by username"""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_by_email_or_username(db: Session, identifier: str) -> Optional[User]:
        """Get user by email or username"""
        return (
            db.query(User)
            .filter(or_(User.email == identifier, User.username == identifier))
            .first()
        )

    @staticmethod
    def get_by_verification_token(db: Session, token: str) -> Optional[User]:
        """
        Get user by verification token

        Args:
            db: Database session
            token: Verification token

        Returns:
            User object or None if not found
        """
        return db.query(User).filter(User.verification_token == token).first()

    @staticmethod
    def get_by_last_verification_token(db: Session, token: str) -> Optional[User]:
        """
        Get user by last verification token (used for friendly error handling)

        Args:
            db: Database session
            token: Last verification token

        Returns:
            User object or None if not found
        """
        return db.query(User).filter(User.last_verification_token == token).first()

    @staticmethod
    def get_by_telegram_id(db: Session, telegram_id: int) -> Optional[User]:
        """
        Get user by Telegram ID

        Args:
            db: Database session
            telegram_id: Telegram chat ID

        Returns:
            User object or None if not found
        """
        return db.query(User).filter(User.telegram_id == telegram_id).first()

    @staticmethod
    def create(db: Session, user_create: UserCreate) -> User:
        """
        Create new user

        Args:
            db: Database session
            user_create: User creation data

        Returns:
            Created user object
        """
        # Hash the password
        hashed_password = get_password_hash(user_create.password)

        # Create user object
        db_user = User(
            email=user_create.email,
            username=user_create.username,
            hashed_password=hashed_password,
            full_name=user_create.full_name,
            is_active=True,
            is_superuser=False,
        )

        # Add to database
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        return db_user

    @staticmethod
    def update(db: Session, user: User, user_update: UserUpdate) -> User:
        """
        Update user

        Args:
            db: Database session
            user: Existing user object
            user_update: Update data

        Returns:
            Updated user object
        """
        update_data = user_update.model_dump(exclude_unset=True)

        # Hash password if provided
        if "password" in update_data:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password

        # Update user fields
        for field, value in update_data.items():
            setattr(user, field, value)

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def delete(db: Session, user: User) -> None:
        """
        Delete user

        Args:
            db: Database session
            user: User to delete
        """
        db.delete(user)
        db.commit()

    @staticmethod
    def update_last_login(db: Session, user: User) -> User:
        """
        Update user's last login timestamp

        Args:
            db: Database session
            user: User object

        Returns:
            Updated user object
        """
        from datetime import datetime, timezone

        user.last_login = datetime.now(timezone.utc)
        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
        """
        Get all users with pagination

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of users
        """
        return db.query(User).offset(skip).limit(limit).all()

    @staticmethod
    def count(db: Session) -> int:
        """
        Count total number of users

        Args:
            db: Database session

        Returns:
            Total user count
        """
        return db.query(User).count()

    @staticmethod
    def count_active(db: Session) -> int:
        """
        Count active users

        Args:
            db: Database session

        Returns:
            Active user count
        """
        return db.query(User).filter(User.is_active == True).count()
