from sqlalchemy.ext.declarative import declarative_base

# SQLAlchemy Base class for all models
Base = declarative_base()

# Import all models here so Alembic can detect them
# These imports must be after Base definition to avoid circular imports
def import_models():
    from app.models.user import User  # noqa: F401
    from app.models.stock import Stock  # noqa: F401
    from app.models.stock_price import StockPrice  # noqa: F401
    from app.models.stock_minute_price import StockMinutePrice  # noqa: F401
    from app.models.strategy import Strategy  # noqa: F401
    from app.models.backtest import Backtest  # noqa: F401
    from app.models.backtest_result import BacktestResult  # noqa: F401
    from app.models.trade import Trade  # noqa: F401
    from app.models.fundamental_data import FundamentalData  # noqa: F401
    from app.models.industry import Industry  # noqa: F401
    from app.models.stock_industry import StockIndustry  # noqa: F401
    from app.models.industry_metrics_cache import IndustryMetricsCache  # noqa: F401
    from app.models.industry_chain import IndustryChain, StockIndustryChain, CustomIndustryCategory, StockCustomCategory  # noqa: F401
    from app.models.rdagent import RDAgentTask, GeneratedFactor, FactorEvaluation  # noqa: F401
    from app.models.institutional_investor import InstitutionalInvestor  # noqa: F401
    from app.models.telegram_notification import TelegramNotification, TelegramNotificationPreference  # noqa: F401
    from app.models.option import OptionContract, OptionDailyFactor, OptionMinutePrice, OptionGreeks, OptionSyncConfig  # noqa: F401
    from app.models.strategy_signal import StrategySignal  # noqa: F401

# Note: import_models() is called in alembic/env.py for migrations
# Don't auto-import to avoid circular dependencies in application code
