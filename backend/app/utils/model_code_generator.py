"""
模型代码生成器

根据 RD-Agent 生成的架构描述和超参数，自动生成 PyTorch/Qlib 兼容的模型代码
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime
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
        """生成 Transformer 模型代碼

        Transformer 架構特點：
        - Multi-Head Self-Attention 機制
        - Position Encoding（支持時序數據）
        - Feed Forward Network
        - Layer Normalization 和 Residual Connection

        適用場景：
        - 長序列時序預測
        - 捕捉長期依賴關係
        - 處理複雜的特徵交互
        """
        # 提取超參數
        hidden_dim = hyperparameters.get('hidden_dim', 128)
        num_layers = hyperparameters.get('num_layers', 2)
        num_heads = hyperparameters.get('num_heads', 4)
        dropout = hyperparameters.get('dropout', 0.1)
        learning_rate = hyperparameters.get('learning_rate', 0.001)
        num_epochs = hyperparameters.get('num_epochs', 100)
        batch_size = hyperparameters.get('batch_size', 32)

        # 生成 PyTorch 模型代碼
        code = f'''"""
{model_name} - Transformer 時序預測模型

架構: {architecture}
生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

模型說明:
- 使用 Multi-Head Self-Attention 機制捕捉時序依賴
- Position Encoding 編碼時間位置信息
- 多層 Transformer Encoder 提取高階特徵
- 適合處理長序列和複雜模式

超參數:
- hidden_dim: {hidden_dim} (嵌入維度)
- num_layers: {num_layers} (Transformer 層數)
- num_heads: {num_heads} (注意力頭數)
- dropout: {dropout}
- learning_rate: {learning_rate}
- num_epochs: {num_epochs}
- batch_size: {batch_size}
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
import numpy as np
from typing import Optional


class PositionalEncoding(nn.Module):
    """位置編碼層

    為序列中的每個位置添加位置信息，使 Transformer 能夠感知時序關係。
    使用正弦和餘弦函數生成位置編碼。
    """

    def __init__(self, d_model: int, max_len: int = 5000, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        # 創建位置編碼矩陣
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))

        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)

        self.register_buffer('pe', pe)

    def forward(self, x):
        """
        Args:
            x: (batch_size, seq_len, d_model)
        Returns:
            x + positional_encoding: (batch_size, seq_len, d_model)
        """
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)


class {model_name}(nn.Module):
    """Transformer 時序預測模型

    使用標準的 Transformer Encoder 架構進行時序預測。
    適合捕捉長期依賴和複雜的時序模式。

    Args:
        d_feat: 輸入特徵維度
        hidden_dim: 隱藏層維度（嵌入維度）
        num_layers: Transformer encoder 層數
        num_heads: Multi-head attention 的頭數
        dropout: Dropout 比率
    """

    def __init__(
        self,
        d_feat: int,
        hidden_dim: int = {hidden_dim},
        num_layers: int = {num_layers},
        num_heads: int = {num_heads},
        dropout: float = {dropout},
        **kwargs
    ):
        super().__init__()

        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.num_heads = num_heads
        self.d_feat = d_feat

        # 輸入嵌入層（將輸入特徵映射到 hidden_dim）
        self.input_embedding = nn.Linear(d_feat, hidden_dim)

        # 位置編碼
        self.positional_encoding = PositionalEncoding(
            d_model=hidden_dim,
            dropout=dropout
        )

        # Transformer Encoder Layer
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim * 4,  # FFN 隱藏層維度
            dropout=dropout,
            activation='relu',
            batch_first=True
        )

        # Transformer Encoder (堆疊多層)
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers
        )

        # 輸出層
        self.fc_out = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1)
        )

        # Layer Normalization
        self.layer_norm = nn.LayerNorm(hidden_dim)

    def forward(self, x):
        """Forward pass

        Args:
            x: Input tensor of shape (batch_size, seq_len, d_feat)

        Returns:
            predictions: Output tensor of shape (batch_size, 1)
        """
        # x shape: (batch_size, seq_len, d_feat)

        # 1. 輸入嵌入
        # embedded shape: (batch_size, seq_len, hidden_dim)
        embedded = self.input_embedding(x)

        # 2. 添加位置編碼
        # embedded shape: (batch_size, seq_len, hidden_dim)
        embedded = self.positional_encoding(embedded)

        # 3. Transformer Encoder
        # encoder_output shape: (batch_size, seq_len, hidden_dim)
        encoder_output = self.transformer_encoder(embedded)

        # 4. 取最後一個時間步的輸出
        # last_hidden shape: (batch_size, hidden_dim)
        last_hidden = encoder_output[:, -1, :]

        # 5. Layer Normalization
        last_hidden = self.layer_norm(last_hidden)

        # 6. 輸出層
        # predictions shape: (batch_size, 1)
        predictions = self.fc_out(last_hidden)

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

            # 梯度裁剪（防止梯度爆炸）
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

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
        num_heads={num_heads},
        dropout={dropout}
    )

    # 設置優化器
    optimizer = torch.optim.Adam(model.parameters(), lr={learning_rate})
    criterion = nn.MSELoss()
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    print(f'Model: {{model}}')
    print(f'Total parameters: {{sum(p.numel() for p in model.parameters())}}')
    print(f'Device: {{device}}')

    # 計算模型大小
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f'Trainable parameters: {{trainable_params}} / {{total_params}}')
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
                    "num_heads": num_heads,
                    "dropout": dropout
                }
            },
            "trainer": {
                "max_epochs": num_epochs,
                "batch_size": batch_size,
                "optimizer": {
                    "class": "Adam",
                    "lr": learning_rate,
                    "weight_decay": 1e-5
                },
                "loss": "mse",
                "GPU": 0,
                "early_stop": {
                    "enable": True,
                    "patience": 10,
                    "min_delta": 1e-5
                }
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

        logger.info(f"Generated Transformer model code for {model_name}")

        return code, qlib_config

    @staticmethod
    def _generate_mlp_model(
        model_name: str,
        architecture: str,
        hyperparameters: Dict[str, Any],
        formulation: Optional[str]
    ) -> Tuple[str, Dict[str, Any]]:
        """生成 MLP 模型代碼（用於表格數據）

        Multi-Layer Perceptron (MLP) 特點：
        - 全連接神經網絡
        - 適合表格/特徵數據
        - 簡單高效，易於訓練
        - 適合作為 baseline 模型

        適用場景：
        - 橫截面特徵預測
        - 非時序數據
        - 快速原型開發
        """
        # 提取超參數
        hidden_dim = hyperparameters.get('hidden_dim', 128)
        num_layers = hyperparameters.get('num_layers', 3)
        dropout = hyperparameters.get('dropout', 0.2)
        learning_rate = hyperparameters.get('learning_rate', 0.001)
        num_epochs = hyperparameters.get('num_epochs', 100)
        batch_size = hyperparameters.get('batch_size', 64)
        activation = hyperparameters.get('activation', 'relu')

        # 生成 PyTorch 模型代碼
        code = f'''"""
{model_name} - MLP 表格數據預測模型

架構: {architecture}
生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

模型說明:
- 多層全連接神經網絡（Multi-Layer Perceptron）
- 適合處理表格特徵數據
- 使用 Batch Normalization 穩定訓練
- 使用 Dropout 防止過擬合

超參數:
- hidden_dim: {hidden_dim} (隱藏層維度)
- num_layers: {num_layers} (隱藏層數量)
- dropout: {dropout}
- activation: {activation}
- learning_rate: {learning_rate}
- num_epochs: {num_epochs}
- batch_size: {batch_size}
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional


class {model_name}(nn.Module):
    """MLP 表格數據預測模型

    標準的全連接神經網絡，適合處理橫截面特徵數據。
    使用 Batch Normalization 和 Dropout 提高模型穩定性和泛化能力。

    Args:
        d_feat: 輸入特徵維度
        hidden_dim: 隱藏層維度
        num_layers: 隱藏層數量
        dropout: Dropout 比率
        activation: 激活函數類型 ('relu', 'tanh', 'gelu')
    """

    def __init__(
        self,
        d_feat: int,
        hidden_dim: int = {hidden_dim},
        num_layers: int = {num_layers},
        dropout: float = {dropout},
        activation: str = '{activation}',
        **kwargs
    ):
        super().__init__()

        self.d_feat = d_feat
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.dropout = dropout

        # 設置激活函數
        if activation == 'relu':
            self.activation = nn.ReLU()
        elif activation == 'tanh':
            self.activation = nn.Tanh()
        elif activation == 'gelu':
            self.activation = nn.GELU()
        else:
            self.activation = nn.ReLU()

        # 構建網絡層
        layers = []

        # 輸入層
        layers.append(nn.Linear(d_feat, hidden_dim))
        layers.append(nn.BatchNorm1d(hidden_dim))
        layers.append(self.activation)
        layers.append(nn.Dropout(dropout))

        # 隱藏層
        for _ in range(num_layers - 1):
            layers.append(nn.Linear(hidden_dim, hidden_dim))
            layers.append(nn.BatchNorm1d(hidden_dim))
            layers.append(self.activation)
            layers.append(nn.Dropout(dropout))

        # 輸出層
        layers.append(nn.Linear(hidden_dim, 1))

        # 組合成 Sequential
        self.mlp = nn.Sequential(*layers)

    def forward(self, x):
        """Forward pass

        Args:
            x: Input tensor of shape (batch_size, d_feat)
               如果輸入是 3D (batch_size, seq_len, d_feat)，取最後一個時間步

        Returns:
            predictions: Output tensor of shape (batch_size, 1)
        """
        # 處理時序輸入：取最後一個時間步
        if x.dim() == 3:
            # x shape: (batch_size, seq_len, d_feat)
            x = x[:, -1, :]  # 取最後一個時間步

        # x shape: (batch_size, d_feat)
        predictions = self.mlp(x)

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
    best_loss = float('inf')

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
            # X shape: (batch_size, d_feat) 或 (batch_size, seq_len, d_feat)
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

        # 保存最佳模型
        if avg_loss < best_loss:
            best_loss = avg_loss

        if (epoch + 1) % 10 == 0:
            print(f'Epoch [{{epoch+1}}/{{num_epochs}}], Loss: {{avg_loss:.4f}}, Best: {{best_loss:.4f}}')

    return model, losses


# 使用示例
if __name__ == '__main__':
    # 初始化模型
    model = {model_name}(
        d_feat=20,
        hidden_dim={hidden_dim},
        num_layers={num_layers},
        dropout={dropout},
        activation='{activation}'
    )

    # 設置優化器
    optimizer = torch.optim.Adam(model.parameters(), lr={learning_rate}, weight_decay=1e-5)
    criterion = nn.MSELoss()
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    print(f'Model: {{model}}')
    print(f'Total parameters: {{sum(p.numel() for p in model.parameters())}}')
    print(f'Device: {{device}}')

    # 測試前向傳播
    sample_input = torch.randn(32, 20).to(device)  # (batch_size, d_feat)
    output = model(sample_input)
    print(f'Input shape: {{sample_input.shape}}')
    print(f'Output shape: {{output.shape}}')
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
                    "dropout": dropout,
                    "activation": activation
                }
            },
            "trainer": {
                "max_epochs": num_epochs,
                "batch_size": batch_size,
                "optimizer": {
                    "class": "Adam",
                    "lr": learning_rate,
                    "weight_decay": 1e-5
                },
                "loss": "mse",
                "GPU": 0,
                "early_stop": {
                    "enable": True,
                    "patience": 15,
                    "min_delta": 1e-6
                }
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

        logger.info(f"Generated MLP model code for {model_name}")

        return code, qlib_config
