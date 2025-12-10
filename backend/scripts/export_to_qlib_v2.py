#!/usr/bin/env python3
"""
將 QuantLab 股票歷史數據轉換為 Qlib 官方格式（v2 + 智慧同步）

使用 Qlib 官方 FileFeatureStorage API 確保格式完全正確
支援智慧增量同步，自動判斷需要更新的日期範圍

目錄結構：
    <output_dir>/
    ├── calendars/
    │   └── day.txt                     # 交易日曆
    └── features/
        └── <instrument>/                # 股票目錄（小寫）
            ├── open.day.bin
            ├── high.day.bin
            ├── low.day.bin
            ├── close.day.bin
            ├── volume.day.bin
            └── factor.day.bin

使用方式：
    # 🧠 智慧同步（推薦）：自動增量更新
    python export_to_qlib_v2.py --output-dir /data/qlib/tw_stock_v2 --stocks all --smart

    # 完整重新導出
    python export_to_qlib_v2.py --output-dir /data/qlib/tw_stock_v2 --stocks all

    # 測試模式
    python export_to_qlib_v2.py --output-dir /data/qlib/tw_stock_v2 --stocks 2330,2317 --test --smart
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from app.core.config import settings

# Qlib imports
import qlib
from qlib.config import REG_CN
from qlib.data.storage.file_storage import FileFeatureStorage
from qlib.data import D

# Qlib 特徵列表
QLIB_FEATURES = ['open', 'high', 'low', 'close', 'volume', 'factor']


def get_db_engine():
    """建立資料庫連接"""
    return create_engine(settings.DATABASE_URL)


def get_all_stock_ids(engine) -> List[str]:
    """獲取所有股票代碼"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT stock_id
            FROM stock_prices
            ORDER BY stock_id
        """))
        return [row[0] for row in result.fetchall()]


def get_all_trading_dates(engine) -> List[date]:
    """獲取所有交易日期"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT date
            FROM stock_prices
            ORDER BY date ASC
        """))
        return [row[0] for row in result.fetchall()]


def get_db_date_range(engine, stock_id: str) -> Tuple[Optional[date], Optional[date]]:
    """
    獲取資料庫中該股票的日期範圍

    Args:
        engine: 資料庫引擎
        stock_id: 股票代碼

    Returns:
        (最早日期, 最新日期) 或 (None, None) 如果無數據
    """
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT MIN(date) as min_date, MAX(date) as max_date
            FROM stock_prices
            WHERE stock_id = :stock_id
        """), {"stock_id": stock_id})
        row = result.fetchone()
        if row and row[0] and row[1]:
            return (row[0], row[1])
        return (None, None)


def get_qlib_last_date(stock_id: str) -> Optional[date]:
    """
    使用 Qlib API 獲取已有數據的最後日期

    Args:
        stock_id: 股票代碼

    Returns:
        最後日期或 None（如果尚未匯出）
    """
    try:
        # 嘗試讀取該股票的數據
        df = D.features([stock_id], ['$close'], freq='day')

        if df is None or df.empty:
            return None

        # 獲取最後一個日期
        last_datetime = df.index.get_level_values('datetime').max()
        return last_datetime.date()
    except Exception:
        # 如果讀取失敗，表示數據不存在
        return None


def determine_sync_range(
    engine,
    stock_id: str,
    smart_mode: bool = False
) -> Tuple[Optional[date], Optional[date], str]:
    """
    智慧判斷需要同步的日期範圍

    Args:
        engine: 資料庫引擎
        stock_id: 股票代碼
        smart_mode: 是否使用智慧模式

    Returns:
        (開始日期, 結束日期, 同步類型)
        同步類型: 'full', 'incremental', 'skip'
    """
    # 獲取資料庫日期範圍
    db_min_date, db_max_date = get_db_date_range(engine, stock_id)

    if not db_min_date or not db_max_date:
        return (None, None, 'skip')  # 資料庫無數據

    # 非智慧模式，完整同步
    if not smart_mode:
        return (db_min_date, db_max_date, 'full')

    # 檢查 Qlib 已有數據
    qlib_last_date = get_qlib_last_date(stock_id)

    if not qlib_last_date:
        # 首次匯出，完整同步
        return (db_min_date, db_max_date, 'full')

    # 檢查是否有新數據
    if qlib_last_date >= db_max_date:
        # 已是最新，跳過
        return (None, None, 'skip')

    # 增量同步（從 Qlib 最後日期的下一天開始）
    incremental_start = qlib_last_date + timedelta(days=1)
    return (incremental_start, db_max_date, 'incremental')


def create_calendar_file(output_dir: Path, trading_dates: List[date]):
    """
    建立 Qlib 交易日曆檔案

    Args:
        output_dir: 輸出目錄
        trading_dates: 交易日期列表
    """
    cal_file = output_dir / 'calendars' / 'day.txt'
    cal_file.parent.mkdir(parents=True, exist_ok=True)

    with open(cal_file, 'w') as f:
        for d in trading_dates:
            f.write(d.strftime('%Y-%m-%d') + '\n')

    print(f"✅ 交易日曆: {len(trading_dates)} 個交易日")
    print(f"   範圍: {trading_dates[0]} 至 {trading_dates[-1]}")


def fetch_stock_data(
    engine,
    stock_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> pd.DataFrame:
    """
    從資料庫獲取股票數據（支援日期範圍篩選）

    Args:
        engine: 資料庫引擎
        stock_id: 股票代碼
        start_date: 開始日期（可選）
        end_date: 結束日期（可選）

    Returns:
        包含 OHLCV 數據的 DataFrame
    """
    query = """
        SELECT
            date,
            open,
            high,
            low,
            close,
            volume,
            COALESCE(adj_close / close, 1.0) as factor
        FROM stock_prices
        WHERE stock_id = :stock_id
    """

    params = {'stock_id': stock_id}

    if start_date:
        query += " AND date >= :start_date"
        params['start_date'] = start_date

    if end_date:
        query += " AND date <= :end_date"
        params['end_date'] = end_date

    query += " ORDER BY date ASC"

    df = pd.read_sql(text(query), engine, params=params)

    # 處理缺失值（使用新的 pandas 語法）
    if not df.empty:
        df = df.ffill().bfill()

    return df


def export_stock_to_qlib(
    stock_id: str,
    df: pd.DataFrame,
    trading_dates: List[date]
):
    """
    使用 Qlib FileFeatureStorage 導出股票數據

    Args:
        stock_id: 股票代碼
        df: 股票數據 DataFrame
        trading_dates: 完整交易日曆
    """
    # 確保股票代碼為小寫（Qlib 要求）
    instrument = stock_id.lower()

    # 將 DataFrame 對齊到完整交易日曆
    df = df.set_index('date')
    df = df.reindex(trading_dates)

    # 為每個特徵寫入數據
    for field in QLIB_FEATURES:
        if field not in df.columns:
            continue

        # 提取特徵數據
        data = df[field].values.astype(np.float32)

        # 使用 FileFeatureStorage 寫入
        storage = FileFeatureStorage(
            instrument=instrument,
            field=field,
            freq="day"
        )

        try:
            storage.write(data)
        except Exception as e:
            print(f"  ⚠️  {field}: 寫入失敗 - {e}")
            continue

    print(f"  ✓ {stock_id}: {len(df)} 個交易日")


def main():
    parser = argparse.ArgumentParser(description='導出股票數據到 Qlib 格式（v2 + 智慧同步）')
    parser.add_argument('--output-dir', type=str, required=True, help='Qlib 數據輸出目錄')
    parser.add_argument('--stocks', type=str, default='all', help='股票代碼（逗號分隔）或 "all"')
    parser.add_argument('--smart', action='store_true', help='🧠 智慧模式：自動增量同步')
    parser.add_argument('--test', action='store_true', help='測試模式（僅處理前 5 檔）')
    parser.add_argument('--limit', type=int, help='限制處理數量（用於測試）')

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 建立資料庫連接
    print("=== 連接資料庫 ===")
    engine = get_db_engine()

    # 獲取交易日曆
    print("\n=== 建立交易日曆 ===")
    trading_dates = get_all_trading_dates(engine)
    create_calendar_file(output_dir, trading_dates)

    # 初始化 Qlib
    print("\n=== 初始化 Qlib ===")
    qlib.init(provider_uri=str(output_dir), region=REG_CN)
    print(f"✅ Qlib 已初始化: {output_dir}")

    # 獲取股票列表
    print("\n=== 準備股票列表 ===")
    if args.stocks == 'all':
        stock_ids = get_all_stock_ids(engine)
    else:
        stock_ids = [s.strip() for s in args.stocks.split(',')]

    if args.test:
        stock_ids = stock_ids[:5]
        print(f"⚠️  測試模式：僅處理前 {len(stock_ids)} 檔")

    if args.limit:
        stock_ids = stock_ids[:args.limit]
        print(f"⚠️  限制處理：{args.limit} 檔")

    print(f"共 {len(stock_ids)} 檔股票")

    if args.smart:
        print(f"🧠 智慧模式：啟用增量同步")

    # 建立 features 目錄結構
    print("\n=== 建立目錄結構 ===")
    for stock_id in stock_ids:
        instrument = stock_id.lower()
        features_dir = output_dir / 'features' / instrument
        features_dir.mkdir(parents=True, exist_ok=True)

    print(f"✅ 已建立 {len(stock_ids)} 個股票目錄")

    # 導出每檔股票（智慧同步）
    print("\n=== 開始導出數據 ===")
    full_count = 0
    incremental_count = 0
    skip_count = 0
    error_count = 0

    for idx, stock_id in enumerate(stock_ids, 1):
        try:
            # 判斷同步範圍
            start_date, end_date, sync_type = determine_sync_range(
                engine, stock_id, smart_mode=args.smart
            )

            # 跳過已是最新的股票
            if sync_type == 'skip':
                skip_count += 1
                if idx % 50 == 0:  # 每 50 檔顯示一次跳過
                    print(f"  ⏭️  {stock_id}: 已是最新，跳過")
                continue

            # 獲取數據（支援日期範圍）
            df = fetch_stock_data(engine, stock_id, start_date, end_date)

            if df.empty:
                print(f"  ⚠️  {stock_id}: 無數據")
                skip_count += 1
                continue

            # 顯示同步資訊
            if sync_type == 'full':
                print(f"  📦 {stock_id}: 完整同步 {len(df)} 筆 ({start_date} ~ {end_date})")
                full_count += 1
            elif sync_type == 'incremental':
                print(f"  ➕ {stock_id}: 增量同步 {len(df)} 筆 ({start_date} ~ {end_date})")
                incremental_count += 1

            # 導出到 Qlib
            export_stock_to_qlib(stock_id, df, trading_dates)

            # 進度報告
            if idx % 100 == 0:
                total_synced = full_count + incremental_count
                print(f"\n📊 進度: {idx}/{len(stock_ids)} ({idx/len(stock_ids)*100:.1f}%)")
                print(f"   完整: {full_count}, 增量: {incremental_count}, 跳過: {skip_count}\n")

        except Exception as e:
            print(f"  ❌ {stock_id}: 失敗 - {str(e)}")
            error_count += 1
            continue

    # 總結
    print("\n" + "="*60)
    print("=== 導出完成 ===")
    print(f"📦 完整同步: {full_count} 檔")
    print(f"➕ 增量同步: {incremental_count} 檔")
    print(f"⏭️  跳過: {skip_count} 檔")
    print(f"✅ 成功: {full_count + incremental_count} 檔")
    if error_count > 0:
        print(f"❌ 失敗: {error_count} 檔")
    print(f"📁 輸出目錄: {output_dir}")

    # 驗證數據
    print("\n=== 驗證數據 ===")
    from qlib.data import D

    test_stock = stock_ids[0] if stock_ids else None
    if test_stock:
        try:
            df_test = D.features(
                [test_stock],
                ['$close', '$open'],
                start_time=str(trading_dates[0]),
                end_time=str(trading_dates[-1]),
                freq='day'
            )
            print(f"✅ 驗證成功: {test_stock}")
            print(f"   Shape: {df_test.shape}")
            if not df_test.empty:
                print(f"   範圍: {df_test.index.get_level_values('datetime').min()} 至 {df_test.index.get_level_values('datetime').max()}")
        except Exception as e:
            print(f"❌ 驗證失敗: {e}")


if __name__ == '__main__':
    main()
