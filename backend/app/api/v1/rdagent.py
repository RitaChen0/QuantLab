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
)
from app.tasks.rdagent_tasks import (
    run_factor_mining_task,
    run_model_generation_task,
    run_strategy_optimization_task,
)
from app.core.rate_limit import limiter, RateLimits
from app.utils.logging import api_log

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
