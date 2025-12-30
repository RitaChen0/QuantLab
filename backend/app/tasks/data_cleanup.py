"""
數據清理任務 - 清理舊的任務記錄和結果

此模組包含定期清理舊數據的 Celery 任務，防止數據庫無限增長。
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.backtest import Backtest
from app.models.rdagent import RDAgentTask, TaskStatus, ModelTrainingJob
from celery import Task
from loguru import logger


@celery_app.task(bind=True, name="app.tasks.cleanup_old_backtests")
def cleanup_old_backtests(
    self: Task,
    days_to_keep: int = 90,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    清理舊的回測記錄

    Args:
        days_to_keep: 保留最近 N 天的記錄（默認 90 天）
        dry_run: 是否為測試模式（不實際刪除）

    Returns:
        清理結果統計
    """
    db: Session = SessionLocal()
    stats = {
        "task": "cleanup_old_backtests",
        "days_to_keep": days_to_keep,
        "dry_run": dry_run,
        "completed_deleted": 0,
        "failed_deleted": 0,
        "total_deleted": 0,
        "errors": []
    }

    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        logger.info(f"[CLEANUP] Starting backtest cleanup, cutoff date: {cutoff_date}")

        # 1. 清理已完成的舊回測（status = COMPLETED）
        completed_query = db.query(Backtest).filter(
            and_(
                Backtest.status == "COMPLETED",
                Backtest.created_at < cutoff_date
            )
        )

        completed_count = completed_query.count()
        logger.info(f"[CLEANUP] Found {completed_count} completed backtests older than {days_to_keep} days")

        if not dry_run and completed_count > 0:
            completed_query.delete(synchronize_session=False)
            stats["completed_deleted"] = completed_count

        # 2. 清理失敗的舊回測（status = FAILED）
        failed_query = db.query(Backtest).filter(
            and_(
                Backtest.status == "FAILED",
                Backtest.created_at < cutoff_date
            )
        )

        failed_count = failed_query.count()
        logger.info(f"[CLEANUP] Found {failed_count} failed backtests older than {days_to_keep} days")

        if not dry_run and failed_count > 0:
            failed_query.delete(synchronize_session=False)
            stats["failed_deleted"] = failed_count

        # 提交刪除
        if not dry_run:
            db.commit()
            stats["total_deleted"] = stats["completed_deleted"] + stats["failed_deleted"]
            logger.info(f"[CLEANUP] Deleted {stats['total_deleted']} old backtests")
        else:
            logger.info(f"[CLEANUP] DRY RUN: Would delete {completed_count + failed_count} backtests")

        stats["success"] = True
        stats["message"] = f"Successfully cleaned up {stats['total_deleted']} old backtests"

    except Exception as e:
        db.rollback()
        error_msg = f"Failed to cleanup backtests: {str(e)}"
        logger.error(f"[CLEANUP] {error_msg}")
        stats["success"] = False
        stats["errors"].append(error_msg)

    finally:
        db.close()

    return stats


@celery_app.task(bind=True, name="app.tasks.cleanup_old_rdagent_tasks")
def cleanup_old_rdagent_tasks(
    self: Task,
    days_to_keep: int = 90,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    清理舊的 RD-Agent 任務記錄

    Args:
        days_to_keep: 保留最近 N 天的記錄（默認 90 天）
        dry_run: 是否為測試模式（不實際刪除）

    Returns:
        清理結果統計
    """
    db: Session = SessionLocal()
    stats = {
        "task": "cleanup_old_rdagent_tasks",
        "days_to_keep": days_to_keep,
        "dry_run": dry_run,
        "completed_deleted": 0,
        "failed_deleted": 0,
        "total_deleted": 0,
        "errors": []
    }

    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        logger.info(f"[CLEANUP] Starting RD-Agent task cleanup, cutoff date: {cutoff_date}")

        # 1. 清理已完成的舊任務（status = COMPLETED）
        completed_query = db.query(RDAgentTask).filter(
            and_(
                RDAgentTask.status == TaskStatus.COMPLETED,
                RDAgentTask.created_at < cutoff_date
            )
        )

        completed_count = completed_query.count()
        logger.info(f"[CLEANUP] Found {completed_count} completed RD-Agent tasks older than {days_to_keep} days")

        if not dry_run and completed_count > 0:
            completed_query.delete(synchronize_session=False)
            stats["completed_deleted"] = completed_count

        # 2. 清理失敗的舊任務（status = FAILED）
        failed_query = db.query(RDAgentTask).filter(
            and_(
                RDAgentTask.status == TaskStatus.FAILED,
                RDAgentTask.created_at < cutoff_date
            )
        )

        failed_count = failed_query.count()
        logger.info(f"[CLEANUP] Found {failed_count} failed RD-Agent tasks older than {days_to_keep} days")

        if not dry_run and failed_count > 0:
            failed_query.delete(synchronize_session=False)
            stats["failed_deleted"] = failed_count

        # 提交刪除
        if not dry_run:
            db.commit()
            stats["total_deleted"] = stats["completed_deleted"] + stats["failed_deleted"]
            logger.info(f"[CLEANUP] Deleted {stats['total_deleted']} old RD-Agent tasks")
        else:
            logger.info(f"[CLEANUP] DRY RUN: Would delete {completed_count + failed_count} RD-Agent tasks")

        stats["success"] = True
        stats["message"] = f"Successfully cleaned up {stats['total_deleted']} old RD-Agent tasks"

    except Exception as e:
        db.rollback()
        error_msg = f"Failed to cleanup RD-Agent tasks: {str(e)}"
        logger.error(f"[CLEANUP] {error_msg}")
        stats["success"] = False
        stats["errors"].append(error_msg)

    finally:
        db.close()

    return stats


@celery_app.task(bind=True, name="app.tasks.cleanup_old_training_jobs")
def cleanup_old_training_jobs(
    self: Task,
    days_to_keep: int = 90,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    清理舊的模型訓練任務記錄

    Args:
        days_to_keep: 保留最近 N 天的記錄（默認 90 天）
        dry_run: 是否為測試模式（不實際刪除）

    Returns:
        清理結果統計
    """
    db: Session = SessionLocal()
    stats = {
        "task": "cleanup_old_training_jobs",
        "days_to_keep": days_to_keep,
        "dry_run": dry_run,
        "completed_deleted": 0,
        "failed_deleted": 0,
        "cancelled_deleted": 0,
        "total_deleted": 0,
        "errors": []
    }

    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        logger.info(f"[CLEANUP] Starting training job cleanup, cutoff date: {cutoff_date}")

        # 1. 清理已完成的舊訓練任務（status = COMPLETED）
        completed_query = db.query(ModelTrainingJob).filter(
            and_(
                ModelTrainingJob.status == "COMPLETED",
                ModelTrainingJob.created_at < cutoff_date
            )
        )

        completed_count = completed_query.count()
        logger.info(f"[CLEANUP] Found {completed_count} completed training jobs older than {days_to_keep} days")

        if not dry_run and completed_count > 0:
            completed_query.delete(synchronize_session=False)
            stats["completed_deleted"] = completed_count

        # 2. 清理失敗的舊訓練任務（status = FAILED）
        failed_query = db.query(ModelTrainingJob).filter(
            and_(
                ModelTrainingJob.status == "FAILED",
                ModelTrainingJob.created_at < cutoff_date
            )
        )

        failed_count = failed_query.count()
        logger.info(f"[CLEANUP] Found {failed_count} failed training jobs older than {days_to_keep} days")

        if not dry_run and failed_count > 0:
            failed_query.delete(synchronize_session=False)
            stats["failed_deleted"] = failed_count

        # 3. 清理已取消的舊訓練任務（status = CANCELLED）
        cancelled_query = db.query(ModelTrainingJob).filter(
            and_(
                ModelTrainingJob.status == "CANCELLED",
                ModelTrainingJob.created_at < cutoff_date
            )
        )

        cancelled_count = cancelled_query.count()
        logger.info(f"[CLEANUP] Found {cancelled_count} cancelled training jobs older than {days_to_keep} days")

        if not dry_run and cancelled_count > 0:
            cancelled_query.delete(synchronize_session=False)
            stats["cancelled_deleted"] = cancelled_count

        # 提交刪除
        if not dry_run:
            db.commit()
            stats["total_deleted"] = (
                stats["completed_deleted"] +
                stats["failed_deleted"] +
                stats["cancelled_deleted"]
            )
            logger.info(f"[CLEANUP] Deleted {stats['total_deleted']} old training jobs")
        else:
            total_would_delete = completed_count + failed_count + cancelled_count
            logger.info(f"[CLEANUP] DRY RUN: Would delete {total_would_delete} training jobs")

        stats["success"] = True
        stats["message"] = f"Successfully cleaned up {stats['total_deleted']} old training jobs"

    except Exception as e:
        db.rollback()
        error_msg = f"Failed to cleanup training jobs: {str(e)}"
        logger.error(f"[CLEANUP] {error_msg}")
        stats["success"] = False
        stats["errors"].append(error_msg)

    finally:
        db.close()

    return stats


@celery_app.task(bind=True, name="app.tasks.cleanup_all_old_tasks")
def cleanup_all_old_tasks(
    self: Task,
    days_to_keep: int = 90,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    清理所有類型的舊任務記錄（一次性執行所有清理）

    Args:
        days_to_keep: 保留最近 N 天的記錄（默認 90 天）
        dry_run: 是否為測試模式（不實際刪除）

    Returns:
        所有清理結果的匯總統計
    """
    logger.info(f"[CLEANUP] Starting comprehensive cleanup (days_to_keep={days_to_keep}, dry_run={dry_run})")

    results = {
        "task": "cleanup_all_old_tasks",
        "days_to_keep": days_to_keep,
        "dry_run": dry_run,
        "backtests": {},
        "rdagent_tasks": {},
        "training_jobs": {},
        "total_deleted": 0,
        "success": True,
        "errors": []
    }

    try:
        # 1. 清理回測
        backtest_result = cleanup_old_backtests(days_to_keep=days_to_keep, dry_run=dry_run)
        results["backtests"] = backtest_result
        results["total_deleted"] += backtest_result.get("total_deleted", 0)

        if not backtest_result.get("success"):
            results["success"] = False
            results["errors"].extend(backtest_result.get("errors", []))

        # 2. 清理 RD-Agent 任務
        rdagent_result = cleanup_old_rdagent_tasks(days_to_keep=days_to_keep, dry_run=dry_run)
        results["rdagent_tasks"] = rdagent_result
        results["total_deleted"] += rdagent_result.get("total_deleted", 0)

        if not rdagent_result.get("success"):
            results["success"] = False
            results["errors"].extend(rdagent_result.get("errors", []))

        # 3. 清理訓練任務
        training_result = cleanup_old_training_jobs(days_to_keep=days_to_keep, dry_run=dry_run)
        results["training_jobs"] = training_result
        results["total_deleted"] += training_result.get("total_deleted", 0)

        if not training_result.get("success"):
            results["success"] = False
            results["errors"].extend(training_result.get("errors", []))

        logger.info(f"[CLEANUP] Comprehensive cleanup completed, total deleted: {results['total_deleted']}")
        results["message"] = f"Successfully cleaned up {results['total_deleted']} old records across all task types"

    except Exception as e:
        error_msg = f"Failed to execute comprehensive cleanup: {str(e)}"
        logger.error(f"[CLEANUP] {error_msg}")
        results["success"] = False
        results["errors"].append(error_msg)

    return results
