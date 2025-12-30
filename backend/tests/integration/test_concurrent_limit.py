"""
並發限制功能整合測試

模擬多個評估任務並發執行，驗證並發限制是否正常工作
"""

import time
import pytest
import threading
from app.utils.concurrent_limit import evaluation_limiter


def simulate_evaluation_task(task_id: str, duration: float = 2.0):
    """模擬評估任務執行"""
    try:
        with evaluation_limiter.acquire(task_id=task_id, wait=False):
            # 模擬評估計算
            time.sleep(duration)
    except RuntimeError:
        # 達到並發限制，任務被拒絕
        pass


@pytest.mark.integration
def test_sequential_execution():
    """測試順序執行（應該全部成功）"""
    evaluation_limiter.reset()

    for i in range(1, 6):
        simulate_evaluation_task(f"seq_{i}", duration=0.5)

    # 驗證所有任務完成後計數為 0
    assert evaluation_limiter.get_current_count() == 0


@pytest.mark.integration
@pytest.mark.slow
def test_concurrent_execution():
    """測試並發執行（應該限制為 3 個）"""
    evaluation_limiter.reset()

    results = {"success": 0, "rejected": 0}
    lock = threading.Lock()

    def worker(task_id):
        try:
            with evaluation_limiter.acquire(task_id=f"concurrent_{task_id}", wait=False):
                with lock:
                    results["success"] += 1
                time.sleep(2)
        except RuntimeError:
            with lock:
                results["rejected"] += 1

    # 啟動 10 個執行緒
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(1, 11)]

    for t in threads:
        t.start()

    # 等待 0.5 秒後檢查並發數
    time.sleep(0.5)
    current_count = evaluation_limiter.get_current_count()

    # 等待所有任務完成
    for t in threads:
        t.join()

    # 驗證
    assert results['success'] >= 3, f"應該至少有 3 個任務成功，實際: {results['success']}"
    assert results['rejected'] >= 5, f"應該至少有 5 個任務被拒絕，實際: {results['rejected']}"
    assert evaluation_limiter.get_current_count() == 0, "所有任務完成後計數應該為 0"


@pytest.mark.integration
@pytest.mark.slow
def test_wait_mode():
    """測試等待模式（應該全部成功，但排隊執行）"""
    evaluation_limiter.reset()

    results = []
    lock = threading.Lock()

    def worker(task_id):
        try:
            with evaluation_limiter.acquire(task_id=f"wait_{task_id}", wait=True, wait_timeout=30):
                with lock:
                    results.append(("success", task_id))
                time.sleep(1)
        except (RuntimeError, TimeoutError) as e:
            with lock:
                results.append(("error", task_id))

    # 啟動 5 個執行緒
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(1, 6)]

    for t in threads:
        t.start()

    # 等待所有任務完成
    for t in threads:
        t.join()

    success_count = len([r for r in results if r[0] == "success"])

    # 驗證
    assert success_count == 5, f"等待模式下所有任務都應該成功，實際: {success_count}/5"
    assert evaluation_limiter.get_current_count() == 0, "所有任務完成後計數應該為 0"


@pytest.mark.integration
def test_redis_state():
    """測試 Redis 狀態檢查"""
    evaluation_limiter.reset()

    # 檢查 Redis 連接
    assert evaluation_limiter.is_available(), "Redis 應該可用"

    # 檢查初始狀態
    assert evaluation_limiter.get_current_count() == 0, "初始計數應該為 0"

    # 測試計數器
    evaluation_limiter.increment("test_1")
    assert evaluation_limiter.get_current_count() == 1

    evaluation_limiter.decrement("test_1")
    assert evaluation_limiter.get_current_count() == 0

    # 檢查 Redis 鍵
    counter_key = evaluation_limiter._get_counter_key()
    assert counter_key is not None

    lock_key = evaluation_limiter._get_lock_key("test_task")
    assert lock_key is not None
