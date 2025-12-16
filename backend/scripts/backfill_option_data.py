#!/usr/bin/env python
"""
選擇權歷史資料回補腳本

使用 Shioaji API 回補選擇權歷史資料：
1. 獲取選擇權合約列表
2. 對每個合約查詢歷史日線資料
3. 計算每日因子（PCR, ATM IV, Greeks）
4. 儲存到 option_daily_factors 表

使用方式：
    python scripts/backfill_option_data.py --start-date 2024-12-01 --end-date 2025-12-15
    python scripts/backfill_option_data.py --days-back 30  # 回補最近 30 天
"""

import sys
import argparse
from datetime import date, datetime, timedelta
from typing import List, Optional
from loguru import logger
from decimal import Decimal

# 添加 app 目錄到路徑
sys.path.insert(0, '/app')

from app.db.session import SessionLocal
from app.services.shioaji_client import ShioajiClient
from app.services.option_calculator import OptionFactorCalculator
from app.repositories.option import (
    OptionDailyFactorRepository,
    OptionSyncConfigRepository,
    OptionContractRepository
)
from app.schemas.option import OptionDailyFactorCreate, OptionContractCreate


def generate_date_range(start_date: date, end_date: date) -> List[date]:
    """
    生成日期範圍（排除週末）

    Args:
        start_date: 開始日期
        end_date: 結束日期

    Returns:
        日期列表（僅交易日）
    """
    dates = []
    current = start_date
    while current <= end_date:
        # 排除週末（0=週一, 6=週日）
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)
    return dates


def get_option_contracts_for_date(
    api,
    underlying: str,
    target_date: date
) -> List:
    """
    獲取特定日期存在的選擇權合約

    Args:
        api: Shioaji API 實例
        underlying: 標的代碼（TX, MTX）
        target_date: 目標日期

    Returns:
        合約列表
    """
    try:
        # 獲取所有合約
        if underlying == 'TX':
            option_contracts_obj = api.Contracts.Options.TXO
        elif underlying == 'MTX':
            if hasattr(api.Contracts.Options, 'MXO'):
                option_contracts_obj = api.Contracts.Options.MXO
            else:
                logger.warning("[BACKFILL] MTX options not available")
                return []
        else:
            logger.error(f"[BACKFILL] Unsupported underlying: {underlying}")
            return []

        # 使用迭代器避免一次性加載所有合約（可能導致阻塞）
        import time

        active_contracts = []
        total_scanned = 0
        max_contracts = 2000  # 安全上限，避免無限循環

        # 直接迭代，避免 list() 轉換
        for contract in option_contracts_obj:
            total_scanned += 1

            # 安全上限檢查
            if total_scanned > max_contracts:
                logger.warning(
                    f"[BACKFILL] Reached max contracts limit ({max_contracts}), "
                    f"stopping scan"
                )
                break

            # 每 100 個合約添加短暫延遲，避免過快
            if total_scanned % 100 == 0:
                time.sleep(0.05)

            if hasattr(contract, 'delivery_date'):
                # 檢查到期日
                if isinstance(contract.delivery_date, str):
                    expiry = datetime.strptime(contract.delivery_date, "%Y/%m/%d").date()
                else:
                    expiry = contract.delivery_date

                # 合約在 target_date 時仍然有效
                if expiry >= target_date:
                    active_contracts.append(contract)

        logger.info(
            f"[BACKFILL] Found {len(active_contracts)}/{total_scanned} "
            f"active contracts for {underlying} on {target_date}"
        )
        return active_contracts

    except Exception as e:
        logger.error(f"[BACKFILL] Error getting contracts: {str(e)}")
        return []


def fetch_contract_daily_data(
    api,
    contract,
    target_date: date,
    retry_count: int = 2,
    retry_delay: float = 1.0
) -> Optional[dict]:
    """
    獲取合約在特定日期的日線資料（帶重試機制）

    Args:
        api: Shioaji API 實例
        contract: 合約物件
        target_date: 目標日期
        retry_count: 重試次數
        retry_delay: 重試延遲（秒）

    Returns:
        價格數據字典，失敗返回 None
    """
    import time

    for attempt in range(retry_count + 1):
        try:
            # 使用 kbars 獲取歷史資料（Shioaji API 返回分鐘線）
            # 查詢當天的數據
            kbars = api.kbars(
                contract=contract,
                start=target_date.strftime('%Y-%m-%d'),
                end=target_date.strftime('%Y-%m-%d'),
                timeout=30000
            )

            if not kbars or not hasattr(kbars, 'ts') or len(kbars.ts) == 0:
                return None

            # 取當天的最後一根 K 線（收盤數據）
            last_index = -1

            data = {
                'contract_id': contract.code,
                'close': float(kbars.Close[last_index]),
                'open': float(kbars.Open[last_index]),
                'high': float(kbars.High[last_index]),
                'low': float(kbars.Low[last_index]),
                'volume': int(kbars.Volume[last_index]),
            }

            return data

        except Exception as e:
            if attempt < retry_count:
                # 重試前延遲
                logger.debug(
                    f"[BACKFILL] Retry {attempt + 1}/{retry_count} for {contract.code} "
                    f"after {retry_delay}s: {str(e)[:100]}"
                )
                time.sleep(retry_delay)
            else:
                # 最後一次失敗，只記錄 DEBUG 級別
                logger.debug(f"[BACKFILL] Failed to fetch data for {contract.code}: {str(e)[:150]}")
                return None

    return None


def validate_contract_data(data: dict, contract_code: str) -> bool:
    """
    驗證合約數據合理性

    Args:
        data: 合約價格數據
        contract_code: 合約代碼（用於日誌）

    Returns:
        True 如果數據有效，False 如果發現異常
    """
    try:
        # 檢查必要欄位
        required_fields = ['close', 'open', 'high', 'low', 'volume']
        for field in required_fields:
            if field not in data:
                logger.warning(f"[VALIDATE] ❌ Missing field '{field}' for {contract_code}")
                return False

        close = data['close']
        open_price = data['open']
        high = data['high']
        low = data['low']
        volume = data['volume']

        # 1. 價格必須為正
        if close <= 0:
            logger.warning(f"[VALIDATE] ❌ Invalid close price ({close}) for {contract_code}")
            return False

        if open_price <= 0:
            logger.warning(f"[VALIDATE] ❌ Invalid open price ({open_price}) for {contract_code}")
            return False

        if high <= 0:
            logger.warning(f"[VALIDATE] ❌ Invalid high price ({high}) for {contract_code}")
            return False

        if low <= 0:
            logger.warning(f"[VALIDATE] ❌ Invalid low price ({low}) for {contract_code}")
            return False

        # 2. OHLC 關係必須合理（low <= open/close/high <= high）
        if not (low <= close <= high):
            logger.warning(
                f"[VALIDATE] ❌ Invalid OHLC relationship: "
                f"low={low}, close={close}, high={high} for {contract_code}"
            )
            return False

        if not (low <= open_price <= high):
            logger.warning(
                f"[VALIDATE] ❌ Invalid OHLC relationship: "
                f"low={low}, open={open_price}, high={high} for {contract_code}"
            )
            return False

        if low > high:
            logger.warning(
                f"[VALIDATE] ❌ Low > High: low={low}, high={high} for {contract_code}"
            )
            return False

        # 3. 成交量不能為負
        if volume < 0:
            logger.warning(f"[VALIDATE] ❌ Negative volume ({volume}) for {contract_code}")
            return False

        # 4. 檢查價格是否異常（例如 close = 999999 這種明顯錯誤）
        if close > 100000 or open_price > 100000 or high > 100000:
            logger.warning(
                f"[VALIDATE] ❌ Suspiciously high price detected for {contract_code}: "
                f"close={close}, open={open_price}, high={high}"
            )
            return False

        # 5. 檢查價格範圍是否合理（high-low 不應該超過 close 的 50%）
        if high - low > close * 0.5:
            logger.warning(
                f"[VALIDATE] ⚠️  Large price range detected for {contract_code}: "
                f"range={high-low}, close={close}"
            )
            # 這不是致命錯誤，只記錄警告但仍然返回 True

        return True

    except Exception as e:
        logger.error(f"[VALIDATE] ❌ Validation error for {contract_code}: {str(e)}")
        return False


def backfill_option_factors(
    underlying: str,
    start_date: date,
    end_date: date,
    dry_run: bool = False
):
    """
    回補選擇權因子數據

    Args:
        underlying: 標的代碼（TX, MTX）
        start_date: 開始日期
        end_date: 結束日期
        dry_run: 是否為測試模式（不寫入資料庫）
    """
    logger.info(f"[BACKFILL] 🚀 Starting option data backfill for {underlying}")
    logger.info(f"[BACKFILL] 📅 Date range: {start_date} to {end_date}")
    logger.info(f"[BACKFILL] 🧪 Dry run: {dry_run}")

    # 生成日期範圍
    dates = generate_date_range(start_date, end_date)
    logger.info(f"[BACKFILL] 📊 Total trading days: {len(dates)}")

    # 初始化資料庫（使用 psycopg2 避開 ORM 映射問題）
    import psycopg2
    from urllib.parse import urlparse
    from app.core.config import settings

    # 安全解析資料庫連線字串
    db_url = settings.DATABASE_URL.replace('+psycopg2', '')
    parsed = urlparse(db_url)

    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path.lstrip('/'),
        user=parsed.username,
        password=parsed.password
    )
    cur = conn.cursor()

    # 初始化 Shioaji 客戶端
    with ShioajiClient() as shioaji:
        if not shioaji.is_available():
            logger.error("[BACKFILL] ❌ Shioaji client not available")
            return

        api = shioaji._api

        # 統計
        stats = {
            'total_days': len(dates),
            'days_processed': 0,
            'days_success': 0,
            'days_failed': 0,
            'total_contracts': 0,
            'contracts_fetched': 0,
            'factors_saved': 0
        }

        # 逐日回補
        for i, target_date in enumerate(dates, 1):
            try:
                logger.info(
                    f"[BACKFILL] 📅 Processing {target_date} "
                    f"({i}/{len(dates)}, {i/len(dates)*100:.1f}%)"
                )

                # 檢查是否已存在（使用 SQL）
                cur.execute(
                    "SELECT 1 FROM option_daily_factors WHERE underlying_id = %s AND date = %s",
                    (underlying, target_date)
                )
                if cur.fetchone() and not dry_run:
                    logger.info(f"[BACKFILL] ⏭️  Data already exists for {target_date}, skipping")
                    stats['days_processed'] += 1
                    continue

                # 獲取當天的合約列表
                contracts = get_option_contracts_for_date(api, underlying, target_date)
                if not contracts:
                    logger.warning(f"[BACKFILL] ⚠️  No contracts for {target_date}")
                    stats['days_failed'] += 1
                    stats['days_processed'] += 1
                    continue

                stats['total_contracts'] += len(contracts)

                # 獲取每個合約的價格數據（分批處理，避免速率限制）
                import time

                contract_data = []
                batch_size = 50  # 每批處理 50 個合約
                batch_delay = 2.0  # 每批之間延遲 2 秒
                request_delay = 0.1  # 每個請求之間延遲 0.1 秒

                for i, contract in enumerate(contracts):
                    # 每批之間添加延遲
                    if i > 0 and i % batch_size == 0:
                        logger.info(
                            f"[BACKFILL] 💤 Batch {i // batch_size} completed, "
                            f"sleeping {batch_delay}s to avoid rate limit..."
                        )
                        time.sleep(batch_delay)

                    # 獲取合約數據
                    data = fetch_contract_daily_data(api, contract, target_date)
                    if data:
                        # 驗證數據合理性
                        if not validate_contract_data(data, contract.code):
                            logger.warning(
                                f"[BACKFILL] ⚠️  Skipping invalid data for {contract.code}"
                            )
                            continue

                        # 補充合約資訊
                        # 確保 expiry_date 是 date 物件而非字串
                        if isinstance(contract.delivery_date, str):
                            expiry_date = datetime.strptime(contract.delivery_date, "%Y/%m/%d").date()
                        else:
                            expiry_date = contract.delivery_date

                        data.update({
                            'underlying_id': underlying,
                            'underlying_type': 'FUTURES',
                            'option_type': 'CALL' if 'C' in contract.code else 'PUT',
                            'strike_price': float(contract.strike_price),
                            'expiry_date': expiry_date
                        })
                        contract_data.append(data)
                        stats['contracts_fetched'] += 1

                    # 每個請求之間添加小延遲
                    if i < len(contracts) - 1:
                        time.sleep(request_delay)

                if not contract_data:
                    logger.warning(
                        f"[BACKFILL] ⚠️  No data fetched for {target_date} "
                        f"(tried {len(contracts)} contracts)"
                    )
                    stats['days_failed'] += 1
                    stats['days_processed'] += 1
                    continue

                logger.info(
                    f"[BACKFILL] ✅ Fetched {len(contract_data)}/{len(contracts)} contracts "
                    f"({len(contract_data)/len(contracts)*100:.1f}%)"
                )

                # 計算因子（直接使用已獲取的數據）
                import pandas as pd
                option_chain = pd.DataFrame(contract_data)

                # 使用 OptionFactorCalculator 的內部方法計算因子
                calculator = OptionFactorCalculator(None, None)

                # 手動計算階段一因子
                factors = {}
                factors.update(calculator._calculate_pcr(option_chain))
                factors.update(calculator._calculate_atm_iv(option_chain))

                # 階段三：Greeks 摘要（如果啟用）
                try:
                    cur.execute("SELECT value FROM option_sync_config WHERE key = 'stage'")
                    stage_row = cur.fetchone()
                    stage = int(stage_row[0]) if stage_row else 1
                    if stage >= 3:
                        factors.update(calculator._calculate_greeks_summary(option_chain))
                except Exception as e:
                    logger.debug(f"[BACKFILL] Greeks calculation skipped: {str(e)}")

                # 添加版本和品質評分
                factors['calculation_version'] = calculator.VERSION
                factors['data_quality_score'] = calculator._assess_quality(factors, option_chain)

                # 儲存到資料庫（使用 SQL）
                if not dry_run:
                    try:
                        # 準備插入/更新數據
                        pcr_volume = factors.get('pcr_volume')
                        pcr_open_interest = factors.get('pcr_open_interest')
                        atm_iv = factors.get('atm_iv')
                        avg_call_delta = factors.get('avg_call_delta')
                        avg_put_delta = factors.get('avg_put_delta')
                        gamma_exposure = factors.get('gamma_exposure')
                        vanna_exposure = factors.get('vanna_exposure')
                        quality_score = factors.get('data_quality_score')
                        version = factors.get('calculation_version')

                        # Upsert 操作
                        cur.execute("""
                            INSERT INTO option_daily_factors (
                                underlying_id, date,
                                pcr_volume, pcr_open_interest, atm_iv,
                                avg_call_delta, avg_put_delta, gamma_exposure, vanna_exposure,
                                data_quality_score, calculation_version,
                                created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                            ON CONFLICT (underlying_id, date)
                            DO UPDATE SET
                                pcr_volume = EXCLUDED.pcr_volume,
                                pcr_open_interest = EXCLUDED.pcr_open_interest,
                                atm_iv = EXCLUDED.atm_iv,
                                avg_call_delta = EXCLUDED.avg_call_delta,
                                avg_put_delta = EXCLUDED.avg_put_delta,
                                gamma_exposure = EXCLUDED.gamma_exposure,
                                vanna_exposure = EXCLUDED.vanna_exposure,
                                data_quality_score = EXCLUDED.data_quality_score,
                                calculation_version = EXCLUDED.calculation_version
                        """, (
                            underlying, target_date,
                            pcr_volume, pcr_open_interest, atm_iv,
                            avg_call_delta, avg_put_delta, gamma_exposure, vanna_exposure,
                            quality_score, version
                        ))
                        conn.commit()

                        stats['factors_saved'] += 1
                        stats['days_success'] += 1
                        logger.info(
                            f"[BACKFILL] 💾 Saved factors for {target_date}: "
                            f"PCR={pcr_volume}, ATM_IV={atm_iv}, Quality={quality_score}"
                        )

                    except Exception as e:
                        conn.rollback()
                        logger.error(
                            f"[BACKFILL] ❌ Error saving factors for {target_date}: {str(e)}"
                        )
                        stats['days_failed'] += 1
                else:
                    # Dry run: 只顯示結果
                    logger.info(
                        f"[BACKFILL] 🧪 [DRY RUN] Would save: "
                        f"PCR={factors.get('pcr_volume')}, "
                        f"ATM_IV={factors.get('atm_iv')}, "
                        f"Quality={factors.get('data_quality_score')}"
                    )
                    stats['days_success'] += 1

                stats['days_processed'] += 1

            except Exception as e:
                logger.error(
                    f"[BACKFILL] ❌ Error processing {target_date}: {str(e)}",
                    exc_info=True
                )
                stats['days_failed'] += 1
                stats['days_processed'] += 1

    # 關閉資料庫
    cur.close()
    conn.close()

    # 輸出統計
    logger.info("=" * 60)
    logger.info("[BACKFILL] 🏁 Backfill completed!")
    logger.info("=" * 60)
    logger.info(f"Days processed: {stats['days_processed']}/{stats['total_days']}")
    logger.info(f"Days success: {stats['days_success']}")
    logger.info(f"Days failed: {stats['days_failed']}")
    logger.info(f"Contracts total: {stats['total_contracts']}")
    logger.info(f"Contracts fetched: {stats['contracts_fetched']}")
    logger.info(f"Factors saved: {stats['factors_saved']}")

    if stats['total_contracts'] > 0:
        fetch_rate = stats['contracts_fetched'] / stats['total_contracts'] * 100
        logger.info(f"Fetch success rate: {fetch_rate:.1f}%")

    success_rate = stats['days_success'] / stats['total_days'] * 100 if stats['total_days'] > 0 else 0
    logger.info(f"Overall success rate: {success_rate:.1f}%")


def main():
    parser = argparse.ArgumentParser(description='選擇權歷史資料回補')
    parser.add_argument(
        '--underlying',
        type=str,
        default='TX',
        choices=['TX', 'MTX'],
        help='標的代碼（預設: TX）'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        help='開始日期（YYYY-MM-DD）'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        help='結束日期（YYYY-MM-DD，預設: 今天）'
    )
    parser.add_argument(
        '--days-back',
        type=int,
        help='回補最近 N 天（替代 start-date）'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='測試模式（不寫入資料庫）'
    )

    args = parser.parse_args()

    # 解析日期
    if args.days_back:
        end_date = date.today()
        start_date = end_date - timedelta(days=args.days_back)
    elif args.start_date:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        if args.end_date:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
        else:
            end_date = date.today()
    else:
        # 預設：回補最近 7 天
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        logger.warning("[BACKFILL] No date specified, defaulting to last 7 days")

    # 執行回補
    backfill_option_factors(
        underlying=args.underlying,
        start_date=start_date,
        end_date=end_date,
        dry_run=args.dry_run
    )


if __name__ == '__main__':
    main()
