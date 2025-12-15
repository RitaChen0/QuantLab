"""
Unit tests for Option Data Source

測試選擇權資料源的各項功能
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from datetime import date
import pandas as pd

from app.services.option_data_source import (
    OptionDataSource,
    ShioajiOptionDataSource,
    QlibOptionDataSource
)


class TestShioajiOptionDataSourceInit:
    """測試 ShioajiOptionDataSource 初始化"""

    def test_init_with_valid_client(self):
        """測試使用有效客戶端初始化"""
        mock_client = Mock()
        mock_client._api = Mock()

        data_source = ShioajiOptionDataSource(mock_client)

        assert data_source.client == mock_client
        assert data_source._api == mock_client._api

    def test_init_with_none_client(self):
        """測試使用 None 客戶端初始化"""
        data_source = ShioajiOptionDataSource(None)

        assert data_source.client is None
        assert data_source._api is None

    def test_is_available_with_valid_client(self):
        """測試客戶端可用性檢查（有效）"""
        mock_client = Mock()
        mock_client.is_available.return_value = True

        data_source = ShioajiOptionDataSource(mock_client)

        assert data_source.is_available() is True
        mock_client.is_available.assert_called_once()

    def test_is_available_with_unavailable_client(self):
        """測試客戶端可用性檢查（不可用）"""
        mock_client = Mock()
        mock_client.is_available.return_value = False

        data_source = ShioajiOptionDataSource(mock_client)

        assert data_source.is_available() is False

    def test_is_available_with_none_client(self):
        """測試客戶端可用性檢查（None）"""
        data_source = ShioajiOptionDataSource(None)

        # 當 client 為 None 時，is_available() 會嘗試調用 None.is_available()
        # 這會導致 AttributeError，但代碼中有 self.client and self.client.is_available()
        # 所以會短路返回 None (falsy)
        result = data_source.is_available()
        # 檢查結果為 falsy（可能是 None 或 False）
        assert not result


class TestGetOptionContracts:
    """測試 _get_option_contracts 方法"""

    def create_mock_contract(self, code='TXO202512C23000', strike=23000):
        """創建模擬合約物件"""
        contract = Mock()
        contract.code = code
        contract.strike_price = strike
        contract.option_right = 'Call'
        contract.delivery_date = '2025-12-17'
        return contract

    def test_get_tx_contracts_with_iter(self):
        """測試獲取 TX 選擇權（使用 __iter__）"""
        mock_client = Mock()
        mock_api = Mock()

        # 模擬 TXO 合約結構（可迭代）
        contracts = [
            self.create_mock_contract('TXO202512C23000'),
            self.create_mock_contract('TXO202512P23000'),
            self.create_mock_contract('TXO202512C23100'),
        ]

        mock_txo = Mock()
        mock_txo.__iter__ = Mock(return_value=iter(contracts))

        mock_api.Contracts.Options.TXO = mock_txo
        mock_client._api = mock_api

        data_source = ShioajiOptionDataSource(mock_client)
        result = data_source._get_option_contracts('TX')

        assert len(result) == 3
        assert result[0].code == 'TXO202512C23000'

    def test_get_tx_contracts_with_values(self):
        """測試獲取 TX 選擇權（使用 values()）"""
        mock_client = Mock()
        mock_api = Mock()

        contracts = [
            self.create_mock_contract('TXO202512C23000'),
            self.create_mock_contract('TXO202512P23000'),
        ]

        mock_txo = Mock()
        # 移除 __iter__，添加 values()
        del mock_txo.__iter__
        mock_txo.values = Mock(return_value=contracts)

        mock_api.Contracts.Options.TXO = mock_txo
        mock_client._api = mock_api

        data_source = ShioajiOptionDataSource(mock_client)
        result = data_source._get_option_contracts('TX')

        assert len(result) == 2

    def test_get_tx_contracts_with_items(self):
        """測試獲取 TX 選擇權（使用 items()）"""
        mock_client = Mock()
        mock_api = Mock()

        contracts = [
            self.create_mock_contract('TXO202512C23000'),
        ]

        # 使用 spec 創建受限的 Mock，只包含 items 方法
        mock_txo = Mock(spec=['items'])
        mock_txo.items = Mock(return_value=[('key1', contracts[0])])

        mock_api.Contracts.Options.TXO = mock_txo
        mock_client._api = mock_api

        data_source = ShioajiOptionDataSource(mock_client)
        result = data_source._get_option_contracts('TX')

        assert len(result) == 1

    def test_get_mtx_contracts(self):
        """測試獲取 MTX 選擇權"""
        mock_client = Mock()
        mock_api = Mock()

        contracts = [
            self.create_mock_contract('MXO202512C23000'),
        ]

        mock_mxo = Mock()
        mock_mxo.__iter__ = Mock(return_value=iter(contracts))

        mock_api.Contracts.Options.MXO = mock_mxo
        mock_api.Contracts.Options.TXO = Mock()
        mock_client._api = mock_api

        data_source = ShioajiOptionDataSource(mock_client)
        result = data_source._get_option_contracts('MTX')

        assert len(result) == 1
        assert result[0].code == 'MXO202512C23000'

    def test_get_mtx_contracts_not_available(self):
        """測試 MXO 不可用的情況"""
        mock_client = Mock()
        mock_api = Mock()

        # MXO 不存在
        mock_api.Contracts.Options = Mock(spec=['TXO'])
        mock_client._api = mock_api

        data_source = ShioajiOptionDataSource(mock_client)
        result = data_source._get_option_contracts('MTX')

        assert len(result) == 0

    def test_get_contracts_unsupported_underlying(self):
        """測試不支援的標的（個股選擇權）"""
        mock_client = Mock()
        mock_client._api = Mock()

        data_source = ShioajiOptionDataSource(mock_client)
        result = data_source._get_option_contracts('2330')

        assert len(result) == 0

    def test_get_contracts_no_api(self):
        """測試無 API 的情況"""
        data_source = ShioajiOptionDataSource(None)
        result = data_source._get_option_contracts('TX')

        assert len(result) == 0


class TestParseContract:
    """測試 _parse_contract 方法"""

    def test_parse_txo_call_contract(self):
        """測試解析 TXO CALL 合約"""
        mock_client = Mock()
        data_source = ShioajiOptionDataSource(mock_client)

        contract = Mock()
        contract.code = 'TXO202512C23000'
        contract.strike_price = 23000
        contract.option_right = 'Call'
        contract.delivery_date = '2025-12-17'

        result = data_source._parse_contract(contract)

        assert result is not None
        assert result['contract_id'] == 'TXO202512C23000'
        assert result['underlying_id'] == 'TX'
        assert result['underlying_type'] == 'FUTURES'
        assert result['option_type'] == 'CALL'
        assert result['strike_price'] == 23000
        assert result['expiry_date'] == '2025-12-17'

    def test_parse_txo_put_contract(self):
        """測試解析 TXO PUT 合約"""
        mock_client = Mock()
        data_source = ShioajiOptionDataSource(mock_client)

        contract = Mock()
        contract.code = 'TXO202512P23000'
        contract.strike_price = 23000
        contract.option_right = 'Put'
        contract.delivery_date = '2025-12-17'

        result = data_source._parse_contract(contract)

        assert result['option_type'] == 'PUT'

    def test_parse_mxo_contract(self):
        """測試解析 MXO 合約"""
        mock_client = Mock()
        data_source = ShioajiOptionDataSource(mock_client)

        contract = Mock()
        contract.code = 'MXO202512C23000'
        contract.strike_price = 23000
        contract.option_right = 'Call'
        contract.delivery_date = '2025-12-17'

        result = data_source._parse_contract(contract)

        assert result['underlying_id'] == 'MTX'
        assert result['underlying_type'] == 'FUTURES'

    def test_parse_contract_without_option_right(self):
        """測試解析無 option_right 屬性的合約（從代碼推斷）"""
        mock_client = Mock()
        data_source = ShioajiOptionDataSource(mock_client)

        contract = Mock()
        contract.code = 'TXO202512C23000'
        contract.strike_price = 23000
        contract.delivery_date = '2025-12-17'
        # 移除 option_right 屬性
        del contract.option_right

        result = data_source._parse_contract(contract)

        # 應從代碼中推斷為 CALL（因為有 'C'）
        assert result['option_type'] == 'CALL'

    def test_parse_unsupported_contract(self):
        """測試解析不支援的合約（個股選擇權）"""
        mock_client = Mock()
        data_source = ShioajiOptionDataSource(mock_client)

        contract = Mock()
        contract.code = '2330O202512C600'
        contract.strike_price = 600
        contract.option_right = 'Call'

        result = data_source._parse_contract(contract)

        # 個股選擇權應返回 None
        assert result is None

    def test_parse_contract_error_handling(self):
        """測試解析合約時的錯誤處理"""
        mock_client = Mock()
        data_source = ShioajiOptionDataSource(mock_client)

        # 缺少必要屬性的合約
        contract = Mock()
        contract.code = 'TXO202512C23000'
        # 缺少 strike_price
        del contract.strike_price

        result = data_source._parse_contract(contract)

        # 應返回 None（錯誤處理）
        assert result is None


class TestGetContractSnapshot:
    """測試 _get_contract_snapshot 方法"""

    def test_get_snapshot_success(self):
        """測試成功獲取快照"""
        mock_client = Mock()
        mock_api = Mock()

        # 模擬 snapshot 數據
        snapshot_data = Mock()
        snapshot_data.close = 150.5
        snapshot_data.volume = 1000
        snapshot_data.open_interest = 5000

        mock_api.snapshots.return_value = [snapshot_data]
        mock_client._api = mock_api

        data_source = ShioajiOptionDataSource(mock_client)

        # 模擬合約
        contract = Mock()
        contract.code = 'TXO202512C23000'
        contract.strike_price = 23000
        contract.option_right = 'Call'
        contract.delivery_date = '2025-12-17'

        result = data_source._get_contract_snapshot(contract, date(2024, 12, 15))

        assert result is not None
        assert result['contract_id'] == 'TXO202512C23000'
        assert result['close'] == 150.5
        assert result['volume'] == 1000
        assert result['open_interest'] == 5000

    def test_get_snapshot_no_data(self):
        """測試無快照數據"""
        mock_client = Mock()
        mock_api = Mock()
        mock_api.snapshots.return_value = []
        mock_client._api = mock_api

        data_source = ShioajiOptionDataSource(mock_client)

        contract = Mock()
        contract.code = 'TXO202512C23000'
        contract.strike_price = 23000
        contract.option_right = 'Call'
        contract.delivery_date = '2025-12-17'

        result = data_source._get_contract_snapshot(contract, date(2024, 12, 15))

        assert result is None

    def test_get_snapshot_missing_attributes(self):
        """測試快照數據缺少屬性"""
        mock_client = Mock()
        mock_api = Mock()

        # 使用 spec 創建快照數據，只包含 close 屬性
        snapshot_data = Mock(spec=['close'])
        snapshot_data.close = 150.5
        # volume 和 open_interest 不在 spec 中，hasattr 會返回 False

        mock_api.snapshots.return_value = [snapshot_data]
        mock_client._api = mock_api

        data_source = ShioajiOptionDataSource(mock_client)

        contract = Mock()
        contract.code = 'TXO202512C23000'
        contract.strike_price = 23000
        contract.option_right = 'Call'
        contract.delivery_date = '2025-12-17'

        result = data_source._get_contract_snapshot(contract, date(2024, 12, 15))

        # 應處理缺失屬性
        assert result is not None
        assert result['close'] == 150.5
        assert result['volume'] == 0  # 預設值
        assert result['open_interest'] is None  # 預設值

    def test_get_snapshot_api_error(self):
        """測試 API 錯誤"""
        mock_client = Mock()
        mock_api = Mock()
        mock_api.snapshots.side_effect = Exception("API Error")
        mock_client._api = mock_api

        data_source = ShioajiOptionDataSource(mock_client)

        contract = Mock()
        contract.code = 'TXO202512C23000'
        contract.strike_price = 23000
        contract.option_right = 'Call'
        contract.delivery_date = '2025-12-17'

        result = data_source._get_contract_snapshot(contract, date(2024, 12, 15))

        assert result is None


class TestGetOptionChain:
    """測試 get_option_chain 完整流程"""

    def create_mock_contract(self, code='TXO202512C23000'):
        """創建模擬合約"""
        contract = Mock()
        contract.code = code
        contract.strike_price = 23000
        contract.option_right = 'Call' if 'C' in code else 'Put'
        contract.delivery_date = '2025-12-17'
        return contract

    def test_get_option_chain_success(self):
        """測試成功獲取 option chain"""
        mock_client = Mock()
        mock_api = Mock()
        mock_client._api = mock_api
        mock_client.is_available.return_value = True

        # 模擬合約列表
        contracts = [
            self.create_mock_contract('TXO202512C23000'),
            self.create_mock_contract('TXO202512P23000'),
        ]

        mock_txo = Mock()
        mock_txo.__iter__ = Mock(return_value=iter(contracts))
        mock_api.Contracts.Options.TXO = mock_txo

        # 模擬 snapshot 數據
        snapshot1 = Mock()
        snapshot1.close = 150.0
        snapshot1.volume = 1000
        snapshot1.open_interest = 5000

        snapshot2 = Mock()
        snapshot2.close = 130.0
        snapshot2.volume = 1200
        snapshot2.open_interest = 6000

        mock_api.snapshots.side_effect = [[snapshot1], [snapshot2]]

        data_source = ShioajiOptionDataSource(mock_client)
        result = data_source.get_option_chain('TX', date(2024, 12, 15))

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert 'contract_id' in result.columns
        assert 'close' in result.columns
        assert 'volume' in result.columns

    def test_get_option_chain_client_unavailable(self):
        """測試客戶端不可用"""
        mock_client = Mock()
        mock_client.is_available.return_value = False

        data_source = ShioajiOptionDataSource(mock_client)
        result = data_source.get_option_chain('TX', date(2024, 12, 15))

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_get_option_chain_no_contracts(self):
        """測試無合約"""
        mock_client = Mock()
        mock_api = Mock()
        mock_client._api = mock_api
        mock_client.is_available.return_value = True

        # 空合約列表
        mock_txo = Mock()
        mock_txo.__iter__ = Mock(return_value=iter([]))
        mock_api.Contracts.Options.TXO = mock_txo

        data_source = ShioajiOptionDataSource(mock_client)
        result = data_source.get_option_chain('TX', date(2024, 12, 15))

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_get_option_chain_all_snapshots_fail(self):
        """測試所有快照獲取失敗"""
        mock_client = Mock()
        mock_api = Mock()
        mock_client._api = mock_api
        mock_client.is_available.return_value = True

        contracts = [
            self.create_mock_contract('TXO202512C23000'),
        ]

        mock_txo = Mock()
        mock_txo.__iter__ = Mock(return_value=iter(contracts))
        mock_api.Contracts.Options.TXO = mock_txo

        # 所有 snapshot 調用失敗
        mock_api.snapshots.side_effect = Exception("API Error")

        data_source = ShioajiOptionDataSource(mock_client)
        result = data_source.get_option_chain('TX', date(2024, 12, 15))

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_get_option_chain_partial_failures(self):
        """測試部分快照獲取失敗"""
        mock_client = Mock()
        mock_api = Mock()
        mock_client._api = mock_api
        mock_client.is_available.return_value = True

        contracts = [
            self.create_mock_contract('TXO202512C23000'),
            self.create_mock_contract('TXO202512P23000'),
            self.create_mock_contract('TXO202512C23100'),
        ]

        mock_txo = Mock()
        mock_txo.__iter__ = Mock(return_value=iter(contracts))
        mock_api.Contracts.Options.TXO = mock_txo

        # 第一個成功，第二個失敗，第三個成功
        snapshot1 = Mock()
        snapshot1.close = 150.0
        snapshot1.volume = 1000
        snapshot1.open_interest = 5000

        snapshot3 = Mock()
        snapshot3.close = 140.0
        snapshot3.volume = 800
        snapshot3.open_interest = 4500

        mock_api.snapshots.side_effect = [
            [snapshot1],
            Exception("API Error"),
            [snapshot3]
        ]

        data_source = ShioajiOptionDataSource(mock_client)
        result = data_source.get_option_chain('TX', date(2024, 12, 15))

        # 應返回 2 個成功的合約
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    def test_get_option_chain_contract_list_error(self):
        """測試獲取合約列表失敗"""
        mock_client = Mock()
        mock_api = Mock()
        mock_client._api = mock_api
        mock_client.is_available.return_value = True

        # 訪問 Contracts.Options.TXO 時拋出異常
        mock_api.Contracts.Options = Mock()
        type(mock_api.Contracts.Options).TXO = PropertyMock(
            side_effect=Exception("Contract API Error")
        )

        data_source = ShioajiOptionDataSource(mock_client)
        result = data_source.get_option_chain('TX', date(2024, 12, 15))

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


class TestGetMinuteKbars:
    """測試 get_minute_kbars 方法"""

    def test_get_minute_kbars_not_implemented(self):
        """測試分鐘線功能未實作"""
        mock_client = Mock()
        data_source = ShioajiOptionDataSource(mock_client)

        result = data_source.get_minute_kbars(
            'TXO202512C23000',
            date(2024, 12, 1),
            date(2024, 12, 15)
        )

        # 階段一應返回空 DataFrame
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


class TestQlibOptionDataSource:
    """測試 QlibOptionDataSource（未實作階段）"""

    def test_init(self):
        """測試初始化"""
        data_source = QlibOptionDataSource('/data/qlib/options')
        assert data_source.qlib_dir == '/data/qlib/options'

    def test_is_available(self):
        """測試可用性（階段一不實作）"""
        data_source = QlibOptionDataSource('/data/qlib/options')
        assert data_source.is_available() is False

    def test_get_option_chain_not_implemented(self):
        """測試 get_option_chain 未實作"""
        data_source = QlibOptionDataSource('/data/qlib/options')
        result = data_source.get_option_chain('TX', date(2024, 12, 15))

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_get_minute_kbars_not_implemented(self):
        """測試 get_minute_kbars 未實作"""
        data_source = QlibOptionDataSource('/data/qlib/options')
        result = data_source.get_minute_kbars(
            'TXO202512C23000',
            date(2024, 12, 1),
            date(2024, 12, 15)
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


class TestEdgeCases:
    """測試邊界情況和錯誤處理"""

    def test_txcont_underlying(self):
        """測試 TXCONT 標的（應對應到 TXO）"""
        mock_client = Mock()
        mock_api = Mock()
        mock_client._api = mock_api

        contracts = [Mock()]
        contracts[0].code = 'TXO202512C23000'

        mock_txo = Mock()
        mock_txo.__iter__ = Mock(return_value=iter(contracts))
        mock_api.Contracts.Options.TXO = mock_txo

        data_source = ShioajiOptionDataSource(mock_client)
        result = data_source._get_option_contracts('TXCONT')

        # TXCONT 應對應到 TXO
        assert len(result) == 1

    def test_mtxcont_underlying(self):
        """測試 MTXCONT 標的（應對應到 MXO）"""
        mock_client = Mock()
        mock_api = Mock()
        mock_client._api = mock_api

        contracts = [Mock()]
        contracts[0].code = 'MXO202512C23000'

        mock_mxo = Mock()
        mock_mxo.__iter__ = Mock(return_value=iter(contracts))
        mock_api.Contracts.Options.MXO = mock_mxo

        data_source = ShioajiOptionDataSource(mock_client)
        result = data_source._get_option_contracts('MTXCONT')

        assert len(result) == 1

    def test_large_contract_list_progress_logging(self):
        """測試大量合約的進度記錄"""
        mock_client = Mock()
        mock_api = Mock()
        mock_client._api = mock_api
        mock_client.is_available.return_value = True

        # 創建 150 個合約（觸發進度記錄）
        contracts = [Mock() for _ in range(150)]
        for i, contract in enumerate(contracts):
            contract.code = f'TXO202512C{23000 + i * 10}'
            contract.strike_price = 23000 + i * 10
            contract.option_right = 'Call'
            contract.delivery_date = '2025-12-17'

        mock_txo = Mock()
        mock_txo.__iter__ = Mock(return_value=iter(contracts))
        mock_api.Contracts.Options.TXO = mock_txo

        # 所有快照都成功
        snapshot = Mock()
        snapshot.close = 150.0
        snapshot.volume = 1000
        snapshot.open_interest = 5000
        mock_api.snapshots.return_value = [snapshot]

        data_source = ShioajiOptionDataSource(mock_client)
        result = data_source.get_option_chain('TX', date(2024, 12, 15))

        # 應成功處理所有合約
        assert len(result) == 150
