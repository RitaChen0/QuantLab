"""
FinLab API Client Service
Provides methods to fetch stock data from FinLab API
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger
from app.core.config import settings

try:
    import finlab
    from finlab import data
    FINLAB_AVAILABLE = True
except ImportError:
    FINLAB_AVAILABLE = False
    logger.warning("FinLab package not installed. FinLab features will be disabled.")


class FinLabClient:
    """Client for interacting with FinLab API"""

    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize FinLab client

        Args:
            api_token: FinLab API token (if None, uses token from settings)
        """
        self.api_token = api_token or settings.FINLAB_API_TOKEN
        self._initialized = False

        if not FINLAB_AVAILABLE:
            logger.error("FinLab package not available")
            return

        if not self.api_token:
            logger.warning("FinLab API token not configured")
            return

        self._initialize()

    def _initialize(self) -> None:
        """Initialize FinLab connection"""
        try:
            finlab.login(self.api_token)
            self._initialized = True
            logger.info("FinLab client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize FinLab client: {str(e)}")
            self._initialized = False

    def is_available(self) -> bool:
        """Check if FinLab client is available and initialized"""
        return FINLAB_AVAILABLE and self._initialized

    def get_stock_list(self) -> pd.DataFrame:
        """
        Get list of all Taiwan stocks

        Returns:
            DataFrame with stock information (stock_id, name, industry, market)
        """
        if not self.is_available():
            raise RuntimeError("FinLab client not available")

        try:
            # Get stock list from price data columns
            # FinLab doesn't have a direct "stock_list" API,
            # so we extract stock IDs from the price data
            close = data.get("price:收盤價")
            stock_ids = close.columns.tolist()

            # Create a DataFrame with stock information
            stocks_df = pd.DataFrame({
                'stock_id': stock_ids,
                'stock_name': stock_ids,  # Will be the same as ID for now
                'industry_category': '',
                'market': '',
            })
            stocks_df.set_index('stock_id', inplace=True)

            logger.info(f"Retrieved {len(stocks_df)} stocks from FinLab")
            return stocks_df
        except Exception as e:
            logger.error(f"Failed to get stock list: {str(e)}")
            raise

    def get_price(
        self,
        stock_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Get stock price data

        Args:
            stock_id: Stock ID (e.g., "2330"). If None, returns all stocks.
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            DataFrame with OHLCV data
        """
        if not self.is_available():
            raise RuntimeError("FinLab client not available")

        try:
            # Get closing price
            close = data.get("price:收盤價")

            # Filter by date range
            if start_date:
                close = close[close.index >= start_date]
            if end_date:
                close = close[close.index <= end_date]

            # Filter by stock_id
            if stock_id:
                if stock_id not in close.columns:
                    raise ValueError(f"Stock {stock_id} not found")
                close = close[[stock_id]]

            logger.info(f"Retrieved price data: {close.shape}")
            return close

        except Exception as e:
            logger.error(f"Failed to get price data: {str(e)}")
            raise

    def get_ohlcv(
        self,
        stock_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Get OHLCV (Open, High, Low, Close, Volume) data for a stock

        Args:
            stock_id: Stock ID (e.g., "2330")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            DataFrame with OHLCV data
        """
        if not self.is_available():
            raise RuntimeError("FinLab client not available")

        try:
            # Get OHLCV data
            open_price = data.get("price:開盤價")
            high = data.get("price:最高價")
            low = data.get("price:最低價")
            close = data.get("price:收盤價")
            volume = data.get("price:成交股數")

            # Combine into single DataFrame
            ohlcv = pd.DataFrame({
                'open': open_price[stock_id],
                'high': high[stock_id],
                'low': low[stock_id],
                'close': close[stock_id],
                'volume': volume[stock_id],
            })

            # Filter by date range
            if start_date:
                ohlcv = ohlcv[ohlcv.index >= start_date]
            if end_date:
                ohlcv = ohlcv[ohlcv.index <= end_date]

            logger.info(f"Retrieved OHLCV data for {stock_id}: {ohlcv.shape}")
            return ohlcv

        except Exception as e:
            logger.error(f"Failed to get OHLCV data: {str(e)}")
            raise

    def get_financial_statement(
        self,
        stock_id: str,
        statement_type: str = "balance_sheet",
    ) -> pd.DataFrame:
        """
        Get financial statement data

        Args:
            stock_id: Stock ID (e.g., "2330")
            statement_type: Type of statement
                - "balance_sheet": 資產負債表
                - "income_statement": 損益表
                - "cash_flow": 現金流量表

        Returns:
            DataFrame with financial data
        """
        if not self.is_available():
            raise RuntimeError("FinLab client not available")

        try:
            # Map statement type to FinLab data key
            statement_map = {
                "balance_sheet": "fundamental_features:資產總額",
                "income_statement": "fundamental_features:營業收入",
                "cash_flow": "fundamental_features:營業活動之淨現金流入",
            }

            if statement_type not in statement_map:
                raise ValueError(f"Invalid statement type: {statement_type}")

            # Get data
            financial_data = data.get(statement_map[statement_type])

            if stock_id not in financial_data.columns:
                raise ValueError(f"Stock {stock_id} not found")

            result = financial_data[[stock_id]]
            logger.info(f"Retrieved {statement_type} for {stock_id}: {result.shape}")
            return result

        except Exception as e:
            logger.error(f"Failed to get financial statement: {str(e)}")
            raise

    def get_technical_indicator(
        self,
        indicator: str,
        stock_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Get technical indicator data

        Args:
            indicator: Technical indicator name (e.g., "RSI", "MACD", "KD")
            stock_id: Stock ID (e.g., "2330"). If None, returns all stocks.
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            DataFrame with indicator values
        """
        if not self.is_available():
            raise RuntimeError("FinLab client not available")

        try:
            # Get indicator data from FinLab
            data_key = f"price:{indicator}"
            indicator_data = data.get(data_key)

            # Filter by date range
            if start_date:
                indicator_data = indicator_data[indicator_data.index >= start_date]
            if end_date:
                indicator_data = indicator_data[indicator_data.index <= end_date]

            # Filter by stock_id
            if stock_id:
                if stock_id not in indicator_data.columns:
                    raise ValueError(f"Stock {stock_id} not found")
                indicator_data = indicator_data[[stock_id]]

            logger.info(f"Retrieved {indicator} data: {indicator_data.shape}")
            return indicator_data

        except Exception as e:
            logger.error(f"Failed to get technical indicator: {str(e)}")
            raise

    def get_latest_price(self, stock_id: str) -> Optional[float]:
        """
        Get latest closing price for a stock

        Args:
            stock_id: Stock ID (e.g., "2330")

        Returns:
            Latest closing price or None if not available
        """
        if not self.is_available():
            raise RuntimeError("FinLab client not available")

        try:
            close = data.get("price:收盤價")
            if stock_id not in close.columns:
                return None

            latest_price = close[stock_id].dropna().iloc[-1]
            return float(latest_price)

        except Exception as e:
            logger.error(f"Failed to get latest price: {str(e)}")
            return None

    def search_stocks(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Search stocks by keyword (name or stock_id)

        Args:
            keyword: Search keyword

        Returns:
            List of matching stocks
        """
        if not self.is_available():
            raise RuntimeError("FinLab client not available")

        try:
            stocks = self.get_stock_list()

            # Search in both stock_id and name
            keyword = keyword.lower()
            matches = stocks[
                stocks.index.str.lower().str.contains(keyword) |
                stocks['stock_name'].str.lower().str.contains(keyword)
            ]

            result = [
                {
                    "stock_id": idx,
                    "name": row['stock_name'],
                    "industry": row.get('industry_category', ''),
                    "market": row.get('market', ''),
                }
                for idx, row in matches.iterrows()
            ]

            logger.info(f"Found {len(result)} stocks matching '{keyword}'")
            return result

        except Exception as e:
            logger.error(f"Failed to search stocks: {str(e)}")
            raise

    def get_fundamental_indicator(
        self,
        indicator: str,
        stock_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Get fundamental indicator data for stocks

        Args:
            indicator: Fundamental indicator name (e.g., "ROE稅後", "ROA稅後息前", "營業毛利率")
            stock_id: Stock ID (e.g., "2330"). If None, returns all stocks.
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            DataFrame with fundamental indicator values

        Examples:
            >>> client = FinLabClient()
            >>> # Get ROE for all stocks
            >>> roe_data = client.get_fundamental_indicator("ROE稅後")
            >>> # Get ROE for specific stock
            >>> roe_2330 = client.get_fundamental_indicator("ROE稅後", stock_id="2330")
        """
        if not self.is_available():
            raise RuntimeError("FinLab client not available")

        try:
            # Get fundamental data from FinLab
            data_key = f"fundamental_features:{indicator}"
            fundamental_data = data.get(data_key)

            # Filter by date range
            if start_date:
                fundamental_data = fundamental_data[fundamental_data.index >= start_date]
            if end_date:
                fundamental_data = fundamental_data[fundamental_data.index <= end_date]

            # Filter by stock_id
            if stock_id:
                if stock_id not in fundamental_data.columns:
                    raise ValueError(f"Stock {stock_id} not found in {indicator} data")
                fundamental_data = fundamental_data[[stock_id]]

            logger.info(f"Retrieved {indicator} data: {fundamental_data.shape}")
            return fundamental_data

        except ValueError as e:
            # Data not found is a normal case (not all stocks have all indicators)
            error_msg = str(e).lower()
            if "not found" in error_msg or "no data" in error_msg:
                logger.warning(f"⚠️  Data unavailable for '{indicator}': {str(e)}")
            else:
                logger.error(f"Failed to get fundamental indicator '{indicator}': {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to get fundamental indicator '{indicator}': {str(e)}")
            raise

    def get_fundamental_indicators_batch(
        self,
        stock_id: str,
        indicators: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        Get multiple fundamental indicators for a single stock

        Args:
            stock_id: Stock ID (e.g., "2330")
            indicators: List of indicator names. If None, returns common indicators.
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            Dictionary mapping indicator names to DataFrames

        Examples:
            >>> client = FinLabClient()
            >>> # Get default indicators for Taiwan Semiconductor
            >>> indicators = client.get_fundamental_indicators_batch("2330")
            >>> # Get specific indicators
            >>> custom = client.get_fundamental_indicators_batch(
            ...     "2330",
            ...     indicators=["ROE稅後", "ROA稅後息前"]
            ... )
        """
        if not self.is_available():
            raise RuntimeError("FinLab client not available")

        # Default common indicators if not specified
        if indicators is None:
            indicators = self.get_common_fundamental_indicators()

        result = {}
        for indicator in indicators:
            try:
                data = self.get_fundamental_indicator(
                    indicator=indicator,
                    stock_id=stock_id,
                    start_date=start_date,
                    end_date=end_date,
                )
                result[indicator] = data
            except Exception as e:
                logger.warning(f"Failed to get {indicator} for {stock_id}: {str(e)}")
                # Continue with other indicators even if one fails
                continue

        logger.info(f"Retrieved {len(result)}/{len(indicators)} indicators for {stock_id}")
        return result

    @staticmethod
    def get_common_fundamental_indicators() -> List[str]:
        """
        Get list of commonly used fundamental indicators

        Returns:
            List of indicator names
        """
        return [
            # Profitability indicators
            "ROE稅後",              # Return on Equity (after tax)
            "ROA稅後息前",          # Return on Assets (after tax, before interest)
            "營業毛利率",           # Operating Gross Margin
            "營業利益率",           # Operating Profit Margin
            "稅前淨利率",           # Pre-tax Net Profit Margin
            "稅後淨利率",           # After-tax Net Profit Margin

            # Growth indicators
            "營收成長率",           # Revenue Growth Rate
            "稅前淨利成長率",       # Pre-tax Net Profit Growth Rate
            "稅後淨利成長率",       # After-tax Net Profit Growth Rate

            # Efficiency indicators
            "應收帳款週轉率",       # Accounts Receivable Turnover
            "存貨週轉率",           # Inventory Turnover
            "總資產週轉次數",       # Total Asset Turnover (corrected name)

            # Financial structure indicators
            "負債比率",             # Debt Ratio
            "流動比率",             # Current Ratio
            "速動比率",             # Quick Ratio

            # Per-share indicators
            "每股稅後淨利",         # Earnings Per Share (EPS) - corrected name
            "每股營業額",           # Revenue Per Share
            "每股現金流量",         # Cash Flow Per Share
        ]

    @staticmethod
    def get_fundamental_indicator_categories() -> Dict[str, List[str]]:
        """
        Get fundamental indicators organized by category

        Returns:
            Dictionary mapping category names to lists of indicators
        """
        return {
            "profitability": [
                "ROE稅後",
                "ROA稅後息前",
                "營業毛利率",
                "營業利益率",
                "稅前淨利率",
                "稅後淨利率",
            ],
            "growth": [
                "營收成長率",
                "稅前淨利成長率",
                "稅後淨利成長率",
            ],
            "efficiency": [
                "應收帳款週轉率",
                "存貨週轉率",
                "總資產週轉次數",
            ],
            "financial_structure": [
                "負債比率",
                "流動比率",
                "速動比率",
            ],
            "per_share": [
                "每股稅後淨利",
                "每股營業額",
                "每股現金流量",
            ],
        }
