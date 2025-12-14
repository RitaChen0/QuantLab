from celery import Celery
from app.core.config import settings

# Create Celery application
celery_app = Celery(
    "quantlab",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"],
)

# Optional configuration, see the application user guide.
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Taipei",
    enable_utc=False,  # 使用本地時區，讓 crontab 使用 Asia/Taipei 時間
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,

    # Task routing - 專用隊列配置
    task_routes={
        'app.tasks.run_backtest_async': {'queue': 'backtest'},
        'app.tasks.sync_*': {'queue': 'data_sync'},
        'app.tasks.cleanup_*': {'queue': 'maintenance'},
    },

    # 並發控制 - 限制同時執行的回測任務數量
    task_annotations={
        'app.tasks.run_backtest_async': {
            'rate_limit': '300/h',  # 每小時最多 300 個任務（平均每分鐘 5 個）
            'time_limit': 600,      # 10 分鐘硬限制
            'soft_time_limit': 540,  # 9 分鐘軟限制
        },
        'app.tasks.sync_shioaji_top_stocks': {
            'time_limit': 14400,      # 4 小時硬限制（同步所有股票）
            'soft_time_limit': 14100,  # 3 小時 55 分鐘軟限制
        }
    },

    # Worker 配置
    # Note: worker_concurrency is set via command-line --concurrency flag in docker-compose.yml
    worker_pool='prefork',  # 使用 prefork pool
)

# Celery Beat schedule (periodic tasks)
from celery.schedules import crontab

# Ensure all SQLAlchemy models are imported before Celery worker starts
# This is critical for relationship() to work correctly in Celery tasks
from app.db.session import ensure_models_imported
ensure_models_imported()

celery_app.conf.beat_schedule = {
    # Sync stock list once per day at 8:00 AM
    "sync-stock-list-daily": {
        "task": "app.tasks.sync_stock_list",
        "schedule": crontab(hour=8, minute=0),
        "options": {"expires": 3600},  # Expire after 1 hour if not executed
    },

    # Sync daily prices once per day at 9:00 PM (after market close)
    "sync-daily-prices": {
        "task": "app.tasks.sync_daily_prices",
        "schedule": crontab(hour=21, minute=0),
        "options": {"expires": 7200},  # Expire after 2 hours
    },

    # Sync OHLCV data once per day at 10:00 PM
    "sync-ohlcv-daily": {
        "task": "app.tasks.sync_ohlcv_data",
        "schedule": crontab(hour=22, minute=0),
        "options": {"expires": 7200},
    },

    # Sync latest prices every 15 minutes during trading hours (9:00-13:30)
    "sync-latest-prices-frequent": {
        "task": "app.tasks.sync_latest_prices",
        "schedule": crontab(
            minute='*/15',
            hour='9-13',
            day_of_week='mon,tue,wed,thu,fri'
        ),
        "options": {"expires": 600},  # Expire after 10 minutes
    },

    # Clean up old cache entries once per day at 3:00 AM
    "cleanup-cache-daily": {
        "task": "app.tasks.cleanup_old_cache",
        "schedule": crontab(hour=3, minute=0),
    },

    # Sync fundamental data (full sync) once per week on Sunday at 4:00 AM
    "sync-fundamental-weekly": {
        "task": "app.tasks.sync_fundamental_data",
        "schedule": crontab(hour=4, minute=0, day_of_week='sunday'),
        "options": {"expires": 21600},  # Expire after 6 hours
    },

    # Sync latest fundamental data (quick sync) once per day at 23:00
    "sync-fundamental-latest-daily": {
        "task": "app.tasks.sync_fundamental_latest",
        "schedule": crontab(hour=23, minute=0),
        "options": {"expires": 7200},  # Expire after 2 hours
    },

    # Sync institutional investors data (top 100 stocks) once per day at 21:00
    "sync-institutional-investors-daily": {
        "task": "app.tasks.sync_top_stocks_institutional",
        "schedule": crontab(hour=21, minute=0),
        "kwargs": {"limit": 100, "days": 7},
        "options": {"expires": 7200},  # Expire after 2 hours
    },

    # Cleanup old institutional data once per week on Sunday at 2:00 AM
    "cleanup-institutional-data-weekly": {
        "task": "app.tasks.cleanup_old_institutional_data",
        "schedule": crontab(hour=2, minute=0, day_of_week='sunday'),
        "kwargs": {"days_to_keep": 365},
        "options": {"expires": 3600},  # Expire after 1 hour
    },

    # Sync Shioaji minute data (all stocks) once per day at 15:00 (3 PM)
    # Runs after market close (13:30) to sync latest minute bars for all stocks
    # Execution time: ~2-4 hours (depends on number of stocks and missing data)
    "sync-shioaji-minute-daily": {
        "task": "app.tasks.sync_shioaji_top_stocks",
        "schedule": crontab(hour=15, minute=0, day_of_week='mon,tue,wed,thu,fri'),
        "options": {"expires": 18000},  # Expire after 5 hours (task may take up to 4 hours)
    },
}

if __name__ == "__main__":
    celery_app.start()
