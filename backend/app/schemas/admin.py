"""
Admin API Schemas
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# User Management Schemas
class UserListResponse(BaseModel):
    """User list response for admin"""
    id: int
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class UserUpdateAdmin(BaseModel):
    """Update user by admin"""
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


# System Stats Schemas
class SystemStats(BaseModel):
    """System statistics"""
    total_users: int
    active_users: int
    total_strategies: int
    total_backtests: int
    database_size: str
    cache_size: str


class ServiceHealth(BaseModel):
    """Service health status"""
    service_name: str
    status: str  # healthy, unhealthy, unknown
    uptime: Optional[str] = None
    last_check: datetime


# Data Sync Management Schemas
class SyncTaskInfo(BaseModel):
    """Sync task information"""
    task_name: str
    display_name: str
    schedule: str
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    status: str  # active, paused, error


class SyncHistoryItem(BaseModel):
    """Sync history record"""
    task_id: str
    task_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str  # pending, running, success, failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ManualSyncRequest(BaseModel):
    """Manual sync request"""
    task_name: str = Field(..., description="Task name to execute")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Task parameters")


# Log Query Schemas
class LogQueryRequest(BaseModel):
    """Log query request"""
    level: Optional[str] = Field(None, description="Log level: DEBUG, INFO, WARNING, ERROR")
    module: Optional[str] = Field(None, description="Module name")
    keyword: Optional[str] = Field(None, description="Search keyword")
    start_time: Optional[datetime] = Field(None, description="Start time")
    end_time: Optional[datetime] = Field(None, description="End time")
    limit: int = Field(100, ge=1, le=1000, description="Result limit")


class LogEntry(BaseModel):
    """Log entry"""
    timestamp: str
    level: str
    module: str
    message: str


class LogQueryResponse(BaseModel):
    """Log query response"""
    total: int
    logs: List[LogEntry]


# Celery Task Management
class CeleryWorkerInfo(BaseModel):
    """Celery worker information"""
    hostname: str
    status: str
    current_active: int = Field(..., description="當前正在執行的任務數")
    total_processed: int = Field(..., description="累計已處理任務數")
    uptime_seconds: Optional[int] = Field(None, description="運行時間（秒）")


class CeleryTaskStatus(BaseModel):
    """Celery task status"""
    task_id: str
    task_name: str
    status: str
    result: Optional[Any] = None
    traceback: Optional[str] = None
    started_at: Optional[datetime] = None


# Security Monitoring Schemas
class SecurityEvent(BaseModel):
    """Security event"""
    type: str = Field(..., description="事件類型：rate_limit, request_size_rejection, cache_tampering")
    timestamp: str
    client_ip: Optional[str] = None
    user_id: Optional[str] = None
    endpoint: Optional[str] = None
    limit: Optional[str] = None
    content_length: Optional[int] = None
    max_allowed: Optional[int] = None
    rejection_type: Optional[str] = None
    size_mb: Optional[float] = None
    cache_key: Optional[str] = None
    client_context: Optional[str] = None


class SecurityStats(BaseModel):
    """Security statistics"""
    rate_limit_total: int = Field(0, description="速率限制總次數")
    request_size_rejection_total: int = Field(0, description="請求過大拒絕總次數")
    cache_tampering_total: int = Field(0, description="快取篡改偵測總次數")
    endpoint_stats: Dict[str, int] = Field(default_factory=dict, description="各端點統計")


class SecurityEventsResponse(BaseModel):
    """Security events response"""
    total: int = Field(..., description="事件總數")
    events: List[SecurityEvent] = Field(..., description="事件列表")
    stats: SecurityStats = Field(..., description="統計資訊")
