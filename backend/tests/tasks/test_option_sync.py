"""
Unit tests for Option Sync Celery Tasks

測試選擇權同步 Celery 任務
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime
from decimal import Decimal
import pandas as pd


@pytest.fixture
def mock_db():
    """模擬資料庫 session"""
    return MagicMock()


@pytest.fixture
def mock_shioaji_client():
    """模擬 Shioaji 客戶端"""
    client = MagicMock()
    client.is_available.return_value = True
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    return client


@pytest.fixture
def mock_option_chain():
    """模擬 option chain DataFrame"""
    return pd.DataFrame({
        'contract_id': ['TXO202512C23000', 'TXO202512P23000'],
        'underlying_id': ['TX', 'TX'],
        'underlying_type': ['FUTURES', 'FUTURES'],
        'option_type': ['CALL', 'PUT'],
        'strike_price': [Decimal('23000'), Decimal('23000')],
        'expiry_date': [date(2025, 12, 17), date(2025, 12, 17)],
        'close': [150.5, 120.3],
        'volume': [1000, 800],
        'open_interest': [5000, 4500]
    })


class TestSyncOptionDailyFactorsLogic:
    """測試 sync_option_daily_factors 任務"""

    @patch('app.tasks.option_sync.OptionDailyFactorRepository')
    @patch('app.tasks.option_sync.OptionSyncConfigRepository')
    @patch('app.tasks.option_sync.OptionFactorCalculator')
    @patch('app.tasks.option_sync.ShioajiOptionDataSource')
    @patch('app.tasks.option_sync.ShioajiClient')
    @patch('app.tasks.option_sync.get_db')
    def test_sync_success_all_underlyings(
        self,
        mock_get_db,
        MockShioajiClient,
        MockDataSource,
        MockCalculator,
        MockSyncConfig,
        MockFactorRepo,
        mock_shioaji_client,
        mock_db
    ):
        """測試成功同步所有標的"""
        from app.tasks.option_sync import sync_option_daily_factors
        
        # 設定 mock
        mock_get_db.return_value = iter([mock_db])
        MockShioajiClient.return_value = mock_shioaji_client
        
        MockSyncConfig.get_current_stage.return_value = 1
        MockSyncConfig.get_enabled_underlyings.return_value = ['TX', 'MTX']
        
        # 模擬計算器返回
        mock_calculator_instance = MockCalculator.return_value
        mock_calculator_instance.calculate_daily_factors.return_value = {
            'pcr_volume': Decimal('1.2'),
            'pcr_open_interest': Decimal('1.1'),
            'atm_iv': Decimal('0.15'),
            'data_quality_score': Decimal('0.95'),
            'calculation_version': '1.0.0'
        }
        
        # 模擬保存成功
        MockFactorRepo.upsert.return_value = Mock()
        
        # 使用 apply() 同步調用任務（不會觸發 Celery）
        result = sync_option_daily_factors.apply(
            args=[],
            kwargs={'underlying_ids': ['TX', 'MTX'], 'target_date': '2024-12-15'}
        ).get()
        
        # 驗證結果
        assert result['status'] == 'success'
        assert result['statistics']['total_underlyings'] == 2
        assert result['statistics']['success_count'] == 2
        assert result['statistics']['error_count'] == 0
        assert result['statistics']['factors_saved'] == 2
        
        # 驗證調用
        assert mock_calculator_instance.calculate_daily_factors.call_count == 2
        assert MockFactorRepo.upsert.call_count == 2

    @patch('app.tasks.option_sync.get_db')
    def test_sync_invalid_date_format(self, mock_get_db, mock_db):
        """測試無效的日期格式"""
        from app.tasks.option_sync import sync_option_daily_factors
        
        mock_get_db.return_value = iter([mock_db])
        
        result = sync_option_daily_factors.apply(
            args=[],
            kwargs={'target_date': 'invalid-date'}
        ).get()
        
        assert result['status'] == 'error'
        assert 'Invalid date format' in result['message']

    @patch('app.tasks.option_sync.OptionDailyFactorRepository')
    @patch('app.tasks.option_sync.OptionSyncConfigRepository')
    @patch('app.tasks.option_sync.OptionFactorCalculator')
    @patch('app.tasks.option_sync.ShioajiOptionDataSource')
    @patch('app.tasks.option_sync.ShioajiClient')
    @patch('app.tasks.option_sync.get_db')
    def test_sync_partial_success(
        self,
        mock_get_db,
        MockShioajiClient,
        MockDataSource,
        MockCalculator,
        MockSyncConfig,
        MockFactorRepo,
        mock_shioaji_client,
        mock_db
    ):
        """測試部分成功（某些標的失敗）"""
        from app.tasks.option_sync import sync_option_daily_factors
        
        mock_get_db.return_value = iter([mock_db])
        MockShioajiClient.return_value = mock_shioaji_client
        
        MockSyncConfig.get_current_stage.return_value = 1
        MockSyncConfig.get_enabled_underlyings.return_value = ['TX', 'MTX', 'EO']
        
        # 模擬計算器：TX 成功，MTX 失敗，EO 成功
        mock_calculator_instance = MockCalculator.return_value
        def calc_side_effect(underlying_id, sync_date):
            if underlying_id == 'MTX':
                raise Exception("Calculation failed for MTX")
            return {
                'pcr_volume': Decimal('1.2'),
                'data_quality_score': Decimal('0.95')
            }
        
        mock_calculator_instance.calculate_daily_factors.side_effect = calc_side_effect
        MockFactorRepo.upsert.return_value = Mock()
        
        result = sync_option_daily_factors.apply().get()
        
        assert result['status'] == 'partial_success'
        assert result['statistics']['total_underlyings'] == 3
        assert result['statistics']['success_count'] == 2
        assert result['statistics']['error_count'] == 1
        assert 'MTX' in result['statistics']['errors'][0]

    @patch('app.tasks.option_sync.OptionDailyFactorRepository')
    @patch('app.tasks.option_sync.OptionSyncConfigRepository')
    @patch('app.tasks.option_sync.OptionFactorCalculator')
    @patch('app.tasks.option_sync.ShioajiOptionDataSource')
    @patch('app.tasks.option_sync.ShioajiClient')
    @patch('app.tasks.option_sync.get_db')
    def test_sync_low_quality_data_skip(
        self,
        mock_get_db,
        MockShioajiClient,
        MockDataSource,
        MockCalculator,
        MockSyncConfig,
        MockFactorRepo,
        mock_shioaji_client,
        mock_db
    ):
        """測試低品質數據被跳過"""
        from app.tasks.option_sync import sync_option_daily_factors
        
        mock_get_db.return_value = iter([mock_db])
        MockShioajiClient.return_value = mock_shioaji_client
        
        MockSyncConfig.get_current_stage.return_value = 1
        MockSyncConfig.get_enabled_underlyings.return_value = ['TX']
        
        # 返回非常低品質的數據（< 0.3）
        mock_calculator_instance = MockCalculator.return_value
        mock_calculator_instance.calculate_daily_factors.return_value = {
            'pcr_volume': Decimal('1.2'),
            'data_quality_score': Decimal('0.2')  # 低於 0.3
        }
        
        result = sync_option_daily_factors.apply().get()
        
        # 應該跳過保存
        assert result['statistics']['error_count'] == 1
        assert 'Very low quality' in result['statistics']['errors'][0]
        MockFactorRepo.upsert.assert_not_called()

    @patch('app.tasks.option_sync.OptionDailyFactorRepository')
    @patch('app.tasks.option_sync.OptionSyncConfigRepository')
    @patch('app.tasks.option_sync.OptionFactorCalculator')
    @patch('app.tasks.option_sync.ShioajiOptionDataSource')
    @patch('app.tasks.option_sync.ShioajiClient')
    @patch('app.tasks.option_sync.get_db')
    def test_sync_low_quality_warning(
        self,
        mock_get_db,
        MockShioajiClient,
        MockDataSource,
        MockCalculator,
        MockSyncConfig,
        MockFactorRepo,
        mock_shioaji_client,
        mock_db
    ):
        """測試中等品質數據產生警告但仍保存"""
        from app.tasks.option_sync import sync_option_daily_factors
        
        mock_get_db.return_value = iter([mock_db])
        MockShioajiClient.return_value = mock_shioaji_client
        
        MockSyncConfig.get_current_stage.return_value = 1
        MockSyncConfig.get_enabled_underlyings.return_value = ['TX']
        
        # 返回中等品質數據（0.3 ~ 0.7）
        mock_calculator_instance = MockCalculator.return_value
        mock_calculator_instance.calculate_daily_factors.return_value = {
            'pcr_volume': Decimal('1.2'),
            'data_quality_score': Decimal('0.5')  # 0.3 < x < 0.7
        }
        
        MockFactorRepo.upsert.return_value = Mock()
        
        result = sync_option_daily_factors.apply().get()
        
        # 應該保存但有警告
        assert result['statistics']['success_count'] == 1
        assert result['statistics']['low_quality_count'] == 1
        assert len(result['statistics']['warnings']) == 1
        MockFactorRepo.upsert.assert_called_once()

    @patch('app.tasks.option_sync.OptionDailyFactorRepository')
    @patch('app.tasks.option_sync.OptionSyncConfigRepository')
    @patch('app.tasks.option_sync.OptionFactorCalculator')
    @patch('app.tasks.option_sync.ShioajiOptionDataSource')
    @patch('app.tasks.option_sync.ShioajiClient')
    @patch('app.tasks.option_sync.get_db')
    def test_sync_database_save_failure(
        self,
        mock_get_db,
        MockShioajiClient,
        MockDataSource,
        MockCalculator,
        MockSyncConfig,
        MockFactorRepo,
        mock_shioaji_client,
        mock_db
    ):
        """測試資料庫保存失敗"""
        from app.tasks.option_sync import sync_option_daily_factors
        
        mock_get_db.return_value = iter([mock_db])
        MockShioajiClient.return_value = mock_shioaji_client
        
        MockSyncConfig.get_current_stage.return_value = 1
        MockSyncConfig.get_enabled_underlyings.return_value = ['TX']
        
        mock_calculator_instance = MockCalculator.return_value
        mock_calculator_instance.calculate_daily_factors.return_value = {
            'pcr_volume': Decimal('1.2'),
            'data_quality_score': Decimal('0.95')
        }
        
        # 模擬保存失敗
        MockFactorRepo.upsert.side_effect = Exception("Database save failed")
        
        result = sync_option_daily_factors.apply().get()
        
        assert result['statistics']['error_count'] == 1
        assert 'DB save failed' in result['statistics']['errors'][0]


class TestRegisterOptionContractsLogic:
    """測試 register_option_contracts 任務"""

    @patch('app.tasks.option_sync.OptionContractRepository')
    @patch('app.tasks.option_sync.OptionSyncConfigRepository')
    @patch('app.tasks.option_sync.ShioajiOptionDataSource')
    @patch('app.tasks.option_sync.ShioajiClient')
    @patch('app.tasks.option_sync.get_db')
    def test_register_contracts_success(
        self,
        mock_get_db,
        MockShioajiClient,
        MockDataSource,
        MockSyncConfig,
        MockContractRepo,
        mock_shioaji_client,
        mock_option_chain,
        mock_db
    ):
        """測試成功註冊合約"""
        from app.tasks.option_sync import register_option_contracts
        
        mock_get_db.return_value = iter([mock_db])
        MockShioajiClient.return_value = mock_shioaji_client
        
        MockSyncConfig.get_enabled_underlyings.return_value = ['TX']
        
        # 模擬 data source 返回 option chain
        mock_data_source_instance = MockDataSource.return_value
        mock_data_source_instance.get_option_chain.return_value = mock_option_chain
        
        # 模擬合約不存在（新註冊）
        MockContractRepo.get_by_id.return_value = None
        MockContractRepo.create.return_value = Mock()
        
        result = register_option_contracts.apply(
            kwargs={'underlying_ids': ['TX']}
        ).get()
        
        assert result['status'] == 'success'
        assert result['statistics']['total_contracts_registered'] == 2
        assert result['statistics']['total_contracts_updated'] == 0
        assert MockContractRepo.create.call_count == 2

    @patch('app.tasks.option_sync.OptionContractRepository')
    @patch('app.tasks.option_sync.OptionSyncConfigRepository')
    @patch('app.tasks.option_sync.ShioajiOptionDataSource')
    @patch('app.tasks.option_sync.ShioajiClient')
    @patch('app.tasks.option_sync.get_db')
    def test_register_contracts_update_existing(
        self,
        mock_get_db,
        MockShioajiClient,
        MockDataSource,
        MockSyncConfig,
        MockContractRepo,
        mock_shioaji_client,
        mock_option_chain,
        mock_db
    ):
        """測試更新已存在的合約"""
        from app.tasks.option_sync import register_option_contracts
        
        mock_get_db.return_value = iter([mock_db])
        MockShioajiClient.return_value = mock_shioaji_client
        
        MockSyncConfig.get_enabled_underlyings.return_value = ['TX']
        
        mock_data_source_instance = MockDataSource.return_value
        mock_data_source_instance.get_option_chain.return_value = mock_option_chain
        
        # 模擬合約已存在
        MockContractRepo.get_by_id.return_value = Mock()
        
        result = register_option_contracts.apply(
            kwargs={'underlying_ids': ['TX']}
        ).get()
        
        assert result['status'] == 'success'
        assert result['statistics']['total_contracts_registered'] == 0
        assert result['statistics']['total_contracts_updated'] == 2

    @patch('app.tasks.option_sync.OptionSyncConfigRepository')
    @patch('app.tasks.option_sync.ShioajiClient')
    @patch('app.tasks.option_sync.get_db')
    def test_register_contracts_shioaji_unavailable(
        self,
        mock_get_db,
        MockShioajiClient,
        MockSyncConfig,
        mock_db
    ):
        """測試 Shioaji 客戶端不可用"""
        from app.tasks.option_sync import register_option_contracts
        
        mock_get_db.return_value = iter([mock_db])
        
        MockSyncConfig.get_enabled_underlyings.return_value = ['TX']
        
        # 模擬客戶端不可用
        mock_client = MagicMock()
        mock_client.is_available.return_value = False
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        MockShioajiClient.return_value = mock_client
        
        result = register_option_contracts.apply().get()
        
        assert result['status'] == 'error'
        assert 'Shioaji client not available' in result['message']

    @patch('app.tasks.option_sync.OptionContractRepository')
    @patch('app.tasks.option_sync.OptionSyncConfigRepository')
    @patch('app.tasks.option_sync.ShioajiOptionDataSource')
    @patch('app.tasks.option_sync.ShioajiClient')
    @patch('app.tasks.option_sync.get_db')
    def test_register_contracts_no_contracts_found(
        self,
        mock_get_db,
        MockShioajiClient,
        MockDataSource,
        MockSyncConfig,
        MockContractRepo,
        mock_shioaji_client,
        mock_db
    ):
        """測試沒有找到合約"""
        from app.tasks.option_sync import register_option_contracts
        
        mock_get_db.return_value = iter([mock_db])
        MockShioajiClient.return_value = mock_shioaji_client
        
        MockSyncConfig.get_enabled_underlyings.return_value = ['TX']
        
        # 返回空 DataFrame
        mock_data_source_instance = MockDataSource.return_value
        mock_data_source_instance.get_option_chain.return_value = pd.DataFrame()
        
        result = register_option_contracts.apply(
            kwargs={'underlying_ids': ['TX']}
        ).get()
        
        assert result['status'] == 'success'
        assert result['statistics']['total_contracts_registered'] == 0
        MockContractRepo.create.assert_not_called()

    @patch('app.tasks.option_sync.get_db')
    def test_register_contracts_fatal_error(self, mock_get_db):
        """測試致命錯誤"""
        from app.tasks.option_sync import register_option_contracts
        
        mock_get_db.side_effect = Exception("Fatal database error")
        
        result = register_option_contracts.apply().get()
        
        assert result['status'] == 'error'
        assert 'Fatal error' in result['message']
