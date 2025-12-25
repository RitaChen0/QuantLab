#!/usr/bin/env python3
"""
RD-Agent 完整 LLM 因子挖掘

直接使用後端服務層執行因子挖掘
預計執行時間：30-60 分鐘
預計成本：$0.5 - $2 USD
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
logger.add(f"/tmp/rdagent_llm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", rotation="500 MB")

logger.info("=" * 80)
logger.info("🤖 RD-Agent 完整 LLM 因子挖掘")
logger.info("=" * 80)
logger.info(f"⏰ 開始時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
logger.info(f"💰 預計成本：$0.5 - $2 USD (GPT-4-turbo)")
logger.info(f"⏳ 預計時間：30-60 分鐘")
logger.info("")

# 檢查環境
logger.info("步驟 1：檢查環境配置")
logger.info("-" * 80)

openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    logger.error("❌ OPENAI_API_KEY 未設置")
    logger.error("請在 .env 檔案中設置 OPENAI_API_KEY")
    sys.exit(1)

logger.info(f"✅ OpenAI API Key: {openai_key[:10]}...{openai_key[-4:]}")

# 配置參數
logger.info("")
logger.info("步驟 2：配置因子挖掘參數")
logger.info("-" * 80)

request = FactorMiningRequest(
    research_goal="找出台指期貨（TX）的短期動量因子，適合5-20日週期的交易策略。重點關注價量關係、波動率調整和趨勢識別。",
    stock_pool="tx",
    max_factors=3,
    max_iterations=2,
    llm_model="gpt-4-turbo"
)

logger.info(f"📊 研究目標：{request.research_goal}")
logger.info(f"📈 標的池：{request.stock_pool}")
logger.info(f"🔢 最大因子數：{request.max_factors}")
logger.info(f"🔄 最大迭代次數：{request.max_iterations}")
logger.info(f"🤖 LLM 模型：{request.llm_model}")

# 創建任務
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
    
    # 執行因子挖掘
    logger.info("")
    logger.info("步驟 4：執行 LLM 因子挖掘")
    logger.info("-" * 80)
    logger.info("🤖 正在調用 GPT-4 生成因子...")
    logger.info("⚠️  這個過程需要 30-60 分鐘，請耐心等待...")
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
        
        # 解析結果
        logger.info("")
        logger.info("步驟 5：解析生成的因子")
        logger.info("-" * 80)
        
        factors = service.parse_rdagent_results(log_dir)
        logger.info(f"✅ 成功解析 {len(factors)} 個因子")
        
        # 計算成本
        llm_calls, llm_cost = service.calculate_llm_costs(log_dir)
        logger.info(f"💰 LLM 調用次數：{llm_calls}")
        logger.info(f"💰 估計成本：${llm_cost:.4f} USD")
        
        # 保存因子
        logger.info("")
        logger.info("步驟 6：保存因子到資料庫")
        logger.info("-" * 80)
        
        saved_factors = []
        for i, factor_data in enumerate(factors, 1):
            try:
                factor = service.save_generated_factor(
                    task_id=task.id,
                    user_id=1,
                    name=factor_data.get("name", f"Factor_{i}"),
                    formula=factor_data.get("formula", ""),
                    description=factor_data.get("description", ""),
                    category=factor_data.get("category", "llm_generated"),
                    metadata=factor_data.get("metadata", {})
                )
                saved_factors.append(factor)
                logger.info(f"✅ [{i}/{len(factors)}] {factor.name} (ID: {factor.id})")
                logger.info(f"   公式：{factor.formula}")
            except Exception as e:
                logger.error(f"❌ [{i}/{len(factors)}] 保存失敗：{e}")
        
        # 更新任務狀態
        service.update_task_status(
            task.id,
            TaskStatus.COMPLETED,
            result={
                "factors_generated": len(saved_factors),
                "execution_time_minutes": duration,
                "log_dir": log_dir,
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
        logger.info("🎉 完整因子挖掘流程成功！")
        logger.info("=" * 80)
        logger.info(f"📊 任務 ID：{task.id}")
        logger.info(f"📈 生成因子數：{len(saved_factors)}")
        logger.info(f"⏱️  總耗時：{duration:.1f} 分鐘")
        logger.info(f"💰 LLM 成本：${llm_cost:.4f} USD")
        logger.info("")
        logger.info("📋 生成的因子：")
        for factor in saved_factors:
            logger.info(f"")
            logger.info(f"   📈 {factor.name} (ID: {factor.id})")
            logger.info(f"      公式：{factor.formula}")
            logger.info(f"      分類：{factor.category}")
        logger.info("")
        logger.info("💡 下一步：")
        logger.info("   1. 在前端 http://localhost:3000 查看生成的因子")
        logger.info("   2. 將因子插入到策略中進行回測")
        logger.info("   3. 評估因子實盤表現（IC、夏普比率）")
        
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
