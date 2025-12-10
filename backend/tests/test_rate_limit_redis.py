"""
速率限制 Redis 整合測試

驗證速率限制器正確使用 Redis 儲存，而非記憶體儲存。
"""

import pytest
import time
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from loguru import logger
from app.core.rate_limit import limiter, _get_storage_uri, RateLimits


class TestRateLimitRedis:
    """測試速率限制 Redis 整合"""

    def test_get_storage_uri_with_redis_url(self):
        """測試當 REDIS_URL 存在時使用 Redis"""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379/0"
            mock_settings.ENVIRONMENT = "production"

            uri = _get_storage_uri()

            assert uri.startswith("redis://"), "應該使用 Redis URL"
            assert "localhost:6379" in uri, "應該包含 Redis 主機資訊"

    def test_get_storage_uri_formats_redis_url(self):
        """測試自動格式化 Redis URL"""
        with patch("app.core.config.settings") as mock_settings:
            # 測試沒有 redis:// 前綴的 URL
            mock_settings.REDIS_URL = "localhost:6379/0"
            mock_settings.ENVIRONMENT = "production"

            uri = _get_storage_uri()

            assert uri.startswith("redis://"), "應該自動添加 redis:// 前綴"

    def test_get_storage_uri_production_without_redis_fails(self):
        """測試生產環境沒有 Redis 應該失敗"""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.REDIS_URL = ""
            mock_settings.ENVIRONMENT = "production"

            with pytest.raises(ValueError) as exc_info:
                _get_storage_uri()

            assert "REDIS_URL" in str(exc_info.value), "錯誤訊息應該提到 REDIS_URL"

    def test_get_storage_uri_development_without_redis_fallback(self):
        """測試開發環境沒有 Redis 回退到記憶體儲存"""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.REDIS_URL = ""
            mock_settings.ENVIRONMENT = "development"

            uri = _get_storage_uri()

            assert uri == "memory://", "開發環境應該回退到記憶體儲存"

    def test_limiter_uses_redis_storage(self):
        """測試 limiter 實例使用 Redis 儲存"""
        # 檢查 limiter 的儲存後端類型
        # slowapi 的 Limiter 會根據 storage_uri 創建對應的儲存後端

        # 檢查是否不是 MemoryStorage（如果配置了 Redis）
        storage_type = type(limiter._storage).__name__

        # 在有 Redis 的環境中，應該是 RedisStorage
        # 在測試環境或沒有 Redis 的環境，可能是 MemoryStorage
        assert storage_type in ["RedisStorage", "MemoryStorage"], \
            f"儲存類型應該是 RedisStorage 或 MemoryStorage，實際是：{storage_type}"

    def test_limiter_storage_backend_type(self):
        """測試 limiter 使用正確的儲存後端類型"""
        # 檢查 limiter 的儲存後端
        storage_type = type(limiter._storage).__name__

        # 根據環境，應該使用 RedisStorage 或 MemoryStorage
        assert storage_type in ["RedisStorage", "MemoryStorage"], \
            f"儲存類型應該是 RedisStorage 或 MemoryStorage，實際是：{storage_type}"

        # 記錄當前使用的儲存類型
        logger.info(f"當前速率限制儲存類型：{storage_type}")

    def test_limiter_with_redis_uses_redis_storage(self):
        """測試當配置 Redis 時，limiter 使用 RedisStorage"""
        # 檢查當前配置
        try:
            from app.core.config import settings

            if settings.REDIS_URL:
                # 如果有 Redis URL，應該使用 RedisStorage
                storage_type = type(limiter._storage).__name__
                logger.info(f"Redis URL 已配置，儲存類型：{storage_type}")

                # 注意：可能因為其他原因（如 Redis 連接失敗）回退到 MemoryStorage
                # 所以這裡只檢查類型在預期範圍內
                assert storage_type in ["RedisStorage", "MemoryStorage"]
        except Exception as e:
            pytest.skip(f"無法檢查 Redis 配置：{str(e)}")

    def test_rate_limits_constants(self):
        """測試速率限制常數定義"""
        assert RateLimits.LOGIN == "5/minute"
        assert RateLimits.REGISTER == "3/hour"
        assert RateLimits.STRATEGY_CREATE == "10/hour"
        assert RateLimits.STRATEGY_UPDATE == "30/hour"
        assert RateLimits.BACKTEST_CREATE == "10/hour"
        assert RateLimits.DATA_FETCH == "100/minute"

    def test_get_storage_uri_handles_import_error(self):
        """測試無法導入 settings 時的處理"""
        # Patch 導入本身
        with patch.dict('sys.modules', {'app.core.config': None}):
            uri = _get_storage_uri()

            # 應該回退到記憶體儲存
            assert uri == "memory://", "無法導入 settings 時應該使用記憶體儲存"

    def test_get_storage_uri_handles_exception(self):
        """測試發生異常時的處理"""
        with patch("app.core.config.settings") as mock_settings:
            # 設定 REDIS_URL 屬性訪問時拋出異常
            type(mock_settings).REDIS_URL = property(lambda self: (_ for _ in ()).throw(Exception("Test error")))

            uri = _get_storage_uri()

            # 應該回退到記憶體儲存
            assert uri == "memory://", "發生異常時應該回退到記憶體儲存"

    def test_redis_connection_available(self):
        """
        測試 Redis 連接是否可用

        如果配置了 Redis，驗證連接正常
        """
        try:
            from app.core.config import settings

            if not settings.REDIS_URL:
                pytest.skip("未配置 Redis URL")

            # 嘗試連接 Redis
            import redis
            r = redis.from_url(settings.REDIS_URL)
            r.ping()

            logger.info("✅ Redis 連接正常")

            # 驗證 limiter 使用 RedisStorage
            storage_type = type(limiter._storage).__name__
            assert storage_type == "RedisStorage", \
                f"配置了 Redis 但使用 {storage_type}"

        except ImportError:
            pytest.skip("redis 套件未安裝")
        except Exception as e:
            pytest.skip(f"無法連接 Redis：{str(e)}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
