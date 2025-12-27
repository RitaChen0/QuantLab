"""
Industry Repository

Handles database operations for industry classification data.
"""
from typing import List, Optional, Dict
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from datetime import date

from app.models.industry import Industry
from app.models.stock_industry import StockIndustry
from app.models.industry_metrics_cache import IndustryMetricsCache
from loguru import logger


class IndustryRepository:
    """Repository for industry-related database operations."""

    def get_all_industries(
        self,
        db: Session,
        level: Optional[int] = None,
        parent_code: Optional[str] = None
    ) -> List[Industry]:
        """
        Get all industries with optional filtering.

        Args:
            db: Database session
            level: Filter by industry level (1=大類, 2=中類, 3=小類)
            parent_code: Filter by parent industry code

        Returns:
            List of Industry objects
        """
        query = db.query(Industry)

        if level is not None:
            query = query.filter(Industry.level == level)

        if parent_code is not None:
            query = query.filter(Industry.parent_code == parent_code)

        return query.order_by(Industry.code).all()

    def get_industry_by_code(self, db: Session, code: str) -> Optional[Industry]:
        """
        Get industry by code.

        Args:
            db: Database session
            code: Industry code

        Returns:
            Industry object or None
        """
        return db.query(Industry).filter(Industry.code == code).first()

    def get_industries_by_codes(self, db: Session, codes: List[str]) -> List[Industry]:
        """
        Get multiple industries by codes.

        Args:
            db: Database session
            codes: List of industry codes

        Returns:
            List of Industry objects
        """
        return db.query(Industry).filter(Industry.code.in_(codes)).all()

    def get_industry_hierarchy(
        self, db: Session, parent_code: str
    ) -> List[Industry]:
        """
        Get industry hierarchy (parent and all children).

        Args:
            db: Database session
            parent_code: Parent industry code

        Returns:
            List of Industry objects (parent + children)
        """
        # Get parent
        parent = self.get_industry_by_code(db, parent_code)
        if not parent:
            return []

        # Get all children
        children = db.query(Industry).filter(
            Industry.parent_code == parent_code
        ).order_by(Industry.code).all()

        return [parent] + children

    def get_root_industries(self, db: Session) -> List[Industry]:
        """
        Get all top-level industries (level 1).

        Args:
            db: Database session

        Returns:
            List of root Industry objects
        """
        return db.query(Industry).filter(
            Industry.parent_code.is_(None)
        ).order_by(Industry.code).all()

    # Stock-Industry Relationship Methods

    def get_industries_by_stock(
        self, db: Session, stock_id: str, primary_only: bool = False
    ) -> List[Industry]:
        """
        Get all industries associated with a stock.

        Args:
            db: Database session
            stock_id: Stock ID
            primary_only: Only return primary industry

        Returns:
            List of Industry objects
        """
        query = db.query(Industry).join(
            StockIndustry, Industry.code == StockIndustry.industry_code
        ).filter(StockIndustry.stock_id == stock_id)

        if primary_only:
            query = query.filter(StockIndustry.is_primary == True)

        return query.all()

    def get_stocks_by_industry(
        self, db: Session, industry_code: str, primary_only: bool = False
    ) -> List[str]:
        """
        Get all stock IDs associated with an industry.

        Args:
            db: Database session
            industry_code: Industry code
            primary_only: Only return stocks where this is primary industry

        Returns:
            List of stock IDs
        """
        query = db.query(StockIndustry.stock_id).filter(
            StockIndustry.industry_code == industry_code
        )

        if primary_only:
            query = query.filter(StockIndustry.is_primary == True)

        results = query.all()
        return [r[0] for r in results]

    def get_stock_industry_mapping(
        self, db: Session, stock_id: str, industry_code: str
    ) -> Optional[StockIndustry]:
        """
        Get specific stock-industry mapping.

        Args:
            db: Database session
            stock_id: Stock ID
            industry_code: Industry code

        Returns:
            StockIndustry object or None
        """
        return db.query(StockIndustry).filter(
            and_(
                StockIndustry.stock_id == stock_id,
                StockIndustry.industry_code == industry_code
            )
        ).first()

    def create_stock_industry_mapping(
        self,
        db: Session,
        stock_id: str,
        industry_code: str,
        is_primary: bool = False
    ) -> StockIndustry:
        """
        Create a new stock-industry mapping.

        Args:
            db: Database session
            stock_id: Stock ID
            industry_code: Industry code
            is_primary: Whether this is the primary industry

        Returns:
            Created StockIndustry object
        """
        mapping = StockIndustry(
            stock_id=stock_id,
            industry_code=industry_code,
            is_primary=is_primary
        )
        db.add(mapping)
        db.commit()
        db.refresh(mapping)

        logger.info(
            f"Created stock-industry mapping: {stock_id} -> {industry_code} "
            f"(primary={is_primary})"
        )
        return mapping

    def delete_stock_industry_mapping(
        self, db: Session, stock_id: str, industry_code: str
    ) -> bool:
        """
        Delete a stock-industry mapping.

        Args:
            db: Database session
            stock_id: Stock ID
            industry_code: Industry code

        Returns:
            True if deleted, False if not found
        """
        mapping = self.get_stock_industry_mapping(db, stock_id, industry_code)
        if not mapping:
            return False

        db.delete(mapping)
        db.commit()

        logger.info(f"Deleted stock-industry mapping: {stock_id} -> {industry_code}")
        return True

    # Industry Metrics Cache Methods

    def get_industry_metrics(
        self,
        db: Session,
        industry_code: str,
        metric_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[IndustryMetricsCache]:
        """
        Get cached industry metrics.

        Args:
            db: Database session
            industry_code: Industry code
            metric_name: Metric name (e.g., "avg_roe", "avg_eps")
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            List of IndustryMetricsCache objects
        """
        query = db.query(IndustryMetricsCache).filter(
            and_(
                IndustryMetricsCache.industry_code == industry_code,
                IndustryMetricsCache.metric_name == metric_name
            )
        )

        if start_date:
            query = query.filter(IndustryMetricsCache.date >= start_date)

        if end_date:
            query = query.filter(IndustryMetricsCache.date <= end_date)

        return query.order_by(IndustryMetricsCache.date).all()

    def get_latest_industry_metric(
        self, db: Session, industry_code: str, metric_name: str
    ) -> Optional[IndustryMetricsCache]:
        """
        Get the latest cached metric for an industry.

        Args:
            db: Database session
            industry_code: Industry code
            metric_name: Metric name

        Returns:
            IndustryMetricsCache object or None
        """
        return db.query(IndustryMetricsCache).filter(
            and_(
                IndustryMetricsCache.industry_code == industry_code,
                IndustryMetricsCache.metric_name == metric_name
            )
        ).order_by(IndustryMetricsCache.date.desc()).first()

    def upsert_industry_metric(
        self,
        db: Session,
        industry_code: str,
        metric_name: str,
        metric_date: date,
        value: float,
        stocks_count: int
    ) -> IndustryMetricsCache:
        """
        Insert or update industry metric cache.

        Args:
            db: Database session
            industry_code: Industry code
            metric_name: Metric name
            metric_date: Metric date
            value: Metric value
            stocks_count: Number of stocks used in calculation

        Returns:
            IndustryMetricsCache object
        """
        # Try to find existing record
        existing = db.query(IndustryMetricsCache).filter(
            and_(
                IndustryMetricsCache.industry_code == industry_code,
                IndustryMetricsCache.metric_name == metric_name,
                IndustryMetricsCache.date == metric_date
            )
        ).first()

        if existing:
            # Update existing
            existing.value = value
            existing.stocks_count = stocks_count
            metric = existing
            logger.debug(
                f"Updated industry metric: {industry_code} - {metric_name} "
                f"on {metric_date}"
            )
        else:
            # Create new
            metric = IndustryMetricsCache(
                industry_code=industry_code,
                metric_name=metric_name,
                date=metric_date,
                value=value,
                stocks_count=stocks_count
            )
            db.add(metric)
            logger.debug(
                f"Created industry metric: {industry_code} - {metric_name} "
                f"on {metric_date}"
            )

        db.commit()
        db.refresh(metric)
        return metric

    def get_industry_count_by_level(self, db: Session) -> Dict[int, int]:
        """
        Get count of industries by level.

        Args:
            db: Database session

        Returns:
            Dict mapping level to count
        """
        results = db.query(
            Industry.level,
            func.count(Industry.id).label('count')
        ).group_by(Industry.level).all()

        return {level: count for level, count in results}

    def count_stock_industry_mappings(self, db: Session) -> int:
        """
        Get total count of stock-industry mappings.

        Args:
            db: Database session

        Returns:
            Total number of stock-industry mappings
        """
        return db.query(StockIndustry).count()

    def get_stock_count_by_industry(
        self, db: Session, industry_code: str
    ) -> int:
        """
        Get number of stocks in an industry.

        Args:
            db: Database session
            industry_code: Industry code

        Returns:
            Number of stocks
        """
        return db.query(StockIndustry).filter(
            StockIndustry.industry_code == industry_code
        ).count()

    def get_stock_counts_bulk(
        self, db: Session, industry_codes: List[str]
    ) -> Dict[str, int]:
        """
        Get stock counts for multiple industries in a single query (avoids N+1).

        Args:
            db: Database session
            industry_codes: List of industry codes

        Returns:
            Dict mapping industry_code to stock count
        """
        from sqlalchemy import func

        if not industry_codes:
            return {}

        counts = db.query(
            StockIndustry.industry_code,
            func.count(StockIndustry.stock_id).label('count')
        ).filter(
            StockIndustry.industry_code.in_(industry_codes)
        ).group_by(
            StockIndustry.industry_code
        ).all()

        # Create dict with default 0 for industries without stocks
        result = {code: 0 for code in industry_codes}
        for industry_code, count in counts:
            result[industry_code] = count

        return result
