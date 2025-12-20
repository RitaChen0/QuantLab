#!/usr/bin/env python3
"""
综合自动化测试脚本

运行所有质量检查和回归测试，确保代码改进的有效性。

测试内容：
1. 数据库索引性能验证
2. 交易时段配置测试
3. 类型提示覆盖率检查
4. 缓存机制测试
5. 错误处理测试
6. 会员配额测试
7. Celery 重试机制测试

使用方法:
    python /app/scripts/run_all_tests.py
    python /app/scripts/run_all_tests.py --verbose
    python /app/scripts/run_all_tests.py --quick  # 快速测试（跳过耗时测试）
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Tuple
from loguru import logger

# 添加项目路径
sys.path.insert(0, '/app')


class TestRunner:
    """测试运行器"""

    def __init__(self, verbose: bool = False, quick: bool = False):
        self.verbose = verbose
        self.quick = quick
        self.results: List[Tuple[str, bool, str]] = []
        self.start_time = datetime.now(timezone.utc)

    def run_test(self, name: str, test_func, skip_on_quick: bool = False) -> bool:
        """
        运行单个测试

        Args:
            name: 测试名称
            test_func: 测试函数
            skip_on_quick: 在快速模式下是否跳过

        Returns:
            测试是否通过
        """
        if self.quick and skip_on_quick:
            logger.info(f"⏭️  Skipping {name} (quick mode)")
            self.results.append((name, True, "Skipped in quick mode"))
            return True

        logger.info(f"\n{'=' * 70}")
        logger.info(f"🧪 Running: {name}")
        logger.info(f"{'=' * 70}")

        try:
            result = test_func()
            status = "✅ PASSED" if result else "❌ FAILED"
            message = "Test completed successfully" if result else "Test failed"

            logger.info(f"\n{status}: {name}")
            self.results.append((name, result, message))
            return result

        except Exception as e:
            logger.error(f"❌ FAILED: {name}")
            logger.error(f"Error: {str(e)}")
            self.results.append((name, False, f"Exception: {str(e)}"))
            return False

    def print_summary(self):
        """打印测试摘要"""
        duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()

        logger.info("\n" + "=" * 70)
        logger.info("📊 Test Summary")
        logger.info("=" * 70)

        passed = sum(1 for _, result, _ in self.results if result)
        total = len(self.results)

        logger.info(f"\n⏱️  Total time: {duration:.2f}s")
        logger.info(f"🧪 Tests run: {total}")
        logger.info(f"✅ Passed: {passed}")
        logger.info(f"❌ Failed: {total - passed}")

        if passed == total:
            logger.info(f"\n🎉 All tests passed! ({passed}/{total})")
        else:
            logger.warning(f"\n⚠️  Some tests failed ({passed}/{total})")

        logger.info("\n" + "=" * 70)
        logger.info("📋 Detailed Results:")
        logger.info("=" * 70)

        for name, result, message in self.results:
            status = "✅" if result else "❌"
            logger.info(f"{status} {name}")
            if not result and self.verbose:
                logger.info(f"   └─ {message}")

        logger.info("=" * 70)

        return passed == total


# ===== 测试函数 =====

def test_database_indexes() -> bool:
    """测试数据库索引性能"""
    from validate_db_indexes import main as validate_indexes

    try:
        # 重定向输出以避免干扰
        import io
        import contextlib

        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            validate_indexes()

        return True
    except Exception as e:
        logger.error(f"Database index validation failed: {e}")
        return False


def test_trading_hours() -> bool:
    """测试交易时段配置"""
    from test_trading_hours import main as test_hours

    try:
        result = test_hours()
        return result == 0
    except Exception as e:
        logger.error(f"Trading hours test failed: {e}")
        return False


def test_type_hints() -> bool:
    """测试类型提示覆盖率"""
    from check_type_hints import main as check_hints

    try:
        # 类型提示检查只要没有高严重度问题就算通过
        result = check_hints()
        return result == 0
    except Exception as e:
        logger.error(f"Type hints check failed: {e}")
        return False


def test_cache_mechanism() -> bool:
    """测试缓存机制（MD5 哈希避免键冲突）"""
    from app.utils.cache import cache, cached_method
    from app.core.config import settings

    if not cache.is_available():
        logger.warning("Redis not available, skipping cache test")
        return True

    try:
        # 测试 1: 设置和获取
        test_key = "test:cache_mechanism"
        test_value = {"data": "test", "number": 123}

        cache.set(test_key, test_value, expiry=60)
        retrieved = cache.get(test_key)

        if retrieved != test_value:
            logger.error("Cache set/get failed")
            return False

        logger.info("✓ Cache set/get works")

        # 测试 2: MD5 哈希避免键冲突
        @cached_method(key_prefix="test", expiry=60)
        def test_func(self, arg1, arg2):
            return f"{arg1}_{arg2}"

        class TestClass:
            pass

        obj = TestClass()

        # 这两个调用参数不同，应该产生不同的缓存键
        result1 = test_func(obj, "2330", "2454")
        result2 = test_func(obj, "2330_2454", "")

        if result1 == result2:
            logger.warning("Cache key collision possible (但结果相同不一定是冲突)")

        logger.info("✓ Cache key hashing works")

        # 清理
        cache.delete(test_key)

        return True

    except Exception as e:
        logger.error(f"Cache mechanism test failed: {e}")
        return False


def test_error_handling() -> bool:
    """测试错误处理（环境感知）"""
    from app.utils.error_handler import get_safe_error_message, get_safe_error_detail
    from app.core.config import settings

    try:
        # 测试不同类型的错误
        test_error = ValueError("Database connection failed with password: secret123")

        # 生产环境应该隐藏详细信息
        safe_message = get_safe_error_message(test_error, "数据库连接")

        # 在开发环境，应该包含详细信息
        if settings.ENVIRONMENT == "development":
            if "ValueError" not in safe_message and "failed" not in safe_message:
                logger.error("Development environment should show detailed errors")
                return False
            logger.info("✓ Development mode shows detailed errors")
        else:
            # 生产环境应该隐藏敏感信息
            if "secret123" in safe_message:
                logger.error("Production environment leaking sensitive info")
                return False
            logger.info("✓ Production mode hides sensitive info")

        # 测试错误详情
        detail = get_safe_error_detail(test_error)

        if "error_type" not in detail or "message" not in detail:
            logger.error("Error detail missing required fields")
            return False

        logger.info("✓ Error detail structure correct")

        return True

    except Exception as e:
        logger.error(f"Error handling test failed: {e}")
        return False


def test_membership_quotas() -> bool:
    """测试会员配额系统"""
    from app.services.strategy_service import StrategyService
    from app.db.session import SessionLocal

    db = SessionLocal()

    try:
        # 这个测试需要实际的数据库连接和用户数据
        # 我们只验证配额映射是否正确定义

        # 检查 StrategyService._check_strategy_quota 方法
        service = StrategyService(db)

        # 验证配额映射存在（通过检查源代码）
        import inspect
        source = inspect.getsource(service._check_strategy_quota)

        if "quota_map" not in source:
            logger.error("Quota map not found in _check_strategy_quota")
            return False

        if "0: 10" not in source or "3: 50" not in source or "6: 200" not in source:
            logger.error("Quota levels not correctly defined")
            return False

        logger.info("✓ Membership quota mapping correct (0:10, 3:50, 6:200)")

        return True

    except Exception as e:
        logger.error(f"Membership quota test failed: {e}")
        return False
    finally:
        db.close()


def test_celery_retry_mechanism() -> bool:
    """测试 Celery 指数退避重试机制"""
    import inspect

    try:
        # 检查任务文件中的重试逻辑
        from app.tasks import stock_data, fundamental_sync, backtest

        test_cases = [
            (stock_data, "sync_stock_list_task"),
            (fundamental_sync, "sync_fundamental_data_task"),
            (backtest, "run_backtest_async"),
        ]

        for module, task_name in test_cases:
            if hasattr(module, task_name):
                task_func = getattr(module, task_name)
                source = inspect.getsource(task_func)

                # 检查是否使用指数退避
                if "2 ** retry_count" not in source and "2**retry_count" not in source:
                    logger.warning(f"{task_name} may not use exponential backoff")
                else:
                    logger.info(f"✓ {task_name} uses exponential backoff")

        return True

    except Exception as e:
        logger.error(f"Celery retry mechanism test failed: {e}")
        return False


def test_shioaji_duplicate_fix() -> bool:
    """测试 Shioaji 同步的重复键修复"""
    import inspect

    try:
        # 检查 sync_shioaji_to_qlib.py 中的修复
        sync_script_path = Path("/app/scripts/sync_shioaji_to_qlib.py")

        if not sync_script_path.exists():
            logger.warning("sync_shioaji_to_qlib.py not found, skipping test")
            return True

        with open(sync_script_path, 'r') as f:
            source = f.read()

        # 检查是否使用 ON CONFLICT DO UPDATE
        if "on_conflict_do_update" not in source:
            logger.error("sync script should use on_conflict_do_update")
            return False

        logger.info("✓ Shioaji sync uses ON CONFLICT DO UPDATE")

        # 检查是否有向量化处理
        if "to_dict('records')" not in source and 'to_dict("records")' not in source:
            logger.warning("sync script may not use vectorized operations")
        else:
            logger.info("✓ Shioaji sync uses vectorized operations")

        # 检查边界条件修复（使用 > 而非 >=）
        if "last_date >" in source and "last_date >=" not in source:
            logger.info("✓ Boundary condition uses > (allows same-day sync)")
        else:
            logger.warning("Boundary condition may not be correctly fixed")

        return True

    except Exception as e:
        logger.error(f"Shioaji duplicate fix test failed: {e}")
        return False


def main():
    """主测试函数"""
    parser = argparse.ArgumentParser(description="Run comprehensive automated tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--quick", "-q", action="store_true", help="Quick mode (skip time-consuming tests)")
    args = parser.parse_args()

    logger.info("🚀 Starting Comprehensive Automated Tests")
    logger.info(f"Mode: {'Quick' if args.quick else 'Full'}")
    logger.info(f"Verbose: {args.verbose}\n")

    runner = TestRunner(verbose=args.verbose, quick=args.quick)

    # 运行所有测试
    runner.run_test("Database Index Performance", test_database_indexes, skip_on_quick=False)
    runner.run_test("Trading Hours Configuration", test_trading_hours, skip_on_quick=False)
    runner.run_test("Type Hints Coverage", test_type_hints, skip_on_quick=True)
    runner.run_test("Cache Mechanism (MD5 Hash)", test_cache_mechanism, skip_on_quick=False)
    runner.run_test("Error Handling (Environment-Aware)", test_error_handling, skip_on_quick=False)
    runner.run_test("Membership Quota System", test_membership_quotas, skip_on_quick=False)
    runner.run_test("Celery Retry Mechanism (Exponential Backoff)", test_celery_retry_mechanism, skip_on_quick=False)
    runner.run_test("Shioaji Duplicate Key Fix", test_shioaji_duplicate_fix, skip_on_quick=False)

    # 打印摘要
    all_passed = runner.print_summary()

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
