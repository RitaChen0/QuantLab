"""模型訓練 Celery 任務"""

import sys
import os
import torch
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from celery import shared_task
from sqlalchemy.orm import Session

# Qlib imports
import qlib
from qlib.data import D
from qlib.contrib.model.pytorch_transformer import Transformer
from qlib.contrib.model.pytorch_nn import DNNModelPytorch

from app.db.session import SessionLocal
from app.repositories.model_training_job import ModelTrainingJobRepository
from app.repositories.model_factor import ModelFactorRepository
from app.repositories.generated_model import GeneratedModelRepository
from app.repositories.generated_factor import GeneratedFactorRepository
from app.utils.timezone_helpers import now_utc
from app.core.config import settings


# 初始化 Qlib（只初始化一次）
if not hasattr(qlib, '_initialized'):
    qlib.init(provider_uri="/data/qlib/tw_stock_v2", region="cn")
    qlib._initialized = True


@shared_task(bind=True, name="app.tasks.model_training_tasks.train_model_async")
def train_model_async(
    self,
    job_id: int,
    model_id: int,
    user_id: int,
    factor_ids: List[int],
    dataset_config: Dict[str, Any],
    training_params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    異步訓練模型任務

    Args:
        self: Celery task instance
        job_id: 訓練任務 ID
        model_id: 模型 ID
        user_id: 用戶 ID
        factor_ids: 因子 ID 列表
        dataset_config: 數據集配置
        training_params: 訓練參數

    Returns:
        訓練結果字典
    """
    db = SessionLocal()

    try:
        # ========== 步驟 1：初始化任務 ==========
        ModelTrainingJobRepository.update_status(
            db, job_id, "RUNNING"
        )
        ModelTrainingJobRepository.update_progress(
            db, job_id,
            progress=0.0,
            current_epoch=0,
            current_step="正在初始化訓練環境..."
        )
        ModelTrainingJobRepository.append_log(
            db, job_id,
            f"開始訓練任務 (Job ID: {job_id}, Model ID: {model_id})"
        )

        # ========== 步驟 2：載入因子資訊 ==========
        ModelTrainingJobRepository.update_progress(
            db, job_id,
            progress=0.1,
            current_epoch=0,
            current_step="正在載入因子資訊..."
        )

        factors = GeneratedFactorRepository.get_by_ids(db, factor_ids)
        if len(factors) != len(factor_ids):
            raise ValueError(f"部分因子不存在。請求 {len(factor_ids)} 個，找到 {len(factors)} 個")

        # 提取 Qlib 表達式
        factor_formulas = [f.formula for f in factors]
        ModelTrainingJobRepository.append_log(
            db, job_id,
            f"載入 {len(factor_formulas)} 個因子：{', '.join([f.name for f in factors])}"
        )

        # ========== 步驟 3：準備數據集 ==========
        ModelTrainingJobRepository.update_progress(
            db, job_id,
            progress=0.2,
            current_epoch=0,
            current_step="正在準備數據集..."
        )

        instruments_config = dataset_config['instruments']
        start_time = dataset_config['start_time']
        end_time = dataset_config['end_time']

        ModelTrainingJobRepository.append_log(
            db, job_id,
            f"數據集配置：股票池={instruments_config}, 時間範圍={start_time} ~ {end_time}"
        )

        # Convert instruments string to list of stock IDs
        if isinstance(instruments_config, str):
            from app.models.stock import Stock

            if instruments_config.lower() in ['all', '全部', '所有']:
                # Get all active stocks
                stocks = db.query(Stock).filter(Stock.is_active == 'active').all()
            else:
                # For specific pools like "台股50", we'll use first 50 active stocks
                # TODO: Implement proper stock pool mapping (e.g., Taiwan 50 index)
                stocks = db.query(Stock).filter(Stock.is_active == 'active').limit(50).all()

            instruments = [stock.stock_id for stock in stocks]
            ModelTrainingJobRepository.append_log(
                db, job_id,
                f"已選擇 {len(instruments)} 支股票進行訓練"
            )
        elif isinstance(instruments_config, list):
            instruments = instruments_config
        else:
            raise ValueError(f"不支援的 instruments 格式: {type(instruments_config)}")

        # 載入數據
        label_formula = "Ref($close, -1) / $close - 1"  # 下一天收益率
        all_fields = factor_formulas + [label_formula]

        df = D.features(
            instruments=instruments,
            fields=all_fields,
            start_time=start_time,
            end_time=end_time,
            freq='day'
        )

        if df is None or df.empty:
            raise ValueError(f"無法載入數據。請檢查 Qlib 數據是否存在於 {start_time} ~ {end_time}")

        ModelTrainingJobRepository.append_log(
            db, job_id,
            f"成功載入 {len(df)} 筆數據（{len(df.index.get_level_values(0).unique())} 支股票）"
        )

        # ========== 步驟 4：數據預處理 ==========
        ModelTrainingJobRepository.update_progress(
            db, job_id,
            progress=0.3,
            current_epoch=0,
            current_step="正在預處理數據..."
        )

        # 填補缺失值
        df = df.fillna(method='ffill').fillna(0)

        # 分割特徵和標籤
        X = df.iloc[:, :-1].values  # 前 N 列為特徵
        y = df.iloc[:, -1].values   # 最後一列為標籤

        # Clean infinite values BEFORE computing statistics
        inf_count = np.isinf(X).sum()
        nan_count = np.isnan(X).sum()

        if inf_count > 0 or nan_count > 0:
            ModelTrainingJobRepository.append_log(
                db, job_id,
                f"⚠️ 清理異常值: {inf_count} 個 Inf, {nan_count} 個 NaN"
            )

            # Use percentile-based clipping for more robust outlier handling
            # Compute 99th percentile of non-infinite values
            valid_X = X[~np.isinf(X)]
            if len(valid_X) > 0:
                p99 = np.percentile(valid_X, 99)
                p1 = np.percentile(valid_X, 1)

                ModelTrainingJobRepository.append_log(
                    db, job_id,
                    f"使用百分位數裁剪: P1={p1:.2f}, P99={p99:.2f}"
                )

                # Clip to percentile range
                X = np.clip(X, p1, p99)
            else:
                # Fallback: use median
                X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

            # Clean labels
            y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)

        # Log data statistics before normalization
        ModelTrainingJobRepository.append_log(
            db, job_id,
            f"清理後數據範圍: X mean={np.mean(X):.6f}, std={np.std(X):.6f}, "
            f"min={np.min(X):.6f}, max={np.max(X):.6f}"
        )

        # 分割訓練/驗證/測試集
        train_ratio = dataset_config.get('train_ratio', 0.7)
        valid_ratio = dataset_config.get('valid_ratio', 0.15)

        n_samples = len(X)
        train_end = int(n_samples * train_ratio)
        valid_end = int(n_samples * (train_ratio + valid_ratio))

        X_train, y_train = X[:train_end], y[:train_end]
        X_valid, y_valid = X[train_end:valid_end], y[train_end:valid_end]
        X_test, y_test = X[valid_end:], y[valid_end:]

        # Standardize features (fit on training set only)
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_valid = scaler.transform(X_valid)
        X_test = scaler.transform(X_test)

        # Check for NaN or Inf after scaling
        if np.any(np.isnan(X_train)) or np.any(np.isinf(X_train)):
            ModelTrainingJobRepository.append_log(
                db, job_id,
                "⚠️ 標準化後發現 NaN/Inf，使用穩健標準化"
            )
            # Use robust scaling if standard scaling fails
            from sklearn.preprocessing import RobustScaler
            scaler = RobustScaler()
            X_train = scaler.fit_transform(X[:train_end])
            X_valid = scaler.transform(X[train_end:valid_end])
            X_test = scaler.transform(X[valid_end:])
            # Replace any remaining NaN with 0
            X_train = np.nan_to_num(X_train, nan=0.0, posinf=0.0, neginf=0.0)
            X_valid = np.nan_to_num(X_valid, nan=0.0, posinf=0.0, neginf=0.0)
            X_test = np.nan_to_num(X_test, nan=0.0, posinf=0.0, neginf=0.0)

        ModelTrainingJobRepository.append_log(
            db, job_id,
            f"訓練集: {len(X_train)} 筆, 驗證集: {len(X_valid)} 筆, 測試集: {len(X_test)} 筆"
        )

        ModelTrainingJobRepository.append_log(
            db, job_id,
            f"標準化後: X_train mean={np.mean(X_train):.6f}, std={np.std(X_train):.6f}"
        )

        # ========== 步驟 5：建立模型 ==========
        ModelTrainingJobRepository.update_progress(
            db, job_id,
            progress=0.4,
            current_epoch=0,
            current_step="正在建立模型..."
        )

        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        ModelTrainingJobRepository.append_log(
            db, job_id,
            f"使用設備: {device}"
        )

        # 獲取模型資訊
        model_info = GeneratedModelRepository.get_by_id(db, model_id)
        if not model_info:
            raise ValueError(f"模型 ID {model_id} 不存在")

        # 根據模型類型建立模型（簡化版本，使用 PyTorch MLP）
        d_feat = len(factor_formulas)

        # Create simple PyTorch MLP model
        class SimpleMLP(torch.nn.Module):
            def __init__(self, input_dim, hidden_dims=(128, 64), dropout=0.1):
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

                layers.append(torch.nn.Linear(prev_dim, 1))  # Output layer
                self.model = torch.nn.Sequential(*layers)

            def forward(self, x):
                return self.model(x)

        model = SimpleMLP(input_dim=d_feat).to(device)

        ModelTrainingJobRepository.append_log(
            db, job_id,
            f"模型架構: MLP (輸入維度={d_feat}, 隱藏層=[128, 64])"
        )

        # ========== 步驟 6：訓練模型 ==========
        num_epochs = training_params.get('num_epochs', 100)
        batch_size = training_params.get('batch_size', 800)
        learning_rate = training_params.get('learning_rate', 0.001)
        early_stop_rounds = training_params.get('early_stop_rounds', 20)

        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        criterion = torch.nn.MSELoss()

        # 轉換為 Tensor
        X_train_tensor = torch.FloatTensor(X_train).to(device)
        y_train_tensor = torch.FloatTensor(y_train).unsqueeze(1).to(device)
        X_valid_tensor = torch.FloatTensor(X_valid).to(device)
        y_valid_tensor = torch.FloatTensor(y_valid).unsqueeze(1).to(device)

        best_valid_loss = float('inf')
        patience_counter = 0

        # Initialize model weight path
        model_weight_dir = "/app/models/trained"
        os.makedirs(model_weight_dir, exist_ok=True)
        model_weight_path = os.path.join(
            model_weight_dir,
            f"model_{model_id}_job_{job_id}_best.pth"
        )

        # Check training data quality before starting
        ModelTrainingJobRepository.append_log(
            db, job_id,
            f"訓練數據檢查: X shape={X_train.shape}, y shape={y_train.shape}, "
            f"X NaN={np.isnan(X_train).sum()}, y NaN={np.isnan(y_train).sum()}"
        )

        ModelTrainingJobRepository.append_log(
            db, job_id,
            f"開始訓練：{num_epochs} 輪, 批次大小={batch_size}, 學習率={learning_rate}"
        )

        for epoch in range(1, num_epochs + 1):
            # 訓練模式
            model.train()
            train_losses = []

            # Mini-batch 訓練
            for i in range(0, len(X_train_tensor), batch_size):
                batch_X = X_train_tensor[i:i+batch_size]
                batch_y = y_train_tensor[i:i+batch_size]

                optimizer.zero_grad()
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)

                # Check for NaN loss
                if torch.isnan(loss):
                    ModelTrainingJobRepository.append_log(
                        db, job_id,
                        f"⚠️ Epoch {epoch} Batch {i//batch_size}: Loss is NaN! "
                        f"Output stats: mean={outputs.mean():.6f}, std={outputs.std():.6f}"
                    )
                    # Skip this batch if loss is NaN
                    continue

                loss.backward()

                # Gradient clipping to prevent exploding gradients
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

                optimizer.step()

                train_losses.append(loss.item())

            if len(train_losses) == 0:
                ModelTrainingJobRepository.append_log(
                    db, job_id,
                    f"⚠️ Epoch {epoch}: 所有 batch 的 loss 都是 NaN，訓練失敗"
                )
                train_loss = float('nan')
            else:
                train_loss = np.mean(train_losses)

            # 驗證模式
            model.eval()
            with torch.no_grad():
                valid_outputs = model(X_valid_tensor)
                valid_loss = criterion(valid_outputs, y_valid_tensor).item()

            # 更新進度（每輪）
            progress = 0.4 + 0.5 * (epoch / num_epochs)  # 0.4 到 0.9

            ModelTrainingJobRepository.update_progress(
                db, job_id,
                progress=progress,
                current_epoch=epoch,
                current_step=f"訓練中 Epoch {epoch}/{num_epochs}",
                train_loss=train_loss if not np.isnan(train_loss) else None,
                valid_loss=valid_loss if not np.isnan(valid_loss) else None
            )

            # Log first, last epoch, or every 10 epochs
            if epoch == 1 or epoch == num_epochs or epoch % 10 == 0:
                ModelTrainingJobRepository.append_log(
                    db, job_id,
                    f"Epoch {epoch}/{num_epochs}: train_loss={train_loss:.6f}, valid_loss={valid_loss:.6f}"
                )

            # Early Stopping
            if valid_loss < best_valid_loss:
                best_valid_loss = valid_loss
                patience_counter = 0

                # 保存最佳模型
                torch.save(model.state_dict(), model_weight_path)
            else:
                patience_counter += 1
                if patience_counter >= early_stop_rounds:
                    ModelTrainingJobRepository.append_log(
                        db, job_id,
                        f"Early stopping triggered at epoch {epoch} (最佳驗證損失: {best_valid_loss:.6f})"
                    )
                    break

        # Save final model if it wasn't saved during training (safety fallback)
        if not os.path.exists(model_weight_path):
            torch.save(model.state_dict(), model_weight_path)
            ModelTrainingJobRepository.append_log(
                db, job_id,
                "保存最終模型權重（未找到最佳模型）"
            )

        # ========== 步驟 7：測試模型 ==========
        ModelTrainingJobRepository.update_progress(
            db, job_id,
            progress=0.95,
            current_epoch=epoch,
            current_step="正在測試模型..."
        )

        # 載入最佳模型
        model.load_state_dict(torch.load(model_weight_path))
        model.eval()

        X_test_tensor = torch.FloatTensor(X_test).to(device)
        y_test_tensor = torch.FloatTensor(y_test).unsqueeze(1).to(device)

        with torch.no_grad():
            test_outputs = model(X_test_tensor)
            test_predictions = test_outputs.cpu().numpy().flatten()
            test_actuals = y_test

            # Debug logging
            ModelTrainingJobRepository.append_log(
                db, job_id,
                f"預測值統計: mean={np.mean(test_predictions):.6f}, std={np.std(test_predictions):.6f}, "
                f"min={np.min(test_predictions):.6f}, max={np.max(test_predictions):.6f}, "
                f"NaN count={np.isnan(test_predictions).sum()}"
            )

            # Check for NaN or Inf in predictions
            if np.any(np.isnan(test_predictions)) or np.any(np.isinf(test_predictions)):
                ModelTrainingJobRepository.append_log(
                    db, job_id,
                    "⚠️ 警告: 預測值包含 NaN 或 Inf，將替換為 0"
                )
                test_predictions = np.nan_to_num(test_predictions, nan=0.0, posinf=0.0, neginf=0.0)

            # Calculate IC (Information Coefficient)
            # Handle case where std is 0 or correlation can't be computed
            if np.std(test_predictions) < 1e-10 or np.std(test_actuals) < 1e-10:
                test_ic = 0.0
                ModelTrainingJobRepository.append_log(
                    db, job_id,
                    "⚠️ 預測值或實際值標準差接近 0，IC 設為 0"
                )
            else:
                try:
                    correlation_matrix = np.corrcoef(test_predictions, test_actuals)
                    test_ic = correlation_matrix[0, 1]
                    if np.isnan(test_ic):
                        test_ic = 0.0
                except:
                    test_ic = 0.0

            # Calculate other metrics
            mse = np.mean((test_predictions - test_actuals) ** 2)
            mae = np.mean(np.abs(test_predictions - test_actuals))
            pred_mean = np.mean(test_predictions)
            pred_std = np.std(test_predictions)

            # Convert NaN to None for JSON compatibility
            def safe_float(value):
                if np.isnan(value) or np.isinf(value):
                    return None
                return float(value)

            test_metrics = {
                'ic': safe_float(test_ic),
                'mse': safe_float(mse),
                'mae': safe_float(mae),
                'predictions_mean': safe_float(pred_mean),
                'predictions_std': safe_float(pred_std)
            }

            # Also convert test_ic for database save
            test_ic_safe = safe_float(test_ic)

        ModelTrainingJobRepository.append_log(
            db, job_id,
            f"測試結果: IC={test_ic_safe if test_ic_safe is not None else 'N/A'}, "
            f"MSE={test_metrics['mse'] if test_metrics['mse'] is not None else 'N/A'}"
        )

        # ========== 步驟 8：完成訓練 ==========
        ModelTrainingJobRepository.update_completed(
            db, job_id,
            model_weight_path=model_weight_path,
            test_ic=test_ic_safe,
            test_metrics=test_metrics
        )

        ModelTrainingJobRepository.append_log(
            db, job_id,
            "✅ 訓練完成！模型權重已保存。"
        )

        return {
            'status': 'success',
            'job_id': job_id,
            'model_weight_path': model_weight_path,
            'test_ic': test_ic_safe,
            'test_metrics': test_metrics
        }

    except Exception as e:
        # Rollback current transaction to allow new queries
        db.rollback()

        # 記錄錯誤
        error_msg = f"訓練失敗: {str(e)}"
        try:
            ModelTrainingJobRepository.update_status(
                db, job_id,
                status="FAILED",
                error_message=error_msg
            )
            ModelTrainingJobRepository.append_log(
                db, job_id,
                f"❌ {error_msg}"
            )
        except Exception as update_error:
            # If we can't update the database, at least log it
            print(f"Failed to update job status: {update_error}")

        raise e

    finally:
        db.close()


@shared_task(name="app.tasks.model_training_tasks.cancel_training_job")
def cancel_training_job(job_id: int) -> Dict[str, Any]:
    """
    取消訓練任務

    Args:
        job_id: 訓練任務 ID

    Returns:
        取消結果
    """
    db = SessionLocal()

    try:
        job = ModelTrainingJobRepository.get_by_id(db, job_id)
        if not job:
            return {'status': 'error', 'message': f'任務 {job_id} 不存在'}

        if job.status not in ['PENDING', 'RUNNING']:
            return {
                'status': 'error',
                'message': f'任務狀態為 {job.status}，無法取消'
            }

        # 更新狀態為 CANCELLED
        ModelTrainingJobRepository.update_status(
            db, job_id,
            status="CANCELLED"
        )

        ModelTrainingJobRepository.append_log(
            db, job_id,
            "🚫 訓練任務已被用戶取消"
        )

        return {
            'status': 'success',
            'job_id': job_id,
            'message': '訓練任務已取消'
        }

    finally:
        db.close()
