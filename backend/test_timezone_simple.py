#!/usr/bin/env python3
"""簡單的時區轉換測試"""
import sys
sys.path.insert(0, '/app')

from datetime import datetime, timezone
from app.utils.timezone_helpers import utc_to_naive_taipei, naive_taipei_to_utc

print("=" * 80)
print("時區轉換工具函數測試")
print("=" * 80)

# 測試 1: UTC 轉台灣時間
print("\n測試 1: UTC → 台灣時間")
test_cases_utc_to_taiwan = [
    ("2025-12-20 00:18:21 UTC", datetime(2025, 12, 20, 0, 18, 21, tzinfo=timezone.utc), "2025-12-20 08:18:21"),
    ("2025-12-19 19:00:00 UTC", datetime(2025, 12, 19, 19, 0, 0, tzinfo=timezone.utc), "2025-12-20 03:00:00"),
    ("2025-12-20 01:00:00 UTC", datetime(2025, 12, 20, 1, 0, 0, tzinfo=timezone.utc), "2025-12-20 09:00:00"),
    ("2025-12-20 07:00:00 UTC", datetime(2025, 12, 20, 7, 0, 0, tzinfo=timezone.utc), "2025-12-20 15:00:00"),
    ("2025-12-20 13:00:00 UTC", datetime(2025, 12, 20, 13, 0, 0, tzinfo=timezone.utc), "2025-12-20 21:00:00"),
]

for desc, utc_time, expected_str in test_cases_utc_to_taiwan:
    taiwan_time = utc_to_naive_taipei(utc_time)
    taiwan_str = taiwan_time.strftime("%Y-%m-%d %H:%M:%S")
    status = "✅" if taiwan_str == expected_str else "❌"
    print(f"  {status} {desc}")
    print(f"     輸入:  {utc_time}")
    print(f"     輸出:  {taiwan_time} (naive)")
    print(f"     預期:  {expected_str}")
    if taiwan_str != expected_str:
        print(f"     實際:  {taiwan_str}")
    print()

# 測試 2: 台灣時間轉 UTC
print("\n測試 2: 台灣時間 → UTC")
test_cases_taiwan_to_utc = [
    ("2025-12-20 08:18:21", datetime(2025, 12, 20, 8, 18, 21), "2025-12-20 00:18:21+00:00"),
    ("2025-12-20 09:00:00", datetime(2025, 12, 20, 9, 0, 0), "2025-12-20 01:00:00+00:00"),
    ("2025-12-20 15:00:00", datetime(2025, 12, 20, 15, 0, 0), "2025-12-20 07:00:00+00:00"),
    ("2025-12-20 21:00:00", datetime(2025, 12, 20, 21, 0, 0), "2025-12-20 13:00:00+00:00"),
]

for desc, taiwan_naive, expected_str in test_cases_taiwan_to_utc:
    utc_time = naive_taipei_to_utc(taiwan_naive)
    utc_str = utc_time.isoformat()
    status = "✅" if utc_str == expected_str else "❌"
    print(f"  {status} {desc}")
    print(f"     輸入:  {taiwan_naive} (naive)")
    print(f"     輸出:  {utc_time}")
    print(f"     預期:  {expected_str}")
    if utc_str != expected_str:
        print(f"     實際:  {utc_str}")
    print()

# 測試 3: 往返轉換
print("\n測試 3: 往返轉換（UTC → 台灣 → UTC）")
original_utc = datetime(2025, 12, 20, 0, 18, 21, tzinfo=timezone.utc)
taiwan = utc_to_naive_taipei(original_utc)
back_to_utc = naive_taipei_to_utc(taiwan)

print(f"  原始 UTC:  {original_utc}")
print(f"  台灣時間:  {taiwan}")
print(f"  轉回 UTC:  {back_to_utc}")

if original_utc == back_to_utc:
    print(f"  ✅ 往返轉換正確！")
else:
    print(f"  ❌ 往返轉換錯誤！")

print("\n" + "=" * 80)
print("測試完成")
print("=" * 80)
