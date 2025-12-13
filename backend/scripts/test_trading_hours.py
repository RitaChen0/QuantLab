#!/usr/bin/env python3
"""
交易时段配置测试脚本

验证日盘和夜盘时间过滤是否正确。
"""

import sys
sys.path.insert(0, '/app')

from app.core.trading_hours import (
    TradingHoursConfig,
    is_day_trading_time,
    is_night_trading_time,
    is_trading_time
)
from loguru import logger


def test_day_trading_hours():
    """测试日盘交易时段"""
    logger.info("=" * 60)
    logger.info("📊 Testing Day Trading Hours")
    logger.info("=" * 60)

    test_cases = [
        # (hour, minute, expected_result, description)
        (8, 59, False, "开盘前"),
        (9, 0, True, "开盘时刻"),
        (9, 30, True, "上午盘中"),
        (12, 0, True, "上午收盘"),
        (12, 30, False, "午休时间"),
        (13, 0, True, "下午开盘"),
        (13, 30, True, "下午收盘"),
        (13, 31, False, "收盘后"),
        (15, 0, False, "盘后"),
    ]

    passed = 0
    failed = 0

    for hour, minute, expected, desc in test_cases:
        result = is_day_trading_time(hour, minute)
        status = "✅" if result == expected else "❌"

        if result == expected:
            passed += 1
        else:
            failed += 1

        logger.info(
            f"  {status} {hour:02d}:{minute:02d} - {desc}: "
            f"Expected={expected}, Got={result}"
        )

    logger.info(f"\n  Summary: {passed} passed, {failed} failed\n")
    return failed == 0


def test_night_trading_hours():
    """测试夜盘交易时段"""
    logger.info("=" * 60)
    logger.info("📊 Testing Night Trading Hours")
    logger.info("=" * 60)

    test_cases = [
        (14, 59, False, "夜盘开盘前"),
        (15, 0, True, "夜盘开盘"),
        (18, 0, True, "夜盘中段"),
        (23, 59, True, "夜盘第一阶段结束"),
        (0, 0, True, "夜盘第二阶段开始"),
        (3, 0, True, "凌晨时段"),
        (5, 0, True, "夜盘收盘"),
        (5, 1, False, "夜盘结束后"),
        (9, 0, False, "日盘时间（不算夜盘）"),
    ]

    passed = 0
    failed = 0

    for hour, minute, expected, desc in test_cases:
        result = is_night_trading_time(hour, minute)
        status = "✅" if result == expected else "❌"

        if result == expected:
            passed += 1
        else:
            failed += 1

        logger.info(
            f"  {status} {hour:02d}:{minute:02d} - {desc}: "
            f"Expected={expected}, Got={result}"
        )

    logger.info(f"\n  Summary: {passed} passed, {failed} failed\n")
    return failed == 0


def test_combined_trading_hours():
    """测试日盘+夜盘组合"""
    logger.info("=" * 60)
    logger.info("📊 Testing Combined Trading Hours (Day + Night)")
    logger.info("=" * 60)

    test_cases = [
        (9, 0, True, "日盘开盘"),
        (13, 30, True, "日盘收盘"),
        (15, 0, True, "夜盘开盘"),
        (5, 0, True, "夜盘收盘"),
        (5, 30, False, "非交易时段"),
        (8, 0, False, "日盘开盘前"),
    ]

    passed = 0
    failed = 0

    for hour, minute, expected, desc in test_cases:
        result = is_trading_time(hour, minute, include_night=True)
        status = "✅" if result == expected else "❌"

        if result == expected:
            passed += 1
        else:
            failed += 1

        logger.info(
            f"  {status} {hour:02d}:{minute:02d} - {desc}: "
            f"Expected={expected}, Got={result}"
        )

    logger.info(f"\n  Summary: {passed} passed, {failed} failed\n")
    return failed == 0


def test_dataframe_filtering():
    """测试 DataFrame 过滤功能"""
    logger.info("=" * 60)
    logger.info("📊 Testing DataFrame Filtering")
    logger.info("=" * 60)

    import pandas as pd

    # 创建测试数据（00:00-23:59 每小时一条）
    df = pd.DataFrame({
        'datetime': pd.date_range('2024-12-13 00:00', '2024-12-13 23:00', freq='H'),
        'close': range(24)
    })

    logger.info(f"  Original DataFrame: {len(df)} rows (24 hours)")

    # 仅日盘过滤
    df_day = TradingHoursConfig.filter_dataframe(df, include_night=False)
    logger.info(f"  After day filter: {len(df_day)} rows")
    logger.info(f"    Hours: {sorted(df_day['datetime'].dt.hour.unique().tolist())}")

    expected_day_hours = [9, 10, 11, 12, 13]
    actual_day_hours = sorted(df_day['datetime'].dt.hour.unique().tolist())

    if actual_day_hours == expected_day_hours:
        logger.info(f"    ✅ Day filtering correct")
    else:
        logger.error(f"    ❌ Expected {expected_day_hours}, got {actual_day_hours}")
        return False

    # 日盘+夜盘过滤
    df_all = TradingHoursConfig.filter_dataframe(df, include_night=True)
    logger.info(f"\n  After day+night filter: {len(df_all)} rows")
    logger.info(f"    Hours: {sorted(df_all['datetime'].dt.hour.unique().tolist())}")

    # 期望：日盘 9-13 + 夜盘 15-23, 0-5
    expected_all_hours = [0, 1, 2, 3, 4, 5, 9, 10, 11, 12, 13, 15, 16, 17, 18, 19, 20, 21, 22, 23]
    actual_all_hours = sorted(df_all['datetime'].dt.hour.unique().tolist())

    if actual_all_hours == expected_all_hours:
        logger.info(f"    ✅ Combined filtering correct")
    else:
        logger.error(f"    ❌ Expected {expected_all_hours}, got {actual_all_hours}")
        return False

    logger.info("")
    return True


def main():
    """主测试函数"""
    logger.info("🚀 Starting Trading Hours Configuration Tests\n")

    results = []
    results.append(("Day Trading Hours", test_day_trading_hours()))
    results.append(("Night Trading Hours", test_night_trading_hours()))
    results.append(("Combined Trading Hours", test_combined_trading_hours()))
    results.append(("DataFrame Filtering", test_dataframe_filtering()))

    logger.info("=" * 60)
    logger.info("📊 Test Results Summary")
    logger.info("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"  {status}: {name}")
        if not passed:
            all_passed = False

    logger.info("=" * 60)

    if all_passed:
        logger.info("✅ All tests passed!")
        return 0
    else:
        logger.error("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    exit(main())
