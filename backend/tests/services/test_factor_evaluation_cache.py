"""
測試因子評估 Redis 快取功能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from app.services.factor_evaluation_service import FactorEvaluationService, _evaluation_cache_key
from app.models.rdagent import GeneratedFactor
from app.utils.cache import cache


class TestFactorEvaluationCache:
    """測試因子評估快取"""

    def test_cache_key_generation(self):
        """測試快取鍵生成邏輯"""
        # 測試基本鍵生成
        key1 = _evaluation_cache_key(
            factor_id=1,
            stock_pool="all",
            start_date="2023-01-01",
            end_date="2023-12-31"
        )
        assert key1 == "1:all:2023-01-01:2023-12-31"

        # 測試預設值處理
        key2 = _evaluation_cache_key(
            factor_id=2,
            stock_pool="top100",
            start_date=None,
            end_date=None
        )
        assert key2 == "2:top100:default:default"

        # 測試相同參數生成相同鍵
        key3 = _evaluation_cache_key(
            factor_id=1,
            stock_pool="all",
            start_date="2023-01-01",
            end_date="2023-12-31",
            save_to_db=True  # 不影響快取鍵
        )
        assert key3 == key1

        key4 = _evaluation_cache_key(
            factor_id=1,
            stock_pool="all",
            start_date="2023-01-01",
            end_date="2023-12-31",
            save_to_db=False  # 不影響快取鍵
        )
        assert key4 == key1

    def test_clear_evaluation_cache(self):
        """測試清除因子快取"""
        mock_db = Mock()
        service = FactorEvaluationService(mock_db)

        with patch.object(cache, 'clear_pattern') as mock_clear:
            mock_clear.return_value = 5  # 清除了 5 個快取項目

            count = service.clear_evaluation_cache(factor_id=1)

            assert count == 5
            mock_clear.assert_called_once_with("factor_evaluation:1:*")

    def test_clear_all_evaluation_cache(self):
        """測試清除所有評估快取"""
        mock_db = Mock()
        service = FactorEvaluationService(mock_db)

        with patch.object(cache, 'clear_pattern') as mock_clear:
            mock_clear.return_value = 25  # 清除了 25 個快取項目

            count = service.clear_all_evaluation_cache()

            assert count == 25
            mock_clear.assert_called_once_with("factor_evaluation:*")


class TestCacheIntegration:
    """測試快取整合（需要 Redis 可用）"""

    @pytest.mark.integration
    @pytest.mark.skipif(
        not cache.is_available(),
        reason="Redis not available"
    )
    def test_real_cache_set_and_get(self):
        """測試真實的 Redis 快取讀寫"""
        test_key = "test:factor_evaluation:12345"
        test_value = {
            "ic": 0.0374,
            "icir": 0.0824,
            "sharpe_ratio": -0.3464,
            "annual_return": -0.2486
        }

        try:
            # 寫入快取
            success = cache.set(test_key, test_value, expiry=60)
            assert success is True

            # 讀取快取
            cached_value = cache.get(test_key)
            assert cached_value is not None
            assert cached_value["ic"] == test_value["ic"]
            assert cached_value["icir"] == test_value["icir"]
            assert cached_value["sharpe_ratio"] == test_value["sharpe_ratio"]
            assert cached_value["annual_return"] == test_value["annual_return"]

        finally:
            # 清理測試快取
            cache.delete(test_key)

    @pytest.mark.integration
    @pytest.mark.skipif(
        not cache.is_available(),
        reason="Redis not available"
    )
    def test_cache_expiry(self):
        """測試快取過期"""
        import time

        test_key = "test:factor_evaluation:expiry"
        test_value = {"ic": 0.05}

        try:
            # 寫入快取，1 秒過期
            cache.set(test_key, test_value, expiry=1)

            # 立即讀取應該成功
            cached_value = cache.get(test_key)
            assert cached_value is not None
            assert cached_value["ic"] == 0.05

            # 等待 2 秒後應該過期
            time.sleep(2)
            expired_value = cache.get(test_key)
            assert expired_value is None

        finally:
            cache.delete(test_key)

    @pytest.mark.integration
    @pytest.mark.skipif(
        not cache.is_available(),
        reason="Redis not available"
    )
    def test_cache_pattern_clear(self):
        """測試模式清除"""
        # 寫入多個測試快取
        test_keys = [
            "factor_evaluation:1:all:default:default",
            "factor_evaluation:1:top100:default:default",
            "factor_evaluation:2:all:default:default",
        ]

        try:
            for key in test_keys:
                cache.set(key, {"ic": 0.05}, expiry=60)

            # 清除 factor 1 的所有快取
            cleared_count = cache.clear_pattern("factor_evaluation:1:*")
            assert cleared_count == 2

            # 驗證 factor 1 的快取已清除
            assert cache.get(test_keys[0]) is None
            assert cache.get(test_keys[1]) is None

            # factor 2 的快取仍存在
            assert cache.get(test_keys[2]) is not None

        finally:
            # 清理所有測試快取
            cache.clear_pattern("factor_evaluation:*")


class TestCachePerformance:
    """測試快取效能"""

    @pytest.mark.integration
    @pytest.mark.skipif(
        not cache.is_available(),
        reason="Redis not available"
    )
    def test_cache_performance_benefit(self):
        """測試快取效能提升"""
        import time

        test_key = "test:factor_evaluation:performance"
        test_value = {
            "ic": 0.05,
            "icir": 0.8,
            # 模擬大型結果（包含 DataFrame 等）
            "large_data": list(range(10000))
        }

        try:
            # 第一次寫入（無快取）
            start_time = time.time()
            cache.set(test_key, test_value, expiry=60)
            write_time = time.time() - start_time

            # 第二次讀取（有快取）
            start_time = time.time()
            cached_value = cache.get(test_key)
            read_time = time.time() - start_time

            # 驗證快取讀取更快
            assert cached_value is not None
            assert read_time < write_time
            print(f"\n快取寫入時間: {write_time:.4f}s, 讀取時間: {read_time:.4f}s")
            print(f"效能提升: {(write_time / read_time):.2f}x")

        finally:
            cache.delete(test_key)
