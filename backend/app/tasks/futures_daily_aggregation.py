"""
TX 期貨日線聚合 Celery 任務

自動從分鐘線聚合生成日線數據，供 RD-Agent 使用
"""

from celery import Task
from celery.utils.log import get_task_logger
import subprocess
import sys
from pathlib import Path

from app.core.celery_app import celery_app
from app.utils.task_history import record_task_history
from app.utils.task_deduplication import skip_if_recently_executed

logger = get_task_logger(__name__)


@celery_app.task(bind=True, name="app.tasks.generate_tx_daily_from_minute")
@skip_if_recently_executed(min_interval_hours=23)  # 每天最多執行一次
@record_task_history
def generate_tx_daily_from_minute(self: Task, contract: str = "TX202512") -> dict:
    """
    從期貨分鐘線聚合生成日線數據

    Args:
        contract: 期貨合約代碼（預設 TX202512）

    Returns:
        dict: 執行結果
    """
    logger.info("=" * 80)
    logger.info("🚀 TX 期貨日線數據聚合任務")
    logger.info("=" * 80)
    logger.info(f"📊 合約：{contract}")

    script_path = Path("/app/scripts/generate_tx_daily_from_minute.py")

    if not script_path.exists():
        logger.error(f"❌ 腳本不存在：{script_path}")
        return {"success": False, "error": "腳本不存在"}

    try:
        # 執行聚合腳本
        cmd = [
            sys.executable,
            str(script_path),
            "--contract", contract
        ]

        logger.info(f"🔧 執行命令：{' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            cwd="/app",
            capture_output=True,
            text=True,
            timeout=300  # 5 分鐘超時
        )

        # 記錄輸出
        if result.stdout:
            for line in result.stdout.split('\n'):
                if line.strip():
                    logger.info(line)

        if result.stderr:
            for line in result.stderr.split('\n'):
                if line.strip() and 'WARNING' not in line:  # 過濾掉警告
                    logger.warning(line)

        # 檢查結果
        if result.returncode == 0:
            logger.info("✅ TX 期貨日線聚合完成")
            return {
                "success": True,
                "contract": contract,
                "message": "TX 期貨日線數據已更新"
            }
        else:
            logger.error(f"❌ TX 期貨日線聚合失敗 (exit code: {result.returncode})")
            return {
                "success": False,
                "error": result.stderr,
                "exit_code": result.returncode
            }

    except subprocess.TimeoutExpired:
        logger.error("❌ TX 期貨日線聚合超時（5 分鐘）")
        return {"success": False, "error": "執行超時"}
    except Exception as e:
        logger.error(f"❌ 執行時發生錯誤：{e}")
        return {"success": False, "error": str(e)}
