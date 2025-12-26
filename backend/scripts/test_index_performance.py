"""
測試複合索引的查詢效能

驗證新增的 9 個複合索引能否提升查詢效能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from app.db.session import SessionLocal
from loguru import logger
import time


def test_query_performance(query: str, description: str, expected_index: str = None):
    """測試單一查詢效能"""
    db = SessionLocal()

    try:
        # EXPLAIN ANALYZE to see query plan and execution time
        explain_query = f"EXPLAIN (ANALYZE, BUFFERS) {query}"

        logger.info(f"\n{'=' * 60}")
        logger.info(f"📊 {description}")
        logger.info(f"{'=' * 60}")

        # Execute EXPLAIN ANALYZE
        result = db.execute(text(explain_query))
        plan_lines = [row[0] for row in result]

        # Extract execution time
        for line in plan_lines:
            if "Execution Time:" in line:
                logger.info(f"⏱️  {line.strip()}")
            elif "Index Scan using" in line or "Index Only Scan using" in line:
                logger.info(f"✅ {line.strip()}")
                if expected_index and expected_index in line:
                    logger.info(f"   ✓ 使用預期索引: {expected_index}")
            elif "Seq Scan" in line and "TimescaleDB" not in line:
                logger.warning(f"⚠️  {line.strip()}")
                logger.warning(f"   ⚠️  使用循序掃描（可能需要優化）")

        return True

    except Exception as e:
        logger.error(f"❌ 查詢失敗: {e}")
        return False
    finally:
        db.close()


def main():
    """執行所有效能測試"""
    logger.info("\n" + "=" * 60)
    logger.info("🧪 開始索引效能測試")
    logger.info("=" * 60 + "\n")

    tests = [
        # Test 1: stock_prices recent data (DESC index)
        {
            "query": """
                SELECT stock_id, date, close
                FROM stock_prices
                WHERE stock_id = '2330'
                ORDER BY date DESC
                LIMIT 30
            """,
            "description": "測試 1: 查詢最近 30 天股價（使用 DESC 索引）",
            "expected_index": "idx_stock_prices_stock_date_desc"
        },

        # Test 2: institutional_investors recent data
        {
            "query": """
                SELECT stock_id, date, investor_type, buy_volume, sell_volume
                FROM institutional_investors
                WHERE stock_id = '2330'
                ORDER BY date DESC
                LIMIT 30
            """,
            "description": "測試 2: 查詢最近 30 天法人買賣超（使用 DESC 索引）",
            "expected_index": "idx_institutional_stock_date_desc"
        },

        # Test 3: Market-wide institutional data by date
        {
            "query": """
                SELECT date, investor_type, SUM(buy_volume) as total_buy
                FROM institutional_investors
                WHERE date >= CURRENT_DATE - INTERVAL '7 days'
                    AND investor_type = 'Foreign'
                GROUP BY date, investor_type
                ORDER BY date DESC
            """,
            "description": "測試 3: 查詢近 7 天外資買賣（使用日期+類型索引）",
            "expected_index": "idx_institutional_date_type"
        },

        # Test 4: stock_minute_prices recent data
        {
            "query": """
                SELECT stock_id, datetime, close
                FROM stock_minute_prices
                WHERE stock_id = '2330'
                    AND timeframe = '1min'
                ORDER BY datetime DESC
                LIMIT 100
            """,
            "description": "測試 4: 查詢最近 100 筆分鐘線（使用 timeframe+DESC 索引）",
            "expected_index": "idx_minute_stock_timeframe_datetime_desc"
        },

        # Test 5: fundamental_data latest data
        {
            "query": """
                SELECT stock_id, indicator, date, value
                FROM fundamental_data
                WHERE stock_id = '2330'
                    AND indicator = '本益比'
                ORDER BY date DESC
                LIMIT 12
            """,
            "description": "測試 5: 查詢最新基本面資料（使用 DESC 索引）",
            "expected_index": "idx_fundamental_stock_indicator_date_desc"
        },

        # Test 6: trades analysis
        {
            "query": """
                SELECT backtest_id, stock_id, date, action, quantity, price
                FROM trades
                WHERE backtest_id = (SELECT id FROM backtests ORDER BY created_at DESC LIMIT 1)
                    AND stock_id = '2330'
                ORDER BY date DESC
            """,
            "description": "測試 6: 查詢回測交易記錄（使用複合索引）",
            "expected_index": "idx_trades_backtest_stock_date_desc"
        },

        # Test 7: Running backtests (partial index)
        {
            "query": """
                SELECT id, name, created_at, status
                FROM backtests
                WHERE status = 'RUNNING'
                    AND user_id = (SELECT id FROM users LIMIT 1)
                ORDER BY created_at DESC
            """,
            "description": "測試 7: 查詢執行中的回測（使用部分索引）",
            "expected_index": "idx_backtests_running"
        },

        # Test 8: Pending backtests (partial index)
        {
            "query": """
                SELECT id, name, created_at, status
                FROM backtests
                WHERE status = 'PENDING'
                ORDER BY created_at DESC
                LIMIT 10
            """,
            "description": "測試 8: 查詢待執行回測（使用部分索引）",
            "expected_index": "idx_backtests_pending"
        },

        # Test 9: Active stocks (partial index)
        {
            "query": """
                SELECT stock_id, name, category, market
                FROM stocks
                WHERE is_active = 'active'
                    AND category = 'STOCK'
                ORDER BY stock_id
                LIMIT 100
            """,
            "description": "測試 9: 查詢活躍股票（使用部分索引）",
            "expected_index": "idx_stocks_active_category"
        }
    ]

    passed = 0
    total = len(tests)

    for i, test in enumerate(tests, 1):
        if test_query_performance(
            test["query"],
            test["description"],
            test.get("expected_index")
        ):
            passed += 1

        # Small delay between tests
        if i < total:
            time.sleep(0.5)

    # 總結
    logger.info("\n" + "=" * 60)
    logger.info("📊 測試結果總結")
    logger.info("=" * 60)

    logger.info(f"總計: {passed}/{total} 查詢測試完成")

    if passed == total:
        logger.info("🎉 所有查詢效能測試完成！")
        return True
    else:
        logger.warning(f"⚠️  {total - passed} 個測試未完成")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
