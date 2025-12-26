"""
測試 CHECK 約束

驗證 stock_prices 表的 CHECK 約束能否正確阻止無效數據
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.db.session import SessionLocal
from loguru import logger
from datetime import date


def test_high_low_constraint():
    """測試 1: high >= low 約束"""
    logger.info("=" * 60)
    logger.info("🔒 測試 1: high >= low 約束")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        test_stock_id = "2330"
        test_date = date.today()

        # 清理可能存在的測試數據
        db.execute(text(f"""
        DELETE FROM stock_prices
        WHERE stock_id = '{test_stock_id}' AND date = '{test_date}'
        """))
        db.commit()

        # 測試 1.1: 嘗試插入 high < low 的記錄（應該失敗）
        logger.info("測試 1.1: 嘗試插入 high < low 的記錄（應該失敗）...")
        try:
            db.execute(text(f"""
            INSERT INTO stock_prices (stock_id, date, open, high, low, close, volume)
            VALUES ('{test_stock_id}', '{test_date}', 100, 95, 105, 100, 1000)
            """))
            db.commit()
            logger.error("   ❌ 錯誤：high < low 的記錄被插入（約束未生效）")
            return False
        except IntegrityError as e:
            db.rollback()
            if "chk_stock_prices_high_low" in str(e) or "chk_stock_prices_close_range" in str(e):
                logger.info("   ✅ 正確：high < low 的記錄被約束阻擋")
            else:
                logger.error(f"   ❌ 錯誤：被其他約束阻擋: {e}")
                return False

        # 測試 1.2: 插入 high = low 的記錄（應該成功）
        logger.info("測試 1.2: 插入 high = low 的記錄（應該成功）...")
        db.execute(text(f"""
        INSERT INTO stock_prices (stock_id, date, open, high, low, close, volume)
        VALUES ('{test_stock_id}', '{test_date}', 100, 100, 100, 100, 1000)
        """))
        db.commit()
        logger.info("   ✅ high = low 的記錄成功插入")

        # 清理測試數據
        db.execute(text(f"""
        DELETE FROM stock_prices
        WHERE stock_id = '{test_stock_id}' AND date = '{test_date}'
        """))
        db.commit()

        logger.info("✅ 測試 1 通過：high >= low 約束正常運作\n")
        return True

    except Exception as e:
        logger.error(f"❌ 測試 1 失敗: {e}")
        return False
    finally:
        db.close()


def test_close_range_constraint():
    """測試 2: close BETWEEN low AND high 約束"""
    logger.info("=" * 60)
    logger.info("🔒 測試 2: close BETWEEN low AND high 約束")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        test_stock_id = "2330"
        test_date = date.today()

        # 清理可能存在的測試數據
        db.execute(text(f"""
        DELETE FROM stock_prices
        WHERE stock_id = '{test_stock_id}' AND date = '{test_date}'
        """))
        db.commit()

        # 測試 2.1: 嘗試插入 close > high 的記錄（應該失敗）
        logger.info("測試 2.1: 嘗試插入 close > high 的記錄（應該失敗）...")
        try:
            db.execute(text(f"""
            INSERT INTO stock_prices (stock_id, date, open, high, low, close, volume)
            VALUES ('{test_stock_id}', '{test_date}', 100, 105, 95, 110, 1000)
            """))
            db.commit()
            logger.error("   ❌ 錯誤：close > high 的記錄被插入（約束未生效）")
            return False
        except IntegrityError as e:
            db.rollback()
            if "chk_stock_prices_close_range" in str(e):
                logger.info("   ✅ 正確：close > high 的記錄被約束阻擋")
            else:
                logger.error(f"   ❌ 錯誤：被其他約束阻擋: {e}")
                return False

        # 測試 2.2: 嘗試插入 close < low 的記錄（應該失敗）
        logger.info("測試 2.2: 嘗試插入 close < low 的記錄（應該失敗）...")
        try:
            db.execute(text(f"""
            INSERT INTO stock_prices (stock_id, date, open, high, low, close, volume)
            VALUES ('{test_stock_id}', '{test_date}', 100, 105, 95, 90, 1000)
            """))
            db.commit()
            logger.error("   ❌ 錯誤：close < low 的記錄被插入（約束未生效）")
            return False
        except IntegrityError as e:
            db.rollback()
            if "chk_stock_prices_close_range" in str(e):
                logger.info("   ✅ 正確：close < low 的記錄被約束阻擋")
            else:
                logger.error(f"   ❌ 錯誤：被其他約束阻擋: {e}")
                return False

        # 測試 2.3: 插入 close 在範圍內的記錄（應該成功）
        logger.info("測試 2.3: 插入 close 在範圍內的記錄（應該成功）...")
        db.execute(text(f"""
        INSERT INTO stock_prices (stock_id, date, open, high, low, close, volume)
        VALUES ('{test_stock_id}', '{test_date}', 100, 105, 95, 102, 1000)
        """))
        db.commit()
        logger.info("   ✅ close 在範圍內的記錄成功插入")

        # 清理測試數據
        db.execute(text(f"""
        DELETE FROM stock_prices
        WHERE stock_id = '{test_stock_id}' AND date = '{test_date}'
        """))
        db.commit()

        logger.info("✅ 測試 2 通過：close BETWEEN low AND high 約束正常運作\n")
        return True

    except Exception as e:
        logger.error(f"❌ 測試 2 失敗: {e}")
        return False
    finally:
        db.close()


def test_positive_prices_constraint():
    """測試 3: 正價格約束（或全零）"""
    logger.info("=" * 60)
    logger.info("🔒 測試 3: 正價格約束")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        test_stock_id = "2330"
        test_date = date.today()

        # 清理可能存在的測試數據
        db.execute(text(f"""
        DELETE FROM stock_prices
        WHERE stock_id = '{test_stock_id}' AND date = '{test_date}'
        """))
        db.commit()

        # 測試 3.1: 嘗試插入部分為零的記錄（應該失敗）
        logger.info("測試 3.1: 嘗試插入 open=0 但其他非零的記錄（應該失敗）...")
        try:
            db.execute(text(f"""
            INSERT INTO stock_prices (stock_id, date, open, high, low, close, volume)
            VALUES ('{test_stock_id}', '{test_date}', 0, 105, 95, 100, 1000)
            """))
            db.commit()
            logger.error("   ❌ 錯誤：部分為零的記錄被插入（約束未生效）")
            return False
        except IntegrityError as e:
            db.rollback()
            if "chk_stock_prices_positive" in str(e):
                logger.info("   ✅ 正確：部分為零的記錄被約束阻擋")
            else:
                logger.error(f"   ❌ 錯誤：被其他約束阻擋: {e}")
                return False

        # 測試 3.2: 嘗試插入 open <= 0 的記錄（應該失敗，除非全零）
        logger.info("測試 3.2: 嘗試插入 open=-1 的記錄（應該失敗）...")
        try:
            db.execute(text(f"""
            INSERT INTO stock_prices (stock_id, date, open, high, low, close, volume)
            VALUES ('{test_stock_id}', '{test_date}', -1, 105, 95, 100, 1000)
            """))
            db.commit()
            logger.error("   ❌ 錯誤：負價格記錄被插入（約束未生效）")
            return False
        except IntegrityError as e:
            db.rollback()
            if "chk_stock_prices_positive" in str(e):
                logger.info("   ✅ 正確：負價格記錄被約束阻擋")
            else:
                logger.error(f"   ❌ 錯誤：被其他約束阻擋: {e}")
                return False

        # 測試 3.3: 插入全零記錄（應該成功）
        logger.info("測試 3.3: 插入全零記錄（應該成功）...")
        db.execute(text(f"""
        INSERT INTO stock_prices (stock_id, date, open, high, low, close, volume)
        VALUES ('{test_stock_id}', '{test_date}', 0, 0, 0, 0, 0)
        """))
        db.commit()
        logger.info("   ✅ 全零記錄成功插入（placeholder 允許）")

        # 清理測試數據
        db.execute(text(f"""
        DELETE FROM stock_prices
        WHERE stock_id = '{test_stock_id}' AND date = '{test_date}'
        """))
        db.commit()

        # 測試 3.4: 插入正常正價格記錄（應該成功）
        logger.info("測試 3.4: 插入正常正價格記錄（應該成功）...")
        db.execute(text(f"""
        INSERT INTO stock_prices (stock_id, date, open, high, low, close, volume)
        VALUES ('{test_stock_id}', '{test_date}', 100, 105, 95, 102, 1000)
        """))
        db.commit()
        logger.info("   ✅ 正常正價格記錄成功插入")

        # 清理測試數據
        db.execute(text(f"""
        DELETE FROM stock_prices
        WHERE stock_id = '{test_stock_id}' AND date = '{test_date}'
        """))
        db.commit()

        logger.info("✅ 測試 3 通過：正價格約束正常運作\n")
        return True

    except Exception as e:
        logger.error(f"❌ 測試 3 失敗: {e}")
        return False
    finally:
        db.close()


def main():
    """執行所有測試"""
    logger.info("\n" + "=" * 60)
    logger.info("🧪 開始 CHECK 約束測試")
    logger.info("=" * 60 + "\n")

    results = {
        "high >= low": test_high_low_constraint(),
        "close 範圍": test_close_range_constraint(),
        "正價格": test_positive_prices_constraint()
    }

    # 總結
    logger.info("=" * 60)
    logger.info("📊 測試結果總結")
    logger.info("=" * 60)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✅ 通過" if result else "❌ 失敗"
        logger.info(f"{test_name}: {status}")

    logger.info("=" * 60)
    logger.info(f"總計: {passed}/{total} 測試通過")

    if passed == total:
        logger.info("🎉 所有 CHECK 約束測試通過！數據品質得到保證")
        return True
    else:
        logger.error(f"⚠️  {total - passed} 個測試失敗，請檢查約束設置")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
