"""
Redis caching utilities with HMAC-signed pickle protection
"""

import json
import pickle
import hmac
import hashlib
from typing import Optional, Any, Callable
from functools import wraps
import redis
from loguru import logger
from app.core.config import settings


class RedisCache:
    """Redis cache manager"""

    def __init__(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=False,  # Keep binary for pickle
            )
            self.redis_client.ping()
            logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self.redis_client = None

    def is_available(self) -> bool:
        """Check if Redis is available"""
        return self.redis_client is not None

    def _get_signing_key(self) -> bytes:
        """
        取得快取簽章金鑰

        如果未設定 CACHE_SIGNING_KEY，使用 JWT_SECRET 作為備用

        Returns:
            簽章金鑰（bytes）
        """
        key = settings.CACHE_SIGNING_KEY or settings.JWT_SECRET
        return key.encode('utf-8')

    def _sign_data(self, data: bytes) -> bytes:
        """
        使用 HMAC-SHA256 簽章資料

        格式: [32 bytes signature][data]

        Args:
            data: 要簽章的資料

        Returns:
            簽章後的資料
        """
        signature = hmac.new(
            self._get_signing_key(),
            data,
            hashlib.sha256
        ).digest()

        return signature + data

    def _verify_and_extract(self, signed_data: bytes) -> Optional[bytes]:
        """
        驗證簽章並提取原始資料

        Args:
            signed_data: 簽章後的資料

        Returns:
            原始資料，如果簽章驗證失敗則返回 None
        """
        if len(signed_data) < 32:
            logger.warning("簽章資料太短，無效")
            return None

        signature = signed_data[:32]  # SHA256 = 32 bytes
        data = signed_data[32:]

        expected_signature = hmac.new(
            self._get_signing_key(),
            data,
            hashlib.sha256
        ).digest()

        # 使用 compare_digest 防止時序攻擊
        if not hmac.compare_digest(signature, expected_signature):
            logger.warning("簽章驗證失敗，可能資料已被篡改")
            return None

        return data

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache with signature verification

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if not self.is_available():
            return None

        try:
            value = self.redis_client.get(key)
            if value is None:
                return None

            # 先嘗試 JSON 解碼（簡單類型，無需簽章）
            try:
                return json.loads(value.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass  # 不是 JSON，可能是簽章的 pickle

            # 嘗試驗證簽章並 unpickle（複雜物件如 DataFrame）
            try:
                # 驗證簽章
                verified_data = self._verify_and_extract(value)
                if verified_data is None:
                    logger.warning(f"簽章驗證失敗，拒絕載入快取 {key}")
                    # 刪除被篡改的快取
                    self.delete(key)
                    return None

                # 簽章驗證通過，安全 unpickle
                return pickle.loads(verified_data)

            except (pickle.UnpicklingError, TypeError, AttributeError) as e:
                logger.warning(f"Failed to unpickle cache value for key {key}: {str(e)}")
                return None

        except redis.ConnectionError as e:
            logger.error(f"Redis connection error when getting key {key}: {str(e)}")
            return None
        except redis.TimeoutError as e:
            logger.error(f"Redis timeout when getting key {key}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting cache key {key}: {str(e)}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        expiry: int = 3600,
    ) -> bool:
        """
        Set value in cache with signature protection

        Args:
            key: Cache key
            value: Value to cache
            expiry: Expiry time in seconds (default: 1 hour)

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return False

        try:
            # 先嘗試 JSON 序列化（簡單類型，無需簽章）
            try:
                serialized = json.dumps(value).encode()
            except (TypeError, ValueError):
                # Fallback: Pickle + HMAC 簽章（複雜物件如 DataFrame）
                try:
                    pickled = pickle.dumps(value)
                    # 🔒 使用 HMAC 簽章保護 pickle 資料
                    serialized = self._sign_data(pickled)
                    logger.debug(f"快取 {key} 使用簽章保護的 pickle 序列化")
                except (pickle.PicklingError, TypeError, AttributeError) as e:
                    logger.warning(f"Failed to serialize value for key {key}: {str(e)}")
                    return False

            self.redis_client.setex(key, expiry, serialized)
            return True

        except redis.ConnectionError as e:
            logger.error(f"Redis connection error when setting key {key}: {str(e)}")
            return False
        except redis.TimeoutError as e:
            logger.error(f"Redis timeout when setting key {key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error setting cache key {key}: {str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete key from cache

        Args:
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return False

        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {str(e)}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern

        Args:
            pattern: Key pattern (e.g., "stock:*")

        Returns:
            Number of keys deleted
        """
        if not self.is_available():
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Failed to clear pattern {pattern}: {str(e)}")
            return 0


# Global cache instance
cache = RedisCache()


def cached(
    key_prefix: str,
    expiry: int = 3600,
    key_func: Optional[Callable] = None,
):
    """
    Decorator to cache function results

    Args:
        key_prefix: Prefix for cache key
        expiry: Cache expiry in seconds
        key_func: Optional function to generate cache key from args

    Example:
        @cached(key_prefix="stock_price", expiry=600)
        def get_stock_price(stock_id: str):
            return expensive_api_call(stock_id)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = f"{key_prefix}:{key_func(*args, **kwargs)}"
            else:
                # Default: use function args as key
                key_parts = [str(arg) for arg in args]
                key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
                cache_key = f"{key_prefix}:{'_'.join(key_parts)}"

            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value

            # Execute function
            logger.debug(f"Cache miss: {cache_key}")
            result = func(*args, **kwargs)

            # Store in cache
            cache.set(cache_key, result, expiry)

            return result

        return wrapper
    return decorator


def cached_method(
    key_prefix: str,
    expiry: int = 3600,
    key_func: Optional[Callable] = None,
):
    """
    Decorator to cache class method results (handles 'self' argument)

    Args:
        key_prefix: Prefix for cache key
        expiry: Cache expiry in seconds
        key_func: Optional function to generate cache key from args (excluding self)

    Example:
        class MyService:
            @cached_method(key_prefix="user_strategies", expiry=300)
            def get_user_strategies(self, user_id: int):
                return expensive_query(user_id)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Generate cache key (skip 'self' argument)
            if key_func:
                cache_key = f"{key_prefix}:{key_func(*args, **kwargs)}"
            else:
                # Default: use function args as key (excluding self)
                key_parts = [str(arg) for arg in args]
                key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
                cache_key = f"{key_prefix}:{'_'.join(key_parts)}"

            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value

            # Execute function
            logger.debug(f"Cache miss: {cache_key}")
            result = func(self, *args, **kwargs)

            # Store in cache
            cache.set(cache_key, result, expiry)

            return result

        # Add cache invalidation method
        wrapper.invalidate_cache = lambda *args, **kwargs: _invalidate_cache(key_prefix, key_func, *args, **kwargs)

        return wrapper
    return decorator


def _invalidate_cache(key_prefix: str, key_func: Optional[Callable], *args, **kwargs):
    """Helper to invalidate cache for specific key"""
    if key_func:
        cache_key = f"{key_prefix}:{key_func(*args, **kwargs)}"
    else:
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
        cache_key = f"{key_prefix}:{'_'.join(key_parts)}"

    cache.delete(cache_key)
    logger.debug(f"Cache invalidated: {cache_key}")
