"""
Structured logging utilities

Provides consistent logging with contextual information across the application.
"""

from typing import Optional, Dict, Any
from loguru import logger
import contextvars

# Context variables for request tracking
request_id_var = contextvars.ContextVar("request_id", default=None)
user_id_var = contextvars.ContextVar("user_id", default=None)


def set_request_context(request_id: str, user_id: Optional[int] = None):
    """
    Set request context for logging

    Args:
        request_id: Unique request identifier
        user_id: Optional user ID
    """
    request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)


def clear_request_context():
    """Clear request context"""
    request_id_var.set(None)
    user_id_var.set(None)


def get_log_context() -> Dict[str, Any]:
    """
    Get current logging context

    Returns:
        Dictionary with contextual information
    """
    context = {}

    request_id = request_id_var.get()
    if request_id:
        context["request_id"] = request_id

    user_id = user_id_var.get()
    if user_id:
        context["user_id"] = user_id

    return context


class StructuredLogger:
    """
    Structured logger with contextual information

    Provides consistent logging with automatic context injection.
    """

    @staticmethod
    def _merge_context(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Merge custom extra fields with request context

        Args:
            extra: Optional extra fields to include

        Returns:
            Merged context dictionary
        """
        context = get_log_context()
        if extra:
            context.update(extra)
        return context

    @staticmethod
    def debug(message: str, **kwargs):
        """Log debug message with context"""
        context = StructuredLogger._merge_context(kwargs)
        logger.bind(**context).debug(message)

    @staticmethod
    def info(message: str, **kwargs):
        """Log info message with context"""
        context = StructuredLogger._merge_context(kwargs)
        logger.bind(**context).info(message)

    @staticmethod
    def warning(message: str, **kwargs):
        """Log warning message with context"""
        context = StructuredLogger._merge_context(kwargs)
        logger.bind(**context).warning(message)

    @staticmethod
    def error(message: str, **kwargs):
        """Log error message with context"""
        context = StructuredLogger._merge_context(kwargs)
        logger.bind(**context).error(message)

    @staticmethod
    def critical(message: str, **kwargs):
        """Log critical message with context"""
        context = StructuredLogger._merge_context(kwargs)
        logger.bind(**context).critical(message)


# API operation structured logging
class APILogger:
    """Structured logger for API operations"""

    @staticmethod
    def log_request(
        method: str,
        path: str,
        user_id: Optional[int] = None,
        **extra
    ):
        """
        Log API request

        Args:
            method: HTTP method
            path: Request path
            user_id: Optional user ID
            **extra: Additional context
        """
        StructuredLogger.info(
            f"API request: {method} {path}",
            method=method,
            path=path,
            user_id=user_id,
            event="api_request",
            **extra
        )

    @staticmethod
    def log_response(
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[int] = None,
        **extra
    ):
        """
        Log API response

        Args:
            method: HTTP method
            path: Request path
            status_code: HTTP status code
            duration_ms: Request duration in milliseconds
            user_id: Optional user ID
            **extra: Additional context
        """
        log_level = "info" if status_code < 400 else "error"
        message = f"API response: {method} {path} - {status_code} ({duration_ms:.2f}ms)"

        if log_level == "info":
            StructuredLogger.info(
                message,
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                event="api_response",
                **extra
            )
        else:
            StructuredLogger.error(
                message,
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                event="api_response",
                **extra
            )

    @staticmethod
    def log_operation(
        operation: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        user_id: Optional[int] = None,
        success: bool = True,
        **extra
    ):
        """
        Log business operation

        Args:
            operation: Operation name (create, update, delete, etc.)
            entity_type: Type of entity (strategy, backtest, etc.)
            entity_id: Optional entity ID
            user_id: Optional user ID
            success: Whether operation succeeded
            **extra: Additional context
        """
        message = f"{operation.capitalize()} {entity_type}"
        if entity_id:
            message += f" {entity_id}"

        StructuredLogger.info(
            message,
            operation=operation,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            success=success,
            event="business_operation",
            **extra
        )


# Convenience instances
structured_log = StructuredLogger()
api_log = APILogger()
