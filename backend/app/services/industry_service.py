"""
Industry Service

Business logic for industry classification and metrics aggregation.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import date, datetime
from statistics import mean

from app.repositories.industry import IndustryRepository
from app.repositories.fundamental_data import FundamentalDataRepository
from app.models.industry import Industry
from app.models.stock_industry import StockIndustry
from app.models.industry_metrics_cache import IndustryMetricsCache
from app.utils.cache import cache
from loguru import logger


class IndustryService:
    """Service layer for industry-related business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = IndustryRepository()
        self.fundamental_repo = FundamentalDataRepository(db)

    # Industry Data Methods

    def get_all_industries(
        self, level: Optional[int] = None, parent_code: Optional[str] = None
    ) -> List[Industry]:
        """
        Get all industries with optional filtering.

        Args:
            level: Filter by industry level
            parent_code: Filter by parent code

        Returns:
            List of Industry objects
        """
        return self.repo.get_all_industries(self.db, level, parent_code)

    def get_industry_by_code(self, code: str) -> Optional[Industry]:
        """Get industry by code."""
        return self.repo.get_industry_by_code(self.db, code)

    def get_industry_hierarchy(self, parent_code: str) -> List[Industry]:
        """Get industry hierarchy (parent and all children)."""
        return self.repo.get_industry_hierarchy(self.db, parent_code)

    def get_root_industries(self) -> List[Industry]:
        """Get all top-level industries."""
        return self.repo.get_root_industries(self.db)

    def get_industry_tree(self) -> List[Dict[str, Any]]:
        """
        Get complete industry tree structure.

        Returns:
            List of industry trees with nested children
        """
        roots = self.get_root_industries()
        trees = []

        for root in roots:
            tree = self._build_industry_tree(root)
            trees.append(tree)

        return trees

    def _build_industry_tree(self, industry: Industry) -> Dict[str, Any]:
        """
        Recursively build industry tree.

        Args:
            industry: Industry node

        Returns:
            Industry dict with nested children
        """
        # Get children
        children = self.repo.get_all_industries(
            self.db, parent_code=industry.code
        )

        # Build tree
        tree = {
            "code": industry.code,
            "name_zh": industry.name_zh,
            "name_en": industry.name_en,
            "level": industry.level,
            "parent_code": industry.parent_code,
            "stock_count": self.repo.get_stock_count_by_industry(
                self.db, industry.code
            ),
            "children": [self._build_industry_tree(child) for child in children]
        }

        return tree

    # Stock-Industry Relationship Methods

    def get_industries_by_stock(
        self, stock_id: str, primary_only: bool = False
    ) -> List[Industry]:
        """Get industries associated with a stock."""
        return self.repo.get_industries_by_stock(
            self.db, stock_id, primary_only
        )

    def get_stocks_by_industry(
        self, industry_code: str, primary_only: bool = False
    ) -> List[Dict[str, str]]:
        """Get stocks associated with an industry with names."""
        from finlab import data

        # Get stock IDs from database
        stock_ids = self.repo.get_stocks_by_industry(
            self.db, industry_code, primary_only
        )

        # Get stock names from FinLab
        try:
            company_info = data.get('company_basic_info')

            # Build stock info list
            stocks_with_names = []
            for stock_id in stock_ids:
                # Find stock name
                stock_data = company_info[company_info['stock_id'] == stock_id]
                if len(stock_data) > 0:
                    stock_name = stock_data.iloc[0]['公司簡稱']
                else:
                    stock_name = stock_id  # Fallback to stock ID

                stocks_with_names.append({
                    'stock_id': stock_id,
                    'stock_name': stock_name
                })

            return stocks_with_names
        except Exception as e:
            logger.warning(f"Failed to get stock names: {str(e)}, returning IDs only")
            # Fallback: return just IDs
            return [{'stock_id': sid, 'stock_name': sid} for sid in stock_ids]

    # Industry Metrics Calculation Methods

    def _get_previous_quarter(self, quarter_str: str) -> Optional[str]:
        """
        Get the previous quarter from a quarter string.

        Args:
            quarter_str: Quarter string like "2025-Q3"

        Returns:
            Previous quarter string like "2025-Q2", or None if invalid
        """
        try:
            year, q = quarter_str.split('-')
            year = int(year)
            quarter = int(q[1])  # Extract number from "Q3"

            if quarter == 1:
                # Previous quarter is Q4 of previous year
                return f"{year - 1}-Q4"
            else:
                # Previous quarter in same year
                return f"{year}-Q{quarter - 1}"
        except Exception as e:
            logger.warning(f"Failed to parse quarter string '{quarter_str}': {str(e)}")
            return None

    def _get_last_n_quarters(self, quarter_str: str, n: int) -> List[str]:
        """
        Get a list of the last N quarters (including current).

        Args:
            quarter_str: Current quarter string like "2025-Q3"
            n: Number of quarters to return

        Returns:
            List of quarter strings in descending order (newest first)
        """
        quarters = []
        current = quarter_str

        for _ in range(n):
            if current:
                quarters.append(current)
                current = self._get_previous_quarter(current)
            else:
                break

        return quarters

    def calculate_industry_fundamental_metrics(
        self,
        industry_code: str,
        metric_date: Optional[date] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate aggregated fundamental metrics for an industry.

        Calculates average values for key financial metrics across all stocks
        in the industry.

        Args:
            industry_code: Industry code
            metric_date: Date for metrics (defaults to latest available)
            force_refresh: Force recalculation (bypass cache)

        Returns:
            Dict containing aggregated metrics
        """
        # Get latest available quarter from fundamental_data
        # Fundamental data uses quarter format like "2024-Q4", not daily dates
        from sqlalchemy import text
        latest_quarter_result = self.db.execute(
            text("SELECT date FROM fundamental_data ORDER BY date DESC LIMIT 1")
        ).fetchone()

        if not latest_quarter_result:
            logger.warning("No fundamental data available in database")
            return {
                "industry_code": industry_code,
                "date": "N/A",
                "stocks_count": 0,
                "metrics": {}
            }

        latest_quarter = latest_quarter_result[0]
        logger.info(f"Using latest available quarter: {latest_quarter}")

        # Check cache first (using quarter string as key)
        cache_key = f"industry_metrics:{industry_code}:{latest_quarter}"
        if not force_refresh:
            cached_value = cache.get(cache_key)
            if cached_value:
                logger.info(
                    f"Using cached industry metrics for {industry_code} "
                    f"on {latest_quarter}"
                )
                return cached_value

        # Get all stocks in this industry
        stocks_with_info = self.get_stocks_by_industry(industry_code, primary_only=True)

        if not stocks_with_info:
            logger.warning(f"No stocks found for industry {industry_code}")
            return {
                "industry_code": industry_code,
                "date": latest_quarter,
                "stocks_count": 0,
                "metrics": {}
            }

        # Extract stock IDs from the list of dicts
        stock_ids = [stock['stock_id'] for stock in stocks_with_info]
        logger.info(f"Processing {len(stock_ids)} stocks for industry {industry_code}")

        # Get previous quarter for comparison
        previous_quarter = self._get_previous_quarter(latest_quarter)

        # Get last 10 quarters for trend data
        last_10_quarters = self._get_last_n_quarters(latest_quarter, 10)

        # Calculate metrics for each indicator
        metrics = {}
        indicators = [
            "ROE稅後", "ROA稅後息前", "營業毛利率", "營業利益率",
            "每股稅後淨利", "營收成長率", "稅後淨利成長率"
        ]

        for indicator in indicators:
            # Current quarter values
            values = []

            # Previous quarter values
            prev_values = []

            # Trend data (last 10 quarters)
            trend_values = []

            # Get indicator data for each stock (using quarter string)
            for stock_id in stock_ids:
                try:
                    # Current quarter
                    data = self.db.execute(
                        text("""
                            SELECT value
                            FROM fundamental_data
                            WHERE stock_id = :stock_id
                              AND indicator = :indicator
                              AND date = :quarter
                        """),
                        {
                            "stock_id": stock_id,
                            "indicator": indicator,
                            "quarter": latest_quarter
                        }
                    ).fetchone()

                    if data and data[0] is not None:
                        values.append(float(data[0]))

                except Exception as e:
                    logger.debug(
                        f"Could not get {indicator} for {stock_id}: {str(e)}"
                    )
                    continue

            # Get previous quarter average
            if previous_quarter:
                for stock_id in stock_ids:
                    try:
                        prev_data = self.db.execute(
                            text("""
                                SELECT value
                                FROM fundamental_data
                                WHERE stock_id = :stock_id
                                  AND indicator = :indicator
                                  AND date = :quarter
                            """),
                            {
                                "stock_id": stock_id,
                                "indicator": indicator,
                                "quarter": previous_quarter
                            }
                        ).fetchone()

                        if prev_data and prev_data[0] is not None:
                            prev_values.append(float(prev_data[0]))
                    except Exception:
                        continue

            # Get trend data (last 10 quarters average)
            for quarter in last_10_quarters:
                quarter_values = []
                for stock_id in stock_ids:
                    try:
                        trend_data = self.db.execute(
                            text("""
                                SELECT value
                                FROM fundamental_data
                                WHERE stock_id = :stock_id
                                  AND indicator = :indicator
                                  AND date = :quarter
                            """),
                            {
                                "stock_id": stock_id,
                                "indicator": indicator,
                                "quarter": quarter
                            }
                        ).fetchone()

                        if trend_data and trend_data[0] is not None:
                            quarter_values.append(float(trend_data[0]))
                    except Exception:
                        continue

                # Calculate average for this quarter
                if quarter_values:
                    trend_values.append(round(mean(quarter_values), 4))
                else:
                    trend_values.append(None)

            # Calculate average if we have values
            if values:
                avg_value = mean(values)
                prev_avg = mean(prev_values) if prev_values else None

                # Calculate change percent
                change_percent = None
                if prev_avg and prev_avg != 0:
                    change_percent = round(((avg_value - prev_avg) / prev_avg) * 100, 2)

                metrics[indicator] = {
                    "average": round(avg_value, 4),
                    "sample_size": len(values),
                    "previous_value": round(prev_avg, 4) if prev_avg else None,
                    "change_percent": change_percent,
                    "trend_data": trend_values if any(v is not None for v in trend_values) else None
                }

        # Check how many stocks have data
        stocks_with_data = sum(
            1 for indicator_data in metrics.values()
            if indicator_data.get('sample_size', 0) > 0
        )

        # Cache the result (30 days TTL)
        result = {
            "industry_code": industry_code,
            "date": latest_quarter,
            "stocks_count": len(stock_ids),
            "stocks_with_data_count": max(
                (m.get('sample_size', 0) for m in metrics.values()),
                default=0
            ),
            "metrics": metrics,
            "has_data": len(metrics) > 0
        }
        cache.set(cache_key, result, expiry=86400 * 30)  # 30 days

        logger.info(
            f"Calculated industry metrics for {industry_code}: "
            f"{len(metrics)} indicators, {len(stock_ids)} stocks, "
            f"{result['stocks_with_data_count']} stocks with data"
        )

        return result

    def get_industry_metrics_historical(
        self,
        industry_code: str,
        metric_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical industry metrics by calculating from fundamental_data.

        Args:
            industry_code: Industry code
            metric_name: Metric name (e.g., "ROE稅後", "營業毛利率")
            start_date: Start date (quarter format: YYYY-QN, e.g., "2024-Q1")
            end_date: End date (quarter format: YYYY-QN, e.g., "2025-Q3")

        Returns:
            List of metric data points with date, value, and stocks_count
        """
        from sqlalchemy import text

        # Get all available quarters from fundamental_data
        quarters_result = self.db.execute(
            text("SELECT DISTINCT date FROM fundamental_data ORDER BY date ASC")
        ).fetchall()

        all_quarters = [row[0] for row in quarters_result]

        # Filter by date range if provided
        if start_date:
            all_quarters = [q for q in all_quarters if q >= start_date]
        if end_date:
            all_quarters = [q for q in all_quarters if q <= end_date]

        # Get stocks in this industry
        stocks_with_info = self.get_stocks_by_industry(industry_code, primary_only=True)
        stock_ids = [stock['stock_id'] for stock in stocks_with_info]

        if not stock_ids:
            return []

        # ✅ OPTIMIZED: Single batch query instead of N×M queries
        # Fetch all data in one query to avoid N+1 problem
        batch_results = self.db.execute(
            text("""
                SELECT date, stock_id, value
                FROM fundamental_data
                WHERE stock_id = ANY(:stock_ids)
                  AND indicator = :indicator
                  AND date = ANY(:quarters)
                ORDER BY date ASC
            """),
            {
                "stock_ids": stock_ids,
                "indicator": metric_name,
                "quarters": all_quarters
            }
        ).fetchall()

        # Group results by quarter
        data_by_quarter = {}
        for date, stock_id, value in batch_results:
            if date not in data_by_quarter:
                data_by_quarter[date] = []
            if value is not None:
                try:
                    data_by_quarter[date].append(float(value))
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Invalid value for {stock_id}/{date}/{metric_name}: {e}"
                    )
                    continue

        # Calculate averages for each quarter
        historical_data = []
        for quarter in all_quarters:
            values = data_by_quarter.get(quarter, [])

            if values:
                avg_value = mean(values)
                historical_data.append({
                    "date": quarter,
                    "value": round(avg_value, 4),
                    "stocks_count": len(values)
                })
            else:
                historical_data.append({
                    "date": quarter,
                    "value": None,
                    "stocks_count": 0
                })

        logger.info(
            f"Retrieved historical metrics for {industry_code}/{metric_name}: "
            f"{len(historical_data)} quarters, {sum(1 for d in historical_data if d['value'] is not None)} with data"
        )

        return historical_data

    def get_industry_performance_summary(
        self, industry_code: str
    ) -> Dict[str, Any]:
        """
        Get industry performance summary with latest metrics.

        Args:
            industry_code: Industry code

        Returns:
            Dict containing industry info and latest metrics
        """
        # Get industry info
        industry = self.get_industry_by_code(industry_code)
        if not industry:
            return None

        # Get stock count
        stocks_count = self.repo.get_stock_count_by_industry(
            self.db, industry_code
        )

        # Get latest metrics
        latest_metrics = {}
        metric_names = [
            "avg_ROE稅後", "avg_ROA稅後息前", "avg_營業毛利率",
            "avg_營業利益率", "avg_每股稅後淨利", "avg_營收成長率"
        ]

        for metric_name in metric_names:
            metric = self.repo.get_latest_industry_metric(
                self.db, industry_code, metric_name
            )
            if metric:
                latest_metrics[metric_name] = {
                    "value": float(metric.value) if metric.value else None,
                    "date": str(metric.date),
                    "stocks_count": metric.stocks_count
                }

        return {
            "code": industry.code,
            "name_zh": industry.name_zh,
            "name_en": industry.name_en,
            "level": industry.level,
            "parent_code": industry.parent_code,
            "stocks_count": stocks_count,
            "latest_metrics": latest_metrics
        }

    # Private Helper Methods

    def _get_cached_industry_metrics(
        self, industry_code: str, metric_date: date
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached industry metrics for a specific date.

        Args:
            industry_code: Industry code
            metric_date: Metric date

        Returns:
            Cached metrics dict or None
        """
        # Get all cached metrics for this industry and date
        metric_names = [
            "avg_ROE稅後", "avg_ROA稅後息前", "avg_營業毛利率",
            "avg_營業利益率", "avg_每股稅後淨利", "avg_營收成長率",
            "avg_稅後淨利成長率"
        ]

        cached_metrics = {}
        stocks_count = None

        for metric_name in metric_names:
            metrics = self.repo.get_industry_metrics(
                self.db,
                industry_code,
                metric_name,
                start_date=str(metric_date),
                end_date=str(metric_date)
            )

            if metrics:
                metric = metrics[0]
                # Remove "avg_" prefix for display
                display_name = metric_name.replace("avg_", "")
                cached_metrics[display_name] = {
                    "average": float(metric.value) if metric.value else None,
                    "sample_size": metric.stocks_count
                }
                stocks_count = metric.stocks_count

        # Only return if we have some cached data
        if cached_metrics:
            return {
                "industry_code": industry_code,
                "date": str(metric_date),
                "stocks_count": stocks_count or 0,
                "metrics": cached_metrics
            }

        return None

    def _cache_industry_metric(
        self,
        industry_code: str,
        metric_name: str,
        metric_date: date,
        value: float,
        stocks_count: int
    ) -> None:
        """
        Cache an industry metric.

        Args:
            industry_code: Industry code
            metric_name: Metric name
            metric_date: Metric date
            value: Metric value
            stocks_count: Number of stocks in calculation
        """
        try:
            self.repo.upsert_industry_metric(
                self.db,
                industry_code,
                metric_name,
                metric_date,
                value,
                stocks_count
            )
        except Exception as e:
            logger.error(f"Failed to cache industry metric: {str(e)}")

    # Industry Comparison Methods

    def compare_industries(
        self,
        industry_codes: List[str],
        metric_name: str
    ) -> Dict[str, Any]:
        """
        Compare multiple industries on a specific metric.

        Args:
            industry_codes: List of industry codes to compare
            metric_name: Metric name (e.g., "ROE稅後")

        Returns:
            Dict containing comparison data
        """
        from sqlalchemy import text

        # Get latest quarter
        latest_quarter_result = self.db.execute(
            text("SELECT date FROM fundamental_data ORDER BY date DESC LIMIT 1")
        ).fetchone()

        if not latest_quarter_result:
            return {
                "metric_name": metric_name,
                "date": "N/A",
                "industries": []
            }

        latest_quarter = latest_quarter_result[0]

        # Get metrics for each industry
        comparison_data = []
        for industry_code in industry_codes:
            # Get industry info
            industry = self.get_industry_by_code(industry_code)
            if not industry:
                continue

            # Get stocks in this industry
            stocks_with_info = self.get_stocks_by_industry(industry_code, primary_only=True)
            stock_ids = [stock['stock_id'] for stock in stocks_with_info]

            if not stock_ids:
                comparison_data.append({
                    "industry_code": industry_code,
                    "industry_name": industry.name_zh,
                    "value": None,
                    "sample_size": 0
                })
                continue

            # Get indicator data for each stock
            values = []
            for stock_id in stock_ids:
                try:
                    data = self.db.execute(
                        text("""
                            SELECT value
                            FROM fundamental_data
                            WHERE stock_id = :stock_id
                              AND indicator = :indicator
                              AND date = :quarter
                        """),
                        {
                            "stock_id": stock_id,
                            "indicator": metric_name,
                            "quarter": latest_quarter
                        }
                    ).fetchone()

                    if data and data[0] is not None:
                        values.append(float(data[0]))
                except Exception:
                    continue

            # Calculate average
            avg_value = mean(values) if values else None

            comparison_data.append({
                "industry_code": industry_code,
                "industry_name": industry.name_zh,
                "value": round(avg_value, 4) if avg_value else None,
                "sample_size": len(values)
            })

        return {
            "metric_name": metric_name,
            "date": latest_quarter,
            "industries": comparison_data
        }

    # Statistics Methods

    def get_industry_statistics(self) -> Dict[str, Any]:
        """
        Get industry database statistics.

        Returns:
            Dict containing statistics
        """
        # Count by level
        level_counts = self.repo.get_industry_count_by_level(self.db)

        # Total industries
        total = sum(level_counts.values())

        # Total stock-industry mappings
        total_mappings = self.repo.count_stock_industry_mappings(self.db)

        return {
            "total_industries": total,
            "by_level": {
                f"level_{level}": count
                for level, count in level_counts.items()
            },
            "total_stock_mappings": total_mappings
        }
