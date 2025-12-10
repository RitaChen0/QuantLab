"""RD-Agent Pydantic Schemas"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class TaskType(str, Enum):
    FACTOR_MINING = "factor_mining"
    STRATEGY_OPTIMIZATION = "strategy_optimization"
    MODEL_EXTRACTION = "model_extraction"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ========== 請求 Schemas ==========

class FactorMiningRequest(BaseModel):
    """因子挖掘請求"""
    research_goal: str = Field(..., description="研究目標描述")
    stock_pool: Optional[str] = Field(None, description="股票池（如：台股全市場）")
    max_factors: int = Field(5, ge=1, le=20, description="最多生成幾個因子")
    llm_model: str = Field("gpt-4", description="使用的 LLM 模型")
    max_iterations: int = Field(3, ge=1, le=10, description="最大迭代次數")


class StrategyOptimizationRequest(BaseModel):
    """策略優化請求"""
    strategy_id: int = Field(..., description="要優化的策略 ID")
    optimization_goal: str = Field(..., description="優化目標（如：提升 Sharpe Ratio）")
    llm_model: str = Field("gpt-4", description="使用的 LLM 模型")
    max_iterations: int = Field(5, ge=1, le=20, description="最大迭代次數")


# ========== 響應 Schemas ==========

class GeneratedFactorResponse(BaseModel):
    """生成的因子響應"""
    id: int
    name: str
    description: Optional[str]
    formula: str
    code: Optional[str] = None
    category: Optional[str]
    ic: Optional[float]
    icir: Optional[float]
    sharpe_ratio: Optional[float]
    annual_return: Optional[float]
    created_at: datetime
    evaluation_count: int = 0  # 評估歷史數量

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z' if v else None
        }


class UpdateGeneratedFactorRequest(BaseModel):
    """更新生成的因子請求"""
    name: Optional[str] = None
    description: Optional[str] = None


class RDAgentTaskResponse(BaseModel):
    """RD-Agent 任務響應"""
    id: int
    user_id: int
    task_type: TaskType
    status: TaskStatus
    input_params: Optional[Dict[str, Any]]
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    llm_calls: int
    llm_cost: float
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    generated_factors: Optional[List[GeneratedFactorResponse]] = []

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z' if v else None
        }
