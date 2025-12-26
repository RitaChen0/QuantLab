"""
模型代码生成器

根据 RD-Agent 生成的架构描述和超参数，自动生成 PyTorch/Qlib 兼容的模型代码
"""

from typing import Dict, Any, Optional, Tuple
from loguru import logger


class ModelCodeGenerator:
    """模型代码生成器"""

    @staticmethod
    def generate_pytorch_code(
        model_name: str,
        model_type: str,
        architecture: str,
        hyperparameters: Dict[str, Any],
        formulation: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """生成 PyTorch 模型代码和 Qlib 配置

        Args:
            model_name: 模型名称
            model_type: 模型类型 (TimeSeries/Tabular)
            architecture: 架构描述
            hyperparameters: 超参数字典
            formulation: 数学公式（可选）

        Returns:
            code: Python 代码字符串
            qlib_config: Qlib 配置字典
        """
        logger.info(f"Generating PyTorch code for {model_name} ({model_type})")

        # 根据模型类型选择生成器
        if model_type == "TimeSeries":
            if "GRU" in model_name or "GRU" in architecture:
                return ModelCodeGenerator._generate_gru_model(
                    model_name, architecture, hyperparameters, formulation
                )
            elif "LSTM" in model_name or "LSTM" in architecture:
                return ModelCodeGenerator._generate_lstm_model(
                    model_name, architecture, hyperparameters, formulation
                )
            elif "Transformer" in model_name or "Transformer" in architecture:
                return ModelCodeGenerator._generate_transformer_model(
                    model_name, architecture, hyperparameters, formulation
                )
            else:
                # 默认使用 GRU
                return ModelCodeGenerator._generate_gru_model(
                    model_name, architecture, hyperparameters, formulation
                )
        else:  # Tabular
            return ModelCodeGenerator._generate_mlp_model(
                model_name, architecture, hyperparameters, formulation
            )

    @staticmethod
    def _generate_gru_model(
        model_name: str,
        architecture: str,
        hyperparameters: Dict[str, Any],
        formulation: Optional[str]
    ) -> Tuple[str, Dict[str, Any]]:
        """生成 GRU 模型代码"""

        # 提取超参数（提供默认值）
        hidden_dim = int(hyperparameters.get('hidden_dim', 128))
        num_layers = int(hyperparameters.get('num_layers', 2))
        dropout = float(hyperparameters.get('dropout', 0.1))
        learning_rate = float(hyperparameters.get('learning_rate', 0.001))
        batch_size = int(hyperparameters.get('batch_size', 64))
        num_epochs = int(hyperparameters.get('num_epochs', 50))

        code = f'''"""
{model_name} - GRU-based Time Series Model

架構描述:
{architecture}

超參數:
- hidden_dim: {hidden_dim}
- num_layers: {num_layers}
- dropout: {dropout}
- learning_rate: {learning_rate}
- batch_size: {batch_size}
- num_epochs: {num_epochs}
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from qlib.model.base import Model
from qlib.data.dataset import DataHandlerLP


class {model_name}(Model):
    """GRU-based Financial Time Series Model

    This model uses Gated Recurrent Units to capture temporal dependencies
    in financial time series data.
    """

    def __init__(
        self,
        d_feat: int = 20,  # 輸入特徵維度
        hidden_dim: int = {hidden_dim},
        num_layers: int = {num_layers},
        dropout: float = {dropout},
        **kwargs
    ):
        super().__init__()

        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.d_feat = d_feat

        # GRU layers
        self.gru = nn.GRU(
            input_size=d_feat,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )

        # Fully connected output layer
        self.fc = nn.Linear(hidden_dim, 1)

        # Dropout layer
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        """Forward pass

        Args:
            x: Input tensor of shape (batch_size, seq_len, d_feat)

        Returns:
            predictions: Output tensor of shape (batch_size, 1)
        """
        # x shape: (batch_size, seq_len, d_feat)

        # GRU forward
        # output shape: (batch_size, seq_len, hidden_dim)
        # h_n shape: (num_layers, batch_size, hidden_dim)
        output, h_n = self.gru(x)

        # Take the last hidden state
        # last_hidden shape: (batch_size, hidden_dim)
        last_hidden = output[:, -1, :]

        # Apply dropout
        last_hidden = self.dropout(last_hidden)

        # Fully connected layer
        # predictions shape: (batch_size, 1)
        predictions = self.fc(last_hidden)

        return predictions


# Qlib 訓練函數
def train_model(
    model,
    data_handler,
    optimizer,
    criterion,
    device,
    num_epochs={num_epochs}
):
    """訓練模型

    Args:
        model: {model_name} 實例
        data_handler: Qlib DataHandler
        optimizer: PyTorch optimizer
        criterion: Loss function
        device: 訓練設備 (cpu/cuda)
        num_epochs: 訓練輪數

    Returns:
        model: 訓練後的模型
        losses: 訓練損失列表
    """
    model = model.to(device)
    model.train()

    losses = []

    for epoch in range(num_epochs):
        epoch_loss = 0.0
        batch_count = 0

        # 從 data_handler 獲取訓練數據
        df_train = data_handler.fetch(selector='train')

        # 這裡需要根據實際的 Qlib DataHandler 調整數據載入邏輯
        # 以下是示例代碼
        for batch_idx in range(0, len(df_train), {batch_size}):
            batch_data = df_train.iloc[batch_idx:batch_idx+{batch_size}]

            # 準備輸入和目標
            # X shape: (batch_size, seq_len, d_feat)
            # y shape: (batch_size, 1)
            X = torch.FloatTensor(batch_data['feature'].values).to(device)
            y = torch.FloatTensor(batch_data['label'].values).to(device)

            # 前向傳播
            optimizer.zero_grad()
            predictions = model(X)

            # 計算損失
            loss = criterion(predictions, y)

            # 反向傳播
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()
            batch_count += 1

        avg_loss = epoch_loss / batch_count if batch_count > 0 else 0
        losses.append(avg_loss)

        if (epoch + 1) % 10 == 0:
            print(f'Epoch [{{epoch+1}}/{{num_epochs}}], Loss: {{avg_loss:.4f}}')

    return model, losses


# 使用示例
if __name__ == '__main__':
    # 初始化模型
    model = {model_name}(
        d_feat=20,
        hidden_dim={hidden_dim},
        num_layers={num_layers},
        dropout={dropout}
    )

    # 設置優化器
    optimizer = torch.optim.Adam(model.parameters(), lr={learning_rate})
    criterion = nn.MSELoss()
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    print(f'Model: {{model}}')
    print(f'Total parameters: {{sum(p.numel() for p in model.parameters())}}')
    print(f'Device: {{device}}')
'''

        # 生成 Qlib 配置
        qlib_config = {
            "model": {
                "class": model_name,
                "module_path": f"custom_models.{model_name.lower()}",
                "kwargs": {
                    "d_feat": 20,
                    "hidden_dim": hidden_dim,
                    "num_layers": num_layers,
                    "dropout": dropout
                }
            },
            "trainer": {
                "max_epochs": num_epochs,
                "batch_size": batch_size,
                "optimizer": {
                    "class": "Adam",
                    "lr": learning_rate
                },
                "loss": "mse",
                "GPU": 0
            },
            "data": {
                "handler": {
                    "class": "Alpha158",
                    "module_path": "qlib.contrib.data.handler",
                    "kwargs": {
                        "start_time": "2015-01-01",
                        "end_time": "2023-12-31",
                        "fit_start_time": "2015-01-01",
                        "fit_end_time": "2020-12-31",
                        "instruments": "csi300",
                        "label": ["Ref($close, -2) / Ref($close, -1) - 1"]
                    }
                }
            }
        }

        return code, qlib_config

    @staticmethod
    def _generate_lstm_model(
        model_name: str,
        architecture: str,
        hyperparameters: Dict[str, Any],
        formulation: Optional[str]
    ) -> Tuple[str, Dict[str, Any]]:
        """生成 LSTM 模型代码"""
        # 类似 GRU，但使用 LSTM
        # 为简化，这里直接复用 GRU 代码并替换为 LSTM
        code, config = ModelCodeGenerator._generate_gru_model(
            model_name, architecture, hyperparameters, formulation
        )

        # 替换 GRU 为 LSTM
        code = code.replace("GRU", "LSTM").replace("gru", "lstm")

        return code, config

    @staticmethod
    def _generate_transformer_model(
        model_name: str,
        architecture: str,
        hyperparameters: Dict[str, Any],
        formulation: Optional[str]
    ) -> Tuple[str, Dict[str, Any]]:
        """生成 Transformer 模型代码"""
        # TODO: 实现 Transformer 代码生成
        # 暂时返回 GRU 代码作为占位符
        logger.warning(f"Transformer code generation not yet implemented, using GRU as fallback")
        return ModelCodeGenerator._generate_gru_model(
            model_name, architecture, hyperparameters, formulation
        )

    @staticmethod
    def _generate_mlp_model(
        model_name: str,
        architecture: str,
        hyperparameters: Dict[str, Any],
        formulation: Optional[str]
    ) -> Tuple[str, Dict[str, Any]]:
        """生成 MLP 模型代码（用于 Tabular 类型）"""
        # TODO: 实现 MLP 代码生成
        logger.warning(f"MLP code generation not yet implemented, using GRU as fallback")
        return ModelCodeGenerator._generate_gru_model(
            model_name, architecture, hyperparameters, formulation
        )
