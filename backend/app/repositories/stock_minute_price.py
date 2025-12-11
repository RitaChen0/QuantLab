"""
Stock Minute Price Repository

資料庫訪問層，負責 stock_minute_prices 表的 CRUD 操作
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.models.stock_minute_price import StockMinutePrice
from app.schemas.stock_minute_price import StockMinutePriceCreate, StockMinutePriceUpdate
from datetime import datetime
from typing import Optional, List
from loguru import logger


class StockMinutePriceRepository:
    """分鐘級股票價格資料庫訪問層"""

    @staticmethod
    def get_by_stock_datetime_timeframe(
        db: Session,
        stock_id: str,
        datetime: datetime,
        timeframe: str = '1min'
    ) -> Optional[StockMinutePrice]:
        """
        複合主鍵查詢

        Args:
            db: 資料庫會話
            stock_id: 股票代碼
            datetime: 時間戳記
            timeframe: 時間粒度

        Returns:
            StockMinutePrice 物件，不存在返回 None
        """
        return db.query(StockMinutePrice).filter(
            and_(
                StockMinutePrice.stock_id == stock_id,
                StockMinutePrice.datetime == datetime,
                StockMinutePrice.timeframe == timeframe
            )
        ).first()

    @staticmethod
    def get_by_stock(
        db: Session,
        stock_id: str,
        start_datetime: Optional[datetime] = None,
        end_datetime: Optional[datetime] = None,
        timeframe: str = '1min',
        limit: int = 10000
    ) -> List[StockMinutePrice]:
        """
        範圍查詢（限制 10000 筆）

        Args:
            db: 資料庫會話
            stock_id: 股票代碼
            start_datetime: 開始時間（可選）
            end_datetime: 結束時間（可選）
            timeframe: 時間粒度
            limit: 最大筆數（預設 10000）

        Returns:
            StockMinutePrice 列表，按時間升序排列
        """
        query = db.query(StockMinutePrice).filter(
            and_(
                StockMinutePrice.stock_id == stock_id,
                StockMinutePrice.timeframe == timeframe
            )
        )

        if start_datetime:
            query = query.filter(StockMinutePrice.datetime >= start_datetime)
        if end_datetime:
            query = query.filter(StockMinutePrice.datetime <= end_datetime)

        return query.order_by(StockMinutePrice.datetime.asc()).limit(limit).all()

    @staticmethod
    def get_latest(
        db: Session,
        stock_id: str,
        timeframe: str = '1min'
    ) -> Optional[StockMinutePrice]:
        """
        獲取最新價格

        Args:
            db: 資料庫會話
            stock_id: 股票代碼
            timeframe: 時間粒度

        Returns:
            最新的 StockMinutePrice 物件，不存在返回 None
        """
        return db.query(StockMinutePrice).filter(
            and_(
                StockMinutePrice.stock_id == stock_id,
                StockMinutePrice.timeframe == timeframe
            )
        ).order_by(desc(StockMinutePrice.datetime)).first()

    @staticmethod
    def create(
        db: Session,
        price_data: StockMinutePriceCreate
    ) -> StockMinutePrice:
        """
        創建單筆記錄

        Args:
            db: 資料庫會話
            price_data: 價格數據 Schema

        Returns:
            創建的 StockMinutePrice 物件
        """
        db_price = StockMinutePrice(**price_data.model_dump())
        db.add(db_price)
        db.commit()
        db.refresh(db_price)
        return db_price

    @staticmethod
    def create_bulk(
        db: Session,
        prices: List[StockMinutePriceCreate]
    ) -> int:
        """
        批次插入

        Args:
            db: 資料庫會話
            prices: 價格數據列表

        Returns:
            插入的記錄數
        """
        db_prices = [StockMinutePrice(**price.model_dump()) for price in prices]
        db.bulk_save_objects(db_prices)
        db.commit()
        return len(db_prices)

    @staticmethod
    def upsert(
        db: Session,
        stock_id: str,
        datetime: datetime,
        timeframe: str,
        price_data: StockMinutePriceCreate
    ) -> StockMinutePrice:
        """
        插入或更新（避免重複數據）

        Args:
            db: 資料庫會話
            stock_id: 股票代碼
            datetime: 時間戳記
            timeframe: 時間粒度
            price_data: 價格數據 Schema

        Returns:
            StockMinutePrice 物件（新建或更新後）
        """
        existing = StockMinutePriceRepository.get_by_stock_datetime_timeframe(
            db, stock_id, datetime, timeframe
        )

        if existing:
            # 更新現有記錄
            for key, value in price_data.model_dump(exclude_unset=True).items():
                setattr(existing, key, value)
            db.commit()
            db.refresh(existing)
            logger.debug(f"Updated minute price for {stock_id} at {datetime}")
            return existing
        else:
            # 插入新記錄
            db_price = StockMinutePrice(**price_data.model_dump())
            db.add(db_price)
            db.commit()
            db.refresh(db_price)
            logger.debug(f"Created new minute price for {stock_id} at {datetime}")
            return db_price

    @staticmethod
    def update(
        db: Session,
        stock_id: str,
        datetime: datetime,
        timeframe: str,
        price_update: StockMinutePriceUpdate
    ) -> Optional[StockMinutePrice]:
        """
        更新記錄

        Args:
            db: 資料庫會話
            stock_id: 股票代碼
            datetime: 時間戳記
            timeframe: 時間粒度
            price_update: 更新數據 Schema

        Returns:
            更新後的 StockMinutePrice 物件，不存在返回 None
        """
        existing = StockMinutePriceRepository.get_by_stock_datetime_timeframe(
            db, stock_id, datetime, timeframe
        )

        if not existing:
            return None

        for key, value in price_update.model_dump(exclude_unset=True).items():
            setattr(existing, key, value)

        db.commit()
        db.refresh(existing)
        return existing

    @staticmethod
    def delete(
        db: Session,
        stock_id: str,
        datetime: datetime,
        timeframe: str = '1min'
    ) -> bool:
        """
        刪除記錄

        Args:
            db: 資料庫會話
            stock_id: 股票代碼
            datetime: 時間戳記
            timeframe: 時間粒度

        Returns:
            成功刪除返回 True，記錄不存在返回 False
        """
        existing = StockMinutePriceRepository.get_by_stock_datetime_timeframe(
            db, stock_id, datetime, timeframe
        )

        if not existing:
            return False

        db.delete(existing)
        db.commit()
        return True

    @staticmethod
    def get_count(
        db: Session,
        stock_id: Optional[str] = None,
        timeframe: Optional[str] = None
    ) -> int:
        """
        獲取記錄數量

        Args:
            db: 資料庫會話
            stock_id: 股票代碼（可選，不傳則統計所有股票）
            timeframe: 時間粒度（可選，不傳則統計所有粒度）

        Returns:
            記錄數量
        """
        query = db.query(StockMinutePrice)

        if stock_id:
            query = query.filter(StockMinutePrice.stock_id == stock_id)
        if timeframe:
            query = query.filter(StockMinutePrice.timeframe == timeframe)

        return query.count()

    @staticmethod
    def get_date_range(
        db: Session,
        stock_id: str,
        timeframe: str = '1min'
    ) -> Optional[dict]:
        """
        獲取股票的數據日期範圍

        Args:
            db: 資料庫會話
            stock_id: 股票代碼
            timeframe: 時間粒度

        Returns:
            {"min_date": datetime, "max_date": datetime}，無數據返回 None
        """
        from sqlalchemy import func

        result = db.query(
            func.min(StockMinutePrice.datetime).label('min_date'),
            func.max(StockMinutePrice.datetime).label('max_date')
        ).filter(
            and_(
                StockMinutePrice.stock_id == stock_id,
                StockMinutePrice.timeframe == timeframe
            )
        ).first()

        if result and result.min_date and result.max_date:
            return {
                "min_date": result.min_date,
                "max_date": result.max_date
            }
        return None
