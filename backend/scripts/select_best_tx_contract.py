#!/usr/bin/env python3
"""
自動選擇最佳 TX 期貨合約

策略：
1. 優先使用連續合約（TXCONT）- 如果 >= 60 天
2. 否則使用歷史最長的月份合約（TX202512, TX202601 等）

目的：確保 RD-Agent 始終有足夠的歷史數據進行因子測試
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.core.config import settings
from loguru import logger


def select_best_contract(min_days: int = 60) -> str:
    """
    自動選擇最佳合約

    Args:
        min_days: 最少需要的交易日數（預設 60 天）

    Returns:
        str: 最佳合約代碼
    """
    logger.info("=" * 80)
    logger.info("🔍 自動選擇最佳 TX 期貨合約")
    logger.info("=" * 80)
    logger.info(f"📊 最少需要：{min_days} 天歷史數據")

    engine = create_engine(settings.DATABASE_URL)

    # 查詢所有 TX 相關合約的數據範圍
    query = text("""
        SELECT stock_id,
               COUNT(DISTINCT datetime::date) as trading_days,
               MIN(datetime::date) as earliest_date,
               MAX(datetime::date) as latest_date
        FROM stock_minute_prices
        WHERE stock_id LIKE 'TX%' AND stock_id != 'TX'
        GROUP BY stock_id
        HAVING COUNT(DISTINCT datetime::date) >= :min_days
        ORDER BY
            CASE
                WHEN stock_id = 'TXCONT' THEN 0
                ELSE 1
            END,
            COUNT(DISTINCT datetime::date) DESC
    """)

    with engine.connect() as conn:
        results = conn.execute(query, {"min_days": min_days}).fetchall()

    if not results:
        logger.error(f"❌ 找不到符合 >= {min_days} 天的合約")
        logger.info("💡 可用合約清單：")

        # 顯示所有可用合約
        query_all = text("""
            SELECT stock_id,
                   COUNT(DISTINCT datetime::date) as trading_days,
                   MIN(datetime::date) as earliest_date,
                   MAX(datetime::date) as latest_date
            FROM stock_minute_prices
            WHERE stock_id LIKE 'TX%' AND stock_id != 'TX'
            GROUP BY stock_id
            ORDER BY COUNT(DISTINCT datetime::date) DESC
        """)

        with engine.connect() as conn:
            all_results = conn.execute(query_all).fetchall()

        for row in all_results:
            logger.info(f"   {row[0]}: {row[1]} 天 ({row[2]} ~ {row[3]})")

        # 返回天數最多的合約（降低要求）
        if all_results:
            best = all_results[0]
            logger.warning(f"⚠️  降低要求，選擇最長合約：{best[0]} ({best[1]} 天)")
            return best[0]
        else:
            raise RuntimeError("無任何 TX 合約數據")

    # 優先選擇連續合約
    for row in results:
        stock_id, trading_days, earliest, latest = row

        if stock_id == 'TXCONT':
            logger.info("")
            logger.info("✅ 選擇連續合約（TXCONT）")
            logger.info(f"   📅 數據範圍：{earliest} ~ {latest}")
            logger.info(f"   📈 交易日數：{trading_days} 天")
            logger.info(f"   💡 優點：永不過期，自動換約")
            return 'TXCONT'

    # 如果連續合約不足，選擇月份合約
    best = results[0]
    stock_id, trading_days, earliest, latest = best

    logger.info("")
    logger.info(f"✅ 選擇月份合約（{stock_id}）")
    logger.info(f"   📅 數據範圍：{earliest} ~ {latest}")
    logger.info(f"   📈 交易日數：{trading_days} 天")
    logger.info(f"   ⚠️  注意：結算後需手動切換到下月合約")

    return stock_id


def main():
    """主程式"""
    try:
        contract = select_best_contract(min_days=60)

        logger.info("")
        logger.info("=" * 80)
        logger.info("🎯 最終決定")
        logger.info("=" * 80)
        logger.info(f"使用合約：{contract}")
        logger.info("")
        logger.info("💡 下一步：")
        logger.info(f"   docker compose exec backend python /app/scripts/generate_tx_daily_from_minute.py --contract {contract}")

        # 輸出到 stdout（供其他腳本使用）
        print(contract)

        sys.exit(0)

    except Exception as e:
        logger.error(f"❌ 選擇失敗：{e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
