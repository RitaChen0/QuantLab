# 任務重試機制使用指南

> 解決 backend 重啟後任務被撤銷的問題

**最後更新**: 2025-12-16

---

## 📋 問題背景

### 為什麼需要任務重試？

當 Docker backend 容器重啟時（例如修改代碼後），會出現以下問題：

```
時間線:
15:30 - Celery Beat 觸發定時任務 ✅
15:30-16:00 - 任務在 Redis 隊列中等待執行
16:00 - backend 容器重啟（docker compose restart backend）
      → Celery Worker 重啟
      → 隊列中所有待執行任務被標記為 "revoked"（已撤銷）
      → 任務被丟棄，不會執行 ❌
```

**影響**：
- 數據同步任務（如股價、期貨分鐘線）可能漏執行
- 導致數據不是最新，影響回測結果
- 需要手動補執行任務

---

## 🔧 解決方案

### 方案 1: 手動執行重試腳本（推薦）

**適用場景**：
- backend 重啟後，手動執行一次
- 發現數據缺失時手動補救

**使用方式**：
```bash
# 在 backend 重啟後執行
bash /home/ubuntu/QuantLab/scripts/retry-missed-tasks.sh
```

**腳本功能**：
- ✅ 自動檢測今天應該執行但未執行的任務
- ✅ 智能判斷任務執行時間是否已過
- ✅ 過濾週末/工作日限制
- ✅ 檢查任務是否已執行過（避免重複）
- ✅ 自動觸發漏執行的任務
- ✅ 彩色輸出，清晰易讀

**輸出範例**：
```
🔄 檢測並重新觸發被撤銷的任務
📅 當前時間: 2025-12-16 19:41:26 (週二)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 檢查: 同步 Shioaji 期貨分鐘線（TX/MTX）
   任務: app.tasks.sync_shioaji_futures
   計劃執行時間: 15:30 (台灣時間)
   ⚠️  狀態: 應執行但未執行，準備重新觸發...
   ✅ 任務已提交: e6176ade-9b99-4d89-afc5-45bbe8875cb0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 執行總結
✅ 重新觸發: 1 個任務
⏭️  已跳過: 10 個任務
```

---

### 方案 2: 自動守護進程（進階）

**適用場景**：
- 頻繁重啟 backend 的開發環境
- 希望完全自動化，無需人工干預

**使用方式**：

#### 選項 A: 在背景執行
```bash
# 啟動守護進程（背景執行）
nohup bash /home/ubuntu/QuantLab/scripts/auto-retry-after-restart.sh > /tmp/auto-retry.log 2>&1 &

# 查看守護進程日誌
tail -f /tmp/auto-retry-tasks.log

# 停止守護進程
pkill -f auto-retry-after-restart.sh
```

#### 選項 B: 使用 systemd service（生產環境推薦）
```bash
# 1. 創建 systemd service 文件
sudo nano /etc/systemd/system/quantlab-task-retry.service
```

```ini
[Unit]
Description=QuantLab Task Retry Service
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/QuantLab
ExecStart=/bin/bash /home/ubuntu/QuantLab/scripts/auto-retry-after-restart.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 2. 啟用並啟動服務
sudo systemctl daemon-reload
sudo systemctl enable quantlab-task-retry.service
sudo systemctl start quantlab-task-retry.service

# 3. 查看服務狀態
sudo systemctl status quantlab-task-retry.service

# 4. 查看日誌
sudo journalctl -u quantlab-task-retry.service -f
```

---

### 方案 3: 後台管理頁面手動執行（最簡單）

**適用場景**：
- 不熟悉命令行
- 只是偶爾需要補執行任務

**使用方式**：
1. 訪問 `http://localhost:3000/admin`
2. 點擊「數據同步」分頁
3. 找到需要執行的任務
4. 點擊「立即執行」按鈕

---

## 📊 支援的任務列表

腳本會自動檢測以下任務：

| 任務 | 執行時間 | 執行日期 | 說明 |
|------|---------|---------|------|
| `sync_stock_list` | 08:00 | 週一至週五 | 同步股票列表 |
| `sync_daily_prices` | 21:00 | 週一至週五 | 同步每日價格 |
| `sync_ohlcv_data` | 22:00 | 週一至週五 | 同步 OHLCV 數據 |
| `sync_fundamental_latest` | 23:00 | 週一至週五 | 同步財務指標（快速） |
| `sync_top_stocks_institutional` | 21:00 | 週一至週五 | 同步法人買賣超 |
| **`sync_shioaji_top_stocks`** | **15:00** | **週一至週五** | **同步 Shioaji 分鐘線（Top 50）** |
| **`sync_shioaji_futures`** | **15:30** | **週一至週五** | **同步 Shioaji 期貨分鐘線（TX/MTX）** |
| `cleanup_old_cache` | 03:00 | 每日 | 清理過期快取 |
| `sync_fundamental_data` | 04:00 | 週日 | 同步財務指標（完整） |
| `cleanup_old_institutional_data` | 02:00 | 週日 | 清理過期法人數據 |
| `generate_continuous_contracts` | 18:00 | 週六 | 生成期貨連續合約 |

---

## 🎯 腳本邏輯說明

### 檢查流程

```
對於每個定時任務：
  1. 檢查是否在執行日期範圍內
     ├─ 否 → 跳過
     └─ 是 → 繼續

  2. 檢查執行時間是否已過
     ├─ 否 → 跳過（時間未到）
     └─ 是 → 繼續

  3. 檢查今天是否已執行過
     ├─ 是 → 跳過（已執行）
     └─ 否 → 重新觸發任務 ✅
```

### 判斷邏輯範例

**案例 1: 週二 19:41 執行腳本**
```
sync_shioaji_futures (15:30, 週一至週五)
  → 今天是週二 ✅
  → 現在 19:41 > 15:30 ✅
  → 今天未執行 ✅
  → 重新觸發 ✅

sync_daily_prices (21:00, 週一至週五)
  → 今天是週二 ✅
  → 現在 19:41 < 21:00 ❌
  → 跳過（時間未到）

sync_fundamental_data (04:00, 週日)
  → 今天是週二 ❌
  → 跳過（不在執行日期）
```

---

## 🔍 故障排查

### Q1: 腳本顯示「任務已執行」但實際沒有數據？

**原因**:
- 任務執行了但失敗
- 或者 Celery 日誌檢測邏輯有誤

**解決**:
```bash
# 手動檢查任務日誌
docker compose logs celery-worker --since 24h | grep "sync_shioaji_futures"

# 強制重新執行
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_shioaji_futures
```

---

### Q2: 腳本執行時報錯「整數表示式」？

**原因**:
- 時間格式解析問題（已在最新版本修復）

**解決**:
```bash
# 重新下載最新腳本
cd /home/ubuntu/QuantLab
git pull
chmod +x scripts/retry-missed-tasks.sh
```

---

### Q3: 如何確認腳本真的在監控？

**查看守護進程日誌**:
```bash
# 查看最新 20 行日誌
tail -20 /tmp/auto-retry-tasks.log

# 實時追蹤日誌
tail -f /tmp/auto-retry-tasks.log
```

**預期輸出**:
```
[2025-12-16 19:45:00] ✅ 初始化完成，開始監控 backend 容器
[2025-12-16 19:45:00]    當前啟動時間: 2025-12-16T11:30:23.123456Z
[2025-12-16 20:15:30] 🔔 檢測到 backend 重啟！
[2025-12-16 20:15:30]    舊啟動時間: 2025-12-16T11:30:23.123456Z
[2025-12-16 20:15:30]    新啟動時間: 2025-12-16T12:15:15.654321Z
[2025-12-16 20:16:00] 🔄 執行任務重試...
[2025-12-16 20:16:15] ✅ 任務重試完成
```

---

## 📝 最佳實踐

### 1. backend 重啟後的標準流程

```bash
# 步驟 1: 重啟 backend
docker compose restart backend

# 步驟 2: 等待啟動完成（約 10 秒）
sleep 10

# 步驟 3: 執行任務重試腳本
bash /home/ubuntu/QuantLab/scripts/retry-missed-tasks.sh

# 步驟 4: 查看執行結果
docker compose logs -f celery-worker | grep -E 'succeeded|failed'
```

---

### 2. 開發時避免任務撤銷的技巧

**技巧 1: 避開任務執行時間重啟**
```
危險時段（避免重啟）:
- 15:00-16:00 (Shioaji 同步時段)
- 21:00-23:30 (財報、股價同步時段)
- 03:00-05:00 (清理和週末任務)
```

**技巧 2: 重啟前清空隊列**
```bash
# 重啟前清空 Redis 隊列（避免任務積壓）
docker compose exec redis redis-cli FLUSHDB

# 然後重啟
docker compose restart backend
```

**技巧 3: 使用 code-server 熱重載**
- 修改代碼後使用 `docker compose exec backend touch /app/main.py` 觸發熱重載
- 而不是完全重啟容器

---

### 3. 生產環境建議

```bash
# 1. 設置 systemd service（自動重試）
sudo systemctl enable quantlab-task-retry.service

# 2. 設置告警（Telegram 通知）
# 當任務失敗時發送通知（待實現）

# 3. 定期檢查日誌
# 每週檢查一次 /tmp/auto-retry-tasks.log

# 4. 資料庫備份
# 重要數據同步前備份資料庫
```

---

## 🔗 相關文檔

- [ADMIN_PANEL_GUIDE.md](ADMIN_PANEL_GUIDE.md) - 後台管理面板使用指南
- [STRATEGY_MONITORING_GUIDE.md](STRATEGY_MONITORING_GUIDE.md) - 策略監控功能詳解
- [CLAUDE.md](CLAUDE.md) - 完整開發指南

---

**文檔版本**: 1.0
**維護者**: 開發團隊
**最後更新**: 2025-12-16
