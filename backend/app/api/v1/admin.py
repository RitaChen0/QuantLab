"""
Admin API Endpoints

Requires superuser authentication.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone, timedelta
from celery.schedules import crontab

from app.api.dependencies import get_db, get_current_superuser
from app.db.session import SessionLocal
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
from app.services.admin_service import AdminService

router = APIRouter()


def get_admin_service(db: Session = Depends(get_db)) -> AdminService:
    """Dependency to get AdminService instance"""
    return AdminService(db)


def format_crontab_schedule(schedule) -> str:
    """
    將 crontab schedule 轉換為人類可讀的文字

    重要：Celery 配置為 timezone="UTC", enable_utc=True
    因此 crontab 的時間參數是 UTC 時間，需要轉換為台北時間顯示！

    Examples:
        crontab(hour=1, minute=0) -> "每天 09:00 (台北時間)"（UTC 01:00 = 台北 09:00）
        crontab(hour='1-5', minute='*/15') -> "交易日 09:00-13:59 每 15 分鐘 (台北時間)"
    """
    if not isinstance(schedule, crontab):
        return str(schedule)

    # 解析 crontab 各個欄位（UTC 時間）
    minute = schedule._orig_minute
    hour = schedule._orig_hour
    day_of_month = schedule._orig_day_of_month
    month_of_year = schedule._orig_month_of_year
    day_of_week = schedule._orig_day_of_week

    # Helper function: UTC → 台北時間（+8 小時）
    def utc_to_taipei(hour_utc: int) -> int:
        """Convert UTC hour to Taipei hour (UTC+8)"""
        return (hour_utc + 8) % 24

    # 星期對照表
    weekday_map = {
        '0': '週日', '1': '週一', '2': '週二', '3': '週三',
        '4': '週四', '5': '週五', '6': '週六'
    }

    # 月份對照表
    month_map = {
        '1': '1月', '2': '2月', '3': '3月', '4': '4月',
        '5': '5月', '6': '6月', '7': '7月', '8': '8月',
        '9': '9月', '10': '10月', '11': '11月', '12': '12月'
    }

    # 處理每週特定日期（非時間範圍）
    if day_of_week != '*' and hour != '*' and minute != '*' and not (isinstance(hour, str) and '-' in hour):
        # 轉換 UTC → 台北時間
        taipei_hour = utc_to_taipei(int(hour))
        if day_of_week == 'mon,tue,wed,thu,fri':
            return f"交易日 {str(taipei_hour).zfill(2)}:{str(minute).zfill(2)} (台北時間)"
        weekday = weekday_map.get(str(day_of_week), f'週{day_of_week}')
        return f"每{weekday} {str(taipei_hour).zfill(2)}:{str(minute).zfill(2)} (台北時間)"

    # 處理每月特定日期
    if day_of_month != '*' and hour != '*' and minute != '*':
        taipei_hour = utc_to_taipei(int(hour))
        return f"每月 {day_of_month} 日 {str(taipei_hour).zfill(2)}:{str(minute).zfill(2)} (台北時間)"

    # 處理每年特定日期
    if month_of_year != '*' and day_of_month != '*' and hour != '*' and minute != '*':
        taipei_hour = utc_to_taipei(int(hour))
        month = month_map.get(str(month_of_year), f'{month_of_year}月')
        return f"每年 {month} {day_of_month} 日 {str(taipei_hour).zfill(2)}:{str(minute).zfill(2)} (台北時間)"

    # 處理每小時
    if hour == '*' and minute != '*':
        if isinstance(minute, str) and minute.startswith('*/'):
            interval = minute.replace('*/', '')
            return f"每 {interval} 分鐘"
        return f"每小時 {str(minute).zfill(2)} 分"

    # 處理特定時間範圍（含 day_of_week）
    if hour != '*' and isinstance(hour, str) and '-' in hour:
        start_hour_utc, end_hour_utc = hour.split('-')
        # 轉換 UTC → 台北時間
        start_hour_taipei = utc_to_taipei(int(start_hour_utc))
        end_hour_taipei = utc_to_taipei(int(end_hour_utc))

        if isinstance(minute, str) and minute.startswith('*/'):
            interval = minute.replace('*/', '')
            if day_of_week == 'mon,tue,wed,thu,fri':
                prefix = "交易日"
            elif day_of_week != '*':
                prefix = f"每{weekday_map.get(str(day_of_week), '天')}"
            else:
                prefix = "每天"
            return f"{prefix} {str(start_hour_taipei).zfill(2)}:00-{str(end_hour_taipei).zfill(2)}:59 每 {interval} 分鐘 (台北時間)"

    # 處理每天特定時間
    if day_of_week == '*' and day_of_month == '*' and hour != '*' and minute != '*':
        # 檢查是否為間隔 (例如 */4)
        if isinstance(hour, str) and hour.startswith('*/'):
            interval = hour.replace('*/', '')
            return f"每 {interval} 小時"

        # 轉換 UTC → 台北時間
        taipei_hour = utc_to_taipei(int(hour))
        return f"每天 {str(taipei_hour).zfill(2)}:{str(minute).zfill(2)} (台北時間)"

    # 預設返回原始格式（UTC 時間 + 標註）
    return f"{minute} {hour} {day_of_month} {month_of_year} {day_of_week} (UTC)"


# ============ User Management ============

@router.get("/users", response_model=List[UserListResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_superuser),
    admin_service: AdminService = Depends(get_admin_service),
):
    """Get all users (admin only)"""
    users = admin_service.list_users(skip=skip, limit=limit)
    return users


@router.get("/users/{user_id}", response_model=UserListResponse)
async def get_user_detail(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    admin_service: AdminService = Depends(get_admin_service),
):
    """Get user detail (admin only)"""
    user = admin_service.get_user(user_id)
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
    admin_service: AdminService = Depends(get_admin_service),
):
    """Update user (admin only)"""
    user = admin_service.update_user(user_id, user_update)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    logger.info(f"Admin {current_user.username} updated user {user.username}")
    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    admin_service: AdminService = Depends(get_admin_service),
):
    """
    Delete user (admin only)

    Returns detailed information about the deletion result,
    including related data counts and error details if deletion fails.
    """
    from app.core.exceptions import DatabaseError

    result = admin_service.delete_user(user_id, current_user.id)

    if not result["success"]:
        error_code = result.get("error_code", "UNKNOWN_ERROR")

        # Map error codes to HTTP status codes
        status_code_map = {
            "CANNOT_DELETE_SELF": status.HTTP_400_BAD_REQUEST,
            "CANNOT_DELETE_SYSTEM_ADMIN": status.HTTP_403_FORBIDDEN,
            "CANNOT_DELETE_PROTECTED_ACCOUNT": status.HTTP_403_FORBIDDEN,
            "USER_NOT_FOUND": status.HTTP_404_NOT_FOUND,
            "FOREIGN_KEY_VIOLATION": status.HTTP_409_CONFLICT,
            "DATABASE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "UNKNOWN_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        }

        http_status = status_code_map.get(error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Use DatabaseError for better error formatting
        if error_code in ["FOREIGN_KEY_VIOLATION", "DATABASE_ERROR"]:
            raise DatabaseError(
                message=result["message"],
                details=result.get("details", {})
            )
        else:
            raise HTTPException(
                status_code=http_status,
                detail={
                    "message": result["message"],
                    "error_code": error_code,
                    "details": result.get("details")
                }
            )

    logger.info(f"Admin {current_user.username} deleted user ID {user_id}")

    return {
        "success": True,
        "message": result["message"],
        "details": result.get("details", {})
    }


# ============ System Stats ============

@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    current_user: User = Depends(get_current_superuser),
    admin_service: AdminService = Depends(get_admin_service),
):
    """Get system statistics (admin only)"""
    stats = admin_service.get_system_stats()
    return SystemStats(**stats)


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

    # ============================================
    # 任務分類：數據同步、數據處理、策略處理
    # ============================================

    # 數據同步任務（外部 API → 資料庫）
    data_sync_task_names = [
        "app.tasks.sync_stock_list",
        "app.tasks.sync_daily_prices",
        "app.tasks.sync_ohlcv_data",
        "app.tasks.sync_latest_prices_shioaji",
        "app.tasks.sync_fundamental_data",
        "app.tasks.sync_fundamental_latest",
        "app.tasks.sync_top_stocks_institutional",
        "app.tasks.sync_institutional_investors",
        "app.tasks.sync_single_stock_institutional",
        "app.tasks.sync_shioaji_top_stocks",
        "app.tasks.sync_shioaji_futures",
        "app.tasks.sync_option_daily_factors",
        "app.tasks.register_option_contracts",
    ]

    # 數據處理任務（資料庫 → 計算 → 資料庫/文件）
    data_processing_task_names = [
        "app.tasks.generate_continuous_contracts",
        "app.tasks.register_new_futures_contracts",
        "app.tasks.cleanup_old_cache",
        "app.tasks.cleanup_old_institutional_data",
        "app.tasks.cleanup_old_signals",
    ]

    # 策略處理任務（資料庫 → 策略引擎 → 信號）
    strategy_processing_task_names = [
        "app.tasks.monitor_active_strategies",
    ]

    task_display_names = {
        # 數據同步任務
        "app.tasks.sync_stock_list": "同步股票列表",
        "app.tasks.sync_daily_prices": "同步每日價格",
        "app.tasks.sync_ohlcv_data": "同步 OHLCV 數據",
        "app.tasks.sync_latest_prices_shioaji": "同步最新價格（Shioaji）",
        "app.tasks.sync_fundamental_data": "同步財務指標（完整）",
        "app.tasks.sync_fundamental_latest": "同步財務指標（快速）",
        "app.tasks.sync_top_stocks_institutional": "同步法人買賣超（全部股票）",
        "app.tasks.sync_institutional_investors": "同步法人買賣超",
        "app.tasks.sync_single_stock_institutional": "同步單一股票法人買賣超",
        "app.tasks.sync_shioaji_top_stocks": "同步 Shioaji 分鐘線（全部股票）",
        "app.tasks.sync_shioaji_futures": "同步 Shioaji 期貨分鐘線（TX/MTX）",
        "app.tasks.sync_option_daily_factors": "同步選擇權因子（含計算）",
        "app.tasks.register_option_contracts": "註冊選擇權合約",

        # 數據處理任務
        "app.tasks.generate_continuous_contracts": "生成期貨連續合約",
        "app.tasks.register_new_futures_contracts": "註冊新年度期貨合約",
        "app.tasks.cleanup_old_cache": "清理過期快取",
        "app.tasks.cleanup_old_institutional_data": "清理過期法人數據",
        "app.tasks.cleanup_old_signals": "清理舊信號記錄",

        # 策略處理任務
        "app.tasks.monitor_active_strategies": "🔔 監控策略信號（實盤）",
    }

    for name, config in schedule.items():
        task_name = config["task"]

        # Only include data sync tasks
        if task_name not in data_sync_task_names:
            continue

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
            schedule=format_crontab_schedule(config["schedule"]),
            last_run=last_run,
            last_run_status=last_run_status,
            last_run_result=last_run_result,
            error_message=error_message,
            status="active",
        ))

    return tasks


@router.get("/processing/tasks", response_model=List[SyncTaskInfo])
async def list_processing_tasks(
    current_user: User = Depends(get_current_superuser),
):
    """Get all data processing tasks and their schedules (admin only)"""
    from app.utils.cache import cache
    import json

    schedule = celery_app.conf.beat_schedule
    tasks = []

    # 數據處理任務清單（資料庫 → 計算 → 資料庫/文件）
    data_processing_task_names = [
        "app.tasks.generate_continuous_contracts",
        "app.tasks.register_new_futures_contracts",
        "app.tasks.cleanup_old_cache",
        "app.tasks.cleanup_old_institutional_data",
        "app.tasks.cleanup_old_signals",
    ]

    task_display_names = {
        "app.tasks.generate_continuous_contracts": "生成期貨連續合約",
        "app.tasks.register_new_futures_contracts": "註冊新年度期貨合約",
        "app.tasks.cleanup_old_cache": "清理過期快取",
        "app.tasks.cleanup_old_institutional_data": "清理過期法人數據",
        "app.tasks.cleanup_old_signals": "清理舊信號記錄",
    }

    for name, config in schedule.items():
        task_name = config["task"]

        # Only include data processing tasks
        if task_name not in data_processing_task_names:
            continue

        # Get last run information from Redis cache
        last_run = None
        last_run_status = None
        last_run_result = None
        error_message = None

        try:
            if cache.is_available():
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
            schedule=format_crontab_schedule(config["schedule"]),
            last_run=last_run,
            last_run_status=last_run_status,
            last_run_result=last_run_result,
            error_message=error_message,
            status="active",
        ))

    return tasks


@router.get("/monitoring/tasks", response_model=List[SyncTaskInfo])
async def list_monitoring_tasks(
    current_user: User = Depends(get_current_superuser),
):
    """Get all strategy processing tasks and their schedules (admin only)"""
    from app.utils.cache import cache
    import json

    schedule = celery_app.conf.beat_schedule
    tasks = []

    # 策略處理任務清單（資料庫 → 策略引擎 → 信號）
    strategy_processing_task_names = [
        "app.tasks.monitor_active_strategies",
    ]

    task_display_names = {
        "app.tasks.monitor_active_strategies": "🔔 監控策略信號（實盤）",
    }

    for name, config in schedule.items():
        task_name = config["task"]

        # Only include strategy processing tasks
        if task_name not in strategy_processing_task_names:
            continue

        # Get last run information from Redis cache
        last_run = None
        last_run_status = None
        last_run_result = None
        error_message = None

        try:
            if cache.is_available():
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
            schedule=format_crontab_schedule(config["schedule"]),
            last_run=last_run,
            last_run_status=last_run_status,
            last_run_result=last_run_result,
            error_message=error_message,
            status="active",
        ))

    return tasks


@router.get("/monitoring/stats")
async def get_monitoring_stats(
    current_user: User = Depends(get_current_superuser),
    admin_service: AdminService = Depends(get_admin_service),
):
    """Get strategy monitoring statistics (admin only)"""
    return admin_service.get_monitoring_stats()


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
