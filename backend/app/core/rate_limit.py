"""
Rate limiting configuration using slowapi

Provides rate limiting middleware and decorators for API endpoints.
Supports tiered rate limiting based on member levels.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException
from typing import Optional, Callable
from functools import wraps
from loguru import logger

from app.core.member_limits import get_level_name


def get_client_identifier(request: Request) -> str:
    """
    Get client identifier for rate limiting

    Includes member level for tiered rate limiting.
    Different member levels have separate rate limit counters.

    Uses the following priority:
    1. User ID + Member Level from token (if authenticated)
    2. X-Forwarded-For header (if behind proxy)
    3. Remote address

    Args:
        request: FastAPI request object

    Returns:
        Client identifier string
    """
    # Try to get user from request state (set by auth middleware)
    if hasattr(request.state, "user") and request.state.user:
        user = request.state.user
        # Include member level in identifier for tiered limits
        level = getattr(user, 'member_level', 0)
        return f"user:{user.id}:level:{level}"

    # Try X-Forwarded-For header (for requests behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Fallback to remote address
    return get_remote_address(request)


# Get Redis URL from settings
def _get_storage_uri() -> str:
    """
    取得速率限制儲存的 URI

    優先使用 Redis 以支援分散式部署和持久化。
    如果 Redis 不可用，則回退到記憶體儲存（僅限開發環境）。

    Returns:
        儲存 URI 字串

    Raises:
        ValueError: 生產環境缺少 REDIS_URL
    """
    try:
        from app.core.config import settings

        # 檢查是否為生產環境
        is_production = settings.ENVIRONMENT.lower() == "production"

        # 嘗試使用 Redis
        if settings.REDIS_URL:
            redis_uri = settings.REDIS_URL

            # 確保 Redis URL 格式正確
            if not redis_uri.startswith("redis://"):
                redis_uri = f"redis://{redis_uri}"

            logger.info(f"🔒 速率限制使用 Redis 儲存：{redis_uri.split('@')[0]}...")
            return redis_uri
        else:
            # Redis URL 未設定
            if is_production:
                logger.error("⚠️  生產環境必須使用 Redis 進行速率限制！")
                raise ValueError("生產環境缺少 REDIS_URL 配置")
            else:
                logger.warning("⚠️  開發環境：速率限制使用記憶體儲存（重啟後重置）")
                return "memory://"

    except ValueError:
        # 重新拋出 ValueError（生產環境缺少 Redis）
        raise
    except ImportError:
        # 無法導入 settings（可能在測試環境）
        logger.warning("⚠️  無法載入設定，使用記憶體儲存")
        return "memory://"
    except Exception as e:
        logger.error(f"❌ 取得儲存 URI 時發生錯誤：{str(e)}")
        # 如果是生產環境，拋出異常；否則回退到記憶體
        try:
            from app.core.config import settings
            if settings.ENVIRONMENT.lower() == "production":
                raise
        except:
            pass
        logger.warning("⚠️  回退到記憶體儲存")
        return "memory://"


# Create limiter instance
limiter = Limiter(
    key_func=get_client_identifier,
    default_limits=["200/hour"],  # Global default limit
    storage_uri=_get_storage_uri(),  # 🔒 使用 Redis 儲存（支援分散式部署）
    strategy="fixed-window",  # Rate limit strategy
)


# Rate limit configurations for different endpoint types
class RateLimits:
    """Predefined rate limits for different operations

    Limits are automatically adjusted based on ENVIRONMENT setting:
    - production: Strict limits for security
    - development/testing: Relaxed limits for easier testing
    """

    @staticmethod
    def _get_limits():
        """Get rate limits based on environment"""
        try:
            from app.core.config import settings
            is_production = settings.ENVIRONMENT.lower() == "production"
        except:
            is_production = False  # Default to development

        if is_production:
            # Production: Strict limits
            return {
                # Authentication endpoints
                "LOGIN": "5/minute",
                "REGISTER": "3/hour",

                # Strategy operations
                "STRATEGY_CREATE": "10/hour",
                "STRATEGY_UPDATE": "30/hour",
                "STRATEGY_VALIDATE": "20/minute",

                # Backtest operations
                "BACKTEST_CREATE": "10/hour",
                "BACKTEST_RUN": "30/hour",

                # Data operations
                "DATA_FETCH": "100/minute",

                # General API
                "GENERAL_READ": "1000/hour",
                "GENERAL_WRITE": "100/hour",

                # RD-Agent operations (AI-powered, LLM-based)
                "RDAGENT_FACTOR_MINING": "3/hour",
                "RDAGENT_STRATEGY_OPT": "5/hour",
            }
        else:
            # Development/Testing: Relaxed limits (10x)
            logger.info("🔓 Rate Limit: 使用開發環境配置（寬鬆限制）")
            return {
                # Authentication endpoints
                "LOGIN": "50/minute",  # 10x
                "REGISTER": "30/hour",  # 10x

                # Strategy operations
                "STRATEGY_CREATE": "100/hour",  # 10x
                "STRATEGY_UPDATE": "300/hour",  # 10x
                "STRATEGY_VALIDATE": "200/minute",  # 10x

                # Backtest operations
                "BACKTEST_CREATE": "100/hour",  # 10x - 避免測試受限
                "BACKTEST_RUN": "300/hour",  # 10x - 與 Celery 層對齊

                # Data operations
                "DATA_FETCH": "1000/minute",  # 10x

                # General API
                "GENERAL_READ": "10000/hour",  # 10x
                "GENERAL_WRITE": "1000/hour",  # 10x

                # RD-Agent operations (AI-powered, LLM-based)
                "RDAGENT_FACTOR_MINING": "30/hour",  # 10x
                "RDAGENT_STRATEGY_OPT": "50/hour",  # 10x
            }

    # Initialize limits
    _limits = _get_limits()

    # Authentication endpoints
    LOGIN = _limits["LOGIN"]
    REGISTER = _limits["REGISTER"]

    # Strategy operations
    STRATEGY_CREATE = _limits["STRATEGY_CREATE"]
    STRATEGY_UPDATE = _limits["STRATEGY_UPDATE"]
    STRATEGY_VALIDATE = _limits["STRATEGY_VALIDATE"]

    # Backtest operations
    BACKTEST_CREATE = _limits["BACKTEST_CREATE"]
    BACKTEST_RUN = _limits["BACKTEST_RUN"]

    # Data operations
    DATA_FETCH = _limits["DATA_FETCH"]

    # General API
    GENERAL_READ = _limits["GENERAL_READ"]
    GENERAL_WRITE = _limits["GENERAL_WRITE"]

    # RD-Agent operations (AI-powered, LLM-based)
    RDAGENT_FACTOR_MINING = _limits["RDAGENT_FACTOR_MINING"]
    RDAGENT_STRATEGY_OPT = _limits["RDAGENT_STRATEGY_OPT"]


def get_rate_limit_error_handler():
    """Get custom rate limit error handler"""
    return _rate_limit_exceeded_handler


# ==================== Legacy Functions (Deprecated) ====================
# These functions are no longer used in the new 0-9 level system.
# Rate limits are now managed directly in member_limits.py with fixed values per level.
# Keeping these commented out for reference during migration.

# def tiered_rate_limit(base_limit: str):
#     """
#     DEPRECATED: Tiered rate limiting is now handled via member_limits.py
#     with fixed values per level (0-9) instead of multipliers.
#     """
#     pass

# def get_user_limit_info(user_level: int, base_limit: str) -> dict:
#     """
#     DEPRECATED: Use get_all_limits() from member_limits.py instead.
#     """
#     pass
