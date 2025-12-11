"""
Prometheus Metrics API Endpoint

Exposes metrics for Prometheus scraping.
"""

from fastapi import APIRouter, Response
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    REGISTRY,
)
from loguru import logger

router = APIRouter()

# Custom metrics for QuantLab
# These will be automatically exposed at /metrics

# API Request Counter
api_requests_total = Counter(
    'quantlab_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

# API Response Time
api_response_time_seconds = Histogram(
    'quantlab_api_response_time_seconds',
    'API response time in seconds',
    ['method', 'endpoint']
)

# Backtest Counter
backtests_total = Counter(
    'quantlab_backtests_total',
    'Total backtests created',
    ['status']
)

# Strategy Counter
strategies_total = Gauge(
    'quantlab_strategies_total',
    'Total strategies in database'
)

# Active Users
active_users = Gauge(
    'quantlab_active_users',
    'Number of active users'
)

# Database Connection Pool
db_connections = Gauge(
    'quantlab_db_connections',
    'Active database connections'
)


@router.get("/metrics", include_in_schema=False)
async def metrics():
    """
    Prometheus metrics endpoint

    Returns metrics in Prometheus text format.
    This endpoint is scraped by Prometheus server.
    """
    try:
        # Generate metrics in Prometheus format
        metrics_output = generate_latest(REGISTRY)

        return Response(
            content=metrics_output,
            media_type=CONTENT_TYPE_LATEST
        )
    except Exception as e:
        logger.error(f"Failed to generate metrics: {str(e)}")
        return Response(
            content=b"# Error generating metrics\n",
            media_type=CONTENT_TYPE_LATEST,
            status_code=500
        )


# Helper functions for updating metrics
def record_api_request(method: str, endpoint: str, status: int):
    """Record an API request"""
    api_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()


def record_api_response_time(method: str, endpoint: str, duration: float):
    """Record API response time"""
    api_response_time_seconds.labels(method=method, endpoint=endpoint).observe(duration)


def record_backtest(status: str):
    """Record a backtest creation"""
    backtests_total.labels(status=status).inc()


def update_strategy_count(count: int):
    """Update strategy count"""
    strategies_total.set(count)


def update_active_users(count: int):
    """Update active users count"""
    active_users.set(count)


def update_db_connections(count: int):
    """Update database connections count"""
    db_connections.set(count)
