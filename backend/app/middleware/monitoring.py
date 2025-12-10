"""
監控中介軟體

追蹤速率限制、請求大小拒絕和其他安全事件
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, List
import json
from loguru import logger


class SecurityMonitoring:
    """
    安全事件監控單例

    追蹤和儲存安全相關事件（速率限制、請求拒絕等）
    """

    _instance = None
    _events: List[Dict] = []
    _stats: Dict = defaultdict(int)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._events = []
            cls._stats = defaultdict(int)
        return cls._instance

    def record_rate_limit(
        self,
        client_ip: str,
        user_id: str = None,
        endpoint: str = None,
        limit: str = None
    ):
        """
        記錄速率限制事件

        Args:
            client_ip: 客戶端 IP
            user_id: 使用者 ID（如果已認證）
            endpoint: API 端點
            limit: 速率限制規則
        """
        event = {
            "type": "rate_limit",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "client_ip": client_ip,
            "user_id": user_id,
            "endpoint": endpoint,
            "limit": limit,
        }

        self._events.append(event)
        self._stats["rate_limit_total"] += 1
        self._stats[f"rate_limit_{endpoint}"] += 1

        logger.warning(
            f"🚫 速率限制觸發 - IP: {client_ip}, "
            f"User: {user_id or 'anonymous'}, "
            f"Endpoint: {endpoint}, "
            f"Limit: {limit}"
        )

    def record_request_size_rejection(
        self,
        client_ip: str,
        endpoint: str,
        content_length: int,
        max_allowed: int,
        rejection_type: str = "general"
    ):
        """
        記錄請求大小拒絕事件

        Args:
            client_ip: 客戶端 IP
            endpoint: API 端點
            content_length: 請求大小（bytes）
            max_allowed: 允許的最大大小
            rejection_type: 拒絕類型（general, strategy_code）
        """
        event = {
            "type": "request_size_rejection",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "client_ip": client_ip,
            "endpoint": endpoint,
            "content_length": content_length,
            "max_allowed": max_allowed,
            "rejection_type": rejection_type,
            "size_mb": round(content_length / (1024 * 1024), 2),
        }

        self._events.append(event)
        self._stats["request_size_rejection_total"] += 1
        self._stats[f"request_size_rejection_{rejection_type}"] += 1

        logger.warning(
            f"🚫 請求過大被拒絕 - IP: {client_ip}, "
            f"Endpoint: {endpoint}, "
            f"Size: {event['size_mb']} MB, "
            f"Max: {round(max_allowed / (1024 * 1024), 1)} MB, "
            f"Type: {rejection_type}"
        )

    def record_cache_tampering(
        self,
        cache_key: str,
        client_context: str = None
    ):
        """
        記錄快取篡改事件

        Args:
            cache_key: 快取鍵
            client_context: 客戶端上下文（如果可用）
        """
        event = {
            "type": "cache_tampering",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cache_key": cache_key,
            "client_context": client_context,
        }

        self._events.append(event)
        self._stats["cache_tampering_total"] += 1

        logger.error(
            f"🔒 偵測到快取篡改！Key: {cache_key}, "
            f"Context: {client_context or 'unknown'}"
        )

    def get_recent_events(self, limit: int = 100, event_type: str = None) -> List[Dict]:
        """
        獲取最近的事件

        Args:
            limit: 返回的最大事件數
            event_type: 過濾事件類型（可選）

        Returns:
            事件列表
        """
        events = self._events

        if event_type:
            events = [e for e in events if e.get("type") == event_type]

        return events[-limit:]

    def get_stats(self) -> Dict:
        """
        獲取統計資訊

        Returns:
            統計字典
        """
        return dict(self._stats)

    def clear_old_events(self, keep_last: int = 1000):
        """
        清理舊事件（保留最近 N 個）

        Args:
            keep_last: 保留的事件數量
        """
        if len(self._events) > keep_last:
            removed = len(self._events) - keep_last
            self._events = self._events[-keep_last:]
            logger.info(f"清理了 {removed} 個舊事件")


# 全域監控實例
security_monitoring = SecurityMonitoring()


class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    監控中介軟體

    攔截 HTTP 錯誤並記錄到監控系統
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        處理請求並監控錯誤

        Args:
            request: HTTP 請求
            call_next: 下一個處理器

        Returns:
            HTTP 響應
        """
        response = await call_next(request)

        # 監控 429 (速率限制) 和 413 (請求過大) 錯誤
        if response.status_code == 429:
            # 速率限制被觸發
            client_ip = request.client.host if request.client else "unknown"
            endpoint = request.url.path

            # 嘗試從請求狀態獲取用戶 ID
            user_id = None
            if hasattr(request.state, "user") and request.state.user:
                user_id = str(request.state.user.id)

            security_monitoring.record_rate_limit(
                client_ip=client_ip,
                user_id=user_id,
                endpoint=endpoint,
                limit="unknown"  # 實際限制會在 slowapi 的錯誤處理中記錄
            )

        elif response.status_code == 413:
            # 請求過大被拒絕
            client_ip = request.client.host if request.client else "unknown"
            endpoint = request.url.path
            content_length = int(request.headers.get("content-length", 0))

            security_monitoring.record_request_size_rejection(
                client_ip=client_ip,
                endpoint=endpoint,
                content_length=content_length,
                max_allowed=0,  # 實際值在中介軟體中已記錄
                rejection_type="general"
            )

        return response
