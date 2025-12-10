#!/usr/bin/env python3
"""
分佈式鎖測試 - 並發回測執行
Purpose: 驗證 Redis 分佈式鎖是否正確防止並發執行
"""

import requests
import time
import threading
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def log(message, color=RESET):
    """Print colored log message"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] {message}{RESET}")

def setup_test_data():
    """Setup test user, strategy, and backtests"""
    log("=" * 50, BLUE)
    log("分佈式鎖測試 - 並發回測執行", BLUE)
    log("=" * 50, BLUE)
    print()

    # Step 1: Register user
    log("Step 1: 建立測試用戶", YELLOW)
    register_data = {
        "email": "locktest2@example.com",
        "username": "locktest2",
        "password": "password123",
        "full_name": "Lock Test User 2"
    }

    response = requests.post(f"{API_BASE}/api/v1/auth/register", json=register_data)
    if response.status_code == 201:
        log(f"✅ 用戶建立成功: {response.json()['username']}", GREEN)
    elif response.status_code == 400:
        log("⚠️  用戶已存在，使用現有用戶", YELLOW)
    else:
        log(f"❌ 用戶建立失敗: {response.text}", RED)
        return None

    # Step 2: Login
    log("\nStep 2: 登入取得 Token", YELLOW)
    login_data = {
        "username": "locktest2",
        "password": "password123"
    }

    response = requests.post(f"{API_BASE}/api/v1/auth/login", json=login_data)
    if response.status_code != 200:
        log(f"❌ 登入失敗: {response.text}", RED)
        return None

    token = response.json()["access_token"]
    log(f"✅ Token 取得成功: {token[:20]}...", GREEN)

    headers = {"Authorization": f"Bearer {token}"}

    # Step 3: Create strategy
    log("\nStep 3: 建立測試策略", YELLOW)
    strategy_data = {
        "name": "Lock Test Strategy 2",
        "description": "Strategy for testing distributed lock",
        "code": "import backtrader as bt\n\nclass TestStrategy(bt.Strategy):\n    def __init__(self):\n        pass\n    def next(self):\n        pass",
        "parameters": {},
        "status": "draft"
    }

    response = requests.post(f"{API_BASE}/api/v1/strategies/", json=strategy_data, headers=headers)
    if response.status_code != 201:
        log(f"❌ 策略建立失敗: {response.text}", RED)
        return None

    strategy_id = response.json()["id"]
    log(f"✅ 策略建立成功，ID: {strategy_id}", GREEN)

    # Step 4: Create two backtests
    log("\nStep 4: 建立兩個回測配置", YELLOW)
    backtest_data = {
        "name": "Lock Test Backtest",
        "description": "Testing distributed lock for concurrent execution",
        "strategy_id": strategy_id,
        "symbol": "2330",
        "start_date": "2024-01-01",
        "end_date": "2024-12-01",
        "initial_capital": 1000000
    }

    response1 = requests.post(f"{API_BASE}/api/v1/backtest/", json=backtest_data, headers=headers)
    if response1.status_code != 201:
        log(f"❌ 回測 1 建立失敗: {response1.text}", RED)
        return None
    backtest_id1 = response1.json()["id"]
    log(f"✅ 回測 1 建立成功，ID: {backtest_id1}", GREEN)

    response2 = requests.post(f"{API_BASE}/api/v1/backtest/", json=backtest_data, headers=headers)
    if response2.status_code != 201:
        log(f"❌ 回測 2 建立失敗: {response2.text}", RED)
        return None
    backtest_id2 = response2.json()["id"]
    log(f"✅ 回測 2 建立成功，ID: {backtest_id2}", GREEN)

    return {
        "token": token,
        "backtest_id1": backtest_id1,
        "backtest_id2": backtest_id2
    }

def run_backtest(backtest_id, token, label):
    """Run a single backtest and return result"""
    headers = {"Authorization": f"Bearer {token}"}
    data = {"backtest_id": backtest_id}

    start_time = time.time()
    log(f">>> 請求 {label} 開始 (Backtest ID: {backtest_id})", BLUE)

    try:
        response = requests.post(
            f"{API_BASE}/api/v1/backtest/run",
            json=data,
            headers=headers,
            timeout=60
        )

        elapsed = time.time() - start_time

        result = {
            "label": label,
            "backtest_id": backtest_id,
            "status_code": response.status_code,
            "elapsed": elapsed,
            "response": response.text
        }

        if response.status_code == 200:
            log(f">>> 請求 {label} 成功結束 (耗時: {elapsed:.2f}s, HTTP: {response.status_code})", GREEN)
        elif response.status_code in [503, 409]:
            log(f">>> 請求 {label} 被鎖阻擋 (耗時: {elapsed:.2f}s, HTTP: {response.status_code})", YELLOW)
        else:
            log(f">>> 請求 {label} 失敗 (耗時: {elapsed:.2f}s, HTTP: {response.status_code})", RED)

        return result

    except Exception as e:
        elapsed = time.time() - start_time
        log(f">>> 請求 {label} 異常 (耗時: {elapsed:.2f}s): {str(e)}", RED)
        return {
            "label": label,
            "backtest_id": backtest_id,
            "status_code": 0,
            "elapsed": elapsed,
            "error": str(e)
        }

def test_concurrent_execution(test_data):
    """Test concurrent backtest execution"""
    log("\n" + "=" * 50, BLUE)
    log("Step 5: 測試並發執行 (關鍵測試)", BLUE)
    log("=" * 50, BLUE)
    log("同時啟動兩個回測執行請求...\n", YELLOW)

    results = []
    threads = []

    # Create threads for concurrent execution
    thread_a = threading.Thread(
        target=lambda: results.append(run_backtest(test_data["backtest_id1"], test_data["token"], "A"))
    )
    thread_b = threading.Thread(
        target=lambda: results.append(run_backtest(test_data["backtest_id2"], test_data["token"], "B"))
    )

    # Start both threads simultaneously
    thread_a.start()
    time.sleep(0.5)  # Small delay to ensure overlap
    thread_b.start()

    # Wait for completion
    thread_a.join()
    thread_b.join()

    return results

def analyze_results(results):
    """Analyze test results"""
    log("\n" + "=" * 50, BLUE)
    log("測試結果分析", BLUE)
    log("=" * 50, BLUE)

    log("\n【預期行為】", YELLOW)
    log("  ✅ 其中一個請求應成功 (HTTP 200)")
    log("  ✅ 另一個請求應被鎖阻擋 (HTTP 503 或 409)")
    log("  ✅ 錯誤訊息應包含: '另一個回測正在執行中，請稍後再試'")

    log("\n【實際結果】", YELLOW)
    success_count = 0
    blocked_count = 0

    for result in results:
        label = result["label"]
        status = result["status_code"]
        elapsed = result.get("elapsed", 0)

        log(f"\n請求 {label}:")
        log(f"  HTTP 狀態碼: {status}")
        log(f"  執行時間: {elapsed:.2f}s")

        if status == 200:
            log(f"  結果: ✅ 成功執行", GREEN)
            success_count += 1
        elif status in [503, 409]:
            log(f"  結果: ✅ 被鎖正確阻擋", GREEN)
            blocked_count += 1
            # Check error message
            response_text = result.get("response", "")
            if "另一個回測正在執行中" in response_text or "already" in response_text.lower():
                log(f"  訊息: ✅ 包含正確的錯誤訊息", GREEN)
            else:
                log(f"  訊息: ⚠️  錯誤訊息不符預期", YELLOW)
        else:
            log(f"  結果: ❌ 非預期狀態", RED)

        log(f"  回應內容: {result.get('response', result.get('error', 'N/A'))[:200]}")

    log("\n【測試總結】", YELLOW)
    log(f"  成功執行: {success_count}")
    log(f"  被鎖阻擋: {blocked_count}")

    if success_count == 1 and blocked_count == 1:
        log("\n✅✅✅ 測試通過！分佈式鎖正常工作！", GREEN)
        log("系統正確確保了同一時間只有一個回測執行。", GREEN)
        return True
    elif success_count == 0 and blocked_count == 0:
        log("\n⚠️  兩個請求都失敗了，請檢查錯誤訊息", YELLOW)
        return False
    else:
        log("\n❌ 測試失敗！分佈式鎖可能有問題！", RED)
        log(f"預期: 1 成功 + 1 被阻擋，實際: {success_count} 成功 + {blocked_count} 被阻擋", RED)
        return False

if __name__ == "__main__":
    try:
        # Setup test data
        test_data = setup_test_data()
        if not test_data:
            log("\n❌ 測試資料準備失敗，中止測試", RED)
            exit(1)

        # Run concurrent test
        results = test_concurrent_execution(test_data)

        # Analyze results
        success = analyze_results(results)

        log("\n" + "=" * 50, BLUE)
        log("測試完成", BLUE)
        log("=" * 50, BLUE)

        exit(0 if success else 1)

    except Exception as e:
        log(f"\n❌ 測試過程發生異常: {str(e)}", RED)
        import traceback
        traceback.print_exc()
        exit(1)
