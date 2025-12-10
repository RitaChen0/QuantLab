#!/usr/bin/env python3
"""
檢查並補齊股票歷史資料的缺失

功能：
1. 檢查所有股票的資料完整性
2. 識別缺失的股票（完全沒有資料）
3. 識別資料不完整的股票（記錄數少於預期）
4. 自動補齊缺失的資料
5. 生成詳細的檢查報告

Usage:
    # 檢查並補齊所有缺失（自動模式）
    python scripts/check_and_fill_gaps.py --auto-fix

    # 只檢查不補齊（報告模式）
    python scripts/check_and_fill_gaps.py --report-only

    # 補齊特定股票
    python scripts/check_and_fill_gaps.py --stocks 2330,2317,2454

    # 設定預期的最小記錄數
    python scripts/check_and_fill_gaps.py --min-records 4500 --auto-fix
"""

import sys
import os
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import argparse
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Tuple, Optional
import pandas as pd
from loguru import logger
from collections import defaultdict

from app.db.session import SessionLocal
from app.repositories.stock import StockRepository
from app.repositories.stock_price import StockPriceRepository
from app.services.finlab_client import FinLabClient
from app.schemas.stock_price import StockPriceCreate
from app.models.stock_price import StockPrice
from sqlalchemy import func


# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)
logger.add(
    "/tmp/check_fill_gaps_{time}.log",
    rotation="100 MB",
    retention="30 days",
    level="DEBUG"
)


class DataGapChecker:
    """股票資料完整性檢查與補齊工具"""

    def __init__(
        self,
        years: int = 20,
        min_records: int = 4500,
        stock_ids: Optional[List[str]] = None,
        auto_fix: bool = False,
        delay_seconds: float = 0.5,
        retry_count: int = 3
    ):
        """
        初始化檢查工具

        Args:
            years: 預期的歷史年數
            min_records: 預期的最小記錄數（預設 4500 約 18 年）
            stock_ids: 指定要檢查的股票 ID 列表
            auto_fix: 是否自動補齊缺失
            delay_seconds: API 呼叫延遲
            retry_count: 失敗重試次數
        """
        self.years = years
        self.min_records = min_records
        self.stock_ids = stock_ids
        self.auto_fix = auto_fix
        self.delay_seconds = delay_seconds
        self.retry_count = retry_count

        self.db = SessionLocal()
        self.client = FinLabClient()

        # Statistics
        self.total_stocks = 0
        self.missing_stocks = []  # 完全沒有資料
        self.incomplete_stocks = []  # 資料不完整
        self.complete_stocks = []  # 資料完整
        self.fixed_stocks = []  # 已修復
        self.failed_stocks = []  # 修復失敗

        self.start_time = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()

    def get_stock_list(self) -> List[str]:
        """獲取要檢查的股票清單"""
        if self.stock_ids:
            logger.info(f"檢查指定的 {len(self.stock_ids)} 檔股票")
            return self.stock_ids

        # 從資料庫獲取所有股票
        stocks = StockRepository.get_all(
            self.db,
            skip=0,
            limit=10000,
            is_active='active'
        )

        stock_ids = [stock.stock_id for stock in stocks]
        logger.info(f"檢查所有 {len(stock_ids)} 檔股票")
        return stock_ids

    def check_stock_data(self, stock_id: str) -> Tuple[str, int]:
        """
        檢查單一股票的資料完整性

        Args:
            stock_id: 股票代碼

        Returns:
            (狀態, 記錄數) - 狀態可能是 'missing', 'incomplete', 'complete'
        """
        try:
            # 查詢該股票的記錄數
            record_count = self.db.query(func.count()).filter(
                StockPrice.stock_id == stock_id
            ).scalar()

            if record_count == 0:
                return ('missing', 0)
            elif record_count < self.min_records:
                return ('incomplete', record_count)
            else:
                return ('complete', record_count)

        except Exception as e:
            logger.error(f"檢查 {stock_id} 時發生錯誤: {str(e)}")
            return ('error', 0)

    def sync_stock_data(self, stock_id: str) -> bool:
        """
        同步單一股票的資料

        Args:
            stock_id: 股票代碼

        Returns:
            是否成功
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.years * 365)

        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        for attempt in range(self.retry_count):
            try:
                # 從 FinLab 獲取資料
                ohlcv_df = self.client.get_ohlcv(
                    stock_id=stock_id,
                    start_date=start_date_str,
                    end_date=end_date_str
                )

                if ohlcv_df.empty:
                    logger.warning(f"{stock_id}: 無資料")
                    return False

                # 批次儲存到資料庫
                saved_count = 0
                for date, row in ohlcv_df.iterrows():
                    try:
                        price_create = StockPriceCreate(
                            stock_id=stock_id,
                            date=date.date() if hasattr(date, 'date') else date,
                            open=Decimal(str(row['open'])) if pd.notna(row['open']) else Decimal('0'),
                            high=Decimal(str(row['high'])) if pd.notna(row['high']) else Decimal('0'),
                            low=Decimal(str(row['low'])) if pd.notna(row['low']) else Decimal('0'),
                            close=Decimal(str(row['close'])) if pd.notna(row['close']) else Decimal('0'),
                            volume=int(row['volume']) if pd.notna(row['volume']) else 0,
                            adj_close=None
                        )
                        StockPriceRepository.upsert(self.db, price_create)
                        saved_count += 1
                    except Exception as e:
                        logger.debug(f"{stock_id} {date}: 儲存失敗 - {str(e)}")
                        continue

                logger.info(f"✓ {stock_id}: 成功補齊 {saved_count} 筆記錄")
                time.sleep(self.delay_seconds)
                return True

            except Exception as e:
                logger.warning(f"{stock_id} 嘗試 {attempt + 1}/{self.retry_count} 失敗: {str(e)}")
                if attempt < self.retry_count - 1:
                    time.sleep(2 ** attempt)
                continue

        logger.error(f"✗ {stock_id}: 所有嘗試都失敗")
        return False

    def run(self):
        """執行檢查與補齊"""
        self.start_time = datetime.now()

        # 檢查 FinLab 客戶端
        if not self.client.is_available():
            logger.error("FinLab 客戶端無法使用，請檢查 API token 設定")
            return

        # 獲取股票清單
        stock_list = self.get_stock_list()
        self.total_stocks = len(stock_list)

        if self.total_stocks == 0:
            logger.error("沒有要檢查的股票")
            return

        logger.info("=" * 80)
        logger.info("開始資料完整性檢查")
        logger.info(f"股票數量: {self.total_stocks}")
        logger.info(f"最小記錄數: {self.min_records}")
        logger.info(f"自動修復: {'是' if self.auto_fix else '否'}")
        logger.info("=" * 80)

        # 第一階段：檢查所有股票
        logger.info("\n【階段 1/2】檢查資料完整性...")

        for i, stock_id in enumerate(stock_list, 1):
            status, record_count = self.check_stock_data(stock_id)

            if status == 'missing':
                self.missing_stocks.append((stock_id, record_count))
                logger.warning(f"[{i}/{self.total_stocks}] {stock_id}: ❌ 缺失（0 筆記錄）")
            elif status == 'incomplete':
                self.incomplete_stocks.append((stock_id, record_count))
                logger.warning(f"[{i}/{self.total_stocks}] {stock_id}: ⚠️  不完整（{record_count} 筆，少於 {self.min_records}）")
            elif status == 'complete':
                self.complete_stocks.append((stock_id, record_count))
                if i % 100 == 0:  # 每 100 檔顯示一次
                    logger.info(f"[{i}/{self.total_stocks}] {stock_id}: ✓ 完整（{record_count} 筆）")

            # 每 100 檔顯示進度
            if i % 100 == 0:
                self._print_progress(i)

        # 第二階段：自動修復（如果啟用）
        if self.auto_fix and (self.missing_stocks or self.incomplete_stocks):
            logger.info("\n【階段 2/2】自動補齊缺失資料...")

            needs_fix = self.missing_stocks + self.incomplete_stocks
            total_fix = len(needs_fix)

            for i, (stock_id, old_count) in enumerate(needs_fix, 1):
                logger.info(f"[{i}/{total_fix}] 修復 {stock_id}（目前 {old_count} 筆）...")

                success = self.sync_stock_data(stock_id)

                if success:
                    # 重新檢查記錄數
                    _, new_count = self.check_stock_data(stock_id)
                    self.fixed_stocks.append((stock_id, old_count, new_count))
                else:
                    self.failed_stocks.append((stock_id, old_count))

                # 每 10 檔顯示進度
                if i % 10 == 0:
                    logger.info(f"修復進度: {i}/{total_fix} ({i/total_fix*100:.1f}%)")

        # 最終報告
        self._print_final_report()

    def _print_progress(self, current: int):
        """印出檢查進度"""
        logger.info("-" * 60)
        logger.info(f"檢查進度: {current}/{self.total_stocks} ({current/self.total_stocks*100:.1f}%)")
        logger.info(f"完整: {len(self.complete_stocks)} | 不完整: {len(self.incomplete_stocks)} | 缺失: {len(self.missing_stocks)}")
        logger.info("-" * 60)

    def _print_final_report(self):
        """印出最終報告"""
        elapsed = datetime.now() - self.start_time

        logger.info("\n" + "=" * 80)
        logger.info("資料完整性檢查報告")
        logger.info("=" * 80)
        logger.info(f"檢查時間: {str(elapsed).split('.')[0]}")
        logger.info(f"總股票數: {self.total_stocks}")
        logger.info("")
        logger.info(f"✓ 資料完整: {len(self.complete_stocks)} ({len(self.complete_stocks)/self.total_stocks*100:.1f}%)")
        logger.info(f"⚠️  資料不完整: {len(self.incomplete_stocks)} ({len(self.incomplete_stocks)/self.total_stocks*100:.1f}%)")
        logger.info(f"❌ 完全缺失: {len(self.missing_stocks)} ({len(self.missing_stocks)/self.total_stocks*100:.1f}%)")

        if self.auto_fix:
            logger.info("")
            logger.info("修復結果:")
            logger.info(f"✓ 修復成功: {len(self.fixed_stocks)}")
            logger.info(f"✗ 修復失敗: {len(self.failed_stocks)}")

        # 顯示問題股票詳情
        if self.missing_stocks:
            logger.info("\n完全缺失的股票（前 20 檔）:")
            for stock_id, count in self.missing_stocks[:20]:
                logger.info(f"  - {stock_id}")
            if len(self.missing_stocks) > 20:
                logger.info(f"  ... 還有 {len(self.missing_stocks) - 20} 檔")

        if self.incomplete_stocks:
            logger.info("\n資料不完整的股票（前 20 檔）:")
            for stock_id, count in self.incomplete_stocks[:20]:
                logger.info(f"  - {stock_id}: {count} 筆（少 {self.min_records - count} 筆）")
            if len(self.incomplete_stocks) > 20:
                logger.info(f"  ... 還有 {len(self.incomplete_stocks) - 20} 檔")

        if self.auto_fix and self.failed_stocks:
            logger.info("\n修復失敗的股票:")
            for stock_id, old_count in self.failed_stocks:
                logger.info(f"  - {stock_id}: {old_count} 筆")

            # 提供重試指令
            failed_ids = [stock_id for stock_id, _ in self.failed_stocks]
            logger.info(f"\n重試失敗股票的指令:")
            logger.info(f"python scripts/check_and_fill_gaps.py --stocks {','.join(failed_ids[:10])} --auto-fix")

        logger.info("=" * 80)

        # 儲存報告到檔案
        self._save_report()

    def _save_report(self):
        """儲存報告到 JSON 檔案"""
        import json

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_stocks": self.total_stocks,
                "complete_stocks": len(self.complete_stocks),
                "incomplete_stocks": len(self.incomplete_stocks),
                "missing_stocks": len(self.missing_stocks),
                "fixed_stocks": len(self.fixed_stocks) if self.auto_fix else 0,
                "failed_stocks": len(self.failed_stocks) if self.auto_fix else 0,
            },
            "missing": [{"stock_id": sid, "count": cnt} for sid, cnt in self.missing_stocks],
            "incomplete": [{"stock_id": sid, "count": cnt} for sid, cnt in self.incomplete_stocks],
            "fixed": [{"stock_id": sid, "old_count": old, "new_count": new}
                     for sid, old, new in self.fixed_stocks] if self.auto_fix else [],
            "failed": [{"stock_id": sid, "count": cnt} for sid, cnt in self.failed_stocks] if self.auto_fix else [],
        }

        report_path = f"/tmp/data_gap_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"\n詳細報告已儲存: {report_path}")


def main():
    """主程式"""
    parser = argparse.ArgumentParser(
        description="檢查並補齊股票歷史資料的缺失",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 只檢查，不補齊
  python scripts/check_and_fill_gaps.py --report-only

  # 檢查並自動補齊所有缺失
  python scripts/check_and_fill_gaps.py --auto-fix

  # 補齊特定股票
  python scripts/check_and_fill_gaps.py --stocks 2330,2317,2454 --auto-fix

  # 設定最小記錄數門檻
  python scripts/check_and_fill_gaps.py --min-records 4000 --auto-fix
        """
    )

    parser.add_argument(
        '--years',
        type=int,
        default=20,
        help='預期的歷史年數 (預設: 20)'
    )
    parser.add_argument(
        '--min-records',
        type=int,
        default=4500,
        help='預期的最小記錄數 (預設: 4500)'
    )
    parser.add_argument(
        '--stocks',
        type=str,
        help='指定要檢查的股票 ID，逗號分隔（例如: 2330,2317,2454）'
    )
    parser.add_argument(
        '--auto-fix',
        action='store_true',
        help='自動補齊缺失的資料'
    )
    parser.add_argument(
        '--report-only',
        action='store_true',
        help='只產生報告，不補齊資料'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=0.5,
        help='API 呼叫延遲秒數 (預設: 0.5)'
    )
    parser.add_argument(
        '--retry',
        type=int,
        default=3,
        help='失敗重試次數 (預設: 3)'
    )

    args = parser.parse_args()

    # 解析股票清單
    stock_ids = None
    if args.stocks:
        stock_ids = [s.strip() for s in args.stocks.split(',')]

    # 執行檢查
    with DataGapChecker(
        years=args.years,
        min_records=args.min_records,
        stock_ids=stock_ids,
        auto_fix=args.auto_fix and not args.report_only,
        delay_seconds=args.delay,
        retry_count=args.retry
    ) as checker:
        checker.run()


if __name__ == "__main__":
    main()
