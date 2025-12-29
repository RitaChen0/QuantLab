"""
因子評估任務並發限制測試

驗證 evaluate_factor_async 任務正確應用並發限制
"""

import pytest
import time
from unittest.mock import Mock, patch
from celery.exceptions import Retry
from app.tasks.factor_evaluation_tasks import evaluate_factor_async
from app.utils.concurrent_limit import evaluation_limiter


@pytest.mark.integration
class TestFactorEvaluationConcurrentLimit:
    """測試因子評估任務的並發限制"""

    @pytest.fixture(autouse=True)
    def reset_limiter(self):
        """每個測試前重置限制器"""
        evaluation_limiter.reset()
        yield
        evaluation_limiter.reset()

    def test_limiter_check_before_execution(self):
        """測試任務執行前檢查並發限制"""
        # 填滿槽位
        evaluation_limiter.increment("task_1")
        evaluation_limiter.increment("task_2")
        evaluation_limiter.increment("task_3")

        assert evaluation_limiter.get_current_count() == 3
        assert evaluation_limiter.can_execute() is False

    def test_task_retries_when_limit_reached(self):
        """測試達到限制時任務會重試"""
        # 填滿槽位
        evaluation_limiter.increment("task_1")
        evaluation_limiter.increment("task_2")
        evaluation_limiter.increment("task_3")

        # 驗證達到限制
        assert evaluation_limiter.get_current_count() == 3
        assert evaluation_limiter.can_execute() is False

        # 嘗試再獲取應該失敗
        assert evaluation_limiter.increment("task_4") is False

        # 釋放一個後可以執行
        evaluation_limiter.decrement("task_1")
        assert evaluation_limiter.can_execute() is True
        assert evaluation_limiter.increment("task_4") is True

    def test_limiter_state_during_execution(self):
        """測試執行期間的限制器狀態"""
        assert evaluation_limiter.get_current_count() == 0

        # 模擬獲取槽位
        with evaluation_limiter.acquire(task_id="eval_test"):
            assert evaluation_limiter.get_current_count() == 1

        # 執行完成後應該釋放
        assert evaluation_limiter.get_current_count() == 0

    def test_multiple_tasks_sequential(self):
        """測試多個任務順序執行"""
        results = []

        for i in range(5):
            task_id = f"eval_task_{i}"

            # 檢查是否可以執行
            if evaluation_limiter.can_execute():
                with evaluation_limiter.acquire(task_id=task_id):
                    results.append(("acquired", i))
                    time.sleep(0.1)
                results.append(("completed", i))
            else:
                results.append(("rejected", i))

        # 由於是順序執行，所有任務都應該成功
        acquired = [r for r in results if r[0] == "acquired"]
        completed = [r for r in results if r[0] == "completed"]

        assert len(acquired) == 5
        assert len(completed) == 5

    def test_concurrent_limit_value(self):
        """測試並發限制值設置正確"""
        assert evaluation_limiter.max_concurrent == 3
        assert evaluation_limiter.key_prefix == "evaluation_concurrent"
        assert evaluation_limiter.timeout == 3600

    def test_limiter_cleanup_after_execution(self):
        """測試執行後限制器清理"""
        # 模擬 3 個任務執行
        with evaluation_limiter.acquire(task_id="eval_1"):
            assert evaluation_limiter.get_current_count() == 1

        with evaluation_limiter.acquire(task_id="eval_2"):
            assert evaluation_limiter.get_current_count() == 1

        with evaluation_limiter.acquire(task_id="eval_3"):
            assert evaluation_limiter.get_current_count() == 1

        # 所有任務完成後應該為 0
        assert evaluation_limiter.get_current_count() == 0


class TestEvaluationLimiterConfiguration:
    """測試評估限制器配置"""

    def test_global_limiter_exists(self):
        """測試全局限制器實例存在"""
        from app.utils.concurrent_limit import evaluation_limiter as limiter

        assert limiter is not None
        assert limiter.key_prefix == "evaluation_concurrent"
        assert limiter.max_concurrent == 3

    def test_redis_connection(self):
        """測試 Redis 連接"""
        assert evaluation_limiter.is_available() is True
        assert evaluation_limiter.redis_client is not None

    def test_limiter_redis_keys(self):
        """測試限制器 Redis 鍵"""
        counter_key = evaluation_limiter._get_counter_key()
        lock_key = evaluation_limiter._get_lock_key("test_123")

        assert counter_key == "evaluation_concurrent:counter"
        assert lock_key == "evaluation_concurrent:lock:test_123"
