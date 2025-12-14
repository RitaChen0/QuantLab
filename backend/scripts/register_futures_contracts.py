#!/usr/bin/env python3
"""
註冊期貨月份合約到資料庫

功能：
1. 為 TX 和 MTX 創建所有月份合約（2024-2026）
2. 自動註冊到 stocks 表
3. 支持批次插入和更新

使用範例：
    # 註冊 2024-2026 年的所有月份合約
    python register_futures_contracts.py

    # 註冊指定年份範圍
    python register_futures_contracts.py --start-year 2024 --end-year 2027

    # 僅註冊 TX
    python register_futures_contracts.py --symbols TX
"""

import sys
import os
from pathlib import Path
from datetime import date
import argparse

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# QuantLab 模組
from app.core.config import settings
from app.db.base import import_models
from app.services.shioaji_client import get_third_wednesday

# 導入所有模型
import_models()

# 日誌配置
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)


def register_monthly_contracts(
    symbols: list,
    start_year: int,
    end_year: int,
    db_url: str = None
):
    """
    註冊期貨月份合約到資料庫

    Args:
        symbols: 期貨代碼列表（如 ['TX', 'MTX']）
        start_year: 開始年份
        end_year: 結束年份（包含）
        db_url: 資料庫連接字串（None 則使用環境變數）
    """
    db_url = db_url or str(settings.DATABASE_URL)
    engine = create_engine(db_url)

    logger.info(f"=" * 80)
    logger.info(f"註冊期貨月份合約")
    logger.info(f"期貨品種: {', '.join(symbols)}")
    logger.info(f"年份範圍: {start_year} ~ {end_year}")
    logger.info(f"=" * 80)

    contracts = []

    for symbol in symbols:
        symbol_name = {
            'TX': '台指期貨',
            'MTX': '小台指期貨'
        }.get(symbol, symbol)

        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                # 構造合約代碼（如 TX202512）
                contract_code = f"{symbol}{year:04d}{month:02d}"

                # 計算結算日
                settlement_date = get_third_wednesday(year, month)

                # 判斷是否已到期
                is_expired = date.today() > settlement_date
                status = 'inactive' if is_expired else 'active'

                contracts.append({
                    'stock_id': contract_code,
                    'name': f'{symbol_name} {year}-{month:02d} 合約',
                    'category': 'FUTURES_MONTHLY',
                    'market': 'FUTURES',
                    'is_active': status
                })

                logger.debug(f"  {contract_code}: {settlement_date} ({status})")

    logger.info(f"\n準備註冊 {len(contracts)} 個月份合約")

    # 批次插入資料庫（使用 executemany 提升性能）
    with engine.connect() as conn:
        insert_query = text("""
            INSERT INTO stocks (stock_id, name, category, market, is_active)
            VALUES (:stock_id, :name, :category, :market, :is_active)
            ON CONFLICT (stock_id) DO UPDATE SET
                name = EXCLUDED.name,
                category = EXCLUDED.category,
                market = EXCLUDED.market,
                is_active = EXCLUDED.is_active,
                updated_at = NOW()
        """)

        # 分批插入（每批 100 個，使用 executemany 提升性能）
        batch_size = 100
        total_inserted = 0

        for i in range(0, len(contracts), batch_size):
            batch = contracts[i:i+batch_size]

            # 使用 executemany 一次插入整批數據（比逐個執行快得多）
            conn.execute(insert_query, batch)

            conn.commit()
            total_inserted += len(batch)
            logger.info(f"  [REGISTER] Registered {total_inserted}/{len(contracts)} contracts")

    logger.info(f"\n[REGISTER] Successfully registered {len(contracts)} monthly contracts")

    # 驗證
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT category, COUNT(*) as count
            FROM stocks
            WHERE category = 'FUTURES_MONTHLY'
            GROUP BY category
        """))

        for row in result:
            logger.info(f"   {row.category}: {row.count} 個合約")

        # 顯示未到期合約
        result = conn.execute(text("""
            SELECT stock_id, name
            FROM stocks
            WHERE category = 'FUTURES_MONTHLY'
              AND is_active = 'active'
            ORDER BY stock_id
            LIMIT 10
        """))

        logger.info(f"\n未到期合約範例（前 10 個）：")
        for row in result:
            logger.info(f"  {row.stock_id}: {row.name}")


def main():
    parser = argparse.ArgumentParser(description='註冊期貨月份合約到資料庫')
    parser.add_argument('--symbols', type=str, default='TX,MTX',
                        help='期貨代碼（逗號分隔，默認: TX,MTX）')
    parser.add_argument('--start-year', type=int, default=2024,
                        help='開始年份（默認: 2024）')
    parser.add_argument('--end-year', type=int, default=2026,
                        help='結束年份（默認: 2026）')

    args = parser.parse_args()

    # 解析期貨代碼
    symbols = [s.strip() for s in args.symbols.split(',')]

    # 註冊合約
    register_monthly_contracts(
        symbols=symbols,
        start_year=args.start_year,
        end_year=args.end_year
    )

    logger.info("\n" + "=" * 80)
    logger.info("🎉 月份合約註冊完成")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
