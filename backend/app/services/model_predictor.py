"""
模型预测服务

加载训练好的 PyTorch 模型并生成预测
"""
import os
from typing import Dict, Optional
import torch
import numpy as np
import pandas as pd
from loguru import logger
from sqlalchemy.orm import Session

from app.repositories.generated_model import GeneratedModelRepository
from app.repositories.model_training_job import ModelTrainingJobRepository


class SimpleMLP(torch.nn.Module):
    """简单 MLP 模型（与训练时一致）"""

    def __init__(self, input_dim: int, hidden_dims=(128, 64), dropout=0.1):
        super().__init__()
        layers = []
        prev_dim = input_dim

        for hidden_dim in hidden_dims:
            layers.extend([
                torch.nn.Linear(prev_dim, hidden_dim),
                torch.nn.ReLU(),
                torch.nn.Dropout(dropout)
            ])
            prev_dim = hidden_dim

        layers.append(torch.nn.Linear(prev_dim, 1))  # 回归任务
        self.model = torch.nn.Sequential(*layers)

    def forward(self, x):
        return self.model(x)


class ModelPredictor:
    """训练好的模型预测器"""

    def __init__(
        self,
        model_weight_path: str,
        input_dim: int,
        hidden_dims=(128, 64),
        dropout=0.1
    ):
        """
        初始化预测器

        Args:
            model_weight_path: .pth 文件路径
            input_dim: 输入特征维度（因子数量）
            hidden_dims: 隐藏层维度
            dropout: Dropout 比率
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # 重建模型架构（必须与训练时一致）
        self.model = SimpleMLP(
            input_dim=input_dim,
            hidden_dims=hidden_dims,
            dropout=dropout
        ).to(self.device)

        # 加载权重
        if not os.path.exists(model_weight_path):
            raise FileNotFoundError(f"模型权重文件不存在: {model_weight_path}")

        self.model.load_state_dict(
            torch.load(model_weight_path, map_location=self.device)
        )
        self.model.eval()

        logger.info(f"✅ 模型加载成功: {model_weight_path}")
        logger.info(f"   设备: {self.device}")
        logger.info(f"   输入维度: {input_dim}")

    @classmethod
    def from_model_id(cls, db: Session, model_id: int) -> "ModelPredictor":
        """
        从模型 ID 创建预测器

        Args:
            db: 数据库 Session
            model_id: 模型 ID

        Returns:
            ModelPredictor 实例
        """
        # 确保所有模型已导入（修复 SQLAlchemy 关系映射问题）
        from app.db.session import ensure_models_imported
        ensure_models_imported()

        # 获取模型信息
        model = GeneratedModelRepository.get_by_id(db, model_id)
        if not model:
            raise ValueError(f"模型不存在: {model_id}")

        # 获取最新训练任务
        jobs = ModelTrainingJobRepository.get_by_model(db, model_id, limit=1)
        if not jobs or jobs[0].status != "COMPLETED":
            raise ValueError(f"模型 {model_id} 尚未训练完成")

        job = jobs[0]

        # 从 Qlib 配置获取模型参数
        qlib_config = model.qlib_config or {}
        model_kwargs = qlib_config.get('model', {}).get('kwargs', {})
        data_handler = qlib_config.get('data', {}).get('handler', {})

        # 确定输入维度
        # 优先从权重文件推断（最准确），否则使用配置值
        input_dim = cls._infer_input_dim_from_weights(job.model_weight_path)
        if input_dim is None:
            # 如果无法推断，使用配置或默认值
            if data_handler.get('class') == 'Alpha158':
                input_dim = 158  # Alpha158 标准特征数
                logger.info("无法推断维度，使用 Alpha158 默认值: input_dim=158")
            else:
                input_dim = model_kwargs.get('d_feat', 20)
                logger.info(f"无法推断维度，使用配置值: input_dim={input_dim}")
        else:
            logger.info(f"从权重文件成功推断 input_dim={input_dim}")

        hidden_dims = tuple(model_kwargs.get('hidden_size', [128, 64]))
        dropout = model_kwargs.get('dropout', 0.1)

        return cls(
            model_weight_path=job.model_weight_path,
            input_dim=input_dim,
            hidden_dims=hidden_dims,
            dropout=dropout
        )

    @staticmethod
    def _infer_input_dim_from_weights(model_weight_path: str) -> Optional[int]:
        """
        从权重文件推断输入维度

        Args:
            model_weight_path: 权重文件路径

        Returns:
            输入维度，如果无法推断则返回 None
        """
        try:
            weights = torch.load(model_weight_path, map_location='cpu')
            # 第一层权重的形状是 (hidden_dim, input_dim)
            first_layer_weight = weights.get('model.0.weight')
            if first_layer_weight is not None:
                input_dim = first_layer_weight.shape[1]
                logger.info(f"从权重文件推断 input_dim={input_dim}")
                return input_dim
        except Exception as e:
            logger.warning(f"无法从权重文件推断维度: {e}")
        return None

    def predict(self, features: np.ndarray) -> np.ndarray:
        """
        生成预测

        Args:
            features: 特征矩阵 (n_samples, d_feat)

        Returns:
            predictions: 预测值数组 (n_samples,)
        """
        if features.shape[0] == 0:
            return np.array([])

        with torch.no_grad():
            X_tensor = torch.FloatTensor(features).to(self.device)
            outputs = self.model(X_tensor)
            predictions = outputs.cpu().numpy().flatten()

        return predictions

    def predict_dataframe(self, df: pd.DataFrame) -> pd.Series:
        """
        从 DataFrame 生成预测

        Args:
            df: 包含因子数据的 DataFrame

        Returns:
            predictions: 预测序列 (index 与 df 相同)
        """
        # 提取特征列（排除基础价格字段）
        exclude_cols = ['$open', '$high', '$low', '$close', '$volume', '$factor', 'label']
        feature_cols = [col for col in df.columns if col not in exclude_cols]

        if len(feature_cols) == 0:
            raise ValueError("DataFrame 中没有特征列")

        # 填充 NaN
        X = df[feature_cols].fillna(0).values

        # 生成预测
        preds = self.predict(X)

        return pd.Series(preds, index=df.index, name='prediction')

    def predict_with_signals(
        self,
        df: pd.DataFrame,
        buy_threshold: float = 0.02,
        sell_threshold: float = -0.02
    ) -> pd.DataFrame:
        """
        生成预测并转换为交易信号

        Args:
            df: 包含因子数据的 DataFrame
            buy_threshold: 买入阈值
            sell_threshold: 卖出阈值

        Returns:
            包含 prediction 和 signal 列的 DataFrame
        """
        predictions = self.predict_dataframe(df)

        # 生成信号
        signals = pd.Series(0, index=df.index, name='signal')
        signals[predictions > buy_threshold] = 1  # 买入
        signals[predictions < sell_threshold] = -1  # 卖出

        result = pd.DataFrame({
            'prediction': predictions,
            'signal': signals
        })

        return result
