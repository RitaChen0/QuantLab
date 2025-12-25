#!/usr/bin/env python3
"""
從 TX 期貨分鐘線聚合生成日線數據並寫入 Qlib 格式

用途：為 RD-Agent 提供完整的 TX 期貨 OHLCV 日線數據

數據來源：PostgreSQL stock_minute_prices 表（TX202512 月份合約）
輸出格式：Qlib v2 binary format
輸出位置：/data/qlib/tw_stock_v2/features/tx/

使用方式：
    # 聚合並寫入（預設使用 TX202512）
    python scripts/generate_tx_daily_from_minute.py

    # 使用連續合約（TXCONT）
    python scripts/generate_tx_daily_from_minute.py --contract TXCONT

    # 僅預覽（不寫入）
    python scripts/generate_tx_daily_from_minute.py --dry-run

    # 從 Docker 執行
    docker compose exec backend python /app/scripts/generate_tx_daily_from_minute.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import numpy as np
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
from loguru import logger

from app.core.config import settings


def aggregate_tx_daily(contract: str = 'TX202512', dry_run: bool = False):
    """
    從分鐘線聚合 TX 期貨日線數據

    Args:
        contract: 期貨合約代碼（TX202512, TX202601, TXCONT 等）
        dry_run: 僅預覽，不寫入檔案

    Returns:
        DataFrame: 聚合的日線數據
    """
    logger.info("=" * 80)
    logger.info("🚀 TX 期貨日線數據聚合")
    logger.info("=" * 80)
    logger.info(f"📊 期貨合約：{contract}")
    logger.info(f"🔧 模式：{'預覽模式（不寫入）' if dry_run else '正式模式（寫入 Qlib）'}")

    # 連接資料庫
    db_url = settings.DATABASE_URL
    engine = create_engine(db_url)

    # 查詢合約數據範圍
    range_query = text("""
        SELECT
            MIN(datetime::date) as earliest,
            MAX(datetime::date) as latest,
            COUNT(DISTINCT datetime::date) as trading_days,
            COUNT(*) as total_bars
        FROM stock_minute_prices
        WHERE stock_id = :contract
    """)

    with engine.connect() as conn:
        range_result = conn.execute(range_query, {"contract": contract}).fetchone()

    if not range_result or not range_result[0]:
        logger.error(f"❌ 找不到合約 {contract} 的分鐘線數據")
        logger.info("💡 提示：請檢查合約代碼是否正確，或先同步分鐘線數據")
        return None

    earliest, latest, trading_days, total_bars = range_result
    logger.info(f"📅 數據範圍：{earliest} ~ {latest}")
    logger.info(f"📈 交易日數：{trading_days} 天")
    logger.info(f"📊 分鐘線數：{total_bars:,} 筆")

    if trading_days < 60:
        logger.warning(f"⚠️  交易日數較少（{trading_days} < 60），可能影響 RD-Agent 因子測試準確性")

    # 聚合日線數據（OHLCV）
    logger.info("")
    logger.info("🔄 開始聚合日線數據...")

    agg_query = text("""
        SELECT
            datetime::date as date,
            (ARRAY_AGG(open ORDER BY datetime ASC))[1] as open,
            MAX(high) as high,
            MIN(low) as low,
            (ARRAY_AGG(close ORDER BY datetime DESC))[1] as close,
            SUM(volume) as volume
        FROM stock_minute_prices
        WHERE stock_id = :contract
        GROUP BY datetime::date
        ORDER BY date
    """)

    logger.info(f"📊 執行聚合 SQL...")
    df = pd.read_sql(agg_query, engine, params={"contract": contract}, index_col='date')

    if df.empty:
        logger.error(f"❌ 聚合結果為空")
        return None

    logger.info(f"✅ 聚合完成：{len(df)} 個交易日")
    logger.info("")
    logger.info("📊 聚合數據預覽（前 5 天）：")
    logger.info(f"\n{df.head(5).to_string()}")
    logger.info("")
    logger.info("📊 聚合數據預覽（最後 5 天）：")
    logger.info(f"\n{df.tail(5).to_string()}")

    # 數據品質檢查
    logger.info("")
    logger.info("🔍 數據品質檢查...")

    null_counts = df.isnull().sum()
    if null_counts.any():
        logger.warning("⚠️  發現缺失值：")
        for field, count in null_counts.items():
            if count > 0:
                logger.warning(f"   {field}: {count} 筆缺失")
    else:
        logger.info("✅ 無缺失值")

    # 檢查異常值（價格為 0 或負數）
    invalid_price = (df[['open', 'high', 'low', 'close']] <= 0).any(axis=1).sum()
    if invalid_price > 0:
        logger.warning(f"⚠️  發現 {invalid_price} 天有異常價格（<= 0）")
    else:
        logger.info("✅ 價格數據正常（> 0）")

    # 檢查 high >= low
    invalid_range = (df['high'] < df['low']).sum()
    if invalid_range > 0:
        logger.warning(f"⚠️  發現 {invalid_range} 天 high < low（異常）")
    else:
        logger.info("✅ 高低價關係正常（high >= low）")

    if dry_run:
        logger.info("")
        logger.info("=" * 80)
        logger.info("🔍 預覽模式完成（未寫入檔案）")
        logger.info("=" * 80)
        logger.info("💡 提示：移除 --dry-run 參數以寫入 Qlib 格式")
        return df

    # 寫入 Qlib 格式
    logger.info("")
    logger.info("=" * 80)
    logger.info("📝 寫入 Qlib 格式...")
    logger.info("=" * 80)

    output_dir = "/data/qlib/tw_stock_v2"
    instrument = "tx"

    logger.info(f"📂 輸出目錄：{output_dir}")
    logger.info(f"📊 標的代碼：{instrument}")

    # 確保目錄存在
    features_dir = Path(output_dir) / "features" / instrument
    features_dir.mkdir(parents=True, exist_ok=True)

    # 初始化 Qlib（必須）
    try:
        import qlib
        qlib.init(provider_uri=output_dir, region='tw')
        logger.info("   ✅ Qlib 已初始化")
    except Exception as e:
        logger.error(f"   ❌ Qlib 初始化失敗：{e}")
        raise

    # 讀取交易日曆
    logger.info("   📅 讀取交易日曆...")
    calendar_file = Path(output_dir) / "calendars" / "day.txt"
    if not calendar_file.exists():
        logger.error(f"   ❌ 交易日曆不存在：{calendar_file}")
        raise FileNotFoundError(f"Calendar file not found: {calendar_file}")

    with open(calendar_file, 'r') as f:
        trading_dates = [pd.to_datetime(line.strip()).date() for line in f if line.strip()]

    logger.info(f"   ✅ 交易日曆：{len(trading_dates)} 天（{trading_dates[0]} ~ {trading_dates[-1]}）")

    # 將數據對齊到完整交易日曆（關鍵步驟！）
    logger.info("   🔄 對齊數據到交易日曆...")
    df_aligned = df.reindex(trading_dates)
    logger.info(f"   ✅ 對齊完成：{len(df_aligned)} 天（含空值）")

    # 寫入 Qlib 二進制格式（包含開始索引）
    try:
        fields = ['open', 'high', 'low', 'close', 'volume']

        for field in fields:
            logger.info(f"   📝 寫入 {field}.day.bin...")

            # 構建檔案路徑
            file_path = features_dir / f"{field}.day.bin"

            # 寫入數據（轉為 float32，允許 NaN）
            data = df_aligned[field].values.astype(np.float32)

            # 寫入 Qlib 二進制格式（包含開始索引）
            # 格式：[start_index (float32)] + [data array (float32)]
            with open(file_path, 'wb') as f:
                # 寫入開始索引（0 表示從第一天開始）
                np.array([0], dtype='<f').tofile(f)
                # 寫入數據
                data.astype('<f').tofile(f)

            logger.info(f"      ✅ 完成（{len(data)} 筆，{file_path.stat().st_size / 1024:.1f} KB）")

        # 寫入 factor.day.bin（調整因子，通常為 1.0）
        logger.info(f"   📝 寫入 factor.day.bin...")
        file_path = features_dir / "factor.day.bin"
        factor_data = np.ones(len(df_aligned), dtype=np.float32)
        with open(file_path, 'wb') as f:
            # 寫入開始索引
            np.array([0], dtype='<f').tofile(f)
            # 寫入數據
            factor_data.astype('<f').tofile(f)
        logger.info(f"      ✅ 完成（{len(factor_data)} 筆，{file_path.stat().st_size / 1024:.1f} KB）")

    except Exception as e:
        logger.error(f"❌ 寫入 Qlib 格式失敗：{e}")
        logger.error("💡 提示：確認已安裝 qlib 套件並有寫入權限")
        raise

    logger.info("")
    logger.info("=" * 80)
    logger.info("✅ TX 期貨日線數據生成完成")
    logger.info("=" * 80)
    logger.info(f"📊 合約：{contract}")
    logger.info(f"📅 日期範圍：{earliest} ~ {latest}")
    logger.info(f"📈 交易日數：{len(df)} 天")
    logger.info(f"📂 輸出位置：{features_dir}")
    logger.info("")
    logger.info("📋 生成的檔案：")
    for field in fields + ['factor']:
        file_path = features_dir / f"{field}.day.bin"
        if file_path.exists():
            size_kb = file_path.stat().st_size / 1024
            logger.info(f"   ✅ {field}.day.bin ({size_kb:.1f} KB)")
        else:
            logger.warning(f"   ❌ {field}.day.bin（未找到）")

    logger.info("")
    logger.info("💡 下一步：")
    logger.info("   1. 驗證數據：ls -lh /data/qlib/tw_stock_v2/features/tx/")
    logger.info("   2. 測試 Qlib 讀取")
    logger.info("   3. 執行 RD-Agent 因子挖掘")

    return df


def main():
    """主程式"""
    parser = argparse.ArgumentParser(
        description="從 TX 期貨分鐘線聚合生成日線數據",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例：
  # 使用預設合約（TX202512）
  python scripts/generate_tx_daily_from_minute.py

  # 使用連續合約
  python scripts/generate_tx_daily_from_minute.py --contract TXCONT

  # 僅預覽
  python scripts/generate_tx_daily_from_minute.py --dry-run
        """
    )

    parser.add_argument(
        '--contract',
        type=str,
        default='TX202512',
        help='期貨合約代碼（預設：TX202512）'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='僅預覽，不寫入檔案'
    )

    args = parser.parse_args()

    try:
        df = aggregate_tx_daily(
            contract=args.contract,
            dry_run=args.dry_run
        )

        if df is not None and not args.dry_run:
            logger.info("🎉 成功！TX 期貨日線數據已就緒，可供 RD-Agent 使用。")
            sys.exit(0)
        elif df is not None and args.dry_run:
            logger.info("🔍 預覽完成")
            sys.exit(0)
        else:
            logger.error("❌ 失敗")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ 執行失敗：{e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
