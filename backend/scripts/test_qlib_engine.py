#!/usr/bin/env python3
"""
測試重構後的 Qlib 引擎

此腳本驗證：
1. Qlib 初始化是否正確
2. 從本地 qlib 數據讀取是否正常
3. Qlib 表達式計算是否正確
4. Fallback 到 FinLab API 是否正常
"""

import sys
import os
from datetime import date, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.qlib_data_adapter import QlibDataAdapter
from app.core.qlib_config import qlib_config
from loguru import logger

# 配置日誌
logger.remove()
logger.add(sys.stderr, level="INFO")


def test_qlib_initialization():
    """測試 Qlib 初始化"""
    print("\n" + "="*60)
    print("測試 1: Qlib 初始化")
    print("="*60)

    is_available = qlib_config.is_qlib_available()
    print(f"Qlib 是否安裝: {is_available}")

    if is_available:
        success = qlib_config.init_qlib()
        print(f"Qlib 初始化: {'✅ 成功' if success else '❌ 失敗'}")
        print(f"數據路徑: {qlib_config.get_data_path()}")
        print(f"快取路徑: {qlib_config.get_cache_path()}")

        # 檢查數據目錄
        data_path = Path(qlib_config.get_data_path()) / 'instruments'
        if data_path.exists():
            bin_files = list(data_path.glob('*.bin'))
            print(f"本地數據檔案數量: {len(bin_files)}")
            if bin_files:
                print(f"範例檔案: {bin_files[0].name}")
        else:
            print("⚠️  本地數據目錄不存在")

        return success
    else:
        print("❌ Qlib 未安裝，請執行: pip install pyqlib")
        return False


def test_basic_data_loading():
    """測試基礎數據讀取"""
    print("\n" + "="*60)
    print("測試 2: 基礎 OHLCV 數據讀取")
    print("="*60)

    adapter = QlibDataAdapter()

    # 測試股票代碼
    symbol = "2330"
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    print(f"股票: {symbol}")
    print(f"日期範圍: {start_date} ~ {end_date}")

    try:
        df = adapter.get_qlib_ohlcv(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )

        if df is not None and not df.empty:
            print(f"✅ 成功讀取 {len(df)} 筆數據")
            print(f"欄位: {list(df.columns)}")
            print(f"\n前 3 筆數據:")
            print(df.head(3))
            return True
        else:
            print("❌ 未獲取到數據")
            return False

    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_qlib_features():
    """測試 Qlib 表達式和技術指標"""
    print("\n" + "="*60)
    print("測試 3: Qlib 表達式和技術指標")
    print("="*60)

    adapter = QlibDataAdapter()

    symbol = "2330"
    end_date = date.today()
    start_date = end_date - timedelta(days=60)  # 需要更多數據來計算技術指標

    # 定義要測試的 Qlib 表達式
    fields = [
        '$close',
        'Mean($close, 5)',
        'Mean($close, 20)',
        'Std($close, 20)',
        '$volume / Mean($volume, 20)',
    ]

    print(f"股票: {symbol}")
    print(f"日期範圍: {start_date} ~ {end_date}")
    print(f"測試表達式: {fields}")

    try:
        df = adapter.get_qlib_features(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            fields=fields
        )

        if df is not None and not df.empty:
            print(f"✅ 成功計算 {len(df.columns)} 個特徵")
            print(f"特徵列表: {list(df.columns)}")
            print(f"數據筆數: {len(df)}")
            print(f"\n最近 5 筆數據:")
            print(df.tail(5))

            # 檢查是否有 NaN
            nan_count = df.isna().sum().sum()
            if nan_count > 0:
                print(f"\n⚠️  包含 {nan_count} 個 NaN 值")
            else:
                print("\n✅ 無 NaN 值")

            return True
        else:
            print("❌ 未獲取到數據")
            return False

    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_default_features():
    """測試預設技術指標"""
    print("\n" + "="*60)
    print("測試 4: 預設技術指標（無需指定 fields）")
    print("="*60)

    adapter = QlibDataAdapter()

    symbol = "2330"
    end_date = date.today()
    start_date = end_date - timedelta(days=90)

    print(f"股票: {symbol}")
    print(f"日期範圍: {start_date} ~ {end_date}")

    try:
        # 不指定 fields，使用預設值
        df = adapter.get_qlib_features(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )

        if df is not None and not df.empty:
            print(f"✅ 成功讀取預設特徵")
            print(f"特徵數量: {len(df.columns)}")
            print(f"數據筆數: {len(df)}")
            print(f"\n特徵列表:")
            for i, col in enumerate(df.columns, 1):
                print(f"  {i:2d}. {col}")

            return True
        else:
            print("❌ 未獲取到數據")
            return False

    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_source():
    """測試數據來源（Qlib 本地 vs FinLab API）"""
    print("\n" + "="*60)
    print("測試 5: 檢查數據來源")
    print("="*60)

    adapter = QlibDataAdapter()

    # 測試已匯出的股票
    test_stocks = ["2330", "2317", "2454"]

    for symbol in test_stocks:
        has_local = adapter._check_qlib_data_exists(symbol)
        source = "📂 本地 Qlib 數據" if has_local else "📡 FinLab API"
        print(f"{symbol}: {source}")

    return True


def main():
    """執行所有測試"""
    print("\n" + "="*60)
    print("Qlib 引擎重構測試")
    print("="*60)

    results = []

    # 測試 1: 初始化
    results.append(("Qlib 初始化", test_qlib_initialization()))

    # 測試 2: 基礎數據讀取
    results.append(("基礎數據讀取", test_basic_data_loading()))

    # 測試 3: Qlib 表達式
    results.append(("Qlib 表達式", test_qlib_features()))

    # 測試 4: 預設特徵
    results.append(("預設技術指標", test_default_features()))

    # 測試 5: 數據來源檢查
    results.append(("數據來源檢查", test_data_source()))

    # 總結
    print("\n" + "="*60)
    print("測試總結")
    print("="*60)

    for name, passed in results:
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"{name:20s}: {status}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print(f"\n總計: {passed}/{total} 測試通過")

    if passed == total:
        print("\n🎉 所有測試通過！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 個測試失敗")
        return 1


if __name__ == "__main__":
    exit(main())
