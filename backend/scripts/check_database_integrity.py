#!/usr/bin/env python3
"""
資料庫完整性檢查和自動修復工具

目的：確保資料庫數據的完整性和一致性
功能：
1. 檢查日線數據完整性（stock_prices）
2. 檢查分鐘線數據完整性（stock_minute_prices）
3. 檢查 Qlib 數據一致性
4. 自動修復缺失數據
5. 生成完整性報告

使用方式：
    # 完整檢查（推薦每日執行）
    python scripts/check_database_integrity.py --check-all

    # 自動修復所有缺失
    python scripts/check_database_integrity.py --fix-all

    # 生成報告
    python scripts/check_database_integrity.py --report

    # 檢查特定類型
    python scripts/check_database_integrity.py --check-daily
    python scripts/check_database_integrity.py --check-minute
    python scripts/check_database_integrity.py --check-qlib
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple
from sqlalchemy import text
import subprocess

from app.db.session import SessionLocal
from app.utils.timezone_helpers import today_taiwan


class DatabaseIntegrityChecker:
    """資料庫完整性檢查器"""

    def __init__(self):
        self.db = SessionLocal()
        self.issues = []
        self.stats = {
            'daily_missing': 0,
            'minute_missing': 0,
            'qlib_missing': 0,
            'fixed': 0,
            'errors': 0
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()

    def log_issue(self, level: str, category: str, message: str):
        """記錄問題"""
        self.issues.append({
            'level': level,
            'category': category,
            'message': message,
            'timestamp': datetime.now()
        })

    def check_daily_completeness(self, days: int = 30) -> Dict:
        """
        檢查日線數據完整性

        Returns:
            {
                'missing_dates': [日期列表],
                'stocks_count': 股票總數,
                'date_range': (最早, 最晚),
                'coverage': 覆蓋率
            }
        """
        print("\n" + "="*60)
        print("📊 檢查日線數據完整性（stock_prices）")
        print("="*60)

        end_date = today_taiwan()
        start_date = end_date - timedelta(days=days)

        # 檢查缺失日期（排除週末）
        query = text("""
            WITH date_series AS (
                SELECT generate_series(
                    :start_date,
                    :end_date,
                    '1 day'::interval
                )::date AS date
            ),
            trading_days AS (
                SELECT DISTINCT date FROM stock_prices
                WHERE date BETWEEN :start_date AND :end_date
            )
            SELECT ds.date
            FROM date_series ds
            LEFT JOIN trading_days td ON ds.date = td.date
            WHERE td.date IS NULL
              AND EXTRACT(DOW FROM ds.date) NOT IN (0, 6)
            ORDER BY ds.date
        """)

        result = self.db.execute(query, {'start_date': start_date, 'end_date': end_date})
        missing_dates = [row[0] for row in result.fetchall()]

        # 統計
        total_stocks = self.db.execute(text("SELECT COUNT(DISTINCT stock_id) FROM stock_prices")).scalar()

        # 日期範圍
        range_query = self.db.execute(text("""
            SELECT MIN(date), MAX(date) FROM stock_prices
        """)).fetchone()

        result = {
            'missing_dates': missing_dates,
            'stocks_count': total_stocks,
            'date_range': range_query,
            'coverage': ((days - len(missing_dates)) / days * 100) if days > 0 else 100
        }

        # 報告
        print(f"\n📅 檢查範圍: {start_date} ~ {end_date} ({days} 天)")
        print(f"📊 股票總數: {total_stocks:,} 檔")
        print(f"📈 數據範圍: {range_query[0]} ~ {range_query[1]}")
        print(f"✅ 覆蓋率: {result['coverage']:.1f}%")

        if missing_dates:
            print(f"\n⚠️  發現 {len(missing_dates)} 個缺失日期:")
            for missing_date in missing_dates[:10]:
                print(f"  🔴 {missing_date}")
                self.log_issue('WARNING', 'daily', f"缺失日線數據: {missing_date}")
            if len(missing_dates) > 10:
                print(f"  ... 還有 {len(missing_dates) - 10} 個")
            self.stats['daily_missing'] = len(missing_dates)
        else:
            print("\n✅ 日線數據完整")

        return result

    def check_minute_completeness(self, days: int = 7) -> Dict:
        """
        檢查分鐘線數據完整性

        Returns:
            {
                'date_range': (最早, 最晚),
                'stocks_count': 股票數,
                'total_bars': 總分鐘線數,
                'daily_stats': {日期: 股票數}
            }
        """
        print("\n" + "="*60)
        print("⏱️  檢查分鐘線數據完整性（stock_minute_prices）")
        print("="*60)

        # 數據範圍
        range_query = self.db.execute(text("""
            SELECT
                MIN(datetime::date) as min_date,
                MAX(datetime::date) as max_date,
                COUNT(DISTINCT stock_id) as stocks_count,
                COUNT(*) as total_bars
            FROM stock_minute_prices
        """)).fetchone()

        if not range_query[0]:
            print("\n❌ 沒有分鐘線數據")
            self.log_issue('ERROR', 'minute', '完全沒有分鐘線數據')
            self.stats['errors'] += 1
            return {'date_range': (None, None), 'stocks_count': 0, 'total_bars': 0, 'daily_stats': {}}

        # 每日統計
        end_date = today_taiwan()
        start_date = end_date - timedelta(days=days)

        daily_query = self.db.execute(text("""
            SELECT
                datetime::date as date,
                COUNT(DISTINCT stock_id) as stocks_count,
                COUNT(*) as bars_count
            FROM stock_minute_prices
            WHERE datetime::date BETWEEN :start_date AND :end_date
            GROUP BY datetime::date
            ORDER BY date DESC
        """), {'start_date': start_date, 'end_date': end_date})

        daily_stats = {row[0]: {'stocks': row[1], 'bars': row[2]} for row in daily_query.fetchall()}

        # 報告
        print(f"\n📅 數據範圍: {range_query[0]} ~ {range_query[1]}")
        print(f"📊 股票數: {range_query[2]:,} 檔")
        print(f"📈 總分鐘線: {range_query[3]:,} 筆")

        print(f"\n📅 最近 {days} 天統計:")
        for i in range(days):
            check_date = end_date - timedelta(days=i)
            if check_date.weekday() >= 5:  # 週末
                continue
            stats = daily_stats.get(check_date)
            if stats:
                status = "✅" if stats['stocks'] > 2000 else "⚠️" if stats['stocks'] > 0 else "❌"
                print(f"  {status} {check_date}: {stats['stocks']:,} 檔, {stats['bars']:,} 筆")
            else:
                print(f"  ❌ {check_date}: 無數據")
                self.log_issue('ERROR', 'minute', f"缺失分鐘線數據: {check_date}")
                self.stats['minute_missing'] += 1

        return {
            'date_range': (range_query[0], range_query[1]),
            'stocks_count': range_query[2],
            'total_bars': range_query[3],
            'daily_stats': daily_stats
        }

    def check_qlib_consistency(self) -> Dict:
        """
        檢查 Qlib 數據一致性

        檢查項目：
        1. Qlib 日線目錄是否存在
        2. Qlib 分鐘線目錄是否存在
        3. 與 PostgreSQL 的一致性
        """
        print("\n" + "="*60)
        print("📊 檢查 Qlib 數據一致性")
        print("="*60)

        qlib_daily = Path("/data/qlib/tw_stock_v2")
        qlib_minute = Path("/data/qlib/tw_stock_minute")

        result = {
            'daily_exists': qlib_daily.exists(),
            'minute_exists': qlib_minute.exists(),
            'daily_stocks': 0,
            'minute_stocks': 0
        }

        # 檢查日線
        if qlib_daily.exists():
            features_dir = qlib_daily / "features"
            if features_dir.exists():
                result['daily_stocks'] = len(list(features_dir.iterdir()))
                print(f"\n✅ Qlib 日線目錄: {qlib_daily}")
                print(f"   📊 股票數: {result['daily_stocks']:,} 檔")
            else:
                print(f"\n⚠️  Qlib 日線目錄存在但無 features 子目錄")
                self.log_issue('WARNING', 'qlib', 'Qlib 日線 features 目錄缺失')
        else:
            print(f"\n❌ Qlib 日線目錄不存在: {qlib_daily}")
            self.log_issue('ERROR', 'qlib', 'Qlib 日線目錄不存在')
            self.stats['errors'] += 1

        # 檢查分鐘線
        if qlib_minute.exists():
            features_dir = qlib_minute / "features"
            if features_dir.exists():
                result['minute_stocks'] = len(list(features_dir.iterdir()))
                print(f"\n✅ Qlib 分鐘線目錄: {qlib_minute}")
                print(f"   📊 股票數: {result['minute_stocks']:,} 檔")
            else:
                print(f"\n⚠️  Qlib 分鐘線目錄存在但無 features 子目錄")
                self.log_issue('WARNING', 'qlib', 'Qlib 分鐘線 features 目錄缺失')
        else:
            print(f"\n❌ Qlib 分鐘線目錄不存在: {qlib_minute}")
            self.log_issue('ERROR', 'qlib', 'Qlib 分鐘線目錄不存在')
            self.stats['errors'] += 1

        return result

    def auto_fix_daily(self) -> int:
        """
        自動修復日線缺失

        使用分鐘線聚合補齊
        """
        print("\n" + "="*60)
        print("🔧 自動修復日線缺失")
        print("="*60)

        try:
            result = subprocess.run(
                ["python", "/app/scripts/backfill_daily_from_minute.py", "--smart"],
                cwd="/app",
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print("✅ 日線修復完成")
                # 解析輸出統計修復數量
                for line in result.stdout.split('\n'):
                    if '新增' in line and '筆' in line:
                        print(f"   {line.strip()}")
                self.stats['fixed'] += 1
                return 1
            else:
                print(f"❌ 日線修復失敗: {result.stderr}")
                self.log_issue('ERROR', 'fix', f"日線修復失敗: {result.stderr}")
                self.stats['errors'] += 1
                return 0
        except Exception as e:
            print(f"❌ 執行修復腳本失敗: {e}")
            self.log_issue('ERROR', 'fix', f"執行修復腳本失敗: {e}")
            self.stats['errors'] += 1
            return 0

    def auto_fix_minute(self) -> int:
        """
        自動修復分鐘線缺失

        使用 Shioaji API 同步
        """
        print("\n" + "="*60)
        print("🔧 自動修復分鐘線缺失")
        print("="*60)

        try:
            result = subprocess.run(
                ["python", "/app/scripts/sync_shioaji_to_qlib.py", "--smart"],
                cwd="/app",
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print("✅ 分鐘線修復完成")
                # 解析輸出統計修復數量
                for line in result.stdout.split('\n'):
                    if 'PostgreSQL: 插入' in line:
                        print(f"   {line.strip()}")
                self.stats['fixed'] += 1
                return 1
            else:
                print(f"❌ 分鐘線修復失敗: {result.stderr}")
                self.log_issue('ERROR', 'fix', f"分鐘線修復失敗: {result.stderr}")
                self.stats['errors'] += 1
                return 0
        except Exception as e:
            print(f"❌ 執行同步腳本失敗: {e}")
            self.log_issue('ERROR', 'fix', f"執行同步腳本失敗: {e}")
            self.stats['errors'] += 1
            return 0

    def generate_report(self, output_file: str = None):
        """生成完整性報告"""
        print("\n" + "="*60)
        print("📋 資料庫完整性報告")
        print("="*60)

        report = []
        report.append(f"\n生成時間: {datetime.now()}")
        report.append(f"\n統計摘要:")
        report.append(f"  - 日線缺失: {self.stats['daily_missing']} 個日期")
        report.append(f"  - 分鐘線缺失: {self.stats['minute_missing']} 個日期")
        report.append(f"  - Qlib 問題: {self.stats['qlib_missing']} 個")
        report.append(f"  - 已修復: {self.stats['fixed']} 項")
        report.append(f"  - 錯誤: {self.stats['errors']} 個")

        if self.issues:
            report.append(f"\n問題詳情 ({len(self.issues)} 個):")
            for issue in self.issues:
                report.append(f"  [{issue['level']}] {issue['category']}: {issue['message']}")

        report_text = '\n'.join(report)
        print(report_text)

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"\n✅ 報告已保存: {output_file}")

        return report_text


def main():
    parser = argparse.ArgumentParser(description="資料庫完整性檢查和自動修復")
    parser.add_argument("--check-all", action="store_true", help="完整檢查（推薦）")
    parser.add_argument("--check-daily", action="store_true", help="只檢查日線")
    parser.add_argument("--check-minute", action="store_true", help="只檢查分鐘線")
    parser.add_argument("--check-qlib", action="store_true", help="只檢查 Qlib")
    parser.add_argument("--fix-all", action="store_true", help="自動修復所有缺失")
    parser.add_argument("--fix-daily", action="store_true", help="只修復日線")
    parser.add_argument("--fix-minute", action="store_true", help="只修復分鐘線")
    parser.add_argument("--report", action="store_true", help="生成報告")
    parser.add_argument("--days", type=int, default=30, help="檢查最近 N 天（默認 30）")
    parser.add_argument("--output", type=str, help="報告輸出文件")

    args = parser.parse_args()

    print("="*60)
    print("🏥 資料庫完整性檢查系統")
    print("="*60)

    with DatabaseIntegrityChecker() as checker:
        # 檢查
        if args.check_all or args.check_daily or (not any([args.check_minute, args.check_qlib, args.fix_all, args.fix_daily, args.fix_minute])):
            checker.check_daily_completeness(days=args.days)

        if args.check_all or args.check_minute:
            checker.check_minute_completeness(days=min(args.days, 7))

        if args.check_all or args.check_qlib:
            checker.check_qlib_consistency()

        # 修復
        if args.fix_all or args.fix_daily:
            if checker.stats['daily_missing'] > 0:
                checker.auto_fix_daily()

        if args.fix_all or args.fix_minute:
            if checker.stats['minute_missing'] > 0:
                checker.auto_fix_minute()

        # 報告
        if args.report or args.output:
            checker.generate_report(output_file=args.output)

        # 最終摘要
        print("\n" + "="*60)
        print("✅ 檢查完成")
        print("="*60)
        print(f"📊 統計: 日線缺失 {checker.stats['daily_missing']}, "
              f"分鐘線缺失 {checker.stats['minute_missing']}, "
              f"已修復 {checker.stats['fixed']}, "
              f"錯誤 {checker.stats['errors']}")

        # 返回狀態碼
        if checker.stats['errors'] > 0:
            return 1
        return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
