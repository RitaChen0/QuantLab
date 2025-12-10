#!/usr/bin/env python3
"""
測試活躍任務 API
"""

import requests
import json
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
    print_colored("=" * 60, BLUE)
    print_colored("測試活躍任務 API", BLUE)
    print_colored("=" * 60, BLUE)
    print()

    # Step 1: Login
    print_colored("Step 1: 登入獲取 Token", YELLOW)
    login_response = requests.post(
        f"{API_BASE}/api/v1/auth/login",
        json={"username": "locktest2", "password": "password123"}
    )

    if login_response.status_code != 200:
        print_colored(f"❌ 登入失敗: {login_response.text}", RED)
        return

    token = login_response.json()["access_token"]
    print_colored(f"✅ 登入成功", GREEN)
    print_colored(f"Token: {token[:20]}...\n", GREEN)

    headers = {"Authorization": f"Bearer {token}"}

    # Step 2: Get active tasks
    print_colored("Step 2: 查詢活躍任務", YELLOW)
    response = requests.get(
        f"{API_BASE}/api/v1/backtest/tasks/active",
        headers=headers
    )

    if response.status_code != 200:
        print_colored(f"❌ API 調用失敗: {response.text}", RED)
        return

    data = response.json()
    print_colored("✅ API 調用成功\n", GREEN)

    # Display results
    print_colored("=" * 60, BLUE)
    print_colored("📊 任務狀態總覽", BLUE)
    print_colored("=" * 60, BLUE)

    summary = data.get("summary", {})
    print_colored(f"  正在執行: {summary.get('active_count', 0)} 個任務", YELLOW)
    print_colored(f"  排隊中:   {summary.get('queued_count', 0)} 個任務", YELLOW)
    print_colored(f"  Workers: {summary.get('total_workers', 0)} 個", YELLOW)
    print()

    # Active tasks
    active_tasks = data.get("active_tasks", [])
    if active_tasks:
        print_colored("🔄 正在執行的任務:", GREEN)
        for task in active_tasks:
            print(f"  - Task ID: {task['task_id'][:8]}...")
            print(f"    Backtest ID: {task['backtest_id']}")
            print(f"    進度: {task['progress']}%")
            print(f"    狀態: {task['status']}")
            print(f"    Worker: {task['worker']}")
            print()
    else:
        print_colored("✅ 目前沒有任務正在執行", GREEN)
        print()

    # Queued tasks
    queued_tasks = data.get("queued_tasks", [])
    if queued_tasks:
        print_colored("⏳ 排隊中的任務:", YELLOW)
        for task in queued_tasks:
            print(f"  - Task ID: {task['task_id'][:8]}...")
            print(f"    Backtest ID: {task['backtest_id']}")
            print(f"    Worker: {task['worker']}")
            print()
    else:
        print_colored("✅ 沒有任務在排隊", GREEN)
        print()

    # Worker info
    worker_info = data.get("worker_info", [])
    if worker_info:
        print_colored("⚙️  Worker 狀態:", BLUE)
        for worker in worker_info:
            print(f"  - {worker['name']}")
            print(f"    並發數: {worker['concurrency']}")
            print(f"    運行時間: {worker['uptime']} 秒")
            total_tasks = worker.get('total_tasks', {})
            if total_tasks:
                print(f"    已執行任務:")
                for task_name, count in total_tasks.items():
                    if 'backtest' in task_name:
                        print(f"      • {task_name}: {count}")
            print()

    print_colored("=" * 60, BLUE)
    print_colored(f"查詢時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", BLUE)
    print_colored("=" * 60, BLUE)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print_colored(f"\n❌ 錯誤: {str(e)}", RED)
        import traceback
        traceback.print_exc()
