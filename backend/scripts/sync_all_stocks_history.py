#!/usr/bin/env python3
"""
批次同步所有股票的歷史資料到資料庫

Usage:
    # 同步所有股票，20 年歷史資料
    python scripts/sync_all_stocks_history.py

    # 同步前 100 檔股票，10 年歷史資料
    python scripts/sync_all_stocks_history.py --limit 100 --years 10

    # 從特定股票開始（續傳功能）
    python scripts/sync_all_stocks_history.py --start-from 2330

    # 只同步特定股票
    python scripts/sync_all_stocks_history.py --stocks 2330,2317,2454
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
from typing import List, Optional
import pandas as pd
from loguru import logger

from app.db.session import SessionLocal
from app.repositories.stock import StockRepository
from app.repositories.stock_price import StockPriceRepository
from app.services.finlab_client import FinLabClient
from app.schemas.stock_price import StockPriceCreate


# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)
logger.add(
    "/tmp/sync_all_stocks_{time}.log",
    rotation="100 MB",
    retention="30 days",
    level="DEBUG"
)


class StockHistorySyncer:
    """股票歷史資料批次同步器"""

    def __init__(
        self,
        years: int = 20,
        limit: Optional[int] = None,
        start_from: Optional[str] = None,
        stock_ids: Optional[List[str]] = None,
        batch_size: int = 10,
        retry_count: int = 3,
        delay_seconds: float = 0.5
    ):
        """
        初始化同步器

        Args:
            years: 要同步的歷史年數
            limit: 限制同步的股票數量（None = 全部）
            start_from: 從特定股票 ID 開始（續傳功能）
            stock_ids: 指定要同步的股票 ID 列表
            batch_size: 批次大小（每批次同步幾檔股票）
            retry_count: 失敗重試次數
            delay_seconds: 每次 API 呼叫的延遲（避免超過速率限制）
        """
        self.years = years
        self.limit = limit
        self.start_from = start_from
        self.stock_ids = stock_ids
        self.batch_size = batch_size
        self.retry_count = retry_count
        self.delay_seconds = delay_seconds

        self.db = SessionLocal()
        self.client = FinLabClient()

        # Statistics
        self.total_stocks = 0
        self.processed_stocks = 0
        self.successful_stocks = 0
        self.failed_stocks = 0
        self.total_records = 0
        self.start_time = None
        self.failed_stock_ids = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()

    def get_stock_list(self) -> List[str]:
        """獲取要同步的股票清單"""
        if self.stock_ids:
            # 使用指定的股票清單
            logger.info(f"使用指定的股票清單: {len(self.stock_ids)} 檔")
            return self.stock_ids

        # 從資料庫獲取所有股票
        stocks = StockRepository.get_all(
            self.db,
            skip=0,
            limit=10000,
            is_active='active'
        )

        stock_ids = [stock.stock_id for stock in stocks]

        # 如果指定了起始股票，從該股票開始
        if self.start_from:
            try:
                start_index = stock_ids.index(self.start_from)
                stock_ids = stock_ids[start_index:]
                logger.info(f"從股票 {self.start_from} 開始（索引 {start_index}）")
            except ValueError:
                logger.warning(f"找不到起始股票 {self.start_from}，從頭開始")

        # 限制數量
        if self.limit:
            stock_ids = stock_ids[:self.limit]

        logger.info(f"總共要同步 {len(stock_ids)} 檔股票")
        return stock_ids

    def sync_stock_history(self, stock_id: str) -> bool:
        """
        同步單一股票的歷史資料

        Args:
            stock_id: 股票代碼

        Returns:
            是否成功
        """
        # 計算日期範圍
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.years * 365)

        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        logger.info(f"開始同步 {stock_id} ({start_date_str} ~ {end_date_str})")

        for attempt in range(self.retry_count):
            try:
                # 從 FinLab 獲取 OHLCV 資料
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

                self.total_records += saved_count
                logger.info(f"✓ {stock_id}: 成功儲存 {saved_count} 筆記錄")

                # 延遲避免超過速率限制
                time.sleep(self.delay_seconds)
                return True

            except Exception as e:
                logger.warning(f"{stock_id} 嘗試 {attempt + 1}/{self.retry_count} 失敗: {str(e)}")
                if attempt < self.retry_count - 1:
                    time.sleep(2 ** attempt)  # 指數退避
                continue

        logger.error(f"✗ {stock_id}: 所有嘗試都失敗")
        return False

    def run(self):
        """執行批次同步"""
        self.start_time = datetime.now()

        # 檢查 FinLab 客戶端
        if not self.client.is_available():
            logger.error("FinLab 客戶端無法使用，請檢查 API token 設定")
            return

        # 獲取股票清單
        stock_list = self.get_stock_list()
        self.total_stocks = len(stock_list)

        if self.total_stocks == 0:
            logger.error("沒有要同步的股票")
            return

        logger.info("=" * 80)
        logger.info(f"開始批次同步")
        logger.info(f"股票數量: {self.total_stocks}")
        logger.info(f"歷史年數: {self.years} 年")
        logger.info(f"批次大小: {self.batch_size}")
        logger.info(f"延遲時間: {self.delay_seconds} 秒/股票")
        logger.info(f"預計時間: {self.total_stocks * self.delay_seconds / 60:.1f} 分鐘")
        logger.info("=" * 80)

        # 分批處理
        for i in range(0, self.total_stocks, self.batch_size):
            batch = stock_list[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (self.total_stocks + self.batch_size - 1) // self.batch_size

            logger.info(f"\n批次 {batch_num}/{total_batches} ({len(batch)} 檔股票)")

            for stock_id in batch:
                self.processed_stocks += 1
                progress = self.processed_stocks / self.total_stocks * 100

                logger.info(f"[{self.processed_stocks}/{self.total_stocks}] ({progress:.1f}%) {stock_id}")

                success = self.sync_stock_history(stock_id)

                if success:
                    self.successful_stocks += 1
                else:
                    self.failed_stocks += 1
                    self.failed_stock_ids.append(stock_id)

                # 顯示進度統計
                if self.processed_stocks % 10 == 0:
                    self._print_progress()

        # 最終報告
        self._print_final_report()

    def _print_progress(self):
        """印出進度統計"""
        elapsed = datetime.now() - self.start_time
        stocks_per_second = self.processed_stocks / elapsed.total_seconds()
        remaining_stocks = self.total_stocks - self.processed_stocks
        eta_seconds = remaining_stocks / stocks_per_second if stocks_per_second > 0 else 0

        logger.info("-" * 60)
        logger.info(f"進度: {self.processed_stocks}/{self.total_stocks} ({self.processed_stocks/self.total_stocks*100:.1f}%)")
        logger.info(f"成功: {self.successful_stocks} | 失敗: {self.failed_stocks}")
        logger.info(f"記錄數: {self.total_records:,}")
        logger.info(f"已用時間: {str(elapsed).split('.')[0]}")
        logger.info(f"預計剩餘: {timedelta(seconds=int(eta_seconds))}")
        logger.info("-" * 60)

    def _print_final_report(self):
        """印出最終報告"""
        elapsed = datetime.now() - self.start_time

        logger.info("\n" + "=" * 80)
        logger.info("同步完成！")
        logger.info("=" * 80)
        logger.info(f"總股票數: {self.total_stocks}")
        logger.info(f"成功: {self.successful_stocks} ({self.successful_stocks/self.total_stocks*100:.1f}%)")
        logger.info(f"失敗: {self.failed_stocks} ({self.failed_stocks/self.total_stocks*100:.1f}%)")
        logger.info(f"總記錄數: {self.total_records:,}")
        logger.info(f"總用時: {str(elapsed).split('.')[0]}")
        logger.info(f"平均速度: {self.total_records / elapsed.total_seconds():.1f} 記錄/秒")
        logger.info("=" * 80)

        if self.failed_stock_ids:
            logger.warning(f"\n失敗的股票 ({len(self.failed_stock_ids)}):")
            logger.warning(", ".join(self.failed_stock_ids))
            logger.warning("\n可使用以下指令重試失敗的股票:")
            logger.warning(f"python scripts/sync_all_stocks_history.py --stocks {','.join(self.failed_stock_ids[:10])}")


def main():
    """主程式"""
    parser = argparse.ArgumentParser(
        description="批次同步所有股票的歷史資料到資料庫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 同步所有股票，20 年歷史資料
  python scripts/sync_all_stocks_history.py

  # 同步前 100 檔股票，10 年歷史資料
  python scripts/sync_all_stocks_history.py --limit 100 --years 10

  # 從特定股票開始（續傳功能）
  python scripts/sync_all_stocks_history.py --start-from 2330

  # 只同步特定股票
  python scripts/sync_all_stocks_history.py --stocks 2330,2317,2454
        """
    )

    parser.add_argument(
        '--years',
        type=int,
        default=20,
        help='要同步的歷史年數 (預設: 20)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='限制同步的股票數量（預設: 全部）'
    )
    parser.add_argument(
        '--start-from',
        type=str,
        help='從特定股票 ID 開始（續傳功能）'
    )
    parser.add_argument(
        '--stocks',
        type=str,
        help='指定要同步的股票 ID，逗號分隔（例如: 2330,2317,2454）'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='批次大小 (預設: 10)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=0.5,
        help='每次 API 呼叫的延遲秒數 (預設: 0.5)'
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

    # 執行同步
    with StockHistorySyncer(
        years=args.years,
        limit=args.limit,
        start_from=args.start_from,
        stock_ids=stock_ids,
        batch_size=args.batch_size,
        retry_count=args.retry,
        delay_seconds=args.delay
    ) as syncer:
        syncer.run()


if __name__ == "__main__":
    main()
