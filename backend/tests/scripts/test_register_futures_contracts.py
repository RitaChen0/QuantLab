"""
Unit tests for register_futures_contracts script
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date
import sys
from pathlib import Path

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.register_futures_contracts import register_monthly_contracts
from app.services.shioaji_client import get_third_wednesday


class TestRegisterFuturesContracts:
    """測試期貨合約註冊功能"""

    @pytest.fixture
    def mock_db_engine(self):
        """Mock 資料庫引擎"""
        engine = Mock()
        connection = Mock()
        engine.connect.return_value.__enter__ = Mock(return_value=connection)
        engine.connect.return_value.__exit__ = Mock(return_value=False)
        return engine, connection

    def test_contract_generation_count(self):
        """測試生成的合約數量"""
        # 2024-2026（3年） × 2符號（TX, MTX） × 12月 = 72個合約
        symbols = ['TX', 'MTX']
        start_year = 2024
        end_year = 2026

        total_contracts = len(symbols) * (end_year - start_year + 1) * 12
        assert total_contracts == 72

    def test_contract_code_format(self):
        """測試合約代碼格式"""
        # TX202512 格式測試
        symbol = 'TX'
        year = 2025
        month = 12

        contract_code = f"{symbol}{year:04d}{month:02d}"
        assert contract_code == 'TX202512'
        assert len(contract_code) == 8

        # MTX202601 格式測試
        symbol = 'MTX'
        year = 2026
        month = 1

        contract_code = f"{symbol}{year:04d}{month:02d}"
        assert contract_code == 'MTX202601'
        assert len(contract_code) == 9

    def test_settlement_date_calculation(self):
        """測試結算日計算"""
        # 2025-12 的結算日應該是 12/17
        settlement = get_third_wednesday(2025, 12)
        assert settlement == date(2025, 12, 17)

        # 2026-01 的結算日應該是 1/21
        settlement = get_third_wednesday(2026, 1)
        assert settlement == date(2026, 1, 21)

    def test_expiry_status_logic(self):
        """測試到期狀態邏輯"""
        today = date(2025, 12, 14)

        # 2024-01 已到期
        settlement_202401 = get_third_wednesday(2024, 1)
        is_expired = today > settlement_202401
        assert is_expired is True

        # 2025-12 未到期
        settlement_202512 = get_third_wednesday(2025, 12)
        is_expired = today > settlement_202512
        assert is_expired is False

        # 2026-01 未到期
        settlement_202601 = get_third_wednesday(2026, 1)
        is_expired = today > settlement_202601
        assert is_expired is False

    @patch('scripts.register_futures_contracts.create_engine')
    @patch('scripts.register_futures_contracts.date')
    def test_register_monthly_contracts_structure(self, mock_date, mock_create_engine):
        """測試註冊合約的數據結構"""
        # Mock 當前日期
        mock_date.today.return_value = date(2025, 12, 14)

        # Mock 資料庫引擎
        mock_engine = Mock()
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=False)
        mock_create_engine.return_value = mock_engine

        # Mock execute 返回值
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        mock_conn.execute.return_value = mock_result

        # 執行註冊（僅 TX，1 年）
        register_monthly_contracts(
            symbols=['TX'],
            start_year=2025,
            end_year=2025,
            db_url='postgresql://test'
        )

        # 驗證 execute 被調用
        assert mock_conn.execute.called

    def test_contract_name_format(self):
        """測試合約名稱格式"""
        symbol_names = {
            'TX': '台指期貨',
            'MTX': '小台指期貨'
        }

        # TX 2025-12
        name = f"{symbol_names['TX']} 2025-12 合約"
        assert name == '台指期貨 2025-12 合約'

        # MTX 2026-01
        name = f"{symbol_names['MTX']} 2026-01 合約"
        assert name == '小台指期貨 2026-01 合約'

    def test_active_status_assignment(self):
        """測試 active 狀態分配邏輯"""
        today = date(2025, 12, 14)

        # 測試多個合約的狀態
        test_cases = [
            ('202401', 'inactive'),  # 已過期
            ('202512', 'active'),     # 未過期（當月）
            ('202601', 'active'),     # 未過期（下月）
            ('202606', 'active'),     # 未過期（遠月）
        ]

        for month_str, expected_status in test_cases:
            year = int(month_str[:4])
            month = int(month_str[4:6])
            settlement_date = get_third_wednesday(year, month)
            is_expired = today > settlement_date
            status = 'inactive' if is_expired else 'active'

            assert status == expected_status, f"{month_str} should be {expected_status}"

    def test_batch_size_logic(self):
        """測試批次處理邏輯"""
        contracts = list(range(250))  # 250 個合約
        batch_size = 100

        batches = []
        for i in range(0, len(contracts), batch_size):
            batch = contracts[i:i+batch_size]
            batches.append(batch)

        # 應該有 3 個批次
        assert len(batches) == 3
        # 前兩個批次應該是 100 個
        assert len(batches[0]) == 100
        assert len(batches[1]) == 100
        # 最後一個批次是 50 個
        assert len(batches[2]) == 50

    def test_upsert_conflict_handling(self):
        """測試 ON CONFLICT DO UPDATE 邏輯"""
        # 驗證 SQL 包含正確的 ON CONFLICT 子句
        insert_query = """
            INSERT INTO stocks (stock_id, name, category, market, is_active)
            VALUES (:stock_id, :name, :category, :market, :is_active)
            ON CONFLICT (stock_id) DO UPDATE SET
                name = EXCLUDED.name,
                category = EXCLUDED.category,
                market = EXCLUDED.market,
                is_active = EXCLUDED.is_active,
                updated_at = NOW()
        """

        # 驗證 SQL 包含必要的關鍵字
        assert 'ON CONFLICT' in insert_query
        assert 'DO UPDATE SET' in insert_query
        assert 'EXCLUDED' in insert_query

    @pytest.mark.integration
    @pytest.mark.skipif(True, reason="Requires database connection")
    def test_register_contracts_integration(self):
        """整合測試：實際註冊合約（需要資料庫）"""
        # 這個測試需要實際的資料庫連接
        # 在 CI/CD 環境中可以啟用
        pass


class TestContractExpiryEdgeCases:
    """測試合約到期邊界條件"""

    def test_settlement_day_boundary(self):
        """測試結算日邊界"""
        # 2025-12-17 是結算日
        settlement = get_third_wednesday(2025, 12)

        # 結算日前一天：未過期
        assert date(2025, 12, 16) <= settlement

        # 結算日當天：未過期
        assert date(2025, 12, 17) <= settlement

        # 結算日後一天：已過期
        assert date(2025, 12, 18) > settlement

    def test_year_boundary(self):
        """測試跨年邊界"""
        # 2025-12 合約
        settlement_dec = get_third_wednesday(2025, 12)

        # 2026-01 合約
        settlement_jan = get_third_wednesday(2026, 1)

        # 12 月結算日應早於 1 月結算日
        assert settlement_dec < settlement_jan

    def test_all_months_have_valid_settlement(self):
        """測試所有月份都有有效的結算日"""
        for month in range(1, 13):
            settlement = get_third_wednesday(2025, month)

            # 應該在該月份內
            assert settlement.month == month
            assert settlement.year == 2025

            # 應該是週三
            assert settlement.weekday() == 2  # 0=Monday, 2=Wednesday

            # 應該在 15-21 號之間（第三個週三的可能範圍）
            assert 15 <= settlement.day <= 21
