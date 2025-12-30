"""
創建公共因子腳本

為所有用戶創建一組常用的技術指標因子，方便快速開始模型訓練。
這些因子使用 admin 用戶（user_id = 18）創建，所有用戶都能使用。
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from datetime import datetime, timezone
import json

# 導入所有模型以確保關係映射正確
from app.db.base import Base
from app.models.rdagent import RDAgentTask, TaskType, TaskStatus, GeneratedFactor
from app.models.user import User
# 導入所有關聯模型以避免映射錯誤
try:
    from app.models.telegram_notification import TelegramNotification
except ImportError:
    pass  # 如果模型不存在就忽略


# 系統用戶 ID（admin）
SYSTEM_USER_ID = 18

# 公共因子定義（使用 Qlib 表達式格式）
PUBLIC_FACTORS = [
    # ===== 動量因子 =====
    {
        "name": "動量_5日",
        "description": "5日價格動量，衡量短期價格變化趨勢",
        "formula": "($close - Ref($close, 5)) / Ref($close, 5)",
        "category": "momentum",
    },
    {
        "name": "動量_10日",
        "description": "10日價格動量，衡量中短期價格變化趨勢",
        "formula": "($close - Ref($close, 10)) / Ref($close, 10)",
        "category": "momentum",
    },
    {
        "name": "動量_20日",
        "description": "20日價格動量，衡量中期價格變化趨勢",
        "formula": "($close - Ref($close, 20)) / Ref($close, 20)",
        "category": "momentum",
    },
    {
        "name": "動量_60日",
        "description": "60日價格動量，衡量長期價格變化趨勢",
        "formula": "($close - Ref($close, 60)) / Ref($close, 60)",
        "category": "momentum",
    },

    # ===== 均線乖離率 =====
    {
        "name": "均線乖離_MA5",
        "description": "5日均線乖離率，價格相對短期均線的偏離程度",
        "formula": "($close - Mean($close, 5)) / Mean($close, 5)",
        "category": "trend",
    },
    {
        "name": "均線乖離_MA10",
        "description": "10日均線乖離率，價格相對中短期均線的偏離程度",
        "formula": "($close - Mean($close, 10)) / Mean($close, 10)",
        "category": "trend",
    },
    {
        "name": "均線乖離_MA20",
        "description": "20日均線乖離率，價格相對中期均線的偏離程度",
        "formula": "($close - Mean($close, 20)) / Mean($close, 20)",
        "category": "trend",
    },
    {
        "name": "均線乖離_MA60",
        "description": "60日均線乖離率，價格相對長期均線的偏離程度",
        "formula": "($close - Mean($close, 60)) / Mean($close, 60)",
        "category": "trend",
    },

    # ===== 波動率指標 =====
    {
        "name": "波動率_20日",
        "description": "20日價格波動率（變異係數），衡量價格波動程度",
        "formula": "Std($close, 20) / Mean($close, 20)",
        "category": "volatility",
    },
    {
        "name": "真實波幅_ATR14",
        "description": "14日真實波幅（Average True Range），衡量價格波動範圍",
        "formula": "Mean(Max(Max($high - $low, Abs($high - Ref($close, 1))), Abs($low - Ref($close, 1))), 14)",
        "category": "volatility",
    },
    {
        "name": "價格振幅",
        "description": "當日價格振幅，衡量日內波動幅度",
        "formula": "($high - $low) / $close",
        "category": "volatility",
    },

    # ===== 成交量指標 =====
    {
        "name": "成交量變化_20日",
        "description": "成交量相對20日均量的變化率",
        "formula": "($volume / Mean($volume, 20)) - 1",
        "category": "volume",
    },
    {
        "name": "價量背離",
        "description": "價格變化與成交量變化的差異，捕捉異常價量關係",
        "formula": "($close / Ref($close, 1) - 1) - ($volume / Ref($volume, 1) - 1)",
        "category": "divergence",
    },
    {
        "name": "成交量加權動量_10日",
        "description": "成交量加權的價格動量，結合量能的動量指標",
        "formula": "Sum($close * $volume, 10) / Sum($volume, 10) / Ref($close, 10) - 1",
        "category": "volume",
    },

    # ===== 技術指標 =====
    {
        "name": "RSI_14日",
        "description": "14日相對強弱指標，衡量超買超賣狀態",
        "formula": "RSI($close, 14)",
        "category": "momentum",
    },
    {
        "name": "MACD",
        "description": "MACD指標（12日EMA - 26日EMA），衡量趨勢強度",
        "formula": "EMA($close, 12) - EMA($close, 26)",
        "category": "trend",
    },
    {
        "name": "布林通道位置",
        "description": "價格在布林通道中的相對位置（0-1之間）",
        "formula": "($close - (Mean($close, 20) - 2 * Std($close, 20))) / (4 * Std($close, 20))",
        "category": "volatility",
    },

    # ===== 價格形態 =====
    {
        "name": "收盤價相對高低",
        "description": "收盤價在當日高低價中的相對位置",
        "formula": "($close - $low) / ($high - $low + 1e-6)",
        "category": "pattern",
    },
    {
        "name": "上影線比例",
        "description": "上影線相對實體的比例，衡量上方賣壓",
        "formula": "($high - Max($open, $close)) / (Abs($close - $open) + 1e-6)",
        "category": "pattern",
    },
    {
        "name": "下影線比例",
        "description": "下影線相對實體的比例，衡量下方支撐",
        "formula": "(Min($open, $close) - $low) / (Abs($close - $open) + 1e-6)",
        "category": "pattern",
    },
]


def create_public_factors():
    """創建公共因子"""
    db: Session = SessionLocal()

    try:
        # 1. 檢查系統用戶是否存在
        admin_user = db.query(User).filter(User.id == SYSTEM_USER_ID).first()
        if not admin_user:
            print(f"❌ 系統用戶 (ID={SYSTEM_USER_ID}) 不存在，請檢查資料庫")
            return

        print(f"✅ 找到系統用戶: {admin_user.username} (ID={SYSTEM_USER_ID})")

        # 2. 創建系統任務記錄
        print("\n📝 創建系統因子生成任務...")
        task = RDAgentTask(
            user_id=SYSTEM_USER_ID,
            task_type=TaskType.FACTOR_MINING,
            status=TaskStatus.COMPLETED,
            input_params=json.dumps({
                "system_task": True,
                "description": "系統預設公共因子",
                "num_iterations": 1
            }),
            result=json.dumps({
                "num_factors": len(PUBLIC_FACTORS),
                "factor_categories": list(set(f["category"] for f in PUBLIC_FACTORS))
            }),
            llm_calls=0,
            llm_cost=0.0,
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc)
        )
        db.add(task)
        db.flush()

        print(f"✅ 創建任務成功，Task ID: {task.id}")

        # 3. 創建公共因子
        print(f"\n🎯 開始創建 {len(PUBLIC_FACTORS)} 個公共因子...\n")

        created_count = 0
        for factor_data in PUBLIC_FACTORS:
            # 檢查因子是否已存在（基於 formula 和 user_id）
            existing = db.query(GeneratedFactor).filter(
                GeneratedFactor.formula == factor_data["formula"],
                GeneratedFactor.user_id == SYSTEM_USER_ID
            ).first()

            if existing:
                print(f"⏭️  因子已存在，跳過: {factor_data['name']}")
                continue

            # 創建新因子
            factor = GeneratedFactor(
                task_id=task.id,
                user_id=SYSTEM_USER_ID,
                name=factor_data["name"],
                description=factor_data["description"],
                formula=factor_data["formula"],
                category=factor_data["category"],
                # 預設指標值（尚未評估）
                ic=None,
                icir=None,
                sharpe_ratio=None,
                annual_return=None,
                created_at=datetime.now(timezone.utc)
            )
            db.add(factor)
            created_count += 1

            print(f"✅ [{created_count:2d}] {factor_data['name']:20s} | {factor_data['category']:12s} | {factor_data['formula'][:60]}")

        # 4. 提交事務
        db.commit()

        print(f"\n{'='*80}")
        print(f"🎉 公共因子創建完成！")
        print(f"{'='*80}")
        print(f"📊 統計資訊：")
        print(f"   - 任務 ID: {task.id}")
        print(f"   - 新增因子數量: {created_count}")
        print(f"   - 跳過已存在: {len(PUBLIC_FACTORS) - created_count}")
        print(f"   - 系統用戶: {admin_user.username} (ID={SYSTEM_USER_ID})")
        print(f"\n💡 所有用戶現在都可以在「模型訓練」頁面看到這些因子！")

    except Exception as e:
        db.rollback()
        print(f"\n❌ 創建失敗: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    print("="*80)
    print("🚀 QuantLab 公共因子創建腳本")
    print("="*80)
    print(f"📅 執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"👤 系統用戶 ID: {SYSTEM_USER_ID}")
    print(f"📈 因子數量: {len(PUBLIC_FACTORS)}")
    print(f"🏷️  因子分類: {', '.join(set(f['category'] for f in PUBLIC_FACTORS))}")
    print("="*80)
    print()

    create_public_factors()
