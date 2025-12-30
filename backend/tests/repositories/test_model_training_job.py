"""
Unit tests for ModelTrainingJobRepository
"""
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.repositories.model_training_job import ModelTrainingJobRepository
from app.models.rdagent import (
    RDAgentTask,
    GeneratedModel,
    ModelTrainingJob,
    TaskType,
    TaskStatus
)
from app.models.user import User


@pytest.fixture
def test_user(db_session: Session):
    """創建測試用戶"""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashedpassword123",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_task(db_session: Session, test_user: User):
    """創建測試任務"""
    task = RDAgentTask(
        user_id=test_user.id,
        task_type=TaskType.MODEL_GENERATION,
        status=TaskStatus.COMPLETED
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


@pytest.fixture
def test_model(db_session: Session, test_task: RDAgentTask, test_user: User):
    """創建測試模型"""
    model = GeneratedModel(
        task_id=test_task.id,
        user_id=test_user.id,
        name="TestModel",
        model_type="TimeSeries"
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


@pytest.fixture
def dataset_config():
    """測試數據集配置"""
    return {
        "stock_pool": ["2330", "2317", "2454"],
        "start_date": "2020-01-01",
        "end_date": "2024-12-31",
        "train_ratio": 0.7,
        "valid_ratio": 0.15,
        "test_ratio": 0.15
    }


@pytest.fixture
def training_params():
    """測試訓練參數"""
    return {
        "num_epochs": 100,
        "batch_size": 64,
        "learning_rate": 0.001,
        "optimizer": "Adam"
    }


class TestModelTrainingJobRepositoryCreate:
    """測試 create 方法"""

    def test_create_basic(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User,
        dataset_config: dict,
        training_params: dict
    ):
        """測試創建基本訓練任務"""
        job = ModelTrainingJobRepository.create(
            db=db_session,
            model_id=test_model.id,
            user_id=test_user.id,
            dataset_config=dataset_config,
            training_params=training_params
        )

        assert job.id is not None
        assert job.model_id == test_model.id
        assert job.user_id == test_user.id
        assert job.dataset_config == dataset_config
        assert job.training_params == training_params
        assert job.status == "PENDING"
        assert job.progress == 0.0
        assert job.current_epoch == 0
        assert job.total_epochs == 100
        assert job.training_log == ""
        assert job.created_at is not None

    def test_create_with_celery_task_id(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User,
        dataset_config: dict,
        training_params: dict
    ):
        """測試創建帶 Celery Task ID 的任務"""
        celery_task_id = "celery-task-12345"

        job = ModelTrainingJobRepository.create(
            db=db_session,
            model_id=test_model.id,
            user_id=test_user.id,
            dataset_config=dataset_config,
            training_params=training_params,
            celery_task_id=celery_task_id
        )

        assert job.celery_task_id == celery_task_id

    def test_create_extracts_total_epochs(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User,
        dataset_config: dict
    ):
        """測試創建時自動提取 total_epochs"""
        training_params = {"num_epochs": 200, "batch_size": 32}

        job = ModelTrainingJobRepository.create(
            db=db_session,
            model_id=test_model.id,
            user_id=test_user.id,
            dataset_config=dataset_config,
            training_params=training_params
        )

        assert job.total_epochs == 200

    def test_create_default_total_epochs(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User,
        dataset_config: dict
    ):
        """測試創建時使用默認 total_epochs"""
        training_params = {"batch_size": 32}  # 未指定 num_epochs

        job = ModelTrainingJobRepository.create(
            db=db_session,
            model_id=test_model.id,
            user_id=test_user.id,
            dataset_config=dataset_config,
            training_params=training_params
        )

        assert job.total_epochs == 100  # 默認值


class TestModelTrainingJobRepositoryGetById:
    """測試 get_by_id 方法"""

    def test_get_existing_job(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User,
        dataset_config: dict,
        training_params: dict
    ):
        """測試獲取存在的任務"""
        created_job = ModelTrainingJobRepository.create(
            db=db_session,
            model_id=test_model.id,
            user_id=test_user.id,
            dataset_config=dataset_config,
            training_params=training_params
        )

        result = ModelTrainingJobRepository.get_by_id(db_session, created_job.id)

        assert result is not None
        assert result.id == created_job.id
        assert result.model_id == test_model.id

    def test_get_nonexistent_job(self, db_session: Session):
        """測試獲取不存在的任務"""
        result = ModelTrainingJobRepository.get_by_id(db_session, 99999)

        assert result is None


class TestModelTrainingJobRepositoryGetByUser:
    """測試 get_by_user 方法"""

    def test_get_user_jobs(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User,
        dataset_config: dict,
        training_params: dict
    ):
        """測試獲取用戶的所有任務"""
        # 創建多個任務
        for i in range(3):
            ModelTrainingJobRepository.create(
                db=db_session,
                model_id=test_model.id,
                user_id=test_user.id,
                dataset_config=dataset_config,
                training_params=training_params
            )

        result = ModelTrainingJobRepository.get_by_user(
            db=db_session,
            user_id=test_user.id,
            limit=50
        )

        assert len(result) == 3
        assert all(job.user_id == test_user.id for job in result)

    def test_get_user_jobs_ordered_by_created_at_desc(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User,
        dataset_config: dict,
        training_params: dict
    ):
        """測試結果按 created_at 倒序排列"""
        # 創建 3 個任務
        jobs = []
        for i in range(3):
            job = ModelTrainingJobRepository.create(
                db=db_session,
                model_id=test_model.id,
                user_id=test_user.id,
                dataset_config=dataset_config,
                training_params=training_params
            )
            jobs.append(job)

        result = ModelTrainingJobRepository.get_by_user(
            db=db_session,
            user_id=test_user.id,
            limit=50
        )

        # 驗證返回所有任務
        assert len(result) == 3

        # 驗證所有創建的任務都在結果中
        result_ids = {job.id for job in result}
        expected_ids = {job.id for job in jobs}
        assert result_ids == expected_ids

        # 驗證排序：檢查 created_at 是倒序的
        for i in range(len(result) - 1):
            assert result[i].created_at >= result[i + 1].created_at

    def test_get_user_jobs_with_limit(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User,
        dataset_config: dict,
        training_params: dict
    ):
        """測試限制返回數量"""
        # 創建 5 個任務
        for i in range(5):
            ModelTrainingJobRepository.create(
                db=db_session,
                model_id=test_model.id,
                user_id=test_user.id,
                dataset_config=dataset_config,
                training_params=training_params
            )

        result = ModelTrainingJobRepository.get_by_user(
            db=db_session,
            user_id=test_user.id,
            limit=3
        )

        assert len(result) == 3


class TestModelTrainingJobRepositoryGetByModel:
    """測試 get_by_model 方法"""

    def test_get_model_jobs(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User,
        dataset_config: dict,
        training_params: dict
    ):
        """測試獲取模型的所有訓練任務"""
        # 創建多個任務
        for i in range(3):
            ModelTrainingJobRepository.create(
                db=db_session,
                model_id=test_model.id,
                user_id=test_user.id,
                dataset_config=dataset_config,
                training_params=training_params
            )

        result = ModelTrainingJobRepository.get_by_model(
            db=db_session,
            model_id=test_model.id,
            limit=10
        )

        assert len(result) == 3
        assert all(job.model_id == test_model.id for job in result)

    def test_get_model_jobs_ordered_by_created_at_desc(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User,
        dataset_config: dict,
        training_params: dict
    ):
        """測試結果按 created_at 倒序排列"""
        jobs = []
        for i in range(3):
            job = ModelTrainingJobRepository.create(
                db=db_session,
                model_id=test_model.id,
                user_id=test_user.id,
                dataset_config=dataset_config,
                training_params=training_params
            )
            jobs.append(job)

        result = ModelTrainingJobRepository.get_by_model(
            db=db_session,
            model_id=test_model.id,
            limit=10
        )

        # 驗證返回所有任務
        assert len(result) == 3

        # 驗證所有創建的任務都在結果中
        result_ids = {job.id for job in result}
        expected_ids = {job.id for job in jobs}
        assert result_ids == expected_ids

        # 驗證排序：檢查 created_at 是倒序的
        for i in range(len(result) - 1):
            assert result[i].created_at >= result[i + 1].created_at


class TestModelTrainingJobRepositoryUpdateStatus:
    """測試 update_status 方法"""

    def test_update_to_running(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User,
        dataset_config: dict,
        training_params: dict
    ):
        """測試更新為 RUNNING 狀態"""
        job = ModelTrainingJobRepository.create(
            db=db_session,
            model_id=test_model.id,
            user_id=test_user.id,
            dataset_config=dataset_config,
            training_params=training_params
        )

        assert job.status == "PENDING"
        assert job.started_at is None

        updated = ModelTrainingJobRepository.update_status(
            db=db_session,
            job_id=job.id,
            status="RUNNING"
        )

        assert updated.status == "RUNNING"
        assert updated.started_at is not None
        assert isinstance(updated.started_at, datetime)

    def test_update_to_completed(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User,
        dataset_config: dict,
        training_params: dict
    ):
        """測試更新為 COMPLETED 狀態"""
        job = ModelTrainingJobRepository.create(
            db=db_session,
            model_id=test_model.id,
            user_id=test_user.id,
            dataset_config=dataset_config,
            training_params=training_params
        )

        # 先設置為 RUNNING
        ModelTrainingJobRepository.update_status(
            db=db_session,
            job_id=job.id,
            status="RUNNING"
        )

        # 更新為 COMPLETED
        updated = ModelTrainingJobRepository.update_status(
            db=db_session,
            job_id=job.id,
            status="COMPLETED"
        )

        assert updated.status == "COMPLETED"
        assert updated.completed_at is not None
        assert updated.progress == 1.0

    def test_update_to_failed_with_error(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User,
        dataset_config: dict,
        training_params: dict
    ):
        """測試更新為 FAILED 狀態並記錄錯誤"""
        job = ModelTrainingJobRepository.create(
            db=db_session,
            model_id=test_model.id,
            user_id=test_user.id,
            dataset_config=dataset_config,
            training_params=training_params
        )

        error_message = "CUDA out of memory"

        updated = ModelTrainingJobRepository.update_status(
            db=db_session,
            job_id=job.id,
            status="FAILED",
            error_message=error_message
        )

        assert updated.status == "FAILED"
        assert updated.completed_at is not None
        assert updated.error_message == error_message

    def test_update_nonexistent_job(self, db_session: Session):
        """測試更新不存在的任務"""
        result = ModelTrainingJobRepository.update_status(
            db=db_session,
            job_id=99999,
            status="RUNNING"
        )

        assert result is None


class TestModelTrainingJobRepositoryUpdateProgress:
    """測試 update_progress 方法"""

    def test_update_progress_basic(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User,
        dataset_config: dict,
        training_params: dict
    ):
        """測試更新訓練進度"""
        job = ModelTrainingJobRepository.create(
            db=db_session,
            model_id=test_model.id,
            user_id=test_user.id,
            dataset_config=dataset_config,
            training_params=training_params
        )

        updated = ModelTrainingJobRepository.update_progress(
            db=db_session,
            job_id=job.id,
            progress=0.5,
            current_epoch=50
        )

        assert updated.progress == 0.5
        assert updated.current_epoch == 50

    def test_update_progress_with_step(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User,
        dataset_config: dict,
        training_params: dict
    ):
        """測試更新進度並設置當前步驟"""
        job = ModelTrainingJobRepository.create(
            db=db_session,
            model_id=test_model.id,
            user_id=test_user.id,
            dataset_config=dataset_config,
            training_params=training_params
        )

        updated = ModelTrainingJobRepository.update_progress(
            db=db_session,
            job_id=job.id,
            progress=0.3,
            current_epoch=30,
            current_step="Training on batch 45/100"
        )

        assert updated.current_step == "Training on batch 45/100"

    def test_update_progress_with_losses(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User,
        dataset_config: dict,
        training_params: dict
    ):
        """測試更新進度並記錄損失"""
        job = ModelTrainingJobRepository.create(
            db=db_session,
            model_id=test_model.id,
            user_id=test_user.id,
            dataset_config=dataset_config,
            training_params=training_params
        )

        updated = ModelTrainingJobRepository.update_progress(
            db=db_session,
            job_id=job.id,
            progress=0.7,
            current_epoch=70,
            train_loss=0.0345,
            valid_loss=0.0412
        )

        assert updated.train_loss == 0.0345
        assert updated.valid_loss == 0.0412

    def test_update_progress_nonexistent_job(self, db_session: Session):
        """測試更新不存在任務的進度"""
        result = ModelTrainingJobRepository.update_progress(
            db=db_session,
            job_id=99999,
            progress=0.5,
            current_epoch=50
        )

        assert result is None


class TestModelTrainingJobRepositoryAppendLog:
    """測試 append_log 方法"""

    def test_append_log_to_empty(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User,
        dataset_config: dict,
        training_params: dict
    ):
        """測試追加日誌到空日誌"""
        job = ModelTrainingJobRepository.create(
            db=db_session,
            model_id=test_model.id,
            user_id=test_user.id,
            dataset_config=dataset_config,
            training_params=training_params
        )

        assert job.training_log == ""

        updated = ModelTrainingJobRepository.append_log(
            db=db_session,
            job_id=job.id,
            log_message="Started training"
        )

        assert "Started training" in updated.training_log
        # 驗證有時間戳
        assert "[" in updated.training_log
        assert "]" in updated.training_log

    def test_append_multiple_logs(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User,
        dataset_config: dict,
        training_params: dict
    ):
        """測試追加多條日誌"""
        job = ModelTrainingJobRepository.create(
            db=db_session,
            model_id=test_model.id,
            user_id=test_user.id,
            dataset_config=dataset_config,
            training_params=training_params
        )

        # 追加第一條
        ModelTrainingJobRepository.append_log(
            db=db_session,
            job_id=job.id,
            log_message="Epoch 1 started"
        )

        # 追加第二條
        updated = ModelTrainingJobRepository.append_log(
            db=db_session,
            job_id=job.id,
            log_message="Epoch 1 completed"
        )

        # 驗證兩條日誌都存在
        assert "Epoch 1 started" in updated.training_log
        assert "Epoch 1 completed" in updated.training_log

        # 驗證有換行
        assert updated.training_log.count("\n") >= 2

    def test_append_log_nonexistent_job(self, db_session: Session):
        """測試追加日誌到不存在的任務"""
        result = ModelTrainingJobRepository.append_log(
            db=db_session,
            job_id=99999,
            log_message="Test log"
        )

        assert result is None


class TestModelTrainingJobRepositoryUpdateCompleted:
    """測試 update_completed 方法"""

    def test_update_completed_basic(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User,
        dataset_config: dict,
        training_params: dict
    ):
        """測試更新訓練完成結果"""
        job = ModelTrainingJobRepository.create(
            db=db_session,
            model_id=test_model.id,
            user_id=test_user.id,
            dataset_config=dataset_config,
            training_params=training_params
        )

        test_metrics = {
            "mse": 0.0234,
            "mae": 0.1123,
            "r2": 0.8956
        }

        updated = ModelTrainingJobRepository.update_completed(
            db=db_session,
            job_id=job.id,
            model_weight_path="/models/weights/model_123.pth",
            test_ic=0.0456,
            test_metrics=test_metrics
        )

        assert updated.status == "COMPLETED"
        assert updated.progress == 1.0
        assert updated.model_weight_path == "/models/weights/model_123.pth"
        assert updated.test_ic == 0.0456
        assert updated.test_metrics == test_metrics
        assert updated.completed_at is not None

    def test_update_completed_nonexistent_job(self, db_session: Session):
        """測試更新不存在任務的完成結果"""
        result = ModelTrainingJobRepository.update_completed(
            db=db_session,
            job_id=99999,
            model_weight_path="/path/to/model.pth",
            test_ic=0.05,
            test_metrics={}
        )

        assert result is None


class TestModelTrainingJobRepositoryDelete:
    """測試 delete 方法"""

    def test_delete_existing_job(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User,
        dataset_config: dict,
        training_params: dict
    ):
        """測試刪除存在的任務"""
        job = ModelTrainingJobRepository.create(
            db=db_session,
            model_id=test_model.id,
            user_id=test_user.id,
            dataset_config=dataset_config,
            training_params=training_params
        )

        job_id = job.id

        # 刪除
        result = ModelTrainingJobRepository.delete(db_session, job_id)

        assert result is True

        # 驗證已刪除
        deleted = ModelTrainingJobRepository.get_by_id(db_session, job_id)
        assert deleted is None

    def test_delete_nonexistent_job(self, db_session: Session):
        """測試刪除不存在的任務"""
        result = ModelTrainingJobRepository.delete(db_session, 99999)

        assert result is False


class TestModelTrainingJobRepositoryCascadeDelete:
    """測試 CASCADE 刪除行為"""

    def test_cascade_delete_when_model_deleted(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User,
        dataset_config: dict,
        training_params: dict
    ):
        """測試刪除模型時自動刪除訓練任務"""
        # 創建訓練任務
        job = ModelTrainingJobRepository.create(
            db=db_session,
            model_id=test_model.id,
            user_id=test_user.id,
            dataset_config=dataset_config,
            training_params=training_params
        )

        job_id = job.id

        # 刪除模型
        db_session.delete(test_model)
        db_session.commit()

        # 驗證訓練任務已自動刪除
        deleted = ModelTrainingJobRepository.get_by_id(db_session, job_id)
        assert deleted is None

    def test_cascade_delete_when_user_deleted(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User,
        dataset_config: dict,
        training_params: dict
    ):
        """測試刪除用戶時自動刪除訓練任務"""
        # 創建訓練任務
        job = ModelTrainingJobRepository.create(
            db=db_session,
            model_id=test_model.id,
            user_id=test_user.id,
            dataset_config=dataset_config,
            training_params=training_params
        )

        job_id = job.id

        # 刪除用戶
        db_session.delete(test_user)
        db_session.commit()

        # 驗證訓練任務已自動刪除
        deleted = ModelTrainingJobRepository.get_by_id(db_session, job_id)
        assert deleted is None
