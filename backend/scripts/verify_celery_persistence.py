#!/usr/bin/env python3
"""
驗證 Celery Beat 持久化機制
測試重啟後能否正確保留任務執行狀態
"""
import shelve
import sys
from datetime import datetime
from pathlib import Path


def verify_schedule_file():
    """驗證 schedule 文件存在性和可訪問性"""
    schedule_path = Path("/app/celerybeat-schedule.db")

    if not schedule_path.exists():
        print("❌ Schedule 文件不存在")
        return False

    print(f"✅ Schedule 文件存在: {schedule_path}")
    print(f"   大小: {schedule_path.stat().st_size} bytes")
    print(f"   修改時間: {datetime.fromtimestamp(schedule_path.stat().st_mtime)}")

    # 嘗試讀取內容
    try:
        with shelve.open(str(schedule_path.with_suffix("")), flag='r') as db:
            entries = dict(db.get("entries", {}))
            print(f"\n✅ 成功讀取持久化數據")
            print(f"   註冊的任務數量: {len(entries)}")

            # 查找 sync-shioaji-minute-daily 任務
            target_task = "sync-shioaji-minute-daily"
            if target_task in entries:
                entry = entries[target_task]
                print(f"\n✅ 找到目標任務: {target_task}")
                print(f"   任務名稱: {entry.name}")
                print(f"   排程: {entry.schedule}")
                if hasattr(entry, "last_run_at"):
                    print(f"   最後執行: {entry.last_run_at}")
                if hasattr(entry, "total_run_count"):
                    print(f"   執行次數: {entry.total_run_count}")
            else:
                print(f"\n⚠️  未找到任務: {target_task}")
                print(f"   可用任務: {', '.join(entries.keys())}")

        return True
    except Exception as e:
        print(f"❌ 讀取 schedule 文件失敗: {e}")
        return False


def test_persistence():
    """測試持久化機制"""
    print("=" * 60)
    print("Celery Beat 持久化機制驗證")
    print("=" * 60)
    print()

    # 驗證文件
    if not verify_schedule_file():
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ 持久化機制驗證通過")
    print("=" * 60)
    print("\n建議測試步驟：")
    print("1. 記錄當前時間和文件內容")
    print("2. 重啟 celery-beat 容器")
    print("3. 再次運行此腳本驗證狀態保留")
    print("\n命令：")
    print("  docker compose restart celery-beat")
    print("  docker compose exec celery-beat python /app/scripts/verify_celery_persistence.py")


if __name__ == "__main__":
    test_persistence()
