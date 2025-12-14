# QuantLab Backend Tests

## 概述

本目錄包含 QuantLab 後端的所有測試套件，包括單元測試和整合測試。

## 測試結構

```
tests/
├── services/          # 服務層測試
│   └── test_shioaji_client.py      # Shioaji 客戶端測試（期貨合約功能）
├── scripts/           # 腳本測試
│   └── test_register_futures_contracts.py  # 期貨合約註冊測試
├── tasks/             # Celery 任務測試
│   └── test_futures_continuous.py  # 連續合約生成任務測試
└── ...                # 其他測試
```

## 安裝測試依賴

```bash
# 在容器中安裝
docker compose exec backend pip install -r requirements-test.txt

# 或在本地安裝
pip install -r requirements-test.txt
```

## 運行測試

### 運行所有測試

```bash
docker compose exec backend pytest tests/ -v
```

### 運行特定測試文件

```bash
# 測試 Shioaji 客戶端
docker compose exec backend pytest tests/services/test_shioaji_client.py -v

# 測試期貨合約註冊
docker compose exec backend pytest tests/scripts/test_register_futures_contracts.py -v

# 測試 Celery 任務
docker compose exec backend pytest tests/tasks/test_futures_continuous.py -v
```

### 運行特定測試類別

```bash
# 只運行單元測試（排除整合測試）
docker compose exec backend pytest tests/ -m "not integration" -v

# 只運行期貨相關測試
docker compose exec backend pytest tests/ -m "futures" -v
```

### 運行特定測試方法

```bash
# 測試第三個週三計算
docker compose exec backend pytest tests/services/test_shioaji_client.py::TestThirdWednesdayCalculation::test_january_2025 -v

# 測試合約到期判斷
docker compose exec backend pytest tests/services/test_shioaji_client.py::TestContractExpiry::test_expired_contract -v
```

## 測試覆蓋率

### 生成覆蓋率報告

```bash
# HTML 報告
docker compose exec backend pytest tests/ --cov=app --cov-report=html

# 終端報告
docker compose exec backend pytest tests/ --cov=app --cov-report=term
```

### 查看覆蓋率報告

HTML 報告會生成在 `htmlcov/index.html`：

```bash
# 在本地打開
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## 測試標記

測試使用以下標記分類：

- `unit`: 單元測試（快速，無外部依賴）
- `integration`: 整合測試（需要數據庫、API 等）
- `slow`: 慢速測試（執行時間 > 1 秒）
- `futures`: 期貨合約相關測試

### 使用標記

```bash
# 只運行單元測試
pytest -m unit

# 只運行整合測試
pytest -m integration

# 排除慢速測試
pytest -m "not slow"
```

## 期貨功能測試總覽

### 1. ShioajiClient 測試 (test_shioaji_client.py)

**測試內容**:
- ✅ 第三個週三計算（14 個測試）
- ✅ 合約到期判斷（6 個測試）
- ✅ 期貨合約代碼格式（4 個測試）

**關鍵測試**:
```python
# 測試 2025 年 1 月的第三個週三
test_january_2025()  # 預期: 2025-01-15

# 測試已過期合約
test_expired_contract()  # 202401 在 2025-12-14 時已過期

# 測試合約代碼格式
test_contract_id_format_generation()  # TX202512 格式驗證
```

### 2. 註冊腳本測試 (test_register_futures_contracts.py)

**測試內容**:
- ✅ 合約生成數量（72 個合約）
- ✅ 合約代碼格式（TX202512）
- ✅ 結算日計算
- ✅ 到期狀態邏輯
- ✅ 批次處理邏輯
- ✅ ON CONFLICT 處理

**關鍵測試**:
```python
# 測試生成 72 個合約
test_contract_generation_count()  # 2024-2026, TX+MTX, 12月

# 測試合約代碼格式
test_contract_code_format()  # TX202512, MTX202601

# 測試批次處理
test_batch_size_logic()  # 100 個一批
```

### 3. Celery 任務測試 (test_futures_continuous.py)

**測試內容**:
- ✅ 連續合約生成成功/失敗/超時
- ✅ 新合約註冊成功/失敗/超時
- ✅ 指數退避重試邏輯
- ✅ 命令格式驗證
- ✅ 結果格式驗證

**關鍵測試**:
```python
# 測試成功生成
test_generate_continuous_contracts_success()  # 2/2 成功

# 測試部分失敗
test_generate_continuous_contracts_partial_failure()  # 1/2 成功

# 測試指數退避
test_exponential_backoff_retry()  # 10分、20分、40分
```

## 持續整合 (CI)

### GitHub Actions 配置範例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          docker compose up -d postgres redis
          docker compose exec -T backend pytest tests/ -m "not integration" -v
```

## 測試最佳實踐

### 1. 測試命名

```python
# 好的命名
def test_expired_contract():  # 清楚說明測試內容
def test_january_2025():      # 具體的測試案例

# 不好的命名
def test_1():  # 不清楚測試什麼
def test():    # 太泛化
```

### 2. 測試結構

```python
def test_something():
    # Arrange（準備）
    input_data = "test"

    # Act（執行）
    result = function_under_test(input_data)

    # Assert（驗證）
    assert result == expected_output
```

### 3. 使用 Fixtures

```python
@pytest.fixture
def sample_data():
    return {"key": "value"}

def test_with_fixture(sample_data):
    assert sample_data["key"] == "value"
```

## 故障排除

### 問題 1: ModuleNotFoundError

```bash
# 確保在正確的目錄運行
cd /home/ubuntu/QuantLab/backend
docker compose exec backend pytest tests/
```

### 問題 2: 數據庫連接失敗

```bash
# 確保 PostgreSQL 正在運行
docker compose ps postgres

# 重啟數據庫
docker compose restart postgres
```

### 問題 3: 測試超時

```bash
# 增加超時限制
pytest tests/ --timeout=300
```

### 問題 4: 快取問題

```bash
# 清除 pytest 快取
rm -rf .pytest_cache __pycache__

# 重新運行
pytest tests/
```

## 貢獻指南

### 添加新測試

1. 在適當的目錄創建測試文件（`test_*.py`）
2. 添加必要的 imports
3. 創建測試類（`Test*`）
4. 編寫測試方法（`test_*`）
5. 運行測試驗證

### 測試覆蓋率目標

- 核心業務邏輯: **>= 80%**
- 工具函數: **>= 90%**
- API 端點: **>= 70%**

## 相關資源

- [Pytest 文檔](https://docs.pytest.org/)
- [pytest-mock 文檔](https://pytest-mock.readthedocs.io/)
- [Coverage.py 文檔](https://coverage.readthedocs.io/)

---

**最後更新**: 2025-12-14
**維護者**: 開發團隊
