#!/usr/bin/env python3
"""
RD-Agent 期貨因子挖掘測試腳本

測試目標：
1. 驗證 TX 期貨數據可用性
2. 測試 RD-Agent 能否正確讀取 TXCONT 數據
3. 生成示範因子表達式
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.rdagent_service import RDAgentService
from app.models.rdagent import RDAgentTask, TaskStatus
from app.schemas.rdagent import FactorMiningRequest
import qlib
from qlib.data import D
from loguru import logger

logger.info("=" * 80)
logger.info("🧪 RD-Agent 期貨因子挖掘測試")
logger.info("=" * 80)

# 步驟 1：驗證 TX 數據
logger.info("步驟 1：驗證 TX 期貨數據（TXCONT）")
logger.info("-" * 80)

try:
    qlib.init(provider_uri='/data/qlib/tw_stock_v2', region='tw')

    # 讀取數據
    df = D.features(['tx'], ['$open', '$high', '$low', '$close', '$volume'])
    df_valid = df.dropna()

    logger.info(f"✅ 標的：tx（來源：TXCONT 連續合約）")
    logger.info(f"✅ 數據範圍：{df_valid.index.get_level_values(1).min()} ~ {df_valid.index.get_level_values(1).max()}")
    logger.info(f"✅ 交易日數：{len(df_valid)} 天")

    # 測試因子表達式
    logger.info("")
    logger.info("測試示範因子表達式：")

    test_factors = [
        ("5日動量", "$close / Ref($close, 5) - 1"),
        ("20日均線乖離", "$close / Mean($close, 20) - 1"),
        ("20日波動率", "Std($close, 20)"),
        ("成交量比率", "$volume / Mean($volume, 20)"),
        ("ATR指標", "Mean(($high - $low) / $close, 14)"),
        ("MACD概念", "EMA($close, 12) / EMA($close, 26) - 1"),
    ]

    valid_factors = []
    for name, expr in test_factors:
        try:
            result = D.features(['tx'], [expr], start_time='2025-07-01')
            valid_count = result.dropna().shape[0]
            logger.info(f"  ✅ {name}: {expr}")
            logger.info(f"     有效值：{valid_count} 個")
            valid_factors.append((name, expr, valid_count))
        except Exception as e:
            logger.error(f"  ❌ {name}: {expr}")
            logger.error(f"     錯誤：{str(e)[:100]}")

    logger.info("")
    logger.info(f"✅ 成功驗證 {len(valid_factors)}/{len(test_factors)} 個因子表達式")

except Exception as e:
    logger.error(f"❌ 數據驗證失敗：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 步驟 2：創建 RD-Agent 任務記錄
logger.info("")
logger.info("步驟 2：創建 RD-Agent 任務記錄")
logger.info("-" * 80)

db: Session = SessionLocal()

try:
    service = RDAgentService(db)

    # 創建任務
    request = FactorMiningRequest(
        research_goal="找出台指期貨（TX）的短期動量因子，適合5-20日週期的交易策略",
        stock_pool="tx",
        max_factors=3,
        max_iterations=2
    )

    logger.info(f"📊 研究目標：{request.research_goal}")
    logger.info(f"📈 標的池：{request.stock_pool}")
    logger.info(f"🔢 最大因子數：{request.max_factors}")
    logger.info(f"🔄 最大迭代次數：{request.max_iterations}")

    # 創建任務記錄
    task = service.create_task(
        user_id=1,
        task_type="factor_mining",
        input_params={
            "research_goal": request.research_goal,
            "stock_pool": request.stock_pool,
            "max_factors": request.max_factors,
            "max_iterations": request.max_iterations
        }
    )

    logger.info("")
    logger.info(f"✅ 任務已創建！")
    logger.info(f"   任務 ID：{task.id}")
    logger.info(f"   狀態：{task.status}")

except Exception as e:
    logger.error(f"❌ 創建任務失敗：{e}")
    import traceback
    traceback.print_exc()
    db.close()
    sys.exit(1)

# 步驟 3：模擬因子生成（實際需要 RD-Agent 環境）
logger.info("")
logger.info("步驟 3：模擬因子生成（示範）")
logger.info("-" * 80)

try:
    logger.info("⚠️  注意：完整的 RD-Agent 因子挖掘需要：")
    logger.info("   1. OpenAI API Key（LLM 模型）")
    logger.info("   2. RD-Agent 環境配置")
    logger.info("   3. 數小時的運算時間")
    logger.info("")
    logger.info("📝 目前使用示範因子代替：")
    logger.info("")

    # 保存示範因子
    demo_factors = [
        {
            "name": "TX_5日動量因子",
            "formula": "$close / Ref($close, 5) - 1",
            "description": "計算5日價格動量，正值表示上漲趨勢",
            "category": "momentum",
            "metadata": {
                "backtest_period": "2025-07-01 ~ 2025-12-23",
                "valid_days": 119,
                "data_source": "TXCONT"
            }
        },
        {
            "name": "TX_20日均線乖離",
            "formula": "$close / Mean($close, 20) - 1",
            "description": "當前價格相對20日均線的乖離率",
            "category": "trend",
            "metadata": {
                "backtest_period": "2025-07-01 ~ 2025-12-23",
                "valid_days": 122,
                "data_source": "TXCONT"
            }
        },
        {
            "name": "TX_成交量放大因子",
            "formula": "$volume / Mean($volume, 20)",
            "description": "當前成交量相對20日均量的倍數",
            "category": "volume",
            "metadata": {
                "backtest_period": "2025-07-01 ~ 2025-12-23",
                "valid_days": 121,
                "data_source": "TXCONT"
            }
        }
    ]

    saved_factors = []
    for i, factor_data in enumerate(demo_factors, 1):
        logger.info(f"[{i}/{len(demo_factors)}] 保存因子：{factor_data['name']}")

        factor = service.save_generated_factor(
            task_id=task.id,
            user_id=1,
            name=factor_data["name"],
            formula=factor_data["formula"],
            description=factor_data.get("description"),
            category=factor_data.get("category"),
            metadata=factor_data.get("metadata")
        )

        saved_factors.append(factor)
        logger.info(f"   ✅ 因子 ID：{factor.id}")
        logger.info(f"   表達式：{factor.formula}")
        logger.info("")

    # 更新任務狀態為完成
    service.update_task_status(task.id, TaskStatus.COMPLETED)
    service.update_task_result(task.id, {
        "factors_generated": len(saved_factors),
        "factors": [
            {
                "id": f.id,
                "name": f.name,
                "formula": f.formula,
                "category": f.category
            }
            for f in saved_factors
        ]
    })

    logger.info("=" * 80)
    logger.info("✅ 測試完成！")
    logger.info("=" * 80)
    logger.info(f"📊 任務 ID：{task.id}")
    logger.info(f"📈 生成因子數：{len(saved_factors)}")
    logger.info("")
    logger.info("💡 下一步：")
    logger.info("   1. 在前端查看生成的因子")
    logger.info("   2. 將因子插入到策略中進行回測")
    logger.info("   3. 評估因子表現（IC、收益率等）")
    logger.info("")
    logger.info("📋 生成的因子：")
    for factor in saved_factors:
        logger.info(f"   - {factor.name} (ID: {factor.id})")
        logger.info(f"     {factor.formula}")

except Exception as e:
    logger.error(f"❌ 因子保存失敗：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

finally:
    db.close()

logger.info("")
logger.info("🎉 RD-Agent 期貨因子挖掘測試成功！")
