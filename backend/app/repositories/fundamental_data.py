from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.fundamental_data import FundamentalData
from loguru import logger


class FundamentalDataRepository:
    """財務指標數據 Repository"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_stock_indicator_date(
        self,
        stock_id: str,
        indicator: str,
        date: str
    ) -> Optional[FundamentalData]:
        """
        獲取特定股票、指標、日期的數據
        """
        return self.db.query(FundamentalData).filter(
            and_(
                FundamentalData.stock_id == stock_id,
                FundamentalData.indicator == indicator,
                FundamentalData.date == date
            )
        ).first()

    def get_by_stock_indicator(
        self,
        stock_id: str,
        indicator: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[FundamentalData]:
        """
        獲取特定股票和指標的歷史數據
        """
        query = self.db.query(FundamentalData).filter(
            and_(
                FundamentalData.stock_id == stock_id,
                FundamentalData.indicator == indicator
            )
        )

        if start_date:
            query = query.filter(FundamentalData.date >= start_date)
        if end_date:
            query = query.filter(FundamentalData.date <= end_date)

        return query.order_by(FundamentalData.date).all()

    def get_by_stock_indicators(
        self,
        stock_id: str,
        indicators: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, List[FundamentalData]]:
        """
        獲取特定股票的多個指標數據

        Returns:
            Dict mapping indicator names to list of data points
        """
        result = {}

        for indicator in indicators:
            data = self.get_by_stock_indicator(
                stock_id, indicator, start_date, end_date
            )
            result[indicator] = data

        return result

    def bulk_upsert(
        self,
        data_points: List[Dict[str, any]]
    ) -> int:
        """
        批量插入或更新數據

        Args:
            data_points: List of dicts with keys: stock_id, indicator, date, value

        Returns:
            Number of records created or updated
        """
        count = 0

        for point in data_points:
            existing = self.get_by_stock_indicator_date(
                stock_id=point['stock_id'],
                indicator=point['indicator'],
                date=point['date']
            )

            if existing:
                # Update existing record
                existing.value = point['value']
                logger.debug(f"Updated {point['stock_id']} {point['indicator']} {point['date']}")
            else:
                # Create new record
                new_data = FundamentalData(**point)
                self.db.add(new_data)
                logger.debug(f"Created {point['stock_id']} {point['indicator']} {point['date']}")

            count += 1

        self.db.commit()
        logger.info(f"Bulk upserted {count} fundamental data records")
        return count

    def get_latest_date_by_indicator(
        self,
        indicator: str,
        stock_id: Optional[str] = None
    ) -> Optional[str]:
        """
        獲取某個指標的最新數據日期

        Args:
            indicator: 指標名稱
            stock_id: 可選的股票代號

        Returns:
            最新日期字符串 (e.g., "2024-Q4")
        """
        query = self.db.query(FundamentalData.date).filter(
            FundamentalData.indicator == indicator
        )

        if stock_id:
            query = query.filter(FundamentalData.stock_id == stock_id)

        result = query.order_by(FundamentalData.date.desc()).first()
        return result[0] if result else None

    def delete_by_stock_indicator(
        self,
        stock_id: str,
        indicator: str
    ) -> int:
        """
        刪除特定股票和指標的所有數據

        Returns:
            刪除的記錄數
        """
        count = self.db.query(FundamentalData).filter(
            and_(
                FundamentalData.stock_id == stock_id,
                FundamentalData.indicator == indicator
            )
        ).delete()

        self.db.commit()
        logger.info(f"Deleted {count} records for {stock_id} - {indicator}")
        return count

    def get_distinct_stock_ids(self) -> List[str]:
        """
        獲取所有有財務數據的股票代號列表
        """
        results = self.db.query(FundamentalData.stock_id).distinct().all()
        return [r[0] for r in results]

    def get_distinct_indicators(self, stock_id: Optional[str] = None) -> List[str]:
        """
        獲取所有可用的財務指標列表

        Args:
            stock_id: 可選的股票代號過濾
        """
        query = self.db.query(FundamentalData.indicator).distinct()

        if stock_id:
            query = query.filter(FundamentalData.stock_id == stock_id)

        results = query.all()
        return [r[0] for r in results]
