"""
RD-Agent 相關資料庫模型

包含：
- RDAgentTask: RD-Agent 任務追蹤
- GeneratedFactor: 自動生成的交易因子
- FactorEvaluation: 因子評估結果
"""

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # 關聯
    user = relationship("User", back_populates="rdagent_tasks")
    generated_factors = relationship("GeneratedFactor", back_populates="task", cascade="all, delete-orphan")


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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 關聯
    factor = relationship("GeneratedFactor", back_populates="evaluations")
