"""
安全的錯誤訊息處理

根據環境決定錯誤訊息的詳細程度，避免在生產環境洩漏敏感信息
"""

from app.core.config import settings
from typing import Optional
import traceback


def get_safe_error_message(error: Exception, context: Optional[str] = None) -> str:
    """
    返回安全的錯誤訊息

    開發環境：返回詳細錯誤訊息
    生產環境：返回通用錯誤訊息

    Args:
        error: 異常對象
        context: 錯誤上下文（例如："回測執行"、"數據載入"）

    Returns:
        安全的錯誤訊息字符串
    """
    # 開發環境返回詳細訊息
    if settings.ENVIRONMENT == "development":
        error_detail = str(error)
        if context:
            return f"{context}失敗: {error_detail}"
        return error_detail

    # 生產環境返回通用訊息
    error_type = type(error).__name__

    # 根據異常類型返回友好的訊息
    error_messages = {
        "ValueError": "輸入的數據格式不正確，請檢查參數設置",
        "KeyError": "缺少必要的數據欄位",
        "TypeError": "數據類型不匹配",
        "FileNotFoundError": "找不到所需的文件",
        "ConnectionError": "連接服務失敗，請稍後重試",
        "TimeoutError": "操作超時，請稍後重試",
        "PermissionError": "沒有足夠的權限執行此操作",
    }

    generic_message = error_messages.get(error_type, "操作失敗，請稍後重試")

    if context:
        return f"{context}時發生錯誤: {generic_message}"

    return generic_message


def get_safe_error_detail(error: Exception) -> dict:
    """
    返回安全的錯誤詳情字典

    Args:
        error: 異常對象

    Returns:
        包含錯誤訊息和類型的字典
    """
    error_type = type(error).__name__

    result = {
        "error_type": error_type,
        "message": get_safe_error_message(error)
    }

    # 開發環境包含完整的 traceback
    if settings.ENVIRONMENT == "development":
        result["traceback"] = traceback.format_exc()
        result["raw_message"] = str(error)

    return result


def sanitize_log_message(message: str) -> str:
    """
    清理日誌訊息，移除敏感信息

    Args:
        message: 原始日誌訊息

    Returns:
        清理後的日誌訊息
    """
    import re

    # 移除可能的密碼、token 等敏感信息
    patterns = [
        (r'password["\s:=]+[^"\s,}]+', 'password=***'),
        (r'token["\s:=]+[^"\s,}]+', 'token=***'),
        (r'api[_-]?key["\s:=]+[^"\s,}]+', 'api_key=***'),
        (r'secret["\s:=]+[^"\s,}]+', 'secret=***'),
        (r'Bearer\s+[A-Za-z0-9\-._~+/]+=*', 'Bearer ***'),
    ]

    sanitized = message
    for pattern, replacement in patterns:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    return sanitized
