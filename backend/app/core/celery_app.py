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
    timezone="UTC",  # 統一使用 UTC 時區
    enable_utc=True,  # 啟用 UTC 模式
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,

    # 結果過期設置 - 自動清理舊結果
    result_expires=3600,  # 結果 1 小時後過期

    # Task acknowledgment settings
    task_acks_late=True,  # 任務執行完成後才確認（確保任務不會丟失）
    task_reject_on_worker_lost=False,  # Worker 丟失時重新排隊任務

    # ⚠️ 關鍵配置：防止過期任務擋住未來任務
    # 當任務過期時，靜默丟棄而不是標記為 revoked
    task_ignore_result=False,  # 保留結果（用於監控）
    task_store_errors_even_if_ignored=True,  # 即使 ignore_result=True 也存儲錯誤

    # Worker 行為：自動清理過期任務
    worker_disable_rate_limits=False,  # 保持速率限制
    worker_send_task_events=True,  # 發送任務事件（用於監控）

    # Task routing - 專用隊列配置
    task_routes={
        'app.tasks.run_backtest_async': {'queue': 'backtest'},
        'app.tasks.sync_*': {'queue': 'data_sync'},
        'app.tasks.cleanup_*': {'queue': 'maintenance'},
        # 因子評估專用隊列（並發控制）
        'app.tasks.evaluate_factor_async': {'queue': 'evaluation'},
        'app.tasks.batch_evaluate_factors': {'queue': 'evaluation'},
        'app.tasks.update_factor_metrics': {'queue': 'evaluation'},
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
        },
        'app.tasks.sync_shioaji_futures': {
            'time_limit': 1800,      # 30 分鐘硬限制（同步期货）
            'soft_time_limit': 1740,  # 29 分鐘軟限制
        },
        'app.tasks.register_option_contracts': {
            'time_limit': 7200,      # 2 小時硬限制（處理 952 個選擇權合約）
            'soft_time_limit': 6900,  # 1 小時 55 分鐘軟限制
        },
        'app.tasks.sync_option_daily_factors': {
            'time_limit': 3600,      # 1 小時硬限制（計算 Greeks）
            'soft_time_limit': 3300,  # 55 分鐘軟限制
        },
        # RD-Agent 任務超時配置（基於歷史數據分析）
        # FACTOR_MINING: 平均 12 分鐘，P95 33 分鐘，最大 39 分鐘
        'app.tasks.run_factor_mining_task': {
            'time_limit': 3600,      # 1 小時硬限制
            'soft_time_limit': 3300,  # 55 分鐘軟限制
        },
        # MODEL_GENERATION: 平均 0.4 分鐘，P95 0.5 分鐘，最大 0.6 分鐘
        'app.tasks.run_model_generation_task': {
            'time_limit': 1800,      # 30 分鐘硬限制
            'soft_time_limit': 1680,  # 28 分鐘軟限制
        },
        # STRATEGY_OPTIMIZATION: 預估與 MODEL_GENERATION 類似
        'app.tasks.run_strategy_optimization_task': {
            'time_limit': 1800,      # 30 分鐘硬限制
            'soft_time_limit': 1680,  # 28 分鐘軟限制
        },
        # 因子評估任務：計算密集，需要較長時間
        'app.tasks.evaluate_factor_async': {
            'time_limit': 3600,      # 1 小時硬限制
            'soft_time_limit': 3300,  # 55 分鐘軟限制
        },
        'app.tasks.batch_evaluate_factors': {
            'time_limit': 7200,      # 2 小時硬限制（批次評估）
            'soft_time_limit': 6900,  # 1 小時 55 分鐘軟限制
        },
        'app.tasks.update_factor_metrics': {
            'time_limit': 60,        # 1 分鐘硬限制（簡單更新）
            'soft_time_limit': 50,   # 50 秒軟限制
        }
    },

    # Worker 配置
    # Note: worker_concurrency is set via command-line --concurrency flag in docker-compose.yml
    worker_pool='prefork',  # 使用 prefork pool

    # Worker 自動重啟設置 - 防止內存洩漏和 revoked 列表積累
    worker_max_memory_per_child=512000,  # Worker 使用 512MB 後自動重啟（清空 revoked 列表）
    worker_max_tasks_per_child=500,  # Worker 執行 500 個任務後自動重啟（清空 revoked 列表）
    # 平均每天處理 ~100-200 個任務，500 個任務約 2-5 天重啟一次

    # ⚠️ 智慧處理過期任務：配合每天 05:00 的 cleanup_celery_metadata 任務
    # 該任務會主動重啟 Worker 進程池，確保過期任務不會擋住未來任務
)

# Celery Beat schedule (periodic tasks)
from celery.schedules import crontab

# Ensure all SQLAlchemy models are imported before Celery worker starts
# This is critical for relationship() to work correctly in Celery tasks
from app.db.session import ensure_models_imported
ensure_models_imported()

celery_app.conf.beat_schedule = {
    # ==================== 系統說明 ====================
    # All times are in UTC (Universal Coordinated Time)
    # Taiwan time = UTC + 8 hours
    # Example: Taiwan 09:00 = UTC 01:00
    # ================================================

    # ==================== 數據同步任務 ====================

    # Sync stock list once per day
    # Runs at: Taiwan 08:00 (UTC 00:00)
    # Duration: ~1-2 minutes
    # Note: expires 23 小時，確保 Beat 重啟補發的任務仍能執行
    "sync-stock-list-daily": {
        "task": "app.tasks.sync_stock_list",
        "schedule": crontab(hour=0, minute=0),  # UTC 00:00 = Taiwan 08:00
        "options": {"expires": 82800},  # 23 hours
    },

    # Sync daily prices once per day
    # Runs at: Taiwan 21:00 (UTC 13:00)
    # Duration: ~5-10 minutes
    "sync-daily-prices": {
        "task": "app.tasks.sync_daily_prices",
        "schedule": crontab(hour=13, minute=0),  # UTC 13:00 = Taiwan 21:00
        "options": {"expires": 82800},  # 23 hours
    },

    # Sync OHLCV data once per day
    # Runs at: Taiwan 22:00 (UTC 14:00)
    # Duration: ~5-10 minutes
    "sync-ohlcv-daily": {
        "task": "app.tasks.sync_ohlcv_data",
        "schedule": crontab(hour=14, minute=0),  # UTC 14:00 = Taiwan 22:00
        "options": {"expires": 82800},  # 23 hours
    },

    # Sync latest prices during trading hours (every 15 minutes)
    # Runs at: Taiwan 09:00-13:59 (UTC 01:00-05:59), Mon-Fri
    # Duration: ~1-2 minutes
    # Data Source: Shioaji API (no quota limit)
    "sync-latest-prices-frequent": {
        "task": "app.tasks.sync_latest_prices_shioaji",
        "schedule": crontab(
            minute='*/15',
            hour='1-5',  # UTC 01:00-05:59 = Taiwan 09:00-13:59
            day_of_week='mon,tue,wed,thu,fri'
        ),
        # Note: 高頻任務不設置 expires（避免立即過期）
    },

    # ==================== 系統維護任務 ====================

    # Cleanup old cache entries once per day
    # Runs at: Taiwan 03:00 (UTC 19:00 previous day)
    # Duration: ~30 seconds
    "cleanup-cache-daily": {
        "task": "app.tasks.cleanup_old_cache",
        "schedule": crontab(hour=19, minute=0),  # UTC 19:00 = Taiwan 03:00 next day
    },

    # Cleanup Celery results and revoked tasks once per day
    # Runs at: Taiwan 05:00 (UTC 21:00 previous day)
    # Duration: ~5-10 seconds
    # Purpose: Prevents revoked task list from growing indefinitely
    "cleanup-celery-metadata-daily": {
        "task": "app.tasks.cleanup_celery_metadata",
        "schedule": crontab(hour=21, minute=0),  # UTC 21:00 = Taiwan 05:00 next day
        "options": {"expires": 82800},  # 23 hours
    },

    # Cleanup stuck RD-Agent tasks once per day
    # Runs at: Taiwan 05:30 (UTC 21:30 previous day)
    # Duration: ~1-2 seconds
    # Purpose: Clear RUNNING tasks that exceed 24 hours timeout
    "cleanup-stuck-rdagent-tasks-daily": {
        "task": "app.tasks.cleanup_stuck_rdagent_tasks",
        "schedule": crontab(hour=21, minute=30),  # UTC 21:30 = Taiwan 05:30 next day
        "kwargs": {"timeout_hours": 24},
        "options": {"expires": 82800},  # 23 hours
    },

    # Monitor RD-Agent tasks and send alerts
    # Runs at: Every 30 minutes
    # Duration: ~2-5 seconds
    # Purpose: Detect long-running tasks, failures, and high failure rates
    "monitor-rdagent-tasks": {
        "task": "app.tasks.monitor_rdagent_tasks",
        "schedule": crontab(minute="*/30"),  # Every 30 minutes
        # 無 expires - 高頻監控任務不應過期
    },

    # Check database integrity once per day
    # Runs at: Taiwan 06:00 (UTC 22:00 previous day)
    # Duration: ~2-5 minutes
    # Purpose: Ensure database completeness and consistency
    "check-database-integrity-daily": {
        "task": "app.tasks.check_database_integrity",
        "schedule": crontab(hour=22, minute=0),  # UTC 22:00 = Taiwan 06:00 next day
        "options": {"expires": 82800},  # 23 hours
    },

    # Auto-fix database missing data once per day
    # Runs at: Taiwan 06:30 (UTC 22:30 previous day)
    # Duration: ~5-30 minutes
    # Purpose: Automatically backfill missing daily/minute data
    "auto-fix-database-daily": {
        "task": "app.tasks.auto_fix_database",
        "schedule": crontab(hour=22, minute=30),  # UTC 22:30 = Taiwan 06:30 next day
        "options": {"expires": 82800},  # 23 hours
    },

    # ==================== 基本面數據同步 ====================

    # Sync fundamental data (full sync) once per week
    # Runs at: Taiwan Sunday 04:00 (UTC Saturday 20:00)
    # Duration: ~30-60 minutes
    "sync-fundamental-weekly": {
        "task": "app.tasks.sync_fundamental_data",
        "schedule": crontab(hour=20, minute=0, day_of_week='saturday'),  # UTC Saturday 20:00 = Taiwan Sunday 04:00
        "options": {"expires": 604800},  # 7 days (weekly task)
    },

    # Sync latest fundamental data (incremental) once per day
    # Runs at: Taiwan 23:00 (UTC 15:00)
    # Duration: ~5-10 minutes
    "sync-fundamental-latest-daily": {
        "task": "app.tasks.sync_fundamental_latest",
        "schedule": crontab(hour=15, minute=0),  # UTC 15:00 = Taiwan 23:00
        "options": {"expires": 82800},  # 23 hours
    },

    # ==================== 法人買賣數據同步 ====================

    # Sync institutional investors data (all active stocks) once per day
    # Runs at: Taiwan 21:00 (UTC 13:00)
    # Duration: ~10-15 minutes
    "sync-institutional-investors-daily": {
        "task": "app.tasks.sync_top_stocks_institutional",
        "schedule": crontab(hour=13, minute=0),  # UTC 13:00 = Taiwan 21:00
        "kwargs": {"limit": None, "days": 7},  # None = 同步全部股票
        "options": {"expires": 82800},  # 23 hours
    },

    # Cleanup old institutional data once per week
    # Runs at: Taiwan Sunday 02:00 (UTC Saturday 18:00)
    # Duration: ~10-30 seconds
    "cleanup-institutional-data-weekly": {
        "task": "app.tasks.cleanup_old_institutional_data",
        "schedule": crontab(hour=18, minute=0, day_of_week='saturday'),  # UTC Saturday 18:00 = Taiwan Sunday 02:00
        "kwargs": {"days_to_keep": 365},
        "options": {"expires": 604800},  # 7 days (weekly task)
    },

    # ==================== Shioaji 分鐘線同步 ====================

    # Sync Shioaji minute data (all stocks) once per day
    # Runs at: Taiwan 15:00 (UTC 07:00), Mon-Fri (after market close)
    # Duration: ~2-4 hours
    # Note: 無 expires 限制 - 任務有 4 層防護（Redis 鎖、去重裝飾器、Worker 重啟、每日清理）
    "sync-shioaji-minute-daily": {
        "task": "app.tasks.sync_shioaji_top_stocks",
        "schedule": crontab(hour=7, minute=0, day_of_week='mon,tue,wed,thu,fri'),  # UTC 07:00 = Taiwan 15:00
        # 無 expires - 已有 4 層防護：
        # 1. Redis 鎖 (14400s = 4h)
        # 2. @skip_if_recently_executed(24h)
        # 3. worker_max_tasks_per_child=500
        # 4. cleanup_celery_metadata 每天 05:00
    },

    # ==================== 期貨數據同步 ====================

    # Sync futures minute data (TX + MTX) once per day
    # Runs at: Taiwan 15:30 (UTC 07:30), Mon-Fri (after market close)
    # Duration: ~5-10 minutes
    # Note: 無 expires 限制，確保 Beat 重啟後補發的任務仍能執行
    "sync-shioaji-futures-daily": {
        "task": "app.tasks.sync_shioaji_futures",
        "schedule": crontab(hour=7, minute=30, day_of_week='mon,tue,wed,thu,fri'),  # UTC 07:30 = Taiwan 15:30
    },

    # Generate TX futures daily data from minute data for RD-Agent
    # Runs at: Taiwan 16:00 (UTC 08:00), Mon-Fri
    # Duration: ~1-2 minutes
    # Purpose: Aggregate minute bars into daily OHLCV for RD-Agent factor mining
    # Note: Runs 30 mins after sync-shioaji-futures-daily to ensure latest minute data
    "generate-tx-daily-from-minute": {
        "task": "app.tasks.generate_tx_daily_from_minute",
        "schedule": crontab(hour=8, minute=0, day_of_week='mon,tue,wed,thu,fri'),  # UTC 08:00 = Taiwan 16:00
        "options": {
            "expires": 82800,  # 23 hours
            "kwargs": {"contract": "TXCONT"}  # 使用 TXCONT 連續合約（永不過期，自動換約）
        },
    },

    # Generate continuous futures contracts (TX + MTX) once per week
    # Runs at: Taiwan Saturday 18:00 (UTC Saturday 10:00)
    # Duration: ~1-2 minutes
    # Purpose: Stitch monthly contracts into continuous contracts (TXCONT, MTXCONT)
    "generate-continuous-contracts-weekly": {
        "task": "app.tasks.generate_continuous_contracts",
        "schedule": crontab(hour=10, minute=0, day_of_week='saturday'),  # UTC Saturday 10:00 = Taiwan Saturday 18:00
        "kwargs": {"symbols": ["TX", "MTX"], "days_back": 90},
        "options": {"expires": 604800},  # 7 days (weekly task)
    },

    # Register new futures contracts once per year
    # Runs at: Taiwan Jan 1 00:05 (UTC Dec 31 16:05)
    # Duration: ~30 seconds
    # Purpose: Auto-register monthly contracts for the new year
    "register-new-futures-contracts-yearly": {
        "task": "app.tasks.register_new_futures_contracts",
        "schedule": crontab(hour=16, minute=5, day_of_month='31', month_of_year='12'),  # UTC Dec 31 16:05 = Taiwan Jan 1 00:05
        "options": {"expires": 86400},  # 24 hours (yearly task)
    },

    # ==================== 選擇權相關任務 ====================

    # Sync option daily factors (PCR, ATM IV, Greeks) once per day
    # Runs at: Taiwan 15:40 (UTC 07:40), Mon-Fri (after futures sync)
    # Duration: ~2-5 minutes
    "sync-option-daily-factors": {
        "task": "app.tasks.sync_option_daily_factors",
        "schedule": crontab(hour=7, minute=40, day_of_week='mon,tue,wed,thu,fri'),  # UTC 07:40 = Taiwan 15:40
        "options": {"expires": 82800},  # 23 hours
    },

    # Register option contracts once per week
    # Runs at: Taiwan Sunday 19:00 (UTC Sunday 11:00)
    # Duration: ~1-2 minutes
    # Purpose: Update option contract list in database
    "register-option-contracts-weekly": {
        "task": "app.tasks.register_option_contracts",
        "schedule": crontab(hour=11, minute=0, day_of_week='sunday'),  # UTC Sunday 11:00 = Taiwan Sunday 19:00
        "options": {"expires": 604800},  # 7 days (weekly task)
    },

    # ==================== 策略實盤監控任務 ====================

    # Monitor active strategies during stock trading hours (every ~15 minutes)
    # Runs at: Taiwan 09:01-13:46 (UTC 01:01-05:46), Mon-Fri
    # Duration: ~1-3 minutes
    # Note: 錯開 1 分鐘避免與 sync-latest-prices 衝突
    "monitor-strategies-trading-hours": {
        "task": "app.tasks.monitor_active_strategies",
        "schedule": crontab(
            minute='1,16,31,46',  # UTC 01:01, 01:16, 01:31, 01:46... = Taiwan 09:01, 09:16, 09:31, 09:46...
            hour='1-5',  # UTC 01:00-05:59 = Taiwan 09:00-13:59
            day_of_week='mon,tue,wed,thu,fri'
        ),
        # Note: 高頻任務不設置 expires（避免立即過期）
    },

    # Monitor active strategies during futures evening session (every 15 minutes)
    # Runs at: Taiwan 15:00-23:59 (UTC 07:00-15:59), Mon-Fri
    # Duration: ~1-3 minutes
    "monitor-strategies-futures-session-1": {
        "task": "app.tasks.monitor_active_strategies",
        "schedule": crontab(
            minute='*/15',
            hour='7-15',  # UTC 07:00-15:59 = Taiwan 15:00-23:59
            day_of_week='mon,tue,wed,thu,fri'
        ),
        # Note: 高頻任務不設置 expires（避免立即過期）
    },

    # Monitor active strategies during futures late night session (every 15 minutes)
    # Runs at: Taiwan 00:00-05:00 (UTC 16:00-21:00 previous day), Mon-Fri UTC
    # Duration: ~1-3 minutes
    "monitor-strategies-futures-session-2": {
        "task": "app.tasks.monitor_active_strategies",
        "schedule": crontab(
            minute='*/15',
            hour='16-21',  # UTC 16:00-21:00 = Taiwan 00:00-05:00 next day
            day_of_week='mon,tue,wed,thu,fri'  # Mon-Fri UTC = Tue-Sat Taiwan morning
        ),
        # Note: 高頻任務不設置 expires（避免立即過期）
    },

    # Cleanup old signal records once per week
    # Runs at: Taiwan Sunday 04:00 (UTC Saturday 20:00)
    # Duration: ~10-30 seconds
    # Purpose: Keep signals for 30 days only
    "cleanup-old-signals-weekly": {
        "task": "app.tasks.cleanup_old_signals",
        "schedule": crontab(hour=20, minute=0, day_of_week='saturday'),  # UTC Saturday 20:00 = Taiwan Sunday 04:00
        "kwargs": {"days_to_keep": 30},
        "options": {"expires": 604800},  # 7 days (weekly task)
    },

    # ==================== 舊任務清理（數據庫維護） ====================

    # Cleanup all old task records once per week
    # Runs at: Taiwan Sunday 03:00 (UTC Saturday 19:00)
    # Duration: ~30-60 seconds
    # Purpose: Clean up old backtests, RD-Agent tasks, and training jobs (keep 90 days)
    "cleanup-all-old-tasks-weekly": {
        "task": "app.tasks.cleanup_all_old_tasks",
        "schedule": crontab(hour=19, minute=0, day_of_week='saturday'),  # UTC Saturday 19:00 = Taiwan Sunday 03:00
        "kwargs": {"days_to_keep": 90},
        "options": {"expires": 604800},  # 7 days (weekly task)
    },
}

if __name__ == "__main__":
    celery_app.start()
