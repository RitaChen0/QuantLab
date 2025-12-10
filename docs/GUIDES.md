# QuantLab 使用指南

本文檔整合了 QuantLab 的各項功能使用指南。

## 目錄

- [批次同步指南](#批次同步指南)
- [手動同步指南](#手動同步指南)
- [基本面分析指南](#基本面分析指南)
- [回測監控指南](#回測監控指南)

---

## 批次同步指南

### 概述

批次同步功能用於同步大量股票的財務指標數據，支援斷點續傳和進度追蹤。

### 使用方式

```bash
# 批次同步所有股票（2,671 檔，約 6-8 小時）
./scripts/batch-sync.sh

# 測試模式（僅 10 檔）
./scripts/batch-sync.sh --test

# 查看批次同步進度
./scripts/batch-sync.sh --status

# 監控批次同步（圖形化介面）
./scripts/monitor-batch-sync.sh

# 重新開始批次同步（清除進度）
./scripts/batch-sync.sh --reset
```

### 功能特性

- **自動斷點續傳**：中斷後可繼續，不需重新開始
- **進度追蹤**：實時顯示已處理/剩餘數量、預估完成時間
- **批次處理**：每批 100 檔，批次間延遲 60 秒避免 API 限制
- **失敗重試**：自動重試失敗的股票
- **詳細日誌**：記錄於 `/tmp/batch_sync_*.log`
- **進度檔案**：`/tmp/batch_sync_progress.json`

### 注意事項

1. 首次同步時間較長（6-8 小時），建議在非交易時段執行
2. 同步期間不要中斷終端，可使用 `screen` 或 `tmux`
3. 確保 FinLab API Token 有效且配額充足
4. 監控日誌檔案以發現潛在問題

---

## 手動同步指南

### 概述

手動同步提供互動式介面，讓您選擇特定股票或股票群組進行同步。

### 使用方式

```bash
# 啟動互動式同步工具
./scripts/manual-sync.sh
```

### 同步選項

1. **同步單一股票**：輸入股票代碼（如 2330）
2. **同步多檔股票**：輸入逗號分隔的股票代碼（如 2330,2317,2454）
3. **同步熱門股票**：預設的 50 檔熱門股票
4. **同步特定產業**：選擇產業類別後同步該產業所有股票
5. **查看同步狀態**：顯示最近同步的股票和時間

### 互動流程

```
歡迎使用 QuantLab 手動同步工具
================================

請選擇操作：
1) 同步單一股票
2) 同步多檔股票
3) 同步熱門股票 (50 檔)
4) 同步特定產業
5) 查看同步狀態
6) 結束

請輸入選項 [1-6]:
```

### 適用場景

- 需要即時更新特定股票數據
- 測試新股票的數據同步
- 補充同步失敗的股票
- 特定產業研究需求

---

## 基本面分析指南

### 概述

QuantLab 整合了完整的財務基本面數據，支援多種分析功能。

### 可用數據

**財務指標**（季度更新）：
- ROE 稅後（%）
- ROA 稅後息前（%）
- 營業毛利率（%）
- 營業利益率（%）
- 每股稅後淨利（元）
- 營收成長率（%）
- 稅後淨利成長率（%）

**數據來源**：
- FinLab API `company_basic_info`
- 更新頻率：每季
- 資料庫表：`fundamental_data`

### API 端點

```bash
# 獲取單一股票基本面數據
GET /api/v1/data/fundamental/{stock_id}

# 獲取產業聚合指標
GET /api/v1/industry/{industry_code}/metrics

# 獲取產業歷史指標趨勢
GET /api/v1/industry/{industry_code}/metrics/historical
```

### 使用範例

```python
# Python 範例：獲取台積電財務數據
import requests

response = requests.get(
    'http://localhost:8000/api/v1/data/fundamental/2330',
    headers={'Authorization': f'Bearer {token}'}
)

data = response.json()
print(f"ROE: {data['roe']}%")
print(f"營業利益率: {data['operating_margin']}%")
```

### 前端功能

**產業分析頁面** (`/industry`)：
- 產業列表與統計
- 產業內股票清單
- 產業平均財務指標
- 歷史指標趨勢圖表

### 注意事項

1. **季度字串格式**：`fundamental_data` 表的 `date` 欄位使用季度字串（如 "2024-Q4"），不是日期格式
2. **數據延遲**：財務數據通常延遲 1-2 個月
3. **缺失數據**：部分股票可能缺少某些財務指標
4. **快取機制**：產業指標快取 30 天

---

## 回測監控指南

### 概述

回測監控系統提供實時追蹤回測任務的執行狀態、進度和結果。

### 監控腳本

```bash
# 啟動回測監控
./scripts/monitor-backtest.sh

# 查看特定回測任務
./scripts/monitor-backtest.sh --task-id 123

# 查看所有活躍任務
./scripts/monitor-backtest.sh --active
```

### 監控指標

**任務狀態**：
- `pending` - 等待執行
- `running` - 執行中
- `completed` - 已完成
- `failed` - 失敗
- `cancelled` - 已取消

**執行資訊**：
- 開始時間 / 結束時間
- 執行時長
- 資料筆數
- 錯誤訊息（如有）

**績效指標**（完成後）：
- 總報酬率
- 年化報酬率
- Sharpe Ratio
- 最大回撤
- 勝率
- 交易次數

### API 端點

```bash
# 獲取回測列表
GET /api/v1/backtest/

# 獲取回測詳情
GET /api/v1/backtest/{id}

# 獲取回測結果
GET /api/v1/backtest/{id}/result

# 獲取特定策略的所有回測
GET /api/v1/backtest/strategy/{strategy_id}
```

### 前端功能

**回測列表頁** (`/backtest`)：
- 所有回測任務列表
- 狀態篩選（全部/執行中/已完成/失敗）
- 即時狀態更新

**回測詳情頁** (`/backtest/{id}`)：
- 回測參數
- 執行日誌
- 績效指標
- 交易記錄視覺化（ECharts）
- 資金曲線圖

### 日誌查看

```bash
# 查看 Celery worker 日誌
docker compose logs -f celery-worker

# 搜尋特定回測任務
docker compose logs celery-worker | grep "backtest_123"

# 查看最近 1 小時的錯誤
docker compose logs --since 1h celery-worker | grep -i error
```

### 故障排查

**常見問題**：

1. **任務卡在 pending 狀態**
   - 檢查 Celery worker 是否運行：`docker compose ps celery-worker`
   - 重啟 worker：`docker compose restart celery-worker`

2. **回測失敗但無錯誤訊息**
   - 查看詳細日誌：`docker compose logs celery-worker --tail 100`
   - 檢查策略代碼語法錯誤

3. **數據不足導致失敗**
   - 確認股票數據已同步
   - 檢查日期範圍是否合理

4. **執行時間過長**
   - 考慮縮小回測日期範圍
   - 使用 Qlib 引擎（效能較佳）

### 最佳實踐

1. **測試策略**：先用短期數據測試（如 1 年）
2. **監控資源**：長期回測會消耗大量記憶體
3. **錯誤處理**：策略代碼要有完善的錯誤處理
4. **日誌記錄**：關鍵決策點記錄日誌方便除錯

---

## 相關文檔

- [CLAUDE.md](../CLAUDE.md) - 開發指南
- [README.md](../README.md) - 專案首頁
- [docs/QLIB.md](./QLIB.md) - Qlib 引擎指南
- [docs/RDAGENT.md](./RDAGENT.md) - RD-Agent 指南
- [Document/DATABASE_SCHEMA_REPORT.md](../Document/DATABASE_SCHEMA_REPORT.md) - 資料庫架構
