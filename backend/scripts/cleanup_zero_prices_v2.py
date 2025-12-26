"""
清理零價格記錄 - TimescaleDB 優化版本

使用直接 DELETE（不使用子查詢）以避免 TimescaleDB 解壓縮限制
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from app.db.session import SessionLocal
from loguru import logger
import argparse


def get_zero_price_stats(db) -> dict:
    """獲取零價格記錄統計"""
    query = text("""
    SELECT
        COUNT(*) as total_zero_records,
        COUNT(DISTINCT stock_id) as affected_stocks,
        MIN(date) as earliest_date,
        MAX(date) as latest_date
    FROM stock_prices
    WHERE open <= 0
    """)

    result = db.execute(query).fetchone()
    return {
        "total_zero_records": result.total_zero_records,
        "affected_stocks": result.affected_stocks,
        "earliest_date": result.earliest_date,
        "latest_date": result.latest_date
    }


def cleanup_zero_prices_direct(db, dry_run: bool = False) -> dict:
    """
    直接清理所有零價格記錄（不使用批次）

    TimescaleDB 壓縮表的最佳實踐：一次性刪除而非批次刪除
    """
    if dry_run:
        logger.info("🔍 [DRY RUN] 預覽將要刪除的記錄...")
        stats = get_zero_price_stats(db)
        logger.info(f"   總記錄數: {stats['total_zero_records']:,}")
        logger.info(f"   影響股票: {stats['affected_stocks']}")
        logger.info(f"   日期範圍: {stats['earliest_date']} ~ {stats['latest_date']}")
        return stats

    # 實際刪除
    logger.info("🗑️  開始刪除零價格記錄...")

    # 獲取初始統計
    initial_stats = get_zero_price_stats(db)
    total_to_delete = initial_stats["total_zero_records"]

    logger.info(f"   準備刪除 {total_to_delete:,} 筆記錄")
    logger.info(f"   影響 {initial_stats['affected_stocks']} 個股票")
    logger.warning("   ⚠️  此操作可能需要 5-10 分鐘，請耐心等待...")

    # 直接刪除所有零價格記錄
    delete_query = text("""
    DELETE FROM stock_prices
    WHERE open <= 0
    """)

    logger.info("   執行刪除...")
    result = db.execute(delete_query)
    deleted_count = result.rowcount

    db.commit()
    logger.info(f"   ✅ 刪除完成: {deleted_count:,} 筆記錄")

    return {
        "total_deleted": deleted_count,
        **initial_stats
    }


def main(dry_run: bool = False):
    """
    主清理函數

    Args:
        dry_run: If True, only show what would be cleaned
    """
    db = SessionLocal()

    try:
        logger.info("=" * 60)
        logger.info("🔧 開始清理零價格記錄 (TimescaleDB 優化版)")
        if dry_run:
            logger.warning("⚠️  DRY RUN MODE - 不會實際修改資料庫")
        logger.info("=" * 60)

        # 執行清理
        result = cleanup_zero_prices_direct(db, dry_run=dry_run)

        # 總結
        logger.info("\n" + "=" * 60)
        logger.info("✅ 清理完成！")
        logger.info("=" * 60)

        if not dry_run:
            logger.info(f"刪除記錄數: {result['total_deleted']:,}")
            logger.info(f"影響股票數: {result['affected_stocks']}")
        else:
            logger.info(f"將刪除記錄數: {result['total_zero_records']:,}")
            logger.info(f"影響股票數: {result['affected_stocks']}")
            logger.info(f"日期範圍: {result['earliest_date']} ~ {result['latest_date']}")
            logger.warning("⚠️  這是 DRY RUN，實際資料庫未被修改")
            logger.info("💡 執行 --no-dry-run 以實際清理資料")

        # 驗證清理後的狀態
        if not dry_run:
            logger.info("\n📊 驗證清理結果...")
            remaining_stats = get_zero_price_stats(db)
            logger.info(f"   剩餘零價格記錄: {remaining_stats['total_zero_records']:,}")

            if remaining_stats['total_zero_records'] == 0:
                logger.info("   ✅ 確認：所有零價格記錄已清除！")
            else:
                logger.warning(f"   ⚠️  仍有 {remaining_stats['total_zero_records']:,} 筆零價格記錄")

    except Exception as e:
        logger.error(f"❌ 清理失敗: {e}")
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='清理零價格記錄 (TimescaleDB 優化版)')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='演練模式（不修改資料庫，預設啟用）'
    )
    parser.add_argument(
        '--no-dry-run',
        action='store_false',
        dest='dry_run',
        help='實際執行清理（會修改資料庫）'
    )

    args = parser.parse_args()

    main(dry_run=args.dry_run)
