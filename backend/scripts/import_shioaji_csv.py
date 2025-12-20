#!/usr/bin/env python3
"""
Shioaji CSV 資料匯入腳本

將 ShioajiData/shioaji-stock/ 下的 CSV 檔案批次匯入到 PostgreSQL + TimescaleDB

使用範例：
    # 測試匯入 10 檔股票
    python scripts/import_shioaji_csv.py --limit 10

    # 匯入指定股票
    python scripts/import_shioaji_csv.py --stocks 2330,2317,2454

    # 匯入最近 1 年資料
    python scripts/import_shioaji_csv.py --start-date 2024-01-01

    # 完整匯入所有資料
    python scripts/import_shioaji_csv.py --batch-size 50000
"""
import sys
import os
from pathlib import Path

# 將專案根目錄加入 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import pandas as pd
from datetime import datetime, timezone
from typing import List, Optional
from loguru import logger
from tqdm import tqdm
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import import_models
from app.repositories.stock_minute_price import StockMinutePriceRepository
from app.schemas.stock_minute_price import StockMinutePriceCreate

# 導入所有模型以避免 ORM mapper 錯誤
import_models()

# 創建專用於導入的 Session（關閉 SQL echo 避免日誌膨脹）
engine_silent = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,  # 關閉 SQL 日誌記錄
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_silent)


# 預設資料路徑（容器內掛載點）
# Docker volume: ./ShioajiData:/data/shioaji
DEFAULT_DATA_DIR = "/data/shioaji/shioaji-stock"

# 熱門股票清單（市值前 50 大）
TOP_50_STOCKS = [
    '2330', '2317', '2454', '2412', '3008',  # 台積電、鴻海、聯發科、中華電、大立光
    '2308', '2882', '1301', '1303', '2002',  # 台達電、國泰金、台塑、南亞、中鋼
    '2886', '2881', '2891', '2892', '2885',  # 兆豐金、富邦金、中信金、第一金、元大金
    '2884', '2887', '2883', '5880', '2912',  # 玉山金、台新金、開發金、合庫金、統一超
    '2880', '2382', '2395', '6505', '3045',  # 華南金、廣達、研華、台塑化、台灣大
    '1216', '2357', '1326', '2303', '2379',  # 統一、華碩、台化、聯電、瑞昱
    '2408', '2207', '2327', '3711', '2474',  # 南亞科、和泰車、國巨、日月光投控、可成
    '2801', '2609', '2615', '2603', '4904',  # 彰銀、陽明、萬海、長榮、遠傳
    '9910', '2888', '2345', '6669', '2409',  # 豐泰、新光金、智邦、緯穎、友達
    '3037', '2377', '2353', '5871', '2324',  # 欣興、微星、宏碁、中租-KY、仁寶
]


def _process_dataframe(
    df: pd.DataFrame,
    stock_id: str,
    start_date: Optional[str],
    end_date: Optional[str]
) -> pd.DataFrame:
    """
    處理 DataFrame：清理、驗證、過濾

    Args:
        df: 原始 DataFrame
        stock_id: 股票代碼
        start_date: 起始日期
        end_date: 結束日期

    Returns:
        處理後的 DataFrame
    """
    # 1. 重命名欄位
    df = df.rename(columns={
        'ts': 'datetime',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume',
        'Amount': 'amount'
    })

    # 2. 轉換時間格式
    df['datetime'] = pd.to_datetime(df['datetime'])

    # 3. 時間範圍過濾
    if start_date:
        start_dt = pd.to_datetime(start_date)
        # 增量模式：使用 > 避免重複最後一筆記錄
        df = df[df['datetime'] > start_dt]

    if end_date:
        end_dt = pd.to_datetime(end_date)
        df = df[df['datetime'] <= end_dt]

    # 4. 過濾無效資料
    # 移除 OHLC 全為 0 的記錄
    df = df[~((df['open'] == 0) & (df['high'] == 0) & (df['low'] == 0) & (df['close'] == 0))]

    # 移除負數價格
    df = df[(df['open'] > 0) & (df['high'] > 0) & (df['low'] > 0) & (df['close'] > 0)]

    # 移除 OHLC 邏輯錯誤的記錄
    df = df[
        (df['high'] >= df['low']) &
        (df['high'] >= df['open']) &
        (df['high'] >= df['close']) &
        (df['low'] <= df['open']) &
        (df['low'] <= df['close'])
    ]

    # 5. 新增欄位
    df['stock_id'] = stock_id
    df['timeframe'] = '1min'

    return df


def _import_csv_chunked(
    csv_path: Path,
    db: Session,
    stock_id: str,
    repo,
    batch_size: int,
    start_date: Optional[str],
    end_date: Optional[str],
    chunk_size: int,
    result: dict
) -> dict:
    """
    使用分塊讀取匯入 CSV（記憶體友善）

    Args:
        csv_path: CSV 檔案路徑
        db: 資料庫會話
        stock_id: 股票代碼
        repo: Repository
        batch_size: 插入批次大小
        start_date: 起始日期
        end_date: 結束日期
        chunk_size: CSV 讀取分塊大小
        result: 結果字典

    Returns:
        更新後的結果字典
    """
    try:
        logger.debug(f"{stock_id}: Using chunked reading (chunk_size={chunk_size})")

        for chunk in pd.read_csv(csv_path, chunksize=chunk_size):
            result["total_rows"] += len(chunk)

            # 處理分塊資料
            df = _process_dataframe(chunk, stock_id, start_date, end_date)

            if df.empty:
                result["skipped"] += len(chunk)
                continue

            # 批次插入
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]

                # 轉換為 Pydantic Schema
                records = []
                for _, row in batch.iterrows():
                    try:
                        record = StockMinutePriceCreate(
                            stock_id=row['stock_id'],
                            datetime=row['datetime'],
                            timeframe=row['timeframe'],
                            open=float(row['open']),
                            high=float(row['high']),
                            low=float(row['low']),
                            close=float(row['close']),
                            volume=int(row['volume']) if row['volume'] > 0 else 0
                        )
                        records.append(record)
                    except Exception as e:
                        logger.debug(f"{stock_id}: Failed to parse row: {str(e)}")
                        result["errors"] += 1
                        continue

                # 批次插入
                if records:
                    try:
                        inserted = repo.create_bulk(db, records)
                        result["inserted"] += inserted
                    except Exception as e:
                        logger.warning(f"{stock_id}: Bulk insert failed, trying upsert - {str(e)}")
                        for record in records:
                            try:
                                repo.upsert(db, record.stock_id, record.datetime, record.timeframe, record)
                                result["inserted"] += 1
                            except Exception as e2:
                                logger.debug(f"{stock_id}: Upsert failed: {str(e2)}")
                                result["errors"] += 1

        result["skipped"] = result["total_rows"] - result["inserted"] - result["errors"]

        logger.info(
            f"✅ {stock_id}: Inserted {result['inserted']:,}/{result['total_rows']:,} records "
            f"(errors: {result['errors']}, skipped: {result['skipped']})"
        )

    except Exception as e:
        logger.error(f"❌ {stock_id}: Chunked import failed - {str(e)}")
        result["status"] = "failed"
        result["errors"] += 1

    return result


def import_csv_file(
    csv_path: Path,
    db: Session,
    batch_size: int = 10000,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    incremental: bool = False,
    use_chunks: bool = False,
    chunk_size: int = 50000
) -> dict:
    """
    匯入單一 CSV 檔案

    Args:
        csv_path: CSV 檔案路徑
        db: 資料庫會話（由呼叫者管理）
        batch_size: 批次大小（預設 10000）
        start_date: 起始日期（僅匯入此日期之後的資料）
        end_date: 結束日期（僅匯入此日期之前的資料）
        incremental: 是否增量匯入（檢查資料庫已有資料）
        use_chunks: 是否使用分塊讀取（降低記憶體使用）
        chunk_size: 分塊大小（預設 50000）

    Returns:
        dict: {
            "stock_id": str,
            "total_rows": int,
            "inserted": int,
            "skipped": int,
            "errors": int,
            "status": "success" | "failed"
        }
    """
    stock_id = csv_path.stem  # 檔名即為股票代碼
    repo = StockMinutePriceRepository

    result = {
        "stock_id": stock_id,
        "total_rows": 0,
        "inserted": 0,
        "skipped": 0,
        "errors": 0,
        "status": "success"
    }

    try:
        # 1. 檢查增量匯入的起始日期
        if incremental:
            latest = repo.get_latest(db, stock_id, '1min')
            if latest:
                start_date = latest.datetime.strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"{stock_id}: Incremental import from {start_date}")

        # 2. 讀取 CSV
        logger.debug(f"{stock_id}: Reading CSV file...")

        if use_chunks:
            # 使用分塊讀取（記憶體友善）
            return _import_csv_chunked(
                csv_path, db, stock_id, repo, batch_size,
                start_date, end_date, chunk_size, result
            )

        # 標準讀取（一次性載入）
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            logger.error(f"{stock_id}: Failed to read CSV - {str(e)}")
            result["status"] = "failed"
            result["errors"] = 1
            return result

        result["total_rows"] = len(df)

        # 3. 處理資料（清理、驗證、過濾）
        df = _process_dataframe(df, stock_id, start_date, end_date)

        if df.empty:
            if incremental:
                logger.info(f"{stock_id}: ✅ Already up-to-date, no new data")
            else:
                logger.warning(f"{stock_id}: No valid data after filtering")
            result["status"] = "success"
            result["skipped"] = result["total_rows"]
            return result

        # 4. 批次插入
        logger.debug(f"{stock_id}: Inserting {len(df):,} records...")

        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]

            # 轉換為 Pydantic Schema
            records = []
            for _, row in batch.iterrows():
                try:
                    record = StockMinutePriceCreate(
                        stock_id=row['stock_id'],
                        datetime=row['datetime'],
                        timeframe=row['timeframe'],
                        open=float(row['open']),
                        high=float(row['high']),
                        low=float(row['low']),
                        close=float(row['close']),
                        volume=int(row['volume']) if row['volume'] > 0 else 0
                    )
                    records.append(record)
                except Exception as e:
                    logger.debug(f"{stock_id}: Failed to parse row at {row['datetime']}: {str(e)}")
                    result["errors"] += 1
                    continue

            # 批次插入（使用 upsert 避免重複）
            if records:
                try:
                    # 使用 bulk insert（速度較快）
                    inserted = repo.create_bulk(db, records)
                    result["inserted"] += inserted
                except Exception as e:
                    # 如果批次插入失敗，嘗試逐筆 upsert
                    logger.warning(f"{stock_id}: Bulk insert failed, trying upsert - {str(e)}")
                    # 🔧 Rollback before trying individual upserts
                    db.rollback()
                    for record in records:
                        try:
                            repo.upsert(
                                db,
                                record.stock_id,
                                record.datetime,
                                record.timeframe,
                                record
                            )
                            result["inserted"] += 1
                        except Exception as e2:
                            logger.debug(f"{stock_id}: Upsert failed at {record.datetime}: {str(e2)}")
                            result["errors"] += 1

        result["skipped"] = result["total_rows"] - result["inserted"] - result["errors"]

        logger.info(
            f"✅ {stock_id}: Inserted {result['inserted']:,}/{result['total_rows']:,} records "
            f"(errors: {result['errors']}, skipped: {result['skipped']})"
        )

    except Exception as e:
        logger.error(f"❌ {stock_id}: Import failed - {str(e)}")
        result["status"] = "failed"
        result["errors"] += 1
        # 🔧 Rollback session to allow subsequent imports to continue
        db.rollback()

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Import Shioaji CSV data to PostgreSQL + TimescaleDB',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 測試匯入 10 檔股票
  python scripts/import_shioaji_csv.py --limit 10

  # 匯入市值前 50 大股票
  python scripts/import_shioaji_csv.py --top50

  # 匯入指定股票
  python scripts/import_shioaji_csv.py --stocks 2330,2317,2454

  # 匯入最近 1 年資料
  python scripts/import_shioaji_csv.py --start-date 2024-01-01

  # 增量匯入（僅匯入新資料）
  python scripts/import_shioaji_csv.py --incremental

  # 完整匯入所有資料（高效能）
  python scripts/import_shioaji_csv.py --batch-size 50000
        """
    )

    parser.add_argument(
        '--data-dir',
        default=DEFAULT_DATA_DIR,
        help=f'Path to shioaji-stock directory (default: {DEFAULT_DATA_DIR})'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10000,
        help='Batch size for insert (default: 10000, recommended: 50000 for full import)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of stocks to import (for testing)'
    )
    parser.add_argument(
        '--stocks',
        help='Comma-separated stock IDs to import (e.g., 2330,2317,2454)'
    )
    parser.add_argument(
        '--top50',
        action='store_true',
        help='Import top 50 stocks by market cap'
    )
    parser.add_argument(
        '--start-date',
        help='Start date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS), only import data after this date'
    )
    parser.add_argument(
        '--end-date',
        help='End date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS), only import data before this date'
    )
    parser.add_argument(
        '--incremental',
        action='store_true',
        help='Incremental import (only import new data after existing records)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging (debug level)'
    )
    parser.add_argument(
        '--use-chunks',
        action='store_true',
        help='Use chunked reading for large CSV files (reduces memory usage)'
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=50000,
        help='Chunk size for chunked reading (default: 50000)'
    )

    args = parser.parse_args()

    # 設定日誌級別
    if args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.remove()
        logger.add(sys.stderr, level="INFO")

    # 檢查資料目錄
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        logger.error(f"❌ Data directory not found: {data_dir}")
        logger.error(f"Please check the path or create symbolic link:")
        logger.error(f"  ln -s /path/to/ShioajiData /home/ubuntu/QuantLab/ShioajiData")
        sys.exit(1)

    # 獲取所有 CSV 檔案
    csv_files = sorted(data_dir.glob('*.csv'))

    if not csv_files:
        logger.error(f"❌ No CSV files found in {data_dir}")
        sys.exit(1)

    logger.info(f"📁 Found {len(csv_files)} CSV files in {data_dir}")

    # 過濾指定股票
    if args.top50:
        logger.info(f"🔥 Filtering top 50 stocks by market cap...")
        csv_files = [f for f in csv_files if f.stem in TOP_50_STOCKS]
        logger.info(f"📊 Selected {len(csv_files)} stocks")

    elif args.stocks:
        stock_ids = [s.strip() for s in args.stocks.split(',')]
        logger.info(f"🎯 Filtering specified stocks: {stock_ids}")
        csv_files = [f for f in csv_files if f.stem in stock_ids]
        logger.info(f"📊 Selected {len(csv_files)} stocks")

    # 限制數量（測試用）
    if args.limit:
        csv_files = csv_files[:args.limit]
        logger.info(f"🧪 Test mode: Limited to first {args.limit} stocks")

    # 統計資訊
    total_stocks = len(csv_files)
    total_rows = 0
    total_inserted = 0
    total_skipped = 0
    total_errors = 0
    failed_stocks = []
    success_stocks = []

    # 顯示匯入設定
    logger.info(f"\n{'='*60}")
    logger.info(f"🚀 Import Configuration:")
    logger.info(f"  Total stocks: {total_stocks}")
    logger.info(f"  Batch size: {args.batch_size:,}")
    logger.info(f"  Start date: {args.start_date or 'All'}")
    logger.info(f"  End date: {args.end_date or 'All'}")
    logger.info(f"  Incremental: {args.incremental}")
    logger.info(f"{'='*60}\n")

    # 開始匯入
    start_time = datetime.now(timezone.utc)

    # 建立共用資料庫連線
    db = SessionLocal()

    try:
        for csv_file in tqdm(csv_files, desc="Importing stocks", unit="stock"):
            try:
                result = import_csv_file(
                    csv_file,
                    db,
                    args.batch_size,
                    args.start_date,
                    args.end_date,
                    args.incremental,
                    args.use_chunks,
                    args.chunk_size
                )

                total_rows += result["total_rows"]
                total_inserted += result["inserted"]
                total_skipped += result["skipped"]
                total_errors += result["errors"]

                if result["status"] == "success":
                    success_stocks.append(result["stock_id"])
                else:
                    failed_stocks.append(result["stock_id"])

            except Exception as e:
                logger.error(f"❌ Failed to import {csv_file.stem}: {str(e)}")
                failed_stocks.append(csv_file.stem)
                continue

    finally:
        # 確保資料庫連線正確關閉
        db.close()

    # 計算執行時間
    end_time = datetime.now(timezone.utc)
    elapsed = end_time - start_time
    elapsed_minutes = elapsed.total_seconds() / 60

    # 總結報告
    logger.info(f"\n{'='*60}")
    logger.info(f"✅ Import Completed!")
    logger.info(f"{'='*60}")
    logger.info(f"📊 Statistics:")
    logger.info(f"  Total stocks processed: {total_stocks}")
    logger.info(f"  Successful: {len(success_stocks)}")
    logger.info(f"  Failed: {len(failed_stocks)}")
    logger.info(f"\n📈 Data:")
    logger.info(f"  Total rows read: {total_rows:,}")
    logger.info(f"  Records inserted: {total_inserted:,}")
    logger.info(f"  Records skipped: {total_skipped:,}")
    logger.info(f"  Errors: {total_errors:,}")
    logger.info(f"\n⏱️  Performance:")
    logger.info(f"  Elapsed time: {elapsed_minutes:.1f} minutes")
    logger.info(f"  Average speed: {total_inserted / elapsed.total_seconds():.0f} records/second")

    if failed_stocks:
        logger.warning(f"\n⚠️  Failed stocks ({len(failed_stocks)}):")
        logger.warning(f"  {', '.join(failed_stocks[:10])}")
        if len(failed_stocks) > 10:
            logger.warning(f"  ... and {len(failed_stocks) - 10} more")

    logger.info(f"{'='*60}\n")

    # 驗證建議
    logger.info(f"💡 Next steps:")
    logger.info(f"  1. Verify data:")
    logger.info(f"     docker compose exec postgres psql -U quantlab quantlab -c \"SELECT COUNT(*) FROM stock_minute_prices;\"")
    logger.info(f"\n  2. Check specific stock:")
    logger.info(f"     docker compose exec postgres psql -U quantlab quantlab -c \"SELECT COUNT(*), MIN(datetime), MAX(datetime) FROM stock_minute_prices WHERE stock_id = '2330';\"")
    logger.info(f"\n  3. Test API:")
    logger.info(f"     curl http://localhost:8000/api/v1/intraday/coverage/2330?timeframe=1min")


if __name__ == '__main__':
    main()
