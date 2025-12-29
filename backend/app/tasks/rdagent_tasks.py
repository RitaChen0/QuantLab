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

        # ========== 步驟 6: 觸發自動評估 ==========
        logger.info("Step 6: Triggering automatic factor evaluation...")

        evaluation_tasks = []
        for factor_info in saved_factors:
            factor_id = factor_info["id"]
            factor_name = factor_info["name"]

            try:
                # 異步觸發評估任務
                from app.tasks.factor_evaluation_tasks import evaluate_factor_async

                task_result = evaluate_factor_async.delay(
                    factor_id=factor_id,
                    stock_pool="all",
                    start_date=None,  # 使用預設 2 年
                    end_date=None
                )

                evaluation_tasks.append({
                    "factor_id": factor_id,
                    "factor_name": factor_name,
                    "task_id": task_result.id
                })

                logger.info(f"✅ Triggered evaluation for factor {factor_id} ({factor_name}), task_id: {task_result.id}")

            except Exception as e:
                logger.error(f"❌ Failed to trigger evaluation for factor {factor_id} ({factor_name}): {str(e)}")

        logger.info(f"Triggered {len(evaluation_tasks)} evaluation tasks for {len(saved_factors)} factors")

        return {
            "status": "success",
            "task_id": task_id,
            "factors_generated": len(factors),
            "llm_calls": llm_calls,
            "llm_cost": llm_cost,
            "log_directory": log_dir,
            "evaluation_tasks": evaluation_tasks  # 新增：返回觸發的評估任務資訊
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

    使用 LLM 分析策略代碼和回測結果，提供優化建議

    Args:
        task_id: RD-Agent 任務 ID

    Returns:
        dict: 任務執行結果
    """
    db: Session = SessionLocal()

    try:
        from app.services.strategy_optimizer import StrategyOptimizer

        service = RDAgentService(db)
        task = db.query(RDAgentTask).filter(RDAgentTask.id == task_id).first()

        if not task:
            logger.error(f"Task {task_id} not found")
            return {"status": "error", "message": "Task not found"}

        # 更新為執行中
        service.update_task_status(task_id, TaskStatus.RUNNING)

        logger.info(f"Starting strategy optimization task {task_id}")
        logger.info(f"Task parameters: {task.input_params}")

        # 提取任務參數
        strategy_id = task.input_params.get("strategy_id")
        optimization_goal = task.input_params.get("optimization_goal", "提升整體績效表現")
        llm_model = task.input_params.get("llm_model", "gpt-4-turbo")
        max_iterations = task.input_params.get("max_iterations", 1)

        if not strategy_id:
            raise ValueError("strategy_id is required in input_params")

        # ========== 步驟 1: 初始化優化器 ==========
        logger.info("Step 1: Initializing strategy optimizer...")
        optimizer = StrategyOptimizer(db)

        # ========== 步驟 2: 分析策略並生成優化建議 ==========
        logger.info(f"Step 2: Analyzing strategy {strategy_id}...")
        analysis_result = optimizer.analyze_strategy(
            strategy_id=strategy_id,
            optimization_goal=optimization_goal,
            llm_model=llm_model
        )

        logger.info(f"✅ Strategy analysis completed")
        logger.info(f"   Current Sharpe Ratio: {analysis_result['current_performance']['sharpe_ratio']}")
        logger.info(f"   Issues diagnosed: {len(analysis_result['issues_diagnosed'])}")
        logger.info(f"   Suggestions generated: {len(analysis_result['optimization_suggestions'])}")

        # ========== 步驟 3: 提取關鍵指標 ==========
        current_perf = analysis_result["current_performance"]
        suggestions = analysis_result["optimization_suggestions"]

        # 估算改進幅度（基於建議的優先級）
        high_priority_count = sum(1 for s in suggestions if s.get("priority") == "high")
        estimated_improvement = min(high_priority_count * 15, 50)  # 每個高優先級建議預計改善 15%，最多 50%

        current_sharpe = current_perf.get("sharpe_ratio") or 0.0
        estimated_sharpe = current_sharpe * (1 + estimated_improvement / 100)

        # ========== 步驟 4: 構建結果 ==========
        optimization_result = {
            "strategy_info": analysis_result["strategy_info"],
            "current_performance": current_perf,
            "issues_diagnosed": analysis_result["issues_diagnosed"],
            "optimization_suggestions": suggestions,
            "optimized_code": analysis_result.get("optimized_code"),
            "estimated_improvements": {
                "sharpe_ratio_before": current_sharpe,
                "sharpe_ratio_estimated": round(estimated_sharpe, 2),
                "improvement_pct": estimated_improvement,
                "high_priority_suggestions": high_priority_count,
                "total_suggestions": len(suggestions)
            },
            "message": f"策略優化分析完成，生成 {len(suggestions)} 條優化建議"
        }

        # ========== 步驟 5: 更新任務狀態 ==========
        llm_metadata = analysis_result.get("llm_metadata", {})
        service.update_task_status(
            task_id,
            TaskStatus.COMPLETED,
            result=optimization_result,
            llm_calls=llm_metadata.get("calls", 1),
            llm_cost=llm_metadata.get("cost", 0.0)
        )

        logger.info(f"Strategy optimization task {task_id} completed")
        logger.info(f"LLM calls: {llm_metadata.get('calls')}, Cost: ${llm_metadata.get('cost')}")

        return {
            "status": "success",
            "task_id": task_id,
            "suggestions_count": len(suggestions),
            "llm_calls": llm_metadata.get("calls", 0),
            "llm_cost": llm_metadata.get("cost", 0.0)
        }

    except Exception as e:
        logger.error(f"Strategy optimization task {task_id} failed: {str(e)}")
        import traceback
        logger.error(f"Full traceback:\n{traceback.format_exc()}")

        service.update_task_status(
            task_id,
            TaskStatus.FAILED,
            error_message=str(e)
        )

        return {"status": "error", "message": str(e)}

    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.run_model_generation_task")
def run_model_generation_task(self: Task, task_id: int):
    """執行模型生成任務

    ⚠️ 注意：此任務需要 RD-Agent 環境和 LLM API 配置

    使用 RD-Agent 的 model.py 模組自動生成量化模型架構

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

        logger.info(f"Starting model generation task {task_id}")
        logger.info(f"Task parameters: {task.input_params}")

        # 提取任務參數
        research_goal = task.input_params.get("research_goal", "Generate quantitative models")
        max_iterations = task.input_params.get("max_iterations", 5)
        llm_model = task.input_params.get("llm_model", "gpt-4-turbo")

        # ========== 步驟 1: 執行 RD-Agent 模型生成 ==========
        logger.info(f"Step 1: Executing RD-Agent model generation with {max_iterations} iterations...")
        log_dir = service.execute_model_generation(
            task_id=task_id,
            research_goal=research_goal,
            max_iterations=max_iterations,
            llm_model=llm_model
        )
        logger.info(f"RD-Agent model generation completed. Log directory: {log_dir}")

        # ========== 步驟 2: 解析 RD-Agent 結果 ==========
        logger.info("Step 2: Parsing RD-Agent model generation results...")
        models = service.parse_model_generation_results(log_dir)
        logger.info(f"Parsed {len(models)} models from results")

        # ========== 步驟 3: 保存生成的模型 ==========
        logger.info("Step 3: Saving generated models to database...")
        logger.info(f"Total models to save: {len(models)}")

        saved_models = []
        failed_models = []

        for i, model_data in enumerate(models, 1):
            model_name = model_data.get("name", "Unknown")
            logger.info(f"[{i}/{len(models)}] Saving model: {model_name}")

            # 重試機制：最多重試 3 次
            max_retries = 3
            retry_delay = 1  # 秒
            saved = False

            for attempt in range(1, max_retries + 1):
                try:
                    model = service.save_generated_model(
                        task_id=task_id,
                        user_id=task.user_id,
                        name=model_data["name"],
                        model_type=model_data["model_type"],
                        description=model_data.get("description"),
                        formulation=model_data.get("formulation"),
                        architecture=model_data.get("architecture"),
                        variables=model_data.get("variables"),
                        hyperparameters=model_data.get("hyperparameters"),
                        code=model_data.get("code"),  # 新增：保存代碼
                        qlib_config=model_data.get("qlib_config"),  # 新增：保存 Qlib 配置
                        iteration=model_data.get("iteration"),
                        metadata=model_data.get("metadata")
                    )

                    saved_models.append({
                        "id": model.id,
                        "name": model.name,
                        "model_type": model.model_type,
                        "architecture": model.architecture
                    })

                    logger.info(f"✅ Saved model {model.id}: {model.name}")
                    saved = True
                    break  # 儲存成功，跳出重試循環

                except Exception as e:
                    logger.error(f"❌ Attempt {attempt}/{max_retries} failed for model '{model_name}': {str(e)}")

                    if attempt < max_retries:
                        import time
                        logger.warning(f"   Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        # 最後一次重試也失敗了
                        logger.error(f"   All {max_retries} attempts failed. Model will be skipped.")
                        failed_models.append({
                            "name": model_name,
                            "error": str(e),
                            "model_type": model_data.get("model_type", "")
                        })

            if not saved:
                logger.warning(f"⚠️  Model '{model_name}' was not saved after {max_retries} attempts")

        # ========== 步驟 3.5: 事務一致性檢查 ==========
        logger.info("Step 3.5: Verifying transaction consistency...")
        logger.info(f"Parsed models: {len(models)}")
        logger.info(f"Successfully saved: {len(saved_models)}")
        logger.info(f"Failed to save: {len(failed_models)}")

        if len(failed_models) > 0:
            logger.warning("⚠️  Some models failed to save:")
            for failed in failed_models:
                logger.warning(f"  - {failed['name']}: {failed['error']}")

        if len(saved_models) != len(models):
            logger.warning(f"⚠️  Transaction consistency issue detected!")
            logger.warning(f"   Expected: {len(models)} models")
            logger.warning(f"   Actually saved: {len(saved_models)} models")
            logger.warning(f"   Missing: {len(models) - len(saved_models)} models")
        else:
            logger.info("✅ Transaction consistency verified: All models saved successfully")

        # ========== 步驟 4: 計算 LLM 成本 ==========
        logger.info("Step 4: Calculating LLM costs...")
        llm_calls, llm_cost = service.calculate_llm_costs(log_dir)
        logger.info(f"LLM API calls: {llm_calls}, Estimated cost: ${llm_cost}")

        # ========== 步驟 5: 更新任務為完成 ==========
        # 構建結果訊息
        result_message = "Model generation completed successfully"
        if len(failed_models) > 0:
            result_message = f"Model generation completed with warnings: {len(failed_models)} models failed to save"

        service.update_task_status(
            task_id,
            TaskStatus.COMPLETED,
            result={
                "generated_models_count": len(models),
                "saved_models_count": len(saved_models),
                "failed_models_count": len(failed_models),
                "log_directory": log_dir,
                "models": saved_models,  # 只包含成功儲存的模型（含 ID）
                "failed_models": failed_models if failed_models else None,
                "consistency_check": {
                    "parsed": len(models),
                    "saved": len(saved_models),
                    "failed": len(failed_models),
                    "passed": len(saved_models) == len(models)
                },
                "message": result_message
            },
            llm_calls=llm_calls,
            llm_cost=llm_cost
        )

        logger.info(f"Model generation task {task_id} completed")
        logger.info(f"Parsed: {len(models)}, Saved: {len(saved_models)}, Failed: {len(failed_models)}")
        logger.info(f"LLM calls: {llm_calls}, Cost: ${llm_cost}")

        return {
            "status": "success",
            "task_id": task_id,
            "models_generated": len(models),
            "llm_calls": llm_calls,
            "llm_cost": llm_cost,
            "log_directory": log_dir
        }

    except Exception as e:
        logger.error(f"Model generation task {task_id} failed: {str(e)}")

        service.update_task_status(
            task_id,
            TaskStatus.FAILED,
            error_message=str(e)
        )

        return {"status": "error", "message": str(e)}

    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.cleanup_stuck_rdagent_tasks")
def cleanup_stuck_rdagent_tasks(self: Task, timeout_hours: int = 24) -> dict:
    """清理執行超時的 RD-Agent 任務

    定期檢查並清理處於 RUNNING 狀態超過指定時間的任務，
    防止任務永久卡住佔用資源。

    Args:
        timeout_hours: 超時時間（小時），預設 24 小時

    Returns:
        dict: 清理統計資訊
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import and_

    db: Session = SessionLocal()

    try:
        logger.info(f"🧹 開始清理卡住的 RD-Agent 任務（超時: {timeout_hours} 小時）")

        # 計算超時時間點
        timeout_threshold = datetime.now(timezone.utc) - timedelta(hours=timeout_hours)

        # 查詢卡住的任務
        stuck_tasks = db.query(RDAgentTask).filter(
            and_(
                RDAgentTask.status == TaskStatus.RUNNING,
                RDAgentTask.started_at < timeout_threshold
            )
        ).all()

        if not stuck_tasks:
            logger.info("✅ 沒有卡住的任務")
            return {
                "status": "success",
                "cleaned_count": 0,
                "tasks": []
            }

        logger.warning(f"⚠️  發現 {len(stuck_tasks)} 個卡住的任務")

        cleaned_tasks = []
        for task in stuck_tasks:
            running_hours = (datetime.now(timezone.utc) - task.started_at).total_seconds() / 3600

            logger.info(f"📋 清理任務 {task.id}:")
            logger.info(f"   - 類型: {task.task_type}")
            logger.info(f"   - 用戶: {task.user_id}")
            logger.info(f"   - 運行時間: {running_hours:.1f} 小時")

            # 更新任務狀態
            task.status = TaskStatus.FAILED
            task.error_message = f"Task timeout after {running_hours:.1f} hours (auto-cleanup on {datetime.now(timezone.utc).date()})"
            task.completed_at = datetime.now(timezone.utc)

            cleaned_tasks.append({
                "id": task.id,
                "task_type": task.task_type.value,
                "user_id": task.user_id,
                "running_hours": round(running_hours, 1)
            })

        db.commit()

        logger.info(f"✅ 成功清理 {len(cleaned_tasks)} 個卡住的任務")

        return {
            "status": "success",
            "cleaned_count": len(cleaned_tasks),
            "tasks": cleaned_tasks
        }

    except Exception as e:
        logger.error(f"❌ 清理卡住任務時發生錯誤: {str(e)}")
        db.rollback()

        return {
            "status": "error",
            "message": str(e),
            "cleaned_count": 0
        }

    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.monitor_rdagent_tasks")
def monitor_rdagent_tasks(self: Task) -> dict:
    """監控 RD-Agent 任務狀態並發送告警

    檢查項目：
    1. 長時間運行的任務（超過軟超時 80%）
    2. 最近失敗的任務
    3. 異常高頻率失敗
    4. 任務執行時間異常

    Returns:
        dict: 監控統計資訊
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import and_, func
    from app.models.rdagent import TaskType  # 添加導入

    db: Session = SessionLocal()

    try:
        logger.info("🔍 開始監控 RD-Agent 任務狀態...")

        alerts = []
        stats = {
            "running_tasks": 0,
            "long_running_tasks": 0,
            "recent_failures": 0,
            "high_failure_rate": False,
            "alerts_sent": 0,
            "errors": []
        }

        # ==================== 檢查 1: 長時間運行的任務 ====================
        # 定義告警閾值（達到軟超時的 80%）
        thresholds = {
            TaskType.FACTOR_MINING: timedelta(minutes=44),  # 55 分鐘 * 80% = 44 分鐘
            TaskType.MODEL_GENERATION: timedelta(minutes=22),  # 28 分鐘 * 80% = 22 分鐘
            TaskType.STRATEGY_OPTIMIZATION: timedelta(minutes=22)
        }

        running_tasks = db.query(RDAgentTask).filter(
            RDAgentTask.status == TaskStatus.RUNNING
        ).all()

        stats["running_tasks"] = len(running_tasks)

        for task in running_tasks:
            if task.started_at:
                running_time = datetime.now(timezone.utc) - task.started_at
                threshold = thresholds.get(task.task_type, timedelta(minutes=30))

                if running_time > threshold:
                    stats["long_running_tasks"] += 1
                    running_minutes = running_time.total_seconds() / 60

                    alerts.append({
                        "severity": "WARNING",
                        "type": "LONG_RUNNING_TASK",
                        "task_id": task.id,
                        "task_type": task.task_type.value,
                        "user_id": task.user_id,
                        "running_minutes": round(running_minutes, 1),
                        "threshold_minutes": threshold.total_seconds() / 60,
                        "message": (
                            f"⚠️ RD-Agent 任務 #{task.id} ({task.task_type.value}) "
                            f"已運行 {running_minutes:.1f} 分鐘，超過告警閾值"
                        )
                    })

                    logger.warning(
                        f"⚠️ Task {task.id} ({task.task_type.value}) "
                        f"running for {running_minutes:.1f} minutes"
                    )

        # ==================== 檢查 2: 最近失敗的任務 ====================
        recent_failures = db.query(RDAgentTask).filter(
            and_(
                RDAgentTask.status == TaskStatus.FAILED,
                RDAgentTask.completed_at >= datetime.now(timezone.utc) - timedelta(hours=1)
            )
        ).all()

        stats["recent_failures"] = len(recent_failures)

        for task in recent_failures:
            alerts.append({
                "severity": "ERROR",
                "type": "TASK_FAILED",
                "task_id": task.id,
                "task_type": task.task_type.value,
                "user_id": task.user_id,
                "error_message": task.error_message or "Unknown error",
                "message": (
                    f"❌ RD-Agent 任務 #{task.id} ({task.task_type.value}) 失敗\n"
                    f"錯誤: {task.error_message or 'Unknown error'}"
                )
            })

            logger.error(
                f"❌ Task {task.id} ({task.task_type.value}) failed: "
                f"{task.error_message}"
            )

        # ==================== 檢查 3: 失敗率過高 ====================
        # 檢查最近 24 小時的任務失敗率
        one_day_ago = datetime.now(timezone.utc) - timedelta(hours=24)

        total_tasks_24h = db.query(func.count(RDAgentTask.id)).filter(
            RDAgentTask.created_at >= one_day_ago
        ).scalar()

        failed_tasks_24h = db.query(func.count(RDAgentTask.id)).filter(
            and_(
                RDAgentTask.status == TaskStatus.FAILED,
                RDAgentTask.created_at >= one_day_ago
            )
        ).scalar()

        if total_tasks_24h and total_tasks_24h > 0:
            failure_rate = (failed_tasks_24h / total_tasks_24h) * 100

            # 失敗率超過 30% 視為異常
            if failure_rate > 30:
                stats["high_failure_rate"] = True

                alerts.append({
                    "severity": "CRITICAL",
                    "type": "HIGH_FAILURE_RATE",
                    "failure_rate": round(failure_rate, 1),
                    "total_tasks": total_tasks_24h,
                    "failed_tasks": failed_tasks_24h,
                    "message": (
                        f"🚨 RD-Agent 任務失敗率過高！\n"
                        f"最近 24 小時: {failed_tasks_24h}/{total_tasks_24h} 失敗 "
                        f"({failure_rate:.1f}%)"
                    )
                })

                logger.critical(
                    f"🚨 High failure rate detected: {failure_rate:.1f}% "
                    f"({failed_tasks_24h}/{total_tasks_24h})"
                )

        # ==================== 發送告警 ====================
        if alerts:
            logger.info(f"📊 檢測到 {len(alerts)} 個告警，準備發送通知...")

            # 按用戶分組告警
            alerts_by_user = {}
            for alert in alerts:
                user_id = alert.get("user_id")
                if user_id:
                    if user_id not in alerts_by_user:
                        alerts_by_user[user_id] = []
                    alerts_by_user[user_id].append(alert)

            # 發送告警通知
            for user_id, user_alerts in alerts_by_user.items():
                try:
                    # 構建告警消息
                    severity_emoji = {
                        "WARNING": "⚠️",
                        "ERROR": "❌",
                        "CRITICAL": "🚨"
                    }

                    message_lines = ["<b>🤖 RD-Agent 任務告警</b>\n"]

                    for alert in user_alerts:
                        emoji = severity_emoji.get(alert["severity"], "ℹ️")
                        message_lines.append(
                            f"{emoji} <b>{alert['type']}</b>\n"
                            f"{alert['message']}\n"
                        )

                    message = "\n".join(message_lines)

                    # 調用 Telegram 通知任務
                    from app.tasks.telegram_notifications import send_telegram_notification

                    send_telegram_notification.delay(
                        user_id=user_id,
                        notification_type="system_alert",
                        title="🤖 RD-Agent 任務告警",
                        message=message,
                        related_object_type="rdagent_monitoring",
                        related_object_id=None
                    )

                    stats["alerts_sent"] += 1

                except Exception as e:
                    error_msg = f"Failed to send alert to user {user_id}: {str(e)}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)

            # 系統級告警（高失敗率）發送給管理員
            critical_alerts = [a for a in alerts if a["severity"] == "CRITICAL"]
            if critical_alerts:
                # TODO: 添加管理員通知邏輯
                logger.critical(
                    f"🚨 {len(critical_alerts)} critical alerts detected, "
                    f"admin notification required"
                )

        else:
            logger.info("✅ 所有 RD-Agent 任務狀態正常，無告警")

        # 記錄監控統計
        logger.info(f"📊 監控統計:")
        logger.info(f"   - 運行中任務: {stats['running_tasks']}")
        logger.info(f"   - 長時間運行: {stats['long_running_tasks']}")
        logger.info(f"   - 最近失敗: {stats['recent_failures']}")
        logger.info(f"   - 高失敗率: {stats['high_failure_rate']}")
        logger.info(f"   - 告警已發送: {stats['alerts_sent']}")

        return {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stats": stats,
            "alerts": alerts
        }

    except Exception as e:
        logger.error(f"❌ RD-Agent 監控任務失敗: {str(e)}")

        return {
            "status": "error",
            "message": str(e),
            "stats": stats
        }

    finally:
        db.close()
