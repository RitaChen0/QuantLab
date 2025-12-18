# Celery 時區配置說明文檔

## ⚠️ 重要：避免時區配置混淆

此文檔永久記錄 Celery 時區配置的正確理解，避免反覆修改導致錯誤。

---

## 1. 當前配置（`backend/app/core/celery_app.py`）

```python
celery_app.conf.update(
    timezone="Asia/Taipei",
    enable_utc=False,  # 關鍵設置
    # ... 其他配置
)
```

---

## 2. 配置含義（官方文檔）

### enable_utc=False 的效果

根據 [Celery 官方文檔](https://docs.celeryq.dev/en/stable/userguide/configuration.html#std-setting-enable_utc)：

> **enable_utc**: If enabled, dates and times in messages will be converted to use the UTC timezone.
>
> **Default**: Enabled (True) since Celery 4.0
>
> **When set to False**: The timezone from the `timezone` setting will be used instead.

### 結論

```
enable_utc=False + timezone="Asia/Taipei"
→ Celery 使用台灣時區 (UTC+8)
→ crontab 的時間參數使用 **台灣本地時間**
→ 日誌時間戳也是台灣本地時間
```

---

## 3. 實際驗證

### 驗證命令

```bash
docker compose exec backend python -c "
from app.core.celery_app import celery_app
print(f'timezone: {celery_app.conf.timezone}')
print(f'enable_utc: {celery_app.conf.enable_utc}')
"
```

**預期輸出**：
```
timezone: Asia/Taipei
enable_utc: False
```

### 容器時區

```bash
docker compose exec celery-beat date
# 輸出：Wed Dec 17 16:31:41 CST 2025
# CST = China Standard Time = Asia/Taipei = UTC+8
```

---

## 4. crontab 時間解讀規則

### ✅ 正確理解

| crontab 配置 | 實際執行時間 | 說明 |
|-------------|-------------|------|
| `hour=15, minute=0` | **台灣時間 15:00** | 下午 3 點 |
| `hour=9, minute=0` | **台灣時間 09:00** | 早上 9 點 |
| `hour=0, minute=5` | **台灣時間 00:05** | 凌晨 12:05 |
| `hour='9-13'` | **台灣時間 09:00-13:59** | 早上 9 點到下午 1 點 |

### ❌ 錯誤理解（原始註釋的誤解）

```python
# ❌ 錯誤註釋（已刪除）
"schedule": crontab(hour=7, minute=0),  # UTC 07:00 = Taiwan 15:00

# 這個註釋是錯誤的！
# 因為 enable_utc=False，所以 hour=7 就是台灣時間 07:00，
# 而不是 UTC 07:00
```

---

## 5. 如果要使用 UTC 時間（參考，不使用）

如果將來需要改用 UTC 時間，需要同時修改兩個設置：

```python
celery_app.conf.update(
    timezone="UTC",        # 改為 UTC
    enable_utc=True,       # 改為 True
)
```

此時：
```python
crontab(hour=7, minute=0)  # UTC 07:00 = 台灣 15:00
crontab(hour=1, minute=0)  # UTC 01:00 = 台灣 09:00
```

**但目前我們不使用這種配置！**

---

## 6. 任務排程時間對照表（當前配置）

### 日常任務

| 任務名稱 | crontab 配置 | 執行時間 | 說明 |
|---------|-------------|---------|------|
| sync-stock-list-daily | `hour=8, minute=0` | 台灣 08:00 | 同步股票清單 |
| sync-latest-prices-frequent | `hour='9-13', minute='*/15'` | 台灣 09:00-13:59 每 15 分鐘 | 同步最新價格（交易時段） |
| sync-daily-prices | `hour=21, minute=0` | 台灣 21:00 | 同步日線價格 |
| sync-ohlcv-daily | `hour=22, minute=0` | 台灣 22:00 | 同步 OHLCV 數據 |
| sync-fundamental-latest-daily | `hour=23, minute=0` | 台灣 23:00 | 同步基本面 |

### Shioaji 數據同步

| 任務名稱 | crontab 配置 | 執行時間 | 說明 |
|---------|-------------|---------|------|
| **sync-shioaji-minute-daily** | **`hour=15, minute=0, day_of_week='mon,tue,wed,thu,fri'`** | **台灣 15:00（工作日）** | **同步股票分鐘線** |
| sync-shioaji-futures-daily | `hour=15, minute=30, day_of_week='mon,tue,wed,thu,fri'` | 台灣 15:30（工作日） | 同步期貨分鐘線 |
| sync-option-daily-factors | `hour=15, minute=40, day_of_week='mon,tue,wed,thu,fri'` | 台灣 15:40（工作日） | 同步選擇權因子 |

### 策略監控

| 任務名稱 | crontab 配置 | 執行時間 | 說明 |
|---------|-------------|---------|------|
| monitor-strategies-trading-hours | `hour='9-13', minute='*/15'` | 台灣 09:00-13:59 每 15 分鐘 | 股市交易時段監控 |
| monitor-strategies-futures-session-1 | `hour='15-23', minute='*/15'` | 台灣 15:00-23:59 每 15 分鐘 | 期貨夜盤監控（前半） |
| monitor-strategies-futures-session-2 | `hour='0-5', minute='*/15'` | 台灣 00:00-05:00 每 15 分鐘 | 期貨夜盤監控（後半） |

### 週期性維護

| 任務名稱 | crontab 配置 | 執行時間 | 說明 |
|---------|-------------|---------|------|
| cleanup-cache-daily | `hour=3, minute=0` | 台灣 03:00（每天） | 清理快取 |
| cleanup-celery-metadata-daily | `hour=5, minute=0` | 台灣 05:00（每天） | 清理 Celery 元數據 |
| cleanup-institutional-data-weekly | `hour=2, minute=0, day_of_week='sunday'` | 台灣週日 02:00 | 清理法人數據 |
| sync-fundamental-weekly | `hour=4, minute=0, day_of_week='sunday'` | 台灣週日 04:00 | 同步基本面（完整） |
| cleanup-old-signals-weekly | `hour=4, minute=0, day_of_week='sunday'` | 台灣週日 04:00 | 清理舊信號 |
| generate-continuous-contracts-weekly | `hour=18, minute=0, day_of_week='saturday'` | 台灣週六 18:00 | 生成期貨連續合約 |
| register-option-contracts-weekly | `hour=19, minute=0, day_of_week='sunday'` | 台灣週日 19:00 | 註冊選擇權合約 |

### 年度任務

| 任務名稱 | crontab 配置 | 執行時間 | 說明 |
|---------|-------------|---------|------|
| register-new-futures-contracts-yearly | `hour=0, minute=5, day_of_month='1', month_of_year='1'` | 台灣 1/1 00:05 | 註冊新年度期貨合約 |

---

## 7. 日誌時間解讀

### Beat 日誌範例

```
[2025-12-17 15:00:00,000: INFO/MainProcess] Scheduler: Sending due task sync-shioaji-minute-daily
```

**時間戳 `2025-12-17 15:00:00` 表示台灣時間 15:00**

### Worker 日誌範例

```
[2025-12-17 15:00:00,010: INFO/MainProcess] Task app.tasks.sync_shioaji_top_stocks received
```

**時間戳 `2025-12-17 15:00:00` 表示台灣時間 15:00**

---

## 8. 驗證方法

### 手動驗證任務時間

1. **查看下次執行時間**：
```bash
docker compose exec backend celery -A app.core.celery_app inspect scheduled
```

2. **查看 Beat 排程**：
```bash
docker compose logs celery-beat --tail=100 | grep "ScheduleEntry"
```

3. **驗證特定任務**：
```bash
docker compose exec backend python -c "
from app.core.celery_app import celery_app
schedule = celery_app.conf.beat_schedule.get('sync-shioaji-minute-daily')
print(f'Task: {schedule.get(\"task\")}')
print(f'Schedule: {schedule.get(\"schedule\")}')
"
```

**預期輸出**：
```
Task: app.tasks.sync_shioaji_top_stocks
Schedule: <crontab: 0 15 * * mon,tue,wed,thu,fri (m/h/dM/MY/d)>
```

**解讀**：`0 15` = 台灣時間 15:00

---

## 9. 常見錯誤與修正

### 錯誤 1：混淆 UTC 和本地時間

❌ **錯誤思維**：
```
"我們設置 timezone='Asia/Taipei'，但 crontab 仍使用 UTC"
```

✅ **正確理解**：
```
enable_utc=False 時，crontab 使用 timezone 設置的時區（台灣時間）
```

### 錯誤 2：錯誤的註釋

❌ **錯誤註釋**：
```python
crontab(hour=7, minute=0)  # UTC 07:00 = Taiwan 15:00
```

✅ **正確註釋**：
```python
crontab(hour=15, minute=0)  # Taiwan 15:00
```

### 錯誤 3：反覆修改時區配置

如果發現任務時間不對，**不要修改 `enable_utc` 或 `timezone`**！

應該修改的是：
- crontab 的 `hour` 參數
- crontab 的 `minute` 參數

---

## 10. 決策記錄

### 為什麼使用 enable_utc=False？

1. **業務需求**：所有任務都按照台灣本地時間排程
2. **運維友好**：日誌時間戳與實際時間一致，無需換算
3. **避免混淆**：crontab 直接使用台灣時間，直觀易懂

### 為什麼不使用 UTC？

1. 需要在腦中換算時間（UTC+8）
2. 日誌時間與實際時間不一致
3. 容易出錯（如本次問題）

---

## 11. 未來維護指南

### 添加新任務時

1. **確定台灣時間**：例如 "每天下午 3 點執行"
2. **直接使用該時間**：`hour=15, minute=0`
3. **添加註釋**：`# Taiwan 15:00`

**範例**：
```python
"my-new-task": {
    "task": "app.tasks.my_new_task",
    "schedule": crontab(hour=15, minute=0),  # Taiwan 15:00
    "options": {"expires": 3600},
}
```

### 檢查配置是否正確

```bash
# 1. 確認 enable_utc 和 timezone
docker compose exec backend python -c "
from app.core.celery_app import celery_app
assert celery_app.conf.enable_utc == False
assert celery_app.conf.timezone == 'Asia/Taipei'
print('✅ 配置正確')
"

# 2. 確認容器時區
docker compose exec celery-beat date | grep CST
```

---

## 12. 總結

### 記住這一條規則

```
enable_utc=False + timezone="Asia/Taipei"
→ crontab 的 hour 參數 = 台灣本地時間
```

### 範例對照

| 需求 | crontab 配置 | 說明 |
|------|-------------|------|
| 台灣時間早上 8 點 | `hour=8` | ✅ 正確 |
| 台灣時間下午 3 點 | `hour=15` | ✅ 正確 |
| 台灣時間晚上 9 點 | `hour=21` | ✅ 正確 |
| 台灣時間凌晨 12:05 | `hour=0, minute=5` | ✅ 正確 |

### 不要做的事

❌ 不要將台灣時間轉換成 UTC 再配置
❌ 不要修改 `enable_utc` 設置
❌ 不要修改 `timezone` 設置
❌ 不要在註釋中寫 "UTC XX:XX = Taiwan YY:YY"

---

**文檔版本**：2025-12-17
**最後更新**：修正所有任務的時區配置錯誤
**維護者**：開發團隊
**重要性**：🔴 關鍵配置，請勿隨意修改
