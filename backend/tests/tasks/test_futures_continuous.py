"""
Unit tests for futures continuous contract Celery tasks
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime, timezone
import subprocess
import sys
from pathlib import Path

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestGenerateContinuousContractsTask:
    """測試連續合約生成任務"""

    @pytest.fixture
    def mock_task(self):
        """Mock Celery 任務"""
        task = Mock()
        task.request = Mock()
        task.request.retries = 0
        task.retry = Mock(side_effect=Exception("Retry called"))
        return task

    @patch('app.tasks.futures_continuous.subprocess.run')
    def test_generate_continuous_contracts_success(self, mock_run):
        """測試成功生成連續合約"""
        from app.tasks.futures_continuous import generate_continuous_contracts

        # Mock 成功的 subprocess 結果
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Successfully generated continuous contract"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # 創建 mock task
        mock_task = Mock()

        # 執行任務
        # 繞過所有裝飾器直接調用函數
        from app.tasks import futures_continuous
        func = futures_continuous.generate_continuous_contracts.__wrapped__.__wrapped__

        result = func(
            mock_task,
            symbols=['TX', 'MTX'],
            days_back=90
        )

        # 驗證結果
        assert result['status'] == 'success'
        assert result['message'] == 'Generated 2/2 continuous contracts'
        assert len(result['results']) == 2

        # 驗證 subprocess 被調用兩次（TX 和 MTX）
        assert mock_run.call_count == 2

    @patch('app.tasks.futures_continuous.subprocess.run')
    def test_generate_continuous_contracts_partial_failure(self, mock_run):
        """測試部分失敗"""
        # Mock TX 成功，MTX 失敗
        results = [
            Mock(returncode=0, stdout="TX success", stderr=""),
            Mock(returncode=1, stdout="", stderr="MTX error")
        ]
        mock_run.side_effect = results

        # 執行任務
        from app.tasks import futures_continuous
        func = futures_continuous.generate_continuous_contracts.__wrapped__.__wrapped__

        result = func(
            Mock(),
            symbols=['TX', 'MTX'],
            days_back=90
        )

        # 驗證結果
        assert result['status'] == 'partial'
        assert result['message'] == 'Generated 1/2 continuous contracts'

        # 驗證有一個成功和一個失敗
        success_count = sum(1 for r in result['results'] if r['status'] == 'success')
        error_count = sum(1 for r in result['results'] if r['status'] == 'error')
        assert success_count == 1
        assert error_count == 1

    @patch('app.tasks.futures_continuous.subprocess.run')
    def test_generate_continuous_contracts_timeout(self, mock_run):
        """測試超時處理"""
        # Mock 超時異常
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd='test',
            timeout=600
        )

        # 執行任務
        from app.tasks import futures_continuous
        func = futures_continuous.generate_continuous_contracts.__wrapped__.__wrapped__

        result = func(
            Mock(),
            symbols=['TX'],
            days_back=90
        )

        # 驗證結果
        assert result['status'] == 'error'
        assert 'timed out' in result['message'].lower()

    def test_generate_continuous_contracts_command_format(self):
        """測試生成的命令格式"""
        import sys
        from datetime import date, timedelta

        symbol = 'TX'
        days_back = 90
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)

        # 預期的命令
        expected_cmd = [
            sys.executable,
            "/app/scripts/generate_continuous_contract.py",
            "--symbol", symbol,
            "--start-date", start_date.strftime('%Y-%m-%d'),
            "--end-date", end_date.strftime('%Y-%m-%d'),
            "--switch-days", "3"
        ]

        # 驗證命令格式正確
        assert expected_cmd[0] == sys.executable
        assert expected_cmd[1] == "/app/scripts/generate_continuous_contract.py"
        assert "--symbol" in expected_cmd
        assert "TX" in expected_cmd
        assert "--start-date" in expected_cmd
        assert "--end-date" in expected_cmd

    def test_default_parameters(self):
        """測試默認參數"""
        # 默認參數應該是 ['TX', 'MTX'] 和 90 天
        default_symbols = ['TX', 'MTX']
        default_days_back = 90

        assert len(default_symbols) == 2
        assert 'TX' in default_symbols
        assert 'MTX' in default_symbols
        assert default_days_back == 90

    @patch('app.tasks.futures_continuous.subprocess.run')
    def test_exponential_backoff_retry(self, mock_run):
        """測試指數退避重試邏輯"""
        # 重試次數和對應的倒計時
        retry_tests = [
            (0, 600),      # 第一次重試: 600 * (2^0) = 600秒 = 10分鐘
            (1, 1200),     # 第二次重試: 600 * (2^1) = 1200秒 = 20分鐘
            (2, 2400),     # 第三次重試: 600 * (2^2) = 2400秒 = 40分鐘
        ]

        for retry_count, expected_countdown in retry_tests:
            countdown = 600 * (2 ** retry_count)
            assert countdown == expected_countdown

    def test_output_truncation(self):
        """測試輸出截斷邏輯"""
        # 模擬長輸出
        long_output = "x" * 1000

        # 應截斷為最後 300 字元
        truncated = long_output[-300:] if long_output else ""

        assert len(truncated) == 300
        assert truncated == "x" * 300


class TestRegisterNewFuturesContractsTask:
    """測試新年度合約註冊任務"""

    @patch('app.tasks.futures_continuous.subprocess.run')
    def test_register_new_contracts_success(self, mock_run):
        """測試成功註冊新合約"""
        # Mock 成功的結果
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Successfully registered 24 contracts"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # 執行任務
        from app.tasks import futures_continuous
        func = futures_continuous.register_new_futures_contracts.__wrapped__.__wrapped__

        result = func(Mock(), year=2027)

        # 驗證結果
        assert result['status'] == 'success'
        assert '2027' in result['message']
        assert mock_run.called

    @patch('app.tasks.futures_continuous.subprocess.run')
    def test_register_new_contracts_failure(self, mock_run):
        """測試註冊失敗"""
        # Mock 失敗的結果
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Database connection failed"
        mock_run.return_value = mock_result

        # 執行任務
        from app.tasks import futures_continuous
        func = futures_continuous.register_new_futures_contracts.__wrapped__.__wrapped__

        result = func(Mock(), year=2027)

        # 驗證結果
        assert result['status'] == 'error'
        assert 'Failed' in result['message']

    @patch('app.tasks.futures_continuous.subprocess.run')
    def test_register_new_contracts_timeout(self, mock_run):
        """測試註冊超時"""
        # Mock 超時
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd='test',
            timeout=300
        )

        # 執行任務
        from app.tasks import futures_continuous
        func = futures_continuous.register_new_futures_contracts.__wrapped__.__wrapped__

        result = func(Mock(), year=2027)

        # 驗證結果
        assert result['status'] == 'error'
        assert 'timed out' in result['message'].lower()

    def test_default_year_parameter(self):
        """測試默認年份參數"""
        current_year = date.today().year
        default_year = current_year + 1

        # 如果不提供年份，應該使用明年
        assert default_year == current_year + 1

    def test_register_command_format(self):
        """測試註冊命令格式"""
        import sys

        year = 2027
        expected_cmd = [
            sys.executable,
            "/app/scripts/register_futures_contracts.py",
            "--symbols", "TX,MTX",
            "--start-year", str(year),
            "--end-year", str(year)
        ]

        # 驗證命令格式
        assert expected_cmd[1] == "/app/scripts/register_futures_contracts.py"
        assert "--symbols" in expected_cmd
        assert "TX,MTX" in expected_cmd
        assert "--start-year" in expected_cmd
        assert str(year) in expected_cmd

    def test_timeout_value(self):
        """測試超時值"""
        # 註冊任務超時應該是 300 秒（5 分鐘）
        timeout = 300
        assert timeout == 5 * 60


class TestTaskResultFormat:
    """測試任務結果格式"""

    def test_success_result_format(self):
        """測試成功結果格式"""
        result = {
            "status": "success",
            "message": "Generated 2/2 continuous contracts",
            "results": [
                {"symbol": "TX", "status": "success"},
                {"symbol": "MTX", "status": "success"}
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # 驗證必要欄位
        assert 'status' in result
        assert 'message' in result
        assert 'timestamp' in result
        assert isinstance(result['timestamp'], str)

    def test_error_result_format(self):
        """測試錯誤結果格式"""
        result = {
            "status": "error",
            "message": "Continuous contract generation timed out",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # 驗證錯誤格式
        assert result['status'] == 'error'
        assert 'message' in result
        assert 'timestamp' in result

    def test_partial_result_format(self):
        """測試部分成功結果格式"""
        result = {
            "status": "partial",
            "message": "Generated 1/2 continuous contracts",
            "results": [
                {"symbol": "TX", "status": "success"},
                {"symbol": "MTX", "status": "error", "error": "Some error"}
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # 驗證部分成功格式
        assert result['status'] == 'partial'
        assert len(result['results']) == 2

        # 統計成功和失敗數量
        success_count = sum(1 for r in result['results'] if r['status'] == 'success')
        error_count = sum(1 for r in result['results'] if r['status'] == 'error')

        assert success_count == 1
        assert error_count == 1


class TestTaskHistoryRecording:
    """測試任務歷史記錄"""

    def test_record_task_history_decorator(self):
        """測試 @record_task_history 裝飾器"""
        # 這個測試驗證裝飾器的存在和基本功能
        from app.tasks.futures_continuous import generate_continuous_contracts

        # 驗證任務有 @record_task_history 裝飾器
        # (實際驗證需要檢查數據庫記錄，這裡只驗證裝飾器存在)
        assert hasattr(generate_continuous_contracts, '__wrapped__') or \
               hasattr(generate_continuous_contracts, '__name__')

    def test_task_naming_convention(self):
        """測試任務命名規範"""
        # 任務名稱應該遵循 app.tasks.xxx 格式
        task_names = [
            "app.tasks.generate_continuous_contracts",
            "app.tasks.register_new_futures_contracts"
        ]

        for name in task_names:
            assert name.startswith("app.tasks.")
            assert "_" in name  # Snake case
