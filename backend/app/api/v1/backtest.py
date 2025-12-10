"""
Backtest API Routes
Handles strategy backtesting operations
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import Optional
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.backtest import BacktestStatus
from app.schemas.backtest import (
    Backtest,
    BacktestDetail,
    BacktestCreate,
    BacktestUpdate,
    BacktestListResponse,
    BacktestRunRequest,
    BacktestProgress,
)
from app.services.backtest_service import BacktestService
from app.services.backtest_engine import BacktestEngine
from app.core.config import settings
from app.core.rate_limit import limiter, RateLimits
from app.utils.logging import api_log
from app.utils.redis_lock import backtest_execution_lock
from app.tasks.backtest import run_backtest_async
from loguru import logger
from datetime import datetime, timezone

router = APIRouter()


def _handle_error(operation: str, error: Exception, user_message: str) -> HTTPException:
    """
    Handle errors with appropriate logging and user-friendly messages

    Args:
        operation: Description of the operation that failed
        error: The caught exception
        user_message: User-friendly error message

    Returns:
        HTTPException with appropriate status and message
    """
    logger.error(f"{operation} failed: {str(error)}", exc_info=settings.DEBUG)
    detail = str(error) if settings.DEBUG else user_message
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=detail
    )


@router.get("/", response_model=BacktestListResponse)
async def list_backtests(
    status_filter: Optional[BacktestStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    取得當前用戶的回測列表

    Args:
        status_filter: 依狀態過濾（pending, running, completed, failed）
        page: 頁碼
        page_size: 每頁筆數

    Returns:
        回測列表與分頁資訊
    """
    try:
        service = BacktestService(db)
        skip = (page - 1) * page_size

        backtests, total = service.get_user_backtests(
            user_id=current_user.id,
            status_filter=status_filter,
            skip=skip,
            limit=page_size
        )

        api_log.log_operation(
            "list",
            "backtest",
            user_id=current_user.id,
            success=True,
            count=len(backtests),
            total=total,
            page=page
        )

        return BacktestListResponse(
            backtests=backtests,
            total=total,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        raise _handle_error(
            "List backtests",
            e,
            "Failed to retrieve backtests. Please try again later."
        )


@router.post("/", response_model=BacktestDetail, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.BACKTEST_CREATE)
async def create_backtest(
    request: Request,
    backtest_create: BacktestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    建立新回測

    Args:
        backtest_create: 回測建立資料

    Returns:
        已建立的回測詳情
    """
    try:
        service = BacktestService(db)
        backtest = service.create_backtest(
            user_id=current_user.id,
            backtest_create=backtest_create
        )

        api_log.log_operation(
            "create",
            "backtest",
            entity_id=backtest.id,
            user_id=current_user.id,
            success=True,
            strategy_id=backtest.strategy_id
        )

        return backtest

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error(
            "Create backtest",
            e,
            "Failed to create backtest. Please try again later."
        )


@router.get("/{backtest_id}", response_model=BacktestDetail)
async def get_backtest(
    backtest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    取得回測詳情

    Args:
        backtest_id: 回測 ID

    Returns:
        回測完整資訊
    """
    try:
        service = BacktestService(db)
        backtest = service.get_backtest(
            backtest_id=backtest_id,
            user_id=current_user.id
        )

        api_log.log_operation(
            "retrieve",
            "backtest",
            entity_id=backtest_id,
            user_id=current_user.id,
            success=True
        )

        return backtest

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error(
            f"Get backtest {backtest_id}",
            e,
            "Failed to retrieve backtest. Please try again later."
        )


@router.put("/{backtest_id}", response_model=BacktestDetail)
async def update_backtest(
    backtest_id: int,
    backtest_update: BacktestUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新回測

    Args:
        backtest_id: 回測 ID
        backtest_update: 更新資料

    Returns:
        更新後的回測詳情
    """
    try:
        service = BacktestService(db)
        backtest = service.update_backtest(
            backtest_id=backtest_id,
            user_id=current_user.id,
            backtest_update=backtest_update
        )

        api_log.log_operation(
            "update",
            "backtest",
            entity_id=backtest_id,
            user_id=current_user.id,
            success=True
        )

        return backtest

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error(
            f"Update backtest {backtest_id}",
            e,
            "Failed to update backtest. Please try again later."
        )


@router.delete("/{backtest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backtest(
    backtest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    刪除回測

    Args:
        backtest_id: 回測 ID

    Returns:
        無內容（204）
    """
    try:
        service = BacktestService(db)
        service.delete_backtest(
            backtest_id=backtest_id,
            user_id=current_user.id
        )

        api_log.log_operation(
            "delete",
            "backtest",
            entity_id=backtest_id,
            user_id=current_user.id,
            success=True
        )

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error(
            f"Delete backtest {backtest_id}",
            e,
            "Failed to delete backtest. Please try again later."
        )


@router.get("/strategy/{strategy_id}", response_model=BacktestListResponse)
async def get_strategy_backtests(
    strategy_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    取得特定策略的回測列表

    Args:
        strategy_id: 策略 ID
        page: 頁碼
        page_size: 每頁筆數

    Returns:
        回測列表與分頁資訊
    """
    try:
        service = BacktestService(db)
        skip = (page - 1) * page_size

        backtests, total = service.get_strategy_backtests(
            strategy_id=strategy_id,
            user_id=current_user.id,
            skip=skip,
            limit=page_size
        )

        api_log.log_operation(
            "list",
            "backtest",
            user_id=current_user.id,
            success=True,
            count=len(backtests),
            total=total,
            strategy_id=strategy_id,
            page=page
        )

        return BacktestListResponse(
            backtests=backtests,
            total=total,
            page=page,
            page_size=page_size
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get backtests for strategy {strategy_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve strategy backtests"
        )


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(RateLimits.BACKTEST_RUN)
async def run_backtest(
    request: Request,
    run_request: BacktestRunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    執行回測（異步執行）

    提交回測任務到 Celery 隊列，立即返回任務 ID。
    使用 GET /api/v1/backtest/{backtest_id}/task/{task_id} 查詢執行狀態。

    Args:
        run_request: 回測執行請求，包含 backtest_id

    Returns:
        任務 ID 和狀態

    Raises:
        HTTPException: 回測不存在、權限不足等錯誤
    """
    try:
        service = BacktestService(db)

        # 1. 取得回測配置（驗證存在和權限）
        backtest = service.get_backtest_with_result(run_request.backtest_id, current_user.id)
        if not backtest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest {run_request.backtest_id} not found"
            )

        # 2. 檢查狀態（避免重複執行已完成的回測）
        if backtest.status == BacktestStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Backtest already completed. Create a new backtest to run again."
            )

        # 3. 檢查是否已經在執行中
        if backtest.status == BacktestStatus.RUNNING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="此回測已在執行中，請等待完成後再試。"
            )

        # 4. 提交異步任務到 Celery
        task = run_backtest_async.apply_async(
            args=[run_request.backtest_id, current_user.id],
            queue='backtest',  # 使用專用隊列
        )

        logger.info(f"Backtest {run_request.backtest_id} submitted to Celery (task_id: {task.id})")

        api_log.log_operation(
            "submit",
            "backtest",
            backtest.id,
            current_user.id,
            success=True,
            task_id=task.id
        )

        return {
            "backtest_id": backtest.id,
            "task_id": task.id,
            "status": "submitted",
            "message": "回測任務已提交，正在排隊執行",
            "status_url": f"/api/v1/backtest/{backtest.id}/task/{task.id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error(
            "Submit backtest",
            e,
            "Failed to submit backtest task"
        )


@router.get("/{backtest_id}/task/{task_id}")
async def get_backtest_task_status(
    backtest_id: int,
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    查詢回測任務執行狀態

    Args:
        backtest_id: 回測 ID
        task_id: Celery 任務 ID

    Returns:
        任務執行狀態和進度
    """
    from celery.result import AsyncResult

    try:
        # 驗證回測存在和權限
        service = BacktestService(db)
        backtest = service.get_backtest(backtest_id, current_user.id)

        # 查詢 Celery 任務狀態
        result = AsyncResult(task_id)

        if result.state == 'PENDING':
            response = {
                'state': 'PENDING',
                'backtest_id': backtest_id,
                'status': '任務等待中...',
                'current': 0,
                'total': 100
            }
        elif result.state == 'PROGRESS':
            response = {
                'state': 'PROGRESS',
                'backtest_id': backtest_id,
                'current': result.info.get('current', 0),
                'total': result.info.get('total', 100),
                'status': result.info.get('status', '執行中...'),
            }
        elif result.state == 'SUCCESS':
            response = {
                'state': 'SUCCESS',
                'backtest_id': backtest_id,
                'current': 100,
                'total': 100,
                'status': '完成！',
                'result': result.info
            }
        elif result.state == 'FAILURE':
            response = {
                'state': 'FAILURE',
                'backtest_id': backtest_id,
                'current': 0,
                'total': 100,
                'status': '執行失敗',
                'error': str(result.info)
            }
        elif result.state == 'RETRY':
            response = {
                'state': 'RETRY',
                'backtest_id': backtest_id,
                'status': '任務重試中...',
                'current': 0,
                'total': 100
            }
        else:
            response = {
                'state': result.state,
                'backtest_id': backtest_id,
                'status': f'未知狀態: {result.state}'
            }

        # 同時返回資料庫中的回測狀態
        response['db_status'] = backtest.status

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error(
            "Get task status",
            e,
            "Failed to retrieve task status"
        )


@router.delete("/{backtest_id}/task/{task_id}")
async def cancel_backtest_task(
    backtest_id: int,
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    取消正在執行的回測任務

    Args:
        backtest_id: 回測 ID
        task_id: Celery 任務 ID

    Returns:
        取消結果

    Raises:
        HTTPException: 回測不存在、權限不足、任務已完成等錯誤
    """
    from celery.result import AsyncResult

    try:
        service = BacktestService(db)

        # 1. 驗證回測存在和權限
        backtest = service.get_backtest(backtest_id, current_user.id)
        if not backtest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest {backtest_id} not found"
            )

        # 2. 檢查當前狀態
        if backtest.status == BacktestStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無法取消已完成的回測"
            )

        if backtest.status == BacktestStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="此回測已經被取消"
            )

        if backtest.status == BacktestStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無法取消已失敗的回測"
            )

        # 3. 取消 Celery 任務
        result = AsyncResult(task_id)

        # 檢查任務是否還在執行
        if result.state in ['PENDING', 'PROGRESS', 'RETRY']:
            # 強制終止任務
            result.revoke(terminate=True, signal='SIGTERM')
            logger.info(f"Celery task {task_id} revoked for backtest {backtest_id}")

        # 4. 更新資料庫狀態
        service.update_backtest_status(backtest_id, BacktestStatus.CANCELLED)
        db.commit()

        api_log.log_operation(
            "cancel",
            "backtest",
            backtest_id,
            current_user.id,
            success=True,
            task_id=task_id
        )

        return {
            "backtest_id": backtest_id,
            "task_id": task_id,
            "status": "cancelled",
            "message": "回測任務已成功取消"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error(
            "Cancel backtest task",
            e,
            "Failed to cancel backtest task"
        )


@router.get("/{backtest_id}/result")
async def get_backtest_result(
    backtest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    取得回測結果

    Args:
        backtest_id: 回測 ID

    Returns:
        回測結果詳情（包含績效指標、交易記錄等）
    """
    try:
        service = BacktestService(db)
        backtest = service.get_backtest_with_result(
            backtest_id=backtest_id,
            user_id=current_user.id
        )

        # Check if backtest is completed
        if backtest.status != BacktestStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Backtest is not completed yet (current status: {backtest.status})"
            )

        if not backtest.result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Backtest result not found"
            )

        api_log.log_operation(
            "retrieve_result",
            "backtest",
            entity_id=backtest_id,
            user_id=current_user.id,
            success=True
        )

        return {
            "backtest_id": backtest.id,
            "status": backtest.status,
            "result": backtest.result,
            "trades": backtest.trades if hasattr(backtest, 'trades') else []
        }

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error(
            "Get backtest result",
            e,
            "Failed to retrieve backtest result. Please try again later."
        )


@router.get("/tasks/active", response_model=dict)
async def get_active_backtest_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    獲取當前正在執行的回測任務

    Returns:
        - active_tasks: 正在執行的任務列表
        - queued_tasks: 排隊中的任務列表
        - worker_info: Worker 狀態信息
    """
    try:
        from celery.result import AsyncResult
        from app.core.celery_app import celery_app

        # 獲取活躍任務
        inspect = celery_app.control.inspect()
        active = inspect.active()
        reserved = inspect.reserved()

        active_backtest_tasks = []
        queued_backtest_tasks = []

        # 處理正在執行的任務
        if active:
            for worker_name, tasks in active.items():
                for task in tasks:
                    if task['name'] == 'app.tasks.run_backtest_async':
                        task_id = task['id']
                        task_args = task.get('args', [])
                        backtest_id = task_args[0] if task_args else None

                        # 獲取任務結果以查看進度
                        result = AsyncResult(task_id)
                        progress_info = {}
                        if result.state == 'PROGRESS':
                            progress_info = result.info or {}

                        # 計算執行時間並檢測超時
                        started_at = task.get('time_start')
                        running_time = None
                        is_timeout_warning = False

                        if started_at:
                            from datetime import datetime
                            running_time = int((datetime.now().timestamp() - started_at))

                            # 軟超時警告（55 分鐘）
                            if running_time > 3300:
                                is_timeout_warning = True

                        active_backtest_tasks.append({
                            'task_id': task_id,
                            'backtest_id': backtest_id,
                            'worker': worker_name,
                            'state': result.state,
                            'progress': progress_info.get('current', 0),
                            'status': progress_info.get('status', 'Running...'),
                            'started_at': started_at,
                            'running_time_seconds': running_time,
                            'timeout_warning': is_timeout_warning,
                        })

        # 處理排隊中的任務
        if reserved:
            for worker_name, tasks in reserved.items():
                for task in tasks:
                    if task['name'] == 'app.tasks.run_backtest_async':
                        task_id = task['id']
                        task_args = task.get('args', [])
                        backtest_id = task_args[0] if task_args else None

                        queued_backtest_tasks.append({
                            'task_id': task_id,
                            'backtest_id': backtest_id,
                            'worker': worker_name,
                            'state': 'QUEUED',
                        })

        # 獲取 Worker 統計信息
        stats = inspect.stats()
        worker_info = []
        if stats:
            for worker_name, worker_stats in stats.items():
                pool_info = worker_stats.get('pool', {})
                total_tasks = worker_stats.get('total', {})

                worker_info.append({
                    'name': worker_name,
                    'concurrency': pool_info.get('max-concurrency', 0),
                    'processes': pool_info.get('processes', []),
                    'total_tasks': total_tasks,
                    'uptime': worker_stats.get('uptime', 0),
                })

        api_log.log_operation(
            "retrieve_active_tasks",
            "backtest",
            user_id=current_user.id,
            success=True,
            metadata={
                'active_count': len(active_backtest_tasks),
                'queued_count': len(queued_backtest_tasks),
            }
        )

        return {
            "active_tasks": active_backtest_tasks,
            "queued_tasks": queued_backtest_tasks,
            "worker_info": worker_info,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "active_count": len(active_backtest_tasks),
                "queued_count": len(queued_backtest_tasks),
                "total_workers": len(worker_info),
            }
        }

    except Exception as e:
        raise _handle_error(
            "Get active backtest tasks",
            e,
            "Failed to retrieve active tasks. Please try again later."
        )
