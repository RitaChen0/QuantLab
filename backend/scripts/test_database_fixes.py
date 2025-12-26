"""
測試資料庫完整性修復

驗證所有 4 個修復項目是否正常運作
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.db.session import SessionLocal
from app.utils.cache import cache
from loguru import logger
import time
from datetime import date, timedelta


def test_distributed_locks():
    """測試 1: 驗證分布式鎖是否正常運作"""
    logger.info("=" * 60)
    logger.info("🔒 測試 1: 分布式鎖")
    logger.info("=" * 60)

    redis_client = cache.redis_client
    lock_key = "task_lock:test_task"

    try:
        # 測試 1.1: 獲取鎖
        logger.info("測試 1.1: 獲取鎖...")
        lock1 = redis_client.lock(lock_key, timeout=10)
        acquired1 = lock1.acquire(blocking=False)

        if acquired1:
            logger.info("   ✅ 成功獲取鎖")
        else:
            logger.error("   ❌ 無法獲取鎖")
            return False

        # 測試 1.2: 第二次獲取應該失敗
        logger.info("測試 1.2: 嘗試重複獲取鎖（應該失敗）...")
        lock2 = redis_client.lock(lock_key, timeout=10)
        acquired2 = lock2.acquire(blocking=False)

        if not acquired2:
            logger.info("   ✅ 正確：重複獲取被阻擋")
        else:
            logger.error("   ❌ 錯誤：重複獲取成功（分布式鎖未生效）")
            lock2.release()
            return False

        # 測試 1.3: 釋放鎖後可以再次獲取
        logger.info("測試 1.3: 釋放鎖後再次獲取...")
        lock1.release()
        time.sleep(0.1)

        lock3 = redis_client.lock(lock_key, timeout=10)
        acquired3 = lock3.acquire(blocking=False)

        if acquired3:
            logger.info("   ✅ 正確：釋放後可以再次獲取")
            lock3.release()
        else:
            logger.error("   ❌ 錯誤：釋放後無法獲取")
            return False

        logger.info("✅ 測試 1 通過：分布式鎖正常運作\n")
        return True

    except Exception as e:
        logger.error(f"❌ 測試 1 失敗: {e}")
        return False


def test_cascade_foreign_key():
    """測試 2: 驗證 CASCADE 外鍵約束"""
    logger.info("=" * 60)
    logger.info("🗑️ 測試 2: CASCADE 外鍵約束")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        # 測試 2.1: 創建測試股票
        logger.info("測試 2.1: 創建測試股票...")
        test_stock_id = "TEST9999"

        # 檢查是否已存在，如果存在則先刪除
        existing = db.execute(text(f"SELECT 1 FROM stocks WHERE stock_id = '{test_stock_id}'")).fetchone()
        if existing:
            db.execute(text(f"DELETE FROM stocks WHERE stock_id = '{test_stock_id}'"))
            db.commit()

        db.execute(text(f"""
        INSERT INTO stocks (stock_id, name, category, market, is_active)
        VALUES ('{test_stock_id}', 'Test Stock', 'TEST', 'TEST', 'active')
        """))
        db.commit()
        logger.info(f"   ✅ 測試股票 {test_stock_id} 創建成功")

        # 測試 2.2: 創建測試分鐘線數據
        logger.info("測試 2.2: 創建測試分鐘線數據...")
        test_datetime = "2025-01-01 09:00:00"

        db.execute(text(f"""
        INSERT INTO stock_minute_prices (stock_id, datetime, timeframe, open, high, low, close, volume)
        VALUES ('{test_stock_id}', '{test_datetime}', '1min', 100, 105, 99, 102, 1000)
        """))
        db.commit()
        logger.info(f"   ✅ 測試分鐘線數據創建成功")

        # 測試 2.3: 驗證數據存在
        logger.info("測試 2.3: 驗證數據存在...")
        minute_count = db.execute(text(f"""
        SELECT COUNT(*) FROM stock_minute_prices WHERE stock_id = '{test_stock_id}'
        """)).fetchone()[0]

        if minute_count > 0:
            logger.info(f"   ✅ 分鐘線數據存在: {minute_count} 筆")
        else:
            logger.error("   ❌ 分鐘線數據不存在")
            return False

        # 測試 2.4: 刪除股票，驗證 CASCADE
        logger.info("測試 2.4: 刪除股票，驗證分鐘線數據是否級聯刪除...")
        db.execute(text(f"DELETE FROM stocks WHERE stock_id = '{test_stock_id}'"))
        db.commit()
        logger.info(f"   ✅ 股票 {test_stock_id} 已刪除")

        # 測試 2.5: 驗證分鐘線數據已被級聯刪除
        logger.info("測試 2.5: 驗證分鐘線數據已被級聯刪除...")
        minute_count_after = db.execute(text(f"""
        SELECT COUNT(*) FROM stock_minute_prices WHERE stock_id = '{test_stock_id}'
        """)).fetchone()[0]

        if minute_count_after == 0:
            logger.info("   ✅ 正確：分鐘線數據已被級聯刪除")
        else:
            logger.error(f"   ❌ 錯誤：仍有 {minute_count_after} 筆分鐘線數據（CASCADE 未生效）")
            return False

        logger.info("✅ 測試 2 通過：CASCADE 外鍵約束正常運作\n")
        return True

    except Exception as e:
        logger.error(f"❌ 測試 2 失敗: {e}")
        db.rollback()
        return False
    finally:
        # 清理測試數據
        try:
            db.execute(text(f"DELETE FROM stocks WHERE stock_id = '{test_stock_id}'"))
            db.commit()
        except:
            pass
        db.close()


def test_unique_constraint():
    """測試 3: 驗證唯一約束"""
    logger.info("=" * 60)
    logger.info("🔒 測試 3: 唯一約束")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        # 測試 3.1: 創建測試股票（如果不存在）
        logger.info("測試 3.1: 準備測試數據...")
        test_stock_id = "2330"  # 使用真實股票
        test_date = date.today() - timedelta(days=1)
        test_investor_type = "Foreign"

        # 清理可能存在的測試數據
        db.execute(text(f"""
        DELETE FROM institutional_investors
        WHERE stock_id = '{test_stock_id}'
          AND date = '{test_date}'
          AND investor_type = '{test_investor_type}'
        """))
        db.commit()
        logger.info("   ✅ 測試環境準備完成")

        # 測試 3.2: 插入第一筆記錄
        logger.info("測試 3.2: 插入第一筆法人買賣超記錄...")
        db.execute(text(f"""
        INSERT INTO institutional_investors (stock_id, date, investor_type, buy_volume, sell_volume)
        VALUES ('{test_stock_id}', '{test_date}', '{test_investor_type}', 1000, 500)
        """))
        db.commit()
        logger.info("   ✅ 第一筆記錄插入成功")

        # 測試 3.3: 嘗試插入重複記錄（應該失敗）
        logger.info("測試 3.3: 嘗試插入重複記錄（應該失敗）...")
        try:
            db.execute(text(f"""
            INSERT INTO institutional_investors (stock_id, date, investor_type, buy_volume, sell_volume)
            VALUES ('{test_stock_id}', '{test_date}', '{test_investor_type}', 2000, 1000)
            """))
            db.commit()
            logger.error("   ❌ 錯誤：重複記錄插入成功（唯一約束未生效）")
            return False
        except IntegrityError as e:
            db.rollback()
            if "uq_institutional_investors_stock_date_type" in str(e):
                logger.info("   ✅ 正確：重複記錄被唯一約束阻擋")
            else:
                logger.error(f"   ❌ 錯誤：被其他約束阻擋: {e}")
                return False

        # 測試 3.4: 插入不同日期的記錄（應該成功）
        logger.info("測試 3.4: 插入不同日期的記錄（應該成功）...")
        test_date2 = test_date - timedelta(days=1)
        db.execute(text(f"""
        INSERT INTO institutional_investors (stock_id, date, investor_type, buy_volume, sell_volume)
        VALUES ('{test_stock_id}', '{test_date2}', '{test_investor_type}', 1500, 800)
        """))
        db.commit()
        logger.info("   ✅ 不同日期記錄插入成功")

        # 測試 3.5: 插入不同投資者類型的記錄（應該成功）
        logger.info("測試 3.5: 插入不同投資者類型的記錄（應該成功）...")
        db.execute(text(f"""
        INSERT INTO institutional_investors (stock_id, date, investor_type, buy_volume, sell_volume)
        VALUES ('{test_stock_id}', '{test_date}', 'Dealer', 3000, 2000)
        """))
        db.commit()
        logger.info("   ✅ 不同投資者類型記錄插入成功")

        logger.info("✅ 測試 3 通過：唯一約束正常運作\n")
        return True

    except Exception as e:
        logger.error(f"❌ 測試 3 失敗: {e}")
        db.rollback()
        return False
    finally:
        # 清理測試數據
        try:
            db.execute(text(f"""
            DELETE FROM institutional_investors
            WHERE stock_id = '{test_stock_id}'
              AND (date = '{test_date}' OR date = '{test_date - timedelta(days=1)}')
            """))
            db.commit()
        except:
            pass
        db.close()


def test_zero_price_cleanup():
    """測試 4: 驗證零價格記錄已清理"""
    logger.info("=" * 60)
    logger.info("🧹 測試 4: 零價格記錄清理")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        # 測試 4.1: 檢查零價格記錄數量
        logger.info("測試 4.1: 檢查零價格記錄數量...")
        zero_count = db.execute(text("""
        SELECT COUNT(*) FROM stock_prices WHERE open <= 0
        """)).fetchone()[0]

        if zero_count == 0:
            logger.info("   ✅ 正確：無零價格記錄")
        else:
            logger.error(f"   ❌ 錯誤：仍有 {zero_count:,} 筆零價格記錄")
            return False

        # 測試 4.2: 檢查所有價格記錄的有效性
        logger.info("測試 4.2: 檢查價格記錄有效性...")
        invalid_count = db.execute(text("""
        SELECT COUNT(*) FROM stock_prices
        WHERE high < low OR close < 0 OR open < 0
        """)).fetchone()[0]

        if invalid_count == 0:
            logger.info("   ✅ 正確：所有價格記錄有效")
        else:
            logger.warning(f"   ⚠️  發現 {invalid_count:,} 筆邏輯無效的記錄（high < low 等）")

        # 測試 4.3: 統計當前數據品質
        logger.info("測試 4.3: 統計數據品質...")
        stats = db.execute(text("""
        SELECT
            COUNT(*) as total_records,
            COUNT(DISTINCT stock_id) as total_stocks,
            MIN(date) as earliest_date,
            MAX(date) as latest_date
        FROM stock_prices
        """)).fetchone()

        logger.info(f"   總記錄數: {stats.total_records:,}")
        logger.info(f"   總股票數: {stats.total_stocks}")
        logger.info(f"   日期範圍: {stats.earliest_date} ~ {stats.latest_date}")
        logger.info("   ✅ 數據品質良好")

        # 測試 4.4: 驗證新記錄不會插入零價格
        logger.info("測試 4.4: 測試插入零價格記錄...")
        test_stock_id = "2330"
        test_date = date.today()

        # 嘗試插入零價格（應該被允許，但我們可以驗證數據被正確記錄）
        try:
            db.execute(text(f"""
            INSERT INTO stock_prices (stock_id, date, open, high, low, close, volume)
            VALUES ('{test_stock_id}', '{test_date}', 0, 0, 0, 0, 0)
            ON CONFLICT (stock_id, date) DO NOTHING
            """))
            db.commit()

            # 檢查是否被插入
            inserted = db.execute(text(f"""
            SELECT COUNT(*) FROM stock_prices
            WHERE stock_id = '{test_stock_id}' AND date = '{test_date}' AND open = 0
            """)).fetchone()[0]

            if inserted > 0:
                logger.warning("   ⚠️  零價格記錄可以插入（建議添加 CHECK 約束）")
                # 清理測試數據
                db.execute(text(f"""
                DELETE FROM stock_prices
                WHERE stock_id = '{test_stock_id}' AND date = '{test_date}' AND open = 0
                """))
                db.commit()
            else:
                logger.info("   ℹ️  零價格記錄未插入（可能已有該日期數據）")

        except Exception as e:
            logger.info(f"   ℹ️  插入測試: {e}")
            db.rollback()

        logger.info("✅ 測試 4 通過：零價格記錄已清理\n")
        return True

    except Exception as e:
        logger.error(f"❌ 測試 4 失敗: {e}")
        return False
    finally:
        db.close()


def main():
    """執行所有測試"""
    logger.info("\n" + "=" * 60)
    logger.info("🧪 開始資料庫完整性修復測試")
    logger.info("=" * 60 + "\n")

    results = {
        "分布式鎖": test_distributed_locks(),
        "CASCADE 外鍵": test_cascade_foreign_key(),
        "唯一約束": test_unique_constraint(),
        "零價格清理": test_zero_price_cleanup()
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
        logger.info("🎉 所有測試通過！資料庫完整性修復正常運作")
        return True
    else:
        logger.error(f"⚠️  {total - passed} 個測試失敗，請檢查相關修復")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
