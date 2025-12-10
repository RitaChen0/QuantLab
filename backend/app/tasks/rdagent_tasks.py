"""RD-Agent Celery 異步任務"""

from celery import Task
from sqlalchemy.orm import Session
from loguru import logger

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.rdagent_service import RDAgentService
from app.models.rdagent import RDAgentTask, TaskStatus


@celery_app.task(bind=True, name="app.tasks.run_factor_mining_task")
def run_factor_mining_task(self: Task, task_id: int):
    """執行因子挖掘任務

    ⚠️ 注意：此任務需要 RD-Agent 環境和 LLM API 配置

    當前版本為模擬執行，實際使用時需要整合 RD-Agent 核心邏輯。

    Args:
        task_id: RD-Agent 任務 ID

    Returns:
        dict: 任務執行結果
    """
    db: Session = SessionLocal()

    try:
        service = RDAgentService(db)
        task = db.query(RDAgentTask).filter(RDAgentTask.id == task_id).first()

        if not task:
            logger.error(f"Task {task_id} not found")
            return {"status": "error", "message": "Task not found"}

        # 更新為執行中
        service.update_task_status(task_id, TaskStatus.RUNNING)

        logger.info(f"Starting factor mining task {task_id}")
        logger.info(f"Task parameters: {task.input_params}")

        # 提取任務參數
        research_goal = task.input_params.get("research_goal", "Generate profitable trading factors")
        max_iterations = task.input_params.get("max_iterations", 3)
        llm_model = task.input_params.get("llm_model", "gpt-4-turbo")

        # ========== 步驟 1: 執行 RD-Agent 因子挖掘 ==========
        logger.info(f"Step 1: Executing RD-Agent with {max_iterations} iterations...")
        log_dir = service.execute_factor_mining(
            task_id=task_id,
            research_goal=research_goal,
            max_iterations=max_iterations,
            llm_model=llm_model
        )
        logger.info(f"RD-Agent execution completed. Log directory: {log_dir}")

        # ========== 步驟 2: 解析 RD-Agent 結果 ==========
        logger.info("Step 2: Parsing RD-Agent results...")
        factors = service.parse_rdagent_results(log_dir)
        logger.info(f"Parsed {len(factors)} factors from results")

        # ========== 步驟 3: 保存生成的因子 ==========
        logger.info("Step 3: Saving generated factors to database...")
        logger.info(f"Total factors to save: {len(factors)}")

        saved_factors = []
        failed_factors = []

        for i, factor_data in enumerate(factors, 1):
            factor_name = factor_data.get("name", "Unknown")
            logger.info(f"[{i}/{len(factors)}] Saving factor: {factor_name}")

            # 重試機制：最多重試 3 次
            max_retries = 3
            retry_delay = 1  # 秒
            saved = False

            for attempt in range(1, max_retries + 1):
                try:
                    factor = service.save_generated_factor(
                        task_id=task_id,
                        user_id=task.user_id,
                        name=factor_data["name"],
                        formula=factor_data["formula"],
                        description=factor_data.get("description"),
                        category=factor_data.get("category"),
                        metadata=factor_data.get("metadata")
                    )

                    saved_factors.append({
                        "id": factor.id,
                        "name": factor.name,
                        "formula": factor.formula
                    })

                    logger.info(f"✅ Saved factor {factor.id}: {factor.name}")
                    saved = True
                    break  # 儲存成功，跳出重試循環

                except Exception as e:
                    logger.error(f"❌ Attempt {attempt}/{max_retries} failed for factor '{factor_name}': {str(e)}")
                    logger.error(f"   Factor data: name={factor_data.get('name')}, formula_length={len(factor_data.get('formula', ''))}")

                    if attempt < max_retries:
                        import time
                        logger.warning(f"   Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        # 最後一次重試也失敗了
                        logger.error(f"   All {max_retries} attempts failed. Factor will be skipped.")
                        failed_factors.append({
                            "name": factor_name,
                            "error": str(e),
                            "formula": factor_data.get("formula", "")[:100]  # 只記錄前 100 字元
                        })

            if not saved:
                logger.warning(f"⚠️  Factor '{factor_name}' was not saved after {max_retries} attempts")

        # ========== 步驟 3.5: 事務一致性檢查 ==========
        logger.info("Step 3.5: Verifying transaction consistency...")
        logger.info(f"Parsed factors: {len(factors)}")
        logger.info(f"Successfully saved: {len(saved_factors)}")
        logger.info(f"Failed to save: {len(failed_factors)}")

        if len(failed_factors) > 0:
            logger.warning("⚠️  Some factors failed to save:")
            for failed in failed_factors:
                logger.warning(f"  - {failed['name']}: {failed['error']}")

        if len(saved_factors) != len(factors):
            logger.warning(f"⚠️  Transaction consistency issue detected!")
            logger.warning(f"   Expected: {len(factors)} factors")
            logger.warning(f"   Actually saved: {len(saved_factors)} factors")
            logger.warning(f"   Missing: {len(factors) - len(saved_factors)} factors")
        else:
            logger.info("✅ Transaction consistency verified: All factors saved successfully")

        # ========== 步驟 4: 計算 LLM 成本 ==========
        logger.info("Step 4: Calculating LLM costs...")
        llm_calls, llm_cost = service.calculate_llm_costs(log_dir)
        logger.info(f"LLM API calls: {llm_calls}, Estimated cost: ${llm_cost}")

        # ========== 步驟 5: 更新任務為完成 ==========
        # 構建結果訊息
        result_message = "Factor mining completed successfully"
        if len(failed_factors) > 0:
            result_message = f"Factor mining completed with warnings: {len(failed_factors)} factors failed to save"

        service.update_task_status(
            task_id,
            TaskStatus.COMPLETED,
            result={
                "generated_factors_count": len(factors),
                "saved_factors_count": len(saved_factors),
                "failed_factors_count": len(failed_factors),
                "log_directory": log_dir,
                "factors": saved_factors,  # 只包含成功儲存的因子（含 ID）
                "failed_factors": failed_factors if failed_factors else None,  # 失敗的因子資訊
                "consistency_check": {
                    "parsed": len(factors),
                    "saved": len(saved_factors),
                    "failed": len(failed_factors),
                    "passed": len(saved_factors) == len(factors)
                },
                "message": result_message
            },
            llm_calls=llm_calls,
            llm_cost=llm_cost
        )

        logger.info(f"Factor mining task {task_id} completed")
        logger.info(f"Parsed: {len(factors)}, Saved: {len(saved_factors)}, Failed: {len(failed_factors)}")
        logger.info(f"LLM calls: {llm_calls}, Cost: ${llm_cost}")

        return {
            "status": "success",
            "task_id": task_id,
            "factors_generated": len(factors),
            "llm_calls": llm_calls,
            "llm_cost": llm_cost,
            "log_directory": log_dir
        }

    except Exception as e:
        logger.error(f"Factor mining task {task_id} failed: {str(e)}")

        service.update_task_status(
            task_id,
            TaskStatus.FAILED,
            error_message=str(e)
        )

        return {"status": "error", "message": str(e)}

    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.run_strategy_optimization_task")
def run_strategy_optimization_task(self: Task, task_id: int):
    """執行策略優化任務

    ⚠️ 注意：此任務需要 RD-Agent 環境和 LLM API 配置

    當前版本為模擬執行，實際使用時需要整合 RD-Agent 核心邏輯。

    Args:
        task_id: RD-Agent 任務 ID

    Returns:
        dict: 任務執行結果
    """
    db: Session = SessionLocal()

    try:
        service = RDAgentService(db)
        task = db.query(RDAgentTask).filter(RDAgentTask.id == task_id).first()

        if not task:
            logger.error(f"Task {task_id} not found")
            return {"status": "error", "message": "Task not found"}

        # 更新為執行中
        service.update_task_status(task_id, TaskStatus.RUNNING)

        logger.info(f"Starting strategy optimization task {task_id}")

        # ========== RD-Agent 核心邏輯 ==========
        # TODO: 實作 RD-Agent 策略優化邏輯
        # 參考：https://github.com/microsoft/RD-Agent/blob/main/rdagent/scenarios/qlib/model/

        # ========== 暫時模擬結果 ==========
        import time
        time.sleep(8)  # 模擬處理時間

        # 更新為完成
        service.update_task_status(
            task_id,
            TaskStatus.COMPLETED,
            result={
                "optimization_improvements": {
                    "sharpe_ratio_before": 1.2,
                    "sharpe_ratio_after": 1.8,
                    "improvement_pct": 50.0
                },
                "message": "Strategy optimization completed (DEMO MODE)"
            },
            llm_calls=25,
            llm_cost=0.60
        )

        logger.info(f"Strategy optimization task {task_id} completed")

        return {
            "status": "success",
            "task_id": task_id
        }

    except Exception as e:
        logger.error(f"Strategy optimization task {task_id} failed: {str(e)}")

        service.update_task_status(
            task_id,
            TaskStatus.FAILED,
            error_message=str(e)
        )

        return {"status": "error", "message": str(e)}

    finally:
        db.close()
