"""
Stock Minute Price Service

業務邏輯層，負責分鐘級股票價格的同步、驗證和管理
"""
from sqlalchemy.orm import Session
from app.repositories.stock_minute_price import StockMinutePriceRepository
from app.schemas.stock_minute_price import StockMinutePriceCreate
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict
import pandas as pd
from loguru import logger

# Optional import for Shioaji client (not needed for CSV-based data)
try:
    from app.services.shioaji_client import ShioajiClient
    SHIOAJI_AVAILABLE = True
except ImportError:
    SHIOAJI_AVAILABLE = False
    logger.warning("ShioajiClient not available - live sync features disabled")


class StockMinutePriceService:
    """分鐘級股票價格業務邏輯層"""

    def __init__(self, db: Session):
        """
        初始化 Service

        Args:
            db: 資料庫會話
        """
        self.db = db
        self.repo = StockMinutePriceRepository

    def sync_stock_minute_data(
        self,
        stock_id: str,
        start_datetime: datetime,
        end_datetime: datetime,
        timeframe: str = '1min'
    ) -> int:
        """
        同步單一股票的分鐘級數據

        Args:
            stock_id: 股票代碼
            start_datetime: 開始時間
            end_datetime: 結束時間
            timeframe: 時間粒度

        Returns:
            int: 新增/更新的記錄數

        Raises:
            RuntimeError: Shioaji 客戶端不可用
            ValueError: 數據驗證失敗
        """
        if not SHIOAJI_AVAILABLE:
            raise RuntimeError("Shioaji client not available. Please install shioaji package.")

        logger.info(f"Starting sync for {stock_id} ({timeframe}) from {start_datetime} to {end_datetime}")

        with ShioajiClient() as client:
            if not client.is_available():
                logger.error("Shioaji client not available")
                raise RuntimeError("Shioaji client not initialized")

            # 獲取 K 線數據
            df = client.get_kbars(stock_id, start_datetime, end_datetime, timeframe)
            if df is None or df.empty:
                logger.warning(f"No data fetched for {stock_id}")
                return 0

            # 批次插入/更新
            saved_count = 0
            failed_count = 0

            for idx, row in df.iterrows():
                try:
                    price_data = StockMinutePriceCreate(
                        stock_id=stock_id,
                        datetime=row['datetime'],
                        timeframe=timeframe,
                        open=row['open'],
                        high=row['high'],
                        low=row['low'],
                        close=row['close'],
                        volume=row['volume']
                    )

                    self.repo.upsert(
                        self.db,
                        stock_id,
                        row['datetime'],
                        timeframe,
                        price_data
                    )
                    saved_count += 1

                except Exception as e:
                    logger.error(f"Failed to save record for {stock_id} at {row['datetime']}: {str(e)}")
                    failed_count += 1
                    continue

            logger.info(
                f"✅ Synced {saved_count} records for {stock_id} ({timeframe}), "
                f"failed: {failed_count}"
            )
            return saved_count

    def get_intraday_ohlcv(
        self,
        stock_id: str,
        start_datetime: Optional[datetime] = None,
        end_datetime: Optional[datetime] = None,
        timeframe: str = '1min',
        limit: int = 10000
    ) -> Dict:
        """
        獲取分鐘級 OHLCV 數據（支援即時聚合）

        Args:
            stock_id: 股票代碼
            start_datetime: 開始時間（可選）
            end_datetime: 結束時間（可選）
            timeframe: 時間粒度 (1min/5min/15min/30min/60min)
            limit: 最大筆數

        Returns:
            dict: {
                "stock_id": str,
                "timeframe": str,
                "data": {datetime: {open, high, low, close, volume}},
                "count": int
            }
        """
        # 資料庫只有 1min 資料，先取得所有 1 分鐘資料
        prices = self.repo.get_by_stock(
            self.db, stock_id, start_datetime, end_datetime, '1min', limit
        )

        if not prices:
            logger.warning(f"No data found for {stock_id} ({timeframe})")
            return {
                "stock_id": stock_id,
                "timeframe": timeframe,
                "data": {},
                "count": 0
            }

        # 轉換為 DataFrame 以便聚合
        df = pd.DataFrame([
            {
                "datetime": price.datetime,
                "open": float(price.open),
                "high": float(price.high),
                "low": float(price.low),
                "close": float(price.close),
                "volume": int(price.volume)
            }
            for price in prices
        ])
        df.set_index('datetime', inplace=True)

        # 如果需要聚合（5min/15min/30min/60min）
        if timeframe in ['5min', '15min', '30min', '60min']:
            df = self._aggregate_to_timeframe(df, timeframe)
            logger.info(f"Aggregated {len(prices)} 1min bars to {len(df)} {timeframe} bars for {stock_id}")

        # 格式化返回
        data = {}
        for idx, row in df.iterrows():
            data[idx.isoformat()] = {
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
                "volume": int(row['volume'])
            }

        return {
            "stock_id": stock_id,
            "timeframe": timeframe,
            "data": data,
            "count": len(df)
        }

    def _aggregate_to_timeframe(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        聚合 1 分鐘資料到指定粒度

        Args:
            df: 1 分鐘 OHLCV DataFrame (index: datetime)
            timeframe: 目標粒度 (5min/15min/30min/60min)

        Returns:
            聚合後的 DataFrame
        """
        # 時間粒度映射（Pandas resample 格式）
        freq_map = {
            '5min': '5T',   # 5 分鐘
            '15min': '15T', # 15 分鐘
            '30min': '30T', # 30 分鐘
            '60min': '60T'  # 60 分鐘
        }

        if timeframe not in freq_map:
            logger.warning(f"Unsupported timeframe: {timeframe}, returning 1min data")
            return df

        freq = freq_map[timeframe]

        # 使用 Pandas resample 聚合
        aggregated = df.resample(freq).agg({
            'open': 'first',   # 第一筆的開盤價
            'high': 'max',     # 最高價
            'low': 'min',      # 最低價
            'close': 'last',   # 最後一筆的收盤價
            'volume': 'sum'    # 成交量總和
        }).dropna()  # 移除沒有資料的時間區間

        return aggregated

    def get_latest_price(
        self,
        stock_id: str,
        timeframe: str = '1min'
    ) -> Optional[Dict]:
        """
        獲取最新分鐘價格

        Args:
            stock_id: 股票代碼
            timeframe: 時間粒度

        Returns:
            dict: {datetime, open, high, low, close, volume} 或 None
        """
        price = self.repo.get_latest(self.db, stock_id, timeframe)

        if not price:
            return None

        return {
            "stock_id": price.stock_id,
            "datetime": price.datetime.isoformat(),
            "timeframe": price.timeframe,
            "open": float(price.open),
            "high": float(price.high),
            "low": float(price.low),
            "close": float(price.close),
            "volume": int(price.volume),
            "created_at": price.created_at.isoformat() if price.created_at else None
        }

    def get_data_coverage(
        self,
        stock_id: str,
        timeframe: str = '1min'
    ) -> Optional[Dict]:
        """
        獲取股票數據覆蓋範圍

        Args:
            stock_id: 股票代碼
            timeframe: 時間粒度

        Returns:
            dict: {
                "stock_id": str,
                "timeframe": str,
                "min_date": str,
                "max_date": str,
                "count": int
            } 或 None
        """
        date_range = self.repo.get_date_range(self.db, stock_id, timeframe)

        if not date_range:
            return None

        count = self.repo.get_count(self.db, stock_id, timeframe)

        return {
            "stock_id": stock_id,
            "timeframe": timeframe,
            "min_date": date_range["min_date"].isoformat(),
            "max_date": date_range["max_date"].isoformat(),
            "count": count
        }

    def sync_multiple_stocks(
        self,
        stock_ids: List[str],
        start_datetime: datetime,
        end_datetime: datetime,
        timeframe: str = '1min'
    ) -> Dict:
        """
        批次同步多檔股票

        Args:
            stock_ids: 股票代碼列表
            start_datetime: 開始時間
            end_datetime: 結束時間
            timeframe: 時間粒度

        Returns:
            dict: {
                "total_stocks": int,
                "total_records": int,
                "succeeded": List[str],
                "failed": List[str]
            }
        """
        total_records = 0
        succeeded = []
        failed = []

        logger.info(f"Starting batch sync for {len(stock_ids)} stocks ({timeframe})")

        for stock_id in stock_ids:
            try:
                count = self.sync_stock_minute_data(
                    stock_id, start_datetime, end_datetime, timeframe
                )
                total_records += count
                succeeded.append(stock_id)
                logger.info(f"✅ Synced {stock_id}: {count} records")

            except Exception as e:
                logger.error(f"❌ Failed to sync {stock_id}: {str(e)}")
                failed.append(stock_id)
                continue

        result = {
            "total_stocks": len(stock_ids),
            "total_records": total_records,
            "succeeded": succeeded,
            "failed": failed,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        logger.info(
            f"Batch sync completed: {len(succeeded)}/{len(stock_ids)} stocks, "
            f"{total_records} total records"
        )

        return result

    def get_statistics(
        self,
        stock_id: Optional[str] = None,
        timeframe: Optional[str] = None
    ) -> Dict:
        """
        獲取統計資訊

        Args:
            stock_id: 股票代碼（可選）
            timeframe: 時間粒度（可選）

        Returns:
            dict: {
                "total_records": int,
                "stock_id": str (optional),
                "timeframe": str (optional)
            }
        """
        count = self.repo.get_count(self.db, stock_id, timeframe)

        result = {"total_records": count}

        if stock_id:
            result["stock_id"] = stock_id
        if timeframe:
            result["timeframe"] = timeframe

        return result

    def validate_timeframe(self, timeframe: str) -> bool:
        """
        驗證時間粒度

        Args:
            timeframe: 時間粒度字串

        Returns:
            bool: 有效返回 True，無效返回 False
        """
        valid_timeframes = ['1min', '5min', '15min', '30min', '60min', '1day']
        return timeframe in valid_timeframes

    def calculate_sync_range(
        self,
        stock_id: str,
        timeframe: str,
        days_back: int = 7
    ) -> tuple[datetime, datetime]:
        """
        計算智慧同步範圍

        檢查現有數據，自動決定同步範圍：
        - 如果無數據：從 days_back 天前開始
        - 如果有數據：從最新數據時間開始

        Args:
            stock_id: 股票代碼
            timeframe: 時間粒度
            days_back: 回溯天數（預設 7 天）

        Returns:
            tuple: (start_datetime, end_datetime)
        """
        from datetime import timezone as tz

        # 檢查現有數據
        date_range = self.repo.get_date_range(self.db, stock_id, timeframe)

        # 明確使用 UTC 時間
        end_datetime = datetime.now(tz.utc)

        if date_range and date_range["max_date"]:
            # 從最後一筆數據的下一分鐘開始（避免重複）
            start_datetime = date_range["max_date"] + timedelta(minutes=1)

            # 確保 timezone-aware
            if start_datetime.tzinfo is None:
                start_datetime = start_datetime.replace(tzinfo=tz.utc)

            logger.info(
                f"Incremental sync for {stock_id}: "
                f"from {start_datetime} (last record + 1min)"
            )
        else:
            # 無數據，從 days_back 天前開始
            start_datetime = end_datetime - timedelta(days=days_back)
            logger.info(
                f"Full sync for {stock_id}: "
                f"from {start_datetime} ({days_back} days back)"
            )

        return start_datetime, end_datetime
