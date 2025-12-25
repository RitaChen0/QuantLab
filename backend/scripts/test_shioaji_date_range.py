#!/usr/bin/env python3
"""
測試 Shioaji API 不同日期範圍的查詢
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from app.services.shioaji_client import ShioajiClient
import pandas as pd

def test_date_range(client, stock_id: str, start: str, end: str, description: str):
    """測試特定日期範圍"""
    print(f"\n{'='*60}")
    print(f"測試: {description}")
    print(f"日期範圍: {start} ~ {end}")
    print('='*60)

    contract = client.get_contract(stock_id)
    if not contract:
        print(f"❌ 無法獲取合約")
        return

    # 直接調用 API
    kbars = client._api.kbars(
        contract=contract,
        start=start,
        end=end,
        timeout=30000
    )

    print(f"\n📊 API 返回數據量: {len(kbars.ts)} 筆")

    if len(kbars.ts) > 0:
        # 轉換第一筆和最後一筆
        first_ts = pd.to_datetime(kbars.ts[0], unit='ns').tz_localize('Asia/Taipei').tz_localize(None)
        last_ts = pd.to_datetime(kbars.ts[-1], unit='ns').tz_localize('Asia/Taipei').tz_localize(None)

        print(f"第一筆時間: {first_ts}")
        print(f"最後一筆時間: {last_ts}")
        print(f"第一筆價格: O:{kbars.Open[0]} H:{kbars.High[0]} L:{kbars.Low[0]} C:{kbars.Close[0]} V:{kbars.Volume[0]}")

        # 統計每天的數據量
        timestamps = [pd.to_datetime(ts, unit='ns').tz_localize('Asia/Taipei').tz_localize(None) for ts in kbars.ts]
        df = pd.DataFrame({'datetime': timestamps})
        daily_counts = df.groupby(df['datetime'].dt.date).size()

        print(f"\n每日數據分布:")
        for date, count in daily_counts.items():
            print(f"  {date}: {count} 筆")
    else:
        print("⚠️ API 返回空數據")

def main():
    print("=" * 60)
    print("Shioaji API 日期範圍測試")
    print("=" * 60)

    with ShioajiClient() as client:
        if not client.is_available():
            print("❌ Shioaji 客戶端初始化失敗")
            return

        print("\n✅ Shioaji 客戶端已連接")
        stock_id = '2330'

        # 測試不同的日期範圍
        test_cases = [
            ('2025-12-24', '2025-12-24', '單日查詢: 12/24'),
            ('2025-12-23', '2025-12-23', '單日查詢: 12/23'),
            ('2025-12-20', '2025-12-20', '單日查詢: 12/20（週五）'),
            ('2025-12-19', '2025-12-19', '單日查詢: 12/19'),
            ('2025-12-18', '2025-12-18', '單日查詢: 12/18'),
            ('2025-12-19', '2025-12-24', '範圍查詢: 12/19-12/24'),
            ('2025-12-18', '2025-12-24', '範圍查詢: 12/18-12/24'),
            ('2025-12-16', '2025-12-24', '範圍查詢: 12/16-12/24（週一開始）'),
        ]

        for start, end, description in test_cases:
            test_date_range(client, stock_id, start, end, description)

if __name__ == "__main__":
    main()
