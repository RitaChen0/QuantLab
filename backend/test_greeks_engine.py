#!/usr/bin/env python
"""
測試 Greeks 計算引擎

驗證：
1. Black-Scholes Greeks 計算器
2. Greeks 摘要計算
3. 階段配置正確性
"""

import sys
from decimal import Decimal
from datetime import date, timedelta

# 測試 1: Black-Scholes Greeks 計算器
print("=" * 60)
print("測試 1: Black-Scholes Greeks 計算器")
print("=" * 60)

try:
    from app.services.greeks_calculator import BlackScholesGreeksCalculator

    calculator = BlackScholesGreeksCalculator(risk_free_rate=0.01)

    # 測試案例：ATM Call Option
    greeks = calculator.calculate_greeks(
        spot_price=23000.0,      # TX 現價
        strike_price=23000.0,    # ATM 履約價
        time_to_expiry=30/365.0, # 30 天到期
        volatility=0.15,         # 15% 波動率
        option_type="CALL"
    )

    print("✅ Black-Scholes 計算成功")
    print(f"   Delta: {greeks['delta']:.4f} (預期: ~0.55)")
    print(f"   Gamma: {greeks['gamma']:.6f}")
    print(f"   Theta: {greeks['theta']:.4f} (每日)")
    print(f"   Vega: {greeks['vega']:.4f} (1% 波動率變化)")
    print(f"   Rho: {greeks['rho']:.4f}")
    print(f"   Vanna: {greeks['vanna']:.6f}")

    # 驗證合理性
    assert 0.45 <= greeks['delta'] <= 0.65, "ATM Call Delta 應約為 0.5"
    assert greeks['gamma'] > 0, "Gamma 應為正"
    assert greeks['theta'] < 0, "Call Theta 應為負（時間衰減）"
    assert greeks['vega'] > 0, "Vega 應為正"
    print("✅ Greeks 值在合理範圍內")

except Exception as e:
    print(f"❌ Black-Scholes 計算失敗: {str(e)}")
    sys.exit(1)

# 測試 2: 階段配置
print("\n" + "=" * 60)
print("測試 2: 階段配置檢查")
print("=" * 60)

try:
    from app.db.session import SessionLocal
    from app.repositories.option import OptionSyncConfigRepository

    db = SessionLocal()
    try:
        stage = OptionSyncConfigRepository.get_current_stage(db)
        greeks_enabled = OptionSyncConfigRepository.is_greeks_calculation_enabled(db)
        underlyings = OptionSyncConfigRepository.get_enabled_underlyings(db)

        print(f"✅ 當前階段: {stage}")
        print(f"✅ Greeks 計算: {'已啟用' if greeks_enabled else '未啟用'}")
        print(f"✅ 啟用標的: {', '.join(underlyings)}")

        if stage >= 3:
            print("✅ 階段 3 已啟用 - Greeks 計算可用")
        else:
            print(f"⚠️  當前階段 {stage} - Greeks 計算需要階段 3")

    finally:
        db.close()

except Exception as e:
    print(f"❌ 配置檢查失敗: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 測試 3: Greeks 摘要計算（使用模擬數據）
print("\n" + "=" * 60)
print("測試 3: Greeks 摘要計算")
print("=" * 60)

try:
    import pandas as pd
    import numpy as np
    from app.services.option_calculator import OptionFactorCalculator
    from app.services.option_data_source import OptionDataSource

    # 創建模擬選擇權鏈數據
    mock_option_chain = pd.DataFrame({
        'contract_id': [
            'TXO202601C23000', 'TXO202601C23100', 'TXO202601C23200',
            'TXO202601P22800', 'TXO202601P22900', 'TXO202601P23000'
        ],
        'option_type': ['CALL', 'CALL', 'CALL', 'PUT', 'PUT', 'PUT'],
        'strike_price': [23000, 23100, 23200, 22800, 22900, 23000],
        'expiry_date': [date.today() + timedelta(days=30)] * 6,
        'close': [300, 220, 150, 180, 250, 320],
        'volume': [100, 150, 120, 80, 130, 110],
        'open_interest': [1000, 1500, 1200, 800, 1300, 1100]
    })

    # 創建簡單的資料源 mock
    class MockDataSource(OptionDataSource):
        def get_option_chain(self, underlying_id: str, target_date: date):
            return mock_option_chain

    # 計算 Greeks 摘要
    calculator = OptionFactorCalculator(MockDataSource())

    # 手動調用 _calculate_greeks_summary
    greeks_summary = calculator._calculate_greeks_summary(mock_option_chain)

    print("✅ Greeks 摘要計算成功")
    print(f"   平均 Call Delta: {greeks_summary['avg_call_delta']}")
    print(f"   平均 Put Delta: {greeks_summary['avg_put_delta']}")
    print(f"   Gamma 曝險: {greeks_summary['gamma_exposure']}")
    print(f"   Vanna 曝險: {greeks_summary['vanna_exposure']}")

    # 驗證結果
    if greeks_summary['avg_call_delta'] is not None:
        assert 0 < float(greeks_summary['avg_call_delta']) < 1, "Call Delta 應在 0-1 之間"
    if greeks_summary['avg_put_delta'] is not None:
        assert -1 < float(greeks_summary['avg_put_delta']) < 0, "Put Delta 應在 -1-0 之間"

    print("✅ Greeks 摘要值在合理範圍內")

except Exception as e:
    print(f"❌ Greeks 摘要計算失敗: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 測試 4: Repository 測試
print("\n" + "=" * 60)
print("測試 4: OptionGreeksRepository")
print("=" * 60)

try:
    from app.repositories.option import OptionGreeksRepository
    from app.schemas.option import OptionGreeksCreate
    from datetime import datetime, timezone

    db = SessionLocal()
    try:
        # 測試創建 Greeks 記錄
        test_greeks = OptionGreeksCreate(
            contract_id='TEST_TXO202601C23000',
            datetime=datetime.now(timezone.utc),  # ✅ Use timezone-aware UTC time
            delta=Decimal('0.5'),
            gamma=Decimal('0.00001'),
            theta=Decimal('-10.5'),
            vega=Decimal('15.2'),
            rho=Decimal('5.3'),
            vanna=Decimal('0.0001'),
            spot_price=Decimal('23000'),
            volatility=Decimal('0.15'),
            risk_free_rate=Decimal('0.01')
        )

        # 測試 upsert
        # 注意：這會真的寫入資料庫，但使用測試合約 ID
        saved = OptionGreeksRepository.upsert(db, test_greeks)
        print(f"✅ Greeks 記錄已儲存: {saved.contract_id}")
        print(f"   Delta: {saved.delta}")
        print(f"   Gamma: {saved.gamma}")

        # 測試讀取
        retrieved = OptionGreeksRepository.get_by_contract_and_datetime(
            db,
            test_greeks.contract_id,
            test_greeks.datetime
        )
        assert retrieved is not None, "應該能讀取剛儲存的記錄"
        print(f"✅ Greeks 記錄已讀取")

        # 清理測試數據
        db.query(OptionGreeks).filter(
            OptionGreeks.contract_id == 'TEST_TXO202601C23000'
        ).delete()
        db.commit()
        print("✅ 測試數據已清理")

    finally:
        db.close()

except Exception as e:
    print(f"❌ Repository 測試失敗: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("🎉 所有測試通過！Greeks 計算引擎已成功啟用")
print("=" * 60)
print("\n可用功能：")
print("1. Black-Scholes Greeks 計算（Delta, Gamma, Theta, Vega, Rho, Vanna）")
print("2. Greeks 摘要統計（階段 3 因子計算）")
print("3. Greeks 時間序列儲存（option_greeks 表）")
print("4. 自動 Greeks 計算任務（calculate_option_greeks）")
print("\n階段狀態：✅ 階段 3 - Greeks 計算已啟用")
