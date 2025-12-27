"""
Option Service for option-related business logic
選擇權服務層，處理選擇權相關業務邏輯
"""

from typing import List, Optional, Dict, Any
from datetime import date
from sqlalchemy.orm import Session
from loguru import logger

from app.repositories.option import (
    OptionContractRepository,
    OptionDailyFactorRepository,
    OptionSyncConfigRepository,
    OptionMinutePriceRepository
)
from app.repositories.stock_minute_price import StockMinutePriceRepository
from app.schemas.option import (
    OptionChainResponse,
    OptionChainItem,
    OptionFactorSummary,
    OptionStageInfo,
    OptionSyncStatus
)


class OptionService:
    """Service for option-related operations"""

    def __init__(self, db: Session):
        self.db = db

    # ============ Option Chain ============

    def get_option_chain(
        self,
        underlying_id: str,
        expiry_date: date
    ) -> OptionChainResponse:
        """
        構建 Option Chain

        Args:
            underlying_id: 標的代碼（如 TX）
            expiry_date: 到期日

        Returns:
            OptionChainResponse 包含 CALL 和 PUT 合約列表

        Raises:
            ValueError: 如果找不到合約
        """
        # 獲取該到期日的所有合約
        contracts = OptionContractRepository.get_by_underlying_and_expiry(
            db=self.db,
            underlying_id=underlying_id,
            expiry_date=expiry_date,
            is_active='active'
        )

        if not contracts:
            raise ValueError(
                f"No option contracts found for {underlying_id} expiring on {expiry_date}"
            )

        # 獲取標的現價（從期貨分鐘線數據）
        spot_price = self._get_spot_price(underlying_id)

        # 獲取選擇權合約的價格數據（使用 Repository）
        snapshot_data = self._get_option_prices(contracts)

        # 分離 CALL 和 PUT
        calls, puts = self._build_chain_items(contracts, snapshot_data)

        return OptionChainResponse(
            underlying_id=underlying_id,
            expiry_date=expiry_date,
            spot_price=spot_price,
            calls=sorted(calls, key=lambda x: x.strike_price),
            puts=sorted(puts, key=lambda x: x.strike_price)
        )

    def _get_spot_price(self, underlying_id: str) -> Optional[float]:
        """
        獲取標的現價

        Args:
            underlying_id: 標的代碼（如 TX/MTX）

        Returns:
            現價（如果有）
        """
        try:
            latest_price = StockMinutePriceRepository.get_latest(
                db=self.db,
                stock_id=underlying_id
            )
            if latest_price:
                spot_price = float(latest_price.close)
                logger.info(f"[OPTION] Got spot price for {underlying_id}: {spot_price}")
                return spot_price
            else:
                logger.warning(f"[OPTION] No spot price found for {underlying_id}")
                return None
        except Exception as e:
            logger.error(f"[OPTION] Error getting spot price for {underlying_id}: {str(e)}")
            return None

    def _get_option_prices(self, contracts: List) -> Dict[str, Dict[str, Any]]:
        """
        獲取選擇權合約的價格數據（批次查詢）

        Args:
            contracts: 合約列表

        Returns:
            合約 ID -> 價格數據的字典
        """
        snapshot_data = {}

        try:
            # 提取所有合約 ID
            contract_ids = [c.contract_id for c in contracts]

            # 批次查詢最新價格（使用 Repository，避免 N+1 問題）
            latest_prices = OptionMinutePriceRepository.get_latest_prices_for_contracts(
                db=self.db,
                contract_ids=contract_ids
            )

            # 構建快照數據
            for contract_id, price_record in latest_prices.items():
                if price_record:
                    snapshot_data[contract_id] = {
                        'last_price': float(price_record.close) if price_record.close else None,
                        'bid_price': float(price_record.bid_price) if price_record.bid_price else None,
                        'ask_price': float(price_record.ask_price) if price_record.ask_price else None,
                        'volume': int(price_record.volume) if price_record.volume else None,
                        'open_interest': int(price_record.open_interest) if price_record.open_interest else None
                    }
                    logger.debug(f"[OPTION] Got price data for {contract_id} from minute_prices")
                else:
                    # 沒有分鐘線數據，使用 None（前端會顯示 "-"）
                    snapshot_data[contract_id] = {
                        'last_price': None,
                        'bid_price': None,
                        'ask_price': None,
                        'volume': None,
                        'open_interest': None
                    }

            logger.info(f"[OPTION] Loaded price data for {len(snapshot_data)} contracts")

        except Exception as e:
            logger.error(f"[OPTION] Error getting option prices: {str(e)}")
            # 發生錯誤時，所有合約都使用 None
            for contract in contracts:
                snapshot_data[contract.contract_id] = {
                    'last_price': None,
                    'bid_price': None,
                    'ask_price': None,
                    'volume': None,
                    'open_interest': None
                }

        return snapshot_data

    def _build_chain_items(
        self,
        contracts: List,
        snapshot_data: Dict[str, Dict[str, Any]]
    ) -> tuple[List[OptionChainItem], List[OptionChainItem]]:
        """
        構建 Option Chain 項目列表

        Args:
            contracts: 合約列表
            snapshot_data: 價格快照數據

        Returns:
            (calls, puts) 元組
        """
        calls = []
        puts = []

        for contract in contracts:
            # 從快照數據獲取實時價格（如果有）
            snapshot = snapshot_data.get(contract.contract_id, {})

            chain_item = OptionChainItem(
                contract_id=contract.contract_id,
                option_type=contract.option_type,
                strike_price=contract.strike_price,
                # 從快照獲取實時數據，如果沒有則為 None
                last_price=snapshot.get('last_price'),
                bid_price=snapshot.get('bid_price'),
                ask_price=snapshot.get('ask_price'),
                volume=snapshot.get('volume'),
                open_interest=snapshot.get('open_interest'),
                # Greeks 欄位階段三才實作
                implied_volatility=None,
                delta=None,
                gamma=None,
                theta=None,
                vega=None
            )

            if contract.option_type == 'CALL':
                calls.append(chain_item)
            else:
                puts.append(chain_item)

        return calls, puts

    # ============ Factor Summary ============

    def get_factor_summary(
        self,
        underlying_id: str,
        target_date: Optional[date] = None
    ) -> OptionFactorSummary:
        """
        獲取選擇權因子摘要（含市場情緒）

        Args:
            underlying_id: 標的代碼
            target_date: 目標日期（可選，預設最新）

        Returns:
            OptionFactorSummary

        Raises:
            ValueError: 如果找不到因子數據
        """
        # 獲取因子數據
        if target_date:
            factor = OptionDailyFactorRepository.get_by_key(
                self.db, underlying_id, target_date
            )
        else:
            factor = OptionDailyFactorRepository.get_latest(
                self.db, underlying_id
            )

        if not factor:
            raise ValueError(f"No factor data found for {underlying_id}")

        # 計算市場情緒
        sentiment = self._calculate_sentiment(factor.pcr_volume)

        # 計算總未平倉量
        total_oi = None
        if factor.total_call_oi is not None and factor.total_put_oi is not None:
            total_oi = factor.total_call_oi + factor.total_put_oi

        return OptionFactorSummary(
            underlying_id=factor.underlying_id,
            factor_date=factor.date,  # Model 的 date → Schema 的 factor_date
            pcr_volume=factor.pcr_volume,
            pcr_open_interest=factor.pcr_open_interest,
            atm_iv=factor.atm_iv,
            iv_skew=factor.iv_skew,
            max_pain_strike=factor.max_pain_strike,
            total_oi=total_oi,
            sentiment=sentiment
        )

    def _calculate_sentiment(self, pcr_volume: Optional[float]) -> str:
        """
        計算市場情緒

        Args:
            pcr_volume: Put/Call Ratio (成交量)

        Returns:
            "bullish" | "neutral" | "bearish"
        """
        if not pcr_volume:
            return "neutral"

        pcr = float(pcr_volume)
        if pcr > 1.2:
            return "bearish"  # 看跌情緒重
        elif pcr < 0.8:
            return "bullish"  # 看漲情緒重
        else:
            return "neutral"

    # ============ Stage Info ============

    def get_stage_info(self) -> OptionStageInfo:
        """
        獲取當前階段資訊

        Returns:
            OptionStageInfo
        """
        from app.services.option_calculator import get_available_factors

        stage = OptionSyncConfigRepository.get_current_stage(self.db)
        enabled_underlyings = OptionSyncConfigRepository.get_enabled_underlyings(self.db)
        sync_minute_data = OptionSyncConfigRepository.is_minute_sync_enabled(self.db)
        calculate_greeks = OptionSyncConfigRepository.is_greeks_calculation_enabled(self.db)
        available_factors = get_available_factors(stage)

        return OptionStageInfo(
            stage=stage,
            enabled_underlyings=enabled_underlyings,
            sync_minute_data=sync_minute_data,
            calculate_greeks=calculate_greeks,
            available_factors=list(available_factors.values())
        )

    # ============ Sync Status ============

    def get_sync_status(self) -> List[OptionSyncStatus]:
        """
        獲取選擇權數據同步狀態

        Returns:
            所有啟用標的物的同步狀態列表
        """
        enabled_underlyings = OptionSyncConfigRepository.get_enabled_underlyings(self.db)
        stage = OptionSyncConfigRepository.get_current_stage(self.db)

        status_list = []

        for underlying_id in enabled_underlyings:
            # 獲取最後同步日期
            last_sync_date = OptionDailyFactorRepository.get_latest_date(
                self.db, underlying_id
            )

            # 獲取合約數量
            total_contracts = OptionContractRepository.count(
                self.db, underlying_id=underlying_id
            )
            active_contracts = OptionContractRepository.count(
                self.db, underlying_id=underlying_id, is_active='active'
            )

            # 獲取資料品質
            latest_factor = OptionDailyFactorRepository.get_latest(
                self.db, underlying_id
            )
            data_quality_score = latest_factor.data_quality_score if latest_factor else None

            status_list.append(OptionSyncStatus(
                underlying_id=underlying_id,
                last_sync_date=last_sync_date,
                total_contracts=total_contracts,
                active_contracts=active_contracts,
                data_quality_score=data_quality_score,
                stage=stage
            ))

        return status_list
