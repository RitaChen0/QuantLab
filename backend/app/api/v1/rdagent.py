"""RD-Agent API 端點"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.services.rdagent_service import RDAgentService
from app.schemas.rdagent import (
    FactorMiningRequest,
    ModelGenerationRequest,
    StrategyOptimizationRequest,
    RDAgentTaskResponse,
    GeneratedFactorResponse,
    GeneratedModelResponse,
    UpdateGeneratedFactorRequest,
    TaskType,
    SelectFactorsRequest,
    ModelTrainingRequest,
    ModelTrainingJobResponse,
    ModelTrainingJobListResponse,
    ModelFactorResponse,
    ModelPredictionRequest,
    ModelPredictionResponse,
    PredictionData,
    ExportStrategyRequest,
    ExportStrategyResponse,
)
from app.tasks.rdagent_tasks import (
    run_factor_mining_task,
    run_model_generation_task,
    run_strategy_optimization_task,
)
from app.tasks.model_training_tasks import (
    train_model_async,
    cancel_training_job,
)
from app.core.rate_limit import limiter, RateLimits
from app.utils.logging import api_log
from loguru import logger

router = APIRouter(prefix="/rdagent", tags=["RD-Agent"])


@router.post("/factor-mining", response_model=RDAgentTaskResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(RateLimits.RDAGENT_FACTOR_MINING)
async def create_factor_mining_task(
    request: Request,
    req: FactorMiningRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """建立因子挖掘任務（異步執行）

    使用 RD-Agent 自動生成交易因子。任務會在背景執行，可通過任務 ID 查詢進度。

    **會員等級限制**：
    - Level 0-2: 不可使用
    - Level 3: 1 次/小時
    - Level 4: 2 次/小時
    - Level 5: 3 次/小時
    - Level 6: 6 次/小時
    - Level 7-9: 3000 次/小時（管理員/創造者）
    """
    # 檢查會員等級限制
    user_level = getattr(current_user, 'member_level', 0)

    # Level 0-2 不允許使用因子挖掘功能
    if user_level < 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="因子挖掘功能僅限 Level 3 以上會員使用。請升級會員等級以使用此功能。"
        )

    # 根據會員等級設定不同的限制（通過自訂 limiter）
    # Level 3: 3/hour, Level 6: 10/hour
    # 實際限制由 rate_limit.py 中的倍數機制處理

    try:
        service = RDAgentService(db)

        # 創建任務
        task = service.create_factor_mining_task(current_user.id, req)

        # 觸發 Celery 異步任務
        run_factor_mining_task.apply_async(args=[task.id])

        api_log.log_operation(
            "create", "rdagent_factor_mining", task.id, current_user.id, success=True
        )

        return task

    except Exception as e:
        api_log.log_operation(
            "create", "rdagent_factor_mining", None, current_user.id, success=False
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create factor mining task: {str(e)}"
        )


@router.post("/strategy-optimization", response_model=RDAgentTaskResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(RateLimits.RDAGENT_STRATEGY_OPT)
async def create_strategy_optimization_task(
    request: Request,
    req: StrategyOptimizationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """建立策略優化任務（異步執行）

    使用 RD-Agent 自動優化現有策略。任務會在背景執行，可通過任務 ID 查詢進度。

    **限制**：每小時最多 5 次
    """
    try:
        service = RDAgentService(db)

        # 創建任務
        task = service.create_strategy_optimization_task(current_user.id, req)

        # 觸發 Celery 異步任務
        run_strategy_optimization_task.apply_async(args=[task.id])

        api_log.log_operation(
            "create", "rdagent_strategy_opt", task.id, current_user.id, success=True
        )

        return task

    except Exception as e:
        api_log.log_operation(
            "create", "rdagent_strategy_opt", None, current_user.id, success=False
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create strategy optimization task: {str(e)}"
        )


@router.post("/model-generation", response_model=RDAgentTaskResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(RateLimits.RDAGENT_FACTOR_MINING)  # 使用相同的速率限制
async def create_model_generation_task(
    request: Request,
    req: ModelGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """建立模型生成任務（異步執行）

    使用 RD-Agent 自動生成量化模型架構。任務會在背景執行，可通過任務 ID 查詢進度。

    **會員等級限制**：
    - Level 0-2: 不可使用
    - Level 3: 1 次/小時
    - Level 4: 2 次/小時
    - Level 5: 3 次/小時
    - Level 6: 6 次/小時
    - Level 7-9: 3000 次/小時（管理員/創造者）
    """
    # 檢查會員等級限制
    user_level = getattr(current_user, 'member_level', 0)

    # Level 0-2 不允許使用模型生成功能
    if user_level < 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="模型生成功能僅限 Level 3 以上會員使用。請升級會員等級以使用此功能。"
        )

    try:
        service = RDAgentService(db)

        # 創建任務
        task = service.create_model_generation_task(current_user.id, req)

        # 觸發 Celery 異步任務
        run_model_generation_task.apply_async(args=[task.id])

        api_log.log_operation(
            "create", "rdagent_model_generation", task.id, current_user.id, success=True
        )

        return task

    except Exception as e:
        api_log.log_operation(
            "create", "rdagent_model_generation", None, current_user.id, success=False
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create model generation task: {str(e)}"
        )


@router.get("/models", response_model=List[GeneratedModelResponse])
async def get_generated_models(
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """獲取生成的模型列表

    查詢 RD-Agent 自動生成的所有量化模型及其詳細資訊。
    """
    service = RDAgentService(db)
    models = service.get_generated_models(current_user.id, limit)
    return models


@router.get("/models/{model_id}", response_model=GeneratedModelResponse)
async def get_generated_model(
    model_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """獲取單一模型詳情

    查詢指定 ID 的 RD-Agent 生成模型及其詳細資訊。
    """
    service = RDAgentService(db)
    model = service.get_generated_model(model_id, current_user.id)

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found or you don't have permission to access it"
        )

    return model


@router.get("/tasks/{task_id}", response_model=RDAgentTaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """獲取任務詳情

    查詢指定 RD-Agent 任務的執行狀態和結果。
    """
    service = RDAgentService(db)
    task = service.get_task(task_id, current_user.id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return task


@router.get("/tasks", response_model=List[RDAgentTaskResponse])
async def get_tasks(
    task_type: Optional[TaskType] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """獲取任務列表

    查詢當前使用者的所有 RD-Agent 任務，可依類型篩選。
    """
    service = RDAgentService(db)
    tasks = service.get_user_tasks(current_user.id, task_type, limit)
    return tasks


@router.get("/factors", response_model=List[GeneratedFactorResponse])
async def get_generated_factors(
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """獲取生成的因子列表

    查詢 RD-Agent 自動生成的所有交易因子及其評估指標。
    """
    service = RDAgentService(db)
    factors = service.get_generated_factors(current_user.id, limit)

    # 為每個因子添加評估數量
    result = []
    for factor in factors:
        factor_dict = {
            "id": factor.id,
            "name": factor.name,
            "description": factor.description,
            "formula": factor.formula,
            "code": factor.code,
            "category": factor.category,
            "ic": factor.ic,
            "icir": factor.icir,
            "sharpe_ratio": factor.sharpe_ratio,
            "annual_return": factor.annual_return,
            "created_at": factor.created_at,
            "evaluation_count": len(factor.evaluations) if factor.evaluations else 0
        }
        result.append(factor_dict)

    return result


@router.get("/factors/{factor_id}", response_model=GeneratedFactorResponse)
async def get_factor_by_id(
    factor_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """獲取單個因子詳情

    根據因子 ID 獲取因子的完整資訊，包括評估記錄數量。
    """
    from app.repositories.generated_factor import GeneratedFactorRepository

    # 獲取因子並驗證權限
    factor = GeneratedFactorRepository.get_by_id_and_user(db, factor_id, current_user.id)

    if not factor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="因子不存在或無權訪問"
        )

    # 返回因子資訊
    return GeneratedFactorResponse(
        id=factor.id,
        name=factor.name,
        description=factor.description,
        formula=factor.formula,
        code=factor.code,
        category=factor.category,
        ic=factor.ic,
        icir=factor.icir,
        sharpe_ratio=factor.sharpe_ratio,
        annual_return=factor.annual_return,
        created_at=factor.created_at,
        evaluation_count=len(factor.evaluations) if factor.evaluations else 0
    )


@router.patch("/factors/{factor_id}", response_model=GeneratedFactorResponse)
async def update_factor(
    factor_id: int,
    update_data: UpdateGeneratedFactorRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新生成的因子

    更新因子的名稱或描述。只能更新自己生成的因子。
    """
    try:
        service = RDAgentService(db)

        # 更新因子
        factor = service.update_factor(
            factor_id=factor_id,
            user_id=current_user.id,
            name=update_data.name,
            description=update_data.description
        )

        if not factor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factor not found or access denied"
            )

        api_log.log_operation(
            "update", "generated_factor", factor_id, current_user.id, success=True
        )

        return factor

    except HTTPException:
        raise
    except Exception as e:
        api_log.log_operation(
            "update", "generated_factor", factor_id, current_user.id, success=False
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update factor: {str(e)}"
        )


@router.post("/tasks/{task_id}/retry", response_model=RDAgentTaskResponse)
@limiter.limit(RateLimits.RDAGENT_FACTOR_MINING)
async def retry_task(
    request: Request,
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """重試失敗的任務

    重新執行失敗或已取消的 RD-Agent 任務。

    **限制**：與創建任務共用速率限制（每小時 3 次）
    """
    try:
        service = RDAgentService(db)

        # 獲取任務
        task = service.get_task(task_id, current_user.id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # 檢查任務狀態
        from app.models.rdagent import TaskStatus
        if task.status not in [TaskStatus.FAILED, TaskStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot retry task with status: {task.status}"
            )

        # 重置任務狀態為 pending
        service.update_task_status(task_id, TaskStatus.PENDING)

        # 根據任務類型重新觸發 Celery 任務
        from app.schemas.rdagent import TaskType
        if task.task_type == TaskType.FACTOR_MINING:
            run_factor_mining_task.apply_async(args=[task_id])
        elif task.task_type == TaskType.MODEL_GENERATION:
            run_model_generation_task.apply_async(args=[task_id])
        elif task.task_type == TaskType.STRATEGY_OPTIMIZATION:
            run_strategy_optimization_task.apply_async(args=[task_id])

        api_log.log_operation(
            "retry", f"rdagent_{task.task_type.value}", task_id, current_user.id, success=True
        )

        # 重新獲取更新後的任務
        updated_task = service.get_task(task_id, current_user.id)
        return updated_task

    except HTTPException:
        raise
    except Exception as e:
        api_log.log_operation(
            "retry", "rdagent_task", task_id, current_user.id, success=False
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry task: {str(e)}"
        )


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """刪除任務

    刪除指定的 RD-Agent 任務及其相關的生成因子。
    只能刪除自己創建的任務。
    """
    try:
        service = RDAgentService(db)

        # 刪除任務（service 會檢查權限）
        service.delete_task(task_id, current_user.id)

        api_log.log_operation(
            "delete", "rdagent_task", task_id, current_user.id, success=True
        )

        return None  # HTTP 204 No Content

    except ValueError as e:
        # 任務不存在或無權限
        api_log.log_operation(
            "delete", "rdagent_task", task_id, current_user.id, success=False
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        api_log.log_operation(
            "delete", "rdagent_task", task_id, current_user.id, success=False
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete task: {str(e)}"
        )


# ========== 模型訓練相關端點 ==========

@router.post("/models/{model_id}/select-factors", response_model=List[ModelFactorResponse])
async def select_factors_for_model(
    model_id: int,
    req: SelectFactorsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """為模型選擇因子
    
    綁定因子到模型，作為訓練時的特徵輸入。
    這個操作會替換模型現有的因子配置。
    
    Args:
        model_id: 模型 ID
        req: 選擇的因子 ID 列表
    
    Returns:
        模型因子關聯列表
    """
    from app.repositories.generated_model import GeneratedModelRepository
    from app.repositories.model_factor import ModelFactorRepository
    from app.repositories.generated_factor import GeneratedFactorRepository
    
    # 驗證模型存在且屬於當前用戶
    model = GeneratedModelRepository.get_by_id(db, model_id)
    if not model or model.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在或無權訪問"
        )
    
    # 驗證所有因子存在且屬於當前用戶
    factors = GeneratedFactorRepository.get_by_ids(db, req.factor_ids)
    if len(factors) != len(req.factor_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="部分因子不存在"
        )
    
    for factor in factors:
        if factor.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"因子 {factor.id} 不屬於當前用戶"
            )
    
    # 批次創建關聯（會先刪除舊關聯）
    model_factors = ModelFactorRepository.batch_create(
        db, model_id, req.factor_ids
    )
    
    api_log.log_operation(
        "select_factors", "generated_model", model_id, current_user.id, success=True
    )
    
    # 構造響應
    result = []
    for mf in model_factors:
        factor = next((f for f in factors if f.id == mf.factor_id), None)
        result.append(ModelFactorResponse(
            id=mf.id,
            model_id=mf.model_id,
            factor_id=mf.factor_id,
            feature_index=mf.feature_index,
            factor=GeneratedFactorResponse(
                id=factor.id,
                name=factor.name,
                description=factor.description,
                formula=factor.formula,
                code=factor.code,
                category=factor.category,
                ic=factor.ic,
                icir=factor.icir,
                sharpe_ratio=factor.sharpe_ratio,
                annual_return=factor.annual_return,
                created_at=factor.created_at,
                evaluation_count=0
            ) if factor else None,
            created_at=mf.created_at
        ))
    
    return result


@router.post("/models/{model_id}/train", response_model=ModelTrainingJobResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(RateLimits.RDAGENT_FACTOR_MINING)  # 使用相同的速率限制
async def train_model(
    request: Request,
    model_id: int,
    req: ModelTrainingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """訓練模型（異步執行）
    
    使用選定的因子和訓練參數訓練模型。
    訓練會在背景異步執行，可通過返回的 job_id 查詢訓練進度。
    
    Args:
        model_id: 模型 ID
        req: 訓練請求（因子 ID、數據集配置、訓練參數）
    
    Returns:
        訓練任務資訊（包含 job_id）
    """
    from app.repositories.generated_model import GeneratedModelRepository
    from app.repositories.model_training_job import ModelTrainingJobRepository
    from app.repositories.model_factor import ModelFactorRepository
    
    # 驗證模型存在且屬於當前用戶
    model = GeneratedModelRepository.get_by_id(db, model_id)
    if not model or model.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在或無權訪問"
        )
    
    # 驗證會員等級（Level 3 以上才能訓練模型）
    user_level = getattr(current_user, 'member_level', 0)
    if user_level < 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="模型訓練功能僅限 Level 3 以上會員使用。請升級會員等級以使用此功能。"
        )

    # 驗證因子或 Alpha158 必須選擇其一
    if not req.use_alpha158 and not req.factor_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="請選擇訓練因子或啟用 Alpha158"
        )

    # 先綁定因子到模型（如果提供了 factor_ids）
    if req.factor_ids:
        ModelFactorRepository.batch_create(db, model_id, req.factor_ids)

    # 創建訓練任務
    training_job = ModelTrainingJobRepository.create(
        db=db,
        model_id=model_id,
        user_id=current_user.id,
        dataset_config=req.dataset_config.model_dump(),
        training_params=req.training_params.model_dump()
    )

    # 觸發 Celery 異步訓練任務
    celery_task = train_model_async.apply_async(
        args=[
            training_job.id,
            model_id,
            current_user.id,
            req.factor_ids,
            req.dataset_config.model_dump(),
            req.training_params.model_dump(),
            req.use_alpha158  # 傳遞 Alpha158 參數
        ]
    )
    
    # 更新 celery_task_id
    training_job.celery_task_id = celery_task.id
    db.commit()
    db.refresh(training_job)
    
    api_log.log_operation(
        "train_model", "model_training_job", training_job.id, current_user.id, success=True
    )
    
    return ModelTrainingJobResponse(
        id=training_job.id,
        model_id=training_job.model_id,
        user_id=training_job.user_id,
        dataset_config=training_job.dataset_config,
        training_params=training_job.training_params,
        status=training_job.status,
        progress=training_job.progress,
        current_epoch=training_job.current_epoch,
        total_epochs=training_job.total_epochs,
        current_step=training_job.current_step,
        train_loss=training_job.train_loss,
        valid_loss=training_job.valid_loss,
        test_ic=training_job.test_ic,
        test_metrics=training_job.test_metrics,
        model_weight_path=training_job.model_weight_path,
        training_log=training_job.training_log,
        error_message=training_job.error_message,
        celery_task_id=training_job.celery_task_id,
        started_at=training_job.started_at,
        completed_at=training_job.completed_at,
        created_at=training_job.created_at
    )


@router.get("/training-jobs/{job_id}", response_model=ModelTrainingJobResponse)
async def get_training_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """獲取訓練任務詳情（用於前端輪詢）
    
    查詢訓練任務的即時進度、狀態和日誌。
    前端可以每 5 秒輪詢一次此端點以更新訊息欄。
    
    Args:
        job_id: 訓練任務 ID
    
    Returns:
        訓練任務詳情（包含 progress, current_step, training_log 等）
    """
    from app.repositories.model_training_job import ModelTrainingJobRepository
    
    job = ModelTrainingJobRepository.get_by_id(db, job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="訓練任務不存在"
        )
    
    # 驗證權限
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="無權訪問此訓練任務"
        )
    
    return ModelTrainingJobResponse(
        id=job.id,
        model_id=job.model_id,
        user_id=job.user_id,
        dataset_config=job.dataset_config,
        training_params=job.training_params,
        status=job.status,
        progress=job.progress,
        current_epoch=job.current_epoch,
        total_epochs=job.total_epochs,
        current_step=job.current_step,
        train_loss=job.train_loss,
        valid_loss=job.valid_loss,
        test_ic=job.test_ic,
        test_metrics=job.test_metrics,
        model_weight_path=job.model_weight_path,
        training_log=job.training_log,
        error_message=job.error_message,
        celery_task_id=job.celery_task_id,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at
    )


@router.get("/models/{model_id}/training-jobs", response_model=ModelTrainingJobListResponse)
async def get_model_training_jobs(
    model_id: int,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """獲取模型的訓練任務列表
    
    查詢特定模型的所有歷史訓練任務。
    
    Args:
        model_id: 模型 ID
        limit: 返回數量限制（默認 10）
    
    Returns:
        訓練任務列表
    """
    from app.repositories.generated_model import GeneratedModelRepository
    from app.repositories.model_training_job import ModelTrainingJobRepository
    
    # 驗證模型存在且屬於當前用戶
    model = GeneratedModelRepository.get_by_id(db, model_id)
    if not model or model.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在或無權訪問"
        )
    
    # 獲取訓練任務列表
    jobs = ModelTrainingJobRepository.get_by_model(db, model_id, limit)
    
    job_responses = [
        ModelTrainingJobResponse(
            id=job.id,
            model_id=job.model_id,
            user_id=job.user_id,
            dataset_config=job.dataset_config,
            training_params=job.training_params,
            status=job.status,
            progress=job.progress,
            current_epoch=job.current_epoch,
            total_epochs=job.total_epochs,
            current_step=job.current_step,
            train_loss=job.train_loss,
            valid_loss=job.valid_loss,
            test_ic=job.test_ic,
            test_metrics=job.test_metrics,
            model_weight_path=job.model_weight_path,
            training_log=job.training_log,
            error_message=job.error_message,
            celery_task_id=job.celery_task_id,
            started_at=job.started_at,
            completed_at=job.completed_at,
            created_at=job.created_at
        )
        for job in jobs
    ]
    
    return ModelTrainingJobListResponse(
        jobs=job_responses,
        total=len(job_responses)
    )


@router.post("/training-jobs/{job_id}/cancel", response_model=ModelTrainingJobResponse)
async def cancel_training(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """取消訓練任務
    
    取消正在執行或等待中的訓練任務。
    
    Args:
        job_id: 訓練任務 ID
    
    Returns:
        更新後的訓練任務資訊
    """
    from app.repositories.model_training_job import ModelTrainingJobRepository
    
    job = ModelTrainingJobRepository.get_by_id(db, job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="訓練任務不存在"
        )
    
    # 驗證權限
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="無權訪問此訓練任務"
        )
    
    # 檢查任務狀態
    if job.status not in ["PENDING", "RUNNING"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"任務狀態為 {job.status}，無法取消"
        )
    
    # 觸發 Celery 取消任務
    cancel_training_job.apply_async(args=[job_id])
    
    # 如果有 celery_task_id，嘗試撤銷 Celery 任務
    if job.celery_task_id:
        from app.core.celery_app import celery_app
        celery_app.control.revoke(job.celery_task_id, terminate=True)
    
    api_log.log_operation(
        "cancel", "model_training_job", job_id, current_user.id, success=True
    )
    
    # 重新獲取更新後的任務
    db.refresh(job)
    
    return ModelTrainingJobResponse(
        id=job.id,
        model_id=job.model_id,
        user_id=job.user_id,
        dataset_config=job.dataset_config,
        training_params=job.training_params,
        status=job.status,
        progress=job.progress,
        current_epoch=job.current_epoch,
        total_epochs=job.total_epochs,
        current_step=job.current_step,
        train_loss=job.train_loss,
        valid_loss=job.valid_loss,
        test_ic=job.test_ic,
        test_metrics=job.test_metrics,
        model_weight_path=job.model_weight_path,
        training_log=job.training_log,
        error_message=job.error_message,
        celery_task_id=job.celery_task_id,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at
    )

# ========== 模型預測端點 ==========

@router.post("/models/{model_id}/predict", response_model=ModelPredictionResponse)
@limiter.limit(RateLimits.GENERAL_READ)
async def predict_with_trained_model(
    request: Request,
    model_id: int,
    req: ModelPredictionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """使用訓練好的模型生成預測

    此端點允許你使用已訓練的 PyTorch 模型對指定股票進行預測。

    **流程**：
    1. 加載訓練好的模型權重
    2. 獲取指定日期範圍的因子數據
    3. 生成預測值
    4. 根據閾值轉換為交易信號

    **使用場景**：
    - 回測前預覽模型預測
    - 批量預測多支股票
    - 實時預測最新數據

    Args:
        model_id: 模型 ID
        req: 預測請求（包含股票、日期範圍、信號閾值）

    Returns:
        各股票的預測結果和交易信號
    """
    from datetime import datetime, timezone
    from app.repositories.generated_model import GeneratedModelRepository
    from app.repositories.model_training_job import ModelTrainingJobRepository
    from app.services.model_predictor import ModelPredictor
    from app.services.qlib_data_adapter import QlibDataAdapter

    # 1. 驗證模型權限
    model = GeneratedModelRepository.get_by_id(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    if model.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="無權訪問此模型")

    # 2. 檢查訓練狀態
    jobs = ModelTrainingJobRepository.get_by_model(db, model_id, limit=1)
    if not jobs or jobs[0].status != "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail=f"模型尚未訓練完成。當前狀態: {jobs[0].status if jobs else 'NO_JOB'}"
        )

    job = jobs[0]

    # 3. 加載模型預測器
    try:
        predictor = ModelPredictor.from_model_id(db, model_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"模型權重文件不存在: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加載模型失敗: {str(e)}")

    # 4. 準備數據適配器
    adapter = QlibDataAdapter()

    # 5. 對每支股票生成預測
    all_predictions = []

    for symbol in req.symbols:
        try:
            # 獲取因子數據
            qlib_config = model.qlib_config or {}
            data_handler = qlib_config.get('data', {}).get('handler', {})

            if data_handler.get('class') == 'Alpha158':
                # 使用 Alpha158 因子
                df = adapter.get_alpha158_data(
                    symbol=symbol,
                    start_date=req.start_date,
                    end_date=req.end_date
                )
            else:
                # 使用自定義因子
                from app.repositories.model_factor import ModelFactorRepository
                model_factors = ModelFactorRepository.get_by_model(db, model_id)

                if not model_factors:
                    raise HTTPException(
                        status_code=400,
                        detail=f"模型 {model_id} 沒有關聯的因子"
                    )

                factor_formulas = [mf.factor.formula for mf in model_factors]

                df = adapter.get_qlib_features(
                    symbol=symbol,
                    start_date=req.start_date,
                    end_date=req.end_date,
                    fields=factor_formulas
                )

            if df is None or df.empty:
                logger.warning(f"⚠️ 股票 {symbol} 沒有數據")
                continue

            # 生成預測和信號
            result = predictor.predict_with_signals(
                df,
                buy_threshold=req.buy_threshold,
                sell_threshold=req.sell_threshold
            )

            # 轉換為字典格式（日期字符串 -> 值）
            predictions_dict = {str(date): float(pred) for date, pred in result['prediction'].items()}
            signals_dict = {str(date): int(signal) for date, signal in result['signal'].items()}

            # 計算統計
            stats = {
                'mean_prediction': float(result['prediction'].mean()),
                'std_prediction': float(result['prediction'].std()),
                'buy_signals': int((result['signal'] == 1).sum()),
                'sell_signals': int((result['signal'] == -1).sum()),
                'hold_signals': int((result['signal'] == 0).sum()),
                'total_days': len(result)
            }

            all_predictions.append(
                PredictionData(
                    symbol=symbol,
                    predictions=predictions_dict,
                    signals=signals_dict,
                    stats=stats
                )
            )

            logger.info(f"✅ 股票 {symbol} 預測完成: {stats['buy_signals']} 買入, {stats['sell_signals']} 賣出")

        except Exception as e:
            logger.error(f"❌ 股票 {symbol} 預測失敗: {str(e)}")
            # 跳過失敗的股票，繼續處理其他股票
            continue

    # 6. 返回結果
    return ModelPredictionResponse(
        model_id=model_id,
        model_name=model.name,
        predictions=all_predictions,
        test_ic=job.test_ic,
        generated_at=datetime.now(timezone.utc)
    )


@router.post("/models/{model_id}/export-strategy", response_model=ExportStrategyResponse)
async def export_model_as_strategy(
    model_id: int,
    request: ExportStrategyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    將訓練好的模型導出為 Qlib 策略

    流程：
    1. 獲取模型及其訓練任務
    2. 驗證模型已完成訓練
    3. 創建基於模型的 Qlib 策略
    4. 返回策略 ID 供回測使用
    """
    from app.repositories.generated_model import GeneratedModelRepository
    from app.repositories.model_training_job import ModelTrainingJobRepository

    logger.info(f"User {current_user.id} exporting model {model_id} as strategy: {request.strategy_name}")

    try:
        # 1. 驗證模型權限
        model = GeneratedModelRepository.get_by_id(db, model_id)
        if not model:
            raise HTTPException(status_code=404, detail=f"模型 {model_id} 不存在")

        if model.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="無權訪問此模型")

        # 2. 獲取最新訓練任務
        training_jobs = ModelTrainingJobRepository.get_by_model(db, model_id, limit=1)
        if not training_jobs:
            raise HTTPException(
                status_code=400,
                detail="模型尚未訓練。請先訓練模型。"
            )

        training_job = training_jobs[0]

        if training_job.status != "COMPLETED":
            raise HTTPException(
                status_code=400,
                detail=f"訓練任務狀態為 {training_job.status}。只有已完成的模型可以導出。"
            )

        if not training_job.model_weight_path:
            raise HTTPException(
                status_code=400,
                detail="模型權重不存在。無法導出未訓練的模型。"
            )

        # 3. 使用 rdagent_service 導出為策略
        rdagent_svc = RDAgentService(db)
        strategy_id = await rdagent_svc.export_model_as_qlib_strategy(
            db=db,
            user_id=current_user.id,
            model_id=model_id,
            model=model,
            training_job=training_job,
            strategy_name=request.strategy_name,
            buy_threshold=request.buy_threshold,
            sell_threshold=request.sell_threshold,
            description=request.description
        )

        logger.info(f"✅ Successfully exported model {model_id} as strategy {strategy_id}")

        return ExportStrategyResponse(
            strategy_id=strategy_id,
            strategy_name=request.strategy_name,
            model_id=model_id,
            message=f"模型已成功導出為策略！策略 ID: {strategy_id}，可在回測中心使用。"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to export model {model_id}: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"導出失敗: {str(e)}")
