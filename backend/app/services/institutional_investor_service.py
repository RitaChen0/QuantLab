"""
Institutional Investor Service
法人買賣超業務邏輯層
"""

from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from loguru import logger
import pandas as pd

from app.repositories.institutional_investor import InstitutionalInvestorRepository
from app.services.finmind_client import FinMindClient
from app.schemas.institutional_investor import (
    InstitutionalInvestorCreate,
    InstitutionalInvestorResponse,
    InstitutionalInvestorSummary,
    InstitutionalInvestorStats,
    InvestorType
)


class InstitutionalInvestorService:
    """法人買賣超服務"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = InstitutionalInvestorRepository()
        self.finmind_client = FinMindClient()

    def sync_stock_data(
        self,
        stock_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        同步指定股票的法人買賣超數據

        Args:
            stock_id: 股票代碼
            start_date: 開始日期 (YYYY-MM-DD)，默認最新數據日期的下一天
            end_date: 結束日期 (YYYY-MM-DD)，默認今天
            force: 是否強制重新同步（覆蓋現有數據）

        Returns:
            同步結果統計
        """
        try:
            # 如果沒有指定開始日期，使用最新數據日期的下一天
            if not start_date:
                latest_date = self.repo.get_latest_date(self.db, stock_id)
                if latest_date and not force:
                    start_date = (latest_date + timedelta(days=1)).strftime('%Y-%m-%d')
                else:
                    # 默認同步最近 30 天
                    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')

            logger.info(f"Syncing institutional investor data for {stock_id}: {start_date} ~ {end_date}")

            # 從 FinMind API 獲取數據
            df = self.finmind_client.get_institutional_investors(
                stock_id=stock_id,
                start_date=start_date,
                end_date=end_date
            )

            if df.empty:
                logger.warning(f"No data found for {stock_id}")
                return {
                    "stock_id": stock_id,
                    "status": "no_data",
                    "inserted": 0,
                    "updated": 0,
                    "errors": 0
                }

            # 轉換為內部格式並儲存
            inserted = 0
            updated = 0
            errors = 0

            for _, row in df.iterrows():
                try:
                    data = InstitutionalInvestorCreate(
                        date=pd.to_datetime(row['date']).date(),
                        stock_id=row['stock_id'],
                        investor_type=row['name'],
                        buy_volume=int(row['buy']),
                        sell_volume=int(row['sell'])
                    )

                    # 直接使用 upsert（repository 會處理新增或更新）
                    # 簡單起見，統計為inserted
                    self.repo.upsert(self.db, data)
                    inserted += 1

                except Exception as e:
                    logger.error(f"Error inserting record: {e}")
                    errors += 1

            logger.info(
                f"Sync completed for {stock_id}: "
                f"inserted={inserted}, updated={updated}, errors={errors}"
            )

            return {
                "stock_id": stock_id,
                "status": "success",
                "period": f"{start_date} ~ {end_date}",
                "inserted": inserted,
                "updated": updated,
                "errors": errors,
                "total": inserted + updated
            }

        except Exception as e:
            logger.error(f"Failed to sync {stock_id}: {str(e)}")
            return {
                "stock_id": stock_id,
                "status": "error",
                "error": str(e),
                "inserted": 0,
                "updated": 0,
                "errors": 1
            }

    def sync_multiple_stocks(
        self,
        stock_ids: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """批量同步多個股票的法人買賣超數據"""
        results = []
        total_inserted = 0
        total_updated = 0
        total_errors = 0

        for stock_id in stock_ids:
            result = self.sync_stock_data(stock_id, start_date, end_date, force)
            results.append(result)
            total_inserted += result.get("inserted", 0)
            total_updated += result.get("updated", 0)
            total_errors += result.get("errors", 0)

        return {
            "status": "completed",
            "total_stocks": len(stock_ids),
            "total_inserted": total_inserted,
            "total_updated": total_updated,
            "total_errors": total_errors,
            "results": results
        }

    def get_stock_data(
        self,
        stock_id: str,
        start_date: date,
        end_date: date,
        investor_type: Optional[InvestorType] = None
    ) -> List[InstitutionalInvestorResponse]:
        """查詢股票的法人買賣超數據"""
        records = self.repo.get_by_stock_date_range(
            self.db, stock_id, start_date, end_date, investor_type
        )
        return [InstitutionalInvestorResponse.model_validate(r) for r in records]

    def get_summary(
        self,
        stock_id: str,
        target_date: date
    ) -> InstitutionalInvestorSummary:
        """獲取指定日期的法人買賣超摘要"""
        summary = self.repo.get_summary_by_date(self.db, stock_id, target_date)
        return InstitutionalInvestorSummary(**summary)

    def get_stats(
        self,
        stock_id: str,
        investor_type: InvestorType,
        start_date: date,
        end_date: date
    ) -> Optional[InstitutionalInvestorStats]:
        """獲取統計數據"""
        stats = self.repo.get_stats(
            self.db, stock_id, investor_type, start_date, end_date
        )
        if stats:
            return InstitutionalInvestorStats(**stats)
        return None

    def get_top_stocks(
        self,
        target_date: date,
        investor_type: InvestorType,
        limit: int = 50,
        order: str = "desc"
    ) -> List[InstitutionalInvestorResponse]:
        """獲取買賣超排行"""
        records = self.repo.get_top_stocks_by_net(
            self.db,
            target_date,
            investor_type,
            limit,
            ascending=(order == "asc")
        )
        return [InstitutionalInvestorResponse.model_validate(r) for r in records]

    def get_latest_date(self, stock_id: Optional[str] = None) -> Optional[date]:
        """獲取最新數據日期"""
        return self.repo.get_latest_date(self.db, stock_id)

    def get_foreign_net_series(
        self,
        stock_id: str,
        start_date: date,
        end_date: date
    ) -> pd.DataFrame:
        """
        獲取外資買賣超時間序列
        返回 DataFrame 格式，方便策略使用
        """
        records = self.repo.get_by_stock_date_range(
            self.db,
            stock_id,
            start_date,
            end_date,
            InvestorType.FOREIGN_INVESTOR
        )

        if not records:
            return pd.DataFrame(columns=['date', 'foreign_net'])

        data = [
            {
                'date': r.date,
                'foreign_net': r.net_buy_sell or 0
            }
            for r in records
        ]

        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()

        return df

    def delete_old_data(self, days_to_keep: int = 365) -> int:
        """刪除舊數據（保留最近 N 天）"""
        cutoff_date = datetime.now().date() - timedelta(days=days_to_keep)
        start_date = date(2000, 1, 1)

        count = self.repo.delete_by_date_range(self.db, start_date, cutoff_date)
        logger.info(f"Deleted {count} old records before {cutoff_date}")

        return count
