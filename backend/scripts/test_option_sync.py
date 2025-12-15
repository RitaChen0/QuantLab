#!/usr/bin/env python3
"""
測試選擇權數據同步功能

測試項目：
1. Shioaji API 連接
2. 獲取選擇權鏈數據
3. 計算每日因子
4. 儲存到資料庫

使用方式：
    python scripts/test_option_sync.py
    python scripts/test_option_sync.py --underlying TX
    python scripts/test_option_sync.py --dry-run  # 不寫入資料庫
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse
from datetime import date
from loguru import logger

from app.services.shioaji_client import ShioajiClient
from app.services.option_data_source import ShioajiOptionDataSource
from app.services.option_calculator import OptionFactorCalculator
from app.repositories.option import (
    OptionDailyFactorRepository,
    OptionSyncConfigRepository,
    OptionContractRepository
)
from app.schemas.option import OptionDailyFactorCreate, OptionContractCreate
from app.db.base import get_db


def test_shioaji_connection() -> bool:
    """測試 Shioaji API 連接"""
    logger.info("=" * 60)
    logger.info("測試 1: Shioaji API 連接")
    logger.info("=" * 60)

    try:
        with ShioajiClient() as client:
            if client.is_available():
                logger.info("✅ Shioaji API 連接成功")
                return True
            else:
                logger.error("❌ Shioaji API 無法使用")
                return False
    except Exception as e:
        logger.error(f"❌ Shioaji API 連接失敗: {str(e)}")
        return False


def test_get_option_chain(underlying: str = 'TX') -> bool:
    """測試獲取選擇權鏈數據"""
    logger.info("=" * 60)
    logger.info(f"測試 2: 獲取選擇權鏈數據 ({underlying})")
    logger.info("=" * 60)

    try:
        with ShioajiClient() as client:
            if not client.is_available():
                logger.error("❌ Shioaji 客戶端不可用")
                return False

            data_source = ShioajiOptionDataSource(client)
            option_chain = data_source.get_option_chain(underlying, date.today())

            if option_chain.empty:
                logger.warning(f"⚠️  未獲取到 {underlying} 的選擇權數據")
                logger.info("這可能是因為：")
                logger.info("1. 非交易時段")
                logger.info("2. 該標的無選擇權合約")
                logger.info("3. API 權限不足")
                return False
            else:
                logger.info(f"✅ 成功獲取 {len(option_chain)} 個選擇權合約")
                logger.info(f"   前 5 個合約:")
                logger.info(f"\n{option_chain.head().to_string()}")

                # 統計資訊
                calls = option_chain[option_chain['option_type'] == 'CALL']
                puts = option_chain[option_chain['option_type'] == 'PUT']
                logger.info(f"\n統計資訊:")
                logger.info(f"   CALL 合約: {len(calls)}")
                logger.info(f"   PUT 合約: {len(puts)}")
                logger.info(f"   履約價範圍: {option_chain['strike_price'].min()} - {option_chain['strike_price'].max()}")

                return True

    except Exception as e:
        logger.error(f"❌ 獲取選擇權鏈失敗: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_calculate_factors(underlying: str = 'TX') -> dict:
    """測試計算每日因子"""
    logger.info("=" * 60)
    logger.info(f"測試 3: 計算每日因子 ({underlying})")
    logger.info("=" * 60)

    try:
        db = next(get_db())

        with ShioajiClient() as client:
            if not client.is_available():
                logger.error("❌ Shioaji 客戶端不可用")
                return {}

            data_source = ShioajiOptionDataSource(client)
            calculator = OptionFactorCalculator(data_source, db)

            factors = calculator.calculate_daily_factors(underlying, date.today())

            if not factors:
                logger.warning(f"⚠️  未計算到 {underlying} 的因子")
                return {}

            logger.info("✅ 成功計算每日因子:")
            logger.info(f"   PCR Volume: {factors.get('pcr_volume')}")
            logger.info(f"   PCR Open Interest: {factors.get('pcr_open_interest')}")
            logger.info(f"   ATM IV: {factors.get('atm_iv')}")
            logger.info(f"   Data Quality Score: {factors.get('data_quality_score')}")
            logger.info(f"   Calculation Version: {factors.get('calculation_version')}")

            # 驗證因子合理性
            pcr_volume = factors.get('pcr_volume')
            if pcr_volume:
                if 0.3 <= float(pcr_volume) <= 3.0:
                    logger.info(f"   ✅ PCR Volume 在合理範圍內")
                else:
                    logger.warning(f"   ⚠️  PCR Volume 超出正常範圍 (0.3-3.0)")

            quality_score = factors.get('data_quality_score')
            if quality_score:
                if float(quality_score) >= 0.8:
                    logger.info(f"   ✅ 資料品質優良 (>= 0.8)")
                elif float(quality_score) >= 0.5:
                    logger.warning(f"   ⚠️  資料品質中等 (0.5-0.8)")
                else:
                    logger.warning(f"   ⚠️  資料品質較低 (< 0.5)")

            return factors

    except Exception as e:
        logger.error(f"❌ 計算因子失敗: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {}


def test_save_to_database(underlying: str = 'TX', dry_run: bool = False) -> bool:
    """測試儲存到資料庫"""
    logger.info("=" * 60)
    logger.info(f"測試 4: 儲存到資料庫 ({underlying})")
    logger.info("=" * 60)

    if dry_run:
        logger.info("🔍 Dry-run 模式：不會實際寫入資料庫")

    try:
        db = next(get_db())

        with ShioajiClient() as client:
            if not client.is_available():
                logger.error("❌ Shioaji 客戶端不可用")
                return False

            data_source = ShioajiOptionDataSource(client)
            calculator = OptionFactorCalculator(data_source, db)

            # 計算因子
            factors = calculator.calculate_daily_factors(underlying, date.today())

            if not factors:
                logger.warning(f"⚠️  無法計算因子，跳過儲存")
                return False

            if dry_run:
                logger.info("✅ Dry-run: 因子計算成功，未寫入資料庫")
                return True

            # 儲存到資料庫
            factor_data = OptionDailyFactorCreate(
                underlying_id=underlying,
                date=date.today(),
                **factors
            )

            saved_factor = OptionDailyFactorRepository.upsert(db, factor_data)

            if saved_factor:
                logger.info(f"✅ 成功儲存因子到資料庫")
                logger.info(f"   Underlying: {saved_factor.underlying_id}")
                logger.info(f"   Date: {saved_factor.date}")
                logger.info(f"   PCR Volume: {saved_factor.pcr_volume}")
                return True
            else:
                logger.error("❌ 儲存因子失敗")
                return False

    except Exception as e:
        logger.error(f"❌ 儲存到資料庫失敗: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_register_contracts(underlying: str = 'TX', dry_run: bool = False) -> bool:
    """測試註冊選擇權合約"""
    logger.info("=" * 60)
    logger.info(f"測試 5: 註冊選擇權合約 ({underlying})")
    logger.info("=" * 60)

    if dry_run:
        logger.info("🔍 Dry-run 模式：不會實際寫入資料庫")

    try:
        db = next(get_db())

        with ShioajiClient() as client:
            if not client.is_available():
                logger.error("❌ Shioaji 客戶端不可用")
                return False

            data_source = ShioajiOptionDataSource(client)
            option_chain = data_source.get_option_chain(underlying, date.today())

            if option_chain.empty:
                logger.warning(f"⚠️  無選擇權合約可註冊")
                return False

            if dry_run:
                logger.info(f"✅ Dry-run: 找到 {len(option_chain)} 個合約，未寫入資料庫")
                return True

            # 註冊合約
            registered_count = 0
            updated_count = 0

            for _, row in option_chain.head(10).iterrows():  # 僅測試前 10 個
                try:
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
                    existing = OptionContractRepository.get_by_id(db, row['contract_id'])

                    if existing:
                        updated_count += 1
                    else:
                        OptionContractRepository.create(db, contract_data)
                        registered_count += 1

                except Exception as e:
                    logger.warning(f"   ⚠️  註冊合約 {row['contract_id']} 失敗: {str(e)}")
                    continue

            logger.info(f"✅ 合約註冊完成")
            logger.info(f"   新註冊: {registered_count}")
            logger.info(f"   已存在: {updated_count}")

            return True

    except Exception as e:
        logger.error(f"❌ 註冊合約失敗: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    parser = argparse.ArgumentParser(description='測試選擇權數據同步功能')
    parser.add_argument(
        '--underlying',
        type=str,
        default='TX',
        help='標的代碼（預設: TX）'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='不寫入資料庫（僅測試）'
    )
    parser.add_argument(
        '--skip-connection',
        action='store_true',
        help='跳過連接測試'
    )

    args = parser.parse_args()

    logger.info("🚀 開始測試選擇權數據同步功能")
    logger.info(f"標的: {args.underlying}")
    logger.info(f"Dry-run: {args.dry_run}")
    logger.info("")

    results = {}

    # 測試 1: Shioaji 連接
    if not args.skip_connection:
        results['connection'] = test_shioaji_connection()
        if not results['connection']:
            logger.error("❌ Shioaji API 連接失敗，後續測試無法進行")
            return

    # 測試 2: 獲取選擇權鏈
    results['option_chain'] = test_get_option_chain(args.underlying)

    # 測試 3: 計算因子
    factors = test_calculate_factors(args.underlying)
    results['calculate'] = bool(factors)

    # 測試 4: 儲存到資料庫
    if results.get('calculate'):
        results['save'] = test_save_to_database(args.underlying, args.dry_run)

    # 測試 5: 註冊合約
    if results.get('option_chain'):
        results['register'] = test_register_contracts(args.underlying, args.dry_run)

    # 總結
    logger.info("")
    logger.info("=" * 60)
    logger.info("測試結果總結")
    logger.info("=" * 60)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name:20s}: {status}")

    success_rate = sum(results.values()) / len(results) * 100 if results else 0
    logger.info("")
    logger.info(f"成功率: {success_rate:.1f}% ({sum(results.values())}/{len(results)})")

    if success_rate == 100:
        logger.info("🎉 所有測試通過！")
    elif success_rate >= 60:
        logger.warning("⚠️  部分測試失敗，請檢查日誌")
    else:
        logger.error("❌ 多數測試失敗，請檢查配置")


if __name__ == '__main__':
    main()
