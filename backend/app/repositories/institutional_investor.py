"""
Institutional Investor Repository
法人買賣超資料的資料庫存取層
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta

from app.models.institutional_investor import InstitutionalInvestor
from app.schemas.institutional_investor import (
    InstitutionalInvestorCreate,
    InstitutionalInvestorUpdate,
    InvestorType
)


class InstitutionalInvestorRepository:
    """法人買賣超 Repository"""

    @staticmethod
    def create(db: Session, data: InstitutionalInvestorCreate) -> InstitutionalInvestor:
        """創建單筆法人買賣超記錄"""
        db_obj = InstitutionalInvestor(**data.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    @staticmethod
    def create_bulk(db: Session, records: List[InstitutionalInvestorCreate]) -> int:
        """批量創建法人買賣超記錄"""
        db_objs = [InstitutionalInvestor(**record.model_dump()) for record in records]
        db.bulk_save_objects(db_objs)
        db.commit()
        return len(db_objs)

    @staticmethod
    def upsert(
        db: Session,
        data: InstitutionalInvestorCreate
    ) -> InstitutionalInvestor:
        """Upsert：如果存在則更新，否則創建"""
        existing = db.query(InstitutionalInvestor).filter(
            and_(
                InstitutionalInvestor.date == data.date,
                InstitutionalInvestor.stock_id == data.stock_id,
                InstitutionalInvestor.investor_type == data.investor_type
            )
        ).first()

        if existing:
            # 更新現有記錄
            existing.buy_volume = data.buy_volume
            existing.sell_volume = data.sell_volume
            existing.updated_at = datetime.now()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # 創建新記錄
            return InstitutionalInvestorRepository.create(db, data)

    @staticmethod
    def get_by_id(db: Session, record_id: int) -> Optional[InstitutionalInvestor]:
        """根據 ID 查詢"""
        return db.query(InstitutionalInvestor).filter(
            InstitutionalInvestor.id == record_id
        ).first()

    @staticmethod
    def get_by_stock_and_date(
        db: Session,
        stock_id: str,
        date: date,
        investor_type: Optional[InvestorType] = None
    ) -> List[InstitutionalInvestor]:
        """查詢指定股票和日期的法人買賣超"""
        query = db.query(InstitutionalInvestor).filter(
            and_(
                InstitutionalInvestor.stock_id == stock_id,
                InstitutionalInvestor.date == date
            )
        )

        if investor_type:
            query = query.filter(InstitutionalInvestor.investor_type == investor_type)

        return query.all()

    @staticmethod
    def get_by_stock_date_range(
        db: Session,
        stock_id: str,
        start_date: date,
        end_date: date,
        investor_type: Optional[InvestorType] = None
    ) -> List[InstitutionalInvestor]:
        """查詢指定股票和日期範圍的法人買賣超"""
        query = db.query(InstitutionalInvestor).filter(
            and_(
                InstitutionalInvestor.stock_id == stock_id,
                InstitutionalInvestor.date >= start_date,
                InstitutionalInvestor.date <= end_date
            )
        )

        if investor_type:
            query = query.filter(InstitutionalInvestor.investor_type == investor_type)

        return query.order_by(InstitutionalInvestor.date).all()

    @staticmethod
    def get_by_date_range(
        db: Session,
        start_date: date,
        end_date: date,
        stock_ids: Optional[List[str]] = None,
        investor_type: Optional[InvestorType] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[InstitutionalInvestor]:
        """查詢日期範圍內的法人買賣超"""
        query = db.query(InstitutionalInvestor).filter(
            and_(
                InstitutionalInvestor.date >= start_date,
                InstitutionalInvestor.date <= end_date
            )
        )

        if stock_ids:
            query = query.filter(InstitutionalInvestor.stock_id.in_(stock_ids))

        if investor_type:
            query = query.filter(InstitutionalInvestor.investor_type == investor_type)

        return query.order_by(
            InstitutionalInvestor.date.desc(),
            InstitutionalInvestor.stock_id
        ).limit(limit).offset(offset).all()

    @staticmethod
    def get_latest_date(db: Session, stock_id: Optional[str] = None) -> Optional[date]:
        """獲取最新數據日期"""
        query = db.query(func.max(InstitutionalInvestor.date))

        if stock_id:
            query = query.filter(InstitutionalInvestor.stock_id == stock_id)

        result = query.scalar()
        return result

    @staticmethod
    def get_summary_by_date(
        db: Session,
        stock_id: str,
        target_date: date
    ) -> Dict[str, Any]:
        """獲取指定日期的法人買賣超摘要"""
        records = InstitutionalInvestorRepository.get_by_stock_and_date(
            db, stock_id, target_date
        )

        summary = {
            "date": target_date,
            "stock_id": stock_id,
            "foreign_net": 0,
            "trust_net": 0,
            "dealer_self_net": 0,
            "dealer_hedging_net": 0,
            "total_net": 0
        }

        for record in records:
            net = record.net_buy_sell or 0
            if record.investor_type == InvestorType.FOREIGN_INVESTOR:
                summary["foreign_net"] = net
            elif record.investor_type == InvestorType.INVESTMENT_TRUST:
                summary["trust_net"] = net
            elif record.investor_type == InvestorType.DEALER_SELF:
                summary["dealer_self_net"] = net
            elif record.investor_type == InvestorType.DEALER_HEDGING:
                summary["dealer_hedging_net"] = net

        summary["total_net"] = (
            summary["foreign_net"] +
            summary["trust_net"] +
            summary["dealer_self_net"] +
            summary["dealer_hedging_net"]
        )

        return summary

    @staticmethod
    def get_stats(
        db: Session,
        stock_id: str,
        investor_type: InvestorType,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """獲取統計數據"""
        records = InstitutionalInvestorRepository.get_by_stock_date_range(
            db, stock_id, start_date, end_date, investor_type
        )

        if not records:
            return None

        total_buy = sum(r.buy_volume for r in records)
        total_sell = sum(r.sell_volume for r in records)
        total_net = sum(r.net_buy_sell or 0 for r in records)
        buy_days = sum(1 for r in records if (r.net_buy_sell or 0) > 0)
        sell_days = sum(1 for r in records if (r.net_buy_sell or 0) < 0)
        days_count = len(records)

        return {
            "stock_id": stock_id,
            "investor_type": investor_type,
            "period_start": start_date,
            "period_end": end_date,
            "total_buy": total_buy,
            "total_sell": total_sell,
            "total_net": total_net,
            "avg_daily_net": total_net / days_count if days_count > 0 else 0,
            "buy_days": buy_days,
            "sell_days": sell_days
        }

    @staticmethod
    def delete_by_date_range(
        db: Session,
        start_date: date,
        end_date: date,
        stock_id: Optional[str] = None
    ) -> int:
        """刪除指定日期範圍的記錄"""
        query = db.query(InstitutionalInvestor).filter(
            and_(
                InstitutionalInvestor.date >= start_date,
                InstitutionalInvestor.date <= end_date
            )
        )

        if stock_id:
            query = query.filter(InstitutionalInvestor.stock_id == stock_id)

        count = query.delete()
        db.commit()
        return count

    @staticmethod
    def get_top_stocks_by_net(
        db: Session,
        target_date: date,
        investor_type: InvestorType,
        limit: int = 50,
        ascending: bool = False
    ) -> List[InstitutionalInvestor]:
        """獲取指定日期買賣超排行"""
        query = db.query(InstitutionalInvestor).filter(
            and_(
                InstitutionalInvestor.date == target_date,
                InstitutionalInvestor.investor_type == investor_type
            )
        )

        if ascending:
            query = query.order_by(InstitutionalInvestor.net_buy_sell)
        else:
            query = query.order_by(desc(InstitutionalInvestor.net_buy_sell))

        return query.limit(limit).all()
