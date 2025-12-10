from typing import List, Optional, Dict
import pandas as pd
from sqlalchemy.orm import Session
from app.repositories.fundamental_data import FundamentalDataRepository
from app.services.finlab_client import FinLabClient
from app.schemas.fundamental import FundamentalDataPoint
from loguru import logger


class FundamentalService:
    """
    財務指標服務層

    實現雙層緩存策略:
    1. PostgreSQL (L2 緩存) - 永久存儲
    2. FinLab API - 數據源

    注意: Redis (L1 緩存) 在 API 層處理
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = FundamentalDataRepository(db)
        self.finlab_client = FinLabClient()

    def get_indicator_data(
        self,
        stock_id: str,
        indicator: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        force_refresh: bool = False
    ) -> List[FundamentalDataPoint]:
        """
        獲取財務指標數據（雙層緩存）

        流程:
        1. 查詢 PostgreSQL (如果 force_refresh=False)
        2. 如果 DB 無數據，從 FinLab API 獲取
        3. 存入 PostgreSQL 供後續使用

        Args:
            stock_id: 股票代號
            indicator: 指標名稱
            start_date: 開始日期
            end_date: 結束日期
            force_refresh: 是否強制從 API 重新獲取

        Returns:
            List of FundamentalDataPoint
        """
        # Step 1: Try PostgreSQL first (if not forcing refresh)
        if not force_refresh:
            db_data = self.repo.get_by_stock_indicator(
                stock_id=stock_id,
                indicator=indicator,
                start_date=start_date,
                end_date=end_date
            )

            if db_data:
                logger.info(f"✅ L2 Cache HIT: {stock_id} - {indicator} ({len(db_data)} points from DB)")
                return [
                    FundamentalDataPoint(
                        date=str(d.date),
                        value=float(d.value) if d.value is not None else None
                    )
                    for d in db_data
                ]
            else:
                logger.info(f"❌ L2 Cache MISS: {stock_id} - {indicator}")

        # Step 2: Fetch from FinLab API
        logger.info(f"📡 Fetching from FinLab API: {stock_id} - {indicator}")
        data_df = self.finlab_client.get_fundamental_indicator(
            indicator=indicator,
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Step 3: Store in PostgreSQL for future use
        data_points = []
        for date, value in data_df[stock_id].items():
            data_points.append({
                'stock_id': stock_id,
                'indicator': indicator,
                'date': str(date),
                'value': float(value) if pd.notna(value) else None
            })

        if data_points:
            self.repo.bulk_upsert(data_points)
            logger.info(f"💾 Stored {len(data_points)} points in DB: {stock_id} - {indicator}")

        # Return formatted response
        return [
            FundamentalDataPoint(
                date=point['date'],
                value=point['value']
            )
            for point in data_points
        ]

    def get_indicators_batch(
        self,
        stock_id: str,
        indicators: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        force_refresh: bool = False
    ) -> Dict[str, List[FundamentalDataPoint]]:
        """
        批量獲取多個財務指標數據

        Args:
            stock_id: 股票代號
            indicators: 指標名稱列表
            start_date: 開始日期
            end_date: 結束日期
            force_refresh: 是否強制刷新

        Returns:
            Dict mapping indicator names to data points
        """
        result = {}

        for indicator in indicators:
            try:
                data = self.get_indicator_data(
                    stock_id=stock_id,
                    indicator=indicator,
                    start_date=start_date,
                    end_date=end_date,
                    force_refresh=force_refresh
                )
                result[indicator] = data
            except Exception as e:
                logger.warning(f"Failed to get {indicator} for {stock_id}: {str(e)}")
                result[indicator] = []  # Return empty list on error

        return result

    def sync_indicator_data(
        self,
        stock_id: str,
        indicator: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        """
        同步財務指標數據到數據庫

        用於 Celery 定時任務

        Returns:
            Number of data points synced
        """
        logger.info(f"Syncing {stock_id} - {indicator}")

        try:
            # Force refresh from API
            data_points = self.get_indicator_data(
                stock_id=stock_id,
                indicator=indicator,
                start_date=start_date,
                end_date=end_date,
                force_refresh=True  # Always fetch from API for sync
            )

            logger.info(f"✅ Synced {len(data_points)} points for {stock_id} - {indicator}")
            return len(data_points)

        except ValueError as e:
            # Handle missing data gracefully (stock not found, no data available, etc.)
            error_msg = str(e).lower()
            if "not found" in error_msg or "no data" in error_msg:
                logger.warning(f"⚠️  Skipping {stock_id} - {indicator}: {str(e)}")
                return 0  # Return 0 to indicate no data synced, but don't fail
            else:
                # Re-raise other ValueError types
                logger.error(f"❌ Failed to sync {stock_id} - {indicator}: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"❌ Failed to sync {stock_id} - {indicator}: {str(e)}")
            raise

    def get_coverage_stats(self) -> Dict[str, any]:
        """
        獲取數據庫中財務數據的覆蓋統計

        Returns:
            Dict with statistics about stored data
        """
        stats = {
            'total_stocks': len(self.repo.get_distinct_stock_ids()),
            'total_indicators': len(self.repo.get_distinct_indicators()),
            'indicators_by_stock': {}
        }

        for stock_id in self.repo.get_distinct_stock_ids()[:10]:  # Sample first 10
            indicators = self.repo.get_distinct_indicators(stock_id=stock_id)
            stats['indicators_by_stock'][stock_id] = len(indicators)

        return stats
