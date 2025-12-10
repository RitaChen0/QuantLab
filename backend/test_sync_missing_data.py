#!/usr/bin/env python3
"""測試財務指標同步的錯誤處理"""

import sys
sys.path.insert(0, '/app')

from app.db.session import SessionLocal
from app.services.fundamental_service import FundamentalService
from loguru import logger

def test_sync_missing_stock():
    """測試同步不存在的股票"""
    db = SessionLocal()
    service = FundamentalService(db)

    logger.info("=" * 60)
    logger.info("測試 1: 同步不存在的股票 0015")
    logger.info("=" * 60)

    try:
        result = service.sync_indicator_data(
            stock_id="0015",
            indicator="稅前淨利率",
            start_date=None,
            end_date=None
        )
        logger.info(f"✅ 結果: 同步了 {result} 筆數據（預期為 0）")

        if result == 0:
            logger.success("✅ 測試通過：正確處理缺失數據")
        else:
            logger.error(f"❌ 測試失敗：預期 0 筆，實際 {result} 筆")

    except Exception as e:
        logger.error(f"❌ 測試失敗：不應該拋出異常")
        logger.error(f"   錯誤: {str(e)}")

    logger.info("")
    logger.info("=" * 60)
    logger.info("測試 2: 同步存在的股票 2330 (台積電)")
    logger.info("=" * 60)

    try:
        result = service.sync_indicator_data(
            stock_id="2330",
            indicator="ROE稅後",
            start_date=None,
            end_date=None
        )
        logger.info(f"✅ 結果: 同步了 {result} 筆數據")

        if result > 0:
            logger.success("✅ 測試通過：成功同步數據")
        else:
            logger.warning("⚠️  警告：2330 沒有 ROE稅後 數據")

    except Exception as e:
        logger.error(f"❌ 測試失敗：{str(e)}")

    db.close()
    logger.info("")
    logger.success("🎉 測試完成")

if __name__ == "__main__":
    test_sync_missing_stock()
