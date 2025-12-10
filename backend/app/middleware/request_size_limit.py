"""
Request Size Limit Middleware

防止 DoS 攻擊：限制請求 body 大小
"""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from loguru import logger
from app.core.config import settings


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    請求大小限制中介軟體

    檢查 Content-Length header，拒絕過大的請求

    預設限制：10 MB（可透過環境變數配置）
    """

    def __init__(self, app, max_size: int = None):
        """
        初始化中介軟體

        Args:
            app: FastAPI 應用實例
            max_size: 最大請求大小（bytes），預設使用 settings.MAX_REQUEST_SIZE
        """
        super().__init__(app)
        self.max_size = max_size or settings.MAX_REQUEST_SIZE

        logger.info(
            f"🔒 請求大小限制中介軟體已啟用：最大 {self.max_size / (1024 * 1024):.1f} MB"
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        處理請求

        Args:
            request: HTTP 請求
            call_next: 下一個中介軟體或路由處理器

        Returns:
            HTTP 響應

        Raises:
            HTTPException: 如果請求過大（413 Payload Too Large）
        """
        # 檢查 Content-Length header
        content_length = request.headers.get("content-length")

        if content_length:
            try:
                content_length = int(content_length)

                if content_length > self.max_size:
                    # 記錄過大請求
                    logger.warning(
                        f"⚠️  拒絕過大請求：{content_length} bytes "
                        f"({content_length / (1024 * 1024):.2f} MB) "
                        f"from {request.client.host if request.client else 'unknown'} "
                        f"to {request.url.path}"
                    )

                    # 返回 413 Payload Too Large
                    raise HTTPException(
                        status_code=413,
                        detail={
                            "error": "Payload Too Large",
                            "message": f"請求 body 過大：{content_length} bytes",
                            "max_allowed": self.max_size,
                            "max_allowed_mb": round(self.max_size / (1024 * 1024), 1),
                            "received_mb": round(content_length / (1024 * 1024), 2),
                        }
                    )

            except ValueError:
                # Content-Length 不是有效的整數，記錄警告但繼續處理
                logger.warning(f"無效的 Content-Length header: {content_length}")

        # 處理請求
        response = await call_next(request)
        return response


class StrategyCodeSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    策略代碼大小限制中介軟體

    專門針對策略建立/更新端點，限制代碼大小為 100 KB
    """

    def __init__(self, app, max_code_size: int = None):
        """
        初始化中介軟體

        Args:
            app: FastAPI 應用實例
            max_code_size: 最大策略代碼大小（bytes）
        """
        super().__init__(app)
        self.max_code_size = max_code_size or settings.MAX_STRATEGY_CODE_SIZE
        self.strategy_paths = [
            "/api/v1/strategies/",
            "/api/v1/strategies/validate",
        ]

        logger.info(
            f"🔒 策略代碼大小限制：最大 {self.max_code_size / 1024:.0f} KB"
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        處理請求

        只針對策略相關端點進行額外檢查

        Args:
            request: HTTP 請求
            call_next: 下一個中介軟體或路由處理器

        Returns:
            HTTP 響應
        """
        # 只檢查策略相關端點
        path = request.url.path
        is_strategy_endpoint = any(
            path.startswith(strategy_path) for strategy_path in self.strategy_paths
        )

        if is_strategy_endpoint and request.method in ["POST", "PUT"]:
            content_length = request.headers.get("content-length")

            if content_length:
                try:
                    content_length = int(content_length)

                    if content_length > self.max_code_size:
                        logger.warning(
                            f"⚠️  拒絕過大策略代碼：{content_length} bytes "
                            f"from {request.client.host if request.client else 'unknown'}"
                        )

                        raise HTTPException(
                            status_code=413,
                            detail={
                                "error": "Strategy Code Too Large",
                                "message": f"策略代碼過大：{content_length} bytes",
                                "max_allowed": self.max_code_size,
                                "max_allowed_kb": round(self.max_code_size / 1024, 1),
                                "received_kb": round(content_length / 1024, 2),
                                "hint": "請縮短策略代碼或分割為多個策略"
                            }
                        )

                except ValueError:
                    pass

        # 處理請求
        response = await call_next(request)
        return response
