#!/usr/bin/env python3
"""
將 QuantLab 股票歷史數據轉換為 Qlib 格式

Qlib 數據格式：
- 使用二進制 bin 文件存儲
- 每個股票、每個特徵分別存儲
- 目錄結構：data/qlib/tw_stock/instruments/{stock_id}.{feature}.bin
- 特徵：open, high, low, close, volume, adj_close

使用方式：
    python export_to_qlib.py --output-dir /path/to/qlib/data --stocks all
    python export_to_qlib.py --output-dir /path/to/qlib/data --stocks 2330,2317
    python export_to_qlib.py --output-dir /path/to/qlib/data --start-date 2020-01-01
"""

import sys
import os
import argparse
import struct
from pathlib import Path
from datetime import datetime, date, timedelta, timezone
from typing import List, Optional, Tuple
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from app.core.config import settings

# Qlib 特徵列表
QLIB_FEATURES = ['open', 'high', 'low', 'close', 'volume', 'adj_close']


def get_db_engine():
    """建立資料庫連接"""
    return create_engine(settings.DATABASE_URL)


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


def get_qlib_last_date(output_dir: Path, stock_id: str) -> Optional[date]:
    """
    獲取 Qlib 已有數據的最後日期

    Args:
        output_dir: Qlib 輸出目錄
        stock_id: 股票代碼

    Returns:
        最後日期或 None（如果尚未匯出）
    """
    dates_file = output_dir / 'instruments' / f'{stock_id}.dates.txt'

    if not dates_file.exists():
        return None

    try:
        with open(dates_file, 'r') as f:
            dates = [line.strip() for line in f if line.strip()]

        if dates:
            last_date_str = dates[-1]
            return datetime.strptime(last_date_str, '%Y-%m-%d').date()
    except Exception:
        return None

    return None


def determine_sync_range(
    engine,
    output_dir: Path,
    stock_id: str,
    force_full: bool = False
) -> Tuple[Optional[date], Optional[date], str]:
    """
    智慧判斷需要同步的日期範圍

    Args:
        engine: 資料庫引擎
        output_dir: Qlib 輸出目錄
        stock_id: 股票代碼
        force_full: 是否強制完整同步

    Returns:
        (開始日期, 結束日期, 同步類型)
        同步類型: 'full', 'incremental', 'skip'
    """
    # 獲取資料庫日期範圍
    db_min_date, db_max_date = get_db_date_range(engine, stock_id)

    if not db_min_date or not db_max_date:
        return (None, None, 'skip')  # 資料庫無數據

    # 強制完整同步
    if force_full:
        return (db_min_date, db_max_date, 'full')

    # 檢查 Qlib 已有數據
    qlib_last_date = get_qlib_last_date(output_dir, stock_id)

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


def get_stock_list(engine, stock_ids: Optional[List[str]] = None) -> List[str]:
    """
    獲取要轉換的股票列表

    Args:
        engine: 資料庫引擎
        stock_ids: 指定的股票代碼列表，None 表示全部

    Returns:
        股票代碼列表
    """
    if stock_ids:
        return stock_ids

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT stock_id
            FROM stock_prices
            ORDER BY stock_id
        """))
        return [row[0] for row in result.fetchall()]


def fetch_stock_data(
    engine,
    stock_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> pd.DataFrame:
    """
    從資料庫獲取股票數據

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
            adj_close
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

    # 處理 adj_close 為 NULL 的情況（使用 close 代替）
    if 'adj_close' in df.columns:
        df['adj_close'] = df['adj_close'].fillna(df['close'])

    return df


def write_qlib_bin(data: np.ndarray, output_path: Path, append: bool = False):
    """
    將數據寫入 Qlib 二進制格式

    Qlib bin 格式：
    - 每個數值使用 float32（4 bytes）
    - 按日期順序排列

    Args:
        data: numpy array（1D）
        output_path: 輸出檔案路徑
        append: 是否附加到現有檔案（True）或覆蓋（False）
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 轉換為 float32
    data_float32 = data.astype(np.float32)

    # 寫入二進制檔案（附加或覆蓋）
    mode = 'ab' if append else 'wb'
    with open(output_path, mode) as f:
        f.write(data_float32.tobytes())

    action = "附加" if append else "寫入"
    print(f"  ✓ {action} {output_path.name}: {len(data)} 筆記錄")


def export_stock_to_qlib(
    engine,
    stock_id: str,
    output_dir: Path,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    append: bool = False
):
    """
    將單一股票的數據轉換為 Qlib 格式

    Args:
        engine: 資料庫引擎
        stock_id: 股票代碼
        output_dir: 輸出目錄
        start_date: 開始日期
        end_date: 結束日期
        append: 是否附加到現有檔案（增量更新）
    """
    print(f"\n📊 處理股票: {stock_id}")

    # 獲取數據
    df = fetch_stock_data(engine, stock_id, start_date, end_date)

    if df.empty:
        print(f"  ⚠️  無數據")
        return

    print(f"  數據範圍: {df['date'].min()} ~ {df['date'].max()} ({len(df)} 筆)")

    # 建立輸出目錄
    instruments_dir = output_dir / 'instruments'
    instruments_dir.mkdir(parents=True, exist_ok=True)

    # 為每個特徵寫入 bin 文件
    for feature in QLIB_FEATURES:
        if feature not in df.columns:
            print(f"  ⚠️  缺少特徵: {feature}")
            continue

        # 獲取數據（處理 NaN）
        data = df[feature].values
        data = np.nan_to_num(data, nan=0.0)

        # 寫入 bin 文件（附加或覆蓋）
        output_path = instruments_dir / f"{stock_id}.{feature}.bin"
        write_qlib_bin(data, output_path, append)

    # 寫入日期索引檔案（附加或覆蓋）
    dates_path = instruments_dir / f"{stock_id}.dates.txt"
    mode = 'a' if append else 'w'
    with open(dates_path, mode) as f:
        for date_val in df['date']:
            f.write(f"{date_val}\n")

    action = "附加" if append else "寫入"
    print(f"  ✓ {action} {dates_path.name}: {len(df)} 個日期")


def create_qlib_metadata(output_dir: Path, stock_list: List[str]):
    """
    建立 Qlib 元數據檔案

    Args:
        output_dir: 輸出目錄
        stock_list: 股票列表
    """
    print("\n📝 建立元數據...")

    # 建立 instruments 清單
    instruments_file = output_dir / 'instruments' / 'all.txt'
    with open(instruments_file, 'w') as f:
        for stock_id in stock_list:
            f.write(f"{stock_id}\n")

    print(f"  ✓ 股票清單: {instruments_file} ({len(stock_list)} 檔)")

    # 建立 README
    readme_file = output_dir / 'README.md'
    with open(readme_file, 'w') as f:
        f.write(f"""# QuantLab → Qlib 數據轉換結果

## 數據資訊

- **轉換時間**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}
- **股票數量**: {len(stock_list)}
- **數據來源**: QuantLab PostgreSQL + TimescaleDB
- **市場**: 台灣股市 (TWSE/TPEX)

## 數據格式

- **特徵**: {', '.join(QLIB_FEATURES)}
- **檔案格式**: Binary (.bin) + 日期索引 (.dates.txt)
- **數值型別**: float32 (4 bytes per value)

## 目錄結構

```
{output_dir.name}/
├── instruments/
│   ├── all.txt              # 所有股票清單
│   ├── 2330.open.bin        # 台積電開盤價
│   ├── 2330.high.bin        # 台積電最高價
│   ├── 2330.low.bin         # 台積電最低價
│   ├── 2330.close.bin       # 台積電收盤價
│   ├── 2330.volume.bin      # 台積電成交量
│   ├── 2330.adj_close.bin   # 台積電調整收盤價
│   ├── 2330.dates.txt       # 台積電日期索引
│   └── ...
└── README.md
```

## 使用方式

### 1. 在 Qlib 中載入數據

```python
from qlib.data import LocalProvider

# 設定數據路徑
provider = LocalProvider(uri='{output_dir.absolute()}')

# 載入數據
data = provider.get_features(
    instruments=['2330', '2317'],
    fields=['open', 'high', 'low', 'close', 'volume'],
    start_time='2020-01-01',
    end_time='2024-12-31'
)
```

### 2. 使用 Qlib 內建載入器

```python
import qlib

# 初始化 Qlib
qlib.init(
    provider_uri='{output_dir.absolute()}',
    region='tw'
)

# 使用 Qlib API
from qlib.data import D

data = D.features(
    instruments=['2330'],
    fields=['$close', '$volume'],
    start_time='2020-01-01',
    end_time='2024-12-31'
)
```

## 注意事項

1. **調整收盤價**: 若原始數據無 `adj_close`，自動使用 `close` 代替
2. **缺失值處理**: NaN 值已轉換為 0.0
3. **日期格式**: 使用 YYYY-MM-DD 格式
4. **數值精度**: 使用 float32（節省空間，符合 Qlib 標準）

## 數據來源

- **FinLab API**: 台股歷史 OHLCV 數據
- **資料庫**: PostgreSQL 15 + TimescaleDB
- **更新頻率**: 每日收盤後同步

## 轉換工具

- **腳本**: `backend/scripts/export_to_qlib.py`
- **執行**: `python export_to_qlib.py --help`
""")

    print(f"  ✓ 說明文件: {readme_file}")


def main():
    parser = argparse.ArgumentParser(
        description='將 QuantLab 股票數據轉換為 Qlib 格式',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 🧠 智慧同步（推薦）：自動判斷需要同步的日期範圍
  python export_to_qlib.py --output-dir /data/qlib/tw_stock_v2 --stocks all --smart

  # 首次完整匯出
  python export_to_qlib.py --output-dir /data/qlib/tw_stock_v2 --stocks all

  # 強制完整重新同步
  python export_to_qlib.py --output-dir /data/qlib/tw_stock_v2 --stocks all --force-full

  # 轉換特定股票（智慧模式）
  python export_to_qlib.py --output-dir /data/qlib/tw_stock_v2 --stocks 2330,2317,2454 --smart

  # 手動指定日期範圍
  python export_to_qlib.py --output-dir /data/qlib/tw_stock_v2 --start-date 2020-01-01 --end-date 2024-12-31

  # 測試模式（僅轉換 10 檔，智慧同步）
  python export_to_qlib.py --output-dir /tmp/qlib_test --stocks all --limit 10 --smart
        """
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        required=True,
        help='Qlib 數據輸出目錄'
    )

    parser.add_argument(
        '--stocks',
        type=str,
        default='all',
        help='股票代碼（逗號分隔），或 "all" 表示全部（預設: all）'
    )

    parser.add_argument(
        '--start-date',
        type=str,
        help='開始日期 (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--end-date',
        type=str,
        help='結束日期 (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--limit',
        type=int,
        help='限制轉換股票數量（用於測試）'
    )

    parser.add_argument(
        '--smart',
        action='store_true',
        help='智慧同步模式：自動判斷需要同步的日期範圍（增量更新）'
    )

    parser.add_argument(
        '--force-full',
        action='store_true',
        help='強制完整同步（即使已有數據也重新匯出）'
    )

    args = parser.parse_args()

    # 智慧模式與手動日期不能同時使用
    if args.smart and (args.start_date or args.end_date):
        print("❌ 錯誤: --smart 模式不能與 --start-date 或 --end-date 同時使用")
        sys.exit(1)

    # 解析日期
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date() if args.start_date else None
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date() if args.end_date else None

    # 建立輸出目錄
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("QuantLab → Qlib 數據轉換工具")
    print("=" * 60)
    print(f"輸出目錄: {output_dir.absolute()}")

    if args.smart:
        print(f"模式: 🧠 智慧同步（自動增量更新）")
    elif args.force_full:
        print(f"模式: 🔄 強制完整同步")
    else:
        if start_date:
            print(f"開始日期: {start_date}")
        if end_date:
            print(f"結束日期: {end_date}")

    # 建立資料庫連接
    engine = get_db_engine()

    # 獲取股票列表
    if args.stocks == 'all':
        stock_list = get_stock_list(engine)
    else:
        stock_list = [s.strip() for s in args.stocks.split(',')]

    # 限制數量（測試模式）
    if args.limit:
        stock_list = stock_list[:args.limit]
        print(f"⚠️  測試模式: 僅轉換 {args.limit} 檔股票")

    print(f"股票數量: {len(stock_list)}")
    print("=" * 60)

    # 轉換每檔股票
    success_count = 0
    error_count = 0
    skip_count = 0
    full_sync_count = 0
    incremental_sync_count = 0

    for i, stock_id in enumerate(stock_list, 1):
        try:
            print(f"\n[{i}/{len(stock_list)}]", end=" ")

            # 智慧模式：自動判斷同步範圍
            if args.smart:
                sync_start, sync_end, sync_type = determine_sync_range(
                    engine, output_dir, stock_id, args.force_full
                )

                if sync_type == 'skip':
                    print(f"📊 {stock_id}: ⏭️  已是最新，跳過")
                    skip_count += 1
                    continue
                elif sync_type == 'full':
                    print(f"📊 {stock_id}: 🆕 首次匯出（完整同步）")
                    full_sync_count += 1
                    export_stock_to_qlib(engine, stock_id, output_dir, sync_start, sync_end, append=False)
                elif sync_type == 'incremental':
                    print(f"📊 {stock_id}: ➕ 增量更新 ({sync_start} ~ {sync_end})")
                    incremental_sync_count += 1
                    export_stock_to_qlib(engine, stock_id, output_dir, sync_start, sync_end, append=True)
            else:
                # 手動模式：使用指定日期範圍（總是覆蓋）
                export_stock_to_qlib(engine, stock_id, output_dir, start_date, end_date, append=False)

            success_count += 1
        except Exception as e:
            print(f"  ❌ 錯誤: {e}")
            error_count += 1

    # 建立元數據
    create_qlib_metadata(output_dir, stock_list)

    # 總結
    print("\n" + "=" * 60)
    print("轉換完成！")
    print("=" * 60)
    print(f"✅ 成功: {success_count} 檔")
    print(f"❌ 失敗: {error_count} 檔")

    if args.smart:
        print(f"\n智慧同步統計：")
        print(f"  🆕 首次匯出: {full_sync_count} 檔")
        print(f"  ➕ 增量更新: {incremental_sync_count} 檔")
        print(f"  ⏭️  已是最新: {skip_count} 檔")

    print(f"\n📁 輸出目錄: {output_dir.absolute()}")
    print("\n下一步：")
    print(f"  1. 查看 {output_dir}/README.md 了解使用方式")
    print(f"  2. 在 Qlib 中設定 provider_uri='{output_dir.absolute()}'")
    print(f"  3. 使用 D.features() 載入數據")
    print("=" * 60)


if __name__ == '__main__':
    main()
