"""
Telegram Integration API Routes

處理 Telegram 綁定、通知管理等功能。
"""

import string
import random
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.models.user import User as UserModel
from app.core.config import settings
from app.utils.cache import cache
from app.services.notification_service import NotificationService
from app.repositories.user import UserRepository
from app.schemas.telegram import (
    TelegramBindingResponse,
    TelegramBindingCheckResponse,
    TelegramUnbindResponse,
    TestNotificationRequest,
    TestNotificationResponse,
    TelegramNotificationPreferences,
    TelegramNotificationPreferencesUpdate,
    TelegramNotificationList,
    NotificationType
)
from loguru import logger

router = APIRouter()


# ===== Helper Functions =====

def generate_verification_code(length: int = 6) -> str:
    """生成驗證碼（數字+大寫字母）"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(characters, k=length))


def get_verification_code_key(user_id: int) -> str:
    """獲取 Redis 驗證碼鍵"""
    return f"telegram:verification:{user_id}"


# ===== Binding Endpoints =====

@router.post("/telegram/request-binding", response_model=TelegramBindingResponse)
async def request_telegram_binding(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    請求生成 Telegram 綁定驗證碼

    Returns:
        驗證碼和綁定說明
    """
    # 檢查是否已綁定
    if current_user.telegram_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram already bound. Please unbind first."
        )

    # 生成驗證碼
    verification_code = generate_verification_code()

    # 存儲到 Redis（10 分鐘過期）
    redis_key = get_verification_code_key(current_user.id)
    cache.set(redis_key, verification_code, expiry=600)

    logger.info(f"Generated Telegram verification code for user {current_user.id}: {verification_code}")

    # 返回響應
    instructions = (
        f"請在 Telegram 中搜尋 @{settings.TELEGRAM_BOT_USERNAME}，"
        f"發送命令：/bind {verification_code}"
    )

    return TelegramBindingResponse(
        verification_code=verification_code,
        expires_in=600,
        bot_username=settings.TELEGRAM_BOT_USERNAME,
        instructions=instructions
    )


@router.post("/telegram/check-binding", response_model=TelegramBindingCheckResponse)
async def check_telegram_binding(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    檢查 Telegram 綁定狀態

    前端每 3 秒輪詢此接口，檢查用戶是否已完成綁定。

    Returns:
        綁定狀態信息
    """
    # 重新從數據庫查詢最新狀態
    user_repo = UserRepository()
    updated_user = user_repo.get_by_id(db, current_user.id)

    is_bound = bool(updated_user.telegram_id)

    return TelegramBindingCheckResponse(
        is_bound=is_bound,
        telegram_id=updated_user.telegram_id if is_bound else None,
        bound_at=updated_user.updated_at if is_bound else None
    )


@router.delete("/telegram/unbind", response_model=TelegramUnbindResponse)
async def unbind_telegram(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    解除 Telegram 綁定

    Returns:
        解綁結果
    """
    if not current_user.telegram_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram not bound"
        )

    # 清除 telegram_id
    user_repo = UserRepository()
    from app.schemas.user import UserUpdate

    user_update = UserUpdate(telegram_id=None)
    user_repo.update(db, current_user, user_update)

    logger.info(f"User {current_user.id} unbound from Telegram")

    return TelegramUnbindResponse(
        success=True,
        message="Telegram unbound successfully"
    )


# ===== Bot Webhook (for receiving /bind commands) =====

@router.post("/telegram/webhook")
async def telegram_webhook(
    # Telegram webhook payload
    # 這個端點接收來自 Telegram 的 webhook 請求
    # 用於處理用戶發送的 /bind 命令
    db: Session = Depends(get_db)
):
    """
    Telegram Bot Webhook

    接收 Telegram Bot 的 webhook 請求，處理用戶命令。

    Note: 此端點需要在 Telegram BotFather 中配置 webhook URL。
          在 Phase 1 MVP 中，我們暫時使用長輪詢 (polling) 模式。
    """
    # TODO: Implement webhook handler for /bind command
    # 1. Parse Telegram update
    # 2. Extract chat_id and command text
    # 3. If command is /bind {code}, validate code
    # 4. Update user's telegram_id in database
    # 5. Send confirmation message

    return {"status": "not_implemented"}


# ===== Test Notification =====

@router.post("/telegram/test-notification", response_model=TestNotificationResponse)
async def send_test_notification(
    request: TestNotificationRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    發送測試通知

    用於測試 Telegram 綁定是否正常工作。

    Args:
        request: 測試請求（是否包含圖片）

    Returns:
        發送結果
    """
    # 檢查是否已綁定
    if not current_user.telegram_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram not bound. Please bind first."
        )

    # 發送測試通知
    notification_service = NotificationService(db)

    title = "🎉 測試通知"
    message = (
        f"哈囉 {current_user.username}！\n\n"
        f"✅ 您的 Telegram 通知已成功配置。\n"
        f"📊 當回測完成時，您將收到通知。\n"
        f"🔔 您可以在設置中調整通知偏好。"
    )

    try:
        result = notification_service.send_notification_sync(
            user_id=current_user.id,
            notification_type=NotificationType.SYSTEM_ALERT,
            title=title,
            message=message,
            image_path=None  # TODO: Add test image if requested
        )

        if result.get("telegram_sent"):
            return TestNotificationResponse(
                success=True,
                message="Test notification sent successfully",
                notification_id=result.get("notification_ids", {}).get("telegram"),
                telegram_message_id=None
            )
        else:
            errors = result.get("errors", [])
            return TestNotificationResponse(
                success=False,
                message=f"Failed to send test notification: {', '.join(errors)}",
                notification_id=None,
                telegram_message_id=None
            )

    except Exception as e:
        logger.error(f"Failed to send test notification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test notification: {str(e)}"
        )


# ===== Notification History =====

@router.get("/telegram/notifications", response_model=TelegramNotificationList)
async def get_notifications(
    limit: int = 50,
    offset: int = 0,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    獲取通知歷史

    Args:
        limit: 每頁數量 (默認 50)
        offset: 偏移量 (默認 0)

    Returns:
        通知列表
    """
    notification_service = NotificationService(db)

    result = notification_service.get_user_notifications(
        user_id=current_user.id,
        limit=limit,
        offset=offset
    )

    return TelegramNotificationList(
        total=result["total"],
        notifications=result["notifications"]
    )


# ===== Notification Preferences =====

@router.get("/telegram/preferences", response_model=TelegramNotificationPreferences)
async def get_notification_preferences(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    獲取通知偏好設置

    Returns:
        用戶的通知偏好
    """
    notification_service = NotificationService(db)
    preferences = notification_service.get_user_preferences(current_user.id)

    return preferences


@router.put("/telegram/preferences", response_model=TelegramNotificationPreferences)
async def update_notification_preferences(
    preferences_update: TelegramNotificationPreferencesUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新通知偏好設置

    Args:
        preferences_update: 更新數據

    Returns:
        更新後的通知偏好
    """
    notification_service = NotificationService(db)
    updated_preferences = notification_service.update_user_preferences(
        current_user.id,
        preferences_update
    )

    return updated_preferences
