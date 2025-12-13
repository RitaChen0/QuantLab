#!/usr/bin/env python3
"""測試 FinMind API - 三大法人買賣超數據"""

from app.services.finmind_client import FinMindClient
import pandas as pd
import requests

def test_institutional_investors_raw():
    """直接測試 FinMind API 響應"""
    print("=" * 80)
    print("測試 FinMind API - 三大法人買賣超數據（原始請求）")
    print("=" * 80)

    # 從環境變數獲取 token
    from app.core.config import settings

    # 構建請求參數
    params = {
        "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
        "data_id": "2330",
        "start_date": "2024-12-01",
        "end_date": "2024-12-13",
        "token": settings.FINMIND_API_TOKEN
    }

    print(f"\n1️⃣ 請求參數:")
    for key, value in params.items():
        if key == "token":
            print(f"   - {key}: {value[:20]}..." if value else f"   - {key}: (未設定)")
        else:
            print(f"   - {key}: {value}")

    try:
        print(f"\n2️⃣ 發送請求到: https://api.finmindtrade.com/api/v4/data")
        response = requests.get(
            "https://api.finmindtrade.com/api/v4/data",
            params=params,
            timeout=30
        )

        print(f"\n3️⃣ HTTP 狀態碼: {response.status_code}")

        # 解析 JSON 響應
        data = response.json()

        print(f"\n4️⃣ API 響應:")
        print(f"   - status: {data.get('status')}")
        print(f"   - msg: {data.get('msg')}")
        print(f"   - data 筆數: {len(data.get('data', []))}")

        if data.get('data'):
            df = pd.DataFrame(data['data'])
            print(f"\n5️⃣ 數據欄位: {df.columns.tolist()}")
            print(f"\n6️⃣ 前 3 筆數據:")
            print(df.head(3).to_string())
        else:
            print("\n⚠️ data 欄位為空")

        # 完整響應
        print(f"\n7️⃣ 完整 JSON 響應:")
        import json
        print(json.dumps(data, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"\n❌ 錯誤: {str(e)}")
        import traceback
        print(traceback.format_exc())

def test_with_client():
    """使用 FinMindClient 測試"""
    print("\n" + "=" * 80)
    print("測試 FinMindClient 封裝")
    print("=" * 80)

    try:
        client = FinMindClient()

        df = client.get_institutional_investors(
            stock_id='2330',
            start_date='2024-12-01',
            end_date='2024-12-13'
        )

        print(f"\n數據形狀: {df.shape}")
        print(f"數據欄位: {df.columns.tolist()}")

        if len(df) > 0:
            print(f"\n前 3 筆數據:")
            print(df.head(3).to_string())
        else:
            print("\n⚠️ 返回空 DataFrame")

    except Exception as e:
        print(f"\n❌ 錯誤: {str(e)}")

if __name__ == "__main__":
    # 測試原始 API
    test_institutional_investors_raw()

    # 測試封裝後的 client
    test_with_client()
