#!/usr/bin/env python3
"""
Debug get_kbars 方法
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from app.services.shioaji_client import ShioajiClient

def main():
    print("=" * 60)
    print("Debug get_kbars 方法")
    print("=" * 60)

    with ShioajiClient() as client:
        if not client.is_available():
            print("❌ Shioaji 客戶端初始化失敗")
            return

        print("\n✅ Shioaji 客戶端已連接")
        print("\n測試 1: 調用 get_kbars (12/24)")
        print("-" * 60)

        df = client.get_kbars(
            stock_id='2330',
            start_datetime=datetime(2025, 12, 24, 9, 0, 0),
            end_datetime=datetime(2025, 12, 24, 13, 30, 0),
            timeframe='1min'
        )

        if df is not None and not df.empty:
            print(f"\n✅ 獲取到 {len(df)} 筆數據")
            print(f"\n前 5 筆：")
            print(df.head())
            print(f"\n後 5 筆：")
            print(df.tail())
            print(f"\n時間範圍：{df['datetime'].min()} ~ {df['datetime'].max()}")
        else:
            print("\n❌ 沒有數據")

        print("\n測試 2: 直接調用 _api.kbars (12/24)")
        print("-" * 60)

        contract = client.get_contract('2330')
        if contract:
            print(f"合約：{contract}")
            kbars = client._api.kbars(
                contract=contract,
                start='2025-12-24',
                end='2025-12-24',
                timeout=30000
            )

            print(f"\n時間戳數量：{len(kbars.ts)}")
            if len(kbars.ts) > 0:
                print(f"第一筆 timestamp: {kbars.ts[0]}")
                print(f"最後一筆 timestamp: {kbars.ts[-1]}")

                # 手動轉換第一筆
                import pandas as pd
                ts_ns = kbars.ts[0]
                dt = pd.to_datetime(ts_ns, unit='ns', utc=True).tz_convert('Asia/Taipei').tz_localize(None)
                print(f"第一筆時間（轉換後）: {dt}")
                print(f"小時: {dt.hour}, 分鐘: {dt.minute}")

                # 檢查是否在交易時段
                from app.core.trading_hours import is_trading_time
                is_valid = is_trading_time(dt.hour, dt.minute, include_night=False)
                print(f"是否在交易時段: {is_valid}")

if __name__ == "__main__":
    main()
