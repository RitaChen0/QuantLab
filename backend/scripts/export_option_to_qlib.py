#!/usr/bin/env python3
"""
將選擇權因子匯出到 Qlib 格式

支援三階段演進式匯出：
- 階段一：3 個因子（pcr, pcr_oi, atm_iv）
- 階段二：+5 個因子（iv_skew, max_pain 等）
- 階段三：+10 個因子（Greeks 相關）

目錄結構：
    <output_dir>/
    ├── calendars/
    │   └── day.txt                     # 交易日曆
    └── features/
        └── <instrument>/                # 股票目錄（如 2330）
            ├── pcr.day.bin             # 階段一因子
            ├── pcr_oi.day.bin
            ├── atm_iv.day.bin
            ├── iv_skew.day.bin         # 階段二因子
            └── gamma_exp.day.bin       # 階段三因子

使用方式：
    # 匯出所有階段一因子（智慧增量）
    python export_option_to_qlib.py --output-dir /data/qlib/tw_stock_v2 --smart

    # 完整重新匯出
    python export_option_to_qlib.py --output-dir /data/qlib/tw_stock_v2

    # 測試模式（僅 TX）
    python export_option_to_qlib.py --output-dir /data/qlib/tw_stock_v2 --test
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple
import pandas as pd
import numpy as np
from loguru import logger

from sqlalchemy import create_engine, text
from app.core.config import settings

# Qlib imports
import qlib
from qlib.config import REG_CN
from qlib.data.storage.file_storage import FileFeatureStorage
from qlib.data import D

# 階段一因子映射
STAGE1_FACTORS = {
    'pcr_volume': 'pcr',           # Put/Call Ratio (成交量)
    'pcr_open_interest': 'pcr_oi', # Put/Call Ratio (未平倉量)
    'atm_iv': 'atm_iv',            # ATM 隱含波動率
}

# 階段二因子映射（預留）
STAGE2_FACTORS = {
    'iv_skew': 'iv_skew',
    'max_pain_strike': 'max_pain',
    'total_call_oi': 'call_oi',
    'total_put_oi': 'put_oi',
}

# 階段三因子映射（預留）
STAGE3_FACTORS = {
    'gamma_exposure': 'gamma_exp',
    'vanna_exposure': 'vanna_exp',
    'avg_call_delta': 'call_delta',
    'avg_put_delta': 'put_delta',
}


def get_db_engine():
    """建立資料庫連接"""
    return create_engine(settings.DATABASE_URL)


def get_current_stage(engine) -> int:
    """獲取當前階段"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT value FROM option_sync_config WHERE key = 'stage'
        """))
        row = result.fetchone()
        return int(row[0]) if row else 1


def get_enabled_underlyings(engine) -> List[str]:
    """獲取啟用的標的物列表"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT value FROM option_sync_config WHERE key = 'enabled_underlyings'
        """))
        row = result.fetchone()
        if row and row[0]:
            return [s.strip() for s in row[0].split(',')]
        return []


def get_available_factors(stage: int) -> dict:
    """
    獲取當前階段可用的因子

    Args:
        stage: 階段號（1/2/3）

    Returns:
        因子映射字典
    """
    factors = {}

    if stage >= 1:
        factors.update(STAGE1_FACTORS)

    if stage >= 2:
        factors.update(STAGE2_FACTORS)

    if stage >= 3:
        factors.update(STAGE3_FACTORS)

    return factors


def get_factor_data(
    engine,
    underlying_id: str,
    factor_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> pd.DataFrame:
    """
    從資料庫獲取因子數據

    Args:
        engine: 資料庫引擎
        underlying_id: 標的代碼
        factor_name: 因子名稱（資料庫欄位名）
        start_date: 開始日期
        end_date: 結束日期

    Returns:
        DataFrame with columns: [date, value]
    """
    query = f"""
        SELECT date, {factor_name}
        FROM option_daily_factors
        WHERE underlying_id = :underlying_id
          AND {factor_name} IS NOT NULL
    """

    params = {'underlying_id': underlying_id}

    if start_date:
        query += " AND date >= :start_date"
        params['start_date'] = start_date

    if end_date:
        query += " AND date <= :end_date"
        params['end_date'] = end_date

    query += " ORDER BY date ASC"

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params)

    if df.empty:
        return pd.DataFrame(columns=['date', 'value'])

    df = df.rename(columns={factor_name: 'value'})
    df['date'] = pd.to_datetime(df['date'])

    return df


def get_qlib_last_date(underlying_id: str, factor_field: str) -> Optional[date]:
    """
    獲取 Qlib 已有數據的最後日期

    Args:
        underlying_id: 標的代碼
        factor_field: Qlib 因子名稱（如 '$pcr'）

    Returns:
        最後日期或 None
    """
    try:
        df = D.features([underlying_id], [factor_field], freq='day')

        if df is None or df.empty:
            return None

        last_datetime = df.index.get_level_values('datetime').max()
        return last_datetime.date()
    except Exception:
        return None


def determine_sync_range(
    engine,
    underlying_id: str,
    factor_name: str,
    factor_field: str,
    smart_mode: bool = False
) -> Tuple[Optional[date], Optional[date], str]:
    """
    智慧判斷需要同步的日期範圍

    Args:
        engine: 資料庫引擎
        underlying_id: 標的代碼
        factor_name: 資料庫欄位名
        factor_field: Qlib 因子名
        smart_mode: 是否使用智慧模式

    Returns:
        (開始日期, 結束日期, 同步類型)
    """
    # 獲取資料庫日期範圍
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT MIN(date) as min_date, MAX(date) as max_date
            FROM option_daily_factors
            WHERE underlying_id = :underlying_id
              AND {factor_name} IS NOT NULL
        """.format(factor_name=factor_name)), {"underlying_id": underlying_id})
        row = result.fetchone()

        if not row or not row[0]:
            logger.warning(f"[QLIB] No data for {underlying_id} - {factor_name}")
            return (None, None, 'skip')

        db_min_date = row[0]
        db_max_date = row[1]

    if not smart_mode:
        # 完整重新匯出
        return (db_min_date, db_max_date, 'full')

    # 智慧模式：檢查 Qlib 最後日期
    qlib_last_date = get_qlib_last_date(underlying_id, f'${factor_field}')

    if qlib_last_date is None:
        # Qlib 無數據，完整匯出
        logger.info(f"[QLIB] {underlying_id} - {factor_field}: 首次匯出")
        return (db_min_date, db_max_date, 'full')

    if qlib_last_date >= db_max_date:
        # Qlib 已是最新
        logger.info(f"[QLIB] {underlying_id} - {factor_field}: 已是最新 ({qlib_last_date})")
        return (None, None, 'skip')

    # 增量匯出
    start_date = qlib_last_date + timedelta(days=1)
    logger.info(
        f"[QLIB] {underlying_id} - {factor_field}: "
        f"增量匯出 {start_date} -> {db_max_date}"
    )
    return (start_date, db_max_date, 'incremental')


def write_qlib_feature(
    instrument: str,
    field: str,
    freq: str,
    data: np.ndarray,
    dates: pd.DatetimeIndex
) -> bool:
    """
    寫入 Qlib 特徵

    Args:
        instrument: 股票代碼
        field: 特徵名稱
        freq: 頻率（'day'）
        data: numpy array
        dates: 日期索引

    Returns:
        是否成功
    """
    try:
        storage = FileFeatureStorage(
            instrument=instrument,
            field=field,
            freq=freq
        )

        # 確保數據類型正確
        data = np.asarray(data, dtype=np.float32)

        storage.write(data, index=dates)
        return True

    except Exception as e:
        logger.error(f"[QLIB] Failed to write {instrument}/{field}: {str(e)}")
        return False


def export_factor(
    engine,
    underlying_id: str,
    factor_name: str,
    factor_field: str,
    smart_mode: bool = False
) -> bool:
    """
    匯出單一因子

    Args:
        engine: 資料庫引擎
        underlying_id: 標的代碼
        factor_name: 資料庫欄位名
        factor_field: Qlib 因子名
        smart_mode: 智慧增量模式

    Returns:
        是否成功
    """
    # 判斷同步範圍
    start_date, end_date, sync_type = determine_sync_range(
        engine,
        underlying_id,
        factor_name,
        factor_field,
        smart_mode
    )

    if sync_type == 'skip':
        return True

    # 獲取因子數據
    df = get_factor_data(engine, underlying_id, factor_name, start_date, end_date)

    if df.empty:
        logger.warning(f"[QLIB] No data to export for {underlying_id} - {factor_field}")
        return False

    # 轉換為 numpy array
    dates = pd.DatetimeIndex(df['date'])
    values = df['value'].values.astype(np.float32)

    # 寫入 Qlib
    success = write_qlib_feature(
        instrument=underlying_id,
        field=factor_field,
        freq='day',
        data=values,
        dates=dates
    )

    if success:
        logger.info(
            f"[QLIB] ✅ Exported {underlying_id}/{factor_field}: "
            f"{len(df)} records ({sync_type})"
        )
    else:
        logger.error(f"[QLIB] ❌ Failed to export {underlying_id}/{factor_field}")

    return success


def export_option_factors_to_qlib(
    output_dir: str,
    smart_mode: bool = False,
    test_mode: bool = False
):
    """
    匯出選擇權因子到 Qlib

    Args:
        output_dir: Qlib 資料目錄
        smart_mode: 智慧增量模式
        test_mode: 測試模式（僅 TX）
    """
    logger.info("=" * 60)
    logger.info("選擇權因子匯出到 Qlib")
    logger.info("=" * 60)

    # 初始化 Qlib
    qlib.init(provider_uri=output_dir, region=REG_CN)
    logger.info(f"[QLIB] Initialized: {output_dir}")

    # 獲取資料庫連接
    engine = get_db_engine()

    # 獲取當前階段
    stage = get_current_stage(engine)
    logger.info(f"[QLIB] Current stage: {stage}")

    # 獲取可用因子
    factors = get_available_factors(stage)
    logger.info(f"[QLIB] Available factors: {list(factors.values())}")

    # 獲取標的物列表
    if test_mode:
        underlyings = ['TX']
        logger.info("[QLIB] Test mode: only TX")
    else:
        underlyings = get_enabled_underlyings(engine)
        if not underlyings:
            underlyings = ['TX', 'MTX']
        logger.info(f"[QLIB] Underlyings: {underlyings}")

    # 統計
    stats = {
        'total_underlyings': len(underlyings),
        'total_factors': len(factors),
        'success_count': 0,
        'error_count': 0,
        'skip_count': 0,
    }

    # 逐個標的物匯出
    for underlying_id in underlyings:
        logger.info(f"\n[QLIB] Processing {underlying_id}...")

        for db_field, qlib_field in factors.items():
            try:
                success = export_factor(
                    engine,
                    underlying_id,
                    db_field,
                    qlib_field,
                    smart_mode
                )

                if success:
                    stats['success_count'] += 1
                else:
                    stats['skip_count'] += 1

            except Exception as e:
                logger.error(
                    f"[QLIB] Error exporting {underlying_id}/{qlib_field}: {str(e)}"
                )
                stats['error_count'] += 1

    # 總結
    logger.info("")
    logger.info("=" * 60)
    logger.info("匯出結果總結")
    logger.info("=" * 60)
    logger.info(f"標的物數量: {stats['total_underlyings']}")
    logger.info(f"因子數量: {stats['total_factors']}")
    logger.info(f"成功匯出: {stats['success_count']}")
    logger.info(f"跳過: {stats['skip_count']}")
    logger.info(f"錯誤: {stats['error_count']}")

    total_expected = stats['total_underlyings'] * stats['total_factors']
    success_rate = stats['success_count'] / total_expected * 100 if total_expected > 0 else 0

    logger.info(f"成功率: {success_rate:.1f}%")

    if stats['error_count'] == 0:
        logger.info("🎉 所有因子匯出成功！")
    else:
        logger.warning(f"⚠️  {stats['error_count']} 個因子匯出失敗")


def main():
    parser = argparse.ArgumentParser(description='匯出選擇權因子到 Qlib')
    parser.add_argument(
        '--output-dir',
        type=str,
        default='/data/qlib/tw_stock_v2',
        help='Qlib 資料目錄（預設: /data/qlib/tw_stock_v2）'
    )
    parser.add_argument(
        '--smart',
        action='store_true',
        help='智慧增量匯出（只更新新數據）'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='測試模式（僅 TX）'
    )

    args = parser.parse_args()

    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Smart mode: {args.smart}")
    logger.info(f"Test mode: {args.test}")
    logger.info("")

    export_option_factors_to_qlib(
        output_dir=args.output_dir,
        smart_mode=args.smart,
        test_mode=args.test
    )


if __name__ == '__main__':
    main()
