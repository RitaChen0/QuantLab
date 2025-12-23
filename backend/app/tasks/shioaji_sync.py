"""
Celery tasks for Shioaji minute data synchronization
"""

from celery import Task
from app.core.celery_app import celery_app
from app.utils.task_history import record_task_history
from app.utils.task_deduplication import skip_if_recently_executed
from loguru import logger
from datetime import datetime, timezone, date, timedelta
from typing import List, Optional
import subprocess
import sys
from redis import Redis
from app.core.config import settings


@celery_app.task(bind=True, name="app.tasks.sync_shioaji_minute_data")
@record_task_history
def sync_shioaji_minute_data(
    self: Task,
    stock_ids: Optional[List[str]] = None,
    smart_mode: bool = True,
    end_date: Optional[str] = None
) -> dict:
    """
    同步 Shioaji 分鐘線數據到 PostgreSQL + Qlib

    Args:
        stock_ids: 股票代碼列表（None 表示同步所有股票）
        smart_mode: 使用智慧增量同步（預設 True）
        end_date: 結束日期（YYYY-MM-DD，預設為今天）

    Returns:
        Task result with sync statistics
    """
    import select
    import time

    try:
        logger.info("=" * 60)
        logger.info("🚀 Starting Shioaji minute data synchronization...")
        logger.info(f"📊 Mode: {'Smart (Incremental)' if smart_mode else 'Today Only'}")
        logger.info(f"📅 End Date: {end_date or 'Today'}")
        logger.info(f"📈 Stocks: {len(stock_ids) if stock_ids else 'All'}")
        logger.info("=" * 60)

        # 準備命令參數
        cmd = [
            sys.executable,  # 使用當前 Python 解釋器
            "/app/scripts/sync_shioaji_to_qlib.py"
        ]

        # 添加模式參數
        if smart_mode:
            cmd.append("--smart")
        else:
            cmd.append("--today")

        # 添加結束日期
        if end_date:
            cmd.extend(["--end-date", end_date])

        # 添加股票清單
        if stock_ids:
            cmd.extend(["--stocks", ",".join(stock_ids)])

        # 執行同步腳本
        logger.info(f"🔧 Command: {' '.join(cmd)}")

        # 根據是否指定股票列表來設定超時時間
        # 所有股票：4 小時，指定股票：30 分鐘
        timeout = 14400 if not stock_ids else 1800
        logger.info(f"⏱️  Timeout: {timeout}s ({timeout//3600}h {(timeout%3600)//60}m)")

        # 使用 Popen 實時輸出日誌
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # 合併 stderr 到 stdout
            text=True,
            bufsize=1,  # 行緩衝
            universal_newlines=True
        )

        logger.info("📝 Script started, streaming logs...")
        logger.info("-" * 60)

        # 實時讀取輸出
        output_lines = []
        start_time = time.time()
        last_log_time = start_time

        while True:
            # 檢查超時
            if time.time() - start_time > timeout:
                process.kill()
                logger.error(f"❌ Process timeout after {timeout}s")
                raise subprocess.TimeoutExpired(cmd, timeout)

            # 讀取一行輸出
            line = process.stdout.readline()
            if line:
                # 輸出到日誌
                logger.info(f"[SCRIPT] {line.rstrip()}")
                output_lines.append(line)
                last_log_time = time.time()

            # 檢查進程是否結束
            if process.poll() is not None:
                break

            # 如果 30 秒沒有輸出，記錄一下（避免以為卡住）
            if time.time() - last_log_time > 30:
                logger.info(f"⏳ Still running... ({int(time.time() - start_time)}s elapsed)")
                last_log_time = time.time()

        # 讀取剩餘輸出
        remaining = process.stdout.read()
        if remaining:
            for line in remaining.splitlines():
                logger.info(f"[SCRIPT] {line}")
                output_lines.append(line + '\n')

        returncode = process.wait()
        elapsed = time.time() - start_time

        logger.info("-" * 60)
        logger.info(f"⏱️  Elapsed time: {int(elapsed)}s ({int(elapsed//60)}m {int(elapsed%60)}s)")
        logger.info(f"🔚 Process exited with code: {returncode}")

        # 檢查執行結果
        if returncode == 0:
            logger.info("✅ Shioaji sync completed successfully")

            return {
                "status": "success",
                "message": "Shioaji minute data synchronized",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": int(elapsed),
                "output": ''.join(output_lines[-20:]) if output_lines else "",  # 保留最後 20 行
            }
        else:
            logger.error(f"❌ Shioaji sync failed with code {returncode}")
            return {
                "status": "error",
                "message": f"Shioaji sync failed (exit code {returncode})",
                "error": ''.join(output_lines[-20:]) if output_lines else "",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    except subprocess.TimeoutExpired:
        timeout_msg = "4 hours" if not stock_ids else "30 minutes"
        logger.error(f"❌ Shioaji sync timed out after {timeout_msg}")
        return {
            "status": "error",
            "message": f"Shioaji sync timed out after {timeout_msg}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Failed to sync Shioaji data: {str(e)}")
        logger.exception("Full traceback:")
        # 使用指數退避：10m, 20m, 40m
        retry_count = self.request.retries
        countdown = 600 * (2 ** retry_count)
        raise self.retry(exc=e, countdown=countdown, max_retries=3)


@celery_app.task(bind=True, name="app.tasks.sync_shioaji_top_stocks")
@skip_if_recently_executed(min_interval_hours=24)
@record_task_history
def sync_shioaji_top_stocks(self: Task) -> dict:
    """
    同步所有股票的 Shioaji 分鐘線數據（完整同步）

    從資料庫 stock_prices 表自動獲取所有股票，用於日常增量更新。
    使用智慧增量模式，只同步缺失的日期範圍。

    執行時間：約 2-4 小時（視股票數量和缺失數據量而定）
    """
    # 使用 Redis 鎖防止重複執行
    redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    lock_key = f"task_lock:{self.name}"
    # 4 小時超時（匹配任務預計執行時間）
    lock = redis_client.lock(lock_key, timeout=14400)

    # 嘗試獲取鎖（非阻塞）
    if not lock.acquire(blocking=False):
        logger.warning(f"⚠️  任務 {self.name} 已在執行中，跳過此次觸發")
        logger.info(f"   鎖定 Key: {lock_key}")
        return {
            "status": "skipped",
            "message": "Task is already running, skipped to prevent duplicate execution",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "lock_key": lock_key
        }

    try:
        logger.info("✅ 獲取任務鎖成功，開始執行...")
        logger.info("Starting Shioaji all stocks sync...")
        logger.info("Stock list will be automatically fetched from database (stock_prices table)")

        # 調用完整同步任務，stock_ids=None 表示同步所有股票
        # 腳本會自動從資料庫 stock_prices 表獲取股票清單
        result = sync_shioaji_minute_data(
            stock_ids=None,  # None = 同步所有股票（從資料庫自動獲取）
            smart_mode=True,  # 智慧增量同步
            end_date=None  # 使用今天
        )

        return result

    except Exception as e:
        logger.error(f"Failed to sync all stocks: {str(e)}")
        # 使用指數退避：10m, 20m, 40m
        retry_count = self.request.retries
        countdown = 600 * (2 ** retry_count)
        raise self.retry(exc=e, countdown=countdown, max_retries=3)

    finally:
        # 確保釋放鎖
        try:
            lock.release()
            logger.info("🔓 任務鎖已釋放")
        except Exception as e:
            logger.warning(f"釋放鎖時發生錯誤: {e}")


@celery_app.task(bind=True, name="app.tasks.sync_shioaji_futures")
@skip_if_recently_executed(min_interval_hours=24)
@record_task_history
def sync_shioaji_futures(self: Task) -> dict:
    """
    同步期货分鐘線數據（TX + MTX）

    每日定時同步台指期货（TX）和小台指期货（MTX）的分鐘線數據。
    使用智慧增量模式，只同步缺失的日期範圍。

    執行時間：約 5-10 分鐘（期货仅 2 档）
    """
    # 使用 Redis 鎖防止重複執行
    redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    lock_key = f"task_lock:{self.name}"
    # 30 分鐘超時（匹配任務預計執行時間）
    lock = redis_client.lock(lock_key, timeout=1800)

    # 嘗試獲取鎖（非阻塞）
    if not lock.acquire(blocking=False):
        logger.warning(f"⚠️  任務 {self.name} 已在執行中，跳過此次觸發")
        logger.info(f"   鎖定 Key: {lock_key}")
        return {
            "status": "skipped",
            "message": "Task is already running, skipped to prevent duplicate execution",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "lock_key": lock_key
        }

    try:
        logger.info("✅ 獲取任務鎖成功，開始執行...")
        logger.info("Starting Shioaji futures sync (TX + MTX)...")

        # 調用同步任務，僅同步期货
        result = sync_shioaji_minute_data(
            stock_ids=['TX', 'MTX'],  # 仅期货
            smart_mode=True,          # 智慧增量同步
            end_date=None             # 使用今天
        )

        return result

    except Exception as e:
        logger.error(f"Failed to sync futures: {str(e)}")
        # 使用指數退避：10m, 20m, 40m
        retry_count = self.request.retries
        countdown = 600 * (2 ** retry_count)
        raise self.retry(exc=e, countdown=countdown, max_retries=3)

    finally:
        # 確保釋放鎖
        try:
            lock.release()
            logger.info("🔓 任務鎖已釋放")
        except Exception as e:
            logger.warning(f"釋放鎖時發生錯誤: {e}")
