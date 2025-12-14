#!/usr/bin/env python3
"""
生成期貨連續合約

功能：
1. 從 PostgreSQL 讀取多個月份的期貨合約數據
2. 在結算日前 N 天自動切換到下月合約
3. 合併為連續時間序列
4. 保存為特殊標的（TXCONT 或 MTXCONT）

使用範例：
    # 生成 TX 連續合約（2024-2025 年）
    python generate_continuous_contract.py --symbol TX --start-date 2024-01-01 --end-date 2025-12-31

    # 生成 MTX 連續合約（最近 3 個月）
    python generate_continuous_contract.py --symbol MTX --start-date 2024-10-01 --end-date 2024-12-31

    # 自定義切換時間（結算日前 5 天）
    python generate_continuous_contract.py --symbol TX --start-date 2024-01-01 --end-date 2025-12-31 --switch-days 5
"""

import sys
import os
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple
import argparse
from calendar import monthrange

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# QuantLab 模組
from app.core.config import settings
from app.db.base import import_models
from app.services.shioaji_client import get_third_wednesday

# 導入所有模型
import_models()

# 日誌配置
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)


class ContinuousContractGenerator:
    """期貨連續合約生成器（簡單拼接法）"""

    def __init__(self, db_url: Optional[str] = None):
        """
        初始化生成器

        Args:
            db_url: 資料庫連接字串（None 則使用環境變數）
        """
        self.db_url = db_url or str(settings.DATABASE_URL)
        self.engine = create_engine(self.db_url)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def _get_contract_months(
        self,
        start_date: date,
        end_date: date
    ) -> List[Tuple[int, int]]:
        """
        獲取需要的合約月份列表

        Args:
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            [(year, month), ...] 格式的合約月份列表
        """
        months = []
        current = start_date.replace(day=1)

        # 從開始月份往前推一個月（確保數據完整）
        if current.month == 1:
            current = current.replace(year=current.year - 1, month=12)
        else:
            current = current.replace(month=current.month - 1)

        # 生成月份列表，直到結束日期後一個月
        end_month = end_date.replace(day=1)
        if end_month.month == 12:
            end_month = end_month.replace(year=end_month.year + 1, month=1)
        else:
            end_month = end_month.replace(month=end_month.month + 1)

        while current <= end_month:
            months.append((current.year, current.month))
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        return months

    def _get_switch_date(
        self,
        year: int,
        month: int,
        switch_days_before: int
    ) -> date:
        """
        計算合約切換日期（結算日前 N 天）

        Args:
            year: 年份
            month: 月份
            switch_days_before: 結算日前幾天切換

        Returns:
            切換日期
        """
        settlement_date = get_third_wednesday(year, month)
        switch_date = settlement_date - timedelta(days=switch_days_before)
        return switch_date

    def _fetch_contract_data(
        self,
        symbol: str,
        year: int,
        month: int,
        start_date: date,
        end_date: date
    ) -> pd.DataFrame:
        """
        從資料庫獲取指定合約月份的數據

        Args:
            symbol: 期貨代碼（TX 或 MTX）
            year: 合約年份
            month: 合約月份
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            分鐘線數據 DataFrame
        """
        # 構造合約代碼，例如 TX202512
        contract_code = f"{symbol}{year:04d}{month:02d}"

        logger.info(f"  讀取合約 {contract_code}：{start_date} ~ {end_date}")

        query = """
        SELECT datetime, open, high, low, close, volume
        FROM stock_minute_prices
        WHERE stock_id = :stock_id
          AND datetime >= :start_dt
          AND datetime < :end_dt
        ORDER BY datetime ASC
        """

        with self.engine.connect() as conn:
            df = pd.read_sql(
                text(query),
                conn,
                params={
                    'stock_id': contract_code,
                    'start_dt': datetime.combine(start_date, datetime.min.time()),
                    'end_dt': datetime.combine(end_date + timedelta(days=1), datetime.min.time())
                }
            )

        if df.empty:
            logger.warning(f"    ⚠️ 合約 {contract_code} 無數據")
        else:
            logger.info(f"    ✅ 讀取 {len(df)} 筆記錄")

        return df

    def generate(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        switch_days_before: int = 3
    ) -> pd.DataFrame:
        """
        生成連續合約數據（簡單拼接法）

        Args:
            symbol: 期貨代碼（TX 或 MTX）
            start_date: 開始日期
            end_date: 結束日期
            switch_days_before: 結算日前幾天切換（默認 3 天）

        Returns:
            連續合約數據 DataFrame
        """
        logger.info(f"=" * 80)
        logger.info(f"生成 {symbol} 連續合約")
        logger.info(f"日期範圍：{start_date} ~ {end_date}")
        logger.info(f"切換規則：結算日前 {switch_days_before} 天")
        logger.info(f"=" * 80)

        # 1. 獲取需要的合約月份
        contract_months = self._get_contract_months(start_date, end_date)
        logger.info(f"\n需要的合約月份：{len(contract_months)} 個")
        for year, month in contract_months:
            settlement = get_third_wednesday(year, month)
            switch = self._get_switch_date(year, month, switch_days_before)
            logger.info(f"  {year}-{month:02d}: 結算日 {settlement}, 切換日 {switch}")

        # 2. 逐月讀取並拼接數據
        all_data = []
        current_date = start_date

        for i, (year, month) in enumerate(contract_months):
            # 計算當前合約的有效期間
            switch_date = self._get_switch_date(year, month, switch_days_before)

            # 確定讀取範圍
            if i == 0:
                # 第一個合約：從 start_date 開始
                fetch_start = start_date
            else:
                # 後續合約：從上個合約的切換日開始
                prev_year, prev_month = contract_months[i - 1]
                fetch_start = self._get_switch_date(prev_year, prev_month, switch_days_before)

            # 結束日期：當前合約的切換日（或 end_date）
            if i < len(contract_months) - 1:
                fetch_end = switch_date - timedelta(days=1)
            else:
                fetch_end = end_date

            # 跳過無效範圍
            if fetch_start > fetch_end:
                continue

            if fetch_start > end_date:
                break

            # 讀取數據
            logger.info(f"\n📊 合約期間 {i+1}/{len(contract_months)}：{year}-{month:02d}")
            df = self._fetch_contract_data(symbol, year, month, fetch_start, fetch_end)

            if not df.empty:
                all_data.append(df)

        # 3. 合併數據
        if not all_data:
            logger.error("❌ 無任何數據，無法生成連續合約")
            return pd.DataFrame()

        logger.info(f"\n合併 {len(all_data)} 段數據...")
        continuous_df = pd.concat(all_data, ignore_index=True)

        # 確保時間順序
        continuous_df = continuous_df.sort_values('datetime').reset_index(drop=True)

        # 移除重複時間點（可能在切換點有重疊）
        continuous_df = continuous_df.drop_duplicates(subset=['datetime'], keep='first')

        logger.info(f"✅ 連續合約生成完成：共 {len(continuous_df)} 筆記錄")
        logger.info(f"   時間範圍：{continuous_df['datetime'].min()} ~ {continuous_df['datetime'].max()}")

        return continuous_df

    def save_to_db(
        self,
        symbol: str,
        data: pd.DataFrame
    ):
        """
        將連續合約數據保存到資料庫

        Args:
            symbol: 期貨代碼（TX 或 MTX）
            data: 連續合約數據
        """
        # 確定連續合約代碼
        continuous_id = f"{symbol}CONT"

        logger.info(f"\n💾 保存連續合約到資料庫：{continuous_id}")

        # 先刪除舊數據
        with self.engine.connect() as conn:
            delete_query = text("DELETE FROM stock_minute_prices WHERE stock_id = :stock_id")
            result = conn.execute(delete_query, {'stock_id': continuous_id})
            conn.commit()
            logger.info(f"   清除舊數據：{result.rowcount} 筆")

        # 準備插入數據
        data_copy = data.copy()
        data_copy['stock_id'] = continuous_id
        data_copy['timeframe'] = '1min'  # 🆕 添加 timeframe 列

        # 批次插入
        batch_size = 10000
        total_inserted = 0

        with self.engine.connect() as conn:
            for i in range(0, len(data_copy), batch_size):
                batch = data_copy.iloc[i:i+batch_size]

                insert_query = text("""
                    INSERT INTO stock_minute_prices (stock_id, datetime, timeframe, open, high, low, close, volume)
                    VALUES (:stock_id, :datetime, :timeframe, :open, :high, :low, :close, :volume)
                    ON CONFLICT (stock_id, datetime, timeframe) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume
                """)

                conn.execute(insert_query, batch.to_dict('records'))
                conn.commit()

                total_inserted += len(batch)
                logger.info(f"   已插入 {total_inserted}/{len(data_copy)} 筆")

        logger.info(f"✅ 連續合約保存完成：{continuous_id}")


def main():
    parser = argparse.ArgumentParser(description='生成期貨連續合約')
    parser.add_argument('--symbol', required=True, choices=['TX', 'MTX'], help='期貨代碼')
    parser.add_argument('--start-date', required=True, help='開始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, help='結束日期 (YYYY-MM-DD)')
    parser.add_argument('--switch-days', type=int, default=3, help='結算日前幾天切換（默認 3 天）')

    args = parser.parse_args()

    # 解析日期
    start = datetime.strptime(args.start_date, '%Y-%m-%d').date()
    end = datetime.strptime(args.end_date, '%Y-%m-%d').date()

    # 創建生成器
    generator = ContinuousContractGenerator()

    # 生成連續合約
    continuous_data = generator.generate(
        symbol=args.symbol,
        start_date=start,
        end_date=end,
        switch_days_before=args.switch_days
    )

    if continuous_data.empty:
        logger.error("❌ 生成失敗")
        sys.exit(1)

    # 保存到資料庫
    generator.save_to_db(args.symbol, continuous_data)

    logger.info("\n" + "=" * 80)
    logger.info("🎉 連續合約生成完成")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
