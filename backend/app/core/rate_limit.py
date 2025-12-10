"""
Rate limiting configuration using slowapi

Provides rate limiting middleware and decorators for API endpoints.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from typing import Optional
from loguru import logger


def get_client_identifier(request: Request) -> str:
    """
    Get client identifier for rate limiting

    Uses the following priority:
    1. User ID from token (if authenticated)
    2. X-Forwarded-For header (if behind proxy)
    3. Remote address

    Args:
        request: FastAPI request object

    Returns:
        Client identifier string
    """
    # Try to get user from request state (set by auth middleware)
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"

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
    """Predefined rate limits for different operations"""

    # Authentication endpoints
    LOGIN = "5/minute"  # 5 login attempts per minute
    REGISTER = "3/hour"  # 3 registrations per hour

    # Strategy operations
    STRATEGY_CREATE = "10/hour"  # 10 strategy creations per hour
    STRATEGY_UPDATE = "30/hour"  # 30 strategy updates per hour
    STRATEGY_VALIDATE = "20/minute"  # 20 validations per minute

    # Backtest operations
    BACKTEST_CREATE = "10/hour"  # 10 backtest creations per hour
    BACKTEST_RUN = "30/hour"  # 30 backtest executions per hour (increased for testing)

    # Data operations
    DATA_FETCH = "100/minute"  # 100 data fetches per minute

    # General API
    GENERAL_READ = "1000/hour"  # General read operations
    GENERAL_WRITE = "100/hour"  # General write operations

    # RD-Agent operations (AI-powered, LLM-based)
    RDAGENT_FACTOR_MINING = "3/hour"  # 3 factor mining tasks per hour (LLM intensive)
    RDAGENT_STRATEGY_OPT = "5/hour"  # 5 strategy optimization tasks per hour


def get_rate_limit_error_handler():
    """Get custom rate limit error handler"""
    return _rate_limit_exceeded_handler
