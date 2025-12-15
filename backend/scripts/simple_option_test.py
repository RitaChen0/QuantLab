#!/usr/bin/env python3
"""
簡化的選擇權 API 測試腳本

測試 Shioaji API 是否能正常連接和獲取選擇權數據
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from loguru import logger
from app.services.shioaji_client import ShioajiClient


def main():
    logger.info("=" * 60)
    logger.info("簡化選擇權 API 測試")
    logger.info("=" * 60)

    # 測試 1: Shioaji 連接
    logger.info("\n測試 1: Shioaji API 連接")
    try:
        with ShioajiClient() as client:
            if client.is_available():
                logger.info("✅ Shioaji API 連接成功")

                # 測試 2: 獲取選擇權合約列表
                logger.info("\n測試 2: 獲取選擇權合約列表")
                try:
                    if client._api and hasattr(client._api, 'Contracts'):
                        if hasattr(client._api.Contracts, 'Options'):
                            if hasattr(client._api.Contracts.Options, 'TXO'):
                                option_contracts_obj = client._api.Contracts.Options.TXO
                                logger.info(f"✅ 找到 TXO 選擇權合約對象")
                                logger.info(f"   對象類型: {type(option_contracts_obj)}")

                                # 嘗試轉換為列表
                                contracts_list = []
                                try:
                                    if hasattr(option_contracts_obj, '__iter__'):
                                        contracts_list = list(option_contracts_obj)
                                    elif hasattr(option_contracts_obj, 'values'):
                                        contracts_list = list(option_contracts_obj.values())
                                    elif hasattr(option_contracts_obj, 'items'):
                                        contracts_list = [c for _, c in option_contracts_obj.items()]

                                    if contracts_list:
                                        logger.info(f"   ✅ 成功轉換為列表: {len(contracts_list)} 個合約")

                                        # 顯示前 5 個合約
                                        logger.info(f"\n前 5 個合約:")
                                        for i, contract in enumerate(contracts_list[:5]):
                                            code = contract.code if hasattr(contract, 'code') else 'N/A'
                                            strike = contract.strike_price if hasattr(contract, 'strike_price') else 'N/A'
                                            option_type = contract.option_right if hasattr(contract, 'option_right') else 'N/A'
                                            logger.info(f"   {i+1}. {code} | Strike: {strike} | Type: {option_type}")
                                    else:
                                        logger.warning("   ⚠️  無法轉換為列表")

                                except Exception as convert_error:
                                    logger.error(f"   ❌ 轉換失敗: {str(convert_error)}")

                            else:
                                logger.warning("⚠️  找不到 TXO 選擇權合約")
                        else:
                            logger.warning("⚠️  Contracts.Options 不存在")
                    else:
                        logger.warning("⚠️  Contracts API 不可用")

                except Exception as e:
                    logger.error(f"❌ 獲取選擇權合約失敗: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())

            else:
                logger.error("❌ Shioaji API 無法使用")
                logger.info("   請檢查：")
                logger.info("   1. SHIOAJI_API_KEY 環境變數")
                logger.info("   2. SHIOAJI_SECRET_KEY 環境變數")
                logger.info("   3. API 金鑰是否有效")

    except Exception as e:
        logger.error(f"❌ 連接失敗: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()
