"""
Unit tests for RDAgentTaskRepository
"""
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.repositories.rdagent_task import RDAgentTaskRepository
from app.models.rdagent import RDAgentTask, TaskType, TaskStatus
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
        status=TaskStatus.PENDING,
        input_params={"param1": "value1"},
        llm_calls=0,
        llm_cost=0.0
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


class TestRDAgentTaskRepositoryGetById:
    """測試 get_by_id 方法"""

    def test_get_existing_task(self, db_session: Session, test_task: RDAgentTask):
        """測試獲取存在的任務"""
        result = RDAgentTaskRepository.get_by_id(db_session, test_task.id)

        assert result is not None
        assert result.id == test_task.id
        assert result.user_id == test_task.user_id
        assert result.task_type == TaskType.FACTOR_MINING
        assert result.status == TaskStatus.PENDING

    def test_get_nonexistent_task(self, db_session: Session):
        """測試獲取不存在的任務"""
        result = RDAgentTaskRepository.get_by_id(db_session, 99999)

        assert result is None


class TestRDAgentTaskRepositoryGetByIdAndUser:
    """測試 get_by_id_and_user 方法（權限檢查）"""

    def test_get_task_with_correct_user(self, db_session: Session, test_task: RDAgentTask, test_user: User):
        """測試正確用戶可以獲取任務"""
        result = RDAgentTaskRepository.get_by_id_and_user(
            db_session,
            test_task.id,
            test_user.id
        )

        assert result is not None
        assert result.id == test_task.id
        assert result.user_id == test_user.id

    def test_get_task_with_wrong_user(self, db_session: Session, test_task: RDAgentTask):
        """測試錯誤用戶無法獲取任務"""
        result = RDAgentTaskRepository.get_by_id_and_user(
            db_session,
            test_task.id,
            99999  # 不存在的用戶 ID
        )

        assert result is None

    def test_get_nonexistent_task(self, db_session: Session, test_user: User):
        """測試獲取不存在的任務"""
        result = RDAgentTaskRepository.get_by_id_and_user(
            db_session,
            99999,
            test_user.id
        )

        assert result is None


class TestRDAgentTaskRepositoryGetByUser:
    """測試 get_by_user 方法"""

    def test_get_user_tasks(self, db_session: Session, test_user: User):
        """測試獲取用戶的所有任務"""
        # 創建多個任務
        tasks = []
        for i in range(3):
            task = RDAgentTask(
                user_id=test_user.id,
                task_type=TaskType.FACTOR_MINING,
                status=TaskStatus.PENDING,
                input_params={"iteration": i}
            )
            db_session.add(task)
            tasks.append(task)
        db_session.commit()

        # 獲取任務列表
        result = RDAgentTaskRepository.get_by_user(
            db_session,
            test_user.id,
            skip=0,
            limit=10
        )

        assert len(result) == 3
        assert all(task.user_id == test_user.id for task in result)

    def test_get_user_tasks_with_type_filter(self, db_session: Session, test_user: User):
        """測試按類型篩選用戶任務"""
        # 創建不同類型的任務
        task1 = RDAgentTask(
            user_id=test_user.id,
            task_type=TaskType.FACTOR_MINING,
            status=TaskStatus.PENDING
        )
        task2 = RDAgentTask(
            user_id=test_user.id,
            task_type=TaskType.MODEL_GENERATION,
            status=TaskStatus.PENDING
        )
        db_session.add_all([task1, task2])
        db_session.commit()

        # 只獲取 FACTOR_MINING 類型
        result = RDAgentTaskRepository.get_by_user(
            db_session,
            test_user.id,
            task_type=TaskType.FACTOR_MINING,
            skip=0,
            limit=10
        )

        assert len(result) == 1
        assert result[0].task_type == TaskType.FACTOR_MINING

    def test_get_user_tasks_pagination(self, db_session: Session, test_user: User):
        """測試分頁功能"""
        # 創建 5 個任務
        for i in range(5):
            task = RDAgentTask(
                user_id=test_user.id,
                task_type=TaskType.FACTOR_MINING,
                status=TaskStatus.PENDING
            )
            db_session.add(task)
        db_session.commit()

        # 獲取第一頁（2 條）
        page1 = RDAgentTaskRepository.get_by_user(
            db_session,
            test_user.id,
            skip=0,
            limit=2
        )

        # 獲取第二頁（2 條）
        page2 = RDAgentTaskRepository.get_by_user(
            db_session,
            test_user.id,
            skip=2,
            limit=2
        )

        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id  # 不同的任務

    def test_get_user_tasks_empty(self, db_session: Session, test_user: User):
        """測試用戶無任務時返回空列表"""
        result = RDAgentTaskRepository.get_by_user(
            db_session,
            test_user.id,
            skip=0,
            limit=10
        )

        assert result == []


class TestRDAgentTaskRepositoryCreate:
    """測試 create 方法"""

    def test_create_task(self, db_session: Session, test_user: User):
        """測試創建任務"""
        # 創建任務對象
        new_task = RDAgentTask(
            user_id=test_user.id,
            task_type=TaskType.FACTOR_MINING,
            status=TaskStatus.PENDING,
            input_params={"test": "data"},
            llm_calls=0,
            llm_cost=0.0
        )

        # 通過 Repository 保存
        task = RDAgentTaskRepository.create(db_session, new_task)

        assert task.id is not None
        assert task.user_id == test_user.id
        assert task.task_type == TaskType.FACTOR_MINING
        assert task.status == TaskStatus.PENDING
        assert task.input_params == {"test": "data"}
        assert task.llm_calls == 0
        assert task.llm_cost == 0.0
        assert task.created_at is not None

    def test_create_task_with_optional_fields(self, db_session: Session, test_user: User):
        """測試創建任務（包含可選欄位）"""
        # 創建任務對象（包含可選欄位）
        new_task = RDAgentTask(
            user_id=test_user.id,
            task_type=TaskType.MODEL_GENERATION,
            status=TaskStatus.PENDING,
            input_params={"param1": "value1"},
            result={"output": "result"},
            error_message="Test error",
            llm_calls=5,
            llm_cost=0.25
        )

        task = RDAgentTaskRepository.create(db_session, new_task)

        assert task.result == {"output": "result"}
        assert task.error_message == "Test error"
        assert task.llm_calls == 5
        assert task.llm_cost == 0.25


class TestRDAgentTaskRepositoryUpdate:
    """測試 update 方法"""

    def test_update_task_status(self, db_session: Session, test_task: RDAgentTask):
        """測試更新任務狀態"""
        # 修改任務對象
        test_task.status = TaskStatus.RUNNING
        test_task.started_at = datetime.now(timezone.utc)

        # 通過 Repository 更新
        updated_task = RDAgentTaskRepository.update(db_session, test_task)

        assert updated_task.status == TaskStatus.RUNNING
        assert updated_task.started_at is not None

    def test_update_task_result(self, db_session: Session, test_task: RDAgentTask):
        """測試更新任務結果"""
        result_data = {"factors": ["factor1", "factor2"]}

        # 修改任務對象
        test_task.status = TaskStatus.COMPLETED
        test_task.result = result_data
        test_task.completed_at = datetime.now(timezone.utc)

        # 通過 Repository 更新
        updated_task = RDAgentTaskRepository.update(db_session, test_task)

        assert updated_task.status == TaskStatus.COMPLETED
        assert updated_task.result == result_data
        assert updated_task.completed_at is not None

    def test_update_task_llm_stats(self, db_session: Session, test_task: RDAgentTask):
        """測試更新 LLM 統計"""
        # 修改任務對象
        test_task.llm_calls = 10
        test_task.llm_cost = 0.50

        # 通過 Repository 更新
        updated_task = RDAgentTaskRepository.update(db_session, test_task)

        assert updated_task.llm_calls == 10
        assert updated_task.llm_cost == 0.50


class TestRDAgentTaskRepositoryDelete:
    """測試 delete 方法"""

    def test_delete_task(self, db_session: Session, test_task: RDAgentTask):
        """測試刪除任務"""
        task_id = test_task.id

        RDAgentTaskRepository.delete(db_session, test_task)

        # 確認已刪除
        deleted_task = RDAgentTaskRepository.get_by_id(db_session, task_id)
        assert deleted_task is None


class TestRDAgentTaskRepositoryCountByUser:
    """測試 count_by_user 方法"""

    def test_count_user_tasks(self, db_session: Session, test_user: User):
        """測試統計用戶任務數"""
        # 創建 3 個任務
        for i in range(3):
            task = RDAgentTask(
                user_id=test_user.id,
                task_type=TaskType.FACTOR_MINING,
                status=TaskStatus.PENDING
            )
            db_session.add(task)
        db_session.commit()

        count = RDAgentTaskRepository.count_by_user(db_session, test_user.id)

        assert count == 3

    def test_count_no_tasks(self, db_session: Session, test_user: User):
        """測試用戶無任務時計數為 0"""
        count = RDAgentTaskRepository.count_by_user(db_session, test_user.id)

        assert count == 0


class TestRDAgentTaskRepositoryGetByStatus:
    """測試 get_by_status 方法"""

    def test_get_tasks_by_status(self, db_session: Session, test_user: User):
        """測試按狀態獲取任務"""
        # 創建不同狀態的任務
        task1 = RDAgentTask(
            user_id=test_user.id,
            task_type=TaskType.FACTOR_MINING,
            status=TaskStatus.PENDING
        )
        task2 = RDAgentTask(
            user_id=test_user.id,
            task_type=TaskType.FACTOR_MINING,
            status=TaskStatus.RUNNING
        )
        task3 = RDAgentTask(
            user_id=test_user.id,
            task_type=TaskType.FACTOR_MINING,
            status=TaskStatus.PENDING
        )
        db_session.add_all([task1, task2, task3])
        db_session.commit()

        # 獲取 PENDING 狀態的任務
        pending_tasks = RDAgentTaskRepository.get_by_status(
            db_session,
            TaskStatus.PENDING
        )

        assert len(pending_tasks) == 2
        assert all(task.status == TaskStatus.PENDING for task in pending_tasks)

    def test_get_tasks_by_status_empty(self, db_session: Session):
        """測試無匹配狀態時返回空列表"""
        tasks = RDAgentTaskRepository.get_by_status(
            db_session,
            TaskStatus.COMPLETED
        )

        assert tasks == []
