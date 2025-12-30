"""RD-Agent Service Layer"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from loguru import logger
import os
import pickle
import re
from pathlib import Path

from app.models.rdagent import RDAgentTask, GeneratedFactor, GeneratedModel, FactorEvaluation, TaskStatus, TaskType
from app.schemas.rdagent import FactorMiningRequest, ModelGenerationRequest, StrategyOptimizationRequest
from app.utils.model_code_generator import ModelCodeGenerator
from app.repositories.rdagent_task import RDAgentTaskRepository
from app.repositories.generated_factor import GeneratedFactorRepository
from app.repositories.generated_model import GeneratedModelRepository


class RDAgentService:
    """RD-Agent 服務類"""

    def __init__(self, db: Session):
        self.db = db

    def create_factor_mining_task(
        self, user_id: int, request: FactorMiningRequest
    ) -> RDAgentTask:
        """建立因子挖掘任務"""
        task = RDAgentTask(
            user_id=user_id,
            task_type=TaskType.FACTOR_MINING,
            status=TaskStatus.PENDING,
            input_params={
                "research_goal": request.research_goal,
                "stock_pool": request.stock_pool,
                "max_factors": request.max_factors,
                "llm_model": request.llm_model,
                "max_iterations": request.max_iterations,
            }
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        logger.info(f"Created factor mining task {task.id} for user {user_id}")
        return task

    def create_strategy_optimization_task(
        self, user_id: int, request: StrategyOptimizationRequest
    ) -> RDAgentTask:
        """建立策略優化任務"""
        task = RDAgentTask(
            user_id=user_id,
            task_type=TaskType.STRATEGY_OPTIMIZATION,
            status=TaskStatus.PENDING,
            input_params={
                "strategy_id": request.strategy_id,
                "optimization_goal": request.optimization_goal,
                "llm_model": request.llm_model,
                "max_iterations": request.max_iterations,
            }
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        logger.info(f"Created strategy optimization task {task.id} for user {user_id}")
        return task

    def get_task(self, task_id: int, user_id: int) -> Optional[RDAgentTask]:
        """獲取任務"""
        return RDAgentTaskRepository.get_by_id_and_user(self.db, task_id, user_id)

    def get_user_tasks(
        self, user_id: int, task_type: Optional[TaskType] = None, limit: int = 50
    ) -> List[RDAgentTask]:
        """獲取使用者任務列表"""
        return RDAgentTaskRepository.get_by_user(
            self.db,
            user_id,
            task_type=task_type,
            skip=0,
            limit=limit
        )

    def delete_task(self, task_id: int, user_id: int) -> bool:
        """刪除任務

        Args:
            task_id: 任務 ID
            user_id: 使用者 ID（用於權限檢查）

        Returns:
            bool: 是否成功刪除

        Raises:
            ValueError: 任務不存在或無權限刪除
        """
        task = RDAgentTaskRepository.get_by_id_and_user(self.db, task_id, user_id)

        if not task:
            raise ValueError(f"Task {task_id} not found or access denied")

        # 刪除相關的生成因子
        GeneratedFactorRepository.delete_by_task(self.db, task_id)

        # 刪除任務
        RDAgentTaskRepository.delete(self.db, task)

        logger.info(f"Deleted task {task_id} for user {user_id}")
        return True

    def get_generated_factors(
        self, user_id: int, limit: int = 100
    ) -> List[GeneratedFactor]:
        """獲取生成的因子列表（包含用戶自己的因子 + 公共因子）"""
        return GeneratedFactorRepository.get_by_user_including_public(
            self.db,
            user_id,
            skip=0,
            limit=limit
        )

    def update_factor(
        self, factor_id: int, user_id: int, name: Optional[str] = None, description: Optional[str] = None
    ) -> Optional[GeneratedFactor]:
        """更新生成的因子

        Args:
            factor_id: 因子 ID
            user_id: 使用者 ID（用於權限檢查）
            name: 新的因子名稱
            description: 新的因子描述

        Returns:
            GeneratedFactor: 更新後的因子，如果不存在或無權限則返回 None
        """
        factor = GeneratedFactorRepository.get_by_id_and_user(self.db, factor_id, user_id)

        if not factor:
            return None

        # 更新欄位
        if name is not None:
            factor.name = name
        if description is not None:
            factor.description = description

        factor = GeneratedFactorRepository.update(self.db, factor)
        logger.info(f"Updated factor {factor_id}: name={name}, description={description}")
        return factor

    def save_generated_factor(
        self,
        task_id: int,
        user_id: int,
        name: str,
        formula: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> GeneratedFactor:
        """保存生成的因子"""
        factor = GeneratedFactor(
            task_id=task_id,
            user_id=user_id,
            name=name,
            formula=formula,
            description=description,
            category=category,
            metadata=metadata
        )
        self.db.add(factor)
        self.db.commit()
        self.db.refresh(factor)

        logger.info(f"Saved generated factor {factor.id}: {name}")
        return factor

    def update_task_status(
        self,
        task_id: int,
        status: TaskStatus,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        llm_calls: Optional[int] = None,
        llm_cost: Optional[float] = None
    ):
        """更新任務狀態"""
        task = RDAgentTaskRepository.get_by_id(self.db, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.status = status

        if status == TaskStatus.RUNNING and not task.started_at:
            task.started_at = datetime.now(timezone.utc)

        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            task.completed_at = datetime.now(timezone.utc)

        if result:
            task.result = result

        if error_message:
            task.error_message = error_message

        if llm_calls is not None:
            task.llm_calls = llm_calls

        if llm_cost is not None:
            task.llm_cost = llm_cost

        RDAgentTaskRepository.update(self.db, task)
        logger.info(f"Updated task {task_id} status to {status}")

    def execute_factor_mining(
        self,
        task_id: int,
        research_goal: str,
        max_iterations: int = 3,
        llm_model: str = "gpt-4-turbo",
    ) -> str:
        """執行 RD-Agent 因子挖掘

        Args:
            task_id: 任務 ID
            research_goal: 研究目標
            max_iterations: 最大迭代次數
            llm_model: LLM 模型名稱

        Returns:
            log_dir: 日誌目錄路徑

        Raises:
            Exception: 執行失敗時拋出異常
        """
        logger.info(f"Starting factor mining for task {task_id}")
        logger.info(f"Research goal: {research_goal}")
        logger.info(f"Max iterations: {max_iterations}")
        logger.info(f"LLM model: {llm_model}")

        # 設定環境變數
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
        os.environ["QLIB_DATA_PATH"] = os.getenv("QLIB_DATA_PATH", "/data/qlib/tw_stock_v2")

        if not os.environ["OPENAI_API_KEY"]:
            raise ValueError("OPENAI_API_KEY not configured")

        try:
            # 導入 RD-Agent
            from rdagent.app.qlib_rd_loop.factor import main

            # 執行因子挖掘
            logger.info(f"Executing RD-Agent with {max_iterations} iterations...")
            main(step_n=max_iterations)

            # 查找最新的日誌目錄
            log_base_dir = Path("/app/log")
            if not log_base_dir.exists():
                raise FileNotFoundError("Log directory /app/log not found")

            # 獲取最新的時間戳目錄
            log_dirs = sorted(log_base_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not log_dirs:
                raise FileNotFoundError("No log directories found")

            log_dir = str(log_dirs[0])
            logger.info(f"RD-Agent execution completed. Log directory: {log_dir}")

            return log_dir

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Factor mining execution failed: {str(e)}")
            logger.error(f"Full traceback:\n{error_trace}")
            raise

    def parse_rdagent_results(self, log_dir: str) -> List[Dict[str, Any]]:
        """解析 RD-Agent 執行結果

        從 .pkl 日誌檔案中提取生成的因子定義

        Args:
            log_dir: RD-Agent 日誌目錄路徑

        Returns:
            factors: 因子列表，每個因子包含 name, formula, description, variables, category
        """
        logger.info(f"Parsing RD-Agent results from {log_dir}")

        log_path = Path(log_dir)
        if not log_path.exists():
            raise FileNotFoundError(f"Log directory not found: {log_dir}")

        factors = []

        # 遍歷所有迭代目錄 (Loop_0, Loop_1, ...)
        for loop_dir in sorted(log_path.glob("Loop_*")):
            loop_num = int(loop_dir.name.split("_")[1])
            logger.info(f"Processing {loop_dir.name}...")

            # 查找 experiment generation 結果 pickle 檔案
            exp_gen_pattern = loop_dir / "direct_exp_gen" / "r" / "experiment generation" / "**" / "*.pkl"
            exp_pkl_files = sorted(log_path.glob(str(exp_gen_pattern.relative_to(log_path))))

            if not exp_pkl_files:
                logger.warning(f"No experiment pickle files found in {loop_dir}")
                continue

            # 讀取所有實驗 pickle 檔案
            for exp_file in exp_pkl_files:
                try:
                    with open(exp_file, "rb") as f:
                        experiment_data = pickle.load(f)

                    logger.info(f"Loaded experiment from {exp_file.name}")

                    # experiment_data 應該是包含 FactorTask 物件的列表
                    if isinstance(experiment_data, list):
                        for task in experiment_data:
                            factor = self._extract_factor_from_task(task, loop_num)
                            if factor:
                                factors.append(factor)
                                logger.info(f"Extracted factor: {factor['name']}")

                except Exception as e:
                    logger.error(f"Failed to load {exp_file}: {e}")

        logger.info(f"Parsed {len(factors)} factors from RD-Agent results")
        return factors

    def _extract_factor_from_task(self, task: Any, loop_num: int) -> Optional[Dict[str, Any]]:
        """從 FactorTask 物件中提取因子定義

        Args:
            task: FactorTask 物件
            loop_num: 迭代編號

        Returns:
            factor: 因子字典，包含 name, formula, description, variables
        """
        try:
            # 提取因子屬性
            factor_name = getattr(task, 'factor_name', None) or str(task)
            factor_description = getattr(task, 'factor_description', '')
            factor_formulation = getattr(task, 'factor_formulation', '')
            variables = getattr(task, 'variables', {})

            # 清理因子名稱（移除特殊字元）
            if factor_name and '<' in factor_name:
                # 處理 <FactorTask[20DaySMA]> 格式
                match = re.search(r'\[(.+?)\]', factor_name)
                if match:
                    factor_name = match.group(1)

            if not factor_name:
                logger.warning(f"No factor name found in task: {task}")
                return None

            factor = {
                "name": factor_name,
                "formula": factor_formulation or "N/A",
                "description": factor_description or f"Factor generated in Loop {loop_num}",
                "variables": variables if isinstance(variables, dict) else {},
                "category": "momentum",  # 預設分類
                "metadata": {
                    "loop_num": loop_num,
                    "task_type": type(task).__name__
                }
            }

            return factor

        except Exception as e:
            logger.error(f"Failed to extract factor from task: {e}")
            return None

    def _extract_factor_from_experiment(
        self,
        hypothesis_data: Any,
        experiment_data: Any,
        loop_num: int
    ) -> Optional[Dict[str, Any]]:
        """從實驗數據中提取因子定義

        Args:
            hypothesis_data: 假設數據 (從 hypothesis.pkl)
            experiment_data: 實驗數據 (從 experiment.pkl)
            loop_num: 迭代編號

        Returns:
            factor: 因子字典，包含 name, formula, description, variables, category, metadata
        """
        try:
            # 提取因子名稱（從 hypothesis 或 experiment）
            factor_name = None
            if hasattr(hypothesis_data, "hypothesis") and hypothesis_data.hypothesis:
                # 從假設文本中提取因子名稱
                match = re.search(r"Factor[:\s]+([A-Za-z0-9_]+)", str(hypothesis_data.hypothesis))
                if match:
                    factor_name = match.group(1)

            if not factor_name:
                factor_name = f"Factor_Loop{loop_num}"

            # 提取因子公式（從實驗代碼中）
            formula = None
            if hasattr(experiment_data, "code") and experiment_data.code:
                # 查找 Qlib 表達式定義
                code_str = str(experiment_data.code)
                # 匹配常見的因子定義模式
                patterns = [
                    r"'([^']+)':\s*'([^']+)'",  # 'factor_name': 'expression'
                    r"\"([^\"]+)\":\s*\"([^\"]+)\"",  # "factor_name": "expression"
                    r"(\w+)\s*=\s*\"([^\"]+)\"",  # factor_name = "expression"
                ]

                for pattern in patterns:
                    matches = re.findall(pattern, code_str)
                    if matches:
                        # 取第一個匹配的表達式
                        formula = matches[0][1] if len(matches[0]) > 1 else matches[0][0]
                        break

            if not formula:
                formula = f"Ref($close, 0)"  # 默認公式

            # 提取描述
            description = None
            if hasattr(hypothesis_data, "hypothesis"):
                description = str(hypothesis_data.hypothesis)[:500]  # 限制長度

            # 提取變數（從公式中）
            variables = self._extract_variables_from_formula(formula)

            # 分類（基於變數或公式關鍵字）
            category = self._categorize_factor(formula, variables)

            # 構建因子字典
            factor = {
                "name": factor_name,
                "formula": formula,
                "description": description,
                "variables": variables,
                "category": category,
                "metadata": {
                    "loop": loop_num,
                    "hypothesis_type": type(hypothesis_data).__name__,
                    "experiment_type": type(experiment_data).__name__,
                }
            }

            return factor

        except Exception as e:
            logger.error(f"Failed to extract factor from experiment: {e}")
            return None

    def _extract_variables_from_formula(self, formula: str) -> List[str]:
        """從 Qlib 表達式中提取變數

        Args:
            formula: Qlib 表達式公式

        Returns:
            variables: 變數列表（如 ['close', 'volume', 'open']）
        """
        variables = set()

        # 匹配 $variable 格式
        dollar_vars = re.findall(r'\$(\w+)', formula)
        variables.update(dollar_vars)

        # 匹配常見的 OHLCV 變數
        common_vars = ['open', 'high', 'low', 'close', 'volume', 'vwap', 'factor']
        for var in common_vars:
            if var.lower() in formula.lower():
                variables.add(var.lower())

        return sorted(list(variables))

    def _categorize_factor(self, formula: str, variables: List[str]) -> str:
        """根據公式和變數對因子分類

        Args:
            formula: Qlib 表達式公式
            variables: 變數列表

        Returns:
            category: 因子類別（momentum, value, quality, volatility, volume, technical）
        """
        formula_lower = formula.lower()

        # 動量類
        if any(kw in formula_lower for kw in ['mean', 'ref', 'delta', 'rank']):
            return "momentum"

        # 波動率類
        if any(kw in formula_lower for kw in ['std', 'var', 'volatility', 'atr']):
            return "volatility"

        # 成交量類
        if 'volume' in variables or 'vol' in formula_lower:
            return "volume"

        # 技術指標類
        if any(kw in formula_lower for kw in ['ma', 'ema', 'rsi', 'macd', 'corr']):
            return "technical"

        # 默認為價值類
        return "value"

    def calculate_llm_costs(self, log_dir: str) -> Tuple[int, float]:
        """計算 LLM API 使用成本

        從 debug_llm.pkl 中提取 API 調用統計，基於 GPT-4-turbo 定價計算成本

        定價參考 (2024-12)：
        - GPT-4-turbo: $0.01/1K input tokens, $0.03/1K output tokens

        Args:
            log_dir: RD-Agent 日誌目錄路徑

        Returns:
            (llm_calls, llm_cost): API 調用次數和估計成本（美元）
        """
        logger.info(f"Calculating LLM costs from {log_dir}")

        log_path = Path(log_dir)
        debug_llm_file = log_path / "debug_llm.pkl"

        llm_calls = 0
        total_input_tokens = 0
        total_output_tokens = 0

        if debug_llm_file.exists():
            try:
                with open(debug_llm_file, "rb") as f:
                    llm_debug_data = pickle.load(f)

                # 提取調用記錄
                if isinstance(llm_debug_data, list):
                    llm_calls = len(llm_debug_data)

                    for call in llm_debug_data:
                        if isinstance(call, dict):
                            # 提取 token 使用量
                            usage = call.get("usage", {})
                            total_input_tokens += usage.get("prompt_tokens", 0)
                            total_output_tokens += usage.get("completion_tokens", 0)

                logger.info(f"LLM API calls: {llm_calls}")
                logger.info(f"Total input tokens: {total_input_tokens}")
                logger.info(f"Total output tokens: {total_output_tokens}")

            except Exception as e:
                logger.error(f"Failed to parse debug_llm.pkl: {e}")
        else:
            logger.warning(f"debug_llm.pkl not found at {debug_llm_file}")
            # 估算：假設每次迭代調用 2 次 LLM
            llm_calls = 2

        # 計算成本（GPT-4-turbo 定價）
        input_cost = (total_input_tokens / 1000) * 0.01
        output_cost = (total_output_tokens / 1000) * 0.03
        llm_cost = input_cost + output_cost

        # 如果無法獲取 token 數據，使用保守估算
        if total_input_tokens == 0 and total_output_tokens == 0:
            # 假設每次調用平均使用 2000 tokens
            estimated_tokens = llm_calls * 2000
            llm_cost = (estimated_tokens / 1000) * 0.02  # 平均成本

        logger.info(f"Estimated LLM cost: ${llm_cost:.4f}")

        return llm_calls, round(llm_cost, 4)

    # ========== 模型生成功能 ==========

    def create_model_generation_task(
        self, user_id: int, request: ModelGenerationRequest
    ) -> RDAgentTask:
        """建立模型生成任務"""
        task = RDAgentTask(
            user_id=user_id,
            task_type=TaskType.MODEL_GENERATION,
            status=TaskStatus.PENDING,
            input_params={
                "research_goal": request.research_goal,
                "model_type": request.model_type,
                "llm_model": request.llm_model,
                "max_iterations": request.max_iterations,
            }
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        logger.info(f"Created model generation task {task.id} for user {user_id}")
        return task

    def execute_model_generation(
        self,
        task_id: int,
        research_goal: str,
        max_iterations: int = 5,
        llm_model: str = "gpt-4-turbo",
    ) -> str:
        """執行 RD-Agent 模型生成

        Args:
            task_id: 任務 ID
            research_goal: 研究目標（用於日誌，實際 RD-Agent 會自動決定）
            max_iterations: 最大迭代次數
            llm_model: LLM 模型名稱

        Returns:
            log_dir: 日誌目錄路徑

        Raises:
            Exception: 執行失敗時拋出異常
        """
        logger.info(f"Starting model generation for task {task_id}")
        logger.info(f"Research goal: {research_goal}")
        logger.info(f"Max iterations: {max_iterations}")
        logger.info(f"LLM model: {llm_model}")

        # 設定環境變數
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
        os.environ["QLIB_DATA_PATH"] = os.getenv("QLIB_DATA_PATH", "/data/qlib/tw_stock_v2")

        if not os.environ["OPENAI_API_KEY"]:
            raise ValueError("OPENAI_API_KEY not configured")

        try:
            # 導入 RD-Agent 模型生成模組
            from rdagent.app.qlib_rd_loop.model import main

            # 執行模型生成
            logger.info(f"Executing RD-Agent model generation with {max_iterations} iterations...")
            main(step_n=max_iterations)

            # 查找最新的日誌目錄
            log_base_dir = Path("/app/log")
            if not log_base_dir.exists():
                raise FileNotFoundError("Log directory /app/log not found")

            # 獲取最新的時間戳目錄
            log_dirs = sorted(log_base_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not log_dirs:
                raise FileNotFoundError("No log directories found")

            log_dir = str(log_dirs[0])
            logger.info(f"RD-Agent model generation completed. Log directory: {log_dir}")

            return log_dir

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Model generation execution failed: {str(e)}")
            logger.error(f"Full traceback:\n{error_trace}")
            raise

    def parse_model_generation_results(self, log_dir: str) -> List[Dict[str, Any]]:
        """解析 RD-Agent 模型生成結果

        從 .pkl 日誌檔案中提取生成的模型定義

        Args:
            log_dir: RD-Agent 日誌目錄路徑

        Returns:
            models: 模型列表，每個模型包含 name, description, model_type, architecture, etc.
        """
        logger.info(f"Parsing RD-Agent model generation results from {log_dir}")

        log_path = Path(log_dir)
        if not log_path.exists():
            raise FileNotFoundError(f"Log directory not found: {log_dir}")

        models = []

        # 遍歷所有迭代目錄 (Loop_0, Loop_1, ...)
        for loop_dir in sorted(log_path.glob("Loop_*")):
            loop_num = int(loop_dir.name.split("_")[1])
            logger.info(f"Processing {loop_dir.name}...")

            # 查找 experiment generation 結果 pickle 檔案
            exp_gen_pattern = loop_dir / "direct_exp_gen" / "r" / "experiment generation" / "**" / "*.pkl"
            exp_pkl_files = sorted(log_path.glob(str(exp_gen_pattern.relative_to(log_path))))

            if not exp_pkl_files:
                logger.warning(f"No experiment pickle files found in {loop_dir}")
                continue

            # 讀取所有實驗 pickle 檔案
            for exp_file in exp_pkl_files:
                try:
                    with open(exp_file, "rb") as f:
                        experiment_data = pickle.load(f)

                    logger.info(f"Loaded experiment from {exp_file.name}")

                    # experiment_data 應該是包含 ModelTask 物件的列表
                    if isinstance(experiment_data, list):
                        for task in experiment_data:
                            model = self._extract_model_from_task(task, loop_num)
                            if model:
                                models.append(model)
                                logger.info(f"Extracted model: {model['name']}")

                except Exception as e:
                    logger.error(f"Failed to load {exp_file}: {e}")

        logger.info(f"Parsed {len(models)} models from RD-Agent results")
        return models

    def _extract_model_from_task(self, task: Any, loop_num: int) -> Optional[Dict[str, Any]]:
        """從 ModelTask 物件中提取模型定義並生成代碼

        Args:
            task: ModelTask 物件
            loop_num: 迭代編號

        Returns:
            model: 模型字典，包含 name, description, architecture, code, qlib_config 等
        """
        try:
            # 提取模型屬性
            model_name = getattr(task, 'name', None) or getattr(task, 'model_name', None) or f"Model_Loop{loop_num}"
            model_description = getattr(task, 'description', '') or getattr(task, 'model_description', '')
            model_type = getattr(task, 'model_type', 'TimeSeries')  # 默認為時間序列
            formulation = getattr(task, 'formulation', '') or getattr(task, 'model_formulation', '')
            architecture = getattr(task, 'architecture', '') or getattr(task, 'model_architecture', '')
            variables = getattr(task, 'variables', {})
            hyperparameters = getattr(task, 'hyperparameters', {})

            # 清理模型名稱（移除特殊字元）
            if model_name and '<' in model_name:
                # 處理 <ModelTask[GRUFinancialModel]> 格式
                match = re.search(r'\[(.+?)\]', model_name)
                if match:
                    model_name = match.group(1)

            # ========== 新增：生成 PyTorch 代碼和 Qlib 配置 ==========
            code = None
            qlib_config = None

            if architecture:  # 只有當有架構描述時才生成代碼
                try:
                    logger.info(f"Generating PyTorch code for {model_name}...")
                    code, qlib_config = ModelCodeGenerator.generate_pytorch_code(
                        model_name=model_name,
                        model_type=model_type,
                        architecture=architecture,
                        hyperparameters=hyperparameters,
                        formulation=formulation
                    )
                    logger.info(f"✅ Successfully generated code for {model_name}")
                    logger.info(f"   Code length: {len(code)} characters")
                    logger.info(f"   Qlib config keys: {list(qlib_config.keys())}")
                except Exception as e:
                    logger.error(f"❌ Failed to generate code for {model_name}: {e}")
                    logger.warning(f"   Model will be saved without code")
            else:
                logger.warning(f"No architecture description for {model_name}, skipping code generation")

            model = {
                "name": model_name,
                "description": model_description or f"Model generated in Loop {loop_num}",
                "model_type": model_type,
                "formulation": formulation,
                "architecture": architecture,
                "variables": variables if isinstance(variables, dict) else {},
                "hyperparameters": hyperparameters if isinstance(hyperparameters, dict) else {},
                "code": code,  # 新增：生成的代碼
                "qlib_config": qlib_config,  # 新增：Qlib 配置
                "iteration": loop_num,
                "metadata": {
                    "loop_num": loop_num,
                    "task_type": type(task).__name__,
                    "code_generated": code is not None,  # 標記是否生成了代碼
                }
            }

            return model

        except Exception as e:
            logger.error(f"Failed to extract model from task: {e}")
            return None

    def save_generated_model(
        self,
        task_id: int,
        user_id: int,
        name: str,
        model_type: str,
        description: Optional[str] = None,
        formulation: Optional[str] = None,
        architecture: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        hyperparameters: Optional[Dict[str, Any]] = None,
        code: Optional[str] = None,  # 新增：模型代碼
        qlib_config: Optional[Dict[str, Any]] = None,  # 新增：Qlib 配置
        iteration: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> GeneratedModel:
        """保存生成的模型"""
        model = GeneratedModel(
            task_id=task_id,
            user_id=user_id,
            name=name,
            model_type=model_type,
            description=description,
            formulation=formulation,
            architecture=architecture,
            variables=variables,
            hyperparameters=hyperparameters,
            code=code,  # 新增：保存代碼
            qlib_config=qlib_config,  # 新增：保存 Qlib 配置
            iteration=iteration,
            model_metadata=metadata
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)

        logger.info(f"Saved generated model {model.id}: {name}")
        if code:
            logger.info(f"  ✅ Model includes generated code ({len(code)} characters)")
        if qlib_config:
            logger.info(f"  ✅ Model includes Qlib config")
        return model

    def get_generated_models(
        self, user_id: int, limit: int = 100
    ) -> List[GeneratedModel]:
        """獲取生成的模型列表"""
        return GeneratedModelRepository.get_by_user(
            self.db,
            user_id,
            skip=0,
            limit=limit
        )

    def get_generated_model(
        self, model_id: int, user_id: int
    ) -> Optional[GeneratedModel]:
        """獲取單一模型詳情

        Args:
            model_id: 模型 ID
            user_id: 用戶 ID（用於權限檢查）

        Returns:
            模型對象，如果不存在或無權限則返回 None
        """
        return GeneratedModelRepository.get_by_id_and_user(
            self.db, model_id, user_id
        )

    async def export_model_as_qlib_strategy(
        self,
        db: Session,
        user_id: int,
        model_id: int,
        model,
        training_job,
        strategy_name: str,
        buy_threshold: float,
        sell_threshold: float,
        description: Optional[str] = None
    ) -> int:
        """
        將訓練好的模型導出為 Qlib 策略

        Args:
            db: 資料庫 session
            user_id: 用戶 ID
            model_id: 模型 ID
            model: GeneratedModel 對象
            training_job: ModelTrainingJob 對象
            strategy_name: 策略名稱
            buy_threshold: 買入閾值
            sell_threshold: 賣出閾值
            description: 策略描述

        Returns:
            創建的策略 ID
        """
        from app.repositories.strategy import StrategyRepository
        from app.schemas.strategy import StrategyCreate
        from app.models.strategy import StrategyStatus

        # 生成 Qlib 策略代碼
        strategy_code = self._generate_qlib_strategy_template(
            model_id=model_id,
            model_name=model.name,
            model_weight_path=training_job.model_weight_path,
            buy_threshold=buy_threshold,
            sell_threshold=sell_threshold,
        )

        # 準備策略參數
        strategy_params = {
            "model_id": model_id,
            "model_name": model.name,
            "model_weight_path": training_job.model_weight_path,
            "buy_threshold": buy_threshold,
            "sell_threshold": sell_threshold,
            "test_ic": training_job.test_ic,
            "input_dim": 179,  # Alpha158+
        }

        # 準備策略描述
        if not description:
            # 格式化測試 IC（避免 f-string 格式化錯誤）
            test_ic_str = f"{training_job.test_ic:.4f}" if training_job.test_ic is not None else "N/A"

            description = f"""
基於 RD-Agent 訓練的 AI 模型策略

**模型資訊**:
- 模型 ID: {model_id}
- 模型名稱: {model.name}
- 測試集 IC: {test_ic_str}

**交易邏輯**:
- 買入閾值: {buy_threshold} (預測收益率 > {buy_threshold} 時買入)
- 賣出閾值: {sell_threshold} (預測收益率 < {sell_threshold} 時賣出)

**特徵工程**:
- 使用 Alpha158+ 因子集（179 個技術因子）
- 自動處理因子計算和數據對齊

**注意事項**:
- 此策略使用 Qlib 引擎運行
- 確保 Qlib 數據已同步
- 回測時建議使用至少 1 年的歷史數據
            """.strip()

        # 創建策略
        strategy_create = StrategyCreate(
            name=strategy_name,
            description=description,
            code=strategy_code,
            parameters=strategy_params,
            engine_type="qlib",
            status=StrategyStatus.ACTIVE
        )

        strategy = StrategyRepository.create(db, user_id, strategy_create)
        logger.info(f"Created Qlib strategy {strategy.id} from model {model_id}")

        return strategy.id

    def _generate_qlib_strategy_template(
        self,
        model_id: int,
        model_name: str,
        model_weight_path: str,
        buy_threshold: float,
        sell_threshold: float,
    ) -> str:
        """
        生成 Qlib 策略模板代碼

        Args:
            model_id: 模型 ID
            model_name: 模型名稱
            model_weight_path: 模型權重路徑
            buy_threshold: 買入閾值
            sell_threshold: 賣出閾值

        Returns:
            策略 Python 代碼
        """
        template = f'''"""
AI Model Strategy: {model_name}
Model ID: {model_id}
Auto-generated from RD-Agent trained model

此策略直接操作 signals 變量生成交易信號

注意：以下模組已由執行環境提供，無需導入：
- np, pd, torch: 數據處理和深度學習
- alpha158_calculator: Alpha158+ 因子計算
- SimpleMLP: 模型類別
- logger: 日誌記錄
- D: Qlib 數據 API
"""

# ===== 模型配置 =====
MODEL_WEIGHT_PATH = "{model_weight_path}"
BUY_THRESHOLD = {buy_threshold}
SELL_THRESHOLD = {sell_threshold}
INPUT_DIM = 179

# ===== 加載模型 =====
try:
    model = SimpleMLP(input_dim=INPUT_DIM, hidden_dims=[128, 64])
    model.load_state_dict(torch.load(MODEL_WEIGHT_PATH, map_location='cpu'))
    model.eval()
    logger.info(f"✅ Loaded AI model from {{MODEL_WEIGHT_PATH}}")
except Exception as e:
    logger.error(f"❌ Failed to load model: {{e}}")
    raise

# ===== 計算 Alpha158+ 因子 =====
try:
    # df 是由系統提供的數據（可能是技術指標，不是原始 OHLCV）
    # 我們需要從 Qlib 獲取原始 OHLCV 數據來計算 Alpha158+
    if df is None or df.empty:
        logger.warning("No data available")
    else:
        # D 對象已由執行環境提供，無需導入

        # 獲取股票代碼（從 params 或推斷）
        symbol = params.get('symbol', '2330')  # 默認台積電

        # 獲取原始 OHLCV 數據（與 df 相同的日期範圍）
        # 使用 .date().isoformat() 代替 strftime（避免 __import__ 錯誤）
        start_date = str(df.index[0].date())
        end_date = str(df.index[-1].date())

        logger.info(f"📊 Fetching OHLCV data for {{symbol}} from {{start_date}} to {{end_date}}")

        # 獲取原始數據
        raw_fields = ['$open', '$high', '$low', '$close', '$volume']
        df_raw = D.features(
            instruments=[symbol],
            fields=raw_fields,
            start_time=start_date,
            end_time=end_date,
            freq='day'
        )

        if df_raw is None or df_raw.empty:
            logger.error("Failed to fetch OHLCV data from Qlib")
            df_factors = None
        else:
            # 提取單一股票數據（Qlib 返回 MultiIndex：datetime, instrument）
            if isinstance(df_raw.index, pd.MultiIndex):
                # 使用 droplevel 而不是 xs，避免股票代碼被誤解析為日期
                df_raw = df_raw.droplevel(level=1)

            # 計算 Alpha158+ 因子（現在輸入是正確的 5 列 OHLCV）
            df_factors, _ = alpha158_calculator.compute_all_factors(df_raw)
            # 排除原始 OHLCV 列，只保留計算出的因子（179 個）
            factor_columns = [col for col in df_factors.columns if not col.startswith('$')]
            df_factors = df_factors[factor_columns]
            logger.info(f"✅ Computed Alpha158+ features: {{df_factors.shape}}")

        # ===== 模型預測 =====
        if df_factors is None or df_factors.empty:
            logger.error("No Alpha158+ features available, cannot generate predictions")
            predictions = [0.0] * len(df)
        else:
            predictions = []
            for idx in range(len(df_factors)):
                try:
                    features = torch.FloatTensor(df_factors.iloc[idx].values).unsqueeze(0)
                    with torch.no_grad():
                        pred = model(features).item()
                    predictions.append(pred)
                except Exception as e:
                    logger.warning(f"Prediction failed at index {{idx}}: {{e}}")
                    predictions.append(0.0)

        # ===== 生成交易信號 =====
        # signals 是預先創建的 pd.Series，初始值全為 0（持有）
        for i, pred in enumerate(predictions):
            if pred > BUY_THRESHOLD:
                signals.iloc[i] = 1  # 買入
            elif pred < SELL_THRESHOLD:
                signals.iloc[i] = -1  # 賣出
            # 否則保持 0（持有）

        buy_count = (signals == 1).sum()
        sell_count = (signals == -1).sum()
        hold_count = (signals == 0).sum()

        logger.info(f"📊 Generated signals:")
        logger.info(f"   Buy:  {{buy_count}} ({{buy_count/len(signals)*100:.1f}}%)")
        logger.info(f"   Sell: {{sell_count}} ({{sell_count/len(signals)*100:.1f}}%)")
        logger.info(f"   Hold: {{hold_count}} ({{hold_count/len(signals)*100:.1f}}%)")

except Exception as e:
    logger.error(f"❌ Strategy execution failed: {{e}}")
    # traceback 已由執行環境提供
    logger.error(traceback.format_exc())
    # 保持 signals 全為 0（不交易）

'''
        return template

    # Legacy BaseStrategy class template (保留注釋供參考)
    def _generate_qlib_basestrategy_template_OLD(
        self,
        model_id: int,
        model_name: str,
        model_weight_path: str,
        buy_threshold: float,
        sell_threshold: float,
    ) -> str:
        """
        舊版 BaseStrategy 類模板（已廢棄）

        注意：此模板定義了完整的 BaseStrategy 類，但當前 qlib_backtest_engine
        期望策略代碼直接操作 signals 變量，因此已不再使用。
        """
        template = f'''"""
AI Model Strategy: {model_name}
Model ID: {model_id}
Auto-generated from RD-Agent trained model
"""

import numpy as np
import pandas as pd
import torch
from qlib.data import D
from qlib.strategy.base import BaseStrategy
from app.services.alpha158_factors import alpha158_calculator
from app.services.model_predictor import SimpleMLP
from loguru import logger


class AIModelStrategy(BaseStrategy):
    """
    基於訓練好的 PyTorch 模型的交易策略

    模型: {model_name}
    買入閾值: {buy_threshold}
    賣出閾值: {sell_threshold}
    """

    def __init__(
        self,
        model_weight_path: str = "{model_weight_path}",
        buy_threshold: float = {buy_threshold},
        sell_threshold: float = {sell_threshold},
        input_dim: int = 179,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.model_weight_path = model_weight_path
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

        # 加載模型
        self.model = SimpleMLP(input_dim=input_dim, hidden_dims=[128, 64])
        self.model.load_state_dict(torch.load(model_weight_path, map_location='cpu'))
        self.model.eval()
        logger.info(f"✅ Loaded AI model from {{self.model_weight_path}}")

    def generate_trade_decision(self, execute_result=None):
        """
        生成交易決策

        Returns:
            dict: {{stock_id: weight}} - 股票權重字典
        """
        trade_date = self.trade_calendar[self.trade_step]

        # 獲取可交易股票
        list_kwargs = {{
            "start_time": trade_date,
            "end_time": trade_date,
            "as_list": True,
        }}
        if self.level_infra is not None:
            list_kwargs["inst_list"] = self.level_infra.get(trade_date)
        inst_list = D.list_instruments(**list_kwargs)

        # 為每支股票計算預測值
        predictions = {{}}
        for stock_id in inst_list:
            try:
                # 獲取 Alpha158+ 因子
                df_factors = self._get_alpha158_features(stock_id, trade_date)
                if df_factors is None or df_factors.empty:
                    continue

                # 模型預測
                features = torch.FloatTensor(df_factors.values)
                with torch.no_grad():
                    pred = self.model(features).item()

                predictions[stock_id] = pred
            except Exception as e:
                logger.warning(f"❌ Failed to predict {{stock_id}}: {{e}}")
                continue

        # 根據閾值生成交易信號
        weights = {{}}
        for stock_id, pred in predictions.items():
            if pred > self.buy_threshold:
                weights[stock_id] = 1.0  # 買入
            elif pred < self.sell_threshold:
                weights[stock_id] = 0.0  # 賣出（權重為 0）

        # 正規化權重
        if weights:
            total_weight = sum(weights.values())
            if total_weight > 0:
                weights = {{k: v / total_weight for k, v in weights.items()}}

        logger.info(f"📊 Trade date {{trade_date}}: {{len(predictions)}} predictions, {{len(weights)}} positions")
        return weights

    def _get_alpha158_features(self, stock_id: str, end_date) -> pd.DataFrame:
        """獲取 Alpha158+ 因子"""
        try:
            # 獲取足夠的歷史數據（Alpha158 需要 60 天）
            start_date = pd.Timestamp(end_date) - pd.Timedelta(days=120)

            raw_fields = ['$open', '$high', '$low', '$close', '$volume']
            df_raw = D.features(
                instruments=[stock_id],
                fields=raw_fields,
                start_time=start_date.strftime('%Y-%m-%d'),
                end_time=end_date.strftime('%Y-%m-%d'),
                freq='day'
            )

            if df_raw is None or df_raw.empty:
                return None

            # 提取單一股票數據
            if isinstance(df_raw.index, pd.MultiIndex):
                df_raw = df_raw.xs(stock_id, level=1)

            # 計算 Alpha158+ 因子
            df_factors, _ = alpha158_calculator.compute_all_factors(df_raw)

            # 只返回當天的因子
            return df_factors.iloc[[-1]]

        except Exception as e:
            logger.warning(f"❌ Failed to get Alpha158+ for {{stock_id}}: {{e}}")
            return None
'''
        return template
