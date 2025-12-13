#!/usr/bin/env python3
"""法人買賣超 API 端點完整測試"""
import requests
import sys

API_BASE = "http://localhost:8000/api/v1"

print("=" * 80)
print("法人買賣超 API 端點測試")
print("=" * 80)

# 步驟 1: 檢查 Backend 狀態
print("\n✅ 步驟 1: 檢查 Backend 狀態")
try:
    response = requests.get("http://localhost:8000/health", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"   Backend 運行正常 - 版本: {data.get('version')}")
    else:
        print(f"   ❌ Backend 狀態異常: {response.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ 無法連接 Backend: {e}")
    sys.exit(1)

# 步驟 2: 獲取測試 Token
print("\n✅ 步驟 2: 生成測試 Token")
import subprocess
result = subprocess.run(
    ['docker', 'compose', 'exec', '-T', 'backend', 'python3', '-c',
     "import sys; sys.path.insert(0, '/app'); from app.core.security import create_access_token; print(create_access_token('1'))"],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print(f"   ❌ Token 生成失敗: {result.stderr}")
    sys.exit(1)

TOKEN = result.stdout.strip()
headers = {"Authorization": f"Bearer {TOKEN}"}
print(f"   Token 已生成: {TOKEN[:20]}...")

# 步驟 3: 測試各個端點
print("\n✅ 步驟 3: 測試 API 端點")

tests = []

# 測試 3.1: 查詢最新數據日期
print("\n   3.1 查詢最新數據日期")
try:
    response = requests.get(
        f"{API_BASE}/institutional/status/latest-date",
        params={"stock_id": "2330"},
        headers=headers,
        timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        print(f"       ✅ 成功 - 最新日期: {data.get('latest_date', 'N/A')}")
        tests.append(("最新數據日期", True))
    else:
        print(f"       ❌ 失敗 - 狀態碼: {response.status_code}")
        print(f"       響應: {response.text}")
        tests.append(("最新數據日期", False))
except Exception as e:
    print(f"       ❌ 錯誤: {e}")
    tests.append(("最新數據日期", False))

# 測試 3.2: 查詢法人買賣超數據
print("\n   3.2 查詢法人買賣超數據")
try:
    response = requests.get(
        f"{API_BASE}/institutional/stocks/2330/data",
        params={
            "start_date": "2024-12-01",
            "end_date": "2024-12-05",
            "investor_type": "Foreign_Investor"
        },
        headers=headers,
        timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        print(f"       ✅ 成功 - 查詢到 {len(data)} 筆記錄")
        if len(data) > 0:
            record = data[0]
            print(f"       範例: {record.get('date')} 買賣超 {record.get('net_buy_sell'):,}")
        tests.append(("查詢數據", True))
    else:
        print(f"       ❌ 失敗 - 狀態碼: {response.status_code}")
        print(f"       響應: {response.text}")
        tests.append(("查詢數據", False))
except Exception as e:
    print(f"       ❌ 錯誤: {e}")
    tests.append(("查詢數據", False))

# 測試 3.3: 查詢單日摘要
print("\n   3.3 查詢單日摘要")
try:
    response = requests.get(
        f"{API_BASE}/institutional/stocks/2330/summary",
        params={"target_date": "2024-12-02"},
        headers=headers,
        timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        print(f"       ✅ 成功")
        print(f"       外資: {data.get('foreign_net', 0):,}")
        print(f"       投信: {data.get('trust_net', 0):,}")
        print(f"       三大法人合計: {data.get('total_net', 0):,}")
        tests.append(("單日摘要", True))
    else:
        print(f"       ❌ 失敗 - 狀態碼: {response.status_code}")
        print(f"       響應: {response.text}")
        tests.append(("單日摘要", False))
except Exception as e:
    print(f"       ❌ 錯誤: {e}")
    tests.append(("單日摘要", False))

# 測試 3.4: 查詢統計數據
print("\n   3.4 查詢統計數據")
try:
    response = requests.get(
        f"{API_BASE}/institutional/stocks/2330/stats",
        params={
            "investor_type": "Foreign_Investor",
            "start_date": "2024-12-01",
            "end_date": "2024-12-05"
        },
        headers=headers,
        timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        print(f"       ✅ 成功")
        print(f"       總買進: {data.get('total_buy', 0):,}")
        print(f"       總賣出: {data.get('total_sell', 0):,}")
        print(f"       淨買賣超: {data.get('total_net', 0):,}")
        tests.append(("統計數據", True))
    elif response.status_code == 404:
        print(f"       ⚠️  期間內無數據（正常）")
        tests.append(("統計數據", True))
    else:
        print(f"       ❌ 失敗 - 狀態碼: {response.status_code}")
        print(f"       響應: {response.text}")
        tests.append(("統計數據", False))
except Exception as e:
    print(f"       ❌ 錯誤: {e}")
    tests.append(("統計數據", False))

# 測試 3.5: 查詢排行榜
print("\n   3.5 查詢買賣超排行榜")
try:
    response = requests.get(
        f"{API_BASE}/institutional/rankings/2024-12-02",
        params={
            "investor_type": "Foreign_Investor",
            "limit": 5
        },
        headers=headers,
        timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        print(f"       ✅ 成功 - 返回 {len(data)} 筆排行")
        tests.append(("排行榜", True))
    else:
        print(f"       ❌ 失敗 - 狀態碼: {response.status_code}")
        print(f"       響應: {response.text}")
        tests.append(("排行榜", False))
except Exception as e:
    print(f"       ❌ 錯誤: {e}")
    tests.append(("排行榜", False))

# 測試 3.6: 觸發數據同步
print("\n   3.6 觸發數據同步（異步任務）")
try:
    response = requests.post(
        f"{API_BASE}/institutional/sync/2330",
        params={
            "start_date": "2024-12-01",
            "end_date": "2024-12-02"
        },
        headers=headers,
        timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        print(f"       ✅ 成功 - 任務 ID: {data.get('task_id', 'N/A')}")
        print(f"       狀態: {data.get('status', 'N/A')}")
        tests.append(("數據同步", True))
    else:
        print(f"       ❌ 失敗 - 狀態碼: {response.status_code}")
        print(f"       響應: {response.text}")
        tests.append(("數據同步", False))
except Exception as e:
    print(f"       ❌ 錯誤: {e}")
    tests.append(("數據同步", False))

# 步驟 4: 檢查 OpenAPI 文檔
print("\n✅ 步驟 4: 檢查 OpenAPI 文檔")
try:
    response = requests.get(f"{API_BASE}/openapi.json", timeout=10)
    if response.status_code == 200:
        openapi = response.json()
        endpoints = [path for path in openapi.get('paths', {}).keys() if 'institutional' in path]
        print(f"   OpenAPI 文檔已生成")
        print(f"   法人買賣超端點數量: {len(endpoints)}")
        print("   端點列表:")
        for endpoint in endpoints:
            print(f"     - {endpoint}")
    else:
        print(f"   ❌ OpenAPI 文檔獲取失敗")
except Exception as e:
    print(f"   ❌ 錯誤: {e}")

# 總結
print("\n" + "=" * 80)
print("測試結果總結")
print("=" * 80)

success_count = sum(1 for _, success in tests if success)
total_count = len(tests)

for name, success in tests:
    status = "✅ 通過" if success else "❌ 失敗"
    print(f"   {status} - {name}")

print(f"\n通過率: {success_count}/{total_count} ({success_count * 100 // total_count if total_count > 0 else 0}%)")

if success_count == total_count:
    print("\n🎉 所有測試通過！法人買賣超 API 端點已成功啟用")
else:
    print(f"\n⚠️  {total_count - success_count} 個測試失敗")

print("\n" + "=" * 80)
print("📚 相關資源")
print("=" * 80)
print("   - Swagger UI: http://localhost:8000/docs")
print("   - ReDoc: http://localhost:8000/redoc")
print("   - API 使用指南: /home/ubuntu/QuantLab/INSTITUTIONAL_API_GUIDE.md")
print("")
