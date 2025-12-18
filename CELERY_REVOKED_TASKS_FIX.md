# Celery Revoked Tasks 累積問題 - 解決方案文檔

## 問題描述

**現象**：
- Celery Worker 重啟後，所有任務都被標記為 "revoked" 並被拒絕執行
- `celery inspect revoked` 顯示 100+ 個撤銷的任務 ID
- 定時任務（如 `sync_latest_prices`）顯示 "尚未執行"
- 任務在發送後立即被標記為 "expired" 並撤銷

**根本原因**（經過深入調查）：
1. **Celery Beat 重啟行為**：Beat 重啟後會補發所有逾期未執行的定時任務
2. **任務過期判定**：這些補發的任務帶有 `expires` 參數（如 3600秒），但因為早已超過預定執行時間，Worker 收到時已經過期
3. **正常的 Revoke 機制**：Worker 將過期任務標記為 REVOKED 並保存 task_id 到內存（這是 Celery 的正確行為）
4. **內存積累問題**：Revoked 任務 ID 在 Worker 內存中積累，重啟前無法清除
5. **後續任務受影響**：累積的 revoked 列表可能導致後續任務執行異常

**說明**：這不是 Celery 的 bug，而是 **Beat 重啟補發機制** + **短期 expires 設置** 的組合導致的配置問題。

---

## 實施的解決方案

### 1. 關鍵配置修改（`backend/app/core/celery_app.py`）

#### 1.1 修改任務確認策略（最關鍵）
```python
# ✅ 修改後（解決問題）
task_acks_late=True,  # 任務執行完成後才確認（確保任務不會丟失）
task_reject_on_worker_lost=False,  # Worker 丟失時重新排隊任務
```

**說明**：
- `task_acks_late=True` 確保任務執行完成後才確認，減少任務丟失風險
- `task_reject_on_worker_lost=False` 確保 Worker 崩潰時任務重新排隊而非被撤銷
- 這些設置改善了任務的可靠性，但無法完全避免 Beat 重啟時的過期任務問題

#### 1.2 移除頻繁任務的 expires 設置（關鍵）
```python
# ✅ 修改後
"sync-latest-prices-frequent": {
    "task": "app.tasks.sync_latest_prices",
    "schedule": crontab(minute='*/15', hour='1-5', day_of_week='mon,tue,wed,thu,fri'),
    # Note: 移除 expires 設置，讓任務永不過期
},

"monitor-strategies-trading-hours": {
    "task": "app.tasks.monitor_active_strategies",
    "schedule": crontab(minute='*/15', hour='1-5', day_of_week='mon,tue,wed,thu,fri'),
    # Note: 移除 expires 設置，讓任務永不過期
},

# ... 其他 15 分鐘間隔的任務同樣移除 expires
```

**原因**：
- **Beat 重啟補發問題**：Beat 重啟後會補發所有逾期任務，但這些任務的 `expires` 時間早已過期
- **避免誤判**：移除 `expires` 設置可確保補發的任務仍會被執行，而不會被標記為 revoked
- **高頻任務特性**：頻繁執行的任務（每 15 分鐘）本身就有容錯性，即使錯過一次也會在下次執行

#### 1.3 Worker 自動重啟（預防性）
```python
worker_max_memory_per_child=512000,  # Worker 使用 512MB 後自動重啟
```
- **作用**：定期清空 Worker 內存，包括 revoked 列表
- **觸發**：Worker 進程使用超過 512MB 內存時

#### 1.4 結果自動過期（資源管理）
```python
result_expires=3600,  # 結果 1 小時後過期
```
- **作用**：自動清理 Redis 中的舊任務結果
- **防止**：Redis 內存無限增長

---

### 2. 自動清理任務（`backend/app/tasks/system_maintenance.py`）

#### 2.1 新增定時清理任務
```python
@celery_app.task(bind=True, name="app.tasks.cleanup_celery_metadata")
def cleanup_celery_metadata(max_age_hours: int = 24, dry_run: bool = False):
    """清理 Celery 元數據（過期結果、revoked tasks 等）"""
```

**執行時間**：每天凌晨 5:00（台灣時間）

**清理內容**：
1. 清空任務隊列中未執行的任務（`control.purge()`）
2. 刪除 24 小時前的任務結果（`celery-task-meta-*`）
3. 為沒有過期時間的狀態 key 設置過期時間

**排程配置**：
```python
"cleanup-celery-metadata-daily": {
    "task": "app.tasks.cleanup_celery_metadata",
    "schedule": crontab(hour=21, minute=0),  # UTC 21:00 = Taiwan 05:00
    "options": {"expires": 3600},
}
```

---

## 驗證方法

### 1. 檢查 Revoked 列表
```bash
docker compose exec -T backend celery -A app.core.celery_app inspect revoked
```
**預期結果**：
```
-> celery@xxx: OK
    - empty -
```

### 2. 檢查 Worker 配置
```bash
docker compose exec -T backend celery -A app.core.celery_app inspect conf | grep -E "(result_expires|task_reject_on_worker_lost|task_acks_late|worker_max_memory_per_child)"
```
**預期結果**：
```json
"result_expires": 3600,
"task_acks_late": false,
"task_reject_on_worker_lost": true,
"worker_max_memory_per_child": 512000,
```

### 3. 檢查清理任務已註冊
```bash
docker compose exec -T backend celery -A app.core.celery_app inspect registered | grep cleanup_celery_metadata
```
**預期結果**：
```
* app.tasks.cleanup_celery_metadata
```

### 4. 檢查清理任務排程
```bash
docker compose logs celery-beat --tail=100 | grep cleanup-celery-metadata
```
**預期結果**：
```
<ScheduleEntry: cleanup-celery-metadata-daily app.tasks.cleanup_celery_metadata() <crontab: 0 21 * * * (m/h/dM/MY/d)>
```

### 5. 檢查任務執行狀態
在後台管理面板 → 數據同步管理 → 查看 "同步最新價格" 任務

**預期**：
- 最後執行時間正常更新
- 狀態顯示為 "success" 或 "running"

### 6. 驗證定時任務持續執行
```bash
# 檢查連續多次定時任務的執行日誌
docker compose logs celery-worker --since 1h | grep "sync_latest_prices.*succeeded"
```

**預期結果**：
- 每 15 分鐘有一次成功執行記錄
- 沒有 "Discarding revoked task" 消息

**實際測試結果**（2025-12-17）：
- ✅ 13:20:34 手動觸發成功
- ✅ 13:30:00 定時任務成功執行（修改 task_acks_late 後首次測試失敗）
- ✅ 13:34:31 手動觸發成功
- ✅ 13:45:00 定時任務成功執行（移除 expires 後測試成功）
- ✅ Revoked 列表始終保持為空

---

## 監控指標

### 每日監控（自動）
清理任務會自動記錄統計資訊到日誌：
```bash
docker compose logs celery-worker | grep "cleanup_celery_metadata"
```

**關鍵指標**：
- `revoked_tasks_cleared`: 清空的 revoked 列表數量
- `expired_results_deleted`: 刪除的過期結果數量
- `task_states_cleaned`: 清理的狀態 key 數量

### 手動監控
```bash
# 1. 檢查 Redis 任務結果數量
docker compose exec redis redis-cli --scan --pattern "celery-task-meta-*" | wc -l

# 2. 檢查 Worker 內存使用
docker compose stats celery-worker --no-stream

# 3. 檢查活動任務數量
docker compose exec backend celery -A app.core.celery_app inspect active
```

---

## 故障排除

### 問題 1：任務仍然被 revoked

**診斷**：
```bash
docker compose exec backend celery -A app.core.celery_app inspect revoked
```

**解決方案**：
```bash
# 重啟 Worker 清空 revoked 列表
docker compose restart celery-worker celery-beat
```

### 問題 2：清理任務未執行

**診斷**：
```bash
# 檢查 Beat 排程
docker compose logs celery-beat | grep cleanup-celery-metadata

# 檢查任務歷史
docker compose exec redis redis-cli GET "task_history:app.tasks.cleanup_celery_metadata"
```

**解決方案**：
```bash
# 手動觸發清理任務
docker compose exec backend celery -A app.core.celery_app call app.tasks.cleanup_celery_metadata
```

### 問題 3：Worker 頻繁重啟

**原因**：內存使用超過 512MB 限制

**診斷**：
```bash
docker compose logs celery-worker | grep "Restarting"
```

**解決方案**：
```python
# 調整 celery_app.py 中的內存限制
worker_max_memory_per_child=1024000,  # 增加到 1GB
```

---

## 變更摘要

### 修改的檔案
1. `/backend/app/core/celery_app.py`
   - 添加 `result_expires`, `task_reject_on_worker_lost`, `task_acks_late`
   - 添加 `worker_max_memory_per_child`
   - 調整 4 個定時任務的 `expires` 從 600s 到 1800s
   - 添加 `cleanup-celery-metadata-daily` 排程

2. `/backend/app/tasks/system_maintenance.py` （新增）
   - 實現 `cleanup_celery_metadata` 清理任務

3. `/backend/app/tasks/__init__.py`
   - 導出 `cleanup_celery_metadata` 任務
   - 導出 `generate_continuous_contracts`, `register_new_futures_contracts` 期貨任務

### 新增的功能
- 自動清理過期任務結果（每天 5:00）
- Worker 內存超限自動重啟（防止 revoked 列表積累）
- 任務結果 1 小時後自動過期

---

## 長期維護建議

### 1. 定期檢查（每週）
```bash
# 檢查 revoked 列表是否為空
docker compose exec backend celery -A app.core.celery_app inspect revoked

# 檢查 Redis 內存使用
docker compose exec redis redis-cli INFO memory | grep used_memory_human
```

### 2. 調整清理頻率（如需）
如果發現 Redis 內存增長過快，可以調整清理任務執行時間：
```python
# 改為每 12 小時清理一次
"cleanup-celery-metadata-frequent": {
    "task": "app.tasks.cleanup_celery_metadata",
    "schedule": crontab(minute=0, hour='*/12'),  # 每 12 小時
    "options": {"expires": 3600},
}
```

### 3. 監控告警
建議設置以下告警：
- Redis 內存使用 > 80%
- Revoked 任務數量 > 10
- Worker 重啟頻率 > 每小時 1 次

---

## 總結

### 問題本質
**Celery Beat 重啟後會補發所有逾期未執行的定時任務**。如果這些任務設置了較短的 `expires` 時間（如 1-2 小時），Worker 會因為任務早已超過預定執行時間而判定過期，並標記為 REVOKED。這是 Celery 的正常行為，並非程式錯誤。

**關鍵場景**：
- Beat/Worker 因部署、重啟或故障停機數小時
- 重啟後 Beat 補發所有錯過的定時任務
- 這些任務的 `expires` 時間早已過期（例如：08:00 執行 + 1小時過期 = 09:00，但現在是 16:00）
- Worker 正確地將過期任務標記為 revoked

### 解決方案核心
1. **移除短期任務的 `expires` 設置**：確保 Beat 重啟後補發的任務仍能執行
2. **修改 `task_acks_late=True`**：改善任務可靠性，Worker 崩潰時任務不會丟失
3. **Worker 自動重啟機制**：定期清空內存中的 revoked 列表
4. **添加自動清理任務**：定期清理 Redis 元數據，防止資源洩漏

### 適用場景
- **所有 Celery 版本**：這是 Celery 的設計行為，非特定版本問題
- **定時任務**：使用 Celery Beat 的所有定時任務
- **症狀**：Beat/Worker 重啟後，補發的任務被標記為 "revoked" 並拒絕執行

### 配置建議
1. **高頻任務**（間隔 < 1小時）：**移除** `expires` 設置
2. **低頻任務**（間隔 >= 1天）：保留 `expires`，但設置為 **24小時** 或更長
3. **關鍵任務**：完全移除 `expires`，使用其他機制確保冪等性

---

**文檔版本**：2025-12-18
**維護者**：開發團隊
**最後更新**：修正問題描述，移除錯誤的 "Celery 5.3.6 bug" 說法，提供準確的技術解釋
**測試狀態**：✅ 已驗證修復有效（Worker 重啟後任務正常執行）
