"""
Redis distributed lock for ensuring safe concurrent operations
"""

import redis
import time
import threading
from typing import Optional
from contextlib import contextmanager
from loguru import logger
from app.core.config import settings


class RedisLock:
    """Redis-based distributed lock implementation with auto-renewal support"""

    def __init__(self, redis_client: redis.Redis, lock_name: str,
                 timeout: int = 300, auto_renew: bool = False):
        """
        Initialize Redis lock

        Args:
            redis_client: Redis client instance
            lock_name: Name of the lock
            timeout: Lock timeout in seconds (default: 300s = 5 minutes)
            auto_renew: Enable automatic lock renewal (default: False)
        """
        self.redis_client = redis_client
        self.lock_name = f"lock:{lock_name}"
        self.timeout = timeout
        self.auto_renew = auto_renew
        self.lock_value = None
        self._renew_thread = None
        self._stop_renew = threading.Event()

    def acquire(self, blocking: bool = True, blocking_timeout: Optional[int] = None) -> bool:
        """
        Acquire the lock

        Args:
            blocking: If True, wait until lock is available
            blocking_timeout: Maximum time to wait for lock (in seconds)

        Returns:
            True if lock was acquired, False otherwise
        """
        import uuid
        self.lock_value = str(uuid.uuid4())

        start_time = time.time()

        while True:
            # Try to set the lock with NX (only if not exists) and EX (expiration)
            acquired = self.redis_client.set(
                self.lock_name,
                self.lock_value,
                nx=True,
                ex=self.timeout
            )

            if acquired:
                logger.info(f"Lock '{self.lock_name}' acquired")
                if self.auto_renew:
                    self._start_auto_renew()
                return True

            if not blocking:
                logger.warning(f"Lock '{self.lock_name}' is already held")
                return False

            # Check blocking timeout
            if blocking_timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= blocking_timeout:
                    logger.warning(f"Failed to acquire lock '{self.lock_name}' within {blocking_timeout}s")
                    return False

            # Wait a bit before retrying
            time.sleep(0.1)

    def release(self) -> bool:
        """
        Release the lock

        Returns:
            True if lock was released, False if lock was not held
        """
        if self.lock_value is None:
            return False

        # Stop auto-renewal
        self._stop_auto_renew()

        # Use Lua script to ensure atomic check-and-delete
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        result = self.redis_client.eval(lua_script, 1, self.lock_name, self.lock_value)

        if result:
            logger.info(f"Lock '{self.lock_name}' released")
            self.lock_value = None
            return True
        else:
            logger.warning(f"Lock '{self.lock_name}' was not held or already expired")
            return False

    def is_locked(self) -> bool:
        """Check if the lock is currently held"""
        return self.redis_client.exists(self.lock_name) > 0

    def __enter__(self):
        """Context manager entry"""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()
        return False  # Don't suppress exceptions

    def _start_auto_renew(self):
        """Start auto-renewal thread"""
        if self._renew_thread is not None:
            return

        def renew_lock():
            """Background thread to renew lock periodically"""
            renew_interval = self.timeout // 2  # Renew at half the timeout
            logger.info(f"Starting auto-renewal for lock '{self.lock_name}' (interval: {renew_interval}s)")

            while not self._stop_renew.wait(renew_interval):
                if self.lock_value:
                    try:
                        # Renew the lock by extending its expiration
                        self.redis_client.expire(self.lock_name, self.timeout)
                        logger.debug(f"Lock '{self.lock_name}' renewed for {self.timeout}s")
                    except Exception as e:
                        logger.error(f"Failed to renew lock '{self.lock_name}': {e}")
                        break

            logger.info(f"Auto-renewal stopped for lock '{self.lock_name}'")

        self._renew_thread = threading.Thread(target=renew_lock, daemon=True, name=f"LockRenew-{self.lock_name}")
        self._renew_thread.start()

    def _stop_auto_renew(self):
        """Stop auto-renewal thread"""
        if self._renew_thread is None:
            return

        self._stop_renew.set()
        # Wait for thread to finish (with timeout)
        self._renew_thread.join(timeout=1)
        self._renew_thread = None
        self._stop_renew.clear()


@contextmanager
def backtest_execution_lock(backtest_id: int, user_id: int):
    """
    Context manager for backtest execution lock

    使用每用戶鎖，允許不同用戶同時執行回測，但同一用戶同時只能執行一個回測

    Args:
        backtest_id: ID of the backtest being executed
        user_id: ID of the user executing the backtest

    Raises:
        RuntimeError: If lock cannot be acquired within timeout
    """
    import redis

    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    try:
        lock = RedisLock(
            redis_client,
            lock_name=f"backtest:user:{user_id}",  # 每用戶鎖
            timeout=600,  # 10 minutes initial timeout
            auto_renew=True  # 啟用自動續期
        )

        # Try to acquire lock with 30 second timeout
        acquired = lock.acquire(blocking=True, blocking_timeout=30)

        if not acquired:
            raise RuntimeError(
                "您的另一個回測正在執行中，請等待完成後再試。"
                "每個用戶同時只能執行一個回測。"
            )

        try:
            logger.info(f"Backtest {backtest_id} (user {user_id}) acquired execution lock")
            yield lock
        finally:
            lock.release()
            logger.info(f"Backtest {backtest_id} (user {user_id}) released execution lock")
    finally:
        # 確保 Redis 連接被關閉
        try:
            redis_client.close()
        except Exception as e:
            logger.warning(f"Failed to close Redis connection: {e}")
