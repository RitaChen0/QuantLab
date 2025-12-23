from app.tasks.stock_data import (
    sync_stock_list,
    sync_daily_prices,
    sync_ohlcv_data,
    sync_latest_prices,
    sync_latest_prices_shioaji,
    cleanup_old_cache,
)
from app.tasks.backtest import (
    run_backtest_async,
    get_backtest_progress,
)
from app.tasks.fundamental_sync import (
    sync_fundamental_data,
    sync_fundamental_latest,
)
from app.tasks.rdagent_tasks import (
    run_factor_mining_task,
    run_strategy_optimization_task,
)
from app.tasks.factor_evaluation_tasks import (
    evaluate_factor_async,
    batch_evaluate_factors,
    update_factor_metrics,
)
from app.tasks.institutional_investor_sync import (
    sync_institutional_investors,
    sync_single_stock_institutional,
    sync_top_stocks_institutional,
    cleanup_old_institutional_data,
)
from app.tasks.shioaji_sync import (
    sync_shioaji_minute_data,
    sync_shioaji_top_stocks,
)
from app.tasks.option_sync import (
    sync_option_daily_factors,
    register_option_contracts,
    sync_option_minute_data,
    calculate_option_greeks,
)
from app.tasks.strategy_monitoring import (
    monitor_active_strategies,
    cleanup_old_signals,
)
from app.tasks.system_maintenance import (
    cleanup_celery_metadata,
)
from app.tasks.futures_continuous import (
    generate_continuous_contracts,
    register_new_futures_contracts,
)

__all__ = [
    "sync_stock_list",
    "sync_daily_prices",
    "sync_ohlcv_data",
    "sync_latest_prices",
    "sync_latest_prices_shioaji",
    "cleanup_old_cache",
    "run_backtest_async",
    "get_backtest_progress",
    "sync_fundamental_data",
    "sync_fundamental_latest",
    "run_factor_mining_task",
    "run_strategy_optimization_task",
    "evaluate_factor_async",
    "batch_evaluate_factors",
    "update_factor_metrics",
    "sync_institutional_investors",
    "sync_single_stock_institutional",
    "sync_top_stocks_institutional",
    "cleanup_old_institutional_data",
    "sync_shioaji_minute_data",
    "sync_shioaji_top_stocks",
    "sync_option_daily_factors",
    "register_option_contracts",
    "sync_option_minute_data",
    "calculate_option_greeks",
    "monitor_active_strategies",
    "cleanup_old_signals",
    "cleanup_celery_metadata",
    "generate_continuous_contracts",
    "register_new_futures_contracts",
]
