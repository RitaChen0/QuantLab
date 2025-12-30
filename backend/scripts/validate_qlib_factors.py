"""
驗證 Qlib 因子公式是否有效

測試所有公共因子的公式是否能被 Qlib 正確解析和計算
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import qlib
from qlib.data import D
from app.db.session import SessionLocal
from app.db.base import Base
from app.models.rdagent import GeneratedFactor
from app.models.user import User
# 導入所有關聯模型以避免映射錯誤
try:
    from app.models.telegram_notification import TelegramNotification
except ImportError:
    pass

# 初始化 Qlib
qlib.init(provider_uri="/data/qlib/tw_stock_v2", region="cn")

# 系統公共因子用戶 ID
SYSTEM_USER_ID = 18

def validate_factors():
    """驗證所有公共因子"""
    db = SessionLocal()

    try:
        # 獲取所有公共因子
        factors = db.query(GeneratedFactor).filter(
            GeneratedFactor.user_id == SYSTEM_USER_ID
        ).all()

        print(f"找到 {len(factors)} 個公共因子，開始驗證...\n")

        # 測試數據配置
        test_instruments = ['2330']  # 台積電
        test_start = '2024-01-01'
        test_end = '2024-01-10'

        valid_factors = []
        invalid_factors = []

        for i, factor in enumerate(factors, 1):
            print(f"[{i}/{len(factors)}] 測試因子: {factor.name}")
            print(f"  公式: {factor.formula}")

            try:
                # 嘗試載入數據
                df = D.features(
                    instruments=test_instruments,
                    fields=[factor.formula],
                    start_time=test_start,
                    end_time=test_end,
                    freq='day'
                )

                if df is not None and not df.empty:
                    print(f"  ✅ 有效 - 載入 {len(df)} 筆數據")
                    valid_factors.append(factor)
                else:
                    print(f"  ⚠️  警告 - 返回空數據")
                    invalid_factors.append((factor, "Empty dataframe"))

            except Exception as e:
                print(f"  ❌ 無效 - 錯誤: {str(e)}")
                invalid_factors.append((factor, str(e)))

            print()

        # 總結
        print("="*80)
        print(f"驗證完成！")
        print(f"  有效因子: {len(valid_factors)}")
        print(f"  無效因子: {len(invalid_factors)}")
        print("="*80)

        if invalid_factors:
            print("\n無效因子列表：")
            for factor, error in invalid_factors:
                print(f"  - ID={factor.id}, 名稱={factor.name}")
                print(f"    公式={factor.formula}")
                print(f"    錯誤={error}")
                print()

            # 詢問是否刪除無效因子
            print(f"\n建議刪除這 {len(invalid_factors)} 個無效因子")
            response = input("是否立即刪除？(y/N): ")

            if response.lower() == 'y':
                for factor, _ in invalid_factors:
                    db.delete(factor)
                db.commit()
                print(f"✅ 已刪除 {len(invalid_factors)} 個無效因子")
            else:
                print("❌ 已取消刪除操作")
        else:
            print("\n✅ 所有公共因子都有效！")

    finally:
        db.close()


if __name__ == "__main__":
    validate_factors()
