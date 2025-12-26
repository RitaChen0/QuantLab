#!/usr/bin/env python3
"""
簡化的價格驗證測試（不依賴完整 ORM）

只測試 PriceValidator 核心邏輯和與 CHECK 約束的一致性。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from decimal import Decimal
from app.utils.price_validator import PriceValidator
from loguru import logger


def test_validation_rules():
    """測試所有價格驗證規則"""
    logger.info("\n" + "=" * 60)
    logger.info("🧪 價格驗證邏輯測試（與 CHECK 約束一致性驗證）")
    logger.info("=" * 60)

    tests = [
        # 有效數據
        {
            "name": "✅ 正常價格數據",
            "data": {"open": 100, "high": 105, "low": 99, "close": 102},
            "expected": True,
            "description": "所有價格合理且在範圍內"
        },
        {
            "name": "✅ close = low（邊界情況）",
            "data": {"open": 100, "high": 105, "low": 99, "close": 99},
            "expected": True,
            "description": "收盤價等於最低價"
        },
        {
            "name": "✅ close = high（邊界情況）",
            "data": {"open": 100, "high": 105, "low": 99, "close": 105},
            "expected": True,
            "description": "收盤價等於最高價"
        },
        {
            "name": "✅ high = low（無波動）",
            "data": {"open": 100, "high": 100, "low": 100, "close": 100},
            "expected": True,
            "description": "價格無波動（停牌或限價）"
        },
        {
            "name": "✅ 全零佔位記錄",
            "data": {"open": 0, "high": 0, "low": 0, "close": 0},
            "expected": True,
            "description": "允許全零的佔位記錄（特殊情況）"
        },

        # 無效數據 - 違反規則 1: high >= low
        {
            "name": "❌ high < low",
            "data": {"open": 100, "high": 95, "low": 105, "close": 100},
            "expected": False,
            "description": "違反 chk_stock_prices_high_low 約束"
        },

        # 無效數據 - 違反規則 2: low <= close <= high
        {
            "name": "❌ close < low",
            "data": {"open": 100, "high": 105, "low": 99, "close": 98},
            "expected": False,
            "description": "違反 chk_stock_prices_close_range 約束"
        },
        {
            "name": "❌ close > high",
            "data": {"open": 100, "high": 105, "low": 99, "close": 106},
            "expected": False,
            "description": "違反 chk_stock_prices_close_range 約束"
        },

        # 無效數據 - 違反規則 3: 價格必須 > 0
        {
            "name": "❌ open = 0（但其他非零）",
            "data": {"open": 0, "high": 105, "low": 99, "close": 102},
            "expected": False,
            "description": "違反 chk_stock_prices_positive 約束"
        },
        {
            "name": "❌ high = 0（但其他非零）",
            "data": {"open": 100, "high": 0, "low": 99, "close": 102},
            "expected": False,
            "description": "違反 chk_stock_prices_positive 約束"
        },
        {
            "name": "❌ low = 0（但其他非零）",
            "data": {"open": 100, "high": 105, "low": 0, "close": 102},
            "expected": False,
            "description": "違反 chk_stock_prices_positive 約束"
        },
        {
            "name": "❌ close = 0（但其他非零）",
            "data": {"open": 100, "high": 105, "low": 99, "close": 0},
            "expected": False,
            "description": "違反 chk_stock_prices_positive 約束"
        },
        {
            "name": "❌ 負數價格",
            "data": {"open": 100, "high": 105, "low": -1, "close": 102},
            "expected": False,
            "description": "負數價格不允許"
        },

        # 複合無效情況
        {
            "name": "❌ 多重錯誤（high<low 且 close<low）",
            "data": {"open": 100, "high": 95, "low": 105, "close": 90},
            "expected": False,
            "description": "多個約束同時違反"
        },
    ]

    passed = 0
    failed = 0
    total = len(tests)

    for i, test in enumerate(tests, 1):
        data = test["data"]
        is_valid, error_msg = PriceValidator.validate_price_data(
            open=Decimal(str(data["open"])),
            high=Decimal(str(data["high"])),
            low=Decimal(str(data["low"])),
            close=Decimal(str(data["close"])),
            stock_id="TEST",
            date="2025-01-01"
        )

        # 檢查結果
        if is_valid == test["expected"]:
            logger.info(f"✅ 測試 {i}/{total}: {test['name']}")
            logger.info(f"   {test['description']}")
            passed += 1
        else:
            logger.error(f"❌ 測試 {i}/{total}: {test['name']} - 失敗")
            logger.error(f"   {test['description']}")
            logger.error(f"   預期: {'有效' if test['expected'] else '無效'}")
            logger.error(f"   實際: {'有效' if is_valid else '無效'}")
            if error_msg:
                logger.error(f"   錯誤: {error_msg}")
            failed += 1

        # 在有效和無效測試之間添加分隔
        if i in [5, 6]:
            logger.info("")

    # 總結
    logger.info("\n" + "=" * 60)
    logger.info("📊 測試結果總結")
    logger.info("=" * 60)
    logger.info(f"總測試數: {total}")
    logger.info(f"通過: {passed} ✅")
    logger.info(f"失敗: {failed} ❌")
    logger.info(f"成功率: {passed/total*100:.1f}%")

    if failed == 0:
        logger.info("\n🎉 所有測試通過！")
        logger.info("✅ 應用層驗證邏輯與資料庫 CHECK 約束完全一致")
        logger.info("✅ 雙層防護機制已就緒")
        return True
    else:
        logger.error(f"\n⚠️  {failed} 個測試失敗")
        return False


def test_error_messages():
    """測試錯誤訊息的清晰度"""
    logger.info("\n" + "=" * 60)
    logger.info("📝 錯誤訊息測試")
    logger.info("=" * 60)

    test_cases = [
        {
            "name": "high < low 的錯誤訊息",
            "data": {"open": 100, "high": 95, "low": 105, "close": 100},
            "expected_keyword": "最高價"
        },
        {
            "name": "close 超出範圍的錯誤訊息",
            "data": {"open": 100, "high": 105, "low": 99, "close": 110},
            "expected_keyword": "範圍內"
        },
        {
            "name": "零價格的錯誤訊息",
            "data": {"open": 0, "high": 105, "low": 99, "close": 102},
            "expected_keyword": "必須"
        },
    ]

    all_clear = True
    for test in test_cases:
        data = test["data"]
        is_valid, error_msg = PriceValidator.validate_price_data(
            open=Decimal(str(data["open"])),
            high=Decimal(str(data["high"])),
            low=Decimal(str(data["low"])),
            close=Decimal(str(data["close"])),
            stock_id="2330",
            date="2025-01-15"
        )

        if error_msg and test["expected_keyword"] in error_msg:
            logger.info(f"✅ {test['name']}")
            logger.info(f"   訊息: {error_msg}")
        else:
            logger.error(f"❌ {test['name']}")
            logger.error(f"   訊息: {error_msg}")
            logger.error(f"   缺少關鍵字: {test['expected_keyword']}")
            all_clear = False

    logger.info("\n" + "-" * 60)
    if all_clear:
        logger.info("✅ 所有錯誤訊息清晰易懂")
    else:
        logger.error("⚠️  部分錯誤訊息不清晰")

    return all_clear


def main():
    """執行所有測試"""
    logger.info("\n" + "=" * 70)
    logger.info("🔍 價格數據驗證邏輯完整性測試")
    logger.info("=" * 70)
    logger.info("\n目的：驗證應用層驗證邏輯與資料庫 CHECK 約束的一致性")
    logger.info("確保無效數據在源頭被阻止，形成雙層防護機制\n")

    # 執行測試
    test1_passed = test_validation_rules()
    test2_passed = test_error_messages()

    # 最終總結
    logger.info("\n" + "=" * 70)
    logger.info("🏁 最終結論")
    logger.info("=" * 70)

    if test1_passed and test2_passed:
        logger.info("✅ 價格驗證邏輯完整且正確")
        logger.info("✅ 應用層與資料庫層驗證邏輯一致")
        logger.info("✅ 錯誤訊息清晰易懂")
        logger.info("\n🎯 P2-3 任務完成：數據同步驗證邏輯已實施")
        logger.info("\n防護機制：")
        logger.info("  1️⃣  應用層：PriceValidator（源頭阻止無效數據）")
        logger.info("  2️⃣  資料庫層：CHECK 約束（最後一道防線）")
        logger.info("=" * 70)
        return True
    else:
        logger.error("⚠️  部分測試失敗，需要修復")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
