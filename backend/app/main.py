"""
QuantLab FastAPI Application
Main entry point for the backend API
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.rate_limit import limiter, get_rate_limit_error_handler
from app.middleware.request_size_limit import RequestSizeLimitMiddleware, StrategyCodeSizeLimitMiddleware
from app.middleware.monitoring import MonitoringMiddleware
from app.api.v1 import auth, users, strategies, backtest, data, trading, ai, industry, industry_chain, admin, rdagent, factor_evaluation, intraday, metrics, membership

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="開源台股量化交易平台 API",
    docs_url="/docs",
    redoc_url=None,  # Disable default Redoc to use custom one
    openapi_url=f"{settings.API_PREFIX}/openapi.json"
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, get_rate_limit_error_handler())

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request size limit middleware (防止 DoS 攻擊)
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_size=settings.MAX_REQUEST_SIZE
)

# Add strategy code size limit middleware
app.add_middleware(
    StrategyCodeSizeLimitMiddleware,
    max_code_size=settings.MAX_STRATEGY_CODE_SIZE
)

# Add monitoring middleware (監控安全事件)
app.add_middleware(MonitoringMiddleware)

# Include routers
app.include_router(
    auth.router,
    prefix=f"{settings.API_PREFIX}/auth",
    tags=["認證"]
)

app.include_router(
    users.router,
    prefix=f"{settings.API_PREFIX}/users",
    tags=["使用者"]
)

app.include_router(
    strategies.router,
    prefix=f"{settings.API_PREFIX}/strategies",
    tags=["策略"]
)

app.include_router(
    backtest.router,
    prefix=f"{settings.API_PREFIX}/backtest",
    tags=["回測"]
)

app.include_router(
    data.router,
    prefix=f"{settings.API_PREFIX}/data",
    tags=["資料"]
)

app.include_router(
    intraday.router,
    prefix=settings.API_PREFIX,
    tags=["分鐘級資料"]
)

app.include_router(
    trading.router,
    prefix=f"{settings.API_PREFIX}/trading",
    tags=["交易"]
)

app.include_router(
    ai.router,
    prefix=f"{settings.API_PREFIX}/ai",
    tags=["AI"]
)

app.include_router(
    industry.router,
    prefix=settings.API_PREFIX,
    tags=["產業分析"]
)

app.include_router(
    industry_chain.router,
    prefix=settings.API_PREFIX,
    tags=["產業鏈"]
)

app.include_router(
    admin.router,
    prefix=f"{settings.API_PREFIX}/admin",
    tags=["後台管理"]
)

app.include_router(
    rdagent.router,
    prefix=settings.API_PREFIX,
    tags=["RD-Agent"]
)

app.include_router(
    factor_evaluation.router,
    prefix=f"{settings.API_PREFIX}/factor-evaluation",
    tags=["因子評估"]
)

app.include_router(
    membership.router,
    prefix=settings.API_PREFIX,
    tags=["會員管理"]
)

# Include metrics router (no prefix, accessed at root /metrics)
app.include_router(
    metrics.router,
    tags=["Monitoring"]
)


@app.get("/")
async def root():
    """根路徑"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康檢查"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION
    }


@app.get("/redoc", response_class=HTMLResponse, include_in_schema=False)
async def redoc_html():
    """自定義 Redoc 頁面 - 使用本地資源"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>QuantLab - ReDoc</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
        <style>
            body {
                margin: 0;
                padding: 0;
            }
        </style>
    </head>
    <body>
        <div id="redoc-container"></div>
        <script src="/static/redoc.standalone.js"></script>
        <script>
            Redoc.init('/api/v1/openapi.json', {
                scrollYOffset: 50
            }, document.getElementById('redoc-container'));
        </script>
    </body>
    </html>
    """


@app.on_event("startup")
async def startup_event():
    """應用啟動事件"""
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 啟動中...")
    print(f"📝 環境: {settings.ENVIRONMENT}")
    print(f"📚 API 文檔: http://localhost:8000/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """應用關閉事件"""
    print(f"👋 {settings.APP_NAME} 正在關閉...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
