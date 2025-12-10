"""Pydantic schemas for request/response validation"""

# User schemas
from app.schemas.user import (
    User,
    UserBase,
    UserCreate,
    UserUpdate,
    UserInDB,
    UserLogin,
    Token,
    TokenPayload,
)

# Stock schemas
from app.schemas.stock import (
    Stock,
    StockBase,
    StockCreate,
    StockUpdate,
    StockInDB,
    StockSearchRequest,
    StockSearchResult,
    StockListResponse,
)

# StockPrice schemas
from app.schemas.stock_price import (
    StockPrice,
    StockPriceBase,
    StockPriceCreate,
    StockPriceUpdate,
    StockPriceQuery,
    StockPriceListResponse,
    OHLCVData,
)

# Strategy schemas
from app.schemas.strategy import (
    Strategy,
    StrategyBase,
    StrategyCreate,
    StrategyUpdate,
    StrategyInDB,
    StrategyDetail,
    StrategyStatus,
    StrategyListResponse,
    StrategyCodeValidationRequest,
    StrategyCodeValidationResponse,
)

# Backtest schemas
from app.schemas.backtest import (
    Backtest,
    BacktestBase,
    BacktestCreate,
    BacktestUpdate,
    BacktestInDB,
    BacktestDetail,
    BacktestStatus,
    BacktestListResponse,
    BacktestRunRequest,
    BacktestProgress,
)

# BacktestResult schemas
from app.schemas.backtest_result import (
    BacktestResult,
    BacktestResultBase,
    BacktestResultCreate,
    BacktestResultUpdate,
    BacktestResultInDB,
    PerformanceMetrics,
    BacktestResultSummary,
)

# Trade schemas
from app.schemas.trade import (
    Trade,
    TradeBase,
    TradeCreate,
    TradeUpdate,
    TradeInDB,
    TradeAction,
    TradeListResponse,
    TradeQuery,
    TradeSummary,
    TradePerformance,
)

# Fundamental schemas
from app.schemas.fundamental import (
    FundamentalIndicatorRequest,
    FundamentalIndicatorBatchRequest,
    FundamentalDataPoint,
    FundamentalIndicatorResponse,
    FundamentalIndicatorBatchResponse,
    FundamentalIndicatorInfo,
    FundamentalIndicatorListResponse,
    FundamentalIndicatorCategoryResponse,
    FundamentalSummary,
    FundamentalComparisonRequest,
    FundamentalComparisonResponse,
)

__all__ = [
    # User
    "User",
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserInDB",
    "UserLogin",
    "Token",
    "TokenPayload",
    # Stock
    "Stock",
    "StockBase",
    "StockCreate",
    "StockUpdate",
    "StockInDB",
    "StockSearchRequest",
    "StockSearchResult",
    "StockListResponse",
    # StockPrice
    "StockPrice",
    "StockPriceBase",
    "StockPriceCreate",
    "StockPriceUpdate",
    "StockPriceQuery",
    "StockPriceListResponse",
    "OHLCVData",
    # Strategy
    "Strategy",
    "StrategyBase",
    "StrategyCreate",
    "StrategyUpdate",
    "StrategyInDB",
    "StrategyDetail",
    "StrategyStatus",
    "StrategyListResponse",
    "StrategyCodeValidationRequest",
    "StrategyCodeValidationResponse",
    # Backtest
    "Backtest",
    "BacktestBase",
    "BacktestCreate",
    "BacktestUpdate",
    "BacktestInDB",
    "BacktestDetail",
    "BacktestStatus",
    "BacktestListResponse",
    "BacktestRunRequest",
    "BacktestProgress",
    # BacktestResult
    "BacktestResult",
    "BacktestResultBase",
    "BacktestResultCreate",
    "BacktestResultUpdate",
    "BacktestResultInDB",
    "PerformanceMetrics",
    "BacktestResultSummary",
    # Trade
    "Trade",
    "TradeBase",
    "TradeCreate",
    "TradeUpdate",
    "TradeInDB",
    "TradeAction",
    "TradeListResponse",
    "TradeQuery",
    "TradeSummary",
    "TradePerformance",
    # Fundamental
    "FundamentalIndicatorRequest",
    "FundamentalIndicatorBatchRequest",
    "FundamentalDataPoint",
    "FundamentalIndicatorResponse",
    "FundamentalIndicatorBatchResponse",
    "FundamentalIndicatorInfo",
    "FundamentalIndicatorListResponse",
    "FundamentalIndicatorCategoryResponse",
    "FundamentalSummary",
    "FundamentalComparisonRequest",
    "FundamentalComparisonResponse",
]
