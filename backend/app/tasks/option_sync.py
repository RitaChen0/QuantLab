"""
Celery tasks for option data synchronization

選擇權資料同步任務，支援三階段演進式架構：
- 階段一：每日聚合因子同步（PCR, ATM IV）
- 階段二：分鐘線同步
- 階段三：Greeks 計算
"""

from celery import Task
from app.core.celery_app import celery_app
from app.utils.task_history import record_task_history
from app.utils.task_deduplication import skip_if_recently_executed
from app.db.session import get_db
from loguru import logger
from datetime import datetime, timezone, date, timedelta
from typing import List, Optional

from app.services.shioaji_client import ShioajiClient
from app.services.option_data_source import ShioajiOptionDataSource
from app.services.option_calculator import OptionFactorCalculator
from app.repositories.option import (
    OptionDailyFactorRepository,
    OptionSyncConfigRepository,
    OptionContractRepository
)
from app.schemas.option import OptionDailyFactorCreate


@celery_app.task(
    bind=True,
    name="app.tasks.sync_option_daily_factors",
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
@skip_if_recently_executed(min_interval_hours=24)
@record_task_history
def sync_option_daily_factors(
    self: Task,
    underlying_ids: Optional[List[str]] = None,
    target_date: Optional[str] = None
) -> dict:
    """
    同步選擇權每日聚合因子（階段一主任務）

    執行流程：
    1. 檢查當前階段配置
    2. 獲取啟用的標的物列表
    3. 使用 Shioaji API 獲取選擇權鏈數據
    4. 計算每日因子
    5. 儲存到 option_daily_factors 表

    Args:
        underlying_ids: 標的代碼列表（None 表示使用配置）
        target_date: 目標日期（YYYY-MM-DD，預設為今天）

    Returns:
        Task result with sync statistics
    """
    start_time = datetime.now(timezone.utc)

    try:
        logger.info(
            f"[OPTION] 🚀 Starting option daily factors synchronization "
            f"(task_id: {self.request.id})"
        )

        # 解析目標日期
        try:
            if target_date:
                sync_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            else:
                from app.utils.timezone_helpers import today_taiwan
                sync_date = today_taiwan()
        except ValueError as e:
            logger.error(f"[OPTION] ❌ Invalid date format: {target_date}. Expected YYYY-MM-DD")
            return {
                "status": "error",
                "message": f"Invalid date format: {target_date}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        logger.info(f"[OPTION] 📅 Sync date: {sync_date}")

        # 獲取資料庫連接
        try:
            db = next(get_db())
        except Exception as e:
            logger.error(
                f"[OPTION] ❌ Failed to get database connection: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            raise self.retry(exc=e, countdown=60)

        # 獲取當前階段配置
        try:
            stage = OptionSyncConfigRepository.get_current_stage(db)
            logger.info(f"[OPTION] 📈 Current stage: {stage}")
        except Exception as e:
            logger.warning(
                f"[OPTION] ⚠️  Failed to get stage config, defaulting to stage 1: {str(e)}"
            )
            stage = 1

        # 獲取啟用的標的物列表
        if not underlying_ids:
            try:
                underlying_ids = OptionSyncConfigRepository.get_enabled_underlyings(db)
            except Exception as e:
                logger.warning(
                    f"[OPTION] ⚠️  Failed to get enabled underlyings: {str(e)}"
                )
                underlying_ids = []

        if not underlying_ids:
            logger.warning("[OPTION] ⚠️  No underlyings configured. Using default: TX only (MTX has no options)")
            underlying_ids = ['TX']  # MTX (小台期貨) 沒有選擇權產品

        logger.info(f"[OPTION] 🎯 Target underlyings: {underlying_ids}")

        # 初始化 Shioaji 客戶端
        try:
            with ShioajiClient() as shioaji:
                if not shioaji.is_available():
                    error_msg = (
                        "Shioaji client not available. Please check: "
                        "1) API credentials, 2) Network connection, 3) API service status"
                    )
                    logger.error(f"[OPTION] ❌ {error_msg}")

                    # Retry if not available
                    if self.request.retries < self.max_retries:
                        raise self.retry(exc=Exception(error_msg), countdown=300)

                    return {
                        "status": "error",
                        "message": error_msg,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                # 創建資料源和計算器
                data_source = ShioajiOptionDataSource(shioaji)
                calculator = OptionFactorCalculator(data_source, db)

                # 同步統計
                stats = {
                    "total_underlyings": len(underlying_ids),
                    "success_count": 0,
                    "error_count": 0,
                    "factors_saved": 0,
                    "low_quality_count": 0,
                    "errors": [],
                    "warnings": []
                }

                # 逐個標的同步
                for index, underlying_id in enumerate(underlying_ids, 1):
                    try:
                        logger.info(
                            f"[OPTION] 📊 Processing {underlying_id} "
                            f"({index}/{len(underlying_ids)})..."
                        )

                        # 計算每日因子
                        try:
                            factors = calculator.calculate_daily_factors(
                                underlying_id,
                                sync_date
                            )
                        except Exception as e:
                            logger.error(
                                f"[OPTION] ❌ Factor calculation failed for {underlying_id}: "
                                f"{type(e).__name__}: {str(e)}",
                                exc_info=True
                            )
                            stats["error_count"] += 1
                            stats["errors"].append(f"{underlying_id}: Calculation failed - {str(e)}")
                            continue

                        # 檢查資料品質
                        quality_score = factors.get('data_quality_score')
                        if quality_score:
                            quality_float = float(quality_score)
                            if quality_float < 0.3:
                                logger.error(
                                    f"[OPTION] ❌ Very low quality data for {underlying_id}: "
                                    f"score={quality_score} (<0.3). Skipping save."
                                )
                                stats["error_count"] += 1
                                stats["errors"].append(
                                    f"{underlying_id}: Very low quality (score={quality_score})"
                                )
                                continue
                            elif quality_float < 0.7:
                                logger.warning(
                                    f"[OPTION] ⚠️  Low quality data for {underlying_id}: "
                                    f"score={quality_score}"
                                )
                                stats["low_quality_count"] += 1
                                stats["warnings"].append(
                                    f"{underlying_id}: Low quality (score={quality_score})"
                                )

                        # 儲存到資料庫（upsert）
                        try:
                            factor_data = OptionDailyFactorCreate(
                                underlying_id=underlying_id,
                                date=sync_date,
                                **factors
                            )

                            saved_factor = OptionDailyFactorRepository.upsert(db, factor_data)

                            if saved_factor:
                                stats["success_count"] += 1
                                stats["factors_saved"] += 1

                                # 構建因子摘要
                                factor_summary = []
                                if factors.get('pcr_volume'):
                                    factor_summary.append(f"PCR={factors['pcr_volume']}")
                                if factors.get('atm_iv'):
                                    factor_summary.append(f"ATM_IV={factors['atm_iv']}")
                                if quality_score:
                                    factor_summary.append(f"Quality={quality_score}")

                                logger.info(
                                    f"[OPTION] ✅ Saved factors for {underlying_id}: "
                                    f"{', '.join(factor_summary)}"
                                )
                            else:
                                stats["error_count"] += 1
                                stats["errors"].append(f"{underlying_id}: Database save returned None")
                                logger.error(
                                    f"[OPTION] ❌ Failed to save factors for {underlying_id}: "
                                    "Database operation returned None"
                                )

                        except Exception as e:
                            logger.error(
                                f"[OPTION] ❌ Database save failed for {underlying_id}: "
                                f"{type(e).__name__}: {str(e)}",
                                exc_info=True
                            )
                            stats["error_count"] += 1
                            stats["errors"].append(f"{underlying_id}: DB save failed - {str(e)}")

                    except Exception as e:
                        logger.error(
                            f"[OPTION] ❌ Unexpected error processing {underlying_id}: "
                            f"{type(e).__name__}: {str(e)}",
                            exc_info=True
                        )
                        stats["error_count"] += 1
                        stats["errors"].append(f"{underlying_id}: Unexpected error - {str(e)}")

        except Exception as e:
            logger.error(
                f"[OPTION] ❌ Failed to initialize Shioaji client: "
                f"{type(e).__name__}: {str(e)}",
                exc_info=True
            )
            # Retry on client initialization failure
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=300)

            return {
                "status": "error",
                "message": f"Shioaji client error: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # 計算執行時間
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        # 記錄最終統計
        logger.info(
            f"[OPTION] 🏁 Sync completed in {duration:.1f}s. "
            f"Success: {stats['success_count']}/{stats['total_underlyings']}, "
            f"Errors: {stats['error_count']}, "
            f"Low quality: {stats['low_quality_count']}"
        )

        # 顯示錯誤摘要
        if stats['errors']:
            logger.error(
                f"[OPTION] ❌ Errors encountered:\n" +
                "\n".join(f"  - {error}" for error in stats['errors'][:10])
            )
            if len(stats['errors']) > 10:
                logger.error(f"  ... and {len(stats['errors']) - 10} more errors")

        # 顯示警告摘要
        if stats['warnings']:
            logger.warning(
                f"[OPTION] ⚠️  Warnings:\n" +
                "\n".join(f"  - {warning}" for warning in stats['warnings'][:5])
            )

        # 添加執行時間到統計
        stats['duration_seconds'] = duration

        # 返回結果
        if stats["error_count"] == 0:
            logger.info(f"[OPTION] ✅ All underlyings synced successfully!")
            return {
                "status": "success",
                "message": f"Successfully synced {stats['success_count']} underlyings",
                "statistics": stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        elif stats["success_count"] > 0:
            success_rate = (stats['success_count'] / stats['total_underlyings']) * 100
            logger.warning(
                f"[OPTION] ⚠️  Partial success: {success_rate:.1f}% success rate"
            )
            return {
                "status": "partial_success",
                "message": (
                    f"Synced {stats['success_count']}/{stats['total_underlyings']} underlyings "
                    f"({success_rate:.1f}% success rate)"
                ),
                "statistics": stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            logger.error(f"[OPTION] ❌ All underlyings failed to sync!")
            return {
                "status": "error",
                "message": "All underlyings failed to sync",
                "statistics": stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    except self.retry as retry_exc:
        # Retry exceptions should propagate
        raise retry_exc
    except Exception as e:
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.error(
            f"[OPTION] ❌ Fatal error in sync_option_daily_factors after {duration:.1f}s: "
            f"{type(e).__name__}: {str(e)}",
            exc_info=True
        )

        # Retry on unexpected errors if within retry limit
        if self.request.retries < self.max_retries:
            logger.info(
                f"[OPTION] 🔄 Retrying task (attempt {self.request.retries + 1}/{self.max_retries})..."
            )
            raise self.retry(exc=e, countdown=300)

        return {
            "status": "error",
            "message": f"Fatal error: {type(e).__name__}: {str(e)}",
            "duration_seconds": duration,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@celery_app.task(bind=True, name="app.tasks.register_option_contracts")
@skip_if_recently_executed(min_interval_hours=168)  # 週任務：7 天 = 168 小時
@record_task_history
def register_option_contracts(
    self: Task,
    underlying_ids: Optional[List[str]] = None
) -> dict:
    """
    註冊選擇權合約到資料庫（階段一輔助任務）

    執行流程：
    1. 使用 Shioaji API 獲取選擇權合約列表
    2. 註冊到 option_contracts 表
    3. 設定到期日和合約規格

    Args:
        underlying_ids: 標的代碼列表（None 表示使用配置）

    Returns:
        Task result with registration statistics
    """
    try:
        logger.info("[OPTION] Starting option contracts registration...")

        # 獲取資料庫連接
        db = next(get_db())

        # 獲取標的物列表
        if not underlying_ids:
            underlying_ids = OptionSyncConfigRepository.get_enabled_underlyings(db)

        if not underlying_ids:
            underlying_ids = ['TX', 'MTX']

        logger.info(f"[OPTION] Registering contracts for: {underlying_ids}")

        # 初始化 Shioaji 客戶端
        with ShioajiClient() as shioaji:
            if not shioaji.is_available():
                logger.error("[OPTION] Shioaji client not available")
                return {
                    "status": "error",
                    "message": "Shioaji client not available",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

            # 創建資料源
            data_source = ShioajiOptionDataSource(shioaji)

            # 註冊統計
            stats = {
                "total_underlyings": len(underlying_ids),
                "total_contracts_registered": 0,
                "total_contracts_updated": 0,
                "errors": []
            }

            # 逐個標的註冊合約
            for underlying_id in underlying_ids:
                try:
                    logger.info(f"[OPTION] Registering contracts for {underlying_id}...")

                    # 獲取合約列表（使用今天的日期）
                    from app.utils.timezone_helpers import today_taiwan
                    option_chain = data_source.get_option_chain(
                        underlying_id,
                        today_taiwan()
                    )

                    if option_chain.empty:
                        logger.warning(f"[OPTION] No contracts found for {underlying_id}")
                        continue

                    # 批次註冊合約（每 50 個合約提交一次）
                    batch_size = 50
                    total_contracts = len(option_chain)

                    for idx, (_, row) in enumerate(option_chain.iterrows(), 1):
                        try:
                            from app.schemas.option import OptionContractCreate

                            contract_data = OptionContractCreate(
                                contract_id=row['contract_id'],
                                underlying_id=row['underlying_id'],
                                underlying_type=row['underlying_type'],
                                option_type=row['option_type'],
                                strike_price=row['strike_price'],
                                expiry_date=row['expiry_date'],
                                is_active='active'
                            )

                            # 檢查是否已存在
                            existing = OptionContractRepository.get_by_id(
                                db,
                                row['contract_id']
                            )

                            if existing:
                                # 更新現有合約
                                stats["total_contracts_updated"] += 1
                            else:
                                # 創建新合約
                                OptionContractRepository.create(db, contract_data)
                                stats["total_contracts_registered"] += 1

                            # 批次提交（每 batch_size 個合約或最後一個合約）
                            if idx % batch_size == 0 or idx == total_contracts:
                                db.commit()
                                logger.debug(
                                    f"[OPTION] Progress: {idx}/{total_contracts} contracts processed, "
                                    f"committed to database"
                                )

                        except Exception as e:
                            logger.warning(
                                f"[OPTION] Failed to register contract "
                                f"{row['contract_id']}: {str(e)}"
                            )
                            # 回滾當前批次中的錯誤
                            db.rollback()
                            continue

                    logger.info(
                        f"[OPTION] ✅ Registered {stats['total_contracts_registered']} contracts "
                        f"for {underlying_id} (updated: {stats['total_contracts_updated']})"
                    )

                except Exception as e:
                    logger.error(
                        f"[OPTION] Error registering contracts for "
                        f"{underlying_id}: {str(e)}"
                    )
                    stats["errors"].append(f"{underlying_id}: {str(e)}")

        # 返回結果
        logger.info(
            f"[OPTION] Registration completed. "
            f"New: {stats['total_contracts_registered']}, "
            f"Updated: {stats['total_contracts_updated']}"
        )

        return {
            "status": "success",
            "message": f"Registered {stats['total_contracts_registered']} new contracts",
            "statistics": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"[OPTION] Fatal error in register_option_contracts: {str(e)}")
        return {
            "status": "error",
            "message": f"Fatal error: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@celery_app.task(bind=True, name="app.tasks.sync_option_minute_data")
@record_task_history
def sync_option_minute_data(
    self: Task,
    underlying_ids: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> dict:
    """
    同步選擇權分鐘線數據（階段二）

    注意：階段一不實作，僅預留接口

    Args:
        underlying_ids: 標的代碼列表
        start_date: 開始日期（YYYY-MM-DD）
        end_date: 結束日期（YYYY-MM-DD）

    Returns:
        Task result
    """
    logger.warning("[OPTION] Minute data sync not implemented in Stage 1")
    return {
        "status": "skipped",
        "message": "Minute data sync not implemented in Stage 1",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@celery_app.task(bind=True, name="app.tasks.calculate_option_greeks")
@record_task_history
def calculate_option_greeks(
    self: Task,
    underlying_ids: Optional[List[str]] = None,
    target_date: Optional[str] = None
) -> dict:
    """
    計算選擇權 Greeks（階段三）

    執行流程：
    1. 獲取選擇權合約列表
    2. 使用 Black-Scholes 模型計算 Greeks
    3. 儲存到 option_greeks 表

    Args:
        underlying_ids: 標的代碼列表（None 表示使用配置）
        target_date: 目標日期（YYYY-MM-DD，預設為今天）

    Returns:
        Task result with calculation statistics
    """
    start_time = datetime.now(timezone.utc)

    try:
        logger.info(
            f"[GREEKS] 🚀 Starting Greeks calculation (task_id: {self.request.id})"
        )

        # 解析目標日期
        try:
            if target_date:
                calc_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            else:
                from app.utils.timezone_helpers import today_taiwan
                calc_date = today_taiwan()
        except ValueError as e:
            logger.error(f"[GREEKS] ❌ Invalid date format: {target_date}")
            return {
                "status": "error",
                "message": f"Invalid date format: {target_date}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        logger.info(f"[GREEKS] 📅 Calculation date: {calc_date}")

        # 獲取資料庫連接
        try:
            db = next(get_db())
        except Exception as e:
            logger.error(f"[GREEKS] ❌ Failed to get database connection: {str(e)}")
            raise self.retry(exc=e, countdown=60)

        # 獲取當前階段配置
        try:
            stage = OptionSyncConfigRepository.get_current_stage(db)
            logger.info(f"[GREEKS] 📈 Current stage: {stage}")

            if stage < 3:
                logger.warning(
                    f"[GREEKS] ⚠️  Greeks calculation requires stage 3, current: {stage}"
                )
                return {
                    "status": "skipped",
                    "message": f"Greeks calculation requires stage 3 (current: {stage})",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
        except Exception as e:
            logger.warning(f"[GREEKS] ⚠️  Failed to get stage config: {str(e)}")

        # 獲取啟用的標的物列表
        if not underlying_ids:
            try:
                underlying_ids = OptionSyncConfigRepository.get_enabled_underlyings(db)
            except Exception as e:
                logger.warning(f"[GREEKS] ⚠️  Failed to get enabled underlyings: {str(e)}")
                underlying_ids = []

        if not underlying_ids:
            logger.warning("[GREEKS] ⚠️  No underlyings configured. Using default: TX, MTX")
            underlying_ids = ['TX', 'MTX']

        logger.info(f"[GREEKS] 🎯 Target underlyings: {underlying_ids}")

        # 初始化 Shioaji 客戶端和計算器
        try:
            from app.services.greeks_calculator import (
                BlackScholesGreeksCalculator,
                calculate_time_to_expiry
            )
            from app.schemas.option import OptionGreeksCreate
            from app.repositories.option import OptionGreeksRepository

            with ShioajiClient() as shioaji:
                if not shioaji.is_available():
                    error_msg = "Shioaji client not available"
                    logger.error(f"[GREEKS] ❌ {error_msg}")
                    if self.request.retries < self.max_retries:
                        raise self.retry(exc=Exception(error_msg), countdown=300)
                    return {
                        "status": "error",
                        "message": error_msg,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                # 創建資料源和計算器
                data_source = ShioajiOptionDataSource(shioaji)
                bs_calculator = BlackScholesGreeksCalculator()

                # 統計
                stats = {
                    "total_underlyings": len(underlying_ids),
                    "total_contracts_processed": 0,
                    "greeks_calculated": 0,
                    "errors": []
                }

                # 逐個標的計算 Greeks
                for index, underlying_id in enumerate(underlying_ids, 1):
                    try:
                        logger.info(
                            f"[GREEKS] 📊 Processing {underlying_id} "
                            f"({index}/{len(underlying_ids)})..."
                        )

                        # 獲取選擇權鏈數據
                        option_chain = data_source.get_option_chain(underlying_id, calc_date)

                        if option_chain.empty:
                            logger.warning(f"[GREEKS] No option chain data for {underlying_id}")
                            continue

                        # 過濾有效合約
                        valid_contracts = option_chain[
                            option_chain['close'].notna() &
                            (option_chain['close'] > 0) &
                            option_chain['strike_price'].notna() &
                            option_chain['expiry_date'].notna()
                        ]

                        if valid_contracts.empty:
                            logger.warning(f"[GREEKS] No valid contracts for {underlying_id}")
                            continue

                        # 估算標的現價
                        calls = valid_contracts[valid_contracts['option_type'] == 'CALL']
                        if not calls.empty and 'volume' in calls.columns and calls['volume'].sum() > 0:
                            atm_call = calls.loc[calls['volume'].idxmax()]
                            spot_price = float(atm_call['strike_price'])
                        else:
                            spot_price = float(valid_contracts['strike_price'].median())

                        logger.debug(f"[GREEKS] Spot price: {spot_price}")

                        # 逐個合約計算 Greeks
                        for _, row in valid_contracts.iterrows():
                            try:
                                contract_id = row['contract_id']
                                strike_price = float(row['strike_price'])
                                expiry_date = row['expiry_date']
                                option_type = row['option_type']
                                option_price = float(row['close'])

                                # 計算到期時間
                                time_to_expiry = calculate_time_to_expiry(expiry_date, calc_date)
                                if time_to_expiry <= 0:
                                    continue

                                # 估算隱含波動率
                                volatility = (option_price / strike_price) * np.sqrt(2 * np.pi / time_to_expiry)
                                volatility = max(0.05, min(volatility, 1.0))

                                # 計算 Greeks
                                greeks = bs_calculator.calculate_greeks(
                                    spot_price=spot_price,
                                    strike_price=strike_price,
                                    time_to_expiry=time_to_expiry,
                                    volatility=volatility,
                                    option_type=option_type
                                )

                                if greeks['delta'] is None:
                                    continue

                                # 創建 Greeks 記錄
                                greeks_data = OptionGreeksCreate(
                                    contract_id=contract_id,
                                    datetime=datetime.combine(calc_date, datetime.min.time()),
                                    delta=Decimal(str(greeks['delta'])),
                                    gamma=Decimal(str(greeks['gamma'])) if greeks['gamma'] else None,
                                    theta=Decimal(str(greeks['theta'])) if greeks['theta'] else None,
                                    vega=Decimal(str(greeks['vega'])) if greeks['vega'] else None,
                                    rho=Decimal(str(greeks['rho'])) if greeks['rho'] else None,
                                    vanna=Decimal(str(greeks['vanna'])) if greeks['vanna'] else None,
                                    spot_price=Decimal(str(spot_price)),
                                    volatility=Decimal(str(volatility)),
                                    risk_free_rate=Decimal('0.01')
                                )

                                # 儲存到資料庫（upsert）
                                OptionGreeksRepository.upsert(db, greeks_data)
                                stats["greeks_calculated"] += 1

                            except Exception as e:
                                logger.debug(
                                    f"[GREEKS] Failed to calculate for contract {row.get('contract_id', 'unknown')}: {str(e)}"
                                )
                                continue

                        stats["total_contracts_processed"] += len(valid_contracts)
                        logger.info(
                            f"[GREEKS] ✅ Processed {len(valid_contracts)} contracts for {underlying_id}"
                        )

                    except Exception as e:
                        logger.error(
                            f"[GREEKS] ❌ Error processing {underlying_id}: {str(e)}"
                        )
                        stats["errors"].append(f"{underlying_id}: {str(e)}")

        except Exception as e:
            logger.error(f"[GREEKS] ❌ Failed to initialize: {str(e)}")
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=300)
            return {
                "status": "error",
                "message": f"Initialization error: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # 計算執行時間
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        stats['duration_seconds'] = duration

        # 記錄最終統計
        logger.info(
            f"[GREEKS] 🏁 Calculation completed in {duration:.1f}s. "
            f"Processed: {stats['total_contracts_processed']}, "
            f"Greeks calculated: {stats['greeks_calculated']}"
        )

        if stats['errors']:
            logger.error(
                f"[GREEKS] ❌ Errors:\n" +
                "\n".join(f"  - {error}" for error in stats['errors'][:10])
            )

        # 返回結果
        if stats["greeks_calculated"] > 0:
            return {
                "status": "success",
                "message": f"Calculated Greeks for {stats['greeks_calculated']} contracts",
                "statistics": stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "status": "error",
                "message": "No Greeks were calculated",
                "statistics": stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    except Exception as e:
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.error(
            f"[GREEKS] ❌ Fatal error after {duration:.1f}s: {type(e).__name__}: {str(e)}",
            exc_info=True
        )
        return {
            "status": "error",
            "message": f"Fatal error: {str(e)}",
            "duration_seconds": duration,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
