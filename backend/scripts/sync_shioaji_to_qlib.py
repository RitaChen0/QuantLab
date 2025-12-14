#!/usr/bin/env python3
"""
Shioaji 到 Qlib 獨立同步工具（智慧增量同步版）

功能：
1. 從 Shioaji API 獲取股票 1 分鐘 K 線數據
2. 同時存儲到 PostgreSQL 和 Qlib 二進制格式
3. 🧠 智慧增量同步：自動檢測現有數據的最後日期，僅同步缺失部分
4. 專門在收盤後運行，截取當天所有股票的分鐘線資料

使用範例：
    # 🧠 智慧增量同步（推薦，收盤後運行）
    python sync_shioaji_to_qlib.py --smart

    # 智慧同步到指定日期
    python sync_shioaji_to_qlib.py --smart --end-date 2025-12-13

    # 傳統模式：同步今天的數據
    python sync_shioaji_to_qlib.py --today

    # 同步指定日期範圍
    python sync_shioaji_to_qlib.py --start-date 2025-12-01 --end-date 2025-12-13

    # 測試模式（僅同步 5 檔股票）
    python sync_shioaji_to_qlib.py --smart --test

定時任務（Cron）：
    # 每個交易日 15:00 自動智慧增量同步
    0 15 * * 1-5 cd /home/ubuntu/QuantLab/backend && python scripts/sync_shioaji_to_qlib.py --smart
"""

import sys
import os
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple
import argparse
import time
import struct

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from loguru import logger
from tqdm import tqdm
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# QuantLab 模組
from app.core.config import settings
from app.db.base import import_models
from app.services.shioaji_client import ShioajiClient
from app.repositories.stock_minute_price import StockMinutePriceRepository
from app.schemas.stock_minute_price import StockMinutePriceCreate

# Qlib 模組
import qlib
from qlib.config import REG_CN
from qlib.data.storage.file_storage import FileFeatureStorage
from qlib.data import D

# 導入所有模型
import_models()

# Qlib 特徵列表（分鐘線）
QLIB_MINUTE_FEATURES = ['open', 'high', 'low', 'close', 'volume']

# 日誌配置
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)
logger.add(
    "/tmp/shioaji_to_qlib_{time}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG"
)


class ShioajiToQlibSyncer:
    """Shioaji 到 Qlib 同步器（支援智慧增量同步）"""

    def __init__(
        self,
        qlib_data_dir: str = "/data/qlib/tw_stock_minute",
        db_url: Optional[str] = None,
        skip_db: bool = False
    ):
        """
        初始化同步器

        Args:
            qlib_data_dir: Qlib 數據目錄
            db_url: 資料庫連接字串（None 則使用環境變數）
            skip_db: 是否跳過資料庫存儲（僅更新 Qlib）
        """
        self.qlib_data_dir = Path(qlib_data_dir)
        self.skip_db = skip_db

        # 初始化資料庫連接
        if not skip_db:
            self.db_url = db_url or settings.DATABASE_URL
            self.engine = create_engine(self.db_url, pool_pre_ping=True)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            self.db_session = SessionLocal()
            self.repo = StockMinutePriceRepository  # 靜態方法，不需實例化
        else:
            logger.info("⚠️  跳過資料庫存儲，僅更新 Qlib")
            self.engine = None
            self.db_session = None
            self.repo = None

        # 初始化 Qlib
        self._init_qlib()

        # Shioaji 客戶端（延遲初始化）
        self.shioaji_client = None

    def _init_qlib(self):
        """初始化 Qlib 環境"""
        try:
            self.qlib_data_dir.mkdir(parents=True, exist_ok=True)
            qlib.init(provider_uri=str(self.qlib_data_dir), region=REG_CN)
            logger.info(f"✅ Qlib 已初始化: {self.qlib_data_dir}")
        except Exception as e:
            logger.error(f"❌ Qlib 初始化失敗: {e}")
            raise

    def get_stock_list(self) -> List[str]:
        """
        從資料庫獲取股票清單

        Returns:
            股票代碼列表
        """
        if self.skip_db or not self.engine:
            logger.warning("⚠️  無法從資料庫獲取股票清單，返回 Top 50")
            # Fallback: 返回熱門股票
            return [
                '2330', '2317', '2454', '2412', '3008',
                '2308', '2882', '1301', '1303', '2002',
                '2886', '2881', '2891', '2892', '2885',
                '2884', '2887', '2883', '5880', '2912',
                '2880', '2382', '2395', '6505', '3045',
                '1216', '2357', '1326', '2303', '2379',
                '2408', '2207', '2327', '3711', '2474',
                '2801', '2609', '2615', '2603', '4904',
                '9910', '2888', '2345', '6669', '2409',
                '3037', '2377', '2353', '5871', '2324',
            ]

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT DISTINCT stock_id
                    FROM stock_prices
                    ORDER BY stock_id
                """))
                stock_ids = [row[0] for row in result.fetchall()]
                logger.info(f"✅ 從資料庫獲取 {len(stock_ids)} 檔股票")
                return stock_ids
        except Exception as e:
            logger.error(f"❌ 獲取股票清單失敗: {e}")
            return []

    def get_db_last_date(self, stock_id: str) -> Optional[date]:
        """
        獲取 PostgreSQL 中該股票的最後日期

        Args:
            stock_id: 股票代碼

        Returns:
            最後日期或 None
        """
        if self.skip_db or not self.engine:
            return None

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT MAX(datetime::date) as last_date
                    FROM stock_minute_prices
                    WHERE stock_id = :stock_id
                """), {"stock_id": stock_id})
                row = result.fetchone()
                if row and row[0]:
                    return row[0]
                return None
        except Exception as e:
            logger.debug(f"無法獲取 {stock_id} 的 PostgreSQL 最後日期: {e}")
            return None

    def get_qlib_last_date(self, stock_id: str) -> Optional[date]:
        """
        獲取 Qlib 中該股票的最後日期

        Args:
            stock_id: 股票代碼

        Returns:
            最後日期或 None
        """
        try:
            # 嘗試讀取該股票的收盤價數據
            df = D.features([stock_id], ['$close'], freq='1min')

            if df is None or df.empty:
                return None

            # 獲取最後一個日期時間
            last_datetime = df.index.get_level_values('datetime').max()
            return last_datetime.date()
        except Exception:
            # 如果讀取失敗，表示數據不存在
            return None

    def determine_sync_range(
        self,
        stock_id: str,
        user_end_date: date,
        smart_mode: bool = False
    ) -> Tuple[Optional[date], Optional[date], str]:
        """
        智慧判斷需要同步的日期範圍

        Args:
            stock_id: 股票代碼
            user_end_date: 用戶指定的結束日期（通常是今天）
            smart_mode: 是否使用智慧模式

        Returns:
            (開始日期, 結束日期, 同步類型)
            同步類型: 'full', 'incremental', 'skip'
        """
        if not smart_mode:
            # 非智慧模式，返回 None 表示使用用戶指定的日期範圍
            return (None, None, 'user_specified')

        # 檢查 PostgreSQL 最後日期
        db_last_date = self.get_db_last_date(stock_id)

        # 檢查 Qlib 最後日期
        qlib_last_date = self.get_qlib_last_date(stock_id)

        # 取兩者中較早的日期作為參考點
        if db_last_date and qlib_last_date:
            last_date = min(db_last_date, qlib_last_date)
        elif db_last_date:
            last_date = db_last_date
        elif qlib_last_date:
            last_date = qlib_last_date
        else:
            # 完全沒有數據，首次同步（預設從 6 個月前開始）
            start_date = user_end_date - timedelta(days=180)
            return (start_date, user_end_date, 'full')

        # 檢查是否已是最新（使用嚴格的 > 而非 >=）
        if last_date > user_end_date:
            return (None, None, 'skip')

        # 增量同步（從最後日期開始，允許覆蓋最後一天，確保幂等性）
        # 注意：使用 ON CONFLICT DO NOTHING，重複數據會被自動跳過
        start_date = last_date
        return (start_date, user_end_date, 'incremental')

    def _is_futures(self, stock_id: str) -> bool:
        """判斷是否為期貨"""
        return stock_id in ['TX', 'MTX']

    def _get_contract_type(self, stock_id: str) -> str:
        """獲取契約類型"""
        return 'futures' if self._is_futures(stock_id) else 'stock'

    def fetch_minute_data(
        self,
        stock_id: str,
        start_date: date,
        end_date: date
    ) -> Optional[Tuple[pd.DataFrame, str]]:
        """
        從 Shioaji API 獲取分鐘 K 線數據（支持股票和期貨）

        Args:
            stock_id: 標的代碼（股票或期貨）
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            (DataFrame, actual_stock_id): 數據和實際標的代碼
            - 股票: ("2330", "2330")
            - 期貨: ("TX", "TX202512")  ← 返回實際月份合約代碼
        """
        if not self.shioaji_client:
            self.shioaji_client = ShioajiClient()

        if not self.shioaji_client.is_available():
            logger.error("❌ Shioaji 客戶端未初始化")
            return None

        # 判斷契約類型
        contract_type = self._get_contract_type(stock_id)
        is_futures = self._is_futures(stock_id)

        # 對於期貨，獲取實際月份合約代碼
        actual_stock_id = stock_id
        if is_futures:
            contract_id = self.shioaji_client.get_futures_contract_id(stock_id)
            if contract_id:
                actual_stock_id = contract_id
                logger.info(f"  [CONTRACT] {stock_id} → {actual_stock_id}")
            else:
                logger.error(f"  [CONTRACT] Failed to get contract ID for {stock_id}")
                return None

        try:
            # 設定時間範圍
            # 期貨：08:45-次日05:00（完整日盤 + 夜盤）
            # 股票：09:00-13:30（僅日盤）
            if is_futures:
                start_datetime = datetime.combine(start_date, datetime.min.time().replace(hour=8, minute=45))
                # 期货夜盘延续到次日 05:00，因此 end_datetime 需要 +1 天
                end_datetime = datetime.combine(end_date + timedelta(days=1), datetime.min.time().replace(hour=5, minute=0))
                logger.debug(f"  期貨 {stock_id}: 時間範圍 {start_datetime} ~ {end_datetime}（含完整夜盤）")
            else:
                start_datetime = datetime.combine(start_date, datetime.min.time().replace(hour=9, minute=0))
                end_datetime = datetime.combine(end_date, datetime.min.time().replace(hour=13, minute=30))

            # 調用 Shioaji API
            df = self.shioaji_client.get_kbars(
                stock_id=stock_id,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                timeframe='1min',
                contract_type=contract_type  # ⭐ 傳遞契約類型
            )

            if df is None or df.empty:
                logger.debug(f"  ⚠️  {stock_id}: 無數據")
                return None

            logger.debug(f"  ✓ {stock_id}: 獲取 {len(df)} 筆分鐘數據")
            # 🆕 返回 DataFrame 和實際合約 ID
            return df, actual_stock_id

        except Exception as e:
            logger.error(f"  ❌ {stock_id}: 獲取數據失敗 - {e}")
            return None

    def save_to_postgresql(self, stock_id: str, df: pd.DataFrame) -> int:
        """
        保存數據到 PostgreSQL（使用 ON CONFLICT 忽略重複）

        使用策略：
        1. 使用 SQLAlchemy Core 的 INSERT ... ON CONFLICT DO NOTHING
        2. 向量化數據準備（避免 iterrows，性能提升 100 倍）
        3. 處理 NaN 值（防止運行時錯誤）

        Args:
            stock_id: 股票代碼
            df: 數據 DataFrame

        Returns:
            成功插入的記錄數
        """
        if self.skip_db or not self.repo:
            return 0

        try:
            if df.empty:
                return 0

            from sqlalchemy.dialects.postgresql import insert
            from app.models.stock_minute_price import StockMinutePrice

            # 向量化準備數據（比 iterrows 快 100 倍）
            df_copy = df.copy()
            df_copy['stock_id'] = stock_id
            df_copy['timeframe'] = '1min'

            # 確保數據類型正確
            df_copy['open'] = df_copy['open'].astype(float)
            df_copy['high'] = df_copy['high'].astype(float)
            df_copy['low'] = df_copy['low'].astype(float)
            df_copy['close'] = df_copy['close'].astype(float)

            # 處理 NaN 值（volume 必須是整數）
            df_copy['volume'] = df_copy['volume'].fillna(0).astype(int)

            # 選擇需要的欄位並轉換為字典列表
            records = df_copy[['stock_id', 'datetime', 'timeframe', 'open', 'high', 'low', 'close', 'volume']].to_dict('records')

            # 分批插入（每批 1,000 筆）
            batch_size = 1000
            total_inserted = 0

            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]

                # 使用 SQLAlchemy Core 的 ON CONFLICT DO UPDATE
                # 允許更新數據源修正的歷史數據
                stmt = insert(StockMinutePrice).values(batch)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['stock_id', 'datetime', 'timeframe'],
                    set_={
                        'open': stmt.excluded.open,
                        'high': stmt.excluded.high,
                        'low': stmt.excluded.low,
                        'close': stmt.excluded.close,
                        'volume': stmt.excluded.volume,
                    }
                )

                result = self.db_session.execute(stmt)
                total_inserted += result.rowcount

                # 每批提交一次（避免大事務導致內存溢出）
                self.db_session.commit()

            skipped = len(records) - total_inserted
            if skipped > 0:
                logger.debug(f"  ✓ PostgreSQL: 插入 {total_inserted} 筆（跳過 {skipped} 筆重複）")
            else:
                logger.debug(f"  ✓ PostgreSQL: 插入 {total_inserted} 筆")
            return total_inserted

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"  ❌ PostgreSQL: 保存失敗 - {e}")
            return 0

    def save_to_qlib(
        self,
        stock_id: str,
        df: pd.DataFrame,
        trading_minutes: pd.DatetimeIndex
    ) -> bool:
        """
        保存數據到 Qlib 格式

        Args:
            stock_id: 股票代碼
            df: 數據 DataFrame
            trading_minutes: 完整的交易分鐘索引

        Returns:
            是否成功
        """
        try:
            instrument = stock_id.lower()

            # 創建股票目錄
            features_dir = self.qlib_data_dir / 'features' / instrument
            features_dir.mkdir(parents=True, exist_ok=True)

            # 將 DataFrame 對齊到完整交易分鐘索引
            df = df.set_index('datetime')
            df = df.reindex(trading_minutes)

            # 為每個特徵寫入數據
            for field in QLIB_MINUTE_FEATURES:
                if field not in df.columns:
                    continue

                # 提取特徵數據
                data = df[field].values.astype(np.float32)

                # 使用 FileFeatureStorage 寫入
                storage = FileFeatureStorage(
                    instrument=instrument,
                    field=field,
                    freq="1min"
                )

                try:
                    storage.write(data)
                except Exception as e:
                    logger.warning(f"  ⚠️  Qlib {field}: 寫入失敗 - {e}")
                    continue

            logger.debug(f"  ✓ Qlib: {len(df)} 個時間點")
            return True

        except Exception as e:
            logger.error(f"  ❌ Qlib: 保存失敗 - {e}")
            return False

    def generate_trading_minutes(
        self,
        start_date: date,
        end_date: date,
        is_futures: bool = False
    ) -> pd.DatetimeIndex:
        """
        生成交易分鐘索引（支持股票和期货）

        Args:
            start_date: 開始日期
            end_date: 結束日期
            is_futures: 是否為期貨（True=期貨，False=股票）

        Returns:
            交易分鐘索引

        交易時間：
        - 股票：09:00-13:30
        - 期貨：完整交易時段（日盤 + 夜盤）
          - 夜盤後段：00:00-05:00
          - 日盤：08:45-13:45
          - 夜盤前段：15:00-23:59
        """
        minutes = []
        current_date = start_date

        if is_futures:
            # 期貨：完整交易時段（日盤 + 夜盤）
            while current_date <= end_date:
                # 1. 夜盤後段：00:00-05:00（屬於前一交易日的夜盤）
                for hour in range(0, 5):
                    for minute in range(60):
                        dt = datetime.combine(current_date, datetime.min.time().replace(hour=hour, minute=minute))
                        minutes.append(dt)

                # 05:00 記錄最後一分鐘
                dt = datetime.combine(current_date, datetime.min.time().replace(hour=5, minute=0))
                minutes.append(dt)

                # 2. 日盤：08:45-13:45
                # 08:45-08:59 (15 分钟)
                for minute in range(45, 60):
                    dt = datetime.combine(current_date, datetime.min.time().replace(hour=8, minute=minute))
                    minutes.append(dt)

                # 09:00-12:00
                for hour in range(9, 12):
                    for minute in range(60):
                        dt = datetime.combine(current_date, datetime.min.time().replace(hour=hour, minute=minute))
                        minutes.append(dt)

                # 12:00-13:45
                for hour in range(12, 14):
                    for minute in range(60):
                        if hour == 13 and minute > 45:
                            break
                        dt = datetime.combine(current_date, datetime.min.time().replace(hour=hour, minute=minute))
                        minutes.append(dt)

                # 3. 夜盤前段：15:00-23:59（屬於當日交易）
                for hour in range(15, 24):
                    for minute in range(60):
                        dt = datetime.combine(current_date, datetime.min.time().replace(hour=hour, minute=minute))
                        minutes.append(dt)

                current_date += timedelta(days=1)
        else:
            # 股票：09:00-13:30
            while current_date <= end_date:
                # 上午盤：09:00-12:00
                for hour in range(9, 12):
                    for minute in range(60):
                        dt = datetime.combine(current_date, datetime.min.time().replace(hour=hour, minute=minute))
                        minutes.append(dt)

                # 下午盤：12:00-13:30
                for hour in range(12, 14):
                    for minute in range(60):
                        if hour == 13 and minute > 30:
                            break
                        dt = datetime.combine(current_date, datetime.min.time().replace(hour=hour, minute=minute))
                        minutes.append(dt)

                current_date += timedelta(days=1)

        return pd.DatetimeIndex(minutes)

    def sync_stock(
        self,
        stock_id: str,
        start_date: date,
        end_date: date,
        trading_minutes: pd.DatetimeIndex
    ) -> Tuple[int, int]:
        """
        同步單一標的的數據（支持股票和期货）

        Args:
            stock_id: 標的代碼（股票或期货）
            start_date: 開始日期
            end_date: 結束日期
            trading_minutes: 交易分鐘索引

        Returns:
            (PostgreSQL 插入數, Qlib 是否成功)
        """
        # 1. 從 Shioaji 獲取數據
        result = self.fetch_minute_data(stock_id, start_date, end_date)

        if result is None:
            return (0, 0)

        # 🆕 解包返回值：DataFrame 和實際標的代碼
        df, actual_stock_id = result

        if df.empty:
            return (0, 0)

        # 2. 保存到 PostgreSQL（使用實際合約代碼）
        db_count = self.save_to_postgresql(actual_stock_id, df) if not self.skip_db else 0

        # 3. 保存到 Qlib（使用實際合約代碼）
        qlib_success = self.save_to_qlib(actual_stock_id, df, trading_minutes)

        return (db_count, 1 if qlib_success else 0)

    def sync_all(
        self,
        stock_ids: List[str],
        user_start_date: Optional[date],
        user_end_date: date,
        smart_mode: bool = False
    ):
        """
        同步所有標的的數據（支持股票和期货，支援智慧模式）

        Args:
            stock_ids: 標的代碼列表（股票或期货）
            user_start_date: 用戶指定的開始日期（智慧模式下可為 None）
            user_end_date: 用戶指定的結束日期
            smart_mode: 是否使用智慧增量同步
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"開始同步: {len(stock_ids)} 檔標的（股票/期货）")
        if smart_mode:
            logger.info(f"🧠 智慧模式: 自動檢測每檔標的的最後日期")
            logger.info(f"   目標日期: {user_end_date}")
        else:
            logger.info(f"日期範圍: {user_start_date} ~ {user_end_date}")
        logger.info(f"{'='*60}\n")

        # 統計變量
        total_db_count = 0
        total_qlib_count = 0
        error_count = 0
        skipped_count = 0
        full_sync_count = 0
        incremental_sync_count = 0

        # 進度條
        progress_bar = tqdm(stock_ids, desc="同步進度", unit="檔")

        for stock_id in progress_bar:
            progress_bar.set_description(f"同步 {stock_id}")

            try:
                # 判斷同步範圍
                if smart_mode:
                    sync_start, sync_end, sync_type = self.determine_sync_range(
                        stock_id, user_end_date, smart_mode=True
                    )

                    if sync_type == 'skip':
                        skipped_count += 1
                        logger.debug(f"  ⏭️  {stock_id}: 已是最新，跳過")
                        continue

                    if sync_type == 'full':
                        full_sync_count += 1
                        logger.info(f"  📦 {stock_id}: 完整同步 ({sync_start} ~ {sync_end})")
                    elif sync_type == 'incremental':
                        incremental_sync_count += 1
                        logger.info(f"  ➕ {stock_id}: 增量同步 ({sync_start} ~ {sync_end})")
                else:
                    # 非智慧模式，使用用戶指定的日期
                    sync_start = user_start_date
                    sync_end = user_end_date

                # 生成交易分鐘索引（根據標的類型）
                is_futures = self._is_futures(stock_id)
                trading_minutes = self.generate_trading_minutes(sync_start, sync_end, is_futures=is_futures)

                # 執行同步
                db_count, qlib_count = self.sync_stock(
                    stock_id, sync_start, sync_end, trading_minutes
                )

                if db_count == 0 and qlib_count == 0:
                    logger.debug(f"  ⚠️  {stock_id}: 無新數據")
                else:
                    total_db_count += db_count
                    total_qlib_count += qlib_count
                    logger.info(f"  ✅ {stock_id}: DB +{db_count}, Qlib {'✓' if qlib_count else '✗'}")

            except Exception as e:
                error_count += 1
                logger.error(f"  ❌ {stock_id}: 同步失敗 - {e}")
                continue

        # 總結
        logger.info(f"\n{'='*60}")
        logger.info("同步完成！")
        if smart_mode:
            logger.info(f"📦 完整同步: {full_sync_count} 檔")
            logger.info(f"➕ 增量同步: {incremental_sync_count} 檔")
            logger.info(f"⏭️  已最新跳過: {skipped_count} 檔")
        else:
            logger.info(f"✅ 成功: {len(stock_ids) - error_count - skipped_count} 檔")
        logger.info(f"❌ 失敗: {error_count} 檔")
        logger.info(f"📊 PostgreSQL: 插入 {total_db_count} 筆")
        logger.info(f"📊 Qlib: 更新 {total_qlib_count} 檔")
        logger.info(f"{'='*60}")

    def close(self):
        """關閉資源"""
        if self.shioaji_client and self.shioaji_client.is_available():
            self.shioaji_client.__exit__(None, None, None)

        if self.db_session:
            self.db_session.close()

        logger.info("✅ 資源已釋放")


def main():
    parser = argparse.ArgumentParser(
        description='Shioaji 到 Qlib 獨立同步工具（智慧增量同步版）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例用法:
  # 🧠 智慧增量同步（推薦）
  python sync_shioaji_to_qlib.py --smart

  # 智慧同步到指定日期
  python sync_shioaji_to_qlib.py --smart --end-date 2025-12-13

  # 傳統模式：同步今天的數據
  python sync_shioaji_to_qlib.py --today

  # 同步指定日期範圍
  python sync_shioaji_to_qlib.py --start-date 2025-12-01 --end-date 2025-12-13

  # 測試模式（僅同步 5 檔股票）
  python sync_shioaji_to_qlib.py --smart --test
        """
    )

    # 日期範圍參數
    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument('--smart', action='store_true',
                           help='🧠 智慧模式：自動檢測最後日期，僅同步缺失部分（推薦）')
    date_group.add_argument('--today', action='store_true', help='同步今天的數據')
    date_group.add_argument('--yesterday', action='store_true', help='同步昨天的數據')
    date_group.add_argument('--start-date', type=str, help='開始日期 (YYYY-MM-DD)')

    parser.add_argument('--end-date', type=str, help='結束日期 (YYYY-MM-DD，預設為今天)')

    # 股票範圍參數
    parser.add_argument('--stocks', type=str, help='股票代碼（逗號分隔），留空則同步所有')
    parser.add_argument('--test', action='store_true', help='測試模式（僅同步前 5 檔）')
    parser.add_argument('--limit', type=int, help='限制同步數量')

    # 存儲選項
    parser.add_argument('--qlib-only', action='store_true', help='僅更新 Qlib，跳過 PostgreSQL')
    parser.add_argument('--qlib-data-dir', type=str, default='/data/qlib/tw_stock_minute',
                        help='Qlib 數據目錄（預設: /data/qlib/tw_stock_minute）')

    args = parser.parse_args()

    # 解析日期範圍
    smart_mode = False
    if args.smart:
        smart_mode = True
        start_date = None  # 智慧模式不需要 start_date
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date() if args.end_date else date.today()
    elif args.today:
        start_date = end_date = date.today()
    elif args.yesterday:
        start_date = end_date = date.today() - timedelta(days=1)
    else:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date() if args.end_date else start_date

    # 初始化同步器
    syncer = ShioajiToQlibSyncer(
        qlib_data_dir=args.qlib_data_dir,
        skip_db=args.qlib_only
    )

    # 獲取股票清單
    if args.stocks:
        stock_ids = [s.strip() for s in args.stocks.split(',')]
        logger.info(f"使用指定股票清單: {len(stock_ids)} 檔")
    else:
        stock_ids = syncer.get_stock_list()

    # 測試模式
    if args.test:
        stock_ids = stock_ids[:5]
        logger.warning(f"⚠️  測試模式: 僅同步前 {len(stock_ids)} 檔")

    # 限制數量
    if args.limit:
        stock_ids = stock_ids[:args.limit]
        logger.warning(f"⚠️  限制同步: {args.limit} 檔")

    # 開始同步
    try:
        syncer.sync_all(stock_ids, start_date, end_date, smart_mode=smart_mode)
    finally:
        syncer.close()


if __name__ == '__main__':
    main()
