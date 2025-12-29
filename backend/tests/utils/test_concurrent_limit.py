"""
並發限制器測試

測試 ConcurrentLimiter 的各種場景
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch
from app.utils.concurrent_limit import ConcurrentLimiter


class TestConcurrentLimiter:
    """並發限制器基本功能測試"""

    @pytest.fixture
    def limiter(self):
        """創建測試用限制器"""
        limiter = ConcurrentLimiter(
            key_prefix="test_concurrent",
            max_concurrent=3,
            timeout=60
        )
        limiter.reset()  # 清空計數器
        yield limiter
        limiter.reset()  # 清理

    def test_limiter_initialization(self):
        """測試初始化"""
        limiter = ConcurrentLimiter(
            key_prefix="test_init",
            max_concurrent=5,
            timeout=120
        )

        assert limiter.key_prefix == "test_init"
        assert limiter.max_concurrent == 5
        assert limiter.timeout == 120
        assert limiter.is_available()  # Redis 可用

    def test_redis_keys(self, limiter):
        """測試 Redis 鍵生成"""
        counter_key = limiter._get_counter_key()
        lock_key = limiter._get_lock_key("task_123")

        assert counter_key == "test_concurrent:counter"
        assert lock_key == "test_concurrent:lock:task_123"

    def test_initial_state(self, limiter):
        """測試初始狀態"""
        assert limiter.get_current_count() == 0
        assert limiter.can_execute() is True

    def test_increment_single(self, limiter):
        """測試單次增加"""
        result = limiter.increment("task_1")

        assert result is True
        assert limiter.get_current_count() == 1

    def test_increment_multiple(self, limiter):
        """測試多次增加"""
        assert limiter.increment("task_1") is True
        assert limiter.get_current_count() == 1

        assert limiter.increment("task_2") is True
        assert limiter.get_current_count() == 2

        assert limiter.increment("task_3") is True
        assert limiter.get_current_count() == 3

    def test_increment_beyond_limit(self, limiter):
        """測試超過限制"""
        # 填滿到限制
        limiter.increment("task_1")
        limiter.increment("task_2")
        limiter.increment("task_3")

        # 第 4 個應該失敗
        result = limiter.increment("task_4")
        assert result is False
        assert limiter.get_current_count() == 3

    def test_decrement_single(self, limiter):
        """測試單次減少"""
        limiter.increment("task_1")
        assert limiter.get_current_count() == 1

        limiter.decrement("task_1")
        assert limiter.get_current_count() == 0

    def test_decrement_multiple(self, limiter):
        """測試多次減少"""
        limiter.increment("task_1")
        limiter.increment("task_2")
        limiter.increment("task_3")
        assert limiter.get_current_count() == 3

        limiter.decrement("task_1")
        assert limiter.get_current_count() == 2

        limiter.decrement("task_2")
        assert limiter.get_current_count() == 1

        limiter.decrement("task_3")
        assert limiter.get_current_count() == 0

    def test_can_execute_state_changes(self, limiter):
        """測試 can_execute 狀態變化"""
        assert limiter.can_execute() is True

        limiter.increment("task_1")
        limiter.increment("task_2")
        assert limiter.can_execute() is True  # 2/3 還可以

        limiter.increment("task_3")
        assert limiter.can_execute() is False  # 3/3 已滿

        limiter.decrement("task_1")
        assert limiter.can_execute() is True  # 2/3 又可以了

    def test_context_manager_basic(self, limiter):
        """測試基本上下文管理器"""
        assert limiter.get_current_count() == 0

        with limiter.acquire(task_id="test_task"):
            assert limiter.get_current_count() == 1
            # 模擬任務執行
            time.sleep(0.1)

        # 退出後應該自動釋放
        assert limiter.get_current_count() == 0

    def test_context_manager_nested(self, limiter):
        """測試嵌套上下文管理器"""
        with limiter.acquire(task_id="task_1"):
            assert limiter.get_current_count() == 1

            with limiter.acquire(task_id="task_2"):
                assert limiter.get_current_count() == 2

                with limiter.acquire(task_id="task_3"):
                    assert limiter.get_current_count() == 3

                assert limiter.get_current_count() == 2

            assert limiter.get_current_count() == 1

        assert limiter.get_current_count() == 0

    def test_context_manager_exception_cleanup(self, limiter):
        """測試異常時也會釋放"""
        try:
            with limiter.acquire(task_id="test_task"):
                assert limiter.get_current_count() == 1
                raise ValueError("Test error")
        except ValueError:
            pass

        # 即使有異常，也應該釋放
        assert limiter.get_current_count() == 0

    def test_context_manager_limit_reached(self, limiter):
        """測試上下文管理器達到限制"""
        # 填滿槽位
        limiter.increment("task_1")
        limiter.increment("task_2")
        limiter.increment("task_3")

        # 嘗試獲取應該失敗
        with pytest.raises(RuntimeError, match="Concurrent limit reached"):
            with limiter.acquire(task_id="task_4", wait=False):
                pass

    def test_reset(self, limiter):
        """測試重置功能"""
        # 增加一些計數
        limiter.increment("task_1")
        limiter.increment("task_2")
        assert limiter.get_current_count() == 2

        # 重置
        limiter.reset()

        # 應該清空
        assert limiter.get_current_count() == 0

    def test_lock_timeout(self, limiter):
        """測試鎖超時設置"""
        import redis

        limiter.increment("task_1")

        # 檢查鎖的 TTL
        lock_key = limiter._get_lock_key("task_1")
        ttl = limiter.redis_client.ttl(lock_key)

        # TTL 應該接近 timeout（60 秒）
        assert ttl > 0
        assert ttl <= limiter.timeout


@pytest.mark.integration
class TestConcurrentLimiterIntegration:
    """並發限制器整合測試"""

    @pytest.fixture
    def limiter(self):
        """創建測試用限制器"""
        limiter = ConcurrentLimiter(
            key_prefix="test_integration",
            max_concurrent=3,
            timeout=60
        )
        limiter.reset()
        yield limiter
        limiter.reset()

    def test_concurrent_threads(self, limiter):
        """測試多執行緒並發"""
        results = []

        def worker(task_id):
            try:
                with limiter.acquire(task_id=f"task_{task_id}", wait=False):
                    results.append(("acquired", task_id))
                    time.sleep(0.5)
                results.append(("released", task_id))
            except RuntimeError:
                results.append(("rejected", task_id))

        # 啟動 5 個執行緒
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 應該有 3 個 acquired，2 個 rejected
        acquired = [r for r in results if r[0] == "acquired"]
        rejected = [r for r in results if r[0] == "rejected"]
        released = [r for r in results if r[0] == "released"]

        assert len(acquired) == 3, f"Expected 3 acquired, got {len(acquired)}: {acquired}"
        assert len(rejected) == 2, f"Expected 2 rejected, got {len(rejected)}: {rejected}"
        assert len(released) == 3, f"Expected 3 released, got {len(released)}: {released}"

        # 最終應該清空
        assert limiter.get_current_count() == 0

    def test_sequential_waves(self, limiter):
        """測試順序波次執行"""
        def execute_task(task_id):
            with limiter.acquire(task_id=f"task_{task_id}"):
                time.sleep(0.2)
                return task_id

        # 第一波：3 個任務
        results_1 = []
        threads_1 = []
        for i in range(3):
            t = threading.Thread(target=lambda tid: results_1.append(execute_task(tid)), args=(i,))
            threads_1.append(t)
            t.start()

        # 確認達到限制
        time.sleep(0.1)
        assert limiter.get_current_count() == 3

        # 等待完成
        for t in threads_1:
            t.join()

        assert len(results_1) == 3
        assert limiter.get_current_count() == 0

        # 第二波：2 個任務
        results_2 = []
        threads_2 = []
        for i in range(3, 5):
            t = threading.Thread(target=lambda tid: results_2.append(execute_task(tid)), args=(i,))
            threads_2.append(t)
            t.start()

        time.sleep(0.1)
        assert limiter.get_current_count() == 2

        for t in threads_2:
            t.join()

        assert len(results_2) == 2
        assert limiter.get_current_count() == 0

    def test_wait_mode(self, limiter):
        """測試等待模式"""
        results = []

        def worker(task_id, wait):
            try:
                with limiter.acquire(task_id=f"task_{task_id}", wait=wait, wait_timeout=10):
                    results.append(("acquired", task_id))
                    time.sleep(1)
                results.append(("completed", task_id))
            except (RuntimeError, TimeoutError) as e:
                results.append(("error", task_id, str(e)))

        # 啟動 4 個執行緒，前 3 個不等待，第 4 個等待
        threads = []
        for i in range(3):
            t = threading.Thread(target=worker, args=(i, False))
            threads.append(t)
            t.start()

        time.sleep(0.1)  # 確保前 3 個已獲取

        # 第 4 個使用等待模式
        t4 = threading.Thread(target=worker, args=(3, True))
        threads.append(t4)
        t4.start()

        # 等待所有完成
        for t in threads:
            t.join()

        # 前 3 個應該成功，第 4 個等待後也成功
        acquired = [r for r in results if r[0] == "acquired"]
        completed = [r for r in results if r[0] == "completed"]

        assert len(acquired) == 4, f"Expected 4 acquired, got {acquired}"
        assert len(completed) == 4, f"Expected 4 completed, got {completed}"

    def test_stress_test(self, limiter):
        """壓力測試：大量並發請求"""
        results = []

        def worker(task_id):
            try:
                with limiter.acquire(task_id=f"task_{task_id}", wait=False):
                    results.append(("success", task_id))
                    time.sleep(0.1)
            except RuntimeError:
                results.append(("rejected", task_id))

        # 啟動 20 個執行緒
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 應該有一些成功，一些被拒絕
        success = [r for r in results if r[0] == "success"]
        rejected = [r for r in results if r[0] == "rejected"]

        assert len(success) + len(rejected) == 20
        assert len(success) >= 3  # 至少有 3 個成功
        assert len(rejected) >= 10  # 大部分被拒絕

        # 最終清空
        assert limiter.get_current_count() == 0


class TestConcurrentLimiterEdgeCases:
    """邊界情況測試"""

    def test_redis_unavailable(self):
        """測試 Redis 不可用時的行為"""
        with patch('app.utils.concurrent_limit.redis.from_url') as mock_redis:
            mock_redis.side_effect = Exception("Redis connection failed")

            limiter = ConcurrentLimiter(key_prefix="test_unavailable", max_concurrent=3)

            # Redis 不可用時應該不限制
            assert limiter.is_available() is False
            assert limiter.can_execute() is True
            assert limiter.increment("task_1") is True

    def test_decrement_nonexistent_lock(self):
        """測試減少不存在的鎖"""
        limiter = ConcurrentLimiter(key_prefix="test_nonexistent", max_concurrent=3)
        limiter.reset()

        # 嘗試減少不存在的鎖（應該不報錯）
        limiter.decrement("nonexistent_task")

        # 計數應該保持 0
        assert limiter.get_current_count() == 0

    def test_max_concurrent_one(self):
        """測試最大並發為 1 的情況"""
        limiter = ConcurrentLimiter(key_prefix="test_one", max_concurrent=1, timeout=60)
        limiter.reset()

        # 第一個成功
        assert limiter.increment("task_1") is True
        assert limiter.can_execute() is False

        # 第二個失敗
        assert limiter.increment("task_2") is False

        # 釋放後可以再次執行
        limiter.decrement("task_1")
        assert limiter.can_execute() is True
        assert limiter.increment("task_2") is True

    def test_auto_generated_task_id(self):
        """測試自動生成的任務 ID"""
        limiter = ConcurrentLimiter(key_prefix="test_auto_id", max_concurrent=3, timeout=60)
        limiter.reset()

        # 不提供 task_id，應該自動生成
        with limiter.acquire():
            assert limiter.get_current_count() == 1

        assert limiter.get_current_count() == 0

    def test_counter_consistency(self):
        """測試計數器一致性"""
        limiter = ConcurrentLimiter(key_prefix="test_consistency", max_concurrent=3, timeout=60)
        limiter.reset()

        # 多次增加和減少
        for i in range(10):
            limiter.increment(f"task_{i}")
            limiter.decrement(f"task_{i}")

        # 計數應該仍然是 0
        assert limiter.get_current_count() == 0
