"""
並發限制工具

使用 Redis 實作分散式並發限制，防止同時執行過多計算密集型任務
"""

import time
from typing import Optional
from contextlib import contextmanager
from loguru import logger
import redis

from app.core.config import settings


class ConcurrentLimiter:
    """
    並發限制器

    使用 Redis 計數器實作分散式並發控制

    範例：
        limiter = ConcurrentLimiter(
            key_prefix="evaluation_limit",
            max_concurrent=3,
            timeout=3600
        )

        # 方法 1：檢查是否可執行
        if limiter.can_execute():
            with limiter.acquire():
                # 執行任務
                pass

        # 方法 2：嘗試獲取，失敗則等待
        with limiter.acquire(wait=True):
            # 執行任務
            pass
    """

    def __init__(
        self,
        key_prefix: str,
        max_concurrent: int = 3,
        timeout: int = 3600,
        redis_url: Optional[str] = None
    ):
        """
        初始化並發限制器

        Args:
            key_prefix: Redis 鍵前綴
            max_concurrent: 最大並發數量
            timeout: 任務執行超時時間（秒），防止死鎖
            redis_url: Redis 連接 URL，預設使用 settings.REDIS_URL
        """
        self.key_prefix = key_prefix
        self.max_concurrent = max_concurrent
        self.timeout = timeout

        # 連接 Redis
        try:
            self.redis_client = redis.from_url(
                redis_url or settings.REDIS_URL,
                decode_responses=True
            )
            self.redis_client.ping()
            logger.debug(f"ConcurrentLimiter initialized: {key_prefix}, max={max_concurrent}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis for ConcurrentLimiter: {e}")
            self.redis_client = None

    def _get_counter_key(self) -> str:
        """獲取計數器鍵"""
        return f"{self.key_prefix}:counter"

    def _get_lock_key(self, task_id: str) -> str:
        """獲取任務鎖鍵"""
        return f"{self.key_prefix}:lock:{task_id}"

    def is_available(self) -> bool:
        """檢查 Redis 是否可用"""
        return self.redis_client is not None

    def get_current_count(self) -> int:
        """
        獲取當前並發數量

        Returns:
            當前正在執行的任務數量
        """
        if not self.is_available():
            return 0

        try:
            count = self.redis_client.get(self._get_counter_key())
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Failed to get current count: {e}")
            return 0

    def can_execute(self) -> bool:
        """
        檢查是否可以執行新任務

        Returns:
            True 如果未達到並發限制，False 否則
        """
        if not self.is_available():
            # Redis 不可用時，不限制並發
            return True

        try:
            current = self.get_current_count()
            can_exec = current < self.max_concurrent

            if not can_exec:
                logger.warning(
                    f"Concurrent limit reached: {current}/{self.max_concurrent} "
                    f"for {self.key_prefix}"
                )

            return can_exec
        except Exception as e:
            logger.error(f"Error checking concurrent limit: {e}")
            return True  # 錯誤時不限制

    def increment(self, task_id: str) -> bool:
        """
        增加並發計數

        Args:
            task_id: 任務 ID

        Returns:
            True 如果成功增加，False 如果達到限制
        """
        if not self.is_available():
            return True

        try:
            # 使用 Lua 腳本原子性地檢查並增加
            lua_script = """
            local counter_key = KEYS[1]
            local max_concurrent = tonumber(ARGV[1])
            local current = tonumber(redis.call('GET', counter_key) or 0)

            if current < max_concurrent then
                redis.call('INCR', counter_key)
                return 1
            else
                return 0
            end
            """

            result = self.redis_client.eval(
                lua_script,
                1,
                self._get_counter_key(),
                self.max_concurrent
            )

            if result == 1:
                # 設置任務鎖，帶超時時間防止死鎖
                lock_key = self._get_lock_key(task_id)
                self.redis_client.setex(lock_key, self.timeout, "1")
                logger.debug(f"Incremented concurrent counter: {self.key_prefix}, task={task_id}")
                return True
            else:
                logger.warning(f"Failed to increment: limit reached for {self.key_prefix}")
                return False

        except Exception as e:
            logger.error(f"Error incrementing concurrent counter: {e}")
            return True  # 錯誤時允許執行

    def decrement(self, task_id: str) -> None:
        """
        減少並發計數

        Args:
            task_id: 任務 ID
        """
        if not self.is_available():
            return

        try:
            counter_key = self._get_counter_key()
            lock_key = self._get_lock_key(task_id)

            # 檢查鎖是否存在（確保是同一個任務）
            if self.redis_client.exists(lock_key):
                # 刪除鎖
                self.redis_client.delete(lock_key)

                # 減少計數（不能小於 0）
                current = self.redis_client.get(counter_key)
                if current and int(current) > 0:
                    self.redis_client.decr(counter_key)
                    logger.debug(f"Decremented concurrent counter: {self.key_prefix}, task={task_id}")
            else:
                logger.warning(f"Task lock not found when decrementing: {task_id}")

        except Exception as e:
            logger.error(f"Error decrementing concurrent counter: {e}")

    def reset(self) -> None:
        """
        重置計數器（清除所有鎖和計數）

        危險操作：僅用於測試或緊急情況
        """
        if not self.is_available():
            return

        try:
            # 刪除計數器
            self.redis_client.delete(self._get_counter_key())

            # 刪除所有任務鎖
            pattern = f"{self.key_prefix}:lock:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)

            logger.info(f"Reset concurrent limiter: {self.key_prefix}")

        except Exception as e:
            logger.error(f"Error resetting concurrent limiter: {e}")

    @contextmanager
    def acquire(self, task_id: Optional[str] = None, wait: bool = False, wait_timeout: int = 300):
        """
        上下文管理器：獲取執行槽位

        Args:
            task_id: 任務 ID，預設使用時間戳
            wait: 是否等待槽位釋放
            wait_timeout: 最大等待時間（秒）

        Raises:
            RuntimeError: 如果無法獲取槽位且 wait=False
            TimeoutError: 如果等待超時

        範例：
            with limiter.acquire(task_id="task_123"):
                # 執行任務
                process_heavy_task()
        """
        if task_id is None:
            task_id = f"task_{int(time.time() * 1000)}"

        acquired = False
        start_time = time.time()

        try:
            # 嘗試獲取槽位
            while not acquired:
                if self.increment(task_id):
                    acquired = True
                    logger.info(
                        f"Acquired concurrent slot: {self.key_prefix}, "
                        f"task={task_id}, current={self.get_current_count()}/{self.max_concurrent}"
                    )
                    break

                if not wait:
                    raise RuntimeError(
                        f"Concurrent limit reached: {self.get_current_count()}/{self.max_concurrent} "
                        f"for {self.key_prefix}"
                    )

                # 等待模式
                elapsed = time.time() - start_time
                if elapsed >= wait_timeout:
                    raise TimeoutError(
                        f"Timeout waiting for concurrent slot: {self.key_prefix}, "
                        f"waited {elapsed:.1f}s"
                    )

                logger.debug(f"Waiting for concurrent slot: {self.key_prefix}, task={task_id}")
                time.sleep(5)  # 每 5 秒重試一次

            # 執行任務
            yield

        finally:
            # 釋放槽位
            if acquired:
                self.decrement(task_id)
                logger.info(
                    f"Released concurrent slot: {self.key_prefix}, "
                    f"task={task_id}, current={self.get_current_count()}/{self.max_concurrent}"
                )


# 全局評估限制器實例
evaluation_limiter = ConcurrentLimiter(
    key_prefix="evaluation_concurrent",
    max_concurrent=3,  # 最多同時 3 個評估
    timeout=3600       # 1 小時超時
)
