"""
Unit tests for OptionFactorCalculator

測試選擇權因子計算器的各項功能
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import date
from decimal import Decimal
import pandas as pd
import numpy as np

from app.services.option_calculator import (
    OptionFactorCalculator,
    OPTION_FACTOR_REGISTRY,
    get_available_factors
)


class TestOptionFactorRegistry:
    """測試因子註冊表"""

    def test_registry_structure(self):
        """測試註冊表結構完整性"""
        assert 'pcr_volume' in OPTION_FACTOR_REGISTRY
        assert 'pcr_open_interest' in OPTION_FACTOR_REGISTRY
        assert 'atm_iv' in OPTION_FACTOR_REGISTRY

    def test_stage1_factors(self):
        """測試階段一因子"""
        stage1_factors = get_available_factors(1)

        assert 'pcr_volume' in stage1_factors
        assert 'pcr_open_interest' in stage1_factors
        assert 'atm_iv' in stage1_factors

        # 階段二因子不應出現
        assert 'iv_skew' not in stage1_factors
        assert 'max_pain_strike' not in stage1_factors

    def test_stage2_factors(self):
        """測試階段二因子"""
        stage2_factors = get_available_factors(2)

        # 包含階段一因子
        assert 'pcr_volume' in stage2_factors
        assert 'atm_iv' in stage2_factors

        # 包含階段二因子
        assert 'iv_skew' in stage2_factors
        assert 'max_pain_strike' in stage2_factors

    def test_factor_metadata(self):
        """測試因子元數據"""
        pcr_factor = OPTION_FACTOR_REGISTRY['pcr_volume']

        assert pcr_factor['stage'] == 1
        assert pcr_factor['qlib_field'] == '$pcr'
        assert 'description' in pcr_factor
        assert 'dependencies' in pcr_factor


class TestPCRCalculation:
    """測試 PCR 計算"""

    def create_mock_option_chain(self, call_volume=1000, put_volume=1200,
                                   call_oi=5000, put_oi=6000):
        """創建模擬 option chain 數據"""
        data = {
            'option_type': ['CALL'] * 5 + ['PUT'] * 5,
            'volume': [call_volume/5] * 5 + [put_volume/5] * 5,
            'open_interest': [call_oi/5] * 5 + [put_oi/5] * 5,
            'strike_price': list(range(20000, 20500, 100)) * 2,
            'close': [100, 80, 60, 40, 20] + [20, 40, 60, 80, 100]
        }
        return pd.DataFrame(data)

    def test_pcr_volume_calculation(self):
        """測試 PCR Volume 計算"""
        # 創建模擬資料源
        mock_data_source = Mock()
        calculator = OptionFactorCalculator(mock_data_source)

        # 創建測試數據
        df = self.create_mock_option_chain(call_volume=1000, put_volume=1200)

        # 計算 PCR
        result = calculator._calculate_pcr(df)

        # 驗證結果
        assert 'pcr_volume' in result
        assert 'pcr_open_interest' in result

        # PCR Volume = 1200 / 1000 = 1.2
        expected_pcr_volume = Decimal('1.2')
        assert result['pcr_volume'] == expected_pcr_volume

    def test_pcr_oi_calculation(self):
        """測試 PCR Open Interest 計算"""
        mock_data_source = Mock()
        calculator = OptionFactorCalculator(mock_data_source)

        df = self.create_mock_option_chain(call_oi=5000, put_oi=6000)

        result = calculator._calculate_pcr(df)

        # PCR OI = 6000 / 5000 = 1.2
        expected_pcr_oi = Decimal('1.2')
        assert result['pcr_open_interest'] == expected_pcr_oi

    def test_pcr_zero_call_volume(self):
        """測試 Call 成交量為 0 的情況"""
        mock_data_source = Mock()
        calculator = OptionFactorCalculator(mock_data_source)

        df = self.create_mock_option_chain(call_volume=0, put_volume=1200)

        result = calculator._calculate_pcr(df)

        # Call volume 為 0 時，PCR 應為 None
        assert result['pcr_volume'] is None

    def test_pcr_missing_volume_column(self):
        """測試缺少 volume 欄位的情況"""
        mock_data_source = Mock()
        calculator = OptionFactorCalculator(mock_data_source)

        # 創建缺少 volume 欄位的 DataFrame
        df = pd.DataFrame({
            'option_type': ['CALL', 'PUT'],
            'close': [100, 50]
        })

        result = calculator._calculate_pcr(df)

        # 應返回 None
        assert result['pcr_volume'] is None
        assert result['pcr_open_interest'] is None


class TestATMIVCalculation:
    """測試 ATM IV 計算"""

    def create_mock_option_chain(self):
        """創建模擬 option chain"""
        data = {
            'option_type': ['CALL'] * 5 + ['PUT'] * 5,
            'strike_price': [20000, 20100, 20200, 20300, 20400] * 2,
            'close': [400, 300, 200, 100, 50] + [50, 100, 200, 300, 400],
            'volume': [500, 1000, 800, 300, 100] + [100, 300, 800, 1000, 500]
        }
        return pd.DataFrame(data)

    def test_atm_iv_calculation(self):
        """測試 ATM IV 計算（簡化版）"""
        mock_data_source = Mock()
        calculator = OptionFactorCalculator(mock_data_source)

        df = self.create_mock_option_chain()

        result = calculator._calculate_atm_iv(df)

        # 應返回 atm_iv
        assert 'atm_iv' in result
        assert result['atm_iv'] is not None

        # ATM IV 應為正數
        if result['atm_iv']:
            assert float(result['atm_iv']) > 0

    def test_atm_iv_no_close_prices(self):
        """測試沒有收盤價的情況"""
        mock_data_source = Mock()
        calculator = OptionFactorCalculator(mock_data_source)

        df = pd.DataFrame({
            'option_type': ['CALL', 'PUT'],
            'strike_price': [20000, 20000],
            'close': [None, None]
        })

        result = calculator._calculate_atm_iv(df)

        # 應返回 None
        assert result['atm_iv'] is None

    def test_atm_iv_no_call_contracts(self):
        """測試沒有 CALL 合約的情況"""
        mock_data_source = Mock()
        calculator = OptionFactorCalculator(mock_data_source)

        df = pd.DataFrame({
            'option_type': ['PUT'],
            'strike_price': [20000],
            'close': [100]
        })

        result = calculator._calculate_atm_iv(df)

        # 應返回 None
        assert result['atm_iv'] is None


class TestDataQualityAssessment:
    """測試資料品質評估"""

    def test_high_quality_data(self):
        """測試高品質數據"""
        mock_data_source = Mock()
        calculator = OptionFactorCalculator(mock_data_source)

        # 所有因子都計算成功
        factors = {
            'pcr_volume': Decimal('1.0'),
            'pcr_open_interest': Decimal('1.1'),
            'atm_iv': Decimal('15.0')
        }

        # 完整的 option chain
        df = pd.DataFrame({
            'close': [100, 90, 80, 70, 60],
            'option_type': ['CALL'] * 5
        })

        quality = calculator._assess_quality(factors, df)

        # 高品質數據應該 > 0.8
        assert quality is not None
        assert float(quality) > 0.8

    def test_low_quality_data(self):
        """測試低品質數據"""
        mock_data_source = Mock()
        calculator = OptionFactorCalculator(mock_data_source)

        # 大部分因子計算失敗
        factors = {
            'pcr_volume': None,
            'pcr_open_interest': None,
            'atm_iv': None
        }

        df = pd.DataFrame({
            'close': [None, None, None]
        })

        quality = calculator._assess_quality(factors, df)

        # 低品質數據應該 < 0.5
        assert quality is not None
        assert float(quality) < 0.5

    def test_pcr_out_of_range(self):
        """測試 PCR 超出合理範圍"""
        mock_data_source = Mock()
        calculator = OptionFactorCalculator(mock_data_source)

        # PCR 超出 0.3-3.0 範圍
        factors = {
            'pcr_volume': Decimal('5.0'),  # 異常值
            'pcr_open_interest': Decimal('1.0'),
            'atm_iv': Decimal('15.0')
        }

        df = pd.DataFrame({
            'close': [100, 90, 80],
            'option_type': ['CALL'] * 3
        })

        quality = calculator._assess_quality(factors, df)

        # 品質分數應該受到影響（但不為 None）
        assert quality is not None


class TestFactorCalculationIntegration:
    """因子計算整合測試"""

    def test_calculate_daily_factors_empty_chain(self):
        """測試空 option chain"""
        mock_data_source = Mock()
        mock_data_source.get_option_chain.return_value = pd.DataFrame()

        calculator = OptionFactorCalculator(mock_data_source)

        result = calculator.calculate_daily_factors('TX', date(2024, 12, 15))

        # 應返回空因子
        assert result['pcr_volume'] is None
        assert result['pcr_open_interest'] is None
        assert result['atm_iv'] is None
        assert result['data_quality_score'] == Decimal('0.0')

    def test_calculate_daily_factors_stage1(self):
        """測試階段一因子計算"""
        # 創建模擬資料源
        mock_data_source = Mock()

        # 模擬返回的 option chain
        mock_chain = pd.DataFrame({
            'option_type': ['CALL'] * 5 + ['PUT'] * 5,
            'volume': [200] * 5 + [240] * 5,
            'open_interest': [1000] * 5 + [1200] * 5,
            'strike_price': list(range(20000, 20500, 100)) * 2,
            'close': [100, 80, 60, 40, 20] + [20, 40, 60, 80, 100]
        })

        mock_data_source.get_option_chain.return_value = mock_chain

        # 創建計算器
        calculator = OptionFactorCalculator(mock_data_source, db=None)

        # 計算因子
        result = calculator.calculate_daily_factors('TX', date(2024, 12, 15))

        # 驗證階段一因子
        assert result['pcr_volume'] is not None
        assert result['pcr_open_interest'] is not None
        assert result['atm_iv'] is not None

        # 驗證元數據
        assert result['calculation_version'] == '1.0.0'
        assert result['data_quality_score'] is not None

    @pytest.mark.integration
    def test_calculate_daily_factors_with_db(self):
        """測試帶資料庫的因子計算（整合測試）"""
        # 此測試需要真實的資料庫連接
        pytest.skip("Requires database connection")


class TestEmptyFactorsHelper:
    """測試空因子輔助函數"""

    def test_empty_factors_structure(self):
        """測試空因子結構"""
        mock_data_source = Mock()
        calculator = OptionFactorCalculator(mock_data_source)

        empty = calculator._empty_factors()

        # 驗證所有階段的因子都存在
        assert 'pcr_volume' in empty
        assert 'pcr_open_interest' in empty
        assert 'atm_iv' in empty
        assert 'iv_skew' in empty
        assert 'max_pain_strike' in empty
        assert 'gamma_exposure' in empty

        # 所有因子應為 None
        assert empty['pcr_volume'] is None
        assert empty['pcr_open_interest'] is None
        assert empty['atm_iv'] is None

        # 元數據應有值
        assert empty['calculation_version'] == '1.0.0'
        assert empty['data_quality_score'] == Decimal('0.0')


class TestBoundaryConditions:
    """測試邊界條件"""

    def test_pcr_with_extreme_values(self):
        """測試 PCR 計算極端數值"""
        mock_data_source = Mock()
        calculator = OptionFactorCalculator(mock_data_source)

        # 極大的成交量
        df = pd.DataFrame({
            'option_type': ['CALL', 'PUT'],
            'volume': [1e10, 1e11],  # 極大數值
            'open_interest': [1e10, 1e11],
            'strike_price': [20000, 20000],
            'close': [100, 100]
        })

        result = calculator._calculate_pcr(df)

        # 應該仍能計算，不應拋出異常
        assert result['pcr_volume'] is not None
        assert float(result['pcr_volume']) == pytest.approx(10.0)

    def test_pcr_with_very_small_values(self):
        """測試 PCR 計算非常小的數值"""
        mock_data_source = Mock()
        calculator = OptionFactorCalculator(mock_data_source)

        df = pd.DataFrame({
            'option_type': ['CALL', 'PUT'],
            'volume': [0.001, 0.002],  # 非常小的數值
            'open_interest': [0.001, 0.002],
            'strike_price': [20000, 20000],
            'close': [100, 100]
        })

        result = calculator._calculate_pcr(df)

        # 應能處理小數值
        assert result['pcr_volume'] is not None
        assert float(result['pcr_volume']) == pytest.approx(2.0)

    def test_pcr_with_nan_values(self):
        """測試 PCR 計算包含 NaN 的情況"""
        mock_data_source = Mock()
        calculator = OptionFactorCalculator(mock_data_source)

        df = pd.DataFrame({
            'option_type': ['CALL', 'PUT', 'CALL'],
            'volume': [1000, np.nan, 500],  # 包含 NaN
            'open_interest': [5000, 6000, np.nan],
            'strike_price': [20000, 20000, 20100],
            'close': [100, 100, 90]
        })

        result = calculator._calculate_pcr(df)

        # 應該處理 NaN（可能返回 None 或過濾掉）
        assert 'pcr_volume' in result
        assert 'pcr_open_interest' in result

    def test_pcr_with_negative_values(self):
        """測試 PCR 計算負值（異常數據）"""
        mock_data_source = Mock()
        calculator = OptionFactorCalculator(mock_data_source)

        df = pd.DataFrame({
            'option_type': ['CALL', 'PUT'],
            'volume': [1000, -500],  # 負值（異常）
            'open_interest': [5000, 6000],
            'strike_price': [20000, 20000],
            'close': [100, 100]
        })

        result = calculator._calculate_pcr(df)

        # 應該能處理或返回 None
        assert 'pcr_volume' in result

    def test_calculate_factors_with_empty_underlying_id(self):
        """測試空標的代碼"""
        mock_data_source = Mock()
        mock_data_source.get_option_chain.return_value = pd.DataFrame()
        calculator = OptionFactorCalculator(mock_data_source)

        # 空字符串作為標的代碼
        result = calculator.calculate_daily_factors('', date(2024, 12, 15))

        # 應返回空因子
        assert result['data_quality_score'] == Decimal('0.0')

    def test_calculate_factors_with_none_underlying_id(self):
        """測試 None 標的代碼"""
        mock_data_source = Mock()
        mock_data_source.get_option_chain.return_value = pd.DataFrame()
        calculator = OptionFactorCalculator(mock_data_source)

        # None 作為標的代碼
        result = calculator.calculate_daily_factors(None, date(2024, 12, 15))

        # 應返回空因子
        assert result['data_quality_score'] == Decimal('0.0')

    def test_calculate_factors_with_future_date(self):
        """測試未來日期"""
        mock_data_source = Mock()
        mock_data_source.get_option_chain.return_value = pd.DataFrame()
        calculator = OptionFactorCalculator(mock_data_source)

        # 未來日期（2099年）
        future_date = date(2099, 12, 31)
        result = calculator.calculate_daily_factors('TX', future_date)

        # 應能處理（可能返回空數據）
        assert result is not None

    def test_single_row_dataframe(self):
        """測試只有一行的 DataFrame"""
        mock_data_source = Mock()
        calculator = OptionFactorCalculator(mock_data_source)

        df = pd.DataFrame({
            'option_type': ['CALL'],
            'volume': [1000],
            'open_interest': [5000],
            'strike_price': [20000],
            'close': [100]
        })

        result = calculator._calculate_pcr(df)

        # 只有 CALL，沒有 PUT，PCR 應為 0.0（PUT/CALL = 0/1000）
        assert result['pcr_volume'] == Decimal('0.0')
        assert result['pcr_open_interest'] == Decimal('0.0')

    def test_duplicate_rows_dataframe(self):
        """測試包含重複行的 DataFrame"""
        mock_data_source = Mock()
        calculator = OptionFactorCalculator(mock_data_source)

        df = pd.DataFrame({
            'option_type': ['CALL', 'CALL', 'PUT', 'PUT'],
            'volume': [1000, 1000, 1200, 1200],  # 重複數據
            'open_interest': [5000, 5000, 6000, 6000],
            'strike_price': [20000, 20000, 20000, 20000],  # 相同履約價
            'close': [100, 100, 100, 100]
        })

        result = calculator._calculate_pcr(df)

        # 應該仍能計算（可能會加總重複的數據）
        assert 'pcr_volume' in result
        assert 'pcr_open_interest' in result

    def test_mixed_option_types(self):
        """測試混合選擇權類型（包含異常類型）"""
        mock_data_source = Mock()
        calculator = OptionFactorCalculator(mock_data_source)

        df = pd.DataFrame({
            'option_type': ['CALL', 'PUT', 'INVALID', 'call', 'put'],  # 包含異常和小寫
            'volume': [1000, 1200, 500, 300, 400],
            'open_interest': [5000, 6000, 2000, 1000, 1500],
            'strike_price': [20000, 20000, 20000, 20100, 20100],
            'close': [100, 100, 50, 90, 90]
        })

        result = calculator._calculate_pcr(df)

        # 應該只計算有效的 CALL 和 PUT
        assert 'pcr_volume' in result
        assert 'pcr_open_interest' in result

    def test_data_quality_with_all_none_factors(self):
        """測試所有因子都為 None 時的品質分數"""
        mock_data_source = Mock()
        calculator = OptionFactorCalculator(mock_data_source)

        factors = {
            'pcr_volume': None,
            'pcr_open_interest': None,
            'atm_iv': None,
            'iv_skew': None,
            'max_pain_strike': None
        }

        df = pd.DataFrame()  # 空 DataFrame

        quality = calculator._assess_quality(factors, df)

        # 品質分數應為 0
        assert quality is not None
        assert float(quality) == 0.0

    def test_data_quality_with_partial_none_factors(self):
        """測試部分因子為 None 時的品質分數"""
        mock_data_source = Mock()
        calculator = OptionFactorCalculator(mock_data_source)

        factors = {
            'pcr_volume': Decimal('1.2'),
            'pcr_open_interest': None,  # 一個為 None
            'atm_iv': Decimal('15.0')
        }

        df = pd.DataFrame({
            'close': [100, 90, 80, 70, 60] * 5,  # 25 rows
            'option_type': ['CALL'] * 25
        })

        quality = calculator._assess_quality(factors, df)

        # 品質分數應該中等（有些因子成功，有些失敗）
        assert quality is not None
        assert 0.3 < float(quality) < 0.9

    def test_atm_iv_with_zero_close_prices(self):
        """測試收盤價為 0 的情況"""
        mock_data_source = Mock()
        calculator = OptionFactorCalculator(mock_data_source)

        df = pd.DataFrame({
            'option_type': ['CALL', 'PUT'],
            'strike_price': [20000, 20000],
            'close': [0, 0],  # 收盤價為 0
            'volume': [100, 100]
        })

        result = calculator._calculate_atm_iv(df)

        # 應能處理（可能返回 None 或計算出異常值）
        assert 'atm_iv' in result

    def test_large_dataframe_performance(self):
        """測試大型 DataFrame 的處理（性能測試）"""
        mock_data_source = Mock()
        calculator = OptionFactorCalculator(mock_data_source)

        # 創建 10000 行的大型 DataFrame
        import time

        large_df = pd.DataFrame({
            'option_type': (['CALL'] * 5000) + (['PUT'] * 5000),
            'volume': np.random.randint(100, 10000, 10000),
            'open_interest': np.random.randint(1000, 100000, 10000),
            'strike_price': np.random.randint(18000, 22000, 10000),
            'close': np.random.randint(10, 500, 10000)
        })

        start_time = time.time()
        result = calculator._calculate_pcr(large_df)
        elapsed_time = time.time() - start_time

        # 應在合理時間內完成（< 1 秒）
        assert elapsed_time < 1.0
        assert result['pcr_volume'] is not None
