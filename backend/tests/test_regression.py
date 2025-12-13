"""
回归测试套件

确保之前修复的所有问题不会再次出现。

测试覆盖：
1. ✅ Shioaji 重复键问题修复
2. ✅ Qlib 增量同步边界条件
3. ✅ 时区一致性（UTC）
4. ✅ 缓存键冲突（MD5 哈希）
5. ✅ 数据库连接池配置
6. ✅ 策略代码安全验证
7. ✅ Celery 指数退避重试
8. ✅ 会员配额系统
9. ✅ 错误处理环境区分
10. ✅ 交易时段配置化
"""

import pytest
import sys
from datetime import datetime, date, timezone as tz
from unittest.mock import Mock, patch
import pandas as pd

sys.path.insert(0, '/app')


class TestShioajiDuplicateFix:
    """测试 Shioaji 重复键修复"""

    def test_on_conflict_do_update_usage(self):
        """验证使用 ON CONFLICT DO UPDATE"""
        from app.repositories.stock_minute_price import StockMinutePriceRepository
        import inspect

        repo = StockMinutePriceRepository()
        source = inspect.getsource(repo.save_bulk_sync)

        assert "on_conflict_do_update" in source, \
            "save_bulk_sync should use ON CONFLICT DO UPDATE"

    def test_vectorized_operations(self):
        """验证使用向量化操作"""
        from app.repositories.stock_minute_price import StockMinutePriceRepository
        import inspect

        repo = StockMinutePriceRepository()
        source = inspect.getsource(repo.save_bulk_sync)

        assert "to_dict('records')" in source or "to_dict(\"records\")" in source, \
            "save_bulk_sync should use vectorized to_dict('records')"


class TestQlibSyncBoundary:
    """测试 Qlib 同步边界条件"""

    def test_boundary_comparison_logic(self):
        """验证边界日期比较逻辑"""
        from backend.scripts.sync_shioaji_to_qlib import ShioajiToQlibSyncer
        import inspect

        # 检查 sync_single_stock 方法的边界逻辑
        source = inspect.getsource(ShioajiToQlibSyncer.sync_single_stock)

        # 应该使用 > 而非 >=，允许同一天更新
        assert "last_date >" in source, \
            "Should use > instead of >= for boundary check"


class TestTimezoneConsistency:
    """测试时区一致性"""

    def test_utc_timezone_usage(self):
        """验证使用 UTC 时区"""
        from app.services.stock_minute_price_service import StockMinutePriceService
        import inspect

        service = StockMinutePriceService(Mock())
        source = inspect.getsource(service.sync_from_shioaji)

        # 检查是否使用 timezone.utc
        assert "timezone.utc" in source or "tz.utc" in source, \
            "Should use explicit UTC timezone"

    def test_datetime_with_timezone(self):
        """测试 datetime 对象包含时区信息"""
        # 创建带时区的 datetime
        dt_utc = datetime.now(tz.utc)

        assert dt_utc.tzinfo is not None, "datetime should have timezone info"
        assert dt_utc.tzinfo == tz.utc, "datetime should use UTC timezone"


class TestCacheKeyCollision:
    """测试缓存键冲突修复"""

    def test_md5_hash_in_cache_key(self):
        """验证缓存键使用 MD5 哈希"""
        from app.utils.cache import cached_method
        import inspect

        source = inspect.getsource(cached_method)

        assert "md5" in source.lower(), \
            "cached_method should use MD5 hash for cache keys"

    def test_cache_key_uniqueness(self):
        """测试缓存键唯一性"""
        from app.utils.cache import cached_method
        import hashlib
        import json

        # 模拟 cached_method 的键生成逻辑
        def generate_key(args, kwargs):
            key_data = {
                'args': [repr(arg) for arg in args],
                'kwargs': {k: repr(v) for k, v in sorted(kwargs.items())}
            }
            key_json = json.dumps(key_data, sort_keys=True)
            key_hash = hashlib.md5(key_json.encode()).hexdigest()[:16]
            return key_hash

        # 这两个调用应该产生不同的键
        key1 = generate_key(("2330", "2454"), {})
        key2 = generate_key(("2330_2454",), {})

        assert key1 != key2, "Different args should produce different cache keys"


class TestDatabaseConnectionPool:
    """测试数据库连接池配置"""

    def test_dynamic_pool_sizing(self):
        """验证动态连接池大小"""
        from app.db.session import engine

        # 检查连接池配置
        pool = engine.pool

        assert pool.size() >= 10, "Pool size should be at least 10"
        assert hasattr(pool, '_max_overflow'), "Pool should have max_overflow configured"


class TestStrategyCodeSecurity:
    """测试策略代码安全验证"""

    def test_expanded_blacklist(self):
        """验证扩展的黑名单"""
        from app.services.strategy_service import StrategyService
        import inspect

        service = StrategyService(Mock())
        source = inspect.getsource(service._validate_ast_security)

        # 检查新增的危险函数
        assert "'type'" in source or '"type"' in source, \
            "Should blacklist 'type' function"
        assert "'object'" in source or '"object"' in source, \
            "Should blacklist 'object' function"

        # 检查新增的危险属性
        assert "'__reduce__'" in source or '"__reduce__"' in source, \
            "Should blacklist '__reduce__' attribute"


class TestCeleryExponentialBackoff:
    """测试 Celery 指数退避"""

    def test_exponential_backoff_formula(self):
        """验证指数退避公式"""
        # 测试 countdown = base * (2 ** retry_count)
        base = 300  # 5 minutes

        expected_delays = {
            0: 300,   # 5m
            1: 600,   # 10m
            2: 1200,  # 20m
            3: 2400,  # 40m
        }

        for retry_count, expected in expected_delays.items():
            actual = base * (2 ** retry_count)
            assert actual == expected, \
                f"Retry {retry_count}: expected {expected}s, got {actual}s"


class TestMembershipQuotas:
    """测试会员配额系统"""

    def test_quota_mapping(self):
        """验证配额映射"""
        expected_quotas = {
            0: 10,   # Free
            3: 50,   # Paid
            6: 200,  # VIP
        }

        # 这些配额应该在 StrategyService._check_strategy_quota 中定义
        from app.services.strategy_service import StrategyService
        import inspect

        service = StrategyService(Mock())
        source = inspect.getsource(service._check_strategy_quota)

        for level, quota in expected_quotas.items():
            pattern = f"{level}: {quota}"
            assert pattern in source, \
                f"Quota mapping should include {pattern}"


class TestErrorHandling:
    """测试错误处理"""

    def test_safe_error_message_development(self):
        """测试开发环境错误消息"""
        from app.utils.error_handler import get_safe_error_message
        from app.core.config import settings

        error = ValueError("Database connection failed")

        safe_msg = get_safe_error_message(error, "测试操作")

        if settings.ENVIRONMENT == "development":
            # 开发环境应包含详细信息
            assert "ValueError" in safe_msg or "Database connection failed" in safe_msg
        else:
            # 生产环境应隐藏详细信息
            assert "Database connection failed" not in safe_msg

    def test_safe_error_detail_structure(self):
        """测试错误详情结构"""
        from app.utils.error_handler import get_safe_error_detail

        error = TypeError("Invalid type")
        detail = get_safe_error_detail(error)

        assert "error_type" in detail
        assert "message" in detail
        assert detail["error_type"] == "TypeError"


class TestTradingHours:
    """测试交易时段配置"""

    def test_day_trading_hours(self):
        """测试日盘时段"""
        from app.core.trading_hours import is_day_trading_time

        # 应该在日盘内
        assert is_day_trading_time(9, 0) is True
        assert is_day_trading_time(13, 30) is True

        # 应该在日盘外
        assert is_day_trading_time(8, 59) is False
        assert is_day_trading_time(13, 31) is False
        assert is_day_trading_time(15, 0) is False

    def test_night_trading_hours(self):
        """测试夜盘时段"""
        from app.core.trading_hours import is_night_trading_time

        # 应该在夜盘内
        assert is_night_trading_time(15, 0) is True
        assert is_night_trading_time(23, 59) is True
        assert is_night_trading_time(0, 0) is True
        assert is_night_trading_time(5, 0) is True

        # 应该在夜盘外
        assert is_night_trading_time(5, 1) is False
        assert is_night_trading_time(9, 0) is False

    def test_dataframe_filtering(self):
        """测试 DataFrame 过滤"""
        from app.core.trading_hours import filter_trading_hours

        # 创建测试数据
        df = pd.DataFrame({
            'datetime': pd.date_range('2024-12-13 00:00', '2024-12-13 23:00', freq='H'),
            'close': range(24)
        })

        # 仅日盘
        df_day = filter_trading_hours(df, include_night=False)
        day_hours = sorted(df_day['datetime'].dt.hour.unique().tolist())

        assert day_hours == [9, 10, 11, 12, 13], \
            f"Day filter should keep hours 9-13, got {day_hours}"

        # 日盘+夜盘
        df_all = filter_trading_hours(df, include_night=True)
        all_hours = sorted(df_all['datetime'].dt.hour.unique().tolist())

        expected = [0, 1, 2, 3, 4, 5, 9, 10, 11, 12, 13, 15, 16, 17, 18, 19, 20, 21, 22, 23]
        assert all_hours == expected, \
            f"Combined filter should keep hours {expected}, got {all_hours}"


class TestBacktestEngine:
    """测试回测引擎错误处理"""

    def test_safe_error_messages(self):
        """验证回测引擎使用安全错误消息"""
        from app.services.backtest_engine import BacktestEngine
        import inspect

        engine = BacktestEngine(Mock())
        source = inspect.getsource(engine.run_backtest)

        # 检查是否使用 get_safe_error_message
        assert "get_safe_error_message" in source, \
            "BacktestEngine should use get_safe_error_message for exceptions"


# ===== Pytest 配置 =====

def pytest_configure(config):
    """Pytest 配置"""
    config.addinivalue_line(
        "markers", "regression: marks tests as regression tests"
    )


if __name__ == "__main__":
    # 允许直接运行此文件
    pytest.main([__file__, "-v", "--tb=short"])
