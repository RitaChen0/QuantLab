"""
Unit tests for ModelFactorRepository
"""
import pytest
from sqlalchemy.orm import Session

from app.repositories.model_factor import ModelFactorRepository
from app.models.rdagent import (
    RDAgentTask,
    GeneratedModel,
    GeneratedFactor,
    ModelFactor,
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
def test_factors(db_session: Session, test_task: RDAgentTask, test_user: User):
    """創建測試因子列表"""
    factors = []
    for i in range(3):
        factor = GeneratedFactor(
            task_id=test_task.id,
            user_id=test_user.id,
            name=f"TestFactor{i}",
            category="Technical",
            formula=f"Close * {i+1}",
            description=f"Test factor {i}"
        )
        factors.append(factor)

    db_session.add_all(factors)
    db_session.commit()

    for factor in factors:
        db_session.refresh(factor)

    return factors


class TestModelFactorRepositoryCreate:
    """測試 create 方法"""

    def test_create_basic(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_factors: list
    ):
        """測試創建基本模型因子關聯"""
        factor = test_factors[0]

        model_factor = ModelFactorRepository.create(
            db=db_session,
            model_id=test_model.id,
            factor_id=factor.id
        )

        assert model_factor.id is not None
        assert model_factor.model_id == test_model.id
        assert model_factor.factor_id == factor.id
        assert model_factor.feature_index is None
        assert model_factor.created_at is not None

    def test_create_with_feature_index(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_factors: list
    ):
        """測試創建帶特徵索引的關聯"""
        factor = test_factors[0]

        model_factor = ModelFactorRepository.create(
            db=db_session,
            model_id=test_model.id,
            factor_id=factor.id,
            feature_index=0
        )

        assert model_factor.feature_index == 0


class TestModelFactorRepositoryGetByModel:
    """測試 get_by_model 方法"""

    def test_get_empty_list(
        self,
        db_session: Session,
        test_model: GeneratedModel
    ):
        """測試獲取無關聯的模型"""
        result = ModelFactorRepository.get_by_model(
            db=db_session,
            model_id=test_model.id
        )

        assert result == []

    def test_get_model_factors(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_factors: list
    ):
        """測試獲取模型的所有關聯因子"""
        # 創建多個關聯
        for idx, factor in enumerate(test_factors):
            ModelFactorRepository.create(
                db=db_session,
                model_id=test_model.id,
                factor_id=factor.id,
                feature_index=idx
            )

        result = ModelFactorRepository.get_by_model(
            db=db_session,
            model_id=test_model.id
        )

        assert len(result) == 3
        assert all(mf.model_id == test_model.id for mf in result)

    def test_get_model_factors_ordered_by_index(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_factors: list
    ):
        """測試結果按 feature_index 排序"""
        # 倒序創建關聯
        for idx, factor in enumerate(reversed(test_factors)):
            ModelFactorRepository.create(
                db=db_session,
                model_id=test_model.id,
                factor_id=factor.id,
                feature_index=len(test_factors) - idx - 1
            )

        result = ModelFactorRepository.get_by_model(
            db=db_session,
            model_id=test_model.id
        )

        # 驗證按 feature_index 升序排列
        for i in range(len(result)):
            assert result[i].feature_index == i


class TestModelFactorRepositoryGetFactorsByModel:
    """測試 get_factors_by_model 方法"""

    def test_get_empty_factor_list(
        self,
        db_session: Session,
        test_model: GeneratedModel
    ):
        """測試獲取無關聯因子的模型"""
        result = ModelFactorRepository.get_factors_by_model(
            db=db_session,
            model_id=test_model.id
        )

        assert result == []

    def test_get_factor_objects(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_factors: list
    ):
        """測試獲取因子對象列表"""
        # 創建關聯
        for idx, factor in enumerate(test_factors):
            ModelFactorRepository.create(
                db=db_session,
                model_id=test_model.id,
                factor_id=factor.id,
                feature_index=idx
            )

        result = ModelFactorRepository.get_factors_by_model(
            db=db_session,
            model_id=test_model.id
        )

        # 驗證返回 GeneratedFactor 對象
        assert len(result) == 3
        assert all(isinstance(f, GeneratedFactor) for f in result)

        # 驗證因子 ID 正確
        result_ids = {f.id for f in result}
        expected_ids = {f.id for f in test_factors}
        assert result_ids == expected_ids


class TestModelFactorRepositoryDeleteByModel:
    """測試 delete_by_model 方法"""

    def test_delete_nonexistent(
        self,
        db_session: Session,
        test_model: GeneratedModel
    ):
        """測試刪除不存在的關聯"""
        count = ModelFactorRepository.delete_by_model(
            db=db_session,
            model_id=test_model.id
        )

        assert count == 0

    def test_delete_all_factors(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_factors: list
    ):
        """測試刪除模型的所有因子關聯"""
        # 創建關聯
        for factor in test_factors:
            ModelFactorRepository.create(
                db=db_session,
                model_id=test_model.id,
                factor_id=factor.id
            )

        # 驗證已創建
        before = ModelFactorRepository.get_by_model(db_session, test_model.id)
        assert len(before) == 3

        # 刪除
        count = ModelFactorRepository.delete_by_model(
            db=db_session,
            model_id=test_model.id
        )

        assert count == 3

        # 驗證已刪除
        after = ModelFactorRepository.get_by_model(db_session, test_model.id)
        assert after == []


class TestModelFactorRepositoryBatchCreate:
    """測試 batch_create 方法"""

    def test_batch_create_basic(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_factors: list
    ):
        """測試批次創建關聯"""
        factor_ids = [f.id for f in test_factors]

        result = ModelFactorRepository.batch_create(
            db=db_session,
            model_id=test_model.id,
            factor_ids=factor_ids
        )

        assert len(result) == 3
        assert all(mf.model_id == test_model.id for mf in result)
        assert all(mf.id is not None for mf in result)

    def test_batch_create_with_feature_index(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_factors: list
    ):
        """測試批次創建自動設置 feature_index"""
        factor_ids = [f.id for f in test_factors]

        result = ModelFactorRepository.batch_create(
            db=db_session,
            model_id=test_model.id,
            factor_ids=factor_ids
        )

        # 驗證 feature_index 按順序設置
        for idx, mf in enumerate(result):
            assert mf.feature_index == idx

    def test_batch_create_replaces_existing(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_factors: list
    ):
        """測試批次創建會替換現有關聯"""
        # 創建初始關聯（前 2 個因子）
        initial_ids = [test_factors[0].id, test_factors[1].id]
        ModelFactorRepository.batch_create(
            db=db_session,
            model_id=test_model.id,
            factor_ids=initial_ids
        )

        # 驗證初始狀態
        before = ModelFactorRepository.get_by_model(db_session, test_model.id)
        assert len(before) == 2

        # 批次創建新關聯（所有 3 個因子）
        new_ids = [f.id for f in test_factors]
        result = ModelFactorRepository.batch_create(
            db=db_session,
            model_id=test_model.id,
            factor_ids=new_ids
        )

        # 驗證舊關聯被替換
        assert len(result) == 3

        after = ModelFactorRepository.get_by_model(db_session, test_model.id)
        assert len(after) == 3

    def test_batch_create_empty_list(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_factors: list
    ):
        """測試批次創建空列表會刪除所有關聯"""
        # 創建初始關聯
        initial_ids = [f.id for f in test_factors]
        ModelFactorRepository.batch_create(
            db=db_session,
            model_id=test_model.id,
            factor_ids=initial_ids
        )

        # 批次創建空列表
        result = ModelFactorRepository.batch_create(
            db=db_session,
            model_id=test_model.id,
            factor_ids=[]
        )

        assert result == []

        # 驗證所有關聯已刪除
        after = ModelFactorRepository.get_by_model(db_session, test_model.id)
        assert after == []


class TestModelFactorRepositoryCascadeDelete:
    """測試 CASCADE 刪除行為"""

    def test_cascade_delete_when_model_deleted(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_factors: list
    ):
        """測試刪除模型時自動刪除關聯"""
        # 創建關聯
        for factor in test_factors:
            ModelFactorRepository.create(
                db=db_session,
                model_id=test_model.id,
                factor_id=factor.id
            )

        # 驗證關聯已創建
        before = ModelFactorRepository.get_by_model(db_session, test_model.id)
        assert len(before) == 3

        # 刪除模型
        db_session.delete(test_model)
        db_session.commit()

        # 驗證關聯已自動刪除（通過查詢 ModelFactor 表）
        remaining = db_session.query(ModelFactor).all()
        assert remaining == []

    def test_cascade_delete_when_factor_deleted(
        self,
        db_session: Session,
        test_model: GeneratedModel,
        test_factors: list
    ):
        """測試刪除因子時自動刪除關聯"""
        # 創建關聯
        for factor in test_factors:
            ModelFactorRepository.create(
                db=db_session,
                model_id=test_model.id,
                factor_id=factor.id
            )

        # 刪除一個因子
        db_session.delete(test_factors[0])
        db_session.commit()

        # 驗證對應關聯已自動刪除
        after = ModelFactorRepository.get_by_model(db_session, test_model.id)
        assert len(after) == 2

        # 驗證剩餘關聯正確
        remaining_factor_ids = {mf.factor_id for mf in after}
        assert test_factors[0].id not in remaining_factor_ids
