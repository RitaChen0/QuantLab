"""
Option repository for database operations

提供選擇權資料表的 CRUD 操作，支援三階段演進式架構
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from app.models.option import (
    OptionContract,
    OptionDailyFactor,
    OptionMinutePrice,
    OptionGreeks,
    OptionSyncConfig
)
from app.schemas.option import (
    OptionContractCreate,
    OptionContractUpdate,
    OptionDailyFactorCreate,
    OptionSyncConfigCreate,
    OptionSyncConfigUpdate
)


class OptionContractRepository:
    """Repository for option contract database operations"""

    @staticmethod
    def get_by_id(db: Session, contract_id: str) -> Optional[OptionContract]:
        """Get option contract by contract_id"""
        return db.query(OptionContract).filter(
            OptionContract.contract_id == contract_id
        ).first()

    @staticmethod
    def get_all(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        underlying_id: Optional[str] = None,
        is_active: Optional[str] = None,
        option_type: Optional[str] = None
    ) -> List[OptionContract]:
        """
        Get all option contracts with pagination and filters

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            underlying_id: Filter by underlying
            is_active: Filter by active status
            option_type: Filter by CALL/PUT

        Returns:
            List of option contracts
        """
        query = db.query(OptionContract)

        if underlying_id:
            query = query.filter(OptionContract.underlying_id == underlying_id)

        if is_active:
            query = query.filter(OptionContract.is_active == is_active)

        if option_type:
            query = query.filter(OptionContract.option_type == option_type)

        return query.order_by(
            OptionContract.expiry_date.desc(),
            OptionContract.strike_price.asc()
        ).offset(skip).limit(limit).all()

    @staticmethod
    def get_by_underlying_and_expiry(
        db: Session,
        underlying_id: str,
        expiry_date: date,
        is_active: Optional[str] = 'active'
    ) -> List[OptionContract]:
        """
        Get all option contracts for specific underlying and expiry date

        用於建構 Option Chain
        """
        query = db.query(OptionContract).filter(
            and_(
                OptionContract.underlying_id == underlying_id,
                OptionContract.expiry_date == expiry_date
            )
        )

        if is_active:
            query = query.filter(OptionContract.is_active == is_active)

        return query.order_by(
            OptionContract.strike_price.asc(),
            OptionContract.option_type.asc()
        ).all()

    @staticmethod
    def get_expiry_dates(
        db: Session,
        underlying_id: str,
        is_active: Optional[str] = 'active'
    ) -> List[date]:
        """Get all expiry dates for specific underlying"""
        query = db.query(OptionContract.expiry_date).distinct().filter(
            OptionContract.underlying_id == underlying_id
        )

        if is_active:
            query = query.filter(OptionContract.is_active == is_active)

        results = query.order_by(OptionContract.expiry_date.asc()).all()
        return [r[0] for r in results]

    @staticmethod
    def count(
        db: Session,
        underlying_id: Optional[str] = None,
        is_active: Optional[str] = None
    ) -> int:
        """Count option contracts"""
        query = db.query(OptionContract)

        if underlying_id:
            query = query.filter(OptionContract.underlying_id == underlying_id)

        if is_active:
            query = query.filter(OptionContract.is_active == is_active)

        return query.count()

    @staticmethod
    def create(db: Session, contract: OptionContractCreate) -> OptionContract:
        """Create new option contract"""
        db_contract = OptionContract(**contract.model_dump())
        db.add(db_contract)
        db.commit()
        db.refresh(db_contract)
        return db_contract

    @staticmethod
    def create_bulk(
        db: Session,
        contracts: List[OptionContractCreate]
    ) -> List[OptionContract]:
        """Bulk create option contracts"""
        db_contracts = [
            OptionContract(**contract.model_dump())
            for contract in contracts
        ]
        db.add_all(db_contracts)
        db.commit()
        for contract in db_contracts:
            db.refresh(contract)
        return db_contracts

    @staticmethod
    def update(
        db: Session,
        contract_id: str,
        contract_update: OptionContractUpdate
    ) -> Optional[OptionContract]:
        """Update option contract"""
        db_contract = OptionContractRepository.get_by_id(db, contract_id)
        if not db_contract:
            return None

        update_data = contract_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_contract, field, value)

        db_contract.updated_at = func.now()
        db.commit()
        db.refresh(db_contract)
        return db_contract

    @staticmethod
    def delete(db: Session, contract_id: str) -> bool:
        """Delete option contract"""
        db_contract = OptionContractRepository.get_by_id(db, contract_id)
        if not db_contract:
            return False

        db.delete(db_contract)
        db.commit()
        return True

    @staticmethod
    def mark_expired(
        db: Session,
        expiry_date: date,
        settlement_price: Optional[float] = None
    ) -> int:
        """
        Mark contracts as expired

        Args:
            expiry_date: 到期日
            settlement_price: 結算價格（可選）

        Returns:
            Number of contracts marked as expired
        """
        update_data = {'is_active': 'expired'}
        if settlement_price is not None:
            update_data['settlement_price'] = settlement_price

        result = db.query(OptionContract).filter(
            and_(
                OptionContract.expiry_date == expiry_date,
                OptionContract.is_active == 'active'
            )
        ).update(update_data)

        db.commit()
        return result


class OptionDailyFactorRepository:
    """Repository for option daily factor database operations"""

    @staticmethod
    def get_by_key(
        db: Session,
        underlying_id: str,
        date: date
    ) -> Optional[OptionDailyFactor]:
        """Get option daily factor by composite key"""
        return db.query(OptionDailyFactor).filter(
            and_(
                OptionDailyFactor.underlying_id == underlying_id,
                OptionDailyFactor.date == date
            )
        ).first()

    @staticmethod
    def get_by_underlying(
        db: Session,
        underlying_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100
    ) -> List[OptionDailyFactor]:
        """
        Get option daily factors for specific underlying

        Args:
            db: Database session
            underlying_id: 標的物代碼
            start_date: 開始日期
            end_date: 結束日期
            limit: 最大記錄數
        """
        query = db.query(OptionDailyFactor).filter(
            OptionDailyFactor.underlying_id == underlying_id
        )

        if start_date:
            query = query.filter(OptionDailyFactor.date >= start_date)

        if end_date:
            query = query.filter(OptionDailyFactor.date <= end_date)

        return query.order_by(
            OptionDailyFactor.date.desc()
        ).limit(limit).all()

    @staticmethod
    def get_by_date_range(
        db: Session,
        start_date: date,
        end_date: date,
        underlying_ids: Optional[List[str]] = None
    ) -> List[OptionDailyFactor]:
        """Get option daily factors within date range"""
        query = db.query(OptionDailyFactor).filter(
            and_(
                OptionDailyFactor.date >= start_date,
                OptionDailyFactor.date <= end_date
            )
        )

        if underlying_ids:
            query = query.filter(
                OptionDailyFactor.underlying_id.in_(underlying_ids)
            )

        return query.order_by(
            OptionDailyFactor.date.desc(),
            OptionDailyFactor.underlying_id.asc()
        ).all()

    @staticmethod
    def get_latest(
        db: Session,
        underlying_id: str
    ) -> Optional[OptionDailyFactor]:
        """Get latest option daily factor for underlying"""
        return db.query(OptionDailyFactor).filter(
            OptionDailyFactor.underlying_id == underlying_id
        ).order_by(
            OptionDailyFactor.date.desc()
        ).first()

    @staticmethod
    def get_latest_date(
        db: Session,
        underlying_id: str
    ) -> Optional[date]:
        """Get latest date for underlying"""
        result = db.query(
            func.max(OptionDailyFactor.date)
        ).filter(
            OptionDailyFactor.underlying_id == underlying_id
        ).scalar()
        return result

    @staticmethod
    def create(
        db: Session,
        factor: OptionDailyFactorCreate
    ) -> OptionDailyFactor:
        """Create new option daily factor"""
        db_factor = OptionDailyFactor(**factor.model_dump())
        db.add(db_factor)
        db.commit()
        db.refresh(db_factor)
        return db_factor

    @staticmethod
    def create_bulk(
        db: Session,
        factors: List[OptionDailyFactorCreate]
    ) -> List[OptionDailyFactor]:
        """Bulk create option daily factors"""
        db_factors = [
            OptionDailyFactor(**factor.model_dump())
            for factor in factors
        ]
        db.add_all(db_factors)
        db.commit()
        for factor in db_factors:
            db.refresh(factor)
        return db_factors

    @staticmethod
    def upsert(
        db: Session,
        factor: OptionDailyFactorCreate
    ) -> OptionDailyFactor:
        """
        Insert or update option daily factor

        如果記錄已存在，更新；否則創建
        """
        db_factor = OptionDailyFactorRepository.get_by_key(
            db,
            factor.underlying_id,
            factor.date
        )

        if db_factor:
            # Update existing record
            update_data = factor.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                if field not in ['underlying_id', 'date']:  # Skip primary keys
                    setattr(db_factor, field, value)
            db.commit()
            db.refresh(db_factor)
        else:
            # Create new record
            db_factor = OptionDailyFactor(**factor.model_dump())
            db.add(db_factor)
            db.commit()
            db.refresh(db_factor)

        return db_factor

    @staticmethod
    def delete_by_date_range(
        db: Session,
        underlying_id: str,
        start_date: date,
        end_date: date
    ) -> int:
        """Delete option daily factors within date range"""
        result = db.query(OptionDailyFactor).filter(
            and_(
                OptionDailyFactor.underlying_id == underlying_id,
                OptionDailyFactor.date >= start_date,
                OptionDailyFactor.date <= end_date
            )
        ).delete()

        db.commit()
        return result


class OptionSyncConfigRepository:
    """Repository for option sync config database operations"""

    @staticmethod
    def get_by_key(db: Session, key: str) -> Optional[OptionSyncConfig]:
        """Get config by key"""
        return db.query(OptionSyncConfig).filter(
            OptionSyncConfig.key == key
        ).first()

    @staticmethod
    def get_all(db: Session) -> List[OptionSyncConfig]:
        """Get all config entries"""
        return db.query(OptionSyncConfig).order_by(
            OptionSyncConfig.key.asc()
        ).all()

    @staticmethod
    def get_all_as_dict(db: Session) -> Dict[str, str]:
        """Get all config as dictionary"""
        configs = OptionSyncConfigRepository.get_all(db)
        return {config.key: config.value for config in configs}

    @staticmethod
    def create(
        db: Session,
        config: OptionSyncConfigCreate
    ) -> OptionSyncConfig:
        """Create new config entry"""
        db_config = OptionSyncConfig(**config.model_dump())
        db.add(db_config)
        db.commit()
        db.refresh(db_config)
        return db_config

    @staticmethod
    def update(
        db: Session,
        key: str,
        config_update: OptionSyncConfigUpdate
    ) -> Optional[OptionSyncConfig]:
        """Update config entry"""
        db_config = OptionSyncConfigRepository.get_by_key(db, key)
        if not db_config:
            return None

        update_data = config_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_config, field, value)

        db_config.updated_at = func.now()
        db.commit()
        db.refresh(db_config)
        return db_config

    @staticmethod
    def upsert(
        db: Session,
        key: str,
        value: str,
        description: Optional[str] = None
    ) -> OptionSyncConfig:
        """Insert or update config entry"""
        db_config = OptionSyncConfigRepository.get_by_key(db, key)

        if db_config:
            db_config.value = value
            if description is not None:
                db_config.description = description
            db_config.updated_at = func.now()
            db.commit()
            db.refresh(db_config)
        else:
            db_config = OptionSyncConfig(
                key=key,
                value=value,
                description=description
            )
            db.add(db_config)
            db.commit()
            db.refresh(db_config)

        return db_config

    @staticmethod
    def delete(db: Session, key: str) -> bool:
        """Delete config entry"""
        db_config = OptionSyncConfigRepository.get_by_key(db, key)
        if not db_config:
            return False

        db.delete(db_config)
        db.commit()
        return True

    @staticmethod
    def get_current_stage(db: Session) -> int:
        """Get current stage (1/2/3)"""
        config = OptionSyncConfigRepository.get_by_key(db, 'stage')
        return int(config.value) if config and config.value else 1

    @staticmethod
    def get_enabled_underlyings(db: Session) -> List[str]:
        """Get list of enabled underlyings"""
        config = OptionSyncConfigRepository.get_by_key(db, 'enabled_underlyings')
        if not config or not config.value:
            return []
        return [s.strip() for s in config.value.split(',') if s.strip()]

    @staticmethod
    def is_minute_sync_enabled(db: Session) -> bool:
        """Check if minute data sync is enabled"""
        config = OptionSyncConfigRepository.get_by_key(db, 'sync_minute_data')
        return config and config.value and config.value.lower() == 'true'

    @staticmethod
    def is_greeks_calculation_enabled(db: Session) -> bool:
        """Check if Greeks calculation is enabled"""
        config = OptionSyncConfigRepository.get_by_key(db, 'calculate_greeks')
        return config and config.value and config.value.lower() == 'true'
