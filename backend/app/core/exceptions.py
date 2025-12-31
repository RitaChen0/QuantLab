"""
全局异常处理器
Enhanced Error Handling for QuantLab
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
import traceback
from typing import Union, Dict, Any
from loguru import logger

from app.core.config import settings


class QuantLabException(Exception):
    """QuantLab 基礎異常類"""
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Dict[str, Any] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class DatabaseError(QuantLabException):
    """資料庫錯誤"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="DATABASE_ERROR",
            details=details
        )


class BacktestError(QuantLabException):
    """回測執行錯誤"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="BACKTEST_ERROR",
            details=details
        )


class StrategyError(QuantLabException):
    """策略錯誤"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="STRATEGY_ERROR",
            details=details
        )


def format_error_response(
    error: Exception,
    request: Request = None,
    include_traceback: bool = None
) -> Dict[str, Any]:
    """
    格式化錯誤響應

    Args:
        error: 異常對象
        request: FastAPI 請求對象
        include_traceback: 是否包含堆棧追蹤（None 時根據 DEBUG 決定）

    Returns:
        格式化的錯誤字典
    """
    if include_traceback is None:
        include_traceback = settings.DEBUG

    # 基本錯誤信息
    error_response = {
        "success": False,
        "error": {
            "type": type(error).__name__,
            "message": str(error),
        }
    }

    # QuantLab 自定義異常
    if isinstance(error, QuantLabException):
        error_response["error"]["code"] = error.error_code
        if error.details:
            error_response["error"]["details"] = error.details

    # 添加請求信息（開發環境）
    if include_traceback and request:
        error_response["request"] = {
            "method": request.method,
            "url": str(request.url),
            "client": request.client.host if request.client else None,
        }

    # 添加完整堆棧追蹤（開發環境）
    if include_traceback:
        error_response["error"]["traceback"] = traceback.format_exc()

        # 嘗試獲取更多上下文信息
        if hasattr(error, '__cause__') and error.__cause__:
            error_response["error"]["cause"] = {
                "type": type(error.__cause__).__name__,
                "message": str(error.__cause__)
            }

    # 生產環境：隱藏敏感信息，提供友好的錯誤訊息
    else:
        if isinstance(error, QuantLabException):
            # 自定義異常可以顯示用戶友好的信息
            error_response["error"]["message"] = error.message
        else:
            # 為常見錯誤類型提供友好的訊息
            error_type = type(error).__name__
            friendly_messages = {
                "DatabaseError": "資料庫暫時無法訪問，請稍後再試",
                "IntegrityError": "資料完整性錯誤，可能存在重複或關聯的數據",
                "OperationalError": "資料庫操作失敗，請檢查連接或稍後再試",
                "ValidationError": "輸入的資料格式不正確，請檢查後重試",
                "ValueError": "輸入的數值不正確，請檢查輸入範圍",
                "KeyError": "缺少必要的資料欄位",
                "TypeError": "資料類型錯誤，請檢查輸入格式",
                "AttributeError": "資料結構錯誤",
                "FileNotFoundError": "找不到指定的檔案或資源",
                "PermissionError": "沒有足夠的權限執行此操作",
                "TimeoutError": "操作超時，請稍後再試",
                "ConnectionError": "網絡連接失敗，請檢查網絡設置",
            }
            error_response["error"]["message"] = friendly_messages.get(
                error_type,
                "系統錯誤，請聯繫管理員"
            )

    return error_response


async def quantlab_exception_handler(request: Request, exc: QuantLabException):
    """QuantLab 自定義異常處理器"""
    logger.error(
        f"QuantLab Exception: {exc.error_code} - {exc.message}",
        extra={"details": exc.details}
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(exc, request)
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP 異常處理器"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "type": "HTTPException",
                "message": exc.detail,
                "code": f"HTTP_{exc.status_code}"
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """請求驗證異常處理器"""
    logger.warning(f"Validation Error: {exc.errors()}")

    error_response = {
        "success": False,
        "error": {
            "type": "ValidationError",
            "message": "請求參數驗證失敗",
            "code": "VALIDATION_ERROR",
            "details": exc.errors()
        }
    }

    # 開發環境顯示詳細驗證錯誤
    if settings.DEBUG:
        error_response["error"]["raw_errors"] = str(exc)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """資料庫異常處理器"""
    logger.error(f"Database Error: {str(exc)}", exc_info=settings.DEBUG)

    error_response = {
        "success": False,
        "error": {
            "type": "DatabaseError",
            "code": "DATABASE_ERROR",
        }
    }

    # 開發環境：顯示詳細 SQL 錯誤
    if settings.DEBUG:
        error_response["error"]["message"] = str(exc)
        error_response["error"]["sql_state"] = getattr(exc, 'code', None)
        error_response["error"]["traceback"] = traceback.format_exc()
    else:
        error_response["error"]["message"] = "資料庫操作失敗"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """通用異常處理器（捕獲所有未處理的異常）"""
    logger.error(
        f"Unhandled Exception: {type(exc).__name__} - {str(exc)}",
        exc_info=True  # 永遠記錄完整堆棧到日誌
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=format_error_response(exc, request)
    )


def register_exception_handlers(app):
    """
    註冊所有異常處理器

    Usage:
        from app.core.exceptions import register_exception_handlers
        register_exception_handlers(app)
    """
    # QuantLab 自定義異常
    app.add_exception_handler(QuantLabException, quantlab_exception_handler)

    # HTTP 異常
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # 驗證異常
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # 資料庫異常
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)

    # 通用異常（必須最後註冊）
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("✅ 異常處理器已註冊")
