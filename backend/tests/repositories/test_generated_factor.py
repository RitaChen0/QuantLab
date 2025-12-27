"""
Unit tests for GeneratedFactorRepository
"""
import pytest
from sqlalchemy.orm import Session

from app.repositories.generated_factor import GeneratedFactorRepository
from app.models.rdagent import RDAgentTask, GeneratedFactor, TaskType, TaskStatus
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
        task_type=TaskType.FACTOR_MINING,
        status=TaskStatus.COMPLETED
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


@pytest.fixture
def test_factor(db_session: Session, test_task: RDAgentTask, test_user: User):
    """Create a test GeneratedFactor"""
    factor = GeneratedFactor(
        task_id=test_task.id,
        user_id=test_user.id,
        name="TestFactor",
        formula="(Close - Open) / Open",
        description="Test momentum factor",
        category="momentum",
        ic=0.05,
        icir=1.2,
        sharpe_ratio=1.5,
        annual_return=0.15
    )
    db_session.add(factor)
    db_session.commit()
    db_session.refresh(factor)
    return factor


class TestGeneratedFactorRepositoryGetById:
    """測試 get_by_id 方法"""

    def test_get_existing_factor(self, db_session: Session, test_factor: GeneratedFactor):
        """測試獲取存在的因子"""
        result = GeneratedFactorRepository.get_by_id(db_session, test_factor.id)

        assert result is not None
        assert result.id == test_factor.id
        assert result.name == "TestFactor"
        assert result.formula == "(Close - Open) / Open"

    def test_get_nonexistent_factor(self, db_session: Session):
        """測試獲取不存在的因子"""
        result = GeneratedFactorRepository.get_by_id(db_session, 99999)

        assert result is None


class TestGeneratedFactorRepositoryGetByIdAndUser:
    """測試 get_by_id_and_user 方法（權限檢查）"""

    def test_get_factor_with_correct_user(
        self,
        db_session: Session,
        test_factor: GeneratedFactor,
        test_user: User
    ):
        """測試正確用戶可以獲取因子"""
        result = GeneratedFactorRepository.get_by_id_and_user(
            db_session,
            test_factor.id,
            test_user.id
        )

        assert result is not None
        assert result.id == test_factor.id
        assert result.user_id == test_user.id

    def test_get_factor_with_wrong_user(
        self,
        db_session: Session,
        test_factor: GeneratedFactor
    ):
        """測試錯誤用戶無法獲取因子"""
        result = GeneratedFactorRepository.get_by_id_and_user(
            db_session,
            test_factor.id,
            99999  # 不存在的用戶 ID
        )

        assert result is None


class TestGeneratedFactorRepositoryGetByUser:
    """測試 get_by_user 方法"""

    def test_get_user_factors(
        self,
        db_session: Session,
        test_user: User,
        test_task: RDAgentTask
    ):
        """測試獲取用戶的所有因子"""
        # 創建多個因子
        for i in range(3):
            factor = GeneratedFactor(
                task_id=test_task.id,
                user_id=test_user.id,
                name=f"Factor{i}",
                formula=f"Close * {i}",
                category="momentum"
            )
            db_session.add(factor)
        db_session.commit()

        # 獲取因子列表
        result = GeneratedFactorRepository.get_by_user(
            db_session,
            test_user.id,
            skip=0,
            limit=10
        )

        assert len(result) == 3
        assert all(factor.user_id == test_user.id for factor in result)

    def test_get_user_factors_pagination(
        self,
        db_session: Session,
        test_user: User,
        test_task: RDAgentTask
    ):
        """測試分頁功能"""
        # 創建 5 個因子
        for i in range(5):
            factor = GeneratedFactor(
                task_id=test_task.id,
                user_id=test_user.id,
                name=f"Factor{i}",
                formula="Close",
                category="momentum"
            )
            db_session.add(factor)
        db_session.commit()

        # 獲取第一頁（2 條）
        page1 = GeneratedFactorRepository.get_by_user(
            db_session,
            test_user.id,
            skip=0,
            limit=2
        )

        # 獲取第二頁（2 條）
        page2 = GeneratedFactorRepository.get_by_user(
            db_session,
            test_user.id,
            skip=2,
            limit=2
        )

        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id


class TestGeneratedFactorRepositoryGetByTask:
    """測試 get_by_task 方法"""

    def test_get_task_factors(
        self,
        db_session: Session,
        test_user: User,
        test_task: RDAgentTask
    ):
        """測試獲取任務的所有因子"""
        # 創建多個因子
        for i in range(3):
            factor = GeneratedFactor(
                task_id=test_task.id,
                user_id=test_user.id,
                name=f"Factor{i}",
                formula="Close",
                category="momentum"
            )
            db_session.add(factor)
        db_session.commit()

        result = GeneratedFactorRepository.get_by_task(
            db_session,
            test_task.id,
            skip=0,
            limit=10
        )

        assert len(result) == 3
        assert all(factor.task_id == test_task.id for factor in result)


class TestGeneratedFactorRepositoryCreate:
    """測試 create 方法"""

    def test_create_factor_basic(
        self,
        db_session: Session,
        test_task: RDAgentTask,
        test_user: User
    ):
        """測試創建基本因子"""
        factor = GeneratedFactorRepository.create(
            db_session,
            task_id=test_task.id,
            user_id=test_user.id,
            name="NewFactor",
            formula="(High + Low) / 2"
        )

        assert factor.id is not None
        assert factor.name == "NewFactor"
        assert factor.formula == "(High + Low) / 2"
        assert factor.task_id == test_task.id
        assert factor.user_id == test_user.id
        assert factor.created_at is not None

    def test_create_factor_with_all_fields(
        self,
        db_session: Session,
        test_task: RDAgentTask,
        test_user: User
    ):
        """測試創建完整因子"""
        factor = GeneratedFactorRepository.create(
            db_session,
            task_id=test_task.id,
            user_id=test_user.id,
            name="CompleteFactor",
            formula="MA(Close, 20)",
            description="20-day moving average",
            code="def calculate(): return ma(close, 20)",
            category="trend",
            ic=0.08,
            icir=1.5,
            sharpe_ratio=2.0,
            annual_return=0.25,
            factor_metadata={"window": 20}
        )

        assert factor.description == "20-day moving average"
        assert factor.code == "def calculate(): return ma(close, 20)"
        assert factor.category == "trend"
        assert factor.ic == 0.08
        assert factor.icir == 1.5
        assert factor.sharpe_ratio == 2.0
        assert factor.annual_return == 0.25
        assert factor.factor_metadata == {"window": 20}


class TestGeneratedFactorRepositoryUpdate:
    """測試 update 方法"""

    def test_update_factor_metrics(
        self,
        db_session: Session,
        test_factor: GeneratedFactor
    ):
        """測試更新因子指標"""
        updated_factor = GeneratedFactorRepository.update(
            db_session,
            test_factor,
            ic=0.10,
            icir=2.0,
            sharpe_ratio=2.5
        )

        assert updated_factor.ic == 0.10
        assert updated_factor.icir == 2.0
        assert updated_factor.sharpe_ratio == 2.5

    def test_update_factor_description(
        self,
        db_session: Session,
        test_factor: GeneratedFactor
    ):
        """測試更新因子描述"""
        updated_factor = GeneratedFactorRepository.update(
            db_session,
            test_factor,
            description="Updated description",
            category="value"
        )

        assert updated_factor.description == "Updated description"
        assert updated_factor.category == "value"


class TestGeneratedFactorRepositoryDelete:
    """測試 delete 方法"""

    def test_delete_factor(
        self,
        db_session: Session,
        test_factor: GeneratedFactor
    ):
        """測試刪除因子"""
        factor_id = test_factor.id

        GeneratedFactorRepository.delete(db_session, test_factor)

        # 確認已刪除
        deleted_factor = GeneratedFactorRepository.get_by_id(db_session, factor_id)
        assert deleted_factor is None


class TestGeneratedFactorRepositoryDeleteByTask:
    """測試 delete_by_task 方法（級聯刪除）"""

    def test_delete_all_task_factors(
        self,
        db_session: Session,
        test_user: User,
        test_task: RDAgentTask
    ):
        """測試刪除任務的所有因子"""
        # 創建 3 個因子
        for i in range(3):
            factor = GeneratedFactor(
                task_id=test_task.id,
                user_id=test_user.id,
                name=f"Factor{i}",
                formula="Close",
                category="momentum"
            )
            db_session.add(factor)
        db_session.commit()

        # 確認創建成功
        factors_before = GeneratedFactorRepository.get_by_task(
            db_session,
            test_task.id
        )
        assert len(factors_before) == 3

        # 刪除所有因子
        deleted_count = GeneratedFactorRepository.delete_by_task(
            db_session,
            test_task.id
        )

        assert deleted_count == 3

        # 確認已刪除
        factors_after = GeneratedFactorRepository.get_by_task(
            db_session,
            test_task.id
        )
        assert len(factors_after) == 0


class TestGeneratedFactorRepositoryCountByUser:
    """測試 count_by_user 方法"""

    def test_count_user_factors(
        self,
        db_session: Session,
        test_user: User,
        test_task: RDAgentTask
    ):
        """測試統計用戶因子數"""
        # 創建 3 個因子
        for i in range(3):
            factor = GeneratedFactor(
                task_id=test_task.id,
                user_id=test_user.id,
                name=f"Factor{i}",
                formula="Close",
                category="momentum"
            )
            db_session.add(factor)
        db_session.commit()

        count = GeneratedFactorRepository.count_by_user(db_session, test_user.id)

        assert count == 3

    def test_count_no_factors(self, db_session: Session, test_user: User):
        """測試用戶無因子時計數為 0"""
        count = GeneratedFactorRepository.count_by_user(db_session, test_user.id)

        assert count == 0


class TestGeneratedFactorRepositoryCountByTask:
    """測試 count_by_task 方法"""

    def test_count_task_factors(
        self,
        db_session: Session,
        test_user: User,
        test_task: RDAgentTask
    ):
        """測試統計任務因子數"""
        # 創建 3 個因子
        for i in range(3):
            factor = GeneratedFactor(
                task_id=test_task.id,
                user_id=test_user.id,
                name=f"Factor{i}",
                formula="Close",
                category="momentum"
            )
            db_session.add(factor)
        db_session.commit()

        count = GeneratedFactorRepository.count_by_task(db_session, test_task.id)

        assert count == 3


class TestGeneratedFactorRepositoryIsOwner:
    """測試 is_owner 方法"""

    def test_is_owner_true(
        self,
        db_session: Session,
        test_factor: GeneratedFactor,
        test_user: User
    ):
        """測試正確的擁有者"""
        is_owner = GeneratedFactorRepository.is_owner(
            db_session,
            test_factor.id,
            test_user.id
        )

        assert is_owner is True

    def test_is_owner_false(
        self,
        db_session: Session,
        test_factor: GeneratedFactor
    ):
        """測試錯誤的擁有者"""
        is_owner = GeneratedFactorRepository.is_owner(
            db_session,
            test_factor.id,
            99999  # 不存在的用戶
        )

        assert is_owner is False
