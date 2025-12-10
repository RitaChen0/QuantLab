"""
Trade repository for database operations
"""

from typing import Optional, List
from datetime import date as DateType
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from app.models.trade import Trade, TradeAction
from app.schemas.trade import TradeCreate, TradeUpdate


class TradeRepository:
    """Repository for trade database operations"""

    @staticmethod
    def get_by_id(db: Session, trade_id: int) -> Optional[Trade]:
        """Get trade by ID"""
        return db.query(Trade).filter(Trade.id == trade_id).first()

    @staticmethod
    def get_by_backtest(
        db: Session,
        backtest_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Trade]:
        """
        Get trades by backtest

        Args:
            db: Database session
            backtest_id: Backtest ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of trades
        """
        return (
            db.query(Trade)
            .filter(Trade.backtest_id == backtest_id)
            .order_by(Trade.trade_date, Trade.id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_stock(
        db: Session,
        backtest_id: int,
        stock_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Trade]:
        """
        Get trades for a specific stock in a backtest

        Args:
            db: Database session
            backtest_id: Backtest ID
            stock_id: Stock ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of trades
        """
        return (
            db.query(Trade)
            .filter(
                and_(
                    Trade.backtest_id == backtest_id,
                    Trade.stock_id == stock_id
                )
            )
            .order_by(Trade.trade_date, Trade.id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_action(
        db: Session,
        backtest_id: int,
        action: TradeAction,
        skip: int = 0,
        limit: int = 100
    ) -> List[Trade]:
        """
        Get trades by action type (buy/sell)

        Args:
            db: Database session
            backtest_id: Backtest ID
            action: Trade action (buy or sell)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of trades
        """
        return (
            db.query(Trade)
            .filter(
                and_(
                    Trade.backtest_id == backtest_id,
                    Trade.action == action
                )
            )
            .order_by(Trade.trade_date, Trade.id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_date_range(
        db: Session,
        backtest_id: int,
        start_date: DateType,
        end_date: DateType
    ) -> List[Trade]:
        """
        Get trades within a date range

        Args:
            db: Database session
            backtest_id: Backtest ID
            start_date: Start date
            end_date: End date

        Returns:
            List of trades
        """
        return (
            db.query(Trade)
            .filter(
                and_(
                    Trade.backtest_id == backtest_id,
                    Trade.trade_date >= start_date,
                    Trade.trade_date <= end_date
                )
            )
            .order_by(Trade.trade_date, Trade.id)
            .all()
        )

    @staticmethod
    def count_by_backtest(db: Session, backtest_id: int) -> int:
        """Count trades by backtest"""
        return db.query(Trade).filter(Trade.backtest_id == backtest_id).count()

    @staticmethod
    def get_summary(db: Session, backtest_id: int) -> dict:
        """
        Get trade summary statistics for a backtest

        Args:
            db: Database session
            backtest_id: Backtest ID

        Returns:
            Dictionary with summary statistics
        """
        trades = db.query(Trade).filter(Trade.backtest_id == backtest_id).all()

        if not trades:
            return {
                "total_trades": 0,
                "buy_trades": 0,
                "sell_trades": 0,
                "total_quantity": 0,
                "total_commission": Decimal("0"),
                "total_tax": Decimal("0"),
                "total_value": Decimal("0"),
            }

        buy_trades = [t for t in trades if t.action == TradeAction.BUY]
        sell_trades = [t for t in trades if t.action == TradeAction.SELL]

        return {
            "total_trades": len(trades),
            "buy_trades": len(buy_trades),
            "sell_trades": len(sell_trades),
            "total_quantity": sum(t.quantity for t in trades),
            "total_commission": sum(t.commission for t in trades),
            "total_tax": sum(t.tax for t in trades),
            "total_value": sum(t.price * t.quantity for t in trades),
        }

    @staticmethod
    def create(
        db: Session,
        backtest_id: int,
        trade_create: TradeCreate
    ) -> Trade:
        """
        Create new trade

        Args:
            db: Database session
            backtest_id: Backtest ID
            trade_create: Trade creation data

        Returns:
            Created trade object
        """
        db_trade = Trade(
            backtest_id=backtest_id,
            stock_id=trade_create.stock_id,
            action=trade_create.action,
            quantity=trade_create.quantity,
            price=trade_create.price,
            commission=trade_create.commission,
            tax=trade_create.tax,
            trade_date=trade_create.trade_date,
        )

        db.add(db_trade)
        db.commit()
        db.refresh(db_trade)

        return db_trade

    @staticmethod
    def create_bulk(
        db: Session,
        backtest_id: int,
        trades: List[TradeCreate]
    ) -> int:
        """
        Bulk create trades

        Args:
            db: Database session
            backtest_id: Backtest ID
            trades: List of trade creation data

        Returns:
            Number of records created
        """
        db_trades = [
            Trade(
                backtest_id=backtest_id,
                stock_id=trade.stock_id,
                action=trade.action,
                quantity=trade.quantity,
                price=trade.price,
                commission=trade.commission,
                tax=trade.tax,
                trade_date=trade.trade_date,
            )
            for trade in trades
        ]

        db.bulk_save_objects(db_trades)
        db.commit()

        return len(db_trades)

    @staticmethod
    def update(
        db: Session,
        trade: Trade,
        trade_update: TradeUpdate
    ) -> Trade:
        """
        Update trade

        Args:
            db: Database session
            trade: Existing trade object
            trade_update: Update data

        Returns:
            Updated trade object
        """
        update_data = trade_update.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(trade, field, value)

        db.add(trade)
        db.commit()
        db.refresh(trade)

        return trade

    @staticmethod
    def delete(db: Session, trade: Trade) -> None:
        """
        Delete trade

        Args:
            db: Database session
            trade: Trade to delete
        """
        db.delete(trade)
        db.commit()

    @staticmethod
    def delete_by_backtest(db: Session, backtest_id: int) -> int:
        """
        Delete all trades for a backtest

        Args:
            db: Database session
            backtest_id: Backtest ID

        Returns:
            Number of records deleted
        """
        count = db.query(Trade).filter(Trade.backtest_id == backtest_id).delete()
        db.commit()
        return count

    @staticmethod
    def get_latest(db: Session, backtest_id: int, limit: int = 10) -> List[Trade]:
        """
        Get latest trades for a backtest

        Args:
            db: Database session
            backtest_id: Backtest ID
            limit: Maximum number of records to return

        Returns:
            List of latest trades
        """
        return (
            db.query(Trade)
            .filter(Trade.backtest_id == backtest_id)
            .order_by(desc(Trade.trade_date), desc(Trade.id))
            .limit(limit)
            .all()
        )
