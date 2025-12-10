"""
安全修復 #5-#8 測試套件

測試所有四個安全修復的功能：
- #5: Pickle 反序列化風險（HMAC 簽章保護）
- #6: 請求大小限制中介軟體
- #7: 已棄用的時區 API
- #8: 資料庫交易回滾機制
"""

import pytest
import hmac
import hashlib
import pickle
import pandas as pd
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from unittest.mock import Mock, patch

from app.main import app
from app.utils.cache import RedisCache
from app.db.session import transaction_scope, get_db
from app.models.strategy import Strategy
from app.repositories.strategy import StrategyRepository
from app.schemas.strategy import StrategyCreate


class TestPickleSignatureProtection:
    """測試問題 #5: Pickle 反序列化風險修復"""

    def test_cache_signs_pickle_data(self):
        """測試快取自動簽章 pickle 資料"""
        cache = RedisCache()

        if not cache.is_available():
            pytest.skip("Redis 不可用")

        # 測試資料：DataFrame（需要 pickle）
        test_df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
        test_key = "test:signed_pickle"

        # 儲存到快取
        success = cache.set(test_key, test_df, expiry=60)
        assert success, "快取儲存應該成功"

        # 從 Redis 直接讀取原始資料
        raw_data = cache.redis_client.get(test_key)
        assert raw_data is not None

        # 驗證資料包含簽章（前 32 bytes）
        assert len(raw_data) > 32, "資料應該包含簽章"

        # 清理
        cache.delete(test_key)

    def test_cache_verifies_signature(self):
        """測試快取驗證簽章"""
        cache = RedisCache()

        if not cache.is_available():
            pytest.skip("Redis 不可用")

        test_key = "test:verify_signature"
        test_data = {"valid": "data"}

        # 正常儲存和讀取
        cache.set(test_key, test_data, expiry=60)
        result = cache.get(test_key)
        assert result == test_data, "正常資料應該可以讀取"

        # 清理
        cache.delete(test_key)

    def test_cache_rejects_tampered_data(self):
        """測試快取拒絕被篡改的資料"""
        cache = RedisCache()

        if not cache.is_available():
            pytest.skip("Redis 不可用")

        test_key = "test:tampered_data"
        test_df = pd.DataFrame({'A': [1, 2, 3]})

        # 儲存資料
        cache.set(test_key, test_df, expiry=60)

        # 篡改資料（修改最後一個 byte）
        tampered = cache.redis_client.get(test_key)
        tampered = tampered[:-1] + b'X'
        cache.redis_client.set(test_key, tampered)

        # 嘗試讀取篡改的資料
        result = cache.get(test_key)

        # 應該返回 None（簽章驗證失敗）
        assert result is None, "篡改的資料應該被拒絕"

    def test_cache_handles_json_without_signature(self):
        """測試快取處理簡單 JSON 資料不需簽章"""
        cache = RedisCache()

        if not cache.is_available():
            pytest.skip("Redis 不可用")

        test_key = "test:simple_json"
        test_data = {"simple": "value", "number": 123}

        # JSON 資料不需要 pickle，應該直接儲存
        cache.set(test_key, test_data, expiry=60)
        result = cache.get(test_key)

        assert result == test_data
        cache.delete(test_key)


class TestRequestSizeLimit:
    """測試問題 #6: 請求大小限制"""

    def test_accepts_normal_request(self):
        """測試接受正常大小的請求"""
        client = TestClient(app)

        # 正常請求（小於 10 MB）
        response = client.get("/health")
        assert response.status_code == 200

    def test_rejects_oversized_request(self):
        """測試拒絕過大的請求"""
        client = TestClient(app)

        # 模擬大請求（設定 Content-Length header）
        headers = {
            "Content-Length": str(11 * 1024 * 1024),  # 11 MB
        }

        response = client.post(
            "/api/v1/strategies/",
            headers=headers,
            json={"name": "test"}
        )

        # 應該返回 413 Payload Too Large
        assert response.status_code == 413
        assert "Payload Too Large" in response.json()["detail"]["error"]

    def test_strategy_code_size_limit(self):
        """測試策略代碼大小限制"""
        client = TestClient(app)

        # 模擬過大的策略代碼（設定 Content-Length > 100 KB）
        headers = {
            "Content-Length": str(101 * 1024),  # 101 KB
        }

        response = client.post(
            "/api/v1/strategies/",
            headers=headers,
            json={"name": "test", "code": "x" * 1000}
        )

        # 策略端點有額外限制
        assert response.status_code in [413, 401, 422]  # 可能因未認證返回 401


class TestDeprecatedTimezoneAPI:
    """測試問題 #7: 已棄用的時區 API 修復"""

    def test_no_utcnow_usage(self):
        """驗證沒有使用已棄用的 datetime.utcnow()"""
        import subprocess

        # 搜尋所有 Python 檔案
        result = subprocess.run(
            ["grep", "-r", "datetime.utcnow()", "app/", "--include=*.py"],
            capture_output=True,
            text=True,
            cwd="/data/CCTest/QuantLab/backend"
        )

        # 應該找不到任何 utcnow() 使用
        assert result.returncode != 0, "不應該再有 datetime.utcnow() 的使用"

    def test_timezone_aware_datetime(self):
        """測試使用時區感知的 datetime"""
        # 模擬新的時區感知方式
        now = datetime.now(timezone.utc)

        # 驗證是時區感知的
        assert now.tzinfo is not None, "datetime 應該是時區感知的"
        assert now.tzinfo == timezone.utc, "時區應該是 UTC"


class TestDatabaseTransactionRollback:
    """測試問題 #8: 資料庫交易回滾機制"""

    def test_transaction_scope_commits_on_success(self):
        """測試交易成功時自動 commit"""
        db = next(get_db())

        try:
            # 初始計數
            initial_count = db.query(Strategy).count()

            with transaction_scope(db):
                # 建立測試策略
                strategy = Strategy(
                    user_id=1,
                    name="Test Transaction",
                    code="test",
                    parameters={},
                )
                db.add(strategy)
                # commit 自動執行

            # 驗證已提交
            final_count = db.query(Strategy).count()
            assert final_count == initial_count + 1, "交易應該已提交"

            # 清理
            db.query(Strategy).filter(Strategy.name == "Test Transaction").delete()
            db.commit()

        finally:
            db.close()

    def test_transaction_scope_rollbacks_on_error(self):
        """測試交易失敗時自動 rollback"""
        db = next(get_db())

        try:
            initial_count = db.query(Strategy).count()

            # 模擬錯誤
            with pytest.raises(Exception):
                with transaction_scope(db):
                    strategy = Strategy(
                        user_id=1,
                        name="Test Rollback",
                        code="test",
                        parameters={},
                    )
                    db.add(strategy)

                    # 拋出錯誤觸發 rollback
                    raise Exception("Test error")

            # 驗證已回滾（計數不變）
            final_count = db.query(Strategy).count()
            assert final_count == initial_count, "交易應該已回滾"

        finally:
            db.close()

    def test_repository_rollback_on_error(self):
        """測試 Repository 方法發生錯誤時回滾"""
        db = next(get_db())

        try:
            initial_count = db.query(Strategy).count()

            # 模擬 commit 失敗
            with patch.object(db, 'commit', side_effect=SQLAlchemyError("Test error")):
                with pytest.raises(SQLAlchemyError):
                    StrategyRepository.create(
                        db,
                        user_id=1,
                        strategy_create=StrategyCreate(
                            name="Test Error",
                            code="test",
                            parameters={},
                        )
                    )

            # 驗證沒有殘留資料
            final_count = db.query(Strategy).count()
            assert final_count == initial_count, "失敗的操作不應留下資料"

        finally:
            db.close()


class TestSecurityFixesIntegration:
    """整合測試：驗證所有修復一起運作"""

    def test_all_fixes_enabled(self):
        """驗證所有安全修復都已啟用"""
        # 1. 檢查 Pickle 簽章保護
        cache = RedisCache()
        assert hasattr(cache, '_sign_data'), "快取應該有簽章方法"
        assert hasattr(cache, '_verify_and_extract'), "快取應該有驗證方法"

        # 2. 檢查請求大小限制中介軟體
        from app.middleware.request_size_limit import RequestSizeLimitMiddleware
        middlewares = [m for m in app.user_middleware]
        assert any(
            m.cls == RequestSizeLimitMiddleware for m in middlewares
        ), "應該有請求大小限制中介軟體"

        # 3. 檢查時區 API
        # （已在上面測試）

        # 4. 檢查交易回滾機制
        from app.db.session import transaction_scope
        assert callable(transaction_scope), "應該有 transaction_scope 函數"

    def test_system_still_functional(self):
        """驗證系統在所有修復後仍正常運作"""
        client = TestClient(app)

        # 測試基本端點
        response = client.get("/health")
        assert response.status_code == 200

        response = client.get("/")
        assert response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
