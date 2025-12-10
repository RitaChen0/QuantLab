"""
Authentication API Routes
Handles user registration, login, and token management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.user import UserCreate, UserLogin, Token, User
from app.services.user_service import UserService
from app.api.dependencies import get_current_user
from app.models.user import User as UserModel

router = APIRouter()


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(
    user_create: UserCreate,
    db: Session = Depends(get_db),
):
    """
    使用者註冊

    註冊新使用者帳號

    Args:
        user_create: 使用者註冊資料（email, username, password）
        db: 資料庫會話

    Returns:
        新建立的使用者資訊

    Raises:
        400: Email 或 username 已被使用
    """
    service = UserService(db)
    user = service.register(user_create)
    return user


@router.post("/login", response_model=Token)
async def login(
    user_login: UserLogin,
    db: Session = Depends(get_db),
):
    """
    使用者登入

    使用 username/email 和密碼登入，返回 JWT tokens

    Args:
        user_login: 登入資料（username 或 email, password）
        db: 資料庫會話

    Returns:
        包含 access_token 和 refresh_token 的 Token 物件

    Raises:
        401: 使用者名稱或密碼錯誤
    """
    service = UserService(db)
    token = service.login(user_login.username, user_login.password)
    return token


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: UserModel = Depends(get_current_user),
):
    """
    刷新 Token

    使用當前有效的 token 獲取新的 access token

    Args:
        current_user: 當前認證的使用者

    Returns:
        新的 Token 物件
    """
    from app.core.security import create_access_token, create_refresh_token

    access_token = create_access_token(subject=current_user.id)
    refresh_token_new = create_refresh_token(subject=current_user.id)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token_new,
        token_type="bearer",
    )


@router.post("/logout")
async def logout(
    current_user: UserModel = Depends(get_current_user),
):
    """
    使用者登出

    登出當前使用者（客戶端需刪除 token）

    Args:
        current_user: 當前認證的使用者

    Returns:
        成功訊息
    """
    # Note: JWT tokens are stateless, so logout is handled client-side
    # The client should delete the token from local storage
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: UserModel = Depends(get_current_user),
):
    """
    取得當前使用者資訊

    返回當前認證使用者的詳細資訊

    Args:
        current_user: 當前認證的使用者

    Returns:
        使用者資訊
    """
    return current_user


@router.post("/verify-email", response_model=User)
async def verify_email(
    token: str,
    db: Session = Depends(get_db),
):
    """
    驗證郵箱

    使用郵件中的 token 驗證用戶郵箱

    Args:
        token: 驗證 token（從郵件連結獲取）
        db: 資料庫會話

    Returns:
        已驗證的使用者資訊

    Raises:
        400: Token 無效或已過期
    """
    service = UserService(db)
    user = service.verify_email(token)
    return user


@router.post("/resend-verification")
async def resend_verification_email(
    email: str,
    db: Session = Depends(get_db),
):
    """
    重新發送驗證郵件

    為指定郵箱重新發送驗證郵件

    Args:
        email: 用戶郵箱
        db: 資料庫會話

    Returns:
        成功訊息

    Raises:
        404: 用戶不存在
        400: 郵箱已驗證
        500: 發送郵件失敗
    """
    service = UserService(db)
    service.resend_verification_email(email)
    return {"message": "Verification email sent successfully"}
