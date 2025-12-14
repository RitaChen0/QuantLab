"""
User Management API Routes
Handles user CRUD operations
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.user import User, UserUpdate, PasswordUpdate
from app.services.user_service import UserService
from app.api.dependencies import get_current_user, get_current_superuser
from app.models.user import User as UserModel

router = APIRouter()


@router.get("/me", response_model=User)
async def read_current_user(
    current_user: UserModel = Depends(get_current_user),
):
    """
    取得當前使用者資訊

    Returns:
        當前使用者的詳細資訊
    """
    return current_user


@router.put("/me", response_model=User)
async def update_current_user(
    user_update: UserUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新當前使用者資訊

    Args:
        user_update: 更新資料
        current_user: 當前認證的使用者
        db: 資料庫會話

    Returns:
        更新後的使用者資訊
    """
    service = UserService(db)
    updated_user = service.update_user(current_user.id, user_update)
    return updated_user


@router.put("/me/password", response_model=User)
async def update_current_user_password(
    password_update: PasswordUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新當前使用者密碼

    Args:
        password_update: 密碼更新資料
        current_user: 當前認證的使用者
        db: 資料庫會話

    Returns:
        更新後的使用者資訊

    Raises:
        400: 目前密碼不正確
    """
    service = UserService(db)
    updated_user = service.update_password(current_user, password_update)
    return updated_user


@router.get("/{user_id}", response_model=User)
async def read_user(
    user_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    取得指定使用者資訊

    Args:
        user_id: 使用者 ID
        current_user: 當前認證的使用者
        db: 資料庫會話

    Returns:
        指定使用者的資訊

    Raises:
        403: 沒有權限（只能查看自己或需要 superuser 權限）
        404: 使用者不存在
    """
    # Users can only view their own info unless they're a superuser
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    service = UserService(db)
    user = service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: UserModel = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """
    更新指定使用者資訊（需要 superuser 權限）

    Args:
        user_id: 使用者 ID
        user_update: 更新資料
        current_user: 當前認證的 superuser
        db: 資料庫會話

    Returns:
        更新後的使用者資訊

    Raises:
        403: 沒有 superuser 權限
        404: 使用者不存在
    """
    service = UserService(db)
    updated_user = service.update_user(user_id, user_update)
    return updated_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: UserModel = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """
    刪除指定使用者（需要 superuser 權限）

    Args:
        user_id: 使用者 ID
        current_user: 當前認證的 superuser
        db: 資料庫會話

    Raises:
        403: 沒有 superuser 權限
        404: 使用者不存在
    """
    service = UserService(db)
    service.delete_user(user_id)
    return None
