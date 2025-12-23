"""
Stock Minute Price Repository

資料庫訪問層，負責 stock_minute_prices 表的 CRUD 操作

⚠️ 時區處理規則：
- stock_minute_prices 表使用 TIMESTAMP WITHOUT TIME ZONE，儲存台灣本地時間
- 查詢時：如果傳入 UTC aware datetime，會自動轉換為台灣 naive datetime
- 寫入時：確保傳入的 datetime 已經是台灣 naive datetime
- 返回時：返回台灣 naive datetime（Service 層負責轉回 UTC）
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.models.stock_minute_price import StockMinutePrice
from app.schemas.stock_minute_price import StockMinutePriceCreate, StockMinutePriceUpdate
from app.utils.timezone_helpers import utc_to_naive_taipei
from datetime import datetime, timezone
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
            datetime: 時間戳記（UTC aware 或 naive）
            timeframe: 時間粒度

        Returns:
            StockMinutePrice 物件，不存在返回 None
        """
        # 時區轉換：如果傳入 UTC aware datetime，轉換為台灣 naive datetime
        if datetime.tzinfo is not None:
            datetime = utc_to_naive_taipei(datetime)
            logger.debug(f"Converted UTC datetime to Taiwan time: {datetime}")

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
            start_datetime: 開始時間（可選，UTC aware 或 naive）
            end_datetime: 結束時間（可選，UTC aware 或 naive）
            timeframe: 時間粒度（僅用於相容性，資料庫只有 1min）
            limit: 最大筆數（預設 10000）

        Returns:
            StockMinutePrice 列表，按時間升序排列

        Note:
            - 如果指定時間範圍：返回範圍內的記錄（升序）
            - 如果未指定時間範圍：返回最新的 N 筆記錄（升序）
        """
        # 時區轉換：如果傳入 UTC aware datetime，轉換為台灣 naive datetime
        if start_datetime and start_datetime.tzinfo is not None:
            start_datetime = utc_to_naive_taipei(start_datetime)
            logger.debug(f"Converted UTC start_datetime to Taiwan time: {start_datetime}")

        if end_datetime and end_datetime.tzinfo is not None:
            end_datetime = utc_to_naive_taipei(end_datetime)
            logger.debug(f"Converted UTC end_datetime to Taiwan time: {end_datetime}")

        # 資料庫只有 1min 資料，移除 timeframe 過濾條件
        query = db.query(StockMinutePrice).filter(
            StockMinutePrice.stock_id == stock_id
        )

        if start_datetime:
            query = query.filter(StockMinutePrice.datetime >= start_datetime)
        if end_datetime:
            query = query.filter(StockMinutePrice.datetime <= end_datetime)

        # 關鍵修復：如果沒有指定時間範圍，返回最新的 N 筆記錄
        if not start_datetime and not end_datetime:
            # 先降序取最新 N 筆，再反轉為升序
            records = query.order_by(StockMinutePrice.datetime.desc()).limit(limit).all()
            return list(reversed(records))  # 反轉為升序（時間從早到晚）
        else:
            # 有時間範圍時，直接升序返回
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
