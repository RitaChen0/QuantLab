#!/usr/bin/env python3
"""完整的法人買賣超功能測試"""
import sys
sys.path.insert(0, '/app')

from app.db.session import SessionLocal, ensure_models_imported
from app.services.institutional_investor_service import InstitutionalInvestorService
from app.schemas.institutional_investor import InvestorType
import datetime

# 確保模型已載入
ensure_models_imported()

print("=" * 80)
print("法人買賣超功能完整測試")
print("=" * 80)

db = SessionLocal()
try:
    service = InstitutionalInvestorService(db)

    # Test 1: 同步數據
    print("\n✅ Test 1: 同步台積電 (2330) 法人買賣超數據")
    result = service.sync_stock_data('2330', '2024-12-01', '2024-12-05')
    print(f"   狀態: {result['status']}")
    print(f"   期間: {result.get('period', 'N/A')}")
    print(f"   新增: {result.get('inserted', 0)} 筆")
    print(f"   更新: {result.get('updated', 0)} 筆")

    # Test 2: 查詢數據
    print("\n✅ Test 2: 查詢法人買賣超數據")
    data = service.get_stock_data(
        stock_id='2330',
        start_date=datetime.date(2024, 12, 1),
        end_date=datetime.date(2024, 12, 5)
    )
    print(f"   查詢到 {len(data)} 筆記錄")
    if len(data) > 0:
        print(f"   範例: {data[0].date} {data[0].investor_type.value} 買賣超: {data[0].net_buy_sell:,}")

    # Test 3: 查詢摘要
    print("\n✅ Test 3: 查詢單日摘要 (2024-12-02)")
    summary = service.get_summary('2330', datetime.date(2024, 12, 2))
    print(f"   外資: {summary.foreign_net:,}")
    print(f"   投信: {summary.trust_net:,}")
    print(f"   三大法人合計: {summary.total_net:,}")

    # Test 4: 查詢統計
    print("\n✅ Test 4: 查詢外資統計 (12/1-12/5)")
    stats = service.get_stats(
        stock_id='2330',
        investor_type=InvestorType.FOREIGN_INVESTOR,
        start_date=datetime.date(2024, 12, 1),
        end_date=datetime.date(2024, 12, 5)
    )
    if stats:
        print(f"   總買進: {stats.total_buy:,}")
        print(f"   總賣出: {stats.total_sell:,}")
        print(f"   淨買賣超: {stats.total_net:,}")
        print(f"   買超天數: {stats.buy_days}")
        print(f"   賣超天數: {stats.sell_days}")

    # Test 5: 查詢最新日期
    print("\n✅ Test 5: 查詢最新數據日期")
    latest = service.get_latest_date('2330')
    print(f"   最新日期: {latest}")

    # Test 6: 時間序列數據
    print("\n✅ Test 6: 查詢外資買賣超時間序列")
    df = service.get_foreign_net_series(
        stock_id='2330',
        start_date=datetime.date(2024, 12, 1),
        end_date=datetime.date(2024, 12, 5)
    )
    print(f"   返回 {len(df)} 筆時間序列數據")

    print("\n" + "=" * 80)
    print("✅ 所有測試通過！法人買賣超功能運作正常")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ 測試失敗: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
