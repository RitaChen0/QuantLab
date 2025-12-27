"""
Unit tests for GeneratedModelRepository
"""
import pytest
from sqlalchemy.orm import Session

from app.repositories.generated_model import GeneratedModelRepository
from app.models.rdagent import RDAgentTask, GeneratedModel, TaskType, TaskStatus
from app.models.user import User


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user"""
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
    """Create a test RDAgentTask"""
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
    """Create a test GeneratedModel"""
    model = GeneratedModel(
        task_id=test_task.id,
        user_id=test_user.id,
        name="TestModel",
        model_type="TimeSeries",
        description="Test ML model",
        architecture="LSTM",
        variables={"features": ["Close", "Volume"]},
        hyperparameters={"layers": 3, "units": 128}
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


class TestGeneratedModelRepositoryGetById:
    """測試 get_by_id 方法"""

    def test_get_existing_model(self, db_session: Session, test_model: GeneratedModel):
        """測試獲取存在的模型"""
        result = GeneratedModelRepository.get_by_id(db_session, test_model.id)

        assert result is not None
        assert result.id == test_model.id
        assert result.name == "TestModel"
        assert result.model_type == "TimeSeries"

    def test_get_nonexistent_model(self, db_session: Session):
        """測試獲取不存在的模型"""
        result = GeneratedModelRepository.get_by_id(db_session, 99999)

        assert result is None


class TestGeneratedModelRepositoryGetByIdAndUser:
    """測試 get_by_id_and_user 方法（權限檢查）"""

    def test_get_model_with_correct_user(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_user: User
    ):
        """測試正確用戶可以獲取模型"""
        result = GeneratedModelRepository.get_by_id_and_user(
            db_session,
            test_model.id,
            test_user.id
        )

        assert result is not None
        assert result.id == test_model.id
        assert result.user_id == test_user.id

    def test_get_model_with_wrong_user(
        self,
        db_session: Session,
        test_model: GeneratedModel
    ):
        """測試錯誤用戶無法獲取模型"""
        result = GeneratedModelRepository.get_by_id_and_user(
            db_session,
            test_model.id,
            99999  # 不存在的用戶 ID
        )

        assert result is None


class TestGeneratedModelRepositoryGetByUser:
    """測試 get_by_user 方法"""

    def test_get_user_models(
        self,
        db_session: Session,
        test_user: User,
        test_task: RDAgentTask
    ):
        """測試獲取用戶的所有模型"""
        # 創建多個模型
        for i in range(3):
            model = GeneratedModel(
                task_id=test_task.id,
                user_id=test_user.id,
                name=f"Model{i}",
                model_type="TimeSeries"
            )
            db_session.add(model)
        db_session.commit()

        result = GeneratedModelRepository.get_by_user(
            db_session,
            test_user.id,
            skip=0,
            limit=10
        )

        assert len(result) == 3
        assert all(model.user_id == test_user.id for model in result)

    def test_get_user_models_pagination(
        self,
        db_session: Session,
        test_user: User,
        test_task: RDAgentTask
    ):
        """測試分頁功能"""
        # 創建 5 個模型
        for i in range(5):
            model = GeneratedModel(
                task_id=test_task.id,
                user_id=test_user.id,
                name=f"Model{i}",
                model_type="TimeSeries"
            )
            db_session.add(model)
        db_session.commit()

        # 獲取第一頁（2 條）
        page1 = GeneratedModelRepository.get_by_user(
            db_session,
            test_user.id,
            skip=0,
            limit=2
        )

        assert len(page1) == 2

        # 獲取第二頁（2 條）
        page2 = GeneratedModelRepository.get_by_user(
            db_session,
            test_user.id,
            skip=2,
            limit=2
        )

        assert len(page2) == 2
        assert page1[0].id != page2[0].id


class TestGeneratedModelRepositoryGetByTask:
    """測試 get_by_task 方法"""

    def test_get_task_models(
        self,
        db_session: Session,
        test_user: User,
        test_task: RDAgentTask
    ):
        """測試獲取任務的所有模型"""
        # 創建多個模型
        for i in range(3):
            model = GeneratedModel(
                task_id=test_task.id,
                user_id=test_user.id,
                name=f"Model{i}",
                model_type="Tabular"
            )
            db_session.add(model)
        db_session.commit()

        result = GeneratedModelRepository.get_by_task(
            db_session,
            test_task.id,
            skip=0,
            limit=10
        )

        assert len(result) == 3
        assert all(model.task_id == test_task.id for model in result)


class TestGeneratedModelRepositoryCreate:
    """測試 create 方法"""

    def test_create_model_basic(
        self,
        db_session: Session,
        test_task: RDAgentTask,
        test_user: User
    ):
        """測試創建基本模型"""
        # 創建模型對象
        new_model = GeneratedModel(
            task_id=test_task.id,
            user_id=test_user.id,
            name="NewModel",
            model_type="TimeSeries"
        )

        # 通過 Repository 保存
        model = GeneratedModelRepository.create(db_session, new_model)

        assert model.id is not None
        assert model.name == "NewModel"
        assert model.model_type == "TimeSeries"
        assert model.task_id == test_task.id
        assert model.user_id == test_user.id
        assert model.created_at is not None

    def test_create_model_with_all_fields(
        self,
        db_session: Session,
        test_task: RDAgentTask,
        test_user: User
    ):
        """測試創建完整模型"""
        # 創建完整模型對象
        new_model = GeneratedModel(
            task_id=test_task.id,
            user_id=test_user.id,
            name="CompleteModel",
            model_type="Tabular",
            description="Full model with all fields",
            architecture="GRU + Attention",
            variables={"x": "features", "y": "target"},
            hyperparameters={"lr": 0.001, "epochs": 100}
        )

        model = GeneratedModelRepository.create(db_session, new_model)

        assert model.description == "Full model with all fields"
        assert model.architecture == "GRU + Attention"
        assert model.variables == {"x": "features", "y": "target"}
        assert model.hyperparameters == {"lr": 0.001, "epochs": 100}


class TestGeneratedModelRepositoryUpdate:
    """測試 update 方法"""

    def test_update_model_description(
        self,
        db_session: Session,
        test_model: GeneratedModel
    ):
        """測試更新模型描述"""
        # 修改模型對象
        test_model.description = "Updated description"

        # 通過 Repository 更新
        updated_model = GeneratedModelRepository.update(db_session, test_model)

        assert updated_model.description == "Updated description"

    def test_update_model_hyperparameters(
        self,
        db_session: Session,
        test_model: GeneratedModel
    ):
        """測試更新超參數"""
        new_params = {"layers": 5, "units": 256}

        # 修改模型對象
        test_model.hyperparameters = new_params

        # 通過 Repository 更新
        updated_model = GeneratedModelRepository.update(db_session, test_model)

        assert updated_model.hyperparameters == new_params


class TestGeneratedModelRepositoryDelete:
    """測試 delete 方法"""

    def test_delete_model(
        self,
        db_session: Session,
        test_model: GeneratedModel
    ):
        """測試刪除模型"""
        model_id = test_model.id

        GeneratedModelRepository.delete(db_session, test_model)

        # 確認已刪除
        deleted_model = GeneratedModelRepository.get_by_id(db_session, model_id)
        assert deleted_model is None


class TestGeneratedModelRepositoryCountByUser:
    """測試 count_by_user 方法"""

    def test_count_user_models(
        self,
        db_session: Session,
        test_user: User,
        test_task: RDAgentTask
    ):
        """測試統計用戶模型數"""
        # 創建 3 個模型
        for i in range(3):
            model = GeneratedModel(
                task_id=test_task.id,
                user_id=test_user.id,
                name=f"Model{i}",
                model_type="TimeSeries"
            )
            db_session.add(model)
        db_session.commit()

        count = GeneratedModelRepository.count_by_user(db_session, test_user.id)

        assert count == 3

    def test_count_no_models(self, db_session: Session, test_user: User):
        """測試用戶無模型時計數為 0"""
        count = GeneratedModelRepository.count_by_user(db_session, test_user.id)

        assert count == 0


class TestGeneratedModelRepositoryCountByTask:
    """測試 count_by_task 方法"""

    def test_count_task_models(
        self,
        db_session: Session,
        test_user: User,
        test_task: RDAgentTask
    ):
        """測試統計任務模型數"""
        # 創建 3 個模型
        for i in range(3):
            model = GeneratedModel(
                task_id=test_task.id,
                user_id=test_user.id,
                name=f"Model{i}",
                model_type="TimeSeries"
            )
            db_session.add(model)
        db_session.commit()

        count = GeneratedModelRepository.count_by_task(db_session, test_task.id)

        assert count == 3
