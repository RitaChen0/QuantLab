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
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800  # 30 分鐘超時
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
        logger.error("Shioaji sync timed out after 30 minutes")
        return {
            "status": "error",
            "message": "Shioaji sync timed out",
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
    同步熱門股票的 Shioaji 分鐘線數據（快速任務）

    僅同步市值前 50 大股票，用於日常增量更新
    """
    try:
        logger.info("Starting Shioaji top 50 stocks sync...")

        # 熱門股票清單（市值前 50 大）
        top_50_stocks = [
            '2330', '2317', '2454', '2412', '3008',  # 台積電、鴻海、聯發科、中華電、大立光
            '2308', '2882', '1301', '1303', '2002',  # 台達電、國泰金、台塑、南亞、中鋼
            '2886', '2881', '2891', '2892', '2885',  # 兆豐金、富邦金、中信金、第一金、元大金
            '2884', '2887', '2883', '5880', '2912',  # 玉山金、台新金、開發金、合庫金、統一超
            '2880', '2382', '2395', '6505', '3045',  # 華南金、廣達、研華、台塑化、台灣大
            '1216', '2357', '1326', '2303', '2379',  # 統一、華碩、台化、聯電、瑞昱
            '2408', '2207', '2327', '3711', '2474',  # 南亞科、和泰車、國巨、日月光投控、可成
            '2801', '2609', '2615', '2603', '4904',  # 彰銀、陽明、萬海、長榮、遠傳
            '9910', '2888', '2345', '6669', '2409',  # 豐泰、新光金、智邦、緯穎、友達
            '3037', '2377', '2353', '5871', '2324',  # 欣興、微星、宏碁、中租-KY、仁寶
        ]

        # 調用完整同步任務
        return sync_shioaji_minute_data(
            stock_ids=top_50_stocks,
            smart_mode=True,
            end_date=None  # 使用今天
        )

    except Exception as e:
        logger.error(f"Failed to sync top stocks: {str(e)}")
        # 使用指數退避：10m, 20m, 40m
        retry_count = self.request.retries
        countdown = 600 * (2 ** retry_count)
        raise self.retry(exc=e, countdown=countdown, max_retries=3)
