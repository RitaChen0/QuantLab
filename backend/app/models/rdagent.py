"""
RD-Agent 相關資料庫模型

包含：
- RDAgentTask: RD-Agent 任務追蹤
- GeneratedFactor: 自動生成的交易因子
- FactorEvaluation: 因子評估結果
"""

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
import enum

from app.db.base import Base


class TaskStatus(str, enum.Enum):
    """任務狀態"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, enum.Enum):
    """任務類型"""
    FACTOR_MINING = "factor_mining"        # 因子挖掘
    MODEL_GENERATION = "model_generation"  # 模型生成
    STRATEGY_OPTIMIZATION = "strategy_optimization"  # 策略優化
    MODEL_EXTRACTION = "model_extraction"  # 模型提取


class RDAgentTask(Base):
    """RD-Agent 任務追蹤表"""
    __tablename__ = "rdagent_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 任務資訊
    task_type = Column(Enum(TaskType), nullable=False, index=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)

    # 輸入參數
    input_params = Column(JSON, nullable=True, comment="輸入參數（JSON 格式）")

    # 輸出結果
    result = Column(JSON, nullable=True, comment="任務結果（JSON 格式）")
    error_message = Column(Text, nullable=True, comment="錯誤訊息")

    # LLM 使用統計
    llm_calls = Column(Integer, default=0, comment="LLM API 呼叫次數")
    llm_cost = Column(Float, default=0.0, comment="LLM 成本（美元）")

    # 時間戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # 關聯
    user = relationship("User", back_populates="rdagent_tasks")
    generated_factors = relationship("GeneratedFactor", back_populates="task", cascade="all, delete-orphan")
    generated_models = relationship("GeneratedModel", back_populates="task", cascade="all, delete-orphan")


class GeneratedFactor(Base):
    """自動生成的交易因子"""
    __tablename__ = "generated_factors"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("rdagent_tasks.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 因子資訊
    name = Column(String(255), nullable=False, index=True, comment="因子名稱")
    description = Column(Text, nullable=True, comment="因子描述")
    formula = Column(Text, nullable=False, comment="Qlib 表達式公式")

    # 因子代碼
    code = Column(Text, nullable=True, comment="Python 實作代碼（可選）")

    # 因子類別
    category = Column(String(100), nullable=True, index=True, comment="因子類別（如：momentum, value, quality）")

    # 評估指標
    ic = Column(Float, nullable=True, comment="Information Coefficient")
    icir = Column(Float, nullable=True, comment="IC Information Ratio")
    sharpe_ratio = Column(Float, nullable=True, comment="Sharpe Ratio")
    annual_return = Column(Float, nullable=True, comment="年化報酬率")

    # 元數據
    factor_metadata = Column(JSON, nullable=True, comment="其他元數據")

    # 時間戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 關聯
    task = relationship("RDAgentTask", back_populates="generated_factors")
    user = relationship("User")
    evaluations = relationship("FactorEvaluation", back_populates="factor", cascade="all, delete-orphan")


class FactorEvaluation(Base):
    """因子評估結果"""
    __tablename__ = "factor_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    factor_id = Column(Integer, ForeignKey("generated_factors.id"), nullable=False, index=True)

    # 評估參數
    stock_pool = Column(String(255), nullable=True, comment="股票池")
    start_date = Column(String(20), nullable=True, comment="開始日期")
    end_date = Column(String(20), nullable=True, comment="結束日期")

    # 評估結果
    ic = Column(Float, nullable=True, comment="Information Coefficient")
    icir = Column(Float, nullable=True, comment="IC Information Ratio")
    rank_ic = Column(Float, nullable=True, comment="Rank IC")
    rank_icir = Column(Float, nullable=True, comment="Rank ICIR")

    # 回測結果
    sharpe_ratio = Column(Float, nullable=True, comment="Sharpe Ratio")
    annual_return = Column(Float, nullable=True, comment="年化報酬率")
    max_drawdown = Column(Float, nullable=True, comment="最大回撤")
    win_rate = Column(Float, nullable=True, comment="勝率")

    # 詳細結果
    detailed_results = Column(JSON, nullable=True, comment="詳細評估結果（JSON）")

    # 時間戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 關聯
    factor = relationship("GeneratedFactor", back_populates="evaluations")


class GeneratedModel(Base):
    """AI 生成的量化模型"""
    __tablename__ = "generated_models"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("rdagent_tasks.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 模型資訊
    name = Column(String(255), nullable=False, index=True, comment="模型名稱")
    description = Column(Text, nullable=True, comment="模型描述")
    model_type = Column(String(100), nullable=False, index=True, comment="模型類型（TimeSeries/Tabular）")

    # 模型架構
    formulation = Column(Text, nullable=True, comment="數學公式")
    architecture = Column(Text, nullable=True, comment="架構描述")
    variables = Column(JSON, nullable=True, comment="變數定義（JSON）")
    hyperparameters = Column(JSON, nullable=True, comment="超參數（JSON）")

    # 模型代碼
    code = Column(Text, nullable=True, comment="模型實作代碼")
    qlib_config = Column(JSON, nullable=True, comment="Qlib 配置（JSON）")

    # 評估指標
    sharpe_ratio = Column(Float, nullable=True, comment="Sharpe Ratio")
    annual_return = Column(Float, nullable=True, comment="年化報酬率")
    max_drawdown = Column(Float, nullable=True, comment="最大回撤")
    information_ratio = Column(Float, nullable=True, comment="Information Ratio")

    # 元數據
    iteration = Column(Integer, nullable=True, comment="迭代次數")
    model_metadata = Column(JSON, nullable=True, comment="其他元數據")

    # 時間戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 關聯
    task = relationship("RDAgentTask", back_populates="generated_models")
    user = relationship("User")
    model_factors = relationship("ModelFactor", back_populates="model", cascade="all, delete-orphan")
    training_jobs = relationship("ModelTrainingJob", back_populates="model", cascade="all, delete-orphan")


class ModelFactor(Base):
    """模型和因子的關聯表"""
    __tablename__ = "model_factors"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("generated_models.id", ondelete="CASCADE"), nullable=False, index=True)
    factor_id = Column(Integer, ForeignKey("generated_factors.id", ondelete="CASCADE"), nullable=False, index=True)

    # 因子配置
    feature_index = Column(Integer, nullable=True, comment="因子在特徵向量中的索引位置")

    # 時間戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 關聯
    model = relationship("GeneratedModel", back_populates="model_factors")
    factor = relationship("GeneratedFactor")


class ModelTrainingJob(Base):
    """模型訓練任務記錄"""
    __tablename__ = "model_training_jobs"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("generated_models.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 訓練配置
    dataset_config = Column(JSON, nullable=True, comment="數據集配置（JSON）")
    training_params = Column(JSON, nullable=True, comment="訓練參數（JSON）")

    # 訓練狀態
    status = Column(String(20), server_default="PENDING", nullable=False, comment="訓練狀態")
    progress = Column(Float, server_default="0.0", comment="訓練進度 0.0-1.0")
    current_epoch = Column(Integer, server_default="0", comment="當前訓練輪數")
    total_epochs = Column(Integer, nullable=True, comment="總訓練輪數")
    current_step = Column(String(100), nullable=True, comment="當前步驟描述")

    # 訓練指標
    train_loss = Column(Float, nullable=True, comment="訓練損失")
    valid_loss = Column(Float, nullable=True, comment="驗證損失")
    test_ic = Column(Float, nullable=True, comment="測試集 IC")
    test_metrics = Column(JSON, nullable=True, comment="詳細測試指標（JSON）")

    # 模型權重
    model_weight_path = Column(String(500), nullable=True, comment="訓練好的權重文件路徑")

    # 訓練日誌
    training_log = Column(Text, nullable=True, comment="訓練日誌（多行文本）")
    error_message = Column(Text, nullable=True, comment="錯誤訊息")

    # Celery 任務 ID
    celery_task_id = Column(String(255), nullable=True, comment="Celery 任務 ID")

    # 時間戳
    started_at = Column(DateTime(timezone=True), nullable=True, comment="開始時間")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="完成時間")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 關聯
    model = relationship("GeneratedModel", back_populates="training_jobs")
    user = relationship("User")
