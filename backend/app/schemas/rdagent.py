"""RD-Agent Pydantic Schemas"""

from pydantic import BaseModel, Field, field_serializer
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import math


class TaskType(str, Enum):
    FACTOR_MINING = "factor_mining"
    MODEL_GENERATION = "model_generation"
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


class ModelGenerationRequest(BaseModel):
    """模型生成請求"""
    research_goal: str = Field(..., description="研究目標描述（如：為台指期貨創建時間序列預測模型）")
    model_type: Optional[str] = Field(None, description="模型類型偏好（TimeSeries/Tabular，不指定則自動選擇）")
    llm_model: str = Field("gpt-4", description="使用的 LLM 模型")
    max_iterations: int = Field(5, ge=1, le=20, description="最大迭代次數")


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
        # Pydantic v2 自動正確序列化 timezone-aware datetime
        # datetime 會序列化為 ISO 8601 格式（如 2025-12-20T00:18:21+00:00）


class UpdateGeneratedFactorRequest(BaseModel):
    """更新生成的因子請求"""
    name: Optional[str] = None
    description: Optional[str] = None


class GeneratedModelResponse(BaseModel):
    """生成的模型響應"""
    id: int
    name: str
    description: Optional[str]
    model_type: str
    formulation: Optional[str]
    architecture: Optional[str]
    variables: Optional[Dict[str, Any]]
    hyperparameters: Optional[Dict[str, Any]]
    code: Optional[str] = None
    qlib_config: Optional[Dict[str, Any]]
    sharpe_ratio: Optional[float]
    annual_return: Optional[float]
    max_drawdown: Optional[float]
    information_ratio: Optional[float]
    iteration: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
        # Pydantic v2 自動正確序列化 timezone-aware datetime


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
    generated_models: Optional[List[GeneratedModelResponse]] = []

    class Config:
        from_attributes = True
        # Pydantic v2 自動正確序列化 timezone-aware datetime
        # datetime 會序列化為 ISO 8601 格式（如 2025-12-20T00:18:21+00:00）


# ========== 模型訓練相關 Schemas ==========

class TrainingStatus(str, Enum):
    """訓練狀態"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class DatasetConfig(BaseModel):
    """數據集配置"""
    instruments: str = Field(..., description="股票池（如：台股50、全市場）")
    start_time: str = Field(..., description="訓練開始日期（YYYY-MM-DD）")
    end_time: str = Field(..., description="訓練結束日期（YYYY-MM-DD）")
    train_ratio: float = Field(0.7, ge=0.1, le=0.9, description="訓練集比例（0.1-0.9）")
    valid_ratio: float = Field(0.15, ge=0.05, le=0.4, description="驗證集比例（0.05-0.4）")
    test_ratio: float = Field(0.15, ge=0.05, le=0.4, description="測試集比例（0.05-0.4）")


class TrainingParams(BaseModel):
    """訓練參數"""
    num_epochs: int = Field(100, ge=1, le=1000, description="訓練輪數（1-1000）")
    batch_size: int = Field(800, ge=32, le=2048, description="批次大小（32-2048）")
    learning_rate: float = Field(0.001, gt=0, le=0.1, description="學習率（0-0.1）")
    early_stop_rounds: int = Field(20, ge=5, le=100, description="早停輪數（5-100）")
    optimizer: str = Field("adam", description="優化器（adam/sgd/rmsprop）")
    loss_function: str = Field("mse", description="損失函數（mse/mae/huber）")


class SelectFactorsRequest(BaseModel):
    """選擇因子請求（用於綁定模型與因子）"""
    factor_ids: List[int] = Field(..., min_length=1, max_length=50, description="選擇的因子 ID 列表（1-50 個）")


class ModelTrainingRequest(BaseModel):
    """模型訓練請求"""
    factor_ids: List[int] = Field(..., min_length=1, max_length=50, description="用於訓練的因子 ID 列表（1-50 個）")
    dataset_config: DatasetConfig = Field(..., description="數據集配置")
    training_params: TrainingParams = Field(..., description="訓練參數")


class ModelFactorResponse(BaseModel):
    """模型因子關聯響應"""
    id: int
    model_id: int
    factor_id: int
    feature_index: Optional[int]
    factor: Optional[GeneratedFactorResponse] = None  # 關聯的因子對象
    created_at: datetime

    class Config:
        from_attributes = True


class ModelTrainingJobResponse(BaseModel):
    """模型訓練任務響應"""
    id: int
    model_id: int
    user_id: int

    # 訓練配置
    dataset_config: Optional[Dict[str, Any]]
    training_params: Optional[Dict[str, Any]]

    # 訓練狀態（用於前端輪詢）
    status: str  # PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    progress: float = Field(0.0, ge=0.0, le=1.0, description="訓練進度（0.0-1.0）")
    current_epoch: int = Field(0, ge=0, description="當前訓練輪數")
    total_epochs: Optional[int] = Field(None, description="總訓練輪數")
    current_step: Optional[str] = Field(None, description="當前步驟描述（用於訊息欄顯示）")

    # 訓練指標（即時更新）
    train_loss: Optional[float] = None
    valid_loss: Optional[float] = None
    test_ic: Optional[float] = None
    test_metrics: Optional[Dict[str, Any]] = None

    # 模型權重
    model_weight_path: Optional[str] = None

    # 訓練日誌（多行文本，用於訊息欄詳細顯示）
    training_log: Optional[str] = None
    error_message: Optional[str] = None

    # Celery 任務 ID
    celery_task_id: Optional[str] = None

    # 時間戳
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    @field_serializer('train_loss', 'valid_loss', 'test_ic', when_used='always')
    def serialize_float(self, value: Optional[float]) -> Optional[float]:
        """Convert NaN/Inf to None for JSON serialization"""
        if value is None:
            return None
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    class Config:
        from_attributes = True


class ModelTrainingJobListResponse(BaseModel):
    """訓練任務列表響應"""
    jobs: List[ModelTrainingJobResponse]
    total: int
