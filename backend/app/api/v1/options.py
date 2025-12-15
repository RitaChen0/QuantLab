"""
Option API Endpoints
選擇權 API 端點

提供選擇權相關數據查詢功能：
- 選擇權因子查詢
- 合約列表查詢
- Option Chain 構建
- 市場情緒指標
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.option import (
    OptionContractRepository,
    OptionDailyFactorRepository,
    OptionSyncConfigRepository
)
from app.repositories.stock_minute_price import StockMinutePriceRepository
from app.schemas.option import (
    OptionContract,
    OptionDailyFactor,
    OptionChainResponse,
    OptionFactorSummary,
    OptionStageInfo,
    OptionSyncStatus,
    OptionChainItem
)
from app.core.rate_limit import limiter, RateLimits
from app.utils.logging import api_log
from app.services.shioaji_client import ShioajiClient
from loguru import logger

router = APIRouter(prefix="/options", tags=["Options"])


@router.get("/stage", response_model=OptionStageInfo)
@limiter.limit(RateLimits.GENERAL_READ)
async def get_stage_info(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    獲取當前階段資訊

    返回：
    - 當前階段（1/2/3）
    - 啟用的標的物列表
    - 功能狀態（分鐘線、Greeks）
    - 可用因子列表
    """
    try:
        from app.services.option_calculator import get_available_factors

        stage = OptionSyncConfigRepository.get_current_stage(db)
        enabled_underlyings = OptionSyncConfigRepository.get_enabled_underlyings(db)
        sync_minute_data = OptionSyncConfigRepository.is_minute_sync_enabled(db)
        calculate_greeks = OptionSyncConfigRepository.is_greeks_calculation_enabled(db)
        available_factors = get_available_factors(stage)

        return OptionStageInfo(
            stage=stage,
            enabled_underlyings=enabled_underlyings,
            sync_minute_data=sync_minute_data,
            calculate_greeks=calculate_greeks,
            available_factors=list(available_factors.values())
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stage info: {str(e)}"
        )


@router.get("/contracts", response_model=List[OptionContract])
@limiter.limit(RateLimits.DATA_FETCH)
async def get_contracts(
    request: Request,
    underlying_id: Optional[str] = Query(None, description="標的代碼（如 TX）"),
    option_type: Optional[str] = Query(None, description="選擇權類型（CALL/PUT）"),
    is_active: Optional[str] = Query("active", description="狀態篩選"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查詢選擇權合約列表

    參數：
    - **underlying_id**: 標的代碼（可選）
    - **option_type**: CALL 或 PUT（可選）
    - **is_active**: active/expired/exercised
    - **skip**: 分頁偏移
    - **limit**: 每頁數量（最多 1000）
    """
    try:
        contracts = OptionContractRepository.get_all(
            db=db,
            skip=skip,
            limit=limit,
            underlying_id=underlying_id,
            is_active=is_active,
            option_type=option_type
        )

        api_log.log_operation(
            "read", "option_contracts", underlying_id or "all", current_user.id, success=True
        )

        return contracts

    except Exception as e:
        api_log.log_operation(
            "read", "option_contracts", underlying_id or "all", current_user.id, success=False
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch contracts: {str(e)}"
        )


@router.get("/contracts/{underlying_id}/expiries", response_model=List[date])
@limiter.limit(RateLimits.GENERAL_READ)
async def get_expiry_dates(
    request: Request,
    underlying_id: str,
    is_active: Optional[str] = Query("active", description="狀態篩選"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    獲取標的物的所有到期日

    返回該標的物所有可用的選擇權到期日列表
    """
    try:
        expiry_dates = OptionContractRepository.get_expiry_dates(
            db=db,
            underlying_id=underlying_id,
            is_active=is_active
        )

        return expiry_dates

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch expiry dates: {str(e)}"
        )


@router.get("/chain/{underlying_id}", response_model=OptionChainResponse)
@limiter.limit(RateLimits.DATA_FETCH)
async def get_option_chain(
    request: Request,
    underlying_id: str,
    expiry_date: date = Query(..., description="到期日"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    獲取 Option Chain

    返回指定標的物和到期日的所有選擇權合約（CALL 和 PUT）

    Option Chain 格式：
    - calls: CALL 合約列表（按履約價排序）
    - puts: PUT 合約列表（按履約價排序）
    - spot_price: 標的現價（如有）
    """
    try:
        # 獲取該到期日的所有合約
        contracts = OptionContractRepository.get_by_underlying_and_expiry(
            db=db,
            underlying_id=underlying_id,
            expiry_date=expiry_date,
            is_active='active'
        )

        if not contracts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No option contracts found for {underlying_id} expiring on {expiry_date}"
            )

        # 獲取標的現價（從期貨分鐘線數據）
        spot_price = None
        try:
            # TX/MTX 是期貨，從 stock_minute_prices 獲取最新價格
            latest_price = StockMinutePriceRepository.get_latest(db=db, stock_id=underlying_id)
            if latest_price:
                spot_price = float(latest_price.close)
                logger.info(f"[OPTION] Got spot price for {underlying_id}: {spot_price}")
            else:
                logger.warning(f"[OPTION] No spot price found for {underlying_id}")
        except Exception as e:
            logger.error(f"[OPTION] Error getting spot price for {underlying_id}: {str(e)}")

        # 獲取選擇權合約的價格數據
        # 優先順序：1) option_minute_prices (最新數據) 2) 回退為 None
        snapshot_data = {}

        try:
            # 嘗試從 option_minute_prices 獲取最新價格（階段二數據）
            from app.models.option import OptionMinutePrice

            for contract in contracts:
                try:
                    # 查詢該合約的最新分鐘線數據
                    latest_price = db.query(OptionMinutePrice).filter(
                        OptionMinutePrice.contract_id == contract.contract_id
                    ).order_by(
                        OptionMinutePrice.datetime.desc()
                    ).first()

                    if latest_price:
                        snapshot_data[contract.contract_id] = {
                            'last_price': float(latest_price.close) if latest_price.close else None,
                            'bid_price': float(latest_price.bid_price) if latest_price.bid_price else None,
                            'ask_price': float(latest_price.ask_price) if latest_price.ask_price else None,
                            'volume': int(latest_price.volume) if latest_price.volume else None,
                            'open_interest': int(latest_price.open_interest) if latest_price.open_interest else None
                        }
                        logger.debug(f"[OPTION] Got price data for {contract.contract_id} from minute_prices")
                    else:
                        # 沒有分鐘線數據，使用 None（前端會顯示 "-"）
                        snapshot_data[contract.contract_id] = {
                            'last_price': None,
                            'bid_price': None,
                            'ask_price': None,
                            'volume': None,
                            'open_interest': None
                        }
                except Exception as e:
                    logger.debug(f"[OPTION] Error getting price for {contract.contract_id}: {str(e)}")
                    snapshot_data[contract.contract_id] = {
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

        # 分離 CALL 和 PUT
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

        api_log.log_operation(
            "read", "option_chain", f"{underlying_id}_{expiry_date}", current_user.id, success=True
        )

        return OptionChainResponse(
            underlying_id=underlying_id,
            expiry_date=expiry_date,
            spot_price=spot_price,
            calls=sorted(calls, key=lambda x: x.strike_price),
            puts=sorted(puts, key=lambda x: x.strike_price)
        )

    except HTTPException:
        raise
    except Exception as e:
        api_log.log_operation(
            "read", "option_chain", f"{underlying_id}_{expiry_date}", current_user.id, success=False
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch option chain: {str(e)}"
        )


@router.get("/factors/{underlying_id}", response_model=List[OptionDailyFactor])
@limiter.limit(RateLimits.DATA_FETCH)
async def get_daily_factors(
    request: Request,
    underlying_id: str,
    start_date: Optional[date] = Query(None, description="開始日期"),
    end_date: Optional[date] = Query(None, description="結束日期"),
    limit: int = Query(100, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查詢選擇權每日因子

    返回指定標的物的每日因子數據（PCR、ATM IV 等）

    參數：
    - **underlying_id**: 標的代碼（如 TX）
    - **start_date**: 開始日期（可選）
    - **end_date**: 結束日期（可選）
    - **limit**: 最多返回筆數（預設 100，最多 365）
    """
    try:
        factors = OptionDailyFactorRepository.get_by_underlying(
            db=db,
            underlying_id=underlying_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        api_log.log_operation(
            "read", "option_factors", underlying_id, current_user.id, success=True
        )

        return factors

    except Exception as e:
        api_log.log_operation(
            "read", "option_factors", underlying_id, current_user.id, success=False
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch daily factors: {str(e)}"
        )


@router.get("/factors/{underlying_id}/latest", response_model=OptionDailyFactor)
@limiter.limit(RateLimits.GENERAL_READ)
async def get_latest_factor(
    request: Request,
    underlying_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    獲取最新的選擇權因子

    返回該標的物最新一筆因子數據
    """
    try:
        factor = OptionDailyFactorRepository.get_latest(db, underlying_id)

        if not factor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No factor data found for {underlying_id}"
            )

        return factor

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch latest factor: {str(e)}"
        )


@router.get("/factors/{underlying_id}/summary", response_model=OptionFactorSummary)
@limiter.limit(RateLimits.GENERAL_READ)
async def get_factor_summary(
    request: Request,
    underlying_id: str,
    target_date: Optional[date] = Query(None, description="目標日期（預設為最新）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    獲取選擇權因子摘要（含市場情緒）

    返回：
    - 基礎因子（PCR、ATM IV）
    - 進階因子（IV Skew、Max Pain，如有）
    - 市場情緒指標（基於 PCR 自動判斷）
    """
    try:
        # 獲取因子數據
        if target_date:
            factor = OptionDailyFactorRepository.get_by_key(db, underlying_id, target_date)
        else:
            factor = OptionDailyFactorRepository.get_latest(db, underlying_id)

        if not factor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No factor data found for {underlying_id}"
            )

        # 計算市場情緒
        sentiment = "neutral"
        if factor.pcr_volume:
            pcr = float(factor.pcr_volume)
            if pcr > 1.2:
                sentiment = "bearish"  # 看跌情緒重
            elif pcr < 0.8:
                sentiment = "bullish"  # 看漲情緒重

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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch factor summary: {str(e)}"
        )


@router.get("/sync-status", response_model=List[OptionSyncStatus])
@limiter.limit(RateLimits.GENERAL_READ)
async def get_sync_status(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    獲取選擇權數據同步狀態

    返回所有啟用標的物的同步狀態
    """
    try:
        enabled_underlyings = OptionSyncConfigRepository.get_enabled_underlyings(db)
        stage = OptionSyncConfigRepository.get_current_stage(db)

        status_list = []

        for underlying_id in enabled_underlyings:
            # 獲取最後同步日期
            last_sync_date = OptionDailyFactorRepository.get_latest_date(db, underlying_id)

            # 獲取合約數量
            total_contracts = OptionContractRepository.count(db, underlying_id=underlying_id)
            active_contracts = OptionContractRepository.count(
                db, underlying_id=underlying_id, is_active='active'
            )

            # 獲取資料品質
            latest_factor = OptionDailyFactorRepository.get_latest(db, underlying_id)
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

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch sync status: {str(e)}"
        )
