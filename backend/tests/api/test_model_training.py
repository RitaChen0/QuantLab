"""
API Integration tests for Model Training endpoints

測試模型訓練 API 端點
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.models.rdagent import (
    RDAgentTask,
    GeneratedModel,
    GeneratedFactor,
    ModelFactor,
    ModelTrainingJob,
    TaskType,
    TaskStatus
)
from app.api.dependencies import get_current_user, get_db


# 測試用戶 fixtures
def get_test_user_level0():
    """返回 Level 0 測試用戶（無權訓練）"""
    user = User(
        id=1,
        username="testuser_level0",
        email="test0@example.com",
        is_active=True,
        is_superuser=False
    )
    user.member_level = 0
    return user


def get_test_user_level3():
    """返回 Level 3 測試用戶（有權訓練）"""
    user = User(
        id=2,
        username="testuser_level3",
        email="test3@example.com",
        is_active=True,
        is_superuser=False
    )
    user.member_level = 3
    return user


@pytest.fixture
def mock_db():
    """模擬資料庫 session"""
    db = MagicMock(spec=Session)
    return db


@pytest.fixture
def client_level0(mock_db):
    """測試客戶端（Level 0 用戶）"""
    app.dependency_overrides[get_current_user] = get_test_user_level0
    app.dependency_overrides[get_db] = lambda: mock_db

    test_client = TestClient(app)

    yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def client_level3(mock_db):
    """測試客戶端（Level 3 用戶）"""
    app.dependency_overrides[get_current_user] = get_test_user_level3
    app.dependency_overrides[get_db] = lambda: mock_db

    test_client = TestClient(app)

    yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_task():
    """模擬 RD-Agent 任務"""
    task = Mock(spec=RDAgentTask)
    task.id = 1
    task.user_id = 2
    task.task_type = TaskType.MODEL_GENERATION
    task.status = TaskStatus.COMPLETED
    return task


@pytest.fixture
def mock_model():
    """模擬生成的模型"""
    model = Mock(spec=GeneratedModel)
    model.id = 10
    model.task_id = 1
    model.user_id = 2
    model.name = "TestModel"
    model.model_type = "TimeSeries"
    model.architecture = "LSTM"
    model.variables = {"features": ["Close", "Volume"]}
    model.hyperparameters = {"layers": 3, "units": 128}
    return model


@pytest.fixture
def mock_factors():
    """模擬生成的因子列表"""
    factors = []
    for i in range(3):
        factor = Mock(spec=GeneratedFactor)
        factor.id = 100 + i
        factor.task_id = 1
        factor.user_id = 2
        factor.name = f"TestFactor{i}"
        factor.category = "Technical"
        factor.formula = f"Close * {i+1}"
        factor.code = f"code_{i}"
        factor.description = f"Test factor {i}"
        factor.ic = 0.05 + i * 0.01
        factor.icir = 0.5 + i * 0.1
        factor.sharpe_ratio = 1.5 + i * 0.2
        factor.annual_return = 0.15 + i * 0.05
        factor.created_at = datetime.now()
        factors.append(factor)
    return factors


@pytest.fixture
def mock_training_job():
    """模擬訓練任務"""
    job = Mock(spec=ModelTrainingJob)
    job.id = 50
    job.model_id = 10
    job.user_id = 2
    job.dataset_config = {
        "instruments": "台股50",
        "start_time": "2020-01-01",
        "end_time": "2024-12-31",
        "train_ratio": 0.7,
        "valid_ratio": 0.15,
        "test_ratio": 0.15
    }
    job.training_params = {
        "num_epochs": 100,
        "batch_size": 800,
        "learning_rate": 0.001,
        "early_stop_rounds": 20,
        "optimizer": "adam",
        "loss_function": "mse"
    }
    job.status = "PENDING"
    job.progress = 0.0
    job.current_epoch = 0
    job.total_epochs = 100
    job.current_step = ""
    job.train_loss = 0.0
    job.valid_loss = 0.0
    job.test_ic = None
    job.test_metrics = None
    job.model_weight_path = None
    job.training_log = ""
    job.error_message = None
    job.celery_task_id = "celery-task-12345"
    job.started_at = None
    job.completed_at = None
    job.created_at = datetime.now()
    return job


class TestSelectFactorsForModel:
    """測試 POST /api/v1/rdagent/models/{model_id}/select-factors"""

    @patch('app.repositories.generated_model.GeneratedModelRepository')
    @patch('app.repositories.generated_factor.GeneratedFactorRepository')
    @patch('app.repositories.model_factor.ModelFactorRepository')
    @patch('app.utils.logging.api_log')
    def test_select_factors_success(
        self,
        mock_api_log,
        MockModelFactorRepo,
        MockFactorRepo,
        MockModelRepo,
        client_level3,
        mock_model,
        mock_factors
    ):
        """測試成功選擇因子"""
        # 模擬 Repository 回應
        MockModelRepo.get_by_id.return_value = mock_model
        MockFactorRepo.get_by_ids.return_value = mock_factors

        # 模擬批次創建返回
        mock_model_factors = []
        for idx, factor in enumerate(mock_factors):
            mf = Mock()
            mf.id = idx + 1
            mf.model_id = mock_model.id
            mf.factor_id = factor.id
            mf.feature_index = idx
            mf.created_at = datetime.now()
            mock_model_factors.append(mf)

        MockModelFactorRepo.batch_create.return_value = mock_model_factors

        # 發送請求
        response = client_level3.post(
            f"/api/v1/rdagent/models/{mock_model.id}/select-factors",
            json={"factor_ids": [100, 101, 102]}
        )

        # 驗證響應
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["model_id"] == mock_model.id
        assert data[0]["factor_id"] == 100
        assert data[0]["feature_index"] == 0

        # 驗證調用
        MockModelRepo.get_by_id.assert_called_once()
        MockFactorRepo.get_by_ids.assert_called_once()
        MockModelFactorRepo.batch_create.assert_called_once()

    @patch('app.repositories.generated_model.GeneratedModelRepository')
    def test_select_factors_model_not_found(
        self,
        MockModelRepo,
        client_level3
    ):
        """測試模型不存在"""
        MockModelRepo.get_by_id.return_value = None

        response = client_level3.post(
            "/api/v1/rdagent/models/999/select-factors",
            json={"factor_ids": [100, 101]}
        )

        assert response.status_code == 404
        assert "模型不存在" in response.json()["detail"]

    @patch('app.repositories.generated_model.GeneratedModelRepository')
    def test_select_factors_wrong_user(
        self,
        MockModelRepo,
        client_level3,
        mock_model
    ):
        """測試模型不屬於當前用戶"""
        # 修改模型所有者
        mock_model.user_id = 999

        MockModelRepo.get_by_id.return_value = mock_model

        response = client_level3.post(
            f"/api/v1/rdagent/models/{mock_model.id}/select-factors",
            json={"factor_ids": [100, 101]}
        )

        assert response.status_code == 404
        assert "無權訪問" in response.json()["detail"]

    @patch('app.repositories.generated_model.GeneratedModelRepository')
    @patch('app.repositories.generated_factor.GeneratedFactorRepository')
    def test_select_factors_some_factors_not_found(
        self,
        MockFactorRepo,
        MockModelRepo,
        client_level3,
        mock_model,
        mock_factors
    ):
        """測試部分因子不存在"""
        MockModelRepo.get_by_id.return_value = mock_model
        # 只返回 2 個因子，但請求了 3 個
        MockFactorRepo.get_by_ids.return_value = mock_factors[:2]

        response = client_level3.post(
            f"/api/v1/rdagent/models/{mock_model.id}/select-factors",
            json={"factor_ids": [100, 101, 102]}
        )

        assert response.status_code == 400
        assert "部分因子不存在" in response.json()["detail"]

    @patch('app.repositories.generated_model.GeneratedModelRepository')
    @patch('app.repositories.generated_factor.GeneratedFactorRepository')
    def test_select_factors_factor_wrong_user(
        self,
        MockFactorRepo,
        MockModelRepo,
        client_level3,
        mock_model,
        mock_factors
    ):
        """測試因子不屬於當前用戶"""
        MockModelRepo.get_by_id.return_value = mock_model

        # 修改一個因子的所有者
        mock_factors[1].user_id = 999

        MockFactorRepo.get_by_ids.return_value = mock_factors

        response = client_level3.post(
            f"/api/v1/rdagent/models/{mock_model.id}/select-factors",
            json={"factor_ids": [100, 101, 102]}
        )

        assert response.status_code == 403
        assert "不屬於當前用戶" in response.json()["detail"]


class TestTrainModel:
    """測試 POST /api/v1/rdagent/models/{model_id}/train"""

    @patch('app.api.v1.rdagent.train_model_async')
    @patch('app.repositories.generated_model.GeneratedModelRepository')
    @patch('app.repositories.model_training_job.ModelTrainingJobRepository')
    @patch('app.repositories.model_factor.ModelFactorRepository')
    @patch('app.utils.logging.api_log')
    def test_train_model_success(
        self,
        mock_api_log,
        MockModelFactorRepo,
        MockTrainingRepo,
        MockModelRepo,
        mock_train_async,
        client_level3,
        mock_model,
        mock_training_job
    ):
        """測試成功啟動訓練"""
        # 模擬 Repository 回應
        MockModelRepo.get_by_id.return_value = mock_model
        MockTrainingRepo.create.return_value = mock_training_job

        # 模擬 Celery 異步任務
        mock_celery_result = Mock()
        mock_celery_result.id = "celery-task-12345"
        mock_train_async.apply_async.return_value = mock_celery_result

        # 準備請求數據
        request_data = {
            "factor_ids": [100, 101, 102],
            "dataset_config": {
                "instruments": "台股50",
                "start_time": "2020-01-01",
                "end_time": "2024-12-31",
                "train_ratio": 0.7,
                "valid_ratio": 0.15,
                "test_ratio": 0.15
            },
            "training_params": {
                "num_epochs": 100,
                "batch_size": 64,
                "learning_rate": 0.001
            }
        }

        # 發送請求
        response = client_level3.post(
            f"/api/v1/rdagent/models/{mock_model.id}/train",
            json=request_data
        )

        # 驗證響應
        assert response.status_code == 202
        data = response.json()
        assert data["id"] == mock_training_job.id
        assert data["model_id"] == mock_model.id
        assert data["status"] == "PENDING"
        # celery_task_id 是動態生成的 UUID，不需要檢查具體值
        assert "celery_task_id" in data

        # 驗證調用
        MockModelRepo.get_by_id.assert_called_once()
        # 驗證 batch_create 被調用，但不檢查具體 db 實例
        assert MockModelFactorRepo.batch_create.called
        call_args = MockModelFactorRepo.batch_create.call_args
        assert call_args[0][1] == mock_model.id  # model_id
        assert call_args[0][2] == [100, 101, 102]  # factor_ids
        MockTrainingRepo.create.assert_called_once()
        mock_train_async.apply_async.assert_called_once()

    @patch('app.repositories.generated_model.GeneratedModelRepository')
    def test_train_model_not_found(
        self,
        MockModelRepo,
        client_level3
    ):
        """測試模型不存在"""
        MockModelRepo.get_by_id.return_value = None

        request_data = {
            "factor_ids": [100, 101],
            "dataset_config": {
                "instruments": "台股50",
                "start_time": "2020-01-01",
                "end_time": "2024-12-31",
                "train_ratio": 0.7,
                "valid_ratio": 0.15,
                "test_ratio": 0.15
            },
            "training_params": {
                "num_epochs": 100,
                "batch_size": 64,
                "learning_rate": 0.001
            }
        }

        response = client_level3.post(
            "/api/v1/rdagent/models/999/train",
            json=request_data
        )

        assert response.status_code == 404
        assert "模型不存在" in response.json()["detail"]

    @patch('app.repositories.generated_model.GeneratedModelRepository')
    def test_train_model_insufficient_level(
        self,
        MockModelRepo,
        client_level0,
        mock_model
    ):
        """測試用戶等級不足"""
        # 創建屬於 Level 0 用戶的模型
        model_level0 = Mock(spec=GeneratedModel)
        model_level0.id = mock_model.id
        model_level0.user_id = 1  # client_level0 的用戶 ID
        model_level0.name = mock_model.name
        model_level0.model_type = mock_model.model_type

        MockModelRepo.get_by_id.return_value = model_level0

        request_data = {
            "factor_ids": [100, 101],
            "dataset_config": {
                "instruments": "台股50",
                "start_time": "2020-01-01",
                "end_time": "2024-12-31",
                "train_ratio": 0.7,
                "valid_ratio": 0.15,
                "test_ratio": 0.15
            },
            "training_params": {
                "num_epochs": 100,
                "batch_size": 64,
                "learning_rate": 0.001
            }
        }

        response = client_level0.post(
            f"/api/v1/rdagent/models/{mock_model.id}/train",
            json=request_data
        )

        assert response.status_code == 403
        assert "Level 3" in response.json()["detail"]

    @patch('app.api.v1.rdagent.train_model_async')
    @patch('app.repositories.generated_model.GeneratedModelRepository')
    @patch('app.repositories.model_training_job.ModelTrainingJobRepository')
    @patch('app.utils.logging.api_log')
    def test_train_model_without_factor_ids(
        self,
        mock_api_log,
        MockTrainingRepo,
        MockModelRepo,
        mock_train_async,
        client_level3,
        mock_model,
        mock_training_job
    ):
        """測試不指定因子（使用現有綁定）"""
        MockModelRepo.get_by_id.return_value = mock_model
        MockTrainingRepo.create.return_value = mock_training_job

        mock_celery_result = Mock()
        mock_celery_result.id = "celery-task-67890"
        mock_train_async.apply_async.return_value = mock_celery_result

        request_data = {
            "dataset_config": {
                "instruments": "台股50",
                "start_time": "2020-01-01",
                "end_time": "2024-12-31",
                "train_ratio": 0.7,
                "valid_ratio": 0.15,
                "test_ratio": 0.15
            },
            "training_params": {
                "num_epochs": 50,
                "batch_size": 32,
                "learning_rate": 0.0001,
                "early_stop_rounds": 10,
                "optimizer": "adam",
                "loss_function": "mse"
            }
        }

        response = client_level3.post(
            f"/api/v1/rdagent/models/{mock_model.id}/train",
            json=request_data
        )

        # 預期 422 因為 schema 要求 factor_ids 必填
        # 注意：這可能是一個設計問題，未來可能需要修改 schema 使 factor_ids 可選
        assert response.status_code == 422
        assert "factor_ids" in response.json()["detail"][0]["loc"]


class TestGetTrainingJob:
    """測試 GET /api/v1/rdagent/training-jobs/{job_id}"""

    @patch('app.repositories.model_training_job.ModelTrainingJobRepository')
    def test_get_training_job_success(
        self,
        MockTrainingRepo,
        client_level3,
        mock_training_job
    ):
        """測試成功獲取訓練任務"""
        MockTrainingRepo.get_by_id.return_value = mock_training_job

        response = client_level3.get(
            f"/api/v1/rdagent/training-jobs/{mock_training_job.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == mock_training_job.id
        assert data["model_id"] == mock_training_job.model_id
        assert data["status"] == "PENDING"

    @patch('app.repositories.model_training_job.ModelTrainingJobRepository')
    def test_get_training_job_not_found(
        self,
        MockTrainingRepo,
        client_level3
    ):
        """測試訓練任務不存在"""
        MockTrainingRepo.get_by_id.return_value = None

        response = client_level3.get("/api/v1/rdagent/training-jobs/999")

        assert response.status_code == 404

    @patch('app.repositories.model_training_job.ModelTrainingJobRepository')
    def test_get_training_job_wrong_user(
        self,
        MockTrainingRepo,
        client_level3,
        mock_training_job
    ):
        """測試訓練任務不屬於當前用戶"""
        mock_training_job.user_id = 999

        MockTrainingRepo.get_by_id.return_value = mock_training_job

        response = client_level3.get(
            f"/api/v1/rdagent/training-jobs/{mock_training_job.id}"
        )

        assert response.status_code == 403
        assert "無權訪問" in response.json()["detail"]


class TestGetModelTrainingJobs:
    """測試 GET /api/v1/rdagent/models/{model_id}/training-jobs"""

    @patch('app.repositories.generated_model.GeneratedModelRepository')
    @patch('app.repositories.model_training_job.ModelTrainingJobRepository')
    def test_get_model_training_jobs_success(
        self,
        MockTrainingRepo,
        MockModelRepo,
        client_level3,
        mock_model,
        mock_training_job
    ):
        """測試成功獲取模型的訓練任務列表"""
        MockModelRepo.get_by_id.return_value = mock_model

        # 創建多個訓練任務，每個都需要完整的字段
        jobs = [mock_training_job]
        for i in range(2):
            job = Mock(spec=ModelTrainingJob)
            job.id = 51 + i
            job.model_id = mock_model.id
            job.user_id = 2
            job.dataset_config = mock_training_job.dataset_config
            job.training_params = mock_training_job.training_params
            job.status = "COMPLETED" if i == 0 else "FAILED"
            job.progress = 1.0 if i == 0 else 0.5
            job.current_epoch = 100 if i == 0 else 50
            job.total_epochs = 100
            job.current_step = "Training completed" if i == 0 else "Training failed"
            job.train_loss = 0.001 if i == 0 else 0.5
            job.valid_loss = 0.002 if i == 0 else 0.6
            job.test_ic = 0.05 if i == 0 else None
            job.test_metrics = {"accuracy": 0.85} if i == 0 else None
            job.model_weight_path = "/path/to/model.pth" if i == 0 else None
            job.training_log = "Training completed successfully" if i == 0 else "Error occurred"
            job.error_message = None if i == 0 else "Training failed"
            job.celery_task_id = f"celery-task-{51 + i}"
            job.started_at = datetime.now()
            job.completed_at = datetime.now() if i == 0 else None
            job.created_at = datetime.now()
            jobs.append(job)

        MockTrainingRepo.get_by_model.return_value = jobs

        response = client_level3.get(
            f"/api/v1/rdagent/models/{mock_model.id}/training-jobs"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["jobs"]) == 3

    @patch('app.repositories.generated_model.GeneratedModelRepository')
    def test_get_model_training_jobs_model_not_found(
        self,
        MockModelRepo,
        client_level3
    ):
        """測試模型不存在"""
        MockModelRepo.get_by_id.return_value = None

        response = client_level3.get("/api/v1/rdagent/models/999/training-jobs")

        assert response.status_code == 404


class TestCancelTrainingJob:
    """測試 POST /api/v1/rdagent/training-jobs/{job_id}/cancel"""

    @patch('app.api.v1.rdagent.cancel_training_job')
    @patch('app.core.celery_app.celery_app')
    @patch('app.repositories.model_training_job.ModelTrainingJobRepository')
    def test_cancel_training_job_success(
        self,
        MockTrainingRepo,
        mock_celery,
        mock_cancel_task,
        client_level3,
        mock_training_job
    ):
        """測試成功取消訓練任務"""
        # 設置訓練任務為 RUNNING 狀態
        mock_training_job.status = "RUNNING"

        MockTrainingRepo.get_by_id.return_value = mock_training_job

        response = client_level3.post(
            f"/api/v1/rdagent/training-jobs/{mock_training_job.id}/cancel"
        )

        assert response.status_code == 200
        data = response.json()
        # 狀態仍為 RUNNING，因為實際取消會由 Celery 任務異步處理
        assert data["id"] == mock_training_job.id

        # 驗證調用 Celery 取消任務
        mock_cancel_task.apply_async.assert_called_once()

        # 驗證調用 Celery revoke
        mock_celery.control.revoke.assert_called_once_with(
            mock_training_job.celery_task_id,
            terminate=True
        )

    @patch('app.repositories.model_training_job.ModelTrainingJobRepository')
    def test_cancel_training_job_not_found(
        self,
        MockTrainingRepo,
        client_level3
    ):
        """測試訓練任務不存在"""
        MockTrainingRepo.get_by_id.return_value = None

        response = client_level3.post("/api/v1/rdagent/training-jobs/999/cancel")

        assert response.status_code == 404

    @patch('app.repositories.model_training_job.ModelTrainingJobRepository')
    def test_cancel_training_job_already_completed(
        self,
        MockTrainingRepo,
        client_level3,
        mock_training_job
    ):
        """測試取消已完成的訓練任務"""
        mock_training_job.status = "COMPLETED"

        MockTrainingRepo.get_by_id.return_value = mock_training_job

        response = client_level3.post(
            f"/api/v1/rdagent/training-jobs/{mock_training_job.id}/cancel"
        )

        assert response.status_code == 400
        assert "已完成" in response.json()["detail"] or "無法取消" in response.json()["detail"]


class TestAPIAuthentication:
    """測試 API 認證"""

    def test_select_factors_unauthorized(self):
        """測試未授權訪問選擇因子"""
        client_no_auth = TestClient(app)
        response = client_no_auth.post(
            "/api/v1/rdagent/models/10/select-factors",
            json={"factor_ids": [100, 101]}
        )
        assert response.status_code == 403

    def test_train_model_unauthorized(self):
        """測試未授權訪問訓練模型"""
        client_no_auth = TestClient(app)
        response = client_no_auth.post(
            "/api/v1/rdagent/models/10/train",
            json={
                "factor_ids": [100],
                "dataset_config": {
                    "instruments": "台股50",
                    "start_time": "2020-01-01",
                    "end_time": "2024-12-31",
                    "train_ratio": 0.7,
                    "valid_ratio": 0.15,
                    "test_ratio": 0.15
                },
                "training_params": {
                    "num_epochs": 100,
                    "batch_size": 64,
                    "learning_rate": 0.001
                }
            }
        )
        assert response.status_code == 403
