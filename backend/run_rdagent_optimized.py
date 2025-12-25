#!/usr/bin/env python3
"""
RD-Agent 優化版因子挖掘

改進點：
1. 更詳細的研究目標描述
2. 明確要求 Qlib 表達式格式
3. 增加因子數量和迭代次數
4. 提供具體範例引導 LLM
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 設置路徑
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from loguru import logger
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.base import import_models
from app.services.rdagent_service import RDAgentService
from app.models.rdagent import TaskStatus
from app.schemas.rdagent import FactorMiningRequest

# 導入所有模型（解決關係引用問題）
import_models()

# 配置日誌
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}", level="INFO")
logger.add(f"/tmp/rdagent_optimized_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", rotation="500 MB")

logger.info("=" * 80)
logger.info("🤖 RD-Agent 優化版 LLM 因子挖掘")
logger.info("=" * 80)
logger.info(f"⏰ 開始時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
logger.info(f"💡 優化重點：詳細 Prompt + 更多因子 + Qlib 格式")
logger.info("")

# 步驟 1：檢查環境
logger.info("步驟 1：檢查環境配置")
logger.info("-" * 80)

openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    logger.error("❌ OPENAI_API_KEY 未設置")
    sys.exit(1)

logger.info(f"✅ OpenAI API Key: {openai_key[:10]}...{openai_key[-4:]}")

# 步驟 2：配置優化後的參數
logger.info("")
logger.info("步驟 2：配置優化後的因子挖掘參數")
logger.info("-" * 80)

# 優化後的研究目標（更詳細、更具體）
optimized_research_goal = """
為台指期貨（TX）設計創新的短期動量因子，目標是捕捉 5-20 日的價格趨勢。

【核心要求】
1. 使用 Qlib 表達式語法（例如：Mean($close, 20), Std($close, 10), Correlation($close, $volume, 5)）
2. 結合多個維度：價量關係、波動率調整、趨勢強度
3. 創新組合：避免單純的移動平均，應組合多個因子
4. 提供至少 5 個不同的候選因子

【Qlib 可用函數】
- 滯後：Ref($close, 5) - 5天前的收盤價
- 移動平均：Mean($close, 20), EMA($close, 12)
- 統計：Std($close, 20), Max($high, 10), Min($low, 10)
- 相關性：Correlation($close, $volume, 10)
- 排名：Rank($close), Quantile($close, 0.8)
- 條件：If($close > Mean($close, 20), 1, -1)
- 運算：+, -, *, /, abs(), sign()

【因子範例】
1. 價量動量：Correlation($close, $volume, 10) * ($close / Ref($close, 5) - 1)
2. 波動調整動量：($close - Mean($close, 20)) / Std($close, 20)
3. 趨勢強度：(Mean($close, 5) - Mean($close, 20)) / Mean($close, 20)
4. 價量背離：Sign($close - Ref($close, 1)) * Sign($volume - Mean($volume, 20))
5. 相對強度：Rank($close / Ref($close, 10))

【輸出格式要求】
- 因子名稱：使用英文，簡潔描述（例如：VolAdjMomentum_10_20）
- 公式：必須是 Qlib 表達式，不要使用數學符號（LaTeX）
- 描述：簡要說明因子邏輯和適用場景
- 分類：momentum, volatility, volume, trend 之一

請生成 5 個創新且實用的因子。
"""

request = FactorMiningRequest(
    research_goal=optimized_research_goal,
    stock_pool="tx",
    max_factors=5,           # 增加到 5 個
    max_iterations=5,        # 增加迭代次數
    llm_model="gpt-4-turbo"
)

logger.info(f"📊 研究目標字數：{len(optimized_research_goal)}")
logger.info(f"📈 標的池：{request.stock_pool}")
logger.info(f"🔢 最大因子數：{request.max_factors}")
logger.info(f"🔄 最大迭代次數：{request.max_iterations}")
logger.info(f"🤖 LLM 模型：{request.llm_model}")

# 步驟 3：創建任務
logger.info("")
logger.info("步驟 3：創建 RD-Agent 任務")
logger.info("-" * 80)

db: Session = SessionLocal()

try:
    service = RDAgentService(db)
    
    # 創建任務記錄
    task = service.create_factor_mining_task(user_id=1, request=request)
    logger.info(f"✅ 任務已創建 (ID: {task.id})")
    
    # 更新狀態為運行中
    service.update_task_status(task.id, TaskStatus.RUNNING)
    logger.info(f"✅ 任務狀態：RUNNING")
    
    # 步驟 4：執行因子挖掘
    logger.info("")
    logger.info("步驟 4：執行 LLM 因子挖掘")
    logger.info("-" * 80)
    logger.info("🤖 正在調用 GPT-4 生成因子...")
    logger.info("📝 使用優化後的 Prompt（更詳細的要求和範例）")
    logger.info("⚠️  預計執行時間：10-20 分鐘（因子數和迭代次數較多）")
    logger.info("")
    
    start_time = datetime.now()
    
    try:
        # 執行 RD-Agent
        log_dir = service.execute_factor_mining(
            task_id=task.id,
            research_goal=request.research_goal,
            max_iterations=request.max_iterations,
            llm_model=request.llm_model
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60
        
        logger.info("")
        logger.info("✅ 因子挖掘執行完成！")
        logger.info(f"⏱️  執行時間：{duration:.1f} 分鐘")
        logger.info(f"📁 日誌目錄：{log_dir}")
        
        # 步驟 5：解析結果
        logger.info("")
        logger.info("步驟 5：解析生成的因子")
        logger.info("-" * 80)
        
        factors = service.parse_rdagent_results(log_dir)
        logger.info(f"✅ 成功解析 {len(factors)} 個因子")
        
        # 計算成本
        llm_calls, llm_cost = service.calculate_llm_costs(log_dir)
        logger.info(f"💰 LLM 調用次數：{llm_calls}")
        logger.info(f"💰 估計成本：${llm_cost:.4f} USD")
        
        # 步驟 6：保存因子
        logger.info("")
        logger.info("步驟 6：保存因子到資料庫")
        logger.info("-" * 80)
        
        saved_factors = []
        for i, factor_data in enumerate(factors, 1):
            try:
                # 檢查公式是否為 Qlib 格式
                formula = factor_data.get("formula", "")
                is_qlib_format = '$' in formula or 'Mean' in formula or 'Std' in formula
                
                logger.info(f"📊 [{i}/{len(factors)}] {factor_data.get('name', f'Factor_{i}')}")
                logger.info(f"   公式：{formula[:80]}...")
                logger.info(f"   格式：{'✅ Qlib 格式' if is_qlib_format else '⚠️ 可能需要轉換'}")
                
                factor = service.save_generated_factor(
                    task_id=task.id,
                    user_id=1,
                    name=factor_data.get("name", f"Factor_{i}"),
                    formula=formula,
                    description=factor_data.get("description", ""),
                    category=factor_data.get("category", "llm_generated"),
                    metadata={
                        **factor_data.get("metadata", {}),
                        "is_qlib_format": is_qlib_format,
                        "prompt_version": "optimized_v2"
                    }
                )
                saved_factors.append(factor)
                logger.info(f"   ✅ 因子已保存 (ID: {factor.id})")
                logger.info("")
            except Exception as e:
                logger.error(f"   ❌ 保存失敗：{e}")
                logger.error("")
        
        # 更新任務狀態
        service.update_task_status(
            task.id,
            TaskStatus.COMPLETED,
            result={
                "factors_generated": len(saved_factors),
                "execution_time_minutes": duration,
                "log_dir": log_dir,
                "prompt_version": "optimized_v2",
                "factors": [
                    {
                        "id": f.id,
                        "name": f.name,
                        "formula": f.formula,
                        "category": f.category
                    }
                    for f in saved_factors
                ]
            },
            llm_calls=llm_calls,
            llm_cost=llm_cost
        )
        
        # 顯示結果
        logger.info("")
        logger.info("=" * 80)
        logger.info("🎉 優化版因子挖掘流程成功！")
        logger.info("=" * 80)
        logger.info(f"📊 任務 ID：{task.id}")
        logger.info(f"📈 生成因子數：{len(saved_factors)}")
        logger.info(f"⏱️  總耗時：{duration:.1f} 分鐘")
        logger.info(f"💰 LLM 成本：${llm_cost:.4f} USD")
        logger.info("")
        logger.info("📋 生成的因子：")
        for factor in saved_factors:
            logger.info("")
            logger.info(f"   📈 {factor.name} (ID: {factor.id})")
            logger.info(f"      公式：{factor.formula[:100]}...")
            logger.info(f"      分類：{factor.category}")
        logger.info("")
        logger.info("💡 下一步：")
        logger.info("   1. 驗證每個因子的 Qlib 表達式")
        logger.info("   2. 計算因子 IC 值")
        logger.info("   3. 插入策略進行回測")
        
    except Exception as e:
        # 執行失敗
        logger.error("")
        logger.error("=" * 80)
        logger.error("❌ 因子挖掘執行失敗")
        logger.error("=" * 80)
        logger.error(f"錯誤訊息：{e}")
        
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"完整錯誤：\n{error_trace}")
        
        # 更新任務狀態為失敗
        service.update_task_status(
            task.id,
            TaskStatus.FAILED,
            error_message=str(e)
        )
        
        sys.exit(1)
        
finally:
    db.close()

logger.info("")
logger.info(f"⏰ 結束時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
