#!/usr/bin/env python3
"""
RD-Agent 完整 LLM 因子挖掘腳本

這個腳本會實際調用 GPT-4 進行因子挖掘
預計執行時間：30-60 分鐘
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 設置路徑
sys.path.insert(0, str(Path(__file__).parent / 'backend'))
os.chdir(Path(__file__).parent)

from loguru import logger
import qlib
from qlib.data import D

# 配置日誌
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}", level="INFO")
logger.add("/tmp/rdagent_mining_{time}.log", rotation="500 MB", level="DEBUG")

logger.info("=" * 80)
logger.info("🤖 RD-Agent 完整 LLM 因子挖掘")
logger.info("=" * 80)
logger.info(f"⏰ 開始時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
logger.info(f"💰 預計成本：$0.5 - $2 USD (GPT-4 API)")
logger.info(f"⏳ 預計時間：30-60 分鐘")
logger.info("")

# 步驟 1：驗證環境
logger.info("步驟 1：驗證 RD-Agent 環境")
logger.info("-" * 80)

try:
    # 檢查 OpenAI API Key
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        logger.error("❌ 未設置 OPENAI_API_KEY")
        sys.exit(1)
    logger.info(f"✅ OpenAI API Key: {openai_key[:10]}...{openai_key[-4:]}")
    
    # 檢查 RD-Agent
    import rdagent
    logger.info(f"✅ RD-Agent 已安裝")
    
    # 檢查 Qlib 數據
    qlib.init(provider_uri='/data/qlib/tw_stock_v2', region='tw')
    df = D.features(['tx'], ['$close'])
    logger.info(f"✅ Qlib 數據可用：{len(df)} 天")
    
except Exception as e:
    logger.error(f"❌ 環境驗證失敗：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 步驟 2：配置 RD-Agent
logger.info("")
logger.info("步驟 2：配置 RD-Agent 因子挖掘參數")
logger.info("-" * 80)

from rdagent.scenarios.qlib.experiment.factor_experiment import QlibFactorExperiment
from rdagent.core.conf import RD_AGENT_SETTINGS

# 配置參數
config = {
    "research_goal": "找出台指期貨（TX）的短期動量因子，適合5-20日週期的交易策略。重點關注價量關係、波動率調整、趨勢識別等特徵。",
    "stock_pool": "tx",
    "max_factors": 3,  # 先生成 3 個因子（快速測試）
    "max_iterations": 2,  # 2 輪迭代
    "data_path": "/data/qlib/tw_stock_v2",
    "start_date": "2025-07-01",
    "end_date": "2025-12-23",
}

logger.info(f"📊 研究目標：{config['research_goal']}")
logger.info(f"📈 標的池：{config['stock_pool']}")
logger.info(f"🔢 最大因子數：{config['max_factors']}")
logger.info(f"🔄 最大迭代次數：{config['max_iterations']}")
logger.info(f"📅 回測區間：{config['start_date']} ~ {config['end_date']}")

# 步驟 3：執行 LLM 因子挖掘
logger.info("")
logger.info("步驟 3：啟動 RD-Agent LLM 因子挖掘")
logger.info("-" * 80)
logger.info("🤖 正在調用 GPT-4 生成因子...")
logger.info("⚠️  這個過程需要 30-60 分鐘，請耐心等待...")
logger.info("")

try:
    # 創建工作目錄
    workspace = Path("/tmp/rdagent_workspace")
    workspace.mkdir(exist_ok=True)
    
    logger.info(f"📁 工作目錄：{workspace}")
    
    # 初始化 RD-Agent 實驗
    experiment = QlibFactorExperiment(
        target_task=config["research_goal"],
        data_folder=config["data_path"],
        workspace=str(workspace),
    )
    
    logger.info("✅ RD-Agent 實驗已初始化")
    logger.info("")
    
    # 執行因子挖掘（這裡會調用 LLM）
    logger.info("🚀 開始執行因子挖掘...")
    start_time = datetime.now()
    
    # 運行實驗
    results = experiment.run(
        max_iterations=config["max_iterations"],
        max_factors=config["max_factors"],
    )
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds() / 60
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("✅ 因子挖掘完成！")
    logger.info("=" * 80)
    logger.info(f"⏱️  執行時間：{duration:.1f} 分鐘")
    logger.info(f"📊 生成因子數：{len(results.get('factors', []))}")
    logger.info("")
    
    # 步驟 4：顯示結果
    logger.info("步驟 4：挖掘結果")
    logger.info("-" * 80)
    
    factors = results.get('factors', [])
    
    if not factors:
        logger.warning("⚠️  未生成任何因子")
    else:
        for i, factor in enumerate(factors, 1):
            logger.info(f"")
            logger.info(f"📈 因子 {i}: {factor.get('name', 'Unnamed')}")
            logger.info(f"   公式: {factor.get('formula', 'N/A')}")
            logger.info(f"   描述: {factor.get('description', 'N/A')}")
            
            # 回測指標
            metrics = factor.get('metrics', {})
            if metrics:
                logger.info(f"   📊 回測指標:")
                logger.info(f"      IC: {metrics.get('ic', 'N/A'):.4f}")
                logger.info(f"      Sharpe: {metrics.get('sharpe', 'N/A'):.2f}")
                logger.info(f"      Return: {metrics.get('return', 'N/A'):.2%}")
    
    # 步驟 5：保存到資料庫
    logger.info("")
    logger.info("步驟 5：保存因子到資料庫")
    logger.info("-" * 80)
    
    from sqlalchemy.orm import Session
    from app.db.session import SessionLocal
    from app.services.rdagent_service import RDAgentService
    from app.models.rdagent import TaskStatus
    
    db: Session = SessionLocal()
    
    try:
        service = RDAgentService(db)
        
        # 創建任務記錄
        task = service.create_task(
            user_id=1,
            task_type="factor_mining",
            input_params=config
        )
        
        logger.info(f"✅ 任務記錄已創建 (ID: {task.id})")
        
        # 保存因子
        saved_factors = []
        for factor in factors:
            saved_factor = service.save_generated_factor(
                task_id=task.id,
                user_id=1,
                name=factor.get('name', 'Unnamed Factor'),
                formula=factor.get('formula', ''),
                description=factor.get('description', ''),
                category='llm_generated',
                metadata={
                    'metrics': factor.get('metrics', {}),
                    'generated_by': 'rdagent_gpt4',
                    'generation_time': datetime.now().isoformat(),
                }
            )
            saved_factors.append(saved_factor)
            logger.info(f"   ✅ 因子已保存: {saved_factor.name} (ID: {saved_factor.id})")
        
        # 更新任務狀態
        service.update_task_status(task.id, TaskStatus.COMPLETED)
        service.update_task_result(task.id, {
            "factors_generated": len(saved_factors),
            "execution_time_minutes": duration,
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
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("🎉 完整因子挖掘流程成功！")
        logger.info("=" * 80)
        logger.info(f"📊 任務 ID: {task.id}")
        logger.info(f"📈 生成因子數: {len(saved_factors)}")
        logger.info(f"⏱️  總耗時: {duration:.1f} 分鐘")
        logger.info("")
        logger.info("💡 下一步：")
        logger.info("   1. 在前端查看生成的因子")
        logger.info("   2. 將因子插入到策略中進行回測")
        logger.info("   3. 評估因子實盤表現")
        
    except Exception as e:
        logger.error(f"❌ 保存失敗：{e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
    
except Exception as e:
    logger.error("")
    logger.error("=" * 80)
    logger.error("❌ 因子挖掘失敗")
    logger.error("=" * 80)
    logger.error(f"錯誤訊息：{e}")
    logger.error("")
    import traceback
    traceback.print_exc()
    sys.exit(1)

logger.info("")
logger.info(f"⏰ 結束時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
