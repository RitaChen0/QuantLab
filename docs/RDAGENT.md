# RD-Agent 完整指南

本文檔整合了 RD-Agent (Research & Development Agent) 在 QuantLab 中的完整使用、配置和故障排查指南。

## 目錄

- [RD-Agent 簡介](#rdagent-簡介)
- [5 分鐘快速上手](#5-分鐘快速上手)（新增）
- [環境配置](#環境配置)
- [功能使用](#功能使用)
- [因子整合](#因子整合)
- [因子評估](#因子評估)（新增）
- [Docker 依賴問題](#docker-依賴問題)
- [故障排查](#故障排查)
- [效能優化](#效能優化)
- [最佳實踐](#最佳實踐)

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

## 5 分鐘快速上手

這是一個完整的端到端工作流程，讓你快速體驗 RD-Agent 的因子挖掘和評估功能。

### 第一步：生成因子（2 分鐘）

1. **前往「自動研發」頁面**：
   ```
   http://localhost:3000/rdagent
   ```

2. **填寫研究目標**：
   ```
   找出台股中的短期動量因子，適合 1-5 天持有期
   ```

3. **調整參數**：
   - 因子數量：3
   - 迭代次數：3
   - LLM 模型：gpt-4-turbo

4. **啟動挖掘**：
   - 點擊「🚀 啟動挖掘」按鈕
   - 等待 3-5 分鐘（LLM 生成和測試）
   - 觀察即時日誌顯示進度

### 第二步：查看評估結果（1 分鐘）

1. **等待自動評估**：
   - 因子生成後會自動觸發評估（30-60 秒）
   - 無需手動操作，系統自動計算 IC/Sharpe

2. **查看因子指標**：
   ```
   ✅ momentum_5d
      IC: 0.0374  |  ICIR: 0.0824  |  Sharpe: -0.35  |  年化: -24.86%
   ```

3. **理解指標含義**：
   - **IC = 0.0374**：因子有預測能力（> 0.03 可用）
   - **ICIR = 0.0824**：穩定性較低（< 1.0，可能需要組合其他因子）
   - **Sharpe = -0.35**：直接交易表現不佳（需優化交易規則）
   - **年化 = -24.86%**：簡單策略虧損（IC 正但 Sharpe 負說明需要改進進出場邏輯）

### 第三步：IC 衰減分析（1 分鐘）

1. **點擊「📈 評估歷史」按鈕**

2. **查看 IC 衰減曲線**：
   ```
   IC 值
     0.08│     ●
         │    ╱ ╲
     0.05│   ╱   ╲
         │  ╱     ╲___
     0.02│ ╱          ╲___
         └─────────────────→ 持有期
           1  3  5  10  15
   ```

3. **智慧分析結果**：
   ```
   📊 智慧分析
   最佳持有期：3 天
   最大 IC：0.065
   因子類型：短期因子
   ```

4. **解讀建議**：
   - **短期因子**：適合 1-5 天持有，不適合長期投資
   - **最佳持有期 = 3 天**：策略應在 T+3 平倉
   - **IC 衰減快速**：避免長期持有，否則預測力失效

### 第四步：插入策略（1 分鐘）

1. **前往「策略列表」頁面**
   ```
   http://localhost:3000/strategies
   ```

2. **建立新策略**：
   - 引擎類型：**Backtrader** 或 **Qlib ML**
   - 切換到「RD-Agent 因子」分頁

3. **選擇因子並插入**：
   - 勾選 `momentum_5d`
   - 點擊「⭐ 插入因子」（智慧合併到現有代碼）

4. **調整持有期**（根據 IC 衰減分析）：
   ```python
   # Backtrader 範例
   class MomentumStrategy(bt.Strategy):
       params = (
           ('momentum_period', 5),
           ('holding_period', 3),  # ← 根據 IC 衰減設置為 3 天
       )
   ```

5. **執行回測**：
   - 驗證因子在實際策略中的表現
   - 比較 Sharpe Ratio 是否改善

### 完成！你已經學會了：

- ✅ 使用 AI 生成量化因子（GPT-4 驅動）
- ✅ 理解因子預測能力（IC > 0.03 可用）
- ✅ 確定最佳持有期（IC 衰減曲線）
- ✅ 整合到交易策略並回測

### 下一步建議

**初學者**：
1. 嘗試不同的研究目標（反轉因子、波動率因子）
2. 調整迭代次數觀察因子品質變化
3. 學習解讀 IC vs Sharpe 的差異

**進階用戶**：
1. 生成多個低相關因子組合（多因子策略）
2. 使用不同股票池評估（大型股 vs 小型股）
3. 結合基本面數據生成複合因子
4. 調整交易規則優化 Sharpe Ratio

**專業用戶**：
1. 實作自定義因子評估邏輯
2. 整合 RD-Agent 到 CI/CD 流程
3. 建立因子庫和版本管理
4. 開發因子組合優化器

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

## 因子評估

RD-Agent 生成因子後，可通過評估系統驗證因子有效性。系統提供**自動評估**和**手動評估**兩種方式，並支援 IC 衰減分析和歷史記錄追蹤。

### 自動評估機制

**觸發時機**：因子生成完成後自動執行

**流程**：
```
因子生成 → 保存到資料庫 → 觸發評估任務 → 計算 IC/Sharpe → 更新因子指標
```

**計算指標**：
- **IC (Information Coefficient)**：因子與未來收益的相關性
- **ICIR (IC Information Ratio)**：IC / Std(IC)，衡量因子穩定性
- **Rank IC**：排序相關性（更穩健）
- **Rank ICIR**：Rank IC / Std(Rank IC)
- **Sharpe Ratio**：風險調整後收益
- **Annual Return**：年化報酬率

**實作位置**：
- 評估任務：`backend/app/tasks/factor_evaluation_tasks.py`
- 評估邏輯：`backend/app/services/factor_evaluation_service.py`

**查看自動評估結果**：
1. 前往「自動研發」頁面
2. 在因子卡片中查看 IC、ICIR、Sharpe Ratio 等指標
3. 指標為 NULL 表示評估尚未完成或失敗

### 手動評估因子

**使用場景**：
- 重新評估已生成的因子
- 使用不同股票池評估
- 驗證因子在不同時期的表現

**操作步驟**：
1. 前往「自動研發」頁面
2. 找到想評估的因子卡片
3. 點擊「📊 評估因子」按鈕
4. 等待評估完成（約 30-60 秒）
5. 查看彈出的評估結果

**評估參數**：
- **股票池**：預設為 `all`（全市場）
- **評估期間**：預設為最近 2 年數據
- **持有期**：1-20 天（計算 IC 衰減）

**注意事項**：
- 評估期間請勿重複點擊按鈕（防止重複評估）
- 如果評估失敗，請檢查 Qlib 數據是否完整
- 評估結果會自動保存到 `factor_evaluations` 表

### 評估歷史與 IC 衰減分析

**查看評估歷史**：
1. 在因子卡片中點擊「📈 評估歷史」按鈕
2. 進入評估詳情頁面

**頁面功能**：

#### 1. 評估歷史表格
顯示所有評估記錄，包含：
- 評估時間
- IC / ICIR / Rank IC / Rank ICIR
- Sharpe Ratio / 年化報酬
- 使用的股票池

#### 2. IC 衰減曲線
可視化展示因子在不同持有期的表現：

```
IC 值
  │
  │     ●
  │    ╱ ╲
  │   ╱   ╲
  │  ╱     ╲___
  │ ╱          ╲___
  └─────────────────→ 持有期（天）
    1  5  10  15  20
```

**解讀方式**：
- **短期因子**：IC 在 1-5 天達到峰值，之後快速衰減
- **中期因子**：IC 在 5-10 天達到峰值
- **長期因子**：IC 緩慢衰減，適合長期持有

#### 3. 智慧分析
系統自動分析因子特性：

- **最佳持有期**：IC 達到最大值的持有天數
- **最大 IC**：最佳持有期對應的 IC 值
- **因子類型**：根據衰減速度分類（短期/中期/長期）

**分類邏輯**：
```python
衰減率 = (首日 IC - 末日 IC) / 首日 IC

衰減率 > 50%  → 短期因子（適合 1-5 天）
衰減率 > 20%  → 中期因子（適合 5-10 天）
衰減率 ≤ 20%  → 長期因子（適合 10+ 天）
```

### API 端點

**評估因子**：
```bash
POST /api/factor-evaluation/evaluate
Authorization: Bearer {token}
Content-Type: application/json

{
  "factor_id": 17,
  "stock_pool": "all",
  "start_date": "2023-01-01",  # 可選
  "end_date": "2025-12-20"      # 可選
}
```

**獲取評估歷史**：
```bash
GET /api/factor-evaluation/factors/{factor_id}/evaluations
Authorization: Bearer {token}
```

**獲取 IC 衰減數據**：
```bash
GET /api/factor-evaluation/factors/{factor_id}/ic-decay
Authorization: Bearer {token}
```

### 評估結果範例

```json
{
  "id": 23,
  "factor_id": 17,
  "ic": 0.0374,
  "icir": 0.0824,
  "rank_ic": 0.0412,
  "rank_icir": 0.0891,
  "sharpe_ratio": -0.3464,
  "annual_return": -0.2486,
  "stock_pool": "all",
  "start_date": "2023-12-20",
  "end_date": "2025-12-20",
  "created_at": "2025-12-22T15:30:00Z"
}
```

**指標解讀**：
- IC = 0.0374：因子具有正向預測能力（> 0.03 可用）
- ICIR = 0.0824：穩定性較低（< 1.0）
- Sharpe = -0.35：策略回測表現不佳
- 結論：因子有預測性但需優化交易規則

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

#### 7. 因子評估失敗

**症狀**：
```
ValueError: Factor evaluation failed
```

**常見原因與解決方案**：

**7.1 Qlib 數據缺失**：
```bash
# 檢查 Qlib 數據完整性
ls /data/qlib/tw_stock_v2/features/2330/

# 重新同步 Qlib 數據
bash scripts/sync-qlib-smart.sh
```

**7.2 因子公式錯誤**：
```bash
# 查看因子公式
docker compose exec postgres psql -U quantlab quantlab -c \
  "SELECT id, name, formula FROM generated_factors WHERE id = 17;"

# 檢查公式語法是否符合 Qlib 規範
# 例如：($close / Ref($close, 5) - 1) 而非 close / close[5]
```

**7.3 時區相關錯誤**：
```bash
# 檢查是否有 timezone import 錯誤
docker compose logs celery-worker | grep -i "timezone\|utc"

# 確認 factor_evaluation_service.py 包含正確 import
# from datetime import datetime, timedelta, timezone
```

**7.4 評估指標為 NULL**：
```bash
# 檢查評估記錄
docker compose exec postgres psql -U quantlab quantlab -c \
  "SELECT id, factor_id, ic, icir, created_at
   FROM factor_evaluations
   ORDER BY created_at DESC LIMIT 5;"

# 手動觸發指標同步
docker compose exec backend python -c "
from app.core.celery_app import celery_app
from app.tasks.factor_evaluation_tasks import update_factor_metrics
result = update_factor_metrics.delay(factor_id=17)
print(f'Task ID: {result.id}')
"
```

#### 8. IC 衰減圖表無法顯示

**症狀**：評估歷史頁面空白或圖表不顯示

**解決方案**：

**8.1 檢查 Chart.js 載入**：
```javascript
// 瀏覽器 Console 檢查
console.log(typeof Chart)  // 應該是 'function'
```

**8.2 檢查評估數據**：
```bash
# 確認 IC decay 數據存在
curl -H "Authorization: Bearer {token}" \
  http://localhost:8000/api/factor-evaluation/factors/17/ic-decay
```

**8.3 清除瀏覽器快取**：
```bash
# 前端重新編譯
docker compose restart frontend
```

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

### 因子評估最佳實踐

#### 關鍵指標解讀

**IC (Information Coefficient)**：因子與未來收益的相關性
- **> 0.03**：可用（具有基本預測能力）
- **> 0.05**：優秀（穩定的預測性）
- **> 0.10**：極佳（罕見，需警惕過擬合）

**ICIR (IC Information Ratio)**：IC / Std(IC)，衡量因子穩定性
- **> 1.0**：可用（穩定性尚可）
- **> 1.5**：優秀（高穩定性）
- **> 2.0**：極佳（極高穩定性）

**Sharpe Ratio**：風險調整後收益
- **> 1.0**：可用（回測表現良好）
- **> 1.5**：優秀（風險收益比佳）
- **> 2.0**：極佳（需驗證是否過擬合）

**Rank IC vs IC**：
- **Rank IC** 對異常值更穩健，適合評估因子排序能力
- **IC** 對因子絕對值更敏感，適合評估因子預測能力
- 通常 Rank IC > IC，如果 Rank IC << IC 需警惕極端值影響

#### 評估工作流程

**1. 自動評估**（推薦）：
```
生成因子 → 等待自動評估（30-60秒） → 查看因子卡片指標
```

**2. 手動重新評估**：
- 因子公式修改後
- 懷疑數據更新影響評估結果
- 需要使用不同股票池驗證

**3. IC 衰減分析**：
```
點擊「評估歷史」 → 查看 IC 衰減曲線 → 確定最佳持有期
```

#### 因子篩選標準

**必須通過**：
- IC > 0.03 且 ICIR > 0.5
- IC 衰減曲線穩定（無劇烈波動）
- 在不同時期評估結果一致

**優先選擇**：
- IC > 0.05 且 ICIR > 1.0
- Rank IC 與 IC 方向一致
- 最佳持有期與策略週期匹配

**警惕過擬合**：
- IC > 0.15（台股市場極少見）
- Sharpe Ratio > 3.0（回測可能過度優化）
- IC 衰減曲線異常（如先降後升）

#### 使用 IC 衰減優化策略

**範例 1：短期因子**
```
IC 衰減：1天=0.08, 3天=0.05, 5天=0.02
建議：T+1 或 T+2 平倉，避免長期持有
策略：短線動量策略
```

**範例 2：中期因子**
```
IC 衰減：1天=0.04, 5天=0.06, 10天=0.05
建議：5-7 天平倉（最佳持有期）
策略：波段交易策略
```

**範例 3：長期因子**
```
IC 衰減：1天=0.05, 10天=0.04, 20天=0.04
建議：可長期持有，適合價值投資
策略：基本面量化策略
```

### 因子組合

- **多因子策略**：組合 3-5 個低相關因子
- **風險分散**：包含不同類型（動量、反轉、波動率）
- **回測驗證**：必須經過充分回測驗證

---

## 相關文檔

### 官方文檔
- [RD-Agent 官方文檔](https://github.com/microsoft/RD-Agent) - Microsoft RD-Agent GitHub
- [Qlib 官方文檔](https://qlib.readthedocs.io/) - Microsoft Qlib

### QuantLab 文檔
- [CLAUDE.md](../CLAUDE.md) - RD-Agent 整合章節
- [README.md](../README.md) - 專案概述
- [docs/QLIB.md](./QLIB.md) - Qlib 引擎指南
- [docs/GUIDES.md](./GUIDES.md) - 使用指南

### 實作報告
- [RDAGENT_AUTO_EVALUATION_IMPLEMENTATION_REPORT.md](../Document/RDAGENT_AUTO_EVALUATION_IMPLEMENTATION_REPORT.md) - 自動評估實作報告
- [RDAGENT_FRONTEND_INTEGRATION_IMPLEMENTATION_REPORT.md](../Document/RDAGENT_FRONTEND_INTEGRATION_IMPLEMENTATION_REPORT.md) - 前端整合實作報告
- [RDAGENT_FACTOR_EVALUATION_VERIFICATION_REPORT.md](../Document/RDAGENT_FACTOR_EVALUATION_VERIFICATION_REPORT.md) - 評估功能驗證報告
- [RDAGENT_MONITORING_ALERT_REPORT.md](../Document/RDAGENT_MONITORING_ALERT_REPORT.md) - 監控告警實作報告
- [RDAGENT_TIMEOUT_CONFIG_REPORT.md](../Document/RDAGENT_TIMEOUT_CONFIG_REPORT.md) - 超時配置報告
- [RDAGENT_TASK13_CLEANUP_REPORT.md](../Document/RDAGENT_TASK13_CLEANUP_REPORT.md) - Task 13 清理報告
