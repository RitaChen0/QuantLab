# RD-Agent 任務超時配置報告

> 📅 **配置日期**: 2025-12-29
> 🎯 **目標**: 為 RD-Agent 任務添加超時配置，防止任務永久卡住
> ✅ **狀態**: 完成

---

## 📊 背景分析

### 問題起因

在清理 Task 13 時發現，該任務卡住運行了 **97.8 小時（4 天）**，沒有任何超時機制自動終止。這暴露了系統缺乏任務級別的超時保護。

### 歷史數據分析

基於現有 8 個已完成的 RD-Agent 任務，進行了執行時間統計分析：

| 任務類型 | 樣本數 | 平均時間 | 最小值 | 最大值 | P95 分位數 |
|---------|--------|---------|--------|--------|-----------|
| **FACTOR_MINING** | 5 | 11.9 分鐘 | 0.1 分鐘 | 38.6 分鐘 | 32.7 分鐘 |
| **MODEL_GENERATION** | 3 | 0.4 分鐘 | 0.3 分鐘 | 0.6 分鐘 | 0.5 分鐘 |

### 數據洞察

1. **FACTOR_MINING（因子挖掘）**：
   - 執行時間變化較大（0.1 - 38.6 分鐘）
   - P95 為 32.7 分鐘，表示 95% 的任務在 33 分鐘內完成
   - 最長執行時間 38.6 分鐘（正常範圍）

2. **MODEL_GENERATION（模型生成）**：
   - 執行時間非常穩定（0.3 - 0.6 分鐘）
   - P95 為 0.5 分鐘，幾乎所有任務都在 1 分鐘內完成
   - 極快的執行速度

3. **STRATEGY_OPTIMIZATION（策略優化）**：
   - 暫無歷史數據
   - 預估與 MODEL_GENERATION 類似

---

## 🔧 超時配置設計

### 設計原則

1. **安全優先**：超時設定遠超歷史最大值，避免誤殺正常任務
2. **數據驅動**：基於 P95 分位數 + 合理緩衝
3. **分層防護**：軟超時 + 硬超時 + 每日清理
4. **漸進式**：軟超時先發警告，硬超時再強制終止

### 最終配置

| 任務名稱 | 軟超時 | 硬超時 | P95 | 緩衝倍數 |
|---------|-------|--------|-----|---------|
| `run_factor_mining_task` | 55 分鐘 | 60 分鐘 | 33 分鐘 | 1.8x |
| `run_model_generation_task` | 28 分鐘 | 30 分鐘 | 0.5 分鐘 | 60x |
| `run_strategy_optimization_task` | 28 分鐘 | 30 分鐘 | - | (預估) |

**配置文件**：`backend/app/core/celery_app.py`

```python
task_annotations={
    # RD-Agent 任務超時配置（基於歷史數據分析）
    # FACTOR_MINING: 平均 12 分鐘，P95 33 分鐘，最大 39 分鐘
    'app.tasks.run_factor_mining_task': {
        'time_limit': 3600,      # 1 小時硬限制
        'soft_time_limit': 3300,  # 55 分鐘軟限制
    },
    # MODEL_GENERATION: 平均 0.4 分鐘，P95 0.5 分鐘，最大 0.6 分鐘
    'app.tasks.run_model_generation_task': {
        'time_limit': 1800,      # 30 分鐘硬限制
        'soft_time_limit': 1680,  # 28 分鐘軟限制
    },
    # STRATEGY_OPTIMIZATION: 預估與 MODEL_GENERATION 類似
    'app.tasks.run_strategy_optimization_task': {
        'time_limit': 1800,      # 30 分鐘硬限制
        'soft_time_limit': 1680,  # 28 分鐘軟限制
    }
}
```

---

## 🛡️ 三層防護機制

### 第 1 層：Celery 軟超時（Soft Time Limit）

**機制**：
- 任務執行時間達到 `soft_time_limit` 時觸發
- 拋出 `SoftTimeLimitExceeded` 異常
- 任務代碼可以捕獲並優雅退出

**作用**：
- 給任務機會保存進度
- 清理資源（關閉資料庫連接、檔案等）
- 記錄詳細錯誤訊息

**範例**：
```python
from celery.exceptions import SoftTimeLimitExceeded

@celery_app.task(bind=True)
def run_factor_mining_task(self, task_id):
    try:
        # 執行任務邏輯
        pass
    except SoftTimeLimitExceeded:
        logger.warning(f"Task {task_id} approaching timeout, cleaning up...")
        # 保存進度
        # 清理資源
        raise
```

### 第 2 層：Celery 硬超時（Time Limit）

**機制**：
- 任務執行時間達到 `time_limit` 時觸發
- 強制終止任務進程（SIGKILL）
- **無法捕獲**，立即停止

**作用**：
- 最終保護措施
- 確保任務不會無限期執行
- 釋放 Worker 資源

**觸發條件**：
- 軟超時後任務未能在 5 分鐘內退出
- 任務無法響應 SoftTimeLimitExceeded

### 第 3 層：每日自動清理（Fallback）

**機制**：
- 每天台北時間 05:30 執行
- 清理 RUNNING 狀態超過 24 小時的任務
- 標記為 FAILED 並記錄錯誤訊息

**作用**：
- 最終兜底機制
- 處理異常情況（如 Worker 崩潰後任務未能正確清理）
- 確保資料庫狀態一致性

**任務名稱**：`cleanup-stuck-rdagent-tasks-daily`

---

## ✅ 實施步驟

### 1. 數據分析
```sql
SELECT
    task_type,
    COUNT(*) as total_tasks,
    ROUND((AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))/60)::numeric, 1) as avg_minutes,
    ROUND((PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (completed_at - started_at)))/60)::numeric, 1) as p95_minutes
FROM rdagent_tasks
WHERE status = 'COMPLETED'
GROUP BY task_type;
```

### 2. 配置更新

**文件**：`backend/app/core/celery_app.py`

**變更**：在 `task_annotations` 中添加三個 RD-Agent 任務的超時配置

### 3. 服務重啟
```bash
docker compose restart celery-worker celery-beat
```

### 4. 配置驗證
```bash
docker compose exec backend celery -A app.core.celery_app inspect conf | grep -A 3 "run_factor_mining_task"
```

**驗證結果**：
```json
"app.tasks.run_factor_mining_task": {
    "soft_time_limit": 3300,
    "time_limit": 3600
}
```

✅ **配置已成功應用**

---

## 📈 預期效果

### 場景 1：正常執行（95% 情況）

**任務**：因子挖掘，執行時間 15 分鐘

```
開始 → 執行 15 分鐘 → 正常完成 ✅
       (遠低於 55 分鐘軟限制)
```

**結果**：無影響，任務正常完成

---

### 場景 2：接近超時（極少數情況）

**任務**：因子挖掘，執行時間 56 分鐘

```
開始 → 執行 55 分鐘 → SoftTimeLimitExceeded ⚠️
       → 優雅退出 (1 分鐘內) → 標記 FAILED
```

**結果**：
- 任務被軟超時機制捕獲
- 保存進度並清理資源
- 標記為 FAILED，記錄「接近超時」

---

### 場景 3：卡死無響應（如 Task 13）

**任務**：因子挖掘，卡死在某個步驟

```
開始 → 執行 55 分鐘 → SoftTimeLimitExceeded ⚠️
       → 無響應 (5 分鐘) → 強制終止 ❌ (60 分鐘)
```

**結果**：
- 軟超時無效（任務卡死）
- 60 分鐘時硬超時強制終止
- Worker 進程被重啟，資源釋放
- **不會再卡住 4 天！** 🎉

---

### 場景 4：極端異常（Worker 崩潰）

**任務**：因子挖掘，Worker 在 30 分鐘時崩潰

```
開始 → 執行 30 分鐘 → Worker 崩潰 💥
       → 任務狀態仍為 RUNNING (資料庫)
       → 次日 05:30 自動清理 🧹 → 標記 FAILED
```

**結果**：
- 硬超時也無法處理（Worker 已崩潰）
- 每日清理任務檢測到異常並清理
- 最遲 24 小時內解決

---

## 📊 對比分析

### 配置前（Task 13 案例）

| 階段 | 時間 | 狀態 | 處理方式 |
|------|------|------|---------|
| 開始執行 | 0 小時 | RUNNING | - |
| 應該完成 | 0.5 小時 | RUNNING | ❌ 無超時保護 |
| 異常卡住 | 1 小時 | RUNNING | ❌ 無超時保護 |
| 繼續卡住 | 24 小時 | RUNNING | ❌ 無自動清理 |
| **發現問題** | **97.8 小時** | **RUNNING** | ⚠️ 手動清理 |

**問題**：
- ❌ 無任務級超時保護
- ❌ 無自動清理機制
- ❌ 需要手動介入

---

### 配置後（新機制）

| 階段 | 時間 | 狀態 | 處理方式 |
|------|------|------|---------|
| 開始執行 | 0 小時 | RUNNING | - |
| 應該完成 | 0.5 小時 | RUNNING | ✅ 正常範圍內 |
| 異常卡住 | 1 小時 | **FAILED** | ✅ **硬超時強制終止** |
| - | - | - | - |
| - | - | - | - |

**改進**：
- ✅ 1 小時內自動終止
- ✅ 無需人工介入
- ✅ 資源及時釋放

**最壞情況**（Worker 崩潰）：
| 階段 | 時間 | 狀態 | 處理方式 |
|------|------|------|---------|
| Worker 崩潰 | 0.5 小時 | RUNNING | ⚠️ 硬超時無效 |
| 次日清理 | **24 小時** | **FAILED** | ✅ **每日清理兜底** |

**改進**：
- ✅ 最遲 24 小時內清理
- ✅ 自動化處理
- ✅ 資料庫狀態一致

---

## 🔍 監控與驗證

### 查看任務超時配置
```bash
docker compose exec backend celery -A app.core.celery_app inspect conf | \
  grep -A 3 "run_.*_task"
```

### 監控任務執行時間
```sql
-- 查看最近任務執行時間
SELECT
    id,
    task_type,
    status,
    ROUND(EXTRACT(EPOCH FROM (COALESCE(completed_at, NOW()) - started_at))/60, 1) as duration_minutes
FROM rdagent_tasks
WHERE created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;
```

### 檢測接近超時的任務
```sql
-- 查找執行時間超過軟限制的任務
SELECT
    id,
    task_type,
    status,
    started_at,
    ROUND(EXTRACT(EPOCH FROM (NOW() - started_at))/60, 1) as running_minutes
FROM rdagent_tasks
WHERE status = 'RUNNING'
  AND (
    (task_type = 'FACTOR_MINING' AND NOW() - started_at > INTERVAL '55 minutes')
    OR
    (task_type IN ('MODEL_GENERATION', 'STRATEGY_OPTIMIZATION') AND NOW() - started_at > INTERVAL '28 minutes')
  );
```

### 查看 Celery Worker 日誌
```bash
# 查看超時相關日誌
docker compose logs celery-worker | grep -i "timeout\|time limit"

# 查看 RD-Agent 任務日誌
docker compose logs celery-worker | grep -i "rdagent\|factor_mining\|model_generation"
```

---

## 💡 後續優化建議

### 🟡 中優先級

#### 1. 添加超時告警

**目標**：任務接近超時時發送通知

**實作**：
```python
# backend/app/tasks/rdagent_tasks.py
from celery.exceptions import SoftTimeLimitExceeded

@celery_app.task(bind=True)
def run_factor_mining_task(self, task_id):
    try:
        # 任務邏輯
        pass
    except SoftTimeLimitExceeded:
        # 發送告警
        logger.warning(f"⚠️ Task {task_id} approaching timeout!")
        # 可選：發送 Telegram 通知
        # send_telegram_alert(f"RD-Agent task {task_id} timeout warning")
        raise
```

#### 2. 記錄超時統計

**目標**：追蹤超時頻率，優化超時設定

**實作**：
```python
# 在任務完成時記錄統計
task.metadata = {
    "execution_time": execution_seconds,
    "soft_timeout": soft_time_limit,
    "hard_timeout": time_limit,
    "timeout_ratio": execution_seconds / time_limit
}
```

#### 3. 動態調整超時

**目標**：根據任務參數動態調整超時時間

**實作**：
```python
# 複雜任務給予更長超時
if max_iterations > 5:
    time_limit = 7200  # 2 小時
else:
    time_limit = 3600  # 1 小時
```

---

### 🟢 低優先級

#### 4. Prometheus 監控

**指標**：
- `rdagent_task_duration_seconds` - 任務執行時間分佈
- `rdagent_task_timeout_total` - 超時次數
- `rdagent_task_soft_timeout_ratio` - 軟超時比例

#### 5. 前端顯示優化

**功能**：
- 顯示任務剩餘時間
- 超過 50% 超時時間時顯示警告
- 接近超時時顯示紅色提醒

---

## 📚 相關文檔

1. **清理報告**：[RDAGENT_TASK13_CLEANUP_REPORT.md](./RDAGENT_TASK13_CLEANUP_REPORT.md)
   - Task 13 清理過程
   - 自動清理機制說明

2. **使用指南**：[../CLAUDE.md](../CLAUDE.md)
   - RD-Agent 任務清理章節
   - 超時配置說明

3. **Celery 文檔**：
   - [Time Limits](https://docs.celeryq.dev/en/stable/userguide/workers.html#time-limits)
   - [Task Annotations](https://docs.celeryq.dev/en/stable/userguide/configuration.html#task-annotations)

---

## 📝 總結

### 完成項目

1. ✅ 基於歷史數據分析任務執行時間
2. ✅ 設計三層防護機制（軟超時 + 硬超時 + 每日清理）
3. ✅ 配置 RD-Agent 任務專屬超時設定
4. ✅ 重啟服務並驗證配置成功
5. ✅ 更新文檔（CLAUDE.md）

### 關鍵成果

| 指標 | 配置前 | 配置後 |
|------|--------|--------|
| 最長執行時間 | 無限制（4 天+） | 60 分鐘 |
| 自動清理 | 手動（97.8 小時後） | 自動（60 分鐘內） |
| 資源釋放 | 延遲 4 天 | 即時 |
| 防護層級 | 0 層 | 3 層 |

### 預期效果

- 🎯 **防止任務永久卡住**：最遲 1 小時內自動終止
- 🚀 **及時釋放資源**：Worker 不會被長時間佔用
- 🛡️ **三層保護機制**：即使某層失效，仍有兜底
- 📊 **數據驅動配置**：基於實際執行時間，避免誤殺

---

**報告人**: Claude Code
**審核**: 待用戶確認
**版本**: v1.0
**最後更新**: 2025-12-29 13:10 UTC
