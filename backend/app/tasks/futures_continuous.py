"""
Celery tasks for futures continuous contract generation
"""

from celery import Task
from app.core.celery_app import celery_app
from app.utils.task_history import record_task_history
from app.utils.alert import send_alert, AlertLevel
from loguru import logger
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
import subprocess
import sys


@celery_app.task(bind=True, name="app.tasks.generate_continuous_contracts")
@record_task_history
def generate_continuous_contracts(
    self: Task,
    symbols: list = None,
    days_back: int = 90
) -> dict:
    """
    生成期貨連續合約（TX 和 MTX）

    每週自動執行，更新連續合約數據。
    讀取最近 N 天的月份合約數據並拼接為連續合約。

    Args:
        symbols: 期貨代碼列表（默認: ['TX', 'MTX']）
        days_back: 回溯天數（默認: 90 天）

    Returns:
        Task result with generation statistics
    """
    if symbols is None:
        symbols = ['TX', 'MTX']

    try:
        logger.info(f"Starting continuous contract generation for {symbols}...")

        # 計算日期範圍
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)

        results = []

        for symbol in symbols:
            logger.info(f"Generating continuous contract for {symbol}...")

            # 準備命令
            cmd = [
                sys.executable,
                "/app/scripts/generate_continuous_contract.py",
                "--symbol", symbol,
                "--start-date", start_date.strftime('%Y-%m-%d'),
                "--end-date", end_date.strftime('%Y-%m-%d'),
                "--switch-days", "3"
            ]

            logger.info(f"Executing: {' '.join(cmd)}")

            # 執行生成腳本
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 分鐘超時
            )

            # 保存完整日誌到文件
            log_dir = Path("/tmp/futures_logs")
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / f"continuous_{symbol}_{datetime.now():%Y%m%d_%H%M%S}.log"

            try:
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write(f"Command: {' '.join(cmd)}\n")
                    f.write(f"Return Code: {result.returncode}\n")
                    f.write(f"\n=== STDOUT ===\n{result.stdout}\n")
                    f.write(f"\n=== STDERR ===\n{result.stderr}\n")
            except Exception as e:
                logger.warning(f"[TASK] Failed to write log file: {e}")

            if result.returncode == 0:
                logger.info(f"[TASK] {symbol} continuous contract generated successfully")
                results.append({
                    "symbol": symbol,
                    "status": "success",
                    "log_file": str(log_file),
                    "output_preview": result.stdout[-300:] if result.stdout else ""
                })
            else:
                logger.error(f"[TASK] {symbol} continuous contract generation failed")
                logger.error(f"[TASK] Error: {result.stderr[:500]}")

                # 發送告警
                send_alert(
                    level=AlertLevel.ERROR,
                    title=f"Continuous contract generation failed: {symbol}",
                    message=f"Failed to generate {symbol} continuous contract",
                    details={
                        "symbol": symbol,
                        "error": result.stderr[:500],
                        "log_file": str(log_file)
                    },
                    task_id=self.request.id if hasattr(self.request, 'id') else None
                )

                results.append({
                    "symbol": symbol,
                    "status": "error",
                    "log_file": str(log_file),
                    "error_preview": result.stderr[-300:] if result.stderr else ""
                })

        # 統計結果
        success_count = sum(1 for r in results if r["status"] == "success")
        total_count = len(results)

        return {
            "status": "success" if success_count == total_count else "partial",
            "message": f"Generated {success_count}/{total_count} continuous contracts",
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except subprocess.TimeoutExpired:
        logger.error("Continuous contract generation timed out")
        return {
            "status": "error",
            "message": "Continuous contract generation timed out",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to generate continuous contracts: {str(e)}")
        # 使用指數退避重試
        retry_count = self.request.retries
        countdown = 600 * (2 ** retry_count)
        raise self.retry(exc=e, countdown=countdown, max_retries=3)


@celery_app.task(bind=True, name="app.tasks.register_new_futures_contracts")
@record_task_history
def register_new_futures_contracts(self: Task, year: int = None) -> dict:
    """
    註冊新年度的期貨月份合約

    每年 1 月 1 日自動執行，為新的一年註冊月份合約。

    Args:
        year: 要註冊的年份（默認: 明年）

    Returns:
        Task result
    """
    try:
        if year is None:
            year = date.today().year + 1

        logger.info(f"Registering futures contracts for year {year}...")

        # 準備命令
        cmd = [
            sys.executable,
            "/app/scripts/register_futures_contracts.py",
            "--symbols", "TX,MTX",
            "--start-year", str(year),
            "--end-year", str(year)
        ]

        logger.info(f"Executing: {' '.join(cmd)}")

        # 執行註冊腳本
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 分鐘超時
        )

        # 保存完整日誌到文件
        log_dir = Path("/tmp/futures_logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"register_{year}_{datetime.now():%Y%m%d_%H%M%S}.log"

        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"Command: {' '.join(cmd)}\n")
                f.write(f"Return Code: {result.returncode}\n")
                f.write(f"\n=== STDOUT ===\n{result.stdout}\n")
                f.write(f"\n=== STDERR ===\n{result.stderr}\n")
        except Exception as e:
            logger.warning(f"[TASK] Failed to write log file: {e}")

        if result.returncode == 0:
            logger.info(f"[TASK] Futures contracts for {year} registered successfully")
            return {
                "status": "success",
                "message": f"Registered futures contracts for {year}",
                "log_file": str(log_file),
                "output_preview": result.stdout[-300:] if result.stdout else "",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            logger.error(f"[TASK] Failed to register contracts for {year}")
            logger.error(f"[TASK] Error: {result.stderr[:500]}")

            # 發送告警
            send_alert(
                level=AlertLevel.ERROR,
                title=f"Futures contract registration failed: {year}",
                message=f"Failed to register futures contracts for year {year}",
                details={
                    "year": year,
                    "error": result.stderr[:500],
                    "log_file": str(log_file)
                },
                task_id=self.request.id if hasattr(self.request, 'id') else None
            )

            return {
                "status": "error",
                "message": "Failed to register futures contracts",
                "log_file": str(log_file),
                "error_preview": result.stderr[-300:] if result.stderr else "",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    except subprocess.TimeoutExpired:
        logger.error("Contract registration timed out")
        return {
            "status": "error",
            "message": "Contract registration timed out",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to register futures contracts: {str(e)}")
        raise
