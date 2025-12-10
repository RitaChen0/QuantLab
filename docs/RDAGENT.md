# RD-Agent 完整指南

本文檔整合了 RD-Agent (Research & Development Agent) 在 QuantLab 中的完整使用、配置和故障排查指南。

## 目錄

- [RD-Agent 簡介](#rdagent-簡介)
- [環境配置](#環境配置)
- [功能使用](#功能使用)
- [因子整合](#因子整合)
- [Docker 依賴問題](#docker-依賴問題)
- [故障排查](#故障排查)

---

## RD-Agent 簡介

### 什麼是 RD-Agent？

**RD-Agent** (Research & Development Agent) 是 Microsoft Research 開發的 AI 驅動量化研究助手，專為自動化量化研究流程設計。

**核心能力**：
- 🧠 **自動因子挖掘**：使用 LLM 生成高品質的 Qlib 表達式因子
- 🔄 **策略優化**：基於回測結果迭代改進交易策略
- 📊 **模型提取**：從現有策略中萃取可重用的量化因子
- 🤖 **AI 驅動**：整合 OpenAI GPT-4、Claude 等 LLM

### 在 QuantLab 中的定位

- **AI 研發助手**：協助量化研究人員發現新因子
- **跨引擎整合**：生成的因子可用於 Backtrader 和 Qlib
- **自動化流程**：從研究目標到可用因子的端到端自動化
- **持續學習**：基於回測結果不斷優化因子

---

## 環境配置

### 前置需求

1. **OpenAI API Key**（必須）：
   - 註冊：https://platform.openai.com/
   - 費用：GPT-4 API 調用費用（約 $0.03-0.06 per 1K tokens）
   - 配額：建議至少 $10 餘額

2. **Docker**（可選，用於代碼隔離執行）：
   - 已安裝 Docker 和 Docker Compose
   - 主機 Docker daemon 可訪問

3. **Qlib 數據**（建議）：
   - 已同步 Qlib v2 數據（加速因子測試）
   - 參考：[docs/QLIB.md](./QLIB.md)

### 環境變數配置

編輯 `.env` 檔案：

```bash
# OpenAI API Key（必填）
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# RD-Agent Docker 隔離（選填，預設 false）
RDAGENT_ENABLE_DOCKER=false

# Qlib 數據路徑（選填，預設值）
QLIB_DATA_PATH=/data/qlib/tw_stock_v2
```

### 依賴套件

**已包含在 `backend/requirements.txt`**：
```txt
rdagent>=0.4.0
openai>=2.9.0
litellm>=1.80.7
aiohttp>=3.13.2
```

**驗證安裝**：
```bash
docker compose exec backend python -c "from rdagent.scenarios.qlib.experiment.factor_experiment import QlibFactorScenario; print('✅ RD-Agent 已安裝')"
```

### 資料庫遷移

**已包含的資料表**：
- `rdagent_tasks` - RD-Agent 任務記錄
- `generated_factors` - 生成的因子結果

**執行遷移**：
```bash
docker compose exec backend alembic upgrade head
```

---

## 功能使用

### 1. 因子挖掘（Factor Mining）

**功能**：使用 LLM 自動生成量化因子

#### 前端使用

1. 進入「自動研發」頁面：`http://localhost:3000/rdagent`
2. 點擊「新增任務」按鈕
3. 選擇「因子挖掘」
4. 填寫參數：
   - **研究目標**：描述您想要的因子類型（如："找出台股中的動量因子"）
   - **股票池**：選擇股票範圍（如："台股全市場"）
   - **最多生成幾個因子**：1-20 個（建議 3-5 個）
   - **LLM 模型**：gpt-4（預設）
   - **最大迭代次數**：1-10 次（建議 3-5 次）
5. 提交任務
6. 等待 LLM 生成因子（約 5-15 分鐘）
7. 查看生成的因子清單

#### API 使用

```bash
# 創建因子挖掘任務
curl -X POST http://localhost:8000/api/v1/rdagent/factor-mining \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "research_goal": "找出台股中的動量因子，適合短期交易",
    "stock_pool": "台股全市場",
    "max_factors": 5,
    "llm_model": "gpt-4",
    "max_iterations": 3
  }'

# 查看任務狀態
curl http://localhost:8000/api/v1/rdagent/tasks/{task_id} \
  -H "Authorization: Bearer $TOKEN"

# 獲取生成的因子
curl http://localhost:8000/api/v1/rdagent/factors \
  -H "Authorization: Bearer $TOKEN"
```

#### 生成因子範例

**研究目標**："找出台股中的動量因子"

**生成的因子**：
```python
# 因子 1：5 日動量
formula = "($close / Ref($close, 5) - 1)"
ic = 0.032
icir = 1.25
sharpe_ratio = 1.8
annual_return = 0.15

# 因子 2：成交量加權動量
formula = "($close / Ref($close, 5) - 1) * Log($volume / Mean($volume, 20))"
ic = 0.045
icir = 1.67
sharpe_ratio = 2.1
annual_return = 0.22

# 因子 3：價格相對位置
formula = "($close - Min($low, 20)) / (Max($high, 20) - Min($low, 20))"
ic = 0.028
icir = 1.12
sharpe_ratio = 1.5
annual_return = 0.12
```

### 2. 策略優化（Strategy Optimization）

**功能**：基於回測結果自動優化現有策略

**使用方式**：
```bash
# 創建策略優化任務
curl -X POST http://localhost:8000/api/v1/rdagent/strategy-optimization \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": 123,
    "optimization_goal": "提升 Sharpe Ratio 至 2.0 以上",
    "llm_model": "gpt-4",
    "max_iterations": 5
  }'
```

**優化流程**：
1. 分析現有策略代碼和回測結果
2. 識別改進機會（參數調整、因子優化、風險控制）
3. 生成優化建議
4. 自動執行回測驗證
5. 迭代改進直到達成目標或達到最大迭代次數

### 3. 任務管理

```bash
# 獲取所有任務
GET /api/v1/rdagent/tasks

# 獲取任務詳情（包含生成的因子）
GET /api/v1/rdagent/tasks/{task_id}

# 刪除任務
DELETE /api/v1/rdagent/tasks/{task_id}
```

---

## 因子整合

### 查看因子代碼

在「自動研發」頁面，點擊「查看代碼」按鈕展開因子的 Python 實作：

```python
# momentum_5d 因子代碼範例
import pandas as pd
import numpy as np
from qlib.data import D

def calculate_momentum_5d(stock_id: str, start_date: str, end_date: str):
    """計算 5 日動量因子"""

    # 使用 Qlib 表達式引擎
    fields = ['($close / Ref($close, 5) - 1)']

    df = D.features(
        instruments=[stock_id],
        fields=fields,
        start_time=start_date,
        end_time=end_date
    )

    return df.iloc[:, 0]  # 返回因子值序列
```

### 插入因子到策略

RD-Agent 生成的因子可插入到 Backtrader 或 Qlib 策略中。

#### 插入到 Backtrader 策略

1. 在策略列表頁面點擊「建立新策略」
2. 選擇引擎類型：**Backtrader**
3. 切換到「RD-Agent 因子」分頁
4. 選擇想要的因子
5. 點擊「⭐ 插入因子」按鈕（推薦）或「🔄 替換策略」

**自動轉換範例**：

RD-Agent 因子（Qlib 格式）：
```python
'($close / Ref($close, 5) - 1)'
```

轉換為 Backtrader 代碼：
```python
class MomentumStrategy(bt.Strategy):
    params = (
        ('momentum_period', 5),
        ('buy_threshold', 0.05),
    )

    def __init__(self):
        # 計算 5 日動量因子
        self.momentum = (
            (self.data.close - self.data.close(-self.params.momentum_period)) /
            self.data.close(-self.params.momentum_period)
        )

    def next(self):
        if not self.position:
            if self.momentum[0] > self.params.buy_threshold:
                self.buy()
        else:
            if self.momentum[0] < -self.params.buy_threshold:
                self.sell()
```

#### 插入到 Qlib 策略

1. 在策略列表頁面點擊「建立新策略」
2. 選擇引擎類型：**Qlib ML**
3. 切換到「RD-Agent 因子」分頁
4. 選擇想要的因子
5. 點擊「⭐ 插入因子」按鈕

**直接插入 QLIB_FIELDS**：

```python
QLIB_FIELDS = [
    '($close / Ref($close, 5) - 1)',  # RD-Agent 動量因子
    '($close / Ref($close, 10) - 1)', # RD-Agent 中期動量
    'Mean($close, 20)',                # 現有因子
]
```

### 三種整合模式

1. **🔄 替換策略**：生成完整的策略框架（適合新手）
2. **⭐ 插入因子**：智慧合併到現有策略（推薦）
3. **➕ 追加代碼**：在末尾追加因子資訊（參考用）

詳見：[README.md - 策略範本整合系統](../README.md#策略範本整合系統)

---

## Docker 依賴問題

### 問題描述

RD-Agent 在執行因子代碼時**需要 Docker** 來建立隔離的執行環境：

```python
# rdagent/utils/env.py
client = docker.from_env()  # ← 嘗試連接 Docker daemon
```

**如果未配置**，會出現錯誤：
```
docker.errors.DockerException: Error while fetching server API version
```

### 解決方案

#### 方案 1：掛載 Docker Socket（適合生產環境）

**優點**：
- 完整支援 RD-Agent 所有功能
- 代碼在隔離環境中執行（安全）

**缺點**：
- 安全風險：容器可完全控制主機 Docker
- 需要重啟服務

**實作步驟**：

1. 編輯 `docker-compose.yml`：
```yaml
services:
  backend:
    volumes:
      - ./backend:/app
      - /var/run/docker.sock:/var/run/docker.sock  # ← 新增此行
```

2. 重啟服務：
```bash
docker compose down
docker compose up -d
```

3. 設定環境變數：
```bash
# .env
RDAGENT_ENABLE_DOCKER=true
```

4. 驗證：
```bash
docker compose exec backend python -c "import docker; client = docker.from_env(); print('✅ Docker 可訪問')"
```

#### 方案 2：禁用 Docker 隔離（適合開發/測試）

**優點**：
- 無需額外配置
- 執行速度更快

**缺點**：
- 代碼直接在 backend 容器內執行（安全性較低）
- 部分 RD-Agent 功能可能受限

**實作步驟**：

1. 設定環境變數：
```bash
# .env
RDAGENT_ENABLE_DOCKER=false
```

2. 重啟服務：
```bash
docker compose restart backend celery-worker
```

**當前預設**：使用方案 2（RDAGENT_ENABLE_DOCKER=false）

### 安全考量

**掛載 Docker Socket 的風險**：
- 容器內的進程可以創建、修改、刪除主機上的所有容器
- 可能被用於逃逸容器、提權到主機 root
- 僅在受信任環境使用（如私有伺服器、內網環境）

**最佳實踐**：
- 開發/測試環境：禁用 Docker 隔離
- 生產環境：啟用 Docker 隔離，並配置嚴格的網路隔離和訪問控制

---

## 故障排查

### 常見問題

#### 1. RD-Agent 導入失敗

**症狀**：
```python
ModuleNotFoundError: No module named 'rdagent'
```

**解決方案**：
```bash
# 1. 確認套件已安裝
docker compose exec backend pip list | grep rdagent

# 2. 重新安裝（如果未安裝）
docker compose exec backend pip install rdagent>=0.4.0

# 3. 重啟服務
docker compose restart backend celery-worker
```

#### 2. OpenAI API Key 錯誤

**症狀**：
```
openai.error.AuthenticationError: Invalid API key
```

**解決方案**：
```bash
# 1. 檢查 .env 配置
cat .env | grep OPENAI_API_KEY

# 2. 驗證 API Key 有效性
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# 3. 重新設定並重啟
docker compose restart backend celery-worker
```

#### 3. 因子測試失敗

**症狀**：
```
ValueError: cannot find stock data
```

**解決方案**：
```bash
# 1. 確認 Qlib 數據已同步
ls /data/qlib/tw_stock_v2/features/2330/

# 2. 重新同步（如果缺失）
./scripts/sync-qlib-smart.sh

# 3. 驗證 Qlib 配置
docker compose exec backend python -c "import qlib; qlib.init(provider_uri='/data/qlib/tw_stock_v2'); print('✅ Qlib OK')"
```

#### 4. 任務卡在 pending 狀態

**症狀**：
任務提交後長時間停留在 `pending` 狀態

**解決方案**：
```bash
# 1. 檢查 Celery worker 是否運行
docker compose ps celery-worker

# 2. 查看 worker 日誌
docker compose logs celery-worker --tail 50

# 3. 重啟 worker
docker compose restart celery-worker

# 4. 檢查任務是否已註冊
docker compose exec backend celery -A app.core.celery_app inspect registered | grep rdagent
```

#### 5. 速率限制錯誤

**症狀**：
```
HTTP 429: Too Many Requests
```

**解決方案**：
```bash
# 開發/測試環境：重置速率限制
./scripts/reset-rate-limit-quick.sh

# 或等待時間窗口結束（因子挖掘：1 小時）
```

**當前限制**：
- 因子挖掘：3 requests/hour
- 策略優化：5 requests/hour

#### 6. LLM 調用超時

**症狀**：
```
Timeout error: LLM request timeout
```

**解決方案**：
1. 檢查網路連接（OpenAI API 是否可訪問）
2. 嘗試降低 `max_iterations` 參數
3. 使用更快的模型（如 gpt-3.5-turbo）
4. 檢查 OpenAI API 配額是否充足

### 日誌調試

```bash
# 查看 RD-Agent 任務日誌
docker compose logs celery-worker | grep -i rdagent

# 查看詳細錯誤堆棧
docker compose logs backend --tail 100 | grep -A 10 "ERROR"

# 查看 LLM API 調用
docker compose logs celery-worker | grep -i "openai\|llm"
```

---

## 效能優化

### 加速因子生成

1. **使用 Qlib 本地數據**：避免 API fallback，速度提升 3-10 倍
2. **限制迭代次數**：3-5 次通常已足夠
3. **精確研究目標**：明確的目標可減少無效嘗試
4. **批次處理**：一次生成 3-5 個因子而非單個

### 降低成本

1. **使用 gpt-3.5-turbo**：成本約為 gpt-4 的 1/10
2. **限制因子數量**：3-5 個因子通常比 10-20 個更有效
3. **本地快取**：已生成的因子可重複使用
4. **測試模式**：開發時使用較小的數據集

---

## 最佳實踐

### 研究目標撰寫

**✅ 好的研究目標**：
- "找出台股中的短期動量因子，適合 1-5 天持有期"
- "發現價量背離的反轉因子，用於逢低買入"
- "挖掘基於波動率的突破因子，適合趨勢跟隨策略"

**❌ 不好的研究目標**：
- "找出好因子"（太模糊）
- "賺大錢的因子"（不具體）
- "Alpha 因子"（過於廣泛）

### 因子評估

**關鍵指標**：
- **IC (Information Coefficient)**：因子與未來收益的相關性
  - > 0.03：可用
  - > 0.05：優秀
  - > 0.10：極佳
- **ICIR (IC / Std(IC))**：因子穩定性
  - > 1.0：可用
  - > 1.5：優秀
  - > 2.0：極佳
- **Sharpe Ratio**：風險調整後收益
  - > 1.0：可用
  - > 1.5：優秀
  - > 2.0：極佳

### 因子組合

- **多因子策略**：組合 3-5 個低相關因子
- **風險分散**：包含不同類型（動量、反轉、波動率）
- **回測驗證**：必須經過充分回測驗證

---

## 相關文檔

- [CLAUDE.md](../CLAUDE.md) - RD-Agent 整合章節
- [README.md](../README.md) - 專案概述
- [docs/QLIB.md](./QLIB.md) - Qlib 引擎指南
- [docs/GUIDES.md](./GUIDES.md) - 使用指南
- [RD-Agent 官方文檔](https://github.com/microsoft/RD-Agent) - Microsoft RD-Agent GitHub
