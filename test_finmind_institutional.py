#!/usr/bin/env python3
"""測試 FinMind API - 三大法人買賣超數據"""

import sys
import os

# 添加專案路徑
sys.path.insert(0, '/home/ubuntu/QuantLab/backend')

from app.services.finmind_client import FinMindClient
import pandas as pd

def test_institutional_investors():
    """測試三大法人買賣超數據"""
    print("=" * 80)
    print("測試 FinMind API - 三大法人買賣超數據")
    print("=" * 80)

    try:
        # 初始化客戶端
        print("\n1️⃣ 初始化 FinMindClient...")
        client = FinMindClient()
        print("✅ FinMindClient 初始化成功")

        # 測試台積電 (2330) - 台股最活躍的股票
        stock_id = '2330'
        start_date = '2024-12-01'
        end_date = '2024-12-13'

        print(f"\n2️⃣ 請求數據: 股票={stock_id}, 期間={start_date} ~ {end_date}")
        df = client.get_institutional_investors(
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )

        # 檢查數據
        print(f"\n3️⃣ 數據檢查:")
        print(f"   - 資料筆數: {len(df)}")
        print(f"   - 資料形狀: {df.shape}")
        print(f"   - 欄位列表: {df.columns.tolist()}")

        if len(df) > 0:
            print(f"\n4️⃣ 數據類型:")
            for col, dtype in df.dtypes.items():
                print(f"   - {col}: {dtype}")

            print(f"\n5️⃣ 前 5 筆數據:")
            print(df.head().to_string())

            print(f"\n6️⃣ 數據統計:")
            # 檢查是否有外資、投信、自營商欄位
            numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
            if len(numeric_cols) > 0:
                print(df[numeric_cols].describe().to_string())

            print("\n✅ 測試成功！FinMind API 可以正常獲取三大法人買賣超數據")
            return True
        else:
            print("\n⚠️ 警告：API 返回空數據")
            return False

    except Exception as e:
        print(f"\n❌ 測試失敗: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = test_institutional_investors()
    sys.exit(0 if success else 1)
