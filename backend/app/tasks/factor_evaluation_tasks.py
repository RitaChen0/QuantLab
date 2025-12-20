"""
因子評估 Celery 異步任務

提供長時間運行的因子評估任務，避免阻塞 API 請求
"""

from celery import Task
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from loguru import logger

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.factor_evaluation_service import FactorEvaluationService
from app.models.rdagent import GeneratedFactor


@celery_app.task(bind=True, name="app.tasks.evaluate_factor_async")
def evaluate_factor_async(
    self: Task,
    factor_id: int,
    stock_pool: str = "all",
    start_date: str = None,
    end_date: str = None
) -> dict:
    """
    異步評估因子績效

    Args:
        factor_id: 因子 ID
        stock_pool: 股票池
        start_date: 開始日期
        end_date: 結束日期

    Returns:
        評估結果字典
    """
    logger.info(f"[Task {self.request.id}] Starting async factor evaluation for factor_id={factor_id}")

    db: Session = SessionLocal()

    try:
        # 檢查因子是否存在
        factor = db.query(GeneratedFactor).filter(
            GeneratedFactor.id == factor_id
        ).first()

        if not factor:
            logger.error(f"[Task {self.request.id}] Factor {factor_id} not found")
            return {
                "status": "error",
                "error": f"Factor {factor_id} not found",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # 執行評估
        service = FactorEvaluationService(db)
        results = service.evaluate_factor(
            factor_id=factor_id,
            stock_pool=stock_pool,
            start_date=start_date,
            end_date=end_date,
            save_to_db=True
        )

        logger.info(
            f"[Task {self.request.id}] Factor evaluation completed - "
            f"IC: {results.get('ic', 'N/A'):.4f}, "
            f"Sharpe: {results.get('sharpe_ratio', 'N/A'):.4f}"
        )

        return {
            "status": "success",
            "factor_id": factor_id,
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"[Task {self.request.id}] Factor evaluation failed: {str(e)}")
        logger.exception(e)

        # 使用指數退避：1m, 2m, 4m
        retry_count = self.request.retries
        countdown = 60 * (2 ** retry_count)
        raise self.retry(exc=e, countdown=countdown, max_retries=3)

    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.batch_evaluate_factors")
def batch_evaluate_factors(
    self: Task,
    factor_ids: list[int],
    stock_pool: str = "all",
    start_date: str = None,
    end_date: str = None
) -> dict:
    """
    批量評估多個因子

    Args:
        factor_ids: 因子 ID 列表
        stock_pool: 股票池
        start_date: 開始日期
        end_date: 結束日期

    Returns:
        批量評估結果
    """
    logger.info(f"[Task {self.request.id}] Starting batch evaluation for {len(factor_ids)} factors")

    db: Session = SessionLocal()
    results = []
    failed = []

    try:
        service = FactorEvaluationService(db)

        for i, factor_id in enumerate(factor_ids, 1):
            logger.info(f"[Task {self.request.id}] Evaluating factor {i}/{len(factor_ids)}: {factor_id}")

            try:
                # 檢查因子是否存在
                factor = db.query(GeneratedFactor).filter(
                    GeneratedFactor.id == factor_id
                ).first()

                if not factor:
                    logger.warning(f"[Task {self.request.id}] Factor {factor_id} not found, skipping")
                    failed.append({
                        "factor_id": factor_id,
                        "error": "Factor not found"
                    })
                    continue

                # 執行評估
                eval_result = service.evaluate_factor(
                    factor_id=factor_id,
                    stock_pool=stock_pool,
                    start_date=start_date,
                    end_date=end_date,
                    save_to_db=True
                )

                results.append({
                    "factor_id": factor_id,
                    "factor_name": factor.name,
                    "ic": eval_result.get("ic"),
                    "icir": eval_result.get("icir"),
                    "sharpe_ratio": eval_result.get("sharpe_ratio"),
                    "annual_return": eval_result.get("annual_return"),
                })

                logger.info(
                    f"[Task {self.request.id}] Factor {factor_id} evaluated - "
                    f"IC: {eval_result.get('ic', 'N/A'):.4f}"
                )

            except Exception as e:
                logger.error(f"[Task {self.request.id}] Failed to evaluate factor {factor_id}: {str(e)}")
                failed.append({
                    "factor_id": factor_id,
                    "error": str(e)
                })
                continue

        logger.info(
            f"[Task {self.request.id}] Batch evaluation completed - "
            f"Success: {len(results)}, Failed: {len(failed)}"
        )

        return {
            "status": "success",
            "total": len(factor_ids),
            "successful": len(results),
            "failed": len(failed),
            "results": results,
            "failures": failed,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"[Task {self.request.id}] Batch evaluation failed: {str(e)}")
        logger.exception(e)

        return {
            "status": "error",
            "error": str(e),
            "partial_results": results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.update_factor_metrics")
def update_factor_metrics(
    self: Task,
    factor_id: int
) -> dict:
    """
    更新因子的最新評估指標到 generated_factors 表

    從最新的 factor_evaluation 記錄中讀取指標並更新

    Args:
        factor_id: 因子 ID

    Returns:
        更新狀態
    """
    logger.info(f"[Task {self.request.id}] Updating metrics for factor_id={factor_id}")

    db: Session = SessionLocal()

    try:
        from app.models.rdagent import FactorEvaluation

        # 獲取因子
        factor = db.query(GeneratedFactor).filter(
            GeneratedFactor.id == factor_id
        ).first()

        if not factor:
            logger.error(f"[Task {self.request.id}] Factor {factor_id} not found")
            return {
                "status": "error",
                "error": f"Factor {factor_id} not found"
            }

        # 獲取最新的評估記錄
        latest_eval = db.query(FactorEvaluation).filter(
            FactorEvaluation.factor_id == factor_id
        ).order_by(FactorEvaluation.created_at.desc()).first()

        if not latest_eval:
            logger.warning(f"[Task {self.request.id}] No evaluation found for factor {factor_id}")
            return {
                "status": "success",
                "message": "No evaluation found",
                "factor_id": factor_id
            }

        # 更新因子指標
        factor.ic = latest_eval.ic
        factor.icir = latest_eval.icir
        factor.sharpe_ratio = latest_eval.sharpe_ratio
        factor.annual_return = latest_eval.annual_return

        db.commit()

        logger.info(
            f"[Task {self.request.id}] Updated factor {factor_id} metrics - "
            f"IC: {factor.ic:.4f}, Sharpe: {factor.sharpe_ratio:.4f}"
        )

        return {
            "status": "success",
            "factor_id": factor_id,
            "metrics": {
                "ic": factor.ic,
                "icir": factor.icir,
                "sharpe_ratio": factor.sharpe_ratio,
                "annual_return": factor.annual_return,
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"[Task {self.request.id}] Failed to update factor metrics: {str(e)}")
        logger.exception(e)
        db.rollback()

        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    finally:
        db.close()
