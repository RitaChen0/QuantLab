"""
Unit tests for Option API endpoints

測試選擇權 API 端點
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.api.dependencies import get_current_user, get_db


# 測試用的假用戶
def get_test_user():
    """返回測試用戶"""
    user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        is_active=True,
        is_superuser=False
    )
    return user


# 測試用的假資料庫 session
def get_test_db():
    """返回測試資料庫 session"""
    db = MagicMock(spec=Session)
    return db


@pytest.fixture
def client():
    """測試客戶端（使用 dependency override）"""
    # Override dependencies
    app.dependency_overrides[get_current_user] = get_test_user
    app.dependency_overrides[get_db] = get_test_db

    test_client = TestClient(app)

    yield test_client

    # 清理 overrides
    app.dependency_overrides.clear()


@pytest.fixture
def mock_user():
    """模擬用戶"""
    return get_test_user()


class TestGetStageInfo:
    """測試 GET /api/v1/options/stage"""

    @patch('app.services.option_calculator.get_available_factors')
    @patch('app.api.v1.options.OptionSyncConfigRepository')
    def test_get_stage_info_success(self, MockRepo, mock_factors, client):
        """測試成功獲取階段資訊"""
        # 模擬 Repository 靜態方法回應
        MockRepo.get_current_stage.return_value = 1
        MockRepo.get_enabled_underlyings.return_value = ['TX', 'MTX']
        MockRepo.is_minute_sync_enabled.return_value = False
        MockRepo.is_greeks_calculation_enabled.return_value = False

        # 模擬可用因子 - 返回dict，key是因子ID，value是因子metadata
        mock_factors.return_value = {
            'pcr_volume': 'PCR Volume',
            'pcr_open_interest': 'PCR OI',
            'atm_iv': 'ATM IV'
        }

        response = client.get("/api/v1/options/stage")

        assert response.status_code == 200
        data = response.json()
        assert data['stage'] == 1
        assert 'TX' in data['enabled_underlyings']
        assert data['sync_minute_data'] is False
        assert data['calculate_greeks'] is False
        assert len(data['available_factors']) == 3

    def test_get_stage_info_unauthorized(self):
        """測試未授權訪問"""
        # 不使用 dependency override 的客戶端
        client_no_auth = TestClient(app)
        response = client_no_auth.get("/api/v1/options/stage")
        assert response.status_code == 403  # 沒有 Bearer token

    @patch('app.api.v1.options.OptionSyncConfigRepository')
    def test_get_stage_info_error_handling(self, MockRepo, client):
        """測試錯誤處理"""
        MockRepo.get_current_stage.side_effect = Exception("Database error")

        response = client.get("/api/v1/options/stage")

        assert response.status_code == 500


class TestGetContracts:
    """測試 GET /api/v1/options/contracts"""

    @patch('app.api.v1.options.OptionContractRepository')
    def test_get_contracts_success(self, MockRepo, client):
        """測試成功獲取合約列表"""
        # 模擬合約
        mock_contract = Mock()
        mock_contract.contract_id = 'TXO202512C23000'
        mock_contract.underlying_id = 'TX'
        mock_contract.option_type = 'CALL'
        mock_contract.strike_price = Decimal('23000')
        mock_contract.expiry_date = date(2025, 12, 17)
        mock_contract.is_active = 'active'
        mock_contract.created_at = datetime(2024, 12, 1)
        mock_contract.updated_at = datetime(2024, 12, 1)
        mock_contract.underlying_type = 'FUTURES'
        mock_contract.settlement_price = None
        mock_contract.contract_size = 1
        mock_contract.tick_size = Decimal('0.01')

        MockRepo.get_all.return_value = [mock_contract]

        response = client.get("/api/v1/options/contracts")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]['contract_id'] == 'TXO202512C23000'

    @patch('app.api.v1.options.OptionContractRepository')
    def test_get_contracts_with_filters(self, MockRepo, client):
        """測試帶篩選條件的合約查詢"""
        MockRepo.get_all.return_value = []

        response = client.get(
            "/api/v1/options/contracts",
            params={
                'underlying_id': 'TX',
                'option_type': 'CALL',
                'is_active': 'active'
            }
        )

        assert response.status_code == 200
        MockRepo.get_all.assert_called_once()

    @patch('app.api.v1.options.OptionContractRepository')
    def test_get_contracts_pagination(self, MockRepo, client):
        """測試分頁功能"""
        MockRepo.get_all.return_value = []

        response = client.get(
            "/api/v1/options/contracts",
            params={'skip': 10, 'limit': 50}
        )

        assert response.status_code == 200


class TestGetExpiryDates:
    """測試 GET /api/v1/options/contracts/{underlying_id}/expiries"""

    @patch('app.api.v1.options.OptionContractRepository')
    def test_get_expiry_dates_success(self, MockRepo, client):
        """測試成功獲取到期日列表"""
        MockRepo.get_expiry_dates.return_value = [
            date(2025, 12, 17),
            date(2026, 1, 21),
            date(2026, 2, 18)
        ]

        response = client.get("/api/v1/options/contracts/TX/expiries")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert '2025-12-17' in data

    @patch('app.api.v1.options.OptionContractRepository')
    def test_get_expiry_dates_empty(self, MockRepo, client):
        """測試無到期日的情況"""
        MockRepo.get_expiry_dates.return_value = []

        response = client.get("/api/v1/options/contracts/TX/expiries")

        assert response.status_code == 200
        assert response.json() == []


class TestGetOptionChain:
    """測試 GET /api/v1/options/chain/{underlying_id}"""

    @patch('app.api.v1.options.OptionContractRepository')
    def test_get_option_chain_success(self, MockRepo, client):
        """測試成功獲取 option chain"""
        # 模擬 CALL 合約
        call_contract = Mock()
        call_contract.contract_id = 'TXO202512C23000'
        call_contract.option_type = 'CALL'
        call_contract.strike_price = Decimal('23000')

        # 模擬 PUT 合約
        put_contract = Mock()
        put_contract.contract_id = 'TXO202512P23000'
        put_contract.option_type = 'PUT'
        put_contract.strike_price = Decimal('23000')

        MockRepo.get_by_underlying_and_expiry.return_value = [
            call_contract, put_contract
        ]

        response = client.get(
            "/api/v1/options/chain/TX",
            params={'expiry_date': '2025-12-17'}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['underlying_id'] == 'TX'
        assert len(data['calls']) == 1
        assert len(data['puts']) == 1

    @patch('app.api.v1.options.OptionContractRepository')
    def test_get_option_chain_not_found(self, MockRepo, client):
        """測試無合約的情況"""
        MockRepo.get_by_underlying_and_expiry.return_value = []

        response = client.get(
            "/api/v1/options/chain/TX",
            params={'expiry_date': '2025-12-17'}
        )

        assert response.status_code == 404


class TestGetDailyFactors:
    """測試 GET /api/v1/options/factors/{underlying_id}"""

    @patch('app.api.v1.options.OptionDailyFactorRepository')
    def test_get_daily_factors_success(self, MockRepo, client):
        """測試成功獲取每日因子"""
        # 模擬因子
        mock_factor = Mock()
        mock_factor.underlying_id = 'TX'
        mock_factor.date = date(2024, 12, 15)
        mock_factor.pcr_volume = Decimal('1.2')
        mock_factor.pcr_open_interest = Decimal('1.1')
        mock_factor.atm_iv = Decimal('0.15')
        mock_factor.created_at = datetime(2024, 12, 15)
        mock_factor.data_quality_score = Decimal('0.95')
        mock_factor.calculation_version = '1.0.0'
        # 階段二因子
        mock_factor.iv_skew = None
        mock_factor.iv_term_structure = None
        mock_factor.max_pain_strike = None
        mock_factor.total_call_oi = None
        mock_factor.total_put_oi = None
        # 階段三因子
        mock_factor.avg_call_delta = None
        mock_factor.avg_put_delta = None
        mock_factor.gamma_exposure = None
        mock_factor.vanna_exposure = None

        MockRepo.get_by_underlying.return_value = [mock_factor]

        response = client.get("/api/v1/options/factors/TX")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]['underlying_id'] == 'TX'

    @patch('app.api.v1.options.OptionDailyFactorRepository')
    def test_get_daily_factors_with_date_range(self, MockRepo, client):
        """測試帶日期範圍的查詢"""
        MockRepo.get_by_underlying.return_value = []

        response = client.get(
            "/api/v1/options/factors/TX",
            params={
                'start_date': '2024-12-01',
                'end_date': '2024-12-15',
                'limit': 50
            }
        )

        assert response.status_code == 200


class TestGetLatestFactor:
    """測試 GET /api/v1/options/factors/{underlying_id}/latest"""

    @patch('app.api.v1.options.OptionDailyFactorRepository')
    def test_get_latest_factor_success(self, MockRepo, client):
        """測試成功獲取最新因子"""
        mock_factor = Mock()
        mock_factor.underlying_id = 'TX'
        mock_factor.date = date(2024, 12, 15)
        mock_factor.pcr_volume = Decimal('1.2')
        mock_factor.created_at = datetime(2024, 12, 15)
        mock_factor.data_quality_score = Decimal('0.95')
        mock_factor.calculation_version = '1.0.0'
        # 添加所有階段因子
        for field in ['pcr_open_interest', 'atm_iv', 'iv_skew', 'iv_term_structure',
                     'max_pain_strike', 'total_call_oi', 'total_put_oi',
                     'avg_call_delta', 'avg_put_delta', 'gamma_exposure', 'vanna_exposure']:
            setattr(mock_factor, field, None)

        MockRepo.get_latest.return_value = mock_factor

        response = client.get("/api/v1/options/factors/TX/latest")

        assert response.status_code == 200
        data = response.json()
        assert data['underlying_id'] == 'TX'

    @patch('app.api.v1.options.OptionDailyFactorRepository')
    def test_get_latest_factor_not_found(self, MockRepo, client):
        """測試無數據的情況"""
        MockRepo.get_latest.return_value = None

        response = client.get("/api/v1/options/factors/TX/latest")

        assert response.status_code == 404


class TestGetFactorSummary:
    """測試 GET /api/v1/options/factors/{underlying_id}/summary"""

    @patch('app.api.v1.options.OptionDailyFactorRepository')
    def test_get_factor_summary_bearish(self, MockRepo, client):
        """測試看跌情緒的因子摘要"""
        mock_factor = Mock()
        mock_factor.underlying_id = 'TX'
        mock_factor.date = date(2024, 12, 15)
        mock_factor.pcr_volume = Decimal('1.3')  # > 1.2 → bearish
        mock_factor.pcr_open_interest = Decimal('1.2')
        mock_factor.atm_iv = Decimal('0.15')
        mock_factor.iv_skew = None
        mock_factor.max_pain_strike = None
        mock_factor.total_call_oi = 10000
        mock_factor.total_put_oi = 13000

        MockRepo.get_latest.return_value = mock_factor

        response = client.get("/api/v1/options/factors/TX/summary")

        assert response.status_code == 200
        data = response.json()
        assert data['sentiment'] == 'bearish'
        assert data['total_oi'] == 23000

    @patch('app.api.v1.options.OptionDailyFactorRepository')
    def test_get_factor_summary_bullish(self, MockRepo, client):
        """測試看漲情緒的因子摘要"""
        mock_factor = Mock()
        mock_factor.underlying_id = 'TX'
        mock_factor.date = date(2024, 12, 15)
        mock_factor.pcr_volume = Decimal('0.7')  # < 0.8 → bullish
        mock_factor.pcr_open_interest = Decimal('0.75')
        mock_factor.atm_iv = Decimal('0.12')
        mock_factor.iv_skew = None
        mock_factor.max_pain_strike = None
        mock_factor.total_call_oi = 15000
        mock_factor.total_put_oi = 10500

        MockRepo.get_latest.return_value = mock_factor

        response = client.get("/api/v1/options/factors/TX/summary")

        assert response.status_code == 200
        data = response.json()
        assert data['sentiment'] == 'bullish'

    @patch('app.api.v1.options.OptionDailyFactorRepository')
    def test_get_factor_summary_with_target_date(self, MockRepo, client):
        """測試指定日期的因子摘要"""
        mock_factor = Mock()
        mock_factor.underlying_id = 'TX'
        mock_factor.date = date(2024, 12, 10)
        mock_factor.pcr_volume = Decimal('1.0')
        mock_factor.pcr_open_interest = Decimal('0.95')
        mock_factor.atm_iv = Decimal('0.13')
        mock_factor.iv_skew = None
        mock_factor.max_pain_strike = None
        mock_factor.total_call_oi = None
        mock_factor.total_put_oi = None

        MockRepo.get_by_key.return_value = mock_factor

        response = client.get(
            "/api/v1/options/factors/TX/summary",
            params={'target_date': '2024-12-10'}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['sentiment'] == 'neutral'


class TestGetSyncStatus:
    """測試 GET /api/v1/options/sync-status"""

    @patch('app.api.v1.options.OptionContractRepository')
    @patch('app.api.v1.options.OptionDailyFactorRepository')
    @patch('app.api.v1.options.OptionSyncConfigRepository')
    def test_get_sync_status_success(self, MockConfigRepo, MockFactorRepo,
                                     MockContractRepo, client):
        """測試成功獲取同步狀態"""
        MockConfigRepo.get_enabled_underlyings.return_value = ['TX', 'MTX']
        MockConfigRepo.get_current_stage.return_value = 1

        MockFactorRepo.get_latest_date.return_value = date(2024, 12, 15)
        MockContractRepo.count.return_value = 100

        mock_factor = Mock()
        mock_factor.data_quality_score = Decimal('0.95')
        MockFactorRepo.get_latest.return_value = mock_factor

        response = client.get("/api/v1/options/sync-status")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]['underlying_id'] in ['TX', 'MTX']
        assert data[0]['stage'] == 1
