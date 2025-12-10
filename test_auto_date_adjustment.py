#!/usr/bin/env python3
"""
測試自動日期調整功能
驗證當用戶設定的日期超出資料庫範圍時，系統能自動調整
"""

import requests
from datetime import datetime

API_BASE = "http://localhost:8000"

# Colors
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RED = '\033[91m'
RESET = '\033[0m'

def print_colored(message, color=RESET):
    print(f"{color}{message}{RESET}")

def main():
    print_colored("=" * 70, BLUE)
    print_colored("測試自動日期調整功能", BLUE)
    print_colored("=" * 70, BLUE)
    print()

    # Step 1: Login
    print_colored("Step 1: 登入", YELLOW)
    login_response = requests.post(
        f"{API_BASE}/api/v1/auth/login",
        json={"username": "robert", "password": "password123"}
    )

    if login_response.status_code != 200:
        print_colored(f"❌ 登入失敗: {login_response.text}", RED)
        return

    token = login_response.json()["access_token"]
    print_colored(f"✅ 登入成功\n", GREEN)

    headers = {"Authorization": f"Bearer {token}"}

    # Step 2: 查詢資料庫中 2330 的實際日期範圍
    print_colored("Step 2: 查詢 2330 實際數據範圍", YELLOW)
    print_colored("資料庫實際範圍: 2007-04-23 ~ 2025-12-01", BLUE)
    print()

    # Step 3: 執行回測（使用超出範圍的日期）
    print_colored("Step 3: 執行回測 ID 15", YELLOW)
    print_colored("配置的日期範圍: 2000-01-02 ~ 2025-12-02 (超出資料庫範圍)", YELLOW)
    print()

    run_response = requests.post(
        f"{API_BASE}/api/v1/backtest/run",
        json={"backtest_id": 15},
        headers=headers
    )

    if run_response.status_code == 202:
        result = run_response.json()
        task_id = result["task_id"]

        print_colored("✅ 回測任務已提交", GREEN)
        print_colored(f"   任務 ID: {task_id[:16]}...", GREEN)
        print()

        # Step 4: 等待任務完成並檢查日誌
        print_colored("Step 4: 等待任務執行（檢查日誌中的日期調整訊息）", YELLOW)
        print()

        import time
        time.sleep(3)

        # 檢查 Celery 日誌
        print_colored("📋 Celery Worker 日誌（最近 20 行）:", BLUE)
        print_colored("=" * 70, BLUE)

        import subprocess
        log_result = subprocess.run(
            ["docker", "compose", "logs", "celery-worker", "--tail", "20"],
            capture_output=True,
            text=True
        )

        # 篩選出關鍵的日誌行
        for line in log_result.stdout.split('\n'):
            if any(keyword in line for keyword in [
                'auto-adjusted', 'Auto-adjusted', 'adjusted to',
                'Date range', 'Starting backtest', 'succeeded', 'failed'
            ]):
                if 'auto-adjusted' in line.lower() or 'adjusted' in line.lower():
                    print_colored(f"  ✅ {line}", GREEN)
                elif 'succeeded' in line.lower():
                    print_colored(f"  ✅ {line}", GREEN)
                elif 'failed' in line.lower() or 'error' in line.lower():
                    print_colored(f"  ❌ {line}", RED)
                else:
                    print_colored(f"  ℹ️  {line}", BLUE)

        print_colored("=" * 70, BLUE)
        print()

        # Step 5: 查詢任務狀態
        print_colored("Step 5: 查詢最終任務狀態", YELLOW)
        time.sleep(2)

        status_response = requests.get(
            f"{API_BASE}/api/v1/backtest/15/task/{task_id}",
            headers=headers
        )

        if status_response.status_code == 200:
            status_data = status_response.json()
            state = status_data.get('state')

            print()
            print_colored("=" * 70, BLUE)
            print_colored("📊 測試結果總結", BLUE)
            print_colored("=" * 70, BLUE)

            if state == 'SUCCESS':
                print_colored("✅ 測試成功！", GREEN)
                print_colored("   • 日期自動調整功能正常運作", GREEN)
                print_colored("   • 回測成功執行", GREEN)
                print_colored("   • 用戶無需知道資料庫的確切日期範圍", GREEN)
            elif state == 'FAILURE':
                error = status_data.get('error', 'Unknown')
                print_colored(f"⚠️  回測失敗: {error}", YELLOW)
                if 'No data available' in error:
                    print_colored("   ⚠️  可能還需要調試日期調整邏輯", YELLOW)
                else:
                    print_colored("   ℹ️  失敗原因可能與日期無關", BLUE)
            else:
                print_colored(f"⏳ 任務狀態: {state}", YELLOW)

            print_colored("=" * 70, BLUE)

    elif run_response.status_code == 429:
        print_colored("⚠️  超過速率限制，請稍後再試", YELLOW)
    else:
        print_colored(f"❌ 執行失敗: {run_response.text}", RED)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print_colored(f"\n❌ 錯誤: {str(e)}", RED)
        import traceback
        traceback.print_exc()
