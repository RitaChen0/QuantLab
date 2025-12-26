"""
清理無效價格數據

此腳本處理以下問題：
1. 股票名稱等於股票代碼（表示缺少正確的公司名稱）
2. 所有價格為 0 的記錄（無效數據）
3. 將這些股票標記為 inactive 並刪除其無效價格數據
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from app.db.session import SessionLocal
from loguru import logger
import argparse


def identify_invalid_stocks(db) -> list:
    """
    識別無效股票（名稱等於股票代碼且所有價格為0）

    Returns:
        List of (stock_id, invalid_count) tuples
    """
    query = text("""
    SELECT
        s.stock_id,
        COUNT(*) as invalid_count
    FROM stocks s
    JOIN stock_prices sp ON s.stock_id = sp.stock_id
    WHERE s.name = s.stock_id  -- 名稱等於代碼（無正確名稱）
      AND sp.open <= 0         -- 價格為0
    GROUP BY s.stock_id
    HAVING COUNT(*) > 100  -- 只處理有大量無效數據的股票
    ORDER BY invalid_count DESC
    """)

    result = db.execute(query)
    return [(row.stock_id, row.invalid_count) for row in result]


def verify_all_prices_zero(db, stock_id: str) -> bool:
    """
    驗證某股票的所有價格是否都為0

    Args:
        db: Database session
        stock_id: Stock ID to check

    Returns:
        True if all prices are zero, False otherwise
    """
    query = text("""
    SELECT COUNT(*) as total,
           SUM(CASE WHEN open > 0 OR high > 0 OR low > 0 OR close > 0 THEN 1 ELSE 0 END) as valid_count
    FROM stock_prices
    WHERE stock_id = :stock_id
    """)

    result = db.execute(query, {"stock_id": stock_id}).fetchone()
    return result.valid_count == 0


def cleanup_invalid_stock(db, stock_id: str, dry_run: bool = False) -> dict:
    """
    清理單一無效股票

    Args:
        db: Database session
        stock_id: Stock ID to cleanup
        dry_run: If True, don't actually delete/update

    Returns:
        Cleanup statistics
    """
    # 計算要刪除的記錄數
    count_query = text("""
    SELECT COUNT(*) as count
    FROM stock_prices
    WHERE stock_id = :stock_id AND open <= 0
    """)
    count_result = db.execute(count_query, {"stock_id": stock_id}).fetchone()
    records_to_delete = count_result.count

    if not dry_run:
        # 刪除無效價格記錄
        delete_query = text("""
        DELETE FROM stock_prices
        WHERE stock_id = :stock_id AND open <= 0
        """)
        db.execute(delete_query, {"stock_id": stock_id})

        # 標記股票為 inactive
        update_query = text("""
        UPDATE stocks
        SET is_active = 'inactive'
        WHERE stock_id = :stock_id
        """)
        db.execute(update_query, {"stock_id": stock_id})

        db.commit()
        logger.info(f"✅ 已清理 {stock_id}: 刪除 {records_to_delete} 筆記錄，標記為 inactive")
    else:
        logger.info(f"🔍 [DRY RUN] {stock_id}: 將刪除 {records_to_delete} 筆記錄，標記為 inactive")

    return {
        "stock_id": stock_id,
        "records_deleted": records_to_delete,
        "marked_inactive": True
    }


def main(dry_run: bool = False, limit: int = None):
    """
    主清理函數

    Args:
        dry_run: If True, only show what would be cleaned
        limit: Maximum number of stocks to process (for testing)
    """
    db = SessionLocal()

    try:
        logger.info("=" * 60)
        logger.info("🔧 開始清理無效價格數據")
        if dry_run:
            logger.warning("⚠️  DRY RUN MODE - 不會實際修改資料庫")
        logger.info("=" * 60)

        # 識別無效股票
        logger.info("📊 識別無效股票...")
        invalid_stocks = identify_invalid_stocks(db)

        if limit:
            invalid_stocks = invalid_stocks[:limit]
            logger.info(f"⚠️  限制處理前 {limit} 個股票（測試模式）")

        logger.info(f"發現 {len(invalid_stocks)} 個無效股票")

        # 統計
        total_deleted = 0
        total_stocks_cleaned = 0
        skipped_stocks = []

        # 清理每個無效股票
        for i, (stock_id, invalid_count) in enumerate(invalid_stocks, 1):
            logger.info(f"\n[{i}/{len(invalid_stocks)}] 處理股票 {stock_id} ({invalid_count} 筆無效記錄)...")

            # 驗證所有價格都為0
            if not verify_all_prices_zero(db, stock_id):
                logger.warning(f"⚠️  跳過 {stock_id}: 存在非零價格，可能不是完全無效的股票")
                skipped_stocks.append(stock_id)
                continue

            # 執行清理
            result = cleanup_invalid_stock(db, stock_id, dry_run=dry_run)
            total_deleted += result["records_deleted"]
            total_stocks_cleaned += 1

        # 總結
        logger.info("\n" + "=" * 60)
        logger.info("✅ 清理完成！")
        logger.info("=" * 60)
        logger.info(f"處理股票數: {total_stocks_cleaned}")
        logger.info(f"刪除記錄數: {total_deleted:,}")
        logger.info(f"跳過股票數: {len(skipped_stocks)}")

        if skipped_stocks:
            logger.info(f"跳過的股票: {', '.join(skipped_stocks[:10])}" +
                       (f" ... 等 {len(skipped_stocks)} 個" if len(skipped_stocks) > 10 else ""))

        if dry_run:
            logger.warning("⚠️  這是 DRY RUN，實際資料庫未被修改")
            logger.info("💡 執行 --no-dry-run 以實際清理資料")

    except Exception as e:
        logger.error(f"❌ 清理失敗: {e}")
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='清理無效價格數據')
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
        '--limit',
        type=int,
        default=None,
        help='限制處理股票數量（用於測試）'
    )

    args = parser.parse_args()

    main(dry_run=args.dry_run, limit=args.limit)
