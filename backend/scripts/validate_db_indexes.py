#!/usr/bin/env python3
"""
数据库索引性能验证脚本

检查关键查询是否正确使用索引，识别性能瓶颈。

使用方法:
    python /app/scripts/validate_db_indexes.py
"""

import sys
sys.path.insert(0, '/app')

from sqlalchemy import text
from app.db.session import SessionLocal
from loguru import logger
from typing import List, Dict, Any


def get_table_indexes(db, table_name: str) -> List[Dict[str, Any]]:
    """获取表的所有索引"""
    query = text("""
        SELECT
            schemaname,
            tablename,
            indexname,
            indexdef
        FROM pg_indexes
        WHERE tablename = :table_name
        ORDER BY indexname;
    """)

    result = db.execute(query, {"table_name": table_name})
    indexes = [row._asdict() for row in result]
    return indexes


def explain_query(db, query: str, params: Dict[str, Any] = None) -> List[str]:
    """
    执行 EXPLAIN ANALYZE 分析查询计划

    返回关键信息：是否使用索引、扫描类型等
    """
    explain_query = f"EXPLAIN (ANALYZE, BUFFERS) {query}"

    try:
        result = db.execute(text(explain_query), params or {})
        plan_lines = [row[0] for row in result]
        return plan_lines
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        return [f"ERROR: {str(e)}"]


def check_index_usage(plan_lines: List[str]) -> Dict[str, Any]:
    """
    分析执行计划，检查索引使用情况

    返回:
        - scan_type: 扫描类型 (Index Scan, Seq Scan, Index Only Scan, etc.)
        - index_used: 是否使用索引
        - index_name: 使用的索引名称（如果有）
        - execution_time: 执行时间（ms）
    """
    scan_type = "Unknown"
    index_used = False
    index_name = None
    execution_time = 0.0

    for line in plan_lines:
        # 检查扫描类型
        if "Index Scan" in line or "Index Only Scan" in line:
            scan_type = "Index Scan" if "Index Scan" in line else "Index Only Scan"
            index_used = True

            # 提取索引名称
            if "using" in line.lower():
                parts = line.split("using")
                if len(parts) > 1:
                    index_part = parts[1].strip()
                    index_name = index_part.split()[0]

        elif "Bitmap Heap Scan" in line or "Bitmap Index Scan" in line:
            scan_type = "Bitmap Scan"
            index_used = True

        elif "Seq Scan" in line:
            scan_type = "Sequential Scan"
            index_used = False

        # 提取执行时间
        if "Execution Time:" in line:
            try:
                time_str = line.split("Execution Time:")[1].strip().split()[0]
                execution_time = float(time_str)
            except:
                pass

    return {
        "scan_type": scan_type,
        "index_used": index_used,
        "index_name": index_name,
        "execution_time_ms": execution_time
    }


def validate_stock_prices_indexes(db):
    """验证 stock_prices 表的索引使用"""
    logger.info("=" * 60)
    logger.info("📊 Validating stock_prices indexes...")
    logger.info("=" * 60)

    # 1. 列出所有索引
    indexes = get_table_indexes(db, "stock_prices")
    logger.info(f"\n✅ Found {len(indexes)} indexes on stock_prices:")
    for idx in indexes:
        logger.info(f"   - {idx['indexname']}: {idx['indexdef']}")

    # 2. 测试常见查询
    test_queries = [
        {
            "name": "按股票ID和日期范围查询",
            "query": """
                SELECT * FROM stock_prices
                WHERE stock_id = :stock_id
                  AND date BETWEEN :start_date AND :end_date
                ORDER BY date DESC
                LIMIT 100
            """,
            "params": {
                "stock_id": "2330",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            },
            "expected_index": "idx_stock_prices_stock_date"
        },
        {
            "name": "按日期查询所有股票",
            "query": """
                SELECT stock_id, close FROM stock_prices
                WHERE date = :date
                LIMIT 100
            """,
            "params": {"date": "2024-12-01"},
            "expected_index": "stock_prices_time_idx"  # TimescaleDB 自动创建
        }
    ]

    logger.info("\n🔍 Testing query performance:")
    for test in test_queries:
        logger.info(f"\n  📝 Query: {test['name']}")
        logger.info(f"     Expected index: {test['expected_index']}")

        plan_lines = explain_query(db, test["query"], test["params"])
        analysis = check_index_usage(plan_lines)

        if analysis["index_used"]:
            logger.info(f"     ✅ Index used: {analysis['index_name']}")
            logger.info(f"     Scan type: {analysis['scan_type']}")
            logger.info(f"     Execution time: {analysis['execution_time_ms']:.2f} ms")
        else:
            logger.warning(f"     ⚠️  No index used! Scan type: {analysis['scan_type']}")
            logger.warning(f"     Execution time: {analysis['execution_time_ms']:.2f} ms")
            logger.warning(f"     Plan details:")
            for line in plan_lines[:5]:  # 只显示前5行
                logger.warning(f"       {line}")


def validate_stock_minute_prices_indexes(db):
    """验证 stock_minute_prices 表的索引使用"""
    logger.info("\n" + "=" * 60)
    logger.info("📊 Validating stock_minute_prices indexes...")
    logger.info("=" * 60)

    # 1. 列出所有索引
    indexes = get_table_indexes(db, "stock_minute_prices")
    logger.info(f"\n✅ Found {len(indexes)} indexes on stock_minute_prices:")
    for idx in indexes:
        logger.info(f"   - {idx['indexname']}")

    # 2. 测试常见查询
    test_queries = [
        {
            "name": "按股票ID和时间范围查询1分钟K线",
            "query": """
                SELECT * FROM stock_minute_prices
                WHERE stock_id = :stock_id
                  AND datetime BETWEEN :start_time AND :end_time
                  AND timeframe = :timeframe
                ORDER BY datetime DESC
                LIMIT 1000
            """,
            "params": {
                "stock_id": "2330",
                "start_time": "2024-12-01 09:00:00",
                "end_time": "2024-12-01 13:30:00",
                "timeframe": "1min"
            },
            "expected_index": "idx_stock_minute_prices_stock_datetime_tf"
        }
    ]

    logger.info("\n🔍 Testing query performance:")
    for test in test_queries:
        logger.info(f"\n  📝 Query: {test['name']}")
        logger.info(f"     Expected index: {test['expected_index']}")

        plan_lines = explain_query(db, test["query"], test["params"])
        analysis = check_index_usage(plan_lines)

        if analysis["index_used"]:
            logger.info(f"     ✅ Index used: {analysis['index_name']}")
            logger.info(f"     Scan type: {analysis['scan_type']}")
            logger.info(f"     Execution time: {analysis['execution_time_ms']:.2f} ms")
        else:
            logger.warning(f"     ⚠️  No index used! Scan type: {analysis['scan_type']}")
            logger.warning(f"     Execution time: {analysis['execution_time_ms']:.2f} ms")


def validate_strategies_indexes(db):
    """验证 strategies 表的索引使用"""
    logger.info("\n" + "=" * 60)
    logger.info("📊 Validating strategies indexes...")
    logger.info("=" * 60)

    indexes = get_table_indexes(db, "strategies")
    logger.info(f"\n✅ Found {len(indexes)} indexes on strategies:")
    for idx in indexes:
        logger.info(f"   - {idx['indexname']}")

    test_queries = [
        {
            "name": "按用户ID查询策略",
            "query": """
                SELECT * FROM strategies
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT 20
            """,
            "params": {"user_id": 1},
            "expected_index": "idx_strategies_user_id"
        }
    ]

    logger.info("\n🔍 Testing query performance:")
    for test in test_queries:
        logger.info(f"\n  📝 Query: {test['name']}")

        plan_lines = explain_query(db, test["query"], test["params"])
        analysis = check_index_usage(plan_lines)

        if analysis["index_used"]:
            logger.info(f"     ✅ Index used: {analysis['index_name']}")
            logger.info(f"     Execution time: {analysis['execution_time_ms']:.2f} ms")
        else:
            logger.warning(f"     ⚠️  No index used!")


def validate_backtests_indexes(db):
    """验证 backtests 表的索引使用"""
    logger.info("\n" + "=" * 60)
    logger.info("📊 Validating backtests indexes...")
    logger.info("=" * 60)

    indexes = get_table_indexes(db, "backtests")
    logger.info(f"\n✅ Found {len(indexes)} indexes on backtests:")
    for idx in indexes:
        logger.info(f"   - {idx['indexname']}")

    test_queries = [
        {
            "name": "按用户ID查询回测记录",
            "query": """
                SELECT * FROM backtests
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT 20
            """,
            "params": {"user_id": 1},
            "expected_index": "idx_backtests_user_id"
        },
        {
            "name": "按策略ID查询回测记录",
            "query": """
                SELECT * FROM backtests
                WHERE strategy_id = :strategy_id
                ORDER BY created_at DESC
            """,
            "params": {"strategy_id": 1},
            "expected_index": "idx_backtests_strategy_id"
        }
    ]

    logger.info("\n🔍 Testing query performance:")
    for test in test_queries:
        logger.info(f"\n  📝 Query: {test['name']}")

        plan_lines = explain_query(db, test["query"], test["params"])
        analysis = check_index_usage(plan_lines)

        if analysis["index_used"]:
            logger.info(f"     ✅ Index used: {analysis['index_name']}")
            logger.info(f"     Execution time: {analysis['execution_time_ms']:.2f} ms")
        else:
            logger.warning(f"     ⚠️  No index used!")


def check_missing_indexes(db):
    """检查可能缺失的索引"""
    logger.info("\n" + "=" * 60)
    logger.info("🔍 Checking for missing indexes...")
    logger.info("=" * 60)

    # 查询未使用索引的查询（需要 pg_stat_statements 扩展）
    check_extension = text("""
        SELECT EXISTS(
            SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
        );
    """)

    result = db.execute(check_extension).scalar()

    if not result:
        logger.warning("⚠️  pg_stat_statements extension not installed")
        logger.info("   Run: CREATE EXTENSION pg_stat_statements;")
        return

    logger.info("✅ pg_stat_statements extension is available")

    # 查找顺序扫描最多的表
    slow_queries = text("""
        SELECT
            schemaname,
            tablename,
            seq_scan,
            seq_tup_read,
            idx_scan,
            idx_tup_fetch,
            CASE
                WHEN seq_scan = 0 THEN 0
                ELSE ROUND(100.0 * idx_scan / (seq_scan + idx_scan), 2)
            END as index_usage_pct
        FROM pg_stat_user_tables
        WHERE schemaname = 'public'
          AND (seq_scan > 0 OR idx_scan > 0)
        ORDER BY seq_scan DESC
        LIMIT 10;
    """)

    result = db.execute(slow_queries)
    logger.info("\n📊 Top 10 tables by sequential scans:")
    logger.info(f"   {'Table':<30} {'Seq Scan':<12} {'Index Scan':<12} {'Index Usage %':<15}")
    logger.info("   " + "-" * 70)

    for row in result:
        logger.info(
            f"   {row.tablename:<30} {row.seq_scan:<12} "
            f"{row.idx_scan or 0:<12} {row.index_usage_pct or 0:<15}%"
        )


def main():
    """主函数"""
    logger.info("🚀 Starting database index validation...")

    db = SessionLocal()

    try:
        # 验证各表索引
        validate_stock_prices_indexes(db)
        validate_stock_minute_prices_indexes(db)
        validate_strategies_indexes(db)
        validate_backtests_indexes(db)

        # 检查缺失索引
        check_missing_indexes(db)

        logger.info("\n" + "=" * 60)
        logger.info("✅ Index validation completed!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        db.close()


if __name__ == "__main__":
    main()
