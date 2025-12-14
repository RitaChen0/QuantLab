"""
Celery tasks for Shioaji minute data synchronization
"""

from celery import Task
from app.core.celery_app import celery_app
from app.utils.task_history import record_task_history
from loguru import logger
from datetime import datetime, timezone, date, timedelta
from typing import List, Optional
import subprocess
import sys


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
    try:
        logger.info("Starting Shioaji minute data synchronization...")

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
        logger.info(f"Executing command: {' '.join(cmd)}")

        # 根據是否指定股票列表來設定超時時間
        # 所有股票：4 小時，指定股票：30 分鐘
        timeout = 14400 if not stock_ids else 1800

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        # 檢查執行結果
        if result.returncode == 0:
            logger.info("Shioaji sync completed successfully")
            logger.debug(f"Output: {result.stdout}")

            return {
                "status": "success",
                "message": "Shioaji minute data synchronized",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "output": result.stdout[-500:] if result.stdout else "",  # 保留最後 500 字元
            }
        else:
            logger.error(f"Shioaji sync failed: {result.stderr}")
            return {
                "status": "error",
                "message": "Shioaji sync failed",
                "error": result.stderr[-500:] if result.stderr else "",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    except subprocess.TimeoutExpired:
        timeout_msg = "4 hours" if not stock_ids else "30 minutes"
        logger.error(f"Shioaji sync timed out after {timeout_msg}")
        return {
            "status": "error",
            "message": f"Shioaji sync timed out after {timeout_msg}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to sync Shioaji data: {str(e)}")
        # 使用指數退避：10m, 20m, 40m
        retry_count = self.request.retries
        countdown = 600 * (2 ** retry_count)
        raise self.retry(exc=e, countdown=countdown, max_retries=3)


@celery_app.task(bind=True, name="app.tasks.sync_shioaji_top_stocks")
@record_task_history
def sync_shioaji_top_stocks(self: Task) -> dict:
    """
    同步所有股票的 Shioaji 分鐘線數據（完整同步）

    從資料庫 stock_prices 表自動獲取所有股票，用於日常增量更新。
    使用智慧增量模式，只同步缺失的日期範圍。

    執行時間：約 2-4 小時（視股票數量和缺失數據量而定）
    """
    try:
        logger.info("Starting Shioaji all stocks sync...")
        logger.info("Stock list will be automatically fetched from database (stock_prices table)")

        # 調用完整同步任務，stock_ids=None 表示同步所有股票
        # 腳本會自動從資料庫 stock_prices 表獲取股票清單
        return sync_shioaji_minute_data(
            stock_ids=None,  # None = 同步所有股票（從資料庫自動獲取）
            smart_mode=True,  # 智慧增量同步
            end_date=None  # 使用今天
        )

    except Exception as e:
        logger.error(f"Failed to sync all stocks: {str(e)}")
        # 使用指數退避：10m, 20m, 40m
        retry_count = self.request.retries
        countdown = 600 * (2 ** retry_count)
        raise self.retry(exc=e, countdown=countdown, max_retries=3)


@celery_app.task(bind=True, name="app.tasks.sync_shioaji_futures")
@record_task_history
def sync_shioaji_futures(self: Task) -> dict:
    """
    同步期货分鐘線數據（TX + MTX）

    每日定時同步台指期货（TX）和小台指期货（MTX）的分鐘線數據。
    使用智慧增量模式，只同步缺失的日期範圍。

    執行時間：約 5-10 分鐘（期货仅 2 档）
    """
    try:
        logger.info("Starting Shioaji futures sync (TX + MTX)...")

        # 調用同步任務，僅同步期货
        return sync_shioaji_minute_data(
            stock_ids=['TX', 'MTX'],  # 仅期货
            smart_mode=True,          # 智慧增量同步
            end_date=None             # 使用今天
        )

    except Exception as e:
        logger.error(f"Failed to sync futures: {str(e)}")
        # 使用指數退避：10m, 20m, 40m
        retry_count = self.request.retries
        countdown = 600 * (2 ** retry_count)
        raise self.retry(exc=e, countdown=countdown, max_retries=3)
