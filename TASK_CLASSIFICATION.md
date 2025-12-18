# Celery 任務職責分類

> 確保數據流向清晰：外部 API → 資料庫 → 策略引擎

**更新日期**: 2025-12-16

---

## 📋 分類原則

### 1️⃣ 數據同步 (Data Sync)
**數據流向**: External API → Database

**定義**: 從外部 API（FinLab、Shioaji）獲取原始數據並存入資料庫

**特徵**:
- 依賴外部 API
- 可能受 API 限制影響（速率、配額）
- 主要是 I/O 操作
- 結果存入 PostgreSQL 或 Qlib 文件

---

### 2️⃣ 數據處理 (Data Processing)
**數據流向**: Database → Compute → Database/File

**定義**: 從資料庫讀取數據，經過計算或轉換後，存回資料庫或導出文件

**特徵**:
- 不依賴外部 API
- 主要是計算密集型操作
- 可離線執行
- 冪等性（可重複執行）

---

### 3️⃣ 策略處理 (Strategy Processing)
**數據流向**: Database → Strategy Engine → Signals/Results

**定義**: 從資料庫讀取策略定義和市場數據，通過策略引擎生成信號或回測結果

**特徵**:
- 完全基於資料庫數據
- 不修改歷史數據
- 生成策略相關產出（信號、回測報告）
- 可能觸發通知（Telegram）

---

## 🗂️ 任務清單

### 類別 1: 數據同步 (11 個任務)

| 任務 | 數據源 | 目標 | 頻率 | 說明 |
|------|--------|------|------|------|
| `sync_stock_list` | FinLab API | stocks 表 | 每日 08:00 | 同步股票列表 |
| `sync_daily_prices` | FinLab API | stock_prices 表 | 每日 21:00 | 同步日線價格 |
| `sync_ohlcv_data` | FinLab API | stock_prices 表 | 每日 22:00 | 同步 OHLCV 數據 |
| `sync_latest_prices` | FinLab API | stock_prices 表 | 交易時段每 15 分鐘 | 即時價格 |
| `sync_fundamental_data` | FinLab API | fundamental_metrics 表 | 每週日 04:00 | 財務指標（完整） |
| `sync_fundamental_latest` | FinLab API | fundamental_metrics 表 | 每日 23:00 | 財務指標（快速） |
| `sync_top_stocks_institutional` | FinLab API | institutional_investors 表 | 每日 21:00 | 法人買賣超 |
| `sync_shioaji_top_stocks` | Shioaji API | stock_minute_prices + Qlib | 交易日 15:00 | 分鐘線（全部股票） |
| `sync_shioaji_futures` | Shioaji API | stock_minute_prices + Qlib | 交易日 15:30 | 期貨分鐘線 |
| `sync_option_daily_factors` | Shioaji API | option_daily_factors 表 | 交易日 15:40 | 選擇權因子（含計算） ⚠️ |
| `register_option_contracts` | Shioaji API | option_contracts 表 | 每週日 19:00 | 註冊選擇權合約 |

**⚠️ 職責說明**:
- `sync_option_daily_factors`: 從 API 獲取選擇權鏈 → 即時計算 PCR/ATM IV → 存入資料庫
  - 雖然包含計算，但因為：
    1. 選擇權數據時效性強，需要獲取後立即計算
    2. 中間狀態（原始快照）沒有獨立使用價值
    3. 避免重複調用 API（受速率限制）
  - **歸類為"數據同步"是合理的**（可視為"聚合同步"）

---

### 類別 2: 數據處理 (5 個任務)

| 任務 | 輸入 | 處理 | 輸出 | 頻率 | 說明 |
|------|------|------|------|------|------|
| `generate_continuous_contracts` | stock_minute_prices | 月份合約拼接 | Qlib 連續合約 | 每週六 18:00 | 生成 TXCONT/MTXCONT |
| `register_new_futures_contracts` | 日期計算 | 生成新年度合約 | stocks 表 | 每年 1/1 00:05 | 註冊新年度月份合約 |
| `cleanup_old_cache` | Redis | 刪除過期 Key | Redis | 每日 03:00 | 清理 Redis 快取 |
| `cleanup_old_institutional_data` | institutional_investors | 刪除舊記錄 | institutional_investors | 每週日 02:00 | 保留 365 天 |
| `cleanup_old_signals` | strategy_signals | 刪除舊記錄 | strategy_signals | 每週日 04:00 | 保留 30 天 |

**職責確認**:
- ✅ 所有任務都不依賴外部 API
- ✅ 完全基於資料庫或文件系統
- ✅ 可重複執行（冪等性）

---

### 類別 3: 策略處理 (1 個任務)

| 任務 | 輸入 | 處理 | 輸出 | 頻率 | 說明 |
|------|------|------|------|------|------|
| `monitor_active_strategies` | strategies + stock_prices | 信號檢測引擎 | strategy_signals + Telegram | 交易時段每 15 分鐘 | 實盤監控 ACTIVE 策略 |

**職責確認**:
- ✅ 完全基於資料庫數據（strategies、stock_prices）
- ✅ 不同步任何外部數據
- ✅ 使用策略引擎進行信號檢測
- ✅ 生成策略信號並通知用戶

**其他策略任務**（手動觸發，不在定時任務中）:
- `run_backtest_async` - 回測引擎
- RD-Agent 相關任務 - AI 因子生成

---

## ⚠️ 職責混淆檢查結果

### ✅ 無需拆分的任務

**`sync_option_daily_factors`**
- 雖然包含"同步"和"計算"兩個步驟
- 但這是合理的 pipeline 設計
- **原因**:
  1. 選擇權數據時效性強（即時計算避免過時）
  2. 中間狀態無獨立價值（快照不需持久化）
  3. API 限制（避免重複調用）
- **結論**: 歸類為"數據同步"，可視為"聚合同步"

### ✅ 正確分類的任務

**`generate_continuous_contracts`**
- 完全基於資料庫數據
- 不調用外部 API
- 純數據處理任務 ✅

**`monitor_active_strategies`**
- 完全基於資料庫數據
- 不同步任何外部數據
- 純策略處理任務 ✅

---

## 📊 統計總結

- **數據同步**: 11 個任務
- **數據處理**: 5 個任務
- **策略處理**: 1 個任務（定時） + N 個（手動觸發）

**總計**: 17 個定時任務

---

## 🔗 相關文檔

- [CLAUDE.md](CLAUDE.md) - 完整開發指南
- [ADMIN_PANEL_GUIDE.md](ADMIN_PANEL_GUIDE.md) - 後台管理面板使用指南
- [CELERY_TASKS_GUIDE.md](Document/CELERY_TASKS_GUIDE.md) - Celery 任務管理

---

**文檔版本**: 1.0
**維護者**: 開發團隊
**最後更新**: 2025-12-16
