"""
清理零價格記錄

此腳本只刪除 open=0 的價格記錄（保留有效數據）
適用於股票有部分有效數據和部分無效數據的情況
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from app.db.session import SessionLocal
from loguru import logger
import argparse


def get_zero_price_stats(db) -> dict:
    """
    獲取零價格記錄統計

    Returns:
        Statistics dictionary
    """
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


def cleanup_zero_prices(db, dry_run: bool = False, batch_size: int = 10000) -> dict:
    """
    清理所有零價格記錄

    Args:
        db: Database session
        dry_run: If True, don't actually delete
        batch_size: Delete records in batches

    Returns:
        Cleanup statistics
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

    # 批次刪除（避免一次性刪除太多造成鎖定問題）
    deleted_count = 0
    batch_num = 0

    while True:
        batch_num += 1
        logger.info(f"   執行批次 #{batch_num} (每批 {batch_size:,} 筆)...")

        # 刪除一批記錄 (使用 stock_id + date 而不是 ctid，兼容 TimescaleDB 壓縮)
        delete_query = text(f"""
        DELETE FROM stock_prices
        WHERE (stock_id, date) IN (
            SELECT stock_id, date FROM stock_prices
            WHERE open <= 0
            LIMIT {batch_size}
        )
        """)

        result = db.execute(delete_query)
        batch_deleted = result.rowcount
        deleted_count += batch_deleted

        db.commit()

        logger.info(f"      ✅ 批次 #{batch_num} 完成: 刪除 {batch_deleted:,} 筆 (總計: {deleted_count:,}/{total_to_delete:,})")

        # 如果這批沒刪除任何記錄，表示完成了
        if batch_deleted == 0:
            logger.info("   ✅ 所有零價格記錄已清理完畢")
            break

        # 每10批顯示進度
        if batch_num % 10 == 0:
            progress = (deleted_count / total_to_delete * 100) if total_to_delete > 0 else 100
            logger.info(f"   📊 進度: {progress:.1f}% ({deleted_count:,}/{total_to_delete:,})")

    return {
        "total_deleted": deleted_count,
        "batches": batch_num,
        **initial_stats
    }


def main(dry_run: bool = False, batch_size: int = 10000):
    """
    主清理函數

    Args:
        dry_run: If True, only show what would be cleaned
        batch_size: Number of records to delete per batch
    """
    db = SessionLocal()

    try:
        logger.info("=" * 60)
        logger.info("🔧 開始清理零價格記錄")
        if dry_run:
            logger.warning("⚠️  DRY RUN MODE - 不會實際修改資料庫")
        logger.info("=" * 60)

        # 執行清理
        result = cleanup_zero_prices(db, dry_run=dry_run, batch_size=batch_size)

        # 總結
        logger.info("\n" + "=" * 60)
        logger.info("✅ 清理完成！")
        logger.info("=" * 60)

        if not dry_run:
            logger.info(f"刪除記錄數: {result['total_deleted']:,}")
            logger.info(f"執行批次數: {result['batches']}")
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
    parser = argparse.ArgumentParser(description='清理零價格記錄')
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
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10000,
        help='每批刪除的記錄數（預設：10000）'
    )

    args = parser.parse_args()

    main(dry_run=args.dry_run, batch_size=args.batch_size)
