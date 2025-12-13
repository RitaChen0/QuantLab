#!/usr/bin/env python3
"""
將 PostgreSQL 分鐘線數據轉換為 Qlib 格式

功能：
1. 從 stock_minute_prices 表讀取分鐘線數據
2. 轉換為 Qlib 官方格式（FileFeatureStorage API）
3. 支援智慧增量同步
4. 比從 Shioaji API 下載快 10-100 倍

使用範例：
    # 🧠 智慧增量轉換（推薦）
    python export_minute_to_qlib.py --output-dir /data/qlib/tw_stock_minute --smart

    # 完整轉換所有數據
    python export_minute_to_qlib.py --output-dir /data/qlib/tw_stock_minute --stocks all

    # 測試模式（僅轉換 10 檔）
    python export_minute_to_qlib.py --output-dir /data/qlib/tw_stock_minute --test
"""

import sys
import os
from pathlib import Path
from datetime import datetime, date, timedelta, time as dt_time
from typing import List, Optional, Tuple
import argparse

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from loguru import logger
from tqdm import tqdm
from sqlalchemy import create_engine, text

from app.core.config import settings

# Qlib 模組
import qlib
from qlib.config import REG_CN
from qlib.data.storage.file_storage import FileFeatureStorage
from qlib.data import D

# Qlib 特徵列表（分鐘線）
QLIB_MINUTE_FEATURES = ['open', 'high', 'low', 'close', 'volume']

# 日誌配置
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)
logger.add(
    "/tmp/export_minute_to_qlib_{time}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG"
)


def get_db_engine():
    """建立資料庫連接"""
    return create_engine(settings.DATABASE_URL)


def get_all_stock_ids(engine) -> List[str]:
    """獲取所有有分鐘線數據的股票代碼"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT stock_id
            FROM stock_minute_prices
            ORDER BY stock_id
        """))
        return [row[0] for row in result.fetchall()]


def get_all_trading_minutes(engine) -> pd.DatetimeIndex:
    """獲取所有交易分鐘"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT datetime
            FROM stock_minute_prices
            ORDER BY datetime ASC
        """))
        datetimes = [row[0] for row in result.fetchall()]
        return pd.DatetimeIndex(datetimes)


def get_db_date_range(engine, stock_id: str) -> Tuple[Optional[date], Optional[date]]:
    """獲取資料庫中該股票的日期範圍"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT MIN(datetime::date) as min_date, MAX(datetime::date) as max_date
            FROM stock_minute_prices
            WHERE stock_id = :stock_id
        """), {"stock_id": stock_id})
        row = result.fetchone()
        if row and row[0] and row[1]:
            return (row[0], row[1])
        return (None, None)


def get_qlib_last_date(stock_id: str) -> Optional[date]:
    """獲取 Qlib 中該股票的最後日期"""
    try:
        df = D.features([stock_id], ['$close'], freq='1min')
        if df is None or df.empty:
            return None
        last_datetime = df.index.get_level_values('datetime').max()
        return last_datetime.date()
    except Exception:
        return None


def determine_sync_range(
    engine,
    stock_id: str,
    smart_mode: bool = False
) -> Tuple[Optional[date], Optional[date], str]:
    """
    智慧判斷需要同步的日期範圍

    Returns:
        (開始日期, 結束日期, 同步類型)
        同步類型: 'full', 'incremental', 'skip'
    """
    # 獲取資料庫日期範圍
    db_min_date, db_max_date = get_db_date_range(engine, stock_id)

    if not db_min_date or not db_max_date:
        return (None, None, 'skip')

    # 非智慧模式，完整同步
    if not smart_mode:
        return (db_min_date, db_max_date, 'full')

    # 檢查 Qlib 已有數據
    qlib_last_date = get_qlib_last_date(stock_id)

    if not qlib_last_date:
        # 首次轉換，完整同步
        return (db_min_date, db_max_date, 'full')

    # 檢查是否有新數據
    if qlib_last_date >= db_max_date:
        # 已是最新，跳過
        return (None, None, 'skip')

    # 增量同步（從 Qlib 最後日期的下一天開始）
    incremental_start = qlib_last_date + timedelta(days=1)
    return (incremental_start, db_max_date, 'incremental')


def create_calendar_file(output_dir: Path, trading_minutes: pd.DatetimeIndex):
    """建立 Qlib 交易分鐘日曆檔案"""
    cal_file = output_dir / 'calendars' / '1min.txt'
    cal_file.parent.mkdir(parents=True, exist_ok=True)

    with open(cal_file, 'w') as f:
        for dt in trading_minutes:
            f.write(dt.strftime('%Y-%m-%d %H:%M:%S') + '\n')

    logger.info(f"✅ 交易分鐘日曆: {len(trading_minutes)} 個交易分鐘")
    logger.info(f"   範圍: {trading_minutes[0]} 至 {trading_minutes[-1]}")


def fetch_stock_minute_data(
    engine,
    stock_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> pd.DataFrame:
    """從資料庫獲取股票分鐘數據"""
    query = """
        SELECT
            datetime,
            open,
            high,
            low,
            close,
            volume
        FROM stock_minute_prices
        WHERE stock_id = :stock_id
    """

    params = {'stock_id': stock_id}

    if start_date:
        query += " AND datetime::date >= :start_date"
        params['start_date'] = start_date

    if end_date:
        query += " AND datetime::date <= :end_date"
        params['end_date'] = end_date

    query += " ORDER BY datetime ASC"

    df = pd.read_sql(text(query), engine, params=params)

    # 處理缺失值
    if not df.empty:
        df = df.ffill().bfill()

    return df


def export_stock_to_qlib(
    stock_id: str,
    df: pd.DataFrame,
    trading_minutes: pd.DatetimeIndex
):
    """使用 Qlib FileFeatureStorage 導出股票數據"""
    instrument = stock_id.lower()

    # 將 DataFrame 對齊到完整交易分鐘索引
    df = df.set_index('datetime')
    df = df.reindex(trading_minutes)

    # 為每個特徵寫入數據
    for field in QLIB_MINUTE_FEATURES:
        if field not in df.columns:
            continue

        # 提取特徵數據
        data = df[field].values.astype(np.float32)

        # 使用 FileFeatureStorage 寫入
        storage = FileFeatureStorage(
            instrument=instrument,
            field=field,
            freq="1min"
        )

        try:
            storage.write(data)
        except Exception as e:
            logger.warning(f"  ⚠️  {field}: 寫入失敗 - {e}")
            continue


def main():
    parser = argparse.ArgumentParser(
        description='將 PostgreSQL 分鐘線數據轉換為 Qlib 格式',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例用法:
  # 🧠 智慧增量轉換（推薦）
  python export_minute_to_qlib.py --output-dir /data/qlib/tw_stock_minute --smart

  # 完整轉換所有數據
  python export_minute_to_qlib.py --output-dir /data/qlib/tw_stock_minute --stocks all

  # 測試模式（僅轉換 10 檔）
  python export_minute_to_qlib.py --output-dir /data/qlib/tw_stock_minute --test
        """
    )

    parser.add_argument('--output-dir', type=str, required=True, help='Qlib 數據輸出目錄')
    parser.add_argument('--stocks', type=str, default='all', help='股票代碼（逗號分隔）或 "all"')
    parser.add_argument('--smart', action='store_true', help='🧠 智慧模式：自動增量同步')
    parser.add_argument('--test', action='store_true', help='測試模式（僅處理前 10 檔）')
    parser.add_argument('--limit', type=int, help='限制處理數量')

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 建立資料庫連接
    logger.info("=== 連接資料庫 ===")
    engine = get_db_engine()

    # 初始化 Qlib
    logger.info("\n=== 初始化 Qlib ===")
    qlib.init(provider_uri=str(output_dir), region=REG_CN)
    logger.info(f"✅ Qlib 已初始化: {output_dir}")

    # 獲取交易分鐘日曆
    logger.info("\n=== 建立交易分鐘日曆 ===")
    trading_minutes = get_all_trading_minutes(engine)
    create_calendar_file(output_dir, trading_minutes)

    # 獲取股票列表
    logger.info("\n=== 準備股票列表 ===")
    if args.stocks == 'all':
        stock_ids = get_all_stock_ids(engine)
    else:
        stock_ids = [s.strip() for s in args.stocks.split(',')]

    if args.test:
        stock_ids = stock_ids[:10]
        logger.warning(f"⚠️  測試模式：僅處理前 {len(stock_ids)} 檔")

    if args.limit:
        stock_ids = stock_ids[:args.limit]
        logger.warning(f"⚠️  限制處理：{args.limit} 檔")

    logger.info(f"共 {len(stock_ids)} 檔股票")

    if args.smart:
        logger.info(f"🧠 智慧模式：啟用增量同步")

    # 建立 features 目錄結構
    logger.info("\n=== 建立目錄結構 ===")
    for stock_id in stock_ids:
        instrument = stock_id.lower()
        features_dir = output_dir / 'features' / instrument
        features_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"✅ 已建立 {len(stock_ids)} 個股票目錄")

    # 導出每檔股票
    logger.info("\n=== 開始轉換數據 ===")
    full_count = 0
    incremental_count = 0
    skip_count = 0
    error_count = 0

    progress_bar = tqdm(stock_ids, desc="轉換進度", unit="檔")

    for stock_id in progress_bar:
        progress_bar.set_description(f"轉換 {stock_id}")

        try:
            # 判斷同步範圍
            start_date, end_date, sync_type = determine_sync_range(
                engine, stock_id, smart_mode=args.smart
            )

            # 跳過已是最新的股票
            if sync_type == 'skip':
                skip_count += 1
                continue

            # 獲取數據
            df = fetch_stock_minute_data(engine, stock_id, start_date, end_date)

            if df.empty:
                logger.warning(f"  ⚠️  {stock_id}: 無數據")
                skip_count += 1
                continue

            # 顯示同步資訊
            if sync_type == 'full':
                logger.info(f"  📦 {stock_id}: 完整轉換 {len(df)} 筆 ({start_date} ~ {end_date})")
                full_count += 1
            elif sync_type == 'incremental':
                logger.info(f"  ➕ {stock_id}: 增量轉換 {len(df)} 筆 ({start_date} ~ {end_date})")
                incremental_count += 1

            # 導出到 Qlib
            export_stock_to_qlib(stock_id, df, trading_minutes)

        except Exception as e:
            logger.error(f"  ❌ {stock_id}: 失敗 - {str(e)}")
            error_count += 1
            continue

    # 總結
    logger.info(f"\n{'='*60}")
    logger.info("=== 轉換完成 ===")
    logger.info(f"📦 完整轉換: {full_count} 檔")
    logger.info(f"➕ 增量轉換: {incremental_count} 檔")
    logger.info(f"⏭️  跳過: {skip_count} 檔")
    logger.info(f"✅ 成功: {full_count + incremental_count} 檔")
    if error_count > 0:
        logger.info(f"❌ 失敗: {error_count} 檔")
    logger.info(f"📁 輸出目錄: {output_dir}")

    # 驗證數據
    logger.info("\n=== 驗證數據 ===")
    test_stock = stock_ids[0] if stock_ids else None
    if test_stock:
        try:
            df_test = D.features(
                [test_stock],
                ['$close', '$volume'],
                freq='1min'
            )
            logger.info(f"✅ 驗證成功: {test_stock}")
            logger.info(f"   Shape: {df_test.shape}")
            if not df_test.empty:
                logger.info(f"   範圍: {df_test.index.get_level_values('datetime').min()} 至 {df_test.index.get_level_values('datetime').max()}")
        except Exception as e:
            logger.error(f"❌ 驗證失敗: {e}")


if __name__ == '__main__':
    main()
