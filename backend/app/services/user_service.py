"""
User service for business logic
"""

import secrets
from typing import Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from loguru import logger
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, Token, PasswordUpdate
from app.repositories.user import UserRepository
from app.core.security import verify_password, create_access_token, create_refresh_token, get_password_hash
from app.core.config import settings
from app.utils.email import EmailService


class UserService:
    """Service for user-related business logic"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository()

    def register(self, user_create: UserCreate) -> User:
        """
        Register a new user

        Args:
            user_create: User registration data

        Returns:
            Created user object

        Raises:
            HTTPException: If email or username already exists
        """
        # Check if email already exists
        existing_user = self.repo.get_by_email(self.db, user_create.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Check if username already exists
        existing_user = self.repo.get_by_username(self.db, user_create.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

        # Create user (email_verified will be False by default)
        user = self.repo.create(self.db, user_create)

        # Generate verification token
        verification_token = secrets.token_urlsafe(32)
        token_expires = datetime.now(timezone.utc) + timedelta(hours=24)

        # Save verification token
        user.verification_token = verification_token
        user.verification_token_expires = token_expires
        self.db.commit()
        self.db.refresh(user)

        # Send verification email
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
        try:
            EmailService.send_verification_email(
                to_email=user.email,
                username=user.username,
                verification_url=verification_url,
            )
            logger.info(f"Verification email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
            # Don't fail registration if email fails, user can request resend

        return user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate user with username/email and password

        Args:
            username: Username or email
            password: Plain text password

        Returns:
            User object if authentication successful, None otherwise
        """
        # Get user by email or username
        user = self.repo.get_by_email_or_username(self.db, username)

        if not user:
            return None

        # Verify password
        if not verify_password(password, user.hashed_password):
            return None

        # Check if user is active
        if not user.is_active:
            return None

        return user

    def login(self, username: str, password: str) -> Token:
        """
        Login user and generate JWT tokens

        Args:
            username: Username or email
            password: Plain text password

        Returns:
            Token object with access and refresh tokens

        Raises:
            HTTPException: If authentication fails or email not verified
        """
        user = self.authenticate(username, password)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if email is verified
        if not user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified. Please check your email for the verification link.",
            )

        # Update last login
        self.repo.update_last_login(self.db, user)

        # Generate tokens
        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.repo.get_by_id(self.db, user_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.repo.get_by_email(self.db, email)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.repo.get_by_username(self.db, username)

    def update_user(self, user_id: int, user_update: UserUpdate) -> User:
        """
        Update user

        Args:
            user_id: User ID
            user_update: Update data

        Returns:
            Updated user object

        Raises:
            HTTPException: If user not found or validation fails
        """
        user = self.repo.get_by_id(self.db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Check if email is being changed and already exists
        if user_update.email and user_update.email != user.email:
            existing_user = self.repo.get_by_email(self.db, user_update.email)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )

        # Check if username is being changed and already exists
        if user_update.username and user_update.username != user.username:
            existing_user = self.repo.get_by_username(self.db, user_update.username)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken",
                )

        return self.repo.update(self.db, user, user_update)

    def delete_user(self, user_id: int) -> None:
        """
        Delete user

        Args:
            user_id: User ID

        Raises:
            HTTPException: If user not found
        """
        user = self.repo.get_by_id(self.db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        self.repo.delete(self.db, user)

    def verify_email(self, token: str) -> User:
        """
        Verify user email with token

        Args:
            token: Verification token from email

        Returns:
            Verified user object

        Raises:
            HTTPException: If token invalid or expired
        """
        # Find user by verification token
        user = self.repo.get_by_verification_token(self.db, token)

        if not user:
            # Token not found in active verification_token field
            # Check if this token was already used (in last_verification_token)
            user = self.repo.get_by_last_verification_token(self.db, token)

            if user and user.email_verified:
                # Email already verified with this token - return success
                logger.info(f"Email already verified for user {user.email} (duplicate verification attempt)")
                return user

            # Token not found anywhere or email not verified
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token",
            )

        # Check if token expired
        if user.verification_token_expires and datetime.now(timezone.utc) > user.verification_token_expires:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification token expired. Please request a new verification email.",
            )

        # Mark email as verified and move token to last_verification_token
        user.email_verified = True
        user.last_verification_token = user.verification_token  # Save for future reference
        user.verification_token = None
        user.verification_token_expires = None
        self.db.commit()
        self.db.refresh(user)

        logger.info(f"Email verified for user {user.email}")
        return user

    def resend_verification_email(self, email: str) -> None:
        """
        Resend verification email to user

        Args:
            email: User email

        Raises:
            HTTPException: If user not found or already verified
        """
        user = self.repo.get_by_email(self.db, email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified",
            )

        # Generate new verification token
        verification_token = secrets.token_urlsafe(32)
        token_expires = datetime.now(timezone.utc) + timedelta(hours=24)

        # Save new token
        user.verification_token = verification_token
        user.verification_token_expires = token_expires
        self.db.commit()

        # Send verification email
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
        try:
            EmailService.send_verification_email(
                to_email=user.email,
                username=user.username,
                verification_url=verification_url,
            )
            logger.info(f"Verification email resent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to resend verification email to {user.email}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email",
            )

    def update_password(self, user: User, password_update: PasswordUpdate) -> User:
        """
        Update user password

        Args:
            user: Current user object
            password_update: Password update data

        Returns:
            Updated user object

        Raises:
            HTTPException: If current password is incorrect
        """
        # Verify current password
        if not verify_password(password_update.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        # Hash new password
        user.hashed_password = get_password_hash(password_update.new_password)
        self.db.commit()
        self.db.refresh(user)

        logger.info(f"Password updated for user {user.email}")
        return user
