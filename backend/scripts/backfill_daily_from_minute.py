#!/usr/bin/env python3
"""
從分鐘線資料聚合補齊日線資料

用途：當 FinLab API 斷線或日線資料缺失時，使用 Shioaji 分鐘線資料聚合成日線

限制：
1. 只能補齊有分鐘線資料的股票（目前約 2,317 檔）
2. PostgreSQL 分鐘線只保留最近 6 個月
3. Qlib 分鐘線保留最近 7 年

使用方式：
    # 🧠 智慧模式（推薦）：自動檢測分鐘線範圍內的所有缺失並補齊
    python scripts/backfill_daily_from_minute.py --smart

    # 智慧模式 + 預覽（不寫入）
    python scripts/backfill_daily_from_minute.py --smart --dry-run

    # 智慧模式 + 只檢查
    python scripts/backfill_daily_from_minute.py --smart --check

    # 補齊特定日期
    python scripts/backfill_daily_from_minute.py --date 2025-12-23

    # 補齊日期範圍
    python scripts/backfill_daily_from_minute.py --start 2025-12-20 --end 2025-12-23

    # 補齊最近 7 天的缺失
    python scripts/backfill_daily_from_minute.py --days 7

    # 檢查缺失（不補齊）
    python scripts/backfill_daily_from_minute.py --check
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from datetime import datetime, timedelta, date
from typing import List, Dict
from sqlalchemy import text

from app.db.session import SessionLocal
from app.utils.timezone_helpers import today_taiwan


def get_missing_dates(
    db, start_date: date, end_date: date
) -> List[date]:
    """
    找出指定範圍內缺失的交易日

    排除週末，但包含可能的補班日
    """
    query = text("""
        WITH date_series AS (
            SELECT generate_series(
                :start_date,
                :end_date,
                '1 day'::interval
            )::date AS date
        ),
        trading_days AS (
            SELECT DISTINCT date FROM stock_prices
            WHERE date BETWEEN :start_date AND :end_date
        )
        SELECT ds.date
        FROM date_series ds
        LEFT JOIN trading_days td ON ds.date = td.date
        WHERE td.date IS NULL
          AND EXTRACT(DOW FROM ds.date) NOT IN (0, 6)  -- 排除週末
        ORDER BY ds.date
    """)

    result = db.execute(query, {"start_date": start_date, "end_date": end_date})
    return [row[0] for row in result]


def check_minute_data_availability(
    db, check_date: date
) -> Dict[str, int]:
    """
    檢查特定日期的分鐘線資料可用性

    Returns:
        {
            'stocks_count': 有資料的股票數,
            'total_records': 總記錄數,
            'total_volume': 總成交量
        }
    """
    query = text("""
        SELECT
            COUNT(DISTINCT stock_id) as stocks_count,
            COUNT(*) as total_records,
            SUM(volume) as total_volume
        FROM stock_minute_prices
        WHERE datetime::date = :check_date
    """)

    result = db.execute(query, {"check_date": check_date}).fetchone()

    return {
        "stocks_count": result[0] or 0,
        "total_records": result[1] or 0,
        "total_volume": result[2] or 0,
    }


def aggregate_minute_to_daily(
    db, target_date: date, dry_run: bool = False
) -> Dict[str, int]:
    """
    從分鐘線聚合成日線資料

    聚合邏輯：
    - Open: 當天第一筆分鐘線的 open
    - High: 當天所有分鐘線的最高價
    - Low: 當天所有分鐘線的最低價
    - Close: 當天最後一筆分鐘線的 close
    - Volume: 當天所有分鐘線的 volume 總和

    Returns:
        {
            'inserted': 新增筆數,
            'updated': 更新筆數,
            'skipped': 跳過筆數
        }
    """
    # 聚合分鐘線資料
    query = text("""
        SELECT
            stock_id,
            (ARRAY_AGG(open ORDER BY datetime ASC))[1] as open,
            MAX(high) as high,
            MIN(low) as low,
            (ARRAY_AGG(close ORDER BY datetime DESC))[1] as close,
            SUM(volume) as volume
        FROM stock_minute_prices
        WHERE datetime::date = :target_date
        GROUP BY stock_id
    """)

    result = db.execute(query, {"target_date": target_date})
    aggregated_data = result.fetchall()

    if not aggregated_data:
        print(f"⚠️  {target_date}: 沒有分鐘線資料可聚合")
        return {"inserted": 0, "updated": 0, "skipped": 0}

    stats = {"inserted": 0, "updated": 0, "skipped": 0}

    for row in aggregated_data:
        stock_id, open_price, high, low, close, volume = row

        # 檢查是否已存在
        check_query = text("""
            SELECT COUNT(*) FROM stock_prices
            WHERE stock_id = :stock_id AND date = :target_date
        """)
        exists = db.execute(check_query, {
            "stock_id": stock_id,
            "target_date": target_date
        }).scalar()

        if exists:
            if dry_run:
                print(f"  [DRY-RUN] 更新: {stock_id} {target_date} O:{open_price} H:{high} L:{low} C:{close} V:{volume}")
            else:
                update_query = text("""
                    UPDATE stock_prices
                    SET open = :open, high = :high, low = :low, close = :close, volume = :volume
                    WHERE stock_id = :stock_id AND date = :target_date
                """)
                db.execute(update_query, {
                    "stock_id": stock_id,
                    "target_date": target_date,
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume
                })
            stats["updated"] += 1
        else:
            if dry_run:
                print(f"  [DRY-RUN] 新增: {stock_id} {target_date} O:{open_price} H:{high} L:{low} C:{close} V:{volume}")
            else:
                insert_query = text("""
                    INSERT INTO stock_prices (stock_id, date, open, high, low, close, volume)
                    VALUES (:stock_id, :target_date, :open, :high, :low, :close, :volume)
                """)
                db.execute(insert_query, {
                    "stock_id": stock_id,
                    "target_date": target_date,
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume
                })
            stats["inserted"] += 1

    if not dry_run:
        db.commit()
        print(f"✅ {target_date}: 新增 {stats['inserted']} 筆, 更新 {stats['updated']} 筆")
    else:
        print(f"[DRY-RUN] {target_date}: 將新增 {stats['inserted']} 筆, 更新 {stats['updated']} 筆")

    return stats


def get_minute_data_range(db) -> tuple:
    """
    獲取分鐘線資料的日期範圍

    Returns:
        (最早日期, 最晚日期) 或 (None, None)
    """
    query = text("""
        SELECT
            MIN(datetime::date) as min_date,
            MAX(datetime::date) as max_date
        FROM stock_minute_prices
    """)

    result = db.execute(query).fetchone()
    if result and result[0] and result[1]:
        return (result[0], result[1])
    return (None, None)


def main():
    parser = argparse.ArgumentParser(description="從分鐘線補齊日線資料")
    parser.add_argument("--smart", action="store_true", help="🧠 智慧模式：自動檢測分鐘線範圍內的所有缺失日線並補齊")
    parser.add_argument("--check", action="store_true", help="只檢查缺失，不補齊")
    parser.add_argument("--date", type=str, help="補齊特定日期 (YYYY-MM-DD)")
    parser.add_argument("--start", type=str, help="開始日期 (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="結束日期 (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, help="補齊最近 N 天的缺失")
    parser.add_argument("--dry-run", action="store_true", help="測試模式，不實際寫入")

    args = parser.parse_args()

    db = SessionLocal()

    try:
        # 確定日期範圍
        if args.smart:
            # 🧠 智慧模式：自動檢測分鐘線資料範圍
            print("\n🧠 智慧模式：自動檢測分鐘線資料範圍...")
            min_date, max_date = get_minute_data_range(db)

            if not min_date or not max_date:
                print("❌ 沒有分鐘線資料")
                return

            start_date = min_date
            end_date = max_date

            print(f"✅ 分鐘線資料範圍: {start_date} ~ {end_date}")
            print(f"   時間跨度: {(end_date - start_date).days} 天")

        elif args.date:
            start_date = end_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        elif args.start and args.end:
            start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
            end_date = datetime.strptime(args.end, "%Y-%m-%d").date()
        elif args.days:
            end_date = today_taiwan()
            start_date = end_date - timedelta(days=args.days)
        else:
            # 預設檢查最近 30 天
            end_date = today_taiwan()
            start_date = end_date - timedelta(days=30)

        print(f"\n📅 檢查日期範圍: {start_date} ~ {end_date}")
        print("=" * 60)

        # 找出缺失日期
        missing_dates = get_missing_dates(db, start_date, end_date)

        if not missing_dates:
            print("✅ 日期範圍內沒有缺失的日線資料")
            return

        print(f"\n⚠️  發現 {len(missing_dates)} 個缺失日期:\n")

        for missing_date in missing_dates:
            # 檢查分鐘線資料可用性
            availability = check_minute_data_availability(db, missing_date)

            status = "🟢" if availability["stocks_count"] > 100 else "🟡" if availability["stocks_count"] > 0 else "🔴"

            print(f"{status} {missing_date} ({missing_date.strftime('%A')}): "
                  f"{availability['stocks_count']:,} 檔股票, "
                  f"{availability['total_records']:,} 筆記錄, "
                  f"成交量 {availability['total_volume']:,}")

            # 如果不是只檢查模式，且有分鐘線資料，則進行補齊
            if not args.check and availability["stocks_count"] > 0:
                aggregate_minute_to_daily(db, missing_date, dry_run=args.dry_run)

        if args.check:
            print("\n💡 提示：")
            print("   --smart           🧠 智慧模式：自動檢測分鐘線範圍內的所有缺失（推薦）")
            print("   --date YYYY-MM-DD    補齊特定日期")
            print("   --start --end        補齊日期範圍")
            print("   --days N             補齊最近 N 天")
            print("   --dry-run            預覽模式（不實際寫入）")

        if args.dry_run:
            print("\n[DRY-RUN] 測試模式，未實際寫入資料庫")

    finally:
        db.close()


if __name__ == "__main__":
    main()
