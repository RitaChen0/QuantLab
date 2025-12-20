#!/usr/bin/env python3
"""
測試時區轉換功能

驗證 stock_minute_price.py 中的時區轉換是否正確工作
"""
import sys
sys.path.insert(0, '/app')

from datetime import datetime, timezone, timedelta
from app.db.session import SessionLocal
from app.repositories.stock_minute_price import StockMinutePriceRepository
from app.utils.timezone_helpers import utc_to_naive_taipei, naive_taipei_to_utc

def test_timezone_conversion():
    """測試時區轉換"""
    print("=" * 80)
    print("時區轉換測試")
    print("=" * 80)

    db = SessionLocal()

    try:
        # 1. 檢查資料庫中是否有分鐘線數據
        print("\n1. 檢查資料庫中的分鐘線數據...")
        stock_id = '2330'  # 台積電

        date_range = StockMinutePriceRepository.get_date_range(db, stock_id)
        if not date_range:
            print(f"   ❌ 資料庫中沒有 {stock_id} 的數據")
            return

        print(f"   ✅ {stock_id} 數據範圍:")
        print(f"      最早: {date_range['min_date']}")
        print(f"      最晚: {date_range['max_date']}")

        # 2. 測試 UTC aware datetime 查詢
        print("\n2. 測試 UTC aware datetime 查詢...")

        # 使用最晚日期的前一天作為測試範圍
        test_date = date_range['max_date'].date()

        # 台灣時間 09:00-10:00
        taiwan_start = datetime(test_date.year, test_date.month, test_date.day, 9, 0, 0)
        taiwan_end = datetime(test_date.year, test_date.month, test_date.day, 10, 0, 0)

        # 轉換為 UTC
        utc_start = naive_taipei_to_utc(taiwan_start)
        utc_end = naive_taipei_to_utc(taiwan_end)

        print(f"   查詢範圍（台灣時間）: {taiwan_start} ~ {taiwan_end}")
        print(f"   查詢範圍（UTC 時間）:  {utc_start} ~ {utc_end}")

        # 使用 UTC aware datetime 查詢
        results = StockMinutePriceRepository.get_by_stock(
            db,
            stock_id=stock_id,
            start_datetime=utc_start,
            end_datetime=utc_end,
            limit=100
        )

        print(f"   ✅ 查詢結果: {len(results)} 筆")

        if results:
            print(f"\n   前 5 筆數據:")
            for i, result in enumerate(results[:5], 1):
                print(f"      {i}. 時間: {result.datetime}, 收盤: {result.close}")

            # 驗證時間範圍
            first_time = results[0].datetime
            last_time = results[-1].datetime

            print(f"\n   實際數據時間範圍（台灣時間）:")
            print(f"      第一筆: {first_time}")
            print(f"      最後筆: {last_time}")

            # 檢查是否在預期範圍內
            if taiwan_start <= first_time <= taiwan_end and taiwan_start <= last_time <= taiwan_end:
                print(f"   ✅ 時間範圍正確！")
            else:
                print(f"   ❌ 時間範圍不正確！")
                print(f"      預期: {taiwan_start} ~ {taiwan_end}")
                print(f"      實際: {first_time} ~ {last_time}")
        else:
            print(f"   ⚠️  該時間範圍內沒有數據")

        # 3. 測試 naive datetime 查詢（向後兼容）
        print("\n3. 測試 naive datetime 查詢（向後兼容）...")

        results_naive = StockMinutePriceRepository.get_by_stock(
            db,
            stock_id=stock_id,
            start_datetime=taiwan_start,  # naive datetime
            end_datetime=taiwan_end,      # naive datetime
            limit=100
        )

        print(f"   ✅ 查詢結果: {len(results_naive)} 筆")

        # 4. 比較兩種查詢結果
        print("\n4. 比較 UTC aware 和 naive datetime 查詢結果...")

        if len(results) == len(results_naive):
            print(f"   ✅ 兩種查詢結果筆數相同: {len(results)} 筆")

            if results and results_naive:
                if results[0].datetime == results_naive[0].datetime:
                    print(f"   ✅ 時區轉換正確！UTC aware datetime 被正確轉換為台灣時間")
                else:
                    print(f"   ❌ 時區轉換錯誤！")
                    print(f"      UTC aware 查詢第一筆: {results[0].datetime}")
                    print(f"      Naive 查詢第一筆: {results_naive[0].datetime}")
        else:
            print(f"   ⚠️  兩種查詢結果筆數不同")
            print(f"      UTC aware: {len(results)} 筆")
            print(f"      Naive: {len(results_naive)} 筆")

        # 5. 測試時區轉換工具函數
        print("\n5. 測試時區轉換工具函數...")

        test_utc = datetime(2025, 12, 20, 0, 18, 21, tzinfo=timezone.utc)
        test_taiwan = utc_to_naive_taipei(test_utc)

        print(f"   UTC:    {test_utc}")
        print(f"   台灣:   {test_taiwan}")

        if test_taiwan.hour == 8:
            print(f"   ✅ UTC 00:18 正確轉換為台灣 08:18")
        else:
            print(f"   ❌ 時區轉換錯誤！")

        print("\n" + "=" * 80)
        print("測試完成")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_timezone_conversion()
