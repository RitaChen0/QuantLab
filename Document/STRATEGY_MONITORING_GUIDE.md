# 策略實盤監控功能使用指南

> **功能說明**: 自動監控 ACTIVE 狀態的策略，檢測買賣信號並通過 Telegram 通知用戶

**最後更新**: 2025-12-16

---

## 📋 功能概述

### 核心功能

1. **自動信號檢測**: 定時執行 ACTIVE 狀態的策略，檢測買入/賣出信號
2. **Telegram 通知**: 檢測到信號後立即發送 Telegram 通知**（只通知策略擁有者）**
3. **重複信號過濾**: 15 分鐘內相同股票相同方向的信號只通知一次
4. **全時段監控**: 覆蓋股票交易時段 + 台指期夜盤時段

### ⚠️ 隱私保護

**重要**: 每個策略的信號**只會通知給該策略的擁有者**，不會通知其他用戶。

- 用戶 A 的策略產生的信號 → 只發送給用戶 A
- 用戶 B 的策略產生的信號 → 只發送給用戶 B
- 確保每個用戶只收到自己策略的通知

### 監控時間表

| 時段 | 時間範圍 | 檢測頻率 | 說明 |
|------|---------|---------|------|
| **股票交易時段** | 09:00-13:00 | 每 15 分鐘 | 股票市場開盤時間 |
| **台指期夜盤 (1)** | 15:00-23:59 | 每 15 分鐘 | 期貨夜盤前半段 |
| **台指期夜盤 (2)** | 00:00-05:00 | 每 15 分鐘 | 期貨夜盤後半段 |

---

## 🚀 快速開始

### 1. 啟用策略監控

在前端策略管理頁面，將策略狀態設置為 **ACTIVE**：

```
策略列表 → 選擇策略 → 狀態改為 "已啟用"
```

### 2. 確保策略配置正確

策略必須包含以下配置：

```json
{
  "stocks": ["2330", "2317", "2454"]  // 必須配置股票清單
}
```

### 3. 綁定 Telegram

確保已綁定 Telegram 帳號：

```
個人設置 → Telegram 通知 → 綁定帳號
```

### 4. 等待信號通知

系統會自動在每個 15 分鐘檢查點執行策略並發送通知。

---

## 📊 信號通知格式

當檢測到買賣信號時，您會收到以下格式的 Telegram 通知：

```
🔔 交易信號提醒

策略：均線交叉策略
股票：2330
信號：🟢 買入
價格：NT$ 580.00
時間：2025-12-16 10:30:00

這是系統自動檢測的信號，請謹慎判斷後再決定是否交易。
```

---

## ⚙️ 系統架構

### 核心組件

1. **StrategySignalDetector** (`backend/app/services/strategy_signal_detector.py`)
   - 輕量級策略執行引擎
   - 只檢測信號，不進行完整回測
   - 支援 Backtrader 引擎（Qlib 引擎暫不支援）

2. **Celery 定時任務** (`backend/app/tasks/strategy_monitoring.py`)
   - `monitor_active_strategies`: 主監控任務
   - `cleanup_old_signals`: 清理舊信號記錄（每週執行）

3. **資料表** (`strategy_signals`)
   - 記錄所有檢測到的信號
   - 用於重複信號過濾
   - 保留 30 天歷史記錄

### 信號檢測流程

```
1. Celery Beat 觸發定時任務（每 15 分鐘）
   ↓
2. 查詢所有 ACTIVE 狀態的策略
   ↓
3. 對每個策略：
   a. 獲取最近 60 天的歷史數據
   b. 執行策略邏輯（只運行最後一個 bar）
   c. 檢查是否有買入/賣出信號
   ↓
4. 過濾重複信號（15 分鐘內相同股票相同方向）
   ↓
5. 保存信號到資料庫
   ↓
6. 發送 Telegram 通知
```

---

## 🔧 手動執行命令

### 立即檢測信號（手動測試）

```bash
# 檢測所有 ACTIVE 策略的信號
docker compose exec backend celery -A app.core.celery_app call app.tasks.monitor_active_strategies

# 檢測並指定數據回溯天數
docker compose exec backend celery -A app.core.celery_app call \
  app.tasks.monitor_active_strategies --kwargs '{"lookback_days": 90}'
```

### 測試信號檢測器（不發送通知）

```bash
docker compose exec backend python -c "
from app.db.session import SessionLocal
from app.services.strategy_signal_detector import StrategySignalDetector

db = SessionLocal()
detector = StrategySignalDetector(db)

# 檢測所有 ACTIVE 策略
signals = detector.detect_signals_for_active_strategies(lookback_days=60)
print(f'檢測到 {len(signals)} 個信號')

# 顯示信號詳情
for signal in signals:
    print(f'{signal[\"stock_id\"]} {signal[\"signal_type\"]} @ {signal.get(\"price\", \"N/A\")}')

db.close()
"
```

### 查詢資料庫中的信號記錄

```bash
# 查詢最近 10 筆信號（包含用戶資訊）
docker compose exec postgres psql -U quantlab quantlab -c "
SELECT
  u.username AS user_name,
  s.name AS strategy_name,
  sg.stock_id,
  sg.signal_type,
  sg.price,
  sg.detected_at,
  sg.notified
FROM strategy_signals sg
JOIN strategies s ON sg.strategy_id = s.id
JOIN users u ON sg.user_id = u.id
ORDER BY sg.detected_at DESC
LIMIT 10;
"

# 驗證信號只通知給策略擁有者
docker compose exec postgres psql -U quantlab quantlab -c "
SELECT
  u.username,
  COUNT(*) AS signal_count
FROM strategy_signals sg
JOIN users u ON sg.user_id = u.id
WHERE sg.detected_at > NOW() - INTERVAL '1 day'
GROUP BY u.username;
"

# 統計今日信號數量
docker compose exec postgres psql -U quantlab quantlab -c "
SELECT
  signal_type,
  COUNT(*) AS count
FROM strategy_signals
WHERE detected_at::date = CURRENT_DATE
GROUP BY signal_type;
"
```

### 清理舊信號記錄

```bash
# 手動清理 30 天前的信號
docker compose exec backend celery -A app.core.celery_app call \
  app.tasks.cleanup_old_signals --kwargs '{"days_to_keep": 30}'
```

---

## 📋 定時任務清單

| 任務名稱 | 執行時間 | Celery Task | 說明 |
|---------|---------|-------------|------|
| `monitor-strategies-trading-hours` | 09:00-13:00 每 15 分 | `app.tasks.monitor_active_strategies` | 股票交易時段監控 |
| `monitor-strategies-futures-session-1` | 15:00-23:59 每 15 分 | `app.tasks.monitor_active_strategies` | 期貨夜盤前半段 |
| `monitor-strategies-futures-session-2` | 00:00-05:00 每 15 分 | `app.tasks.monitor_active_strategies` | 期貨夜盤後半段 |
| `cleanup-old-signals-weekly` | 週日 04:00 | `app.tasks.cleanup_old_signals` | 清理舊信號記錄 |

---

## ⚠️ 限制與注意事項

### 目前限制

1. **只支援 Backtrader 引擎**
   - Qlib 引擎的策略暫不支援實盤監控
   - 計劃未來版本支援

2. **策略必須配置股票清單**
   - `parameters` 中必須包含 `stocks` 陣列
   - 範例：`{"stocks": ["2330", "2454"]}`

3. **輕量級檢測**
   - 只檢測最新的買賣信號
   - 不執行完整回測邏輯
   - 數據回溯預設 60 天

### 性能考量

- **執行時間**: 每個策略約 1-3 秒（取決於股票數量）
- **建議策略數量**: 建議同時 ACTIVE 的策略不超過 20 個
- **數據載入**: 每次檢測會載入最近 60 天的日線數據

### 最佳實踐

1. **策略狀態管理**
   - 只將確實要監控的策略設為 ACTIVE
   - 測試中的策略使用 DRAFT 狀態
   - 不再使用的策略設為 ARCHIVED

2. **信號確認**
   - 系統檢測的信號僅供參考
   - 建議人工確認後再進行交易
   - 考慮設置風控規則

3. **Telegram 通知**
   - 確保 Telegram Bot 已啟動
   - 定期檢查綁定狀態
   - 設置通知偏好

---

## 🐛 故障排查

### 1. 沒有收到通知

**可能原因**：
- Telegram 未綁定 → 檢查個人設置
- 策略狀態不是 ACTIVE → 檢查策略列表
- 策略沒有配置股票清單 → 檢查 parameters
- 信號被重複過濾 → 檢查是否 15 分鐘內有相同信號

**檢查步驟**：
```bash
# 1. 檢查 Celery Beat 是否運行
docker compose ps celery-beat

# 2. 查看 Celery Beat 日誌
docker compose logs -f celery-beat

# 3. 查看 Worker 日誌
docker compose logs -f celery-worker | grep STRATEGY_MONITOR

# 4. 檢查 Telegram Bot 狀態
docker compose ps telegram-bot
```

### 2. 策略執行失敗

**查看錯誤日誌**：
```bash
docker compose logs celery-worker | grep -A 10 "STRATEGY_MONITOR.*失敗"
```

**常見錯誤**：
- `沒有配置股票清單` → 在策略 parameters 中添加 stocks
- `使用 qlib 引擎` → 目前只支援 Backtrader 引擎
- `未找到有效的策略類` → 檢查策略代碼是否正確

### 3. 信號重複

如果同一個信號被重複檢測到，檢查：

```bash
# 查詢最近的重複信號
docker compose exec postgres psql -U quantlab quantlab -c "
SELECT
  strategy_id,
  stock_id,
  signal_type,
  COUNT(*) AS count,
  MAX(detected_at) - MIN(detected_at) AS time_diff
FROM strategy_signals
WHERE detected_at > NOW() - INTERVAL '1 hour'
GROUP BY strategy_id, stock_id, signal_type
HAVING COUNT(*) > 1;
"
```

---

## 📚 相關文檔

- [CLAUDE.md](CLAUDE.md) - 完整開發指南
- [DATA_SYNC_SCHEDULE.md](DATA_SYNC_SCHEDULE.md) - 數據同步排程
- [backend/app/services/strategy_signal_detector.py](backend/app/services/strategy_signal_detector.py) - 信號檢測器原始碼
- [backend/app/tasks/strategy_monitoring.py](backend/app/tasks/strategy_monitoring.py) - 監控任務原始碼

---

## 🔄 版本歷史

- **v1.0** (2025-12-16)
  - 初始版本
  - 支援 Backtrader 引擎
  - 覆蓋股票 + 期貨交易時段
  - Telegram 通知整合
  - 重複信號過濾（15 分鐘）

---

**文檔版本**: 1.0
**維護者**: 開發團隊
**最後更新**: 2025-12-16
