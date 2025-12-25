"""
資料庫完整性檢查和自動修復任務

每日自動執行：
1. 檢查日線數據完整性
2. 檢查分鐘線數據完整性
3. 檢查 Qlib 數據一致性
4. 自動修復可修復的缺失
5. 生成報告並記錄問題
"""

from celery import shared_task
from celery.utils.log import get_task_logger
import subprocess
from pathlib import Path

logger = get_task_logger(__name__)


@shared_task(bind=True, name="app.tasks.check_database_integrity")
def check_database_integrity(self, auto_fix: bool = False):
    """
    資料庫完整性檢查

    Args:
        auto_fix: 是否自動修復缺失（默認 False）

    Returns:
        dict: 檢查結果
    """
    logger.info("=" * 60)
    logger.info("🏥 開始資料庫完整性檢查")
    logger.info("=" * 60)

    script_path = Path("/app/scripts/check_database_integrity.py")

    if not script_path.exists():
        logger.error(f"❌ 檢查腳本不存在: {script_path}")
        return {"success": False, "error": "檢查腳本不存在"}

    try:
        # 執行檢查
        args = ["python", str(script_path), "--check-all"]

        if auto_fix:
            args.append("--fix-all")
            logger.info("🔧 啟用自動修復模式")

        result = subprocess.run(
            args,
            cwd="/app",
            capture_output=True,
            text=True,
            timeout=600  # 10 分鐘超時
        )

        # 記錄輸出
        if result.stdout:
            for line in result.stdout.split('\n'):
                if line.strip():
                    logger.info(line)

        if result.stderr:
            for line in result.stderr.split('\n'):
                if line.strip():
                    logger.warning(line)

        # 檢查結果
        if result.returncode == 0:
            logger.info("✅ 資料庫完整性檢查完成")
            return {"success": True, "output": result.stdout}
        else:
            logger.error(f"❌ 資料庫完整性檢查失敗 (exit code: {result.returncode})")
            return {"success": False, "error": result.stderr, "exit_code": result.returncode}

    except subprocess.TimeoutExpired:
        logger.error("❌ 資料庫完整性檢查超時（10 分鐘）")
        return {"success": False, "error": "執行超時"}
    except Exception as e:
        logger.error(f"❌ 執行檢查時發生錯誤: {e}")
        return {"success": False, "error": str(e)}


@shared_task(bind=True, name="app.tasks.auto_fix_database")
def auto_fix_database(self):
    """
    自動修復資料庫缺失

    檢查並自動修復：
    1. 日線缺失（使用分鐘線聚合）
    2. 分鐘線缺失（使用 Shioaji API）
    """
    logger.info("=" * 60)
    logger.info("🔧 開始自動修復資料庫缺失")
    logger.info("=" * 60)

    return check_database_integrity(self, auto_fix=True)
