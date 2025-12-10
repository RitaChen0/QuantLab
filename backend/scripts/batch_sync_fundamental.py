#!/usr/bin/env python3
"""
批次同步所有股票的財務指標數據

特性：
- 分批處理（每批 100 檔股票）
- 進度追蹤與斷點續傳
- 失敗重試機制
- API 配額監控
- 預估剩餘時間
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set

# Add backend to path
sys.path.insert(0, '/app')

from app.db.session import SessionLocal
from app.services.fundamental_service import FundamentalService
from app.services.finlab_client import FinLabClient
from loguru import logger


class BatchSyncProgress:
    """進度追蹤"""

    def __init__(self, progress_file: str = "/tmp/batch_sync_progress.json"):
        self.progress_file = Path(progress_file)
        self.data = self.load()

    def load(self) -> Dict:
        """載入進度"""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {
            "completed_stocks": [],
            "failed_stocks": [],
            "current_batch": 0,
            "total_synced": 0,
            "start_time": None,
            "last_update": None
        }

    def save(self):
        """儲存進度"""
        self.data["last_update"] = datetime.now().isoformat()
        with open(self.progress_file, 'w') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def mark_completed(self, stock_id: str, synced_count: int):
        """標記股票已完成"""
        if stock_id not in self.data["completed_stocks"]:
            self.data["completed_stocks"].append(stock_id)
        self.data["total_synced"] += synced_count
        self.save()

    def mark_failed(self, stock_id: str, error: str):
        """標記股票失敗"""
        self.data["failed_stocks"].append({
            "stock_id": stock_id,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        self.save()

    def get_completed_stocks(self) -> Set[str]:
        """取得已完成的股票"""
        return set(self.data["completed_stocks"])

    def reset(self):
        """重置進度"""
        self.data = {
            "completed_stocks": [],
            "failed_stocks": [],
            "current_batch": 0,
            "total_synced": 0,
            "start_time": datetime.now().isoformat(),
            "last_update": None
        }
        self.save()


def get_all_stock_ids() -> List[str]:
    """取得所有股票代碼（過濾掉 ETF 和特別股）"""
    logger.info("正在取得股票清單...")

    try:
        client = FinLabClient()
        stocks_df = client.get_stock_list()

        # Get all stock IDs
        all_stock_ids = stocks_df.index.tolist()

        # Filter out ETFs and special stocks
        # - ETFs: start with '00' (e.g., 0050, 00721B)
        # - Special stocks: end with 'B', 'C', 'P' (e.g., 00679B)
        normal_stocks = [
            stock_id for stock_id in all_stock_ids
            if not (
                stock_id.startswith('00') or  # ETFs
                stock_id.endswith('B') or      # Special stocks (B shares)
                stock_id.endswith('C') or      # Special stocks (C shares)
                stock_id.endswith('P')         # Special stocks (preferred)
            )
        ]

        excluded_count = len(all_stock_ids) - len(normal_stocks)
        logger.info(f"✅ 取得 {len(all_stock_ids)} 檔標的")
        logger.info(f"📈 一般股票: {len(normal_stocks)} 檔")
        logger.info(f"⚠️  已過濾: {excluded_count} 檔 (ETF + 特別股)")

        return normal_stocks
    except Exception as e:
        logger.error(f"❌ 取得股票清單失敗: {e}")
        raise


def sync_single_stock(
    db,
    stock_id: str,
    indicators: List[str],
    progress: BatchSyncProgress
) -> int:
    """同步單一股票的所有指標"""
    service = FundamentalService(db)
    synced_count = 0

    for indicator in indicators:
        try:
            count = service.sync_indicator_data(
                stock_id=stock_id,
                indicator=indicator,
                start_date=None,  # 全部歷史數據
                end_date=None
            )
            synced_count += count

        except Exception as e:
            logger.warning(f"⚠️  {stock_id} - {indicator} 失敗: {str(e)[:50]}")
            continue

    return synced_count


def batch_sync_all_stocks(
    batch_size: int = 100,
    batch_delay: int = 60,
    resume: bool = True,
    max_stocks: int = None
):
    """
    批次同步所有股票

    Args:
        batch_size: 每批處理的股票數量
        batch_delay: 批次之間的延遲（秒）
        resume: 是否從上次中斷處繼續
        max_stocks: 最大處理股票數（None = 全部）
    """

    logger.info("=" * 80)
    logger.info("🚀 開始批次同步財務指標數據")
    logger.info("=" * 80)

    # 初始化
    progress = BatchSyncProgress()

    if not resume:
        logger.warning("⚠️  重置進度，從頭開始")
        progress.reset()
    else:
        logger.info(f"📋 載入進度: 已完成 {len(progress.get_completed_stocks())} 檔股票")

    # 取得所有股票
    all_stock_ids = get_all_stock_ids()

    # 限制數量（測試用）
    if max_stocks:
        all_stock_ids = all_stock_ids[:max_stocks]
        logger.info(f"⚠️  測試模式：僅處理前 {max_stocks} 檔股票")

    # 過濾已完成的股票
    completed = progress.get_completed_stocks()
    remaining_stocks = [s for s in all_stock_ids if s not in completed]

    logger.info(f"📊 總計: {len(all_stock_ids)} 檔")
    logger.info(f"✅ 已完成: {len(completed)} 檔")
    logger.info(f"⏳ 待處理: {len(remaining_stocks)} 檔")

    if len(remaining_stocks) == 0:
        logger.info("🎉 所有股票已同步完成！")
        return

    # 取得指標清單
    indicators = FinLabClient.get_common_fundamental_indicators()
    logger.info(f"📈 指標數量: {len(indicators)} 個")

    # 預估時間
    avg_time_per_stock = 2.5  # 秒
    total_time = len(remaining_stocks) * avg_time_per_stock
    hours = int(total_time // 3600)
    minutes = int((total_time % 3600) // 60)
    logger.info(f"⏱️  預估時間: {hours} 小時 {minutes} 分鐘")
    logger.info(f"⚙️  批次大小: {batch_size} 檔/批")
    logger.info(f"⏸️  批次延遲: {batch_delay} 秒")

    # 詢問確認
    print("\n" + "=" * 80)
    print("⚠️  警告：此操作將執行數小時，請確保：")
    print("   1. Docker 容器保持運行")
    print("   2. 網路連線穩定")
    print("   3. FinLab API 配額充足（建議 > 1000 MB）")
    print("=" * 80)
    confirm = input("\n是否繼續？(yes/no): ")

    if confirm.lower() != 'yes':
        logger.info("❌ 使用者取消")
        return

    # 開始處理
    from app.db.session import ensure_models_imported
    ensure_models_imported()  # Ensure all models are loaded

    db = SessionLocal()
    start_time = time.time()

    try:
        # 分批處理
        for batch_idx, i in enumerate(range(0, len(remaining_stocks), batch_size)):
            batch = remaining_stocks[i:i + batch_size]
            batch_num = batch_idx + 1
            total_batches = (len(remaining_stocks) + batch_size - 1) // batch_size

            logger.info("")
            logger.info("=" * 80)
            logger.info(f"📦 批次 {batch_num}/{total_batches} - 處理 {len(batch)} 檔股票")
            logger.info("=" * 80)

            batch_start = time.time()

            for stock_idx, stock_id in enumerate(batch):
                stock_num = i + stock_idx + 1
                total_stocks = len(remaining_stocks)

                try:
                    logger.info(f"[{stock_num}/{total_stocks}] 🔄 處理 {stock_id}...")

                    synced = sync_single_stock(db, stock_id, indicators, progress)
                    progress.mark_completed(stock_id, synced)

                    # 計算進度
                    elapsed = time.time() - start_time
                    avg_time = elapsed / (stock_num)
                    remaining = (total_stocks - stock_num) * avg_time

                    remaining_hours = int(remaining // 3600)
                    remaining_mins = int((remaining % 3600) // 60)

                    logger.info(
                        f"✅ {stock_id} 完成: {synced} 筆 | "
                        f"進度: {stock_num}/{total_stocks} ({stock_num*100//total_stocks}%) | "
                        f"預估剩餘: {remaining_hours}h {remaining_mins}m"
                    )

                    # 小延遲避免 API 過載
                    time.sleep(0.5)

                except Exception as e:
                    error_msg = str(e)[:200]
                    logger.error(f"❌ {stock_id} 失敗: {error_msg}")
                    progress.mark_failed(stock_id, error_msg)
                    continue

            batch_elapsed = time.time() - batch_start
            logger.info(f"✅ 批次 {batch_num} 完成，耗時 {batch_elapsed:.1f} 秒")

            # 批次間延遲（最後一批除外）
            if batch_num < total_batches:
                logger.info(f"⏸️  等待 {batch_delay} 秒後繼續下一批...")
                time.sleep(batch_delay)

        # 完成統計
        total_elapsed = time.time() - start_time
        hours = int(total_elapsed // 3600)
        minutes = int((total_elapsed % 3600) // 60)

        logger.info("")
        logger.info("=" * 80)
        logger.info("🎉 批次同步完成！")
        logger.info("=" * 80)
        logger.info(f"✅ 成功: {len(progress.get_completed_stocks())} 檔")
        logger.info(f"❌ 失敗: {len(progress.data['failed_stocks'])} 檔")
        logger.info(f"📊 總數據: {progress.data['total_synced']} 筆")
        logger.info(f"⏱️  總耗時: {hours} 小時 {minutes} 分鐘")

        # 顯示失敗清單
        if progress.data['failed_stocks']:
            logger.warning(f"\n失敗的股票（前 10 筆）：")
            for item in progress.data['failed_stocks'][:10]:
                logger.warning(f"  - {item['stock_id']}: {item['error'][:100]}")

    except KeyboardInterrupt:
        logger.warning("\n⚠️  使用者中斷！進度已儲存")
        logger.info(f"📋 已完成: {len(progress.get_completed_stocks())} 檔")
        logger.info(f"💾 進度檔: {progress.progress_file}")
        logger.info("💡 下次執行時將自動續傳")

    except Exception as e:
        logger.error(f"❌ 發生錯誤: {e}")
        raise

    finally:
        db.close()


def show_progress():
    """顯示當前進度"""
    progress = BatchSyncProgress()

    print("\n" + "=" * 80)
    print("📊 批次同步進度")
    print("=" * 80)
    print(f"✅ 已完成股票: {len(progress.get_completed_stocks())} 檔")
    print(f"❌ 失敗股票: {len(progress.data['failed_stocks'])} 檔")
    print(f"📊 累計數據: {progress.data['total_synced']} 筆")
    print(f"🕐 開始時間: {progress.data.get('start_time', 'N/A')}")
    print(f"🕐 最後更新: {progress.data.get('last_update', 'N/A')}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='批次同步財務指標數據')
    parser.add_argument('--batch-size', type=int, default=100, help='每批處理股票數')
    parser.add_argument('--batch-delay', type=int, default=60, help='批次間延遲（秒）')
    parser.add_argument('--reset', action='store_true', help='重置進度從頭開始')
    parser.add_argument('--max-stocks', type=int, help='最大處理股票數（測試用）')
    parser.add_argument('--status', action='store_true', help='顯示進度')

    args = parser.parse_args()

    if args.status:
        show_progress()
    else:
        batch_sync_all_stocks(
            batch_size=args.batch_size,
            batch_delay=args.batch_delay,
            resume=not args.reset,
            max_stocks=args.max_stocks
        )
