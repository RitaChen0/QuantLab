#!/usr/bin/env python3
"""測試法人買賣超功能"""

import sys
sys.path.insert(0, '/home/ubuntu/QuantLab/backend')

from app.db.session import SessionLocal
from app.services.institutional_investor_service import InstitutionalInvestorService
from app.schemas.institutional_investor import InvestorType
from datetime import date

def test_sync_and_query():
    """測試同步和查詢功能"""
    db = SessionLocal()

    try:
        print("=" * 80)
        print("測試法人買賣超功能")
        print("=" * 80)

        # 初始化服務
        service = InstitutionalInvestorService(db)

        # 測試 1: 同步台積電 (2330) 最近 7 天的數據
        print("\n1️⃣ 同步台積電 (2330) 最近 7 天的法人買賣超數據...")
        result = service.sync_stock_data(
            stock_id='2330',
            start_date='2024-12-01',
            end_date='2024-12-13',
            force=False
        )

        print(f"   狀態: {result['status']}")
        print(f"   期間: {result.get('period', 'N/A')}")
        print(f"   新增: {result.get('inserted', 0)} 筆")
        print(f("   更新: {result.get('updated', 0)} 筆")
        print(f"   錯誤: {result.get('errors', 0)} 筆")

        # 測試 2: 查詢數據
        print("\n2️⃣ 查詢台積電 2024-12-13 的法人買賣超摘要...")
        summary = service.get_summary('2330', date(2024, 12, 13))

        print(f"   日期: {summary.date}")
        print(f"   外資: {summary.foreign_net:,} 股")
        print(f"   投信: {summary.trust_net:,} 股")
        print(f"   自營商-自行: {summary.dealer_self_net:,} 股")
        print(f"   自營商-避險: {summary.dealer_hedging_net:,} 股")
        print(f"   三大法人合計: {summary.total_net:,} 股")

        # 測試 3: 查詢統計數據
        print("\n3️⃣ 查詢外資 12/1-12/13 統計...")
        stats = service.get_stats(
            stock_id='2330',
            investor_type=InvestorType.FOREIGN_INVESTOR,
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 13)
        )

        if stats:
            print(f"   期間: {stats.period_start} ~ {stats.period_end}")
            print(f"   總買進: {stats.total_buy:,} 股")
            print(f"   總賣出: {stats.total_sell:,} 股")
            print(f"   淨買賣超: {stats.total_net:,} 股")
            print(f"   日均買賣超: {stats.avg_daily_net:,.0f} 股")
            print(f"   買超天數: {stats.buy_days} 天")
            print(f"   賣超天數: {stats.sell_days} 天")

        # 測試 4: 查詢最新數據日期
        print("\n4️⃣ 查詢最新數據日期...")
        latest_date = service.get_latest_date('2330')
        print(f"   台積電最新數據: {latest_date}")

        latest_global = service.get_latest_date()
        print(f"   全局最新數據: {latest_global}")

        # 測試 5: 查詢時間序列數據
        print("\n5️⃣ 查詢外資買賣超時間序列...")
        df = service.get_foreign_net_series(
            stock_id='2330',
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 13)
        )

        print(f"   返回 {len(df)} 筆記錄")
        if len(df) > 0:
            print("\n   前 5 筆數據:")
            print(df.head().to_string())

        print("\n" + "=" * 80)
        print("✅ 測試完成！")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ 測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    test_sync_and_query()
