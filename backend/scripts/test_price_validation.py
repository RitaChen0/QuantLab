#!/usr/bin/env python3
"""
測試價格驗證邏輯

驗證應用層價格驗證能夠正確阻止無效數據插入資料庫。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from decimal import Decimal
from datetime import date
from sqlalchemy import text
from app.db.session import SessionLocal
from app.repositories.stock_price import StockPriceRepository
from app.schemas.stock_price import StockPriceCreate
from app.utils.price_validator import PriceValidator, PriceValidationError
from loguru import logger


def test_price_validator():
    """測試 1: PriceValidator 單元測試"""
    logger.info("\n" + "=" * 60)
    logger.info("測試 1: PriceValidator 單元測試")
    logger.info("=" * 60)

    tests = [
        {
            "name": "1.1 有效的價格數據",
            "data": {
                "open": Decimal("100"), "high": Decimal("105"),
                "low": Decimal("99"), "close": Decimal("102")
            },
            "expected": True
        },
        {
            "name": "1.2 high < low (應拒絕)",
            "data": {
                "open": Decimal("100"), "high": Decimal("95"),
                "low": Decimal("105"), "close": Decimal("100")
            },
            "expected": False
        },
        {
            "name": "1.3 close < low (應拒絕)",
            "data": {
                "open": Decimal("100"), "high": Decimal("105"),
                "low": Decimal("99"), "close": Decimal("98")
            },
            "expected": False
        },
        {
            "name": "1.4 close > high (應拒絕)",
            "data": {
                "open": Decimal("100"), "high": Decimal("105"),
                "low": Decimal("99"), "close": Decimal("106")
            },
            "expected": False
        },
        {
            "name": "1.5 零價格 (應拒絕)",
            "data": {
                "open": Decimal("0"), "high": Decimal("105"),
                "low": Decimal("99"), "close": Decimal("102")
            },
            "expected": False
        },
        {
            "name": "1.6 負價格 (應拒絕)",
            "data": {
                "open": Decimal("100"), "high": Decimal("105"),
                "low": Decimal("-1"), "close": Decimal("102")
            },
            "expected": False
        },
        {
            "name": "1.7 全零佔位記錄 (應允許)",
            "data": {
                "open": Decimal("0"), "high": Decimal("0"),
                "low": Decimal("0"), "close": Decimal("0")
            },
            "expected": True
        },
    ]

    passed = 0
    failed = 0

    for test in tests:
        is_valid, error_msg = PriceValidator.validate_price_data(
            open=test["data"]["open"],
            high=test["data"]["high"],
            low=test["data"]["low"],
            close=test["data"]["close"],
            stock_id="TEST",
            date="2025-01-01"
        )

        if is_valid == test["expected"]:
            logger.info(f"✅ {test['name']} - 通過")
            passed += 1
        else:
            logger.error(f"❌ {test['name']} - 失敗")
            logger.error(f"   預期: {test['expected']}, 實際: {is_valid}")
            if error_msg:
                logger.error(f"   錯誤: {error_msg}")
            failed += 1

    logger.info(f"\n測試 1 結果: {passed}/{len(tests)} 通過")
    return failed == 0


def test_repository_validation():
    """測試 2: Repository 層驗證"""
    logger.info("\n" + "=" * 60)
    logger.info("測試 2: Repository 層驗證")
    logger.info("=" * 60)

    db = SessionLocal()
    try:
        # 清理測試數據
        db.execute(text("DELETE FROM stock_prices WHERE stock_id = 'TESTVAL'"))
        db.commit()

        # 測試 2.1: 有效數據應該成功插入
        logger.info("\n測試 2.1: 插入有效數據")
        try:
            valid_price = StockPriceCreate(
                stock_id="TESTVAL",
                date=date(2025, 1, 1),
                open=Decimal("100.0"),
                high=Decimal("105.0"),
                low=Decimal("99.0"),
                close=Decimal("102.0"),
                volume=1000
            )
            StockPriceRepository.create(db, valid_price)
            logger.info("✅ 有效數據成功插入")
            test_2_1_passed = True
        except Exception as e:
            logger.error(f"❌ 有效數據插入失敗: {e}")
            test_2_1_passed = False

        # 測試 2.2: 無效數據應該被拒絕
        logger.info("\n測試 2.2: 嘗試插入無效數據 (high < low)")
        try:
            invalid_price = StockPriceCreate(
                stock_id="TESTVAL",
                date=date(2025, 1, 2),
                open=Decimal("100.0"),
                high=Decimal("95.0"),  # high < low
                low=Decimal("105.0"),
                close=Decimal("100.0"),
                volume=1000
            )
            StockPriceRepository.create(db, invalid_price)
            logger.error("❌ 無效數據未被拒絕（應該拋出異常）")
            test_2_2_passed = False
        except PriceValidationError as e:
            logger.info(f"✅ 無效數據被正確拒絕: {e}")
            test_2_2_passed = True
        except Exception as e:
            logger.error(f"❌ 拋出了錯誤的異常類型: {type(e).__name__} - {e}")
            test_2_2_passed = False

        # 測試 2.3: skip_validation 參數
        logger.info("\n測試 2.3: skip_validation 參數（跳過驗證）")
        try:
            # 使用 skip_validation=True 應該允許無效數據
            invalid_price_skip = StockPriceCreate(
                stock_id="TESTVAL",
                date=date(2025, 1, 3),
                open=Decimal("0"),  # 無效：零價格
                high=Decimal("0"),
                low=Decimal("0"),
                close=Decimal("0"),
                volume=0
            )
            StockPriceRepository.create(db, invalid_price_skip, skip_validation=True)
            logger.info("✅ skip_validation=True 允許插入（但不建議生產環境使用）")
            test_2_3_passed = True

            # 清理這筆測試數據
            db.execute(text("DELETE FROM stock_prices WHERE stock_id = 'TESTVAL' AND date = '2025-01-03'"))
            db.commit()
        except Exception as e:
            logger.error(f"❌ skip_validation 測試失敗: {e}")
            test_2_3_passed = False

        # 清理測試數據
        db.execute(text("DELETE FROM stock_prices WHERE stock_id = 'TESTVAL'"))
        db.commit()

        all_passed = test_2_1_passed and test_2_2_passed and test_2_3_passed
        logger.info(f"\n測試 2 結果: {'通過' if all_passed else '失敗'}")
        return all_passed

    except Exception as e:
        logger.error(f"❌ 測試 2 執行失敗: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def test_bulk_validation():
    """測試 3: 批量插入驗證"""
    logger.info("\n" + "=" * 60)
    logger.info("測試 3: 批量插入驗證")
    logger.info("=" * 60)

    db = SessionLocal()
    try:
        # 清理測試數據
        db.execute(text("DELETE FROM stock_prices WHERE stock_id = 'TESTBULK'"))
        db.commit()

        # 準備混合數據（有效 + 無效）
        prices = [
            # 有效數據
            StockPriceCreate(
                stock_id="TESTBULK", date=date(2025, 1, 1),
                open=Decimal("100"), high=Decimal("105"),
                low=Decimal("99"), close=Decimal("102"), volume=1000
            ),
            StockPriceCreate(
                stock_id="TESTBULK", date=date(2025, 1, 2),
                open=Decimal("102"), high=Decimal("107"),
                low=Decimal("101"), close=Decimal("105"), volume=1200
            ),
            # 無效數據（high < low）
            StockPriceCreate(
                stock_id="TESTBULK", date=date(2025, 1, 3),
                open=Decimal("100"), high=Decimal("95"),
                low=Decimal("105"), close=Decimal("100"), volume=1000
            ),
            # 無效數據（零價格）
            StockPriceCreate(
                stock_id="TESTBULK", date=date(2025, 1, 4),
                open=Decimal("0"), high=Decimal("105"),
                low=Decimal("99"), close=Decimal("102"), volume=1000
            ),
            # 有效數據
            StockPriceCreate(
                stock_id="TESTBULK", date=date(2025, 1, 5),
                open=Decimal("105"), high=Decimal("110"),
                low=Decimal("104"), close=Decimal("108"), volume=1500
            ),
        ]

        logger.info(f"準備批量插入 {len(prices)} 筆記錄（3 有效 + 2 無效）")

        result = StockPriceRepository.create_bulk(db, prices)

        logger.info(f"\n批量插入結果:")
        logger.info(f"  總計: {result['total']}")
        logger.info(f"  成功: {result['created']}")
        logger.info(f"  跳過: {result['skipped']}")

        # 驗證結果
        if result['created'] == 3 and result['skipped'] == 2:
            logger.info("✅ 批量驗證正確：只插入了 3 筆有效記錄，拒絕了 2 筆無效記錄")

            # 檢查資料庫
            count = db.execute(
                text("SELECT COUNT(*) FROM stock_prices WHERE stock_id = 'TESTBULK'")
            ).scalar()

            if count == 3:
                logger.info(f"✅ 資料庫驗證通過：確實只有 {count} 筆記錄")
                test_passed = True
            else:
                logger.error(f"❌ 資料庫驗證失敗：預期 3 筆，實際 {count} 筆")
                test_passed = False
        else:
            logger.error(
                f"❌ 批量驗證失敗：預期 3 成功/2 跳過，"
                f"實際 {result['created']} 成功/{result['skipped']} 跳過"
            )
            test_passed = False

        # 清理測試數據
        db.execute(text("DELETE FROM stock_prices WHERE stock_id = 'TESTBULK'"))
        db.commit()

        logger.info(f"\n測試 3 結果: {'通過' if test_passed else '失敗'}")
        return test_passed

    except Exception as e:
        logger.error(f"❌ 測試 3 執行失敗: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def main():
    """執行所有測試"""
    logger.info("\n" + "=" * 60)
    logger.info("🧪 開始價格驗證邏輯測試")
    logger.info("=" * 60 + "\n")

    results = []

    # 執行測試
    results.append(("PriceValidator 單元測試", test_price_validator()))
    results.append(("Repository 層驗證", test_repository_validation()))
    results.append(("批量插入驗證", test_bulk_validation()))

    # 總結
    logger.info("\n" + "=" * 60)
    logger.info("📊 測試結果總結")
    logger.info("=" * 60)

    for name, passed in results:
        status = "✅ 通過" if passed else "❌ 失敗"
        logger.info(f"{status} - {name}")

    all_passed = all(passed for _, passed in results)

    logger.info("\n" + "=" * 60)
    if all_passed:
        logger.info("🎉 所有測試通過！價格驗證邏輯工作正常。")
        logger.info("=" * 60)
        return True
    else:
        failed_count = sum(1 for _, passed in results if not passed)
        logger.error(f"⚠️  {failed_count} 個測試失敗")
        logger.error("=" * 60)
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
