"""
Unit tests for StrategySignalRepository
"""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.repositories.strategy_signal import StrategySignalRepository
from app.models.strategy_signal import StrategySignal
from app.models.strategy import Strategy, StrategyStatus
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
def test_strategy(db_session: Session, test_user: User):
    """Create a test strategy"""
    strategy = Strategy(
        user_id=test_user.id,
        name="TestStrategy",
        description="Test strategy",
        engine_type="backtrader",
        code="class TestStrategy: pass",
        status=StrategyStatus.ACTIVE
    )
    db_session.add(strategy)
    db_session.commit()
    db_session.refresh(strategy)
    return strategy


@pytest.fixture
def test_signal(db_session: Session, test_strategy: Strategy, test_user: User):
    """Create a test signal"""
    signal = StrategySignal(
        strategy_id=test_strategy.id,
        user_id=test_user.id,
        stock_id="2330",
        signal_type="BUY",
        price=580.00,
        reason="MA crossover",
        notified=False
    )
    db_session.add(signal)
    db_session.commit()
    db_session.refresh(signal)
    return signal


class TestStrategySignalRepositoryCheckDuplicate:
    """測試 check_duplicate 方法（信號去重）"""

    def test_no_duplicate_signal(
        self,
        db_session: Session,
        test_strategy: Strategy
    ):
        """測試無重複信號時返回 False"""
        time_threshold = datetime.now(timezone.utc) - timedelta(minutes=15)

        is_duplicate = StrategySignalRepository.check_duplicate(
            db_session,
            strategy_id=test_strategy.id,
            stock_id="2330",
            signal_type="BUY",
            time_threshold=time_threshold
        )

        assert is_duplicate is False

    def test_duplicate_signal_detected(
        self,
        db_session: Session,
        test_signal: StrategySignal,
        test_strategy: Strategy
    ):
        """測試檢測到重複信號"""
        # 時間閾值設為當前時間 - 15 分鐘
        time_threshold = datetime.now(timezone.utc) - timedelta(minutes=15)

        # test_signal 剛創建，應該被檢測為重複
        is_duplicate = StrategySignalRepository.check_duplicate(
            db_session,
            strategy_id=test_strategy.id,
            stock_id="2330",
            signal_type="BUY",
            time_threshold=time_threshold
        )

        assert is_duplicate is True

    def test_different_signal_type_not_duplicate(
        self,
        db_session: Session,
        test_signal: StrategySignal,
        test_strategy: Strategy
    ):
        """測試不同信號類型不算重複"""
        time_threshold = datetime.now(timezone.utc) - timedelta(minutes=15)

        # test_signal 是 BUY，查詢 SELL 不應重複
        is_duplicate = StrategySignalRepository.check_duplicate(
            db_session,
            strategy_id=test_strategy.id,
            stock_id="2330",
            signal_type="SELL",  # 不同類型
            time_threshold=time_threshold
        )

        assert is_duplicate is False

    def test_different_stock_not_duplicate(
        self,
        db_session: Session,
        test_signal: StrategySignal,
        test_strategy: Strategy
    ):
        """測試不同股票不算重複"""
        time_threshold = datetime.now(timezone.utc) - timedelta(minutes=15)

        # test_signal 是 2330，查詢 2454 不應重複
        is_duplicate = StrategySignalRepository.check_duplicate(
            db_session,
            strategy_id=test_strategy.id,
            stock_id="2454",  # 不同股票
            signal_type="BUY",
            time_threshold=time_threshold
        )

        assert is_duplicate is False


class TestStrategySignalRepositoryCreate:
    """測試 create 方法"""

    def test_create_signal_basic(
        self,
        db_session: Session,
        test_strategy: Strategy,
        test_user: User
    ):
        """測試創建基本信號"""
        signal = StrategySignalRepository.create(
            db_session,
            strategy_id=test_strategy.id,
            user_id=test_user.id,
            stock_id="2454",
            signal_type="SELL",
            price=125.50
        )

        assert signal.id is not None
        assert signal.strategy_id == test_strategy.id
        assert signal.user_id == test_user.id
        assert signal.stock_id == "2454"
        assert signal.signal_type == "SELL"
        assert float(signal.price) == 125.50
        assert signal.notified is False
        assert signal.detected_at is not None
        assert signal.created_at is not None

    def test_create_signal_with_reason(
        self,
        db_session: Session,
        test_strategy: Strategy,
        test_user: User
    ):
        """測試創建帶原因的信號"""
        signal = StrategySignalRepository.create(
            db_session,
            strategy_id=test_strategy.id,
            user_id=test_user.id,
            stock_id="2330",
            signal_type="BUY",
            price=580.00,
            reason="RSI oversold + MACD crossover"
        )

        assert signal.reason == "RSI oversold + MACD crossover"


class TestStrategySignalRepositoryGetByUser:
    """測試 get_by_user 方法"""

    def test_get_user_signals(
        self,
        db_session: Session,
        test_user: User,
        test_strategy: Strategy
    ):
        """測試獲取用戶的所有信號"""
        # 創建多個信號
        for i in range(3):
            signal = StrategySignal(
                strategy_id=test_strategy.id,
                user_id=test_user.id,
                stock_id=f"233{i}",
                signal_type="BUY",
                price=580.00
            )
            db_session.add(signal)
        db_session.commit()

        result = StrategySignalRepository.get_by_user(
            db_session,
            test_user.id,
            skip=0,
            limit=10
        )

        assert len(result) == 3
        assert all(signal.user_id == test_user.id for signal in result)

    def test_get_user_signals_pagination(
        self,
        db_session: Session,
        test_user: User,
        test_strategy: Strategy
    ):
        """測試分頁功能"""
        # 創建 5 個信號
        for i in range(5):
            signal = StrategySignal(
                strategy_id=test_strategy.id,
                user_id=test_user.id,
                stock_id=f"233{i}",
                signal_type="BUY",
                price=580.00
            )
            db_session.add(signal)
        db_session.commit()

        # 獲取第一頁（2 條）
        page1 = StrategySignalRepository.get_by_user(
            db_session,
            test_user.id,
            skip=0,
            limit=2
        )

        assert len(page1) == 2

        # 獲取第二頁（2 條）
        page2 = StrategySignalRepository.get_by_user(
            db_session,
            test_user.id,
            skip=2,
            limit=2
        )

        assert len(page2) == 2
        # 第二頁應該是不同的信號（按時間降序）
        assert page1[0].id != page2[0].id


class TestStrategySignalRepositoryGetByStrategy:
    """測試 get_by_strategy 方法"""

    def test_get_strategy_signals(
        self,
        db_session: Session,
        test_user: User,
        test_strategy: Strategy
    ):
        """測試獲取策略的所有信號"""
        # 創建多個信號
        for i in range(3):
            signal = StrategySignal(
                strategy_id=test_strategy.id,
                user_id=test_user.id,
                stock_id=f"233{i}",
                signal_type="BUY" if i % 2 == 0 else "SELL",
                price=580.00
            )
            db_session.add(signal)
        db_session.commit()

        result = StrategySignalRepository.get_by_strategy(
            db_session,
            test_strategy.id,
            skip=0,
            limit=10
        )

        assert len(result) == 3
        assert all(signal.strategy_id == test_strategy.id for signal in result)


class TestStrategySignalRepositoryGetUnnotified:
    """測試 get_unnotified 方法"""

    def test_get_unnotified_signals(
        self,
        db_session: Session,
        test_user: User,
        test_strategy: Strategy
    ):
        """測試獲取未通知的信號"""
        # 創建已通知和未通知的信號
        notified_signal = StrategySignal(
            strategy_id=test_strategy.id,
            user_id=test_user.id,
            stock_id="2330",
            signal_type="BUY",
            price=580.00,
            notified=True,
            notified_at=datetime.now(timezone.utc)
        )
        unnotified_signal = StrategySignal(
            strategy_id=test_strategy.id,
            user_id=test_user.id,
            stock_id="2454",
            signal_type="SELL",
            price=125.50,
            notified=False
        )
        db_session.add_all([notified_signal, unnotified_signal])
        db_session.commit()

        result = StrategySignalRepository.get_unnotified(
            db_session,
            limit=10
        )

        # 應該只返回未通知的信號
        assert len(result) >= 1
        assert all(not signal.notified for signal in result)
        assert unnotified_signal.id in [s.id for s in result]
        assert notified_signal.id not in [s.id for s in result]


class TestStrategySignalRepositoryMarkAsNotified:
    """測試 mark_as_notified 方法"""

    def test_mark_signal_as_notified(
        self,
        db_session: Session,
        test_signal: StrategySignal
    ):
        """測試標記信號為已通知"""
        # 確認初始狀態
        assert test_signal.notified is False
        assert test_signal.notified_at is None

        # 標記為已通知
        updated_signal = StrategySignalRepository.mark_as_notified(
            db_session,
            test_signal
        )

        # 確認更新成功
        assert updated_signal.notified is True
        assert updated_signal.notified_at is not None
        assert isinstance(updated_signal.notified_at, datetime)


class TestStrategySignalRepositoryCount:
    """測試 count 方法"""

    def test_count_all_signals(
        self,
        db_session: Session,
        test_user: User,
        test_strategy: Strategy
    ):
        """測試統計所有信號"""
        # 創建 3 個信號
        for i in range(3):
            signal = StrategySignal(
                strategy_id=test_strategy.id,
                user_id=test_user.id,
                stock_id=f"233{i}",
                signal_type="BUY",
                price=580.00
            )
            db_session.add(signal)
        db_session.commit()

        count = StrategySignalRepository.count(db_session)

        assert count >= 3

    def test_count_by_strategy(
        self,
        db_session: Session,
        test_user: User,
        test_strategy: Strategy
    ):
        """測試統計特定策略的信號數"""
        # 創建 3 個信號
        for i in range(3):
            signal = StrategySignal(
                strategy_id=test_strategy.id,
                user_id=test_user.id,
                stock_id=f"233{i}",
                signal_type="BUY",
                price=580.00
            )
            db_session.add(signal)
        db_session.commit()

        count = StrategySignalRepository.count(
            db_session,
            strategy_id=test_strategy.id
        )

        assert count == 3

    def test_count_by_user(
        self,
        db_session: Session,
        test_user: User,
        test_strategy: Strategy
    ):
        """測試統計特定用戶的信號數"""
        # 創建 3 個信號
        for i in range(3):
            signal = StrategySignal(
                strategy_id=test_strategy.id,
                user_id=test_user.id,
                stock_id=f"233{i}",
                signal_type="BUY",
                price=580.00
            )
            db_session.add(signal)
        db_session.commit()

        count = StrategySignalRepository.count(
            db_session,
            user_id=test_user.id
        )

        assert count == 3


class TestStrategySignalRepositoryDelete:
    """測試 delete 方法"""

    def test_delete_signal(
        self,
        db_session: Session,
        test_signal: StrategySignal
    ):
        """測試刪除信號"""
        signal_id = test_signal.id

        StrategySignalRepository.delete(db_session, test_signal)

        # 確認已刪除
        deleted_signal = db_session.query(StrategySignal).filter(
            StrategySignal.id == signal_id
        ).first()
        assert deleted_signal is None
