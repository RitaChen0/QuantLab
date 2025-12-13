"""
Admin API Endpoints

Requires superuser authentication.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone, timedelta

from app.api.dependencies import get_db, get_current_superuser
from app.models.user import User
from app.models.strategy import Strategy
from app.models.backtest import Backtest
from app.schemas.admin import (
    UserListResponse,
    UserUpdateAdmin,
    SystemStats,
    ServiceHealth,
    SyncTaskInfo,
    SyncHistoryItem,
    ManualSyncRequest,
    LogQueryRequest,
    LogQueryResponse,
    LogEntry,
    CeleryWorkerInfo,
    CeleryTaskStatus,
    SecurityEvent,
    SecurityStats,
    SecurityEventsResponse,
)
from app.core.celery_app import celery_app
from app.utils.logging import logger

router = APIRouter()


# ============ User Management ============

@router.get("/users", response_model=List[UserListResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """Get all users (admin only)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/users/{user_id}", response_model=UserListResponse)
async def get_user_detail(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """Get user detail (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.patch("/users/{user_id}", response_model=UserListResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdateAdmin,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """Update user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update fields
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    logger.info(f"Admin {current_user.username} updated user {user.username}")
    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """Delete user (admin only)"""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    db.delete(user)
    db.commit()

    logger.info(f"Admin {current_user.username} deleted user {user.username}")
    return {"message": "User deleted successfully"}


# ============ System Stats ============

@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """Get system statistics (admin only)"""
    from sqlalchemy import text

    # Count users
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()

    # Count strategies and backtests
    total_strategies = db.query(Strategy).count()
    total_backtests = db.query(Backtest).count()

    # Get database size
    db_size_result = db.execute(
        text("SELECT pg_size_pretty(pg_database_size('quantlab'))")
    ).fetchone()
    database_size = db_size_result[0] if db_size_result else "Unknown"

    # Get cache info (Redis)
    from app.utils.cache import cache
    try:
        if cache.is_available():
            cache_info = cache.redis_client.info("memory")
            cache_size = f"{cache_info.get('used_memory_human', 'Unknown')}"
        else:
            cache_size = "Unavailable"
    except Exception as e:
        logger.error(f"Failed to get cache size: {str(e)}")
        cache_size = "Unknown"

    return SystemStats(
        total_users=total_users,
        active_users=active_users,
        total_strategies=total_strategies,
        total_backtests=total_backtests,
        database_size=database_size,
        cache_size=cache_size,
    )


@router.get("/health", response_model=List[ServiceHealth])
async def get_services_health(
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """Check health of all services (admin only)"""
    services = []

    # Check PostgreSQL
    try:
        # Execute a simple query to test database connectivity
        # No explicit transaction needed for read-only health checks
        result = db.execute(text("SELECT 1"))
        result.fetchone()  # Ensure query executes
        services.append(ServiceHealth(
            service_name="PostgreSQL",
            status="healthy",
            last_check=datetime.now(timezone.utc)
        ))
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {str(e)}")
        services.append(ServiceHealth(
            service_name="PostgreSQL",
            status="unhealthy",
            last_check=datetime.now(timezone.utc)
        ))

    # Check Redis
    from app.utils.cache import cache
    try:
        if cache.is_available():
            cache.redis_client.ping()
            services.append(ServiceHealth(
                service_name="Redis",
                status="healthy",
                last_check=datetime.now(timezone.utc)
            ))
        else:
            services.append(ServiceHealth(
                service_name="Redis",
                status="unhealthy",
                last_check=datetime.now(timezone.utc)
            ))
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        services.append(ServiceHealth(
            service_name="Redis",
            status="unhealthy",
            last_check=datetime.now(timezone.utc)
        ))

    # Check Celery Worker
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        if stats:
            services.append(ServiceHealth(
                service_name="Celery Worker",
                status="healthy",
                last_check=datetime.now(timezone.utc)
            ))
        else:
            logger.warning("Celery Worker health check: No workers found")
            services.append(ServiceHealth(
                service_name="Celery Worker",
                status="unhealthy",
                last_check=datetime.now(timezone.utc)
            ))
    except Exception as e:
        logger.error(f"Celery Worker health check failed: {str(e)}")
        services.append(ServiceHealth(
            service_name="Celery Worker",
            status="unknown",
            last_check=datetime.now(timezone.utc)
        ))

    return services


# ============ Data Sync Management ============

@router.get("/sync/tasks", response_model=List[SyncTaskInfo])
async def list_sync_tasks(
    current_user: User = Depends(get_current_superuser),
):
    """Get all sync tasks and their schedules (admin only)"""
    from app.utils.cache import cache
    import json

    schedule = celery_app.conf.beat_schedule
    tasks = []

    task_display_names = {
        "app.tasks.sync_stock_list": "同步股票列表",
        "app.tasks.sync_daily_prices": "同步每日價格",
        "app.tasks.sync_ohlcv_data": "同步 OHLCV 數據",
        "app.tasks.sync_latest_prices": "同步最新價格",
        "app.tasks.cleanup_old_cache": "清理過期快取",
        "app.tasks.sync_fundamental_data": "同步財務指標（完整）",
        "app.tasks.sync_fundamental_latest": "同步財務指標（快速）",
        "app.tasks.sync_top_stocks_institutional": "同步法人買賣超（Top 100）",
        "app.tasks.sync_institutional_investors": "同步法人買賣超",
        "app.tasks.sync_single_stock_institutional": "同步單一股票法人買賣超",
        "app.tasks.cleanup_old_institutional_data": "清理過期法人數據",
    }

    for name, config in schedule.items():
        task_name = config["task"]

        # Get last run information from Redis cache
        last_run = None
        last_run_status = None
        last_run_result = None
        error_message = None

        try:
            if cache.is_available():
                # Try to get task execution history from Redis
                # Key format: task_history:{task_name}
                history_key = f"task_history:{task_name}"
                history_data = cache.get(history_key)

                if history_data:
                    if isinstance(history_data, str):
                        history_data = json.loads(history_data)

                    last_run_str = history_data.get("last_run")
                    if last_run_str:
                        last_run = datetime.fromisoformat(last_run_str.replace('Z', '+00:00'))

                    last_run_status = history_data.get("status", "unknown")
                    last_run_result = history_data.get("result")
                    error_message = history_data.get("error")
        except Exception as e:
            logger.warning(f"Failed to get task history for {task_name}: {str(e)}")

        tasks.append(SyncTaskInfo(
            task_name=task_name,
            display_name=task_display_names.get(task_name, task_name),
            schedule=str(config["schedule"]),
            last_run=last_run,
            last_run_status=last_run_status,
            last_run_result=last_run_result,
            error_message=error_message,
            status="active",
        ))

    return tasks


@router.post("/sync/trigger")
async def trigger_sync_task(
    request: ManualSyncRequest,
    current_user: User = Depends(get_current_superuser),
):
    """Manually trigger a sync task (admin only)"""
    try:
        result = celery_app.send_task(
            request.task_name,
            kwargs=request.params or {}
        )

        logger.info(f"Admin {current_user.username} triggered task {request.task_name}")

        return {
            "message": "Task submitted successfully",
            "task_id": result.id,
            "task_name": request.task_name,
        }
    except Exception as e:
        logger.error(f"Failed to trigger task {request.task_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger task: {str(e)}"
        )


@router.get("/sync/workers", response_model=List[CeleryWorkerInfo])
async def get_celery_workers(
    current_user: User = Depends(get_current_superuser),
):
    """Get Celery worker information (admin only)"""
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()

        if not stats:
            return []

        # Get current active tasks
        active_tasks_dict = inspect.active()

        workers = []
        for hostname, info in stats.items():
            # Calculate total processed tasks from task breakdown
            total_dict = info.get("total", {})
            total_processed = sum(total_dict.values()) if isinstance(total_dict, dict) else 0

            # Get current active task count (actually running now)
            current_active = len(active_tasks_dict.get(hostname, [])) if active_tasks_dict else 0

            # Get uptime in seconds
            uptime_seconds = int(info.get("uptime", 0))

            workers.append(CeleryWorkerInfo(
                hostname=hostname,
                status="active",
                current_active=current_active,
                total_processed=total_processed,
                uptime_seconds=uptime_seconds,
            ))

        return workers
    except Exception as e:
        logger.error(f"Failed to get Celery workers: {str(e)}")
        return []


@router.get("/sync/active-tasks", response_model=List[CeleryTaskStatus])
async def get_active_tasks(
    current_user: User = Depends(get_current_superuser),
):
    """Get currently running tasks (admin only)"""
    try:
        inspect = celery_app.control.inspect()
        active = inspect.active()

        if not active:
            return []

        tasks = []
        for worker, task_list in active.items():
            for task in task_list:
                tasks.append(CeleryTaskStatus(
                    task_id=task["id"],
                    task_name=task["name"],
                    status="running",
                ))

        return tasks
    except Exception as e:
        logger.error(f"Failed to get active tasks: {str(e)}")
        return []


# ============ Log Query ============

@router.post("/logs/query", response_model=LogQueryResponse)
async def query_logs(
    request: LogQueryRequest,
    current_user: User = Depends(get_current_superuser),
):
    """Query application logs (admin only)"""
    import subprocess
    import re
    import shutil

    try:
        # Check if docker command is available
        if not shutil.which("docker"):
            # Docker not available in container, return helpful message
            help_message = (
                "日誌查詢功能需要從主機執行。請使用以下命令查看日誌：\n\n"
                "# 查看所有日誌\n"
                "docker compose logs --tail 100\n\n"
                "# 查看特定服務\n"
                "docker compose logs --tail 100 backend\n"
                "docker compose logs --tail 100 celery-worker\n\n"
                "# 即時跟蹤日誌\n"
                "docker compose logs -f backend"
            )
            return LogQueryResponse(
                total=1,
                logs=[LogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    level="INFO",
                    module="system",
                    message=help_message
                )]
            )

        # Build docker logs command
        cmd = ["docker", "compose", "logs", "--tail", str(request.limit)]

        # Add service filter
        if request.module:
            if request.module == "backend":
                cmd.append("backend")
            elif request.module == "celery":
                cmd.extend(["celery-worker", "celery-beat"])
            elif request.module == "frontend":
                cmd.append("frontend")

        # Execute command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )

        lines = result.stdout.split("\n")
        logs = []

        # Parse log lines
        for line in lines:
            if not line.strip():
                continue

            # Filter by level
            if request.level:
                if request.level.upper() not in line.upper():
                    continue

            # Filter by keyword
            if request.keyword:
                if request.keyword.lower() not in line.lower():
                    continue

            # Extract log components (basic parsing)
            timestamp_match = re.search(r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}', line)
            level_match = re.search(r'(DEBUG|INFO|WARNING|ERROR|CRITICAL)', line)

            logs.append(LogEntry(
                timestamp=timestamp_match.group(0) if timestamp_match else "Unknown",
                level=level_match.group(0) if level_match else "INFO",
                module=request.module or "Unknown",
                message=line,
            ))

        return LogQueryResponse(
            total=len(logs),
            logs=logs[:request.limit]
        )

    except Exception as e:
        logger.error(f"Failed to query logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"日誌查詢失敗。請使用命令行查看: docker compose logs --tail 100"
        )


# ============ Security Monitoring ============

@router.get("/security/events", response_model=SecurityEventsResponse)
async def get_security_events(
    event_type: Optional[str] = Query(None, description="過濾事件類型：rate_limit, request_size_rejection, cache_tampering"),
    limit: int = Query(100, ge=1, le=1000, description="返回的最大事件數"),
    current_user: User = Depends(get_current_superuser),
):
    """
    獲取安全事件記錄（需 superuser 權限）

    追蹤速率限制、請求過大拒絕、快取篡改等安全事件
    """
    from app.middleware.monitoring import security_monitoring

    # 獲取事件
    events = security_monitoring.get_recent_events(limit=limit, event_type=event_type)

    # 獲取統計資訊
    stats_dict = security_monitoring.get_stats()

    # 轉換為響應格式
    security_events = [SecurityEvent(**event) for event in events]

    # 構建統計資訊
    stats = SecurityStats(
        rate_limit_total=stats_dict.get("rate_limit_total", 0),
        request_size_rejection_total=stats_dict.get("request_size_rejection_total", 0),
        cache_tampering_total=stats_dict.get("cache_tampering_total", 0),
        endpoint_stats={
            k: v for k, v in stats_dict.items()
            if k.startswith("rate_limit_") and k != "rate_limit_total"
        }
    )

    return SecurityEventsResponse(
        total=len(events),
        events=security_events,
        stats=stats
    )


@router.get("/security/stats", response_model=SecurityStats)
async def get_security_stats(
    current_user: User = Depends(get_current_superuser),
):
    """
    獲取安全統計資訊（需 superuser 權限）

    返回速率限制、請求拒絕等統計數據
    """
    from app.middleware.monitoring import security_monitoring

    stats_dict = security_monitoring.get_stats()

    return SecurityStats(
        rate_limit_total=stats_dict.get("rate_limit_total", 0),
        request_size_rejection_total=stats_dict.get("request_size_rejection_total", 0),
        cache_tampering_total=stats_dict.get("cache_tampering_total", 0),
        endpoint_stats={
            k: v for k, v in stats_dict.items()
            if k.startswith("rate_limit_") and k != "rate_limit_total"
        }
    )


@router.post("/security/events/clear")
async def clear_security_events(
    keep_last: int = Query(1000, ge=0, description="保留的最近事件數量"),
    current_user: User = Depends(get_current_superuser),
):
    """
    清理舊的安全事件（需 superuser 權限）

    保留最近 N 個事件，刪除較舊的記錄
    """
    from app.middleware.monitoring import security_monitoring

    security_monitoring.clear_old_events(keep_last=keep_last)

    logger.info(f"Admin {current_user.username} cleared old security events, keeping last {keep_last}")

    return {
        "message": "舊事件已清理",
        "kept_events": keep_last
    }
