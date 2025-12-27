# QuantLab 日誌改進報告

**日期**: 2025-12-27
**版本**: 1.0
**目的**: 為所有容器日誌添加 UTC 時間戳，提升可追蹤性

---

## 📋 改進內容

### 1. Backend (FastAPI + Uvicorn)

**文件**: `backend/logging_config.yaml` (新增)

**格式**:
```
[2025-12-27 13:58:12] INFO:     172.18.0.11:45486 - "GET /metrics HTTP/1.1" 200 OK
[2025-12-27 13:57:43] INFO:     Started server process [22]
```

**配置**:
- 使用 Uvicorn 的自定義 Formatter (`uvicorn.logging.DefaultFormatter`, `uvicorn.logging.AccessFormatter`)
- 時間格式: `YYYY-MM-DD HH:MM:SS` (UTC)
- 訪問日誌包含: 時間戳 + 客戶端 IP + 請求方法 + 路徑 + 狀態碼

**修改文件**:
- `backend/logging_config.yaml` - 日誌配置
- `backend/start.sh` - 添加 `--log-config /app/logging_config.yaml` 參數

### 2. Frontend (Nuxt.js)

**文件**: `frontend/plugins/logger.ts` (新增)

**功能**:
- 重寫 `console.log`, `console.warn`, `console.error`
- 自動添加 UTC 時間戳

**格式**:
```
[2025-12-27 13:00:00.123] WARN [Vue Router warn]: No match found for location with path "/wp-admin/test.php"
```

**實作**: 僅在服務端運行（避免影響瀏覽器開發工具）

### 3. Nginx 日誌時間戳

**文件**: `nginx/nginx.conf`, `nginx/conf.d/quantlab.conf`

**格式**:
```
2025-12-27T14:07:39+00:00 172.18.0.1 - - "GET / HTTP/1.1" 200 3944 "-" "curl/7.81.0" "-"
```

**配置**:
- 使用 ISO 8601 標準時間格式（`$time_iso8601`）
- 時間戳格式: `YYYY-MM-DDTHH:MM:SS+00:00` (UTC)
- 應用於所有日誌文件：訪問日誌、攔截日誌

**修改文件**:
- `nginx/nginx.conf` - 新增 `log_format main_with_time`
- `nginx/conf.d/quantlab.conf` - 所有 `access_log` 指定使用 `main_with_time`

**日誌位置**:
- 訪問日誌: `/var/log/nginx/quantlab-access.log`
- 錯誤日誌: `/var/log/nginx/quantlab-error.log`
- 攔截日誌: `/var/log/nginx/blocked.log`

### 4. Nginx 安全加固

**文件**: `nginx/conf.d/quantlab.conf`

**新增功能**:
- 攔截 WordPress 掃描 (`/wp-admin/`, `/wp-content/`, `xmlrpc.php`)
- 攔截 PHP 後門 (`*.php`, `*.phtml`, `*.asp`, `*.jsp`)
- 攔截敏感檔案 (`.env`, `.git`, `.htaccess`)
- 攔截後台路徑 (`/admin`, `/phpmyadmin`, `/adminer`)
- 限制 HTTP 方法（只允許 GET, POST, PUT, DELETE, OPTIONS, HEAD）

**安全響應**: 返回 `444` 狀態碼（直接斷開連接）

**攔截日誌**: `/var/log/nginx/blocked.log` (帶時間戳)

### 5. 輔助腳本

#### view-blocked-requests.sh

**功能**:
- 統計被攔截的惡意請求
- 即時監控攔截事件

**使用**:
```bash
bash /home/ubuntu/QuantLab/scripts/view-blocked-requests.sh
```

#### view-nginx-logs.sh (新增)

**功能**:
- 互動式日誌查看工具
- 支援查看訪問日誌、錯誤日誌、攔截日誌
- 統計 Top 10 路徑和來源 IP
- 即時追蹤日誌

**使用**:
```bash
bash /home/ubuntu/QuantLab/scripts/view-nginx-logs.sh
```

**選單**:
1. 訪問日誌（最近 20 條）
2. 錯誤日誌（最近 20 條）
3. 攔截日誌（惡意請求）
4. 即時追蹤訪問日誌
5. 統計訪問 Top 10 路徑
6. 統計訪問來源 IP Top 10

---

## 🔧 時區配置統一

### Docker Compose 環境變數

所有容器統一使用 `TZ=UTC`:

| 容器 | 舊配置 | 新配置 | 狀態 |
|------|--------|--------|------|
| postgres | `TZ: UTC` | `TZ: UTC` | ✅ 未變更 |
| backend | `TZ: Asia/Taipei` | `TZ: UTC` | ✅ 已修改 |
| celery-worker | `TZ: Asia/Taipei` | `TZ: UTC` | ✅ 已修改 |
| celery-beat | `TZ: Asia/Taipei` | `TZ: UTC` | ✅ 已修改 |
| telegram-bot | `TZ: Asia/Taipei` | `TZ: UTC` | ✅ 已修改 |

### 時區掛載移除

**移除的掛載**:
```yaml
- /etc/localtime:/etc/localtime:ro
- /etc/timezone:/etc/timezone:ro
```

**原因**:
- 避免主機時區覆蓋容器環境變數
- 確保所有容器使用 UTC

---

## 📊 日誌格式對比

### 之前（無時間戳）

```
quantlab-backend  | INFO:     172.18.0.11:49400 - "GET /metrics HTTP/1.1" 200 OK
quantlab-frontend | WARN  [Vue Router warn]: No match found for location with path "/wp-admin/test.php"
quantlab-celery-beat | [INFO/MainProcess] Scheduler: Sending due task sync-daily-prices
quantlab-nginx (access.log) | 172.18.0.1 - - [27/Dec/2025:14:06:01 +0000] "GET / HTTP/1.1" 200 3944
```

### 現在（帶時間戳）

```
quantlab-backend  | [2025-12-27 13:58:12] INFO:     172.18.0.11:49400 - "GET /metrics HTTP/1.1" 200 OK
quantlab-frontend | [2025-12-27 13:00:00.123] WARN  [Vue Router warn]: (已被 Nginx 攔截，不再出現)
quantlab-celery-beat | [2025-12-27 13:00:04,303: INFO/MainProcess] Scheduler: Sending due task sync-daily-prices
quantlab-nginx (access.log) | 2025-12-27T14:07:39+00:00 172.18.0.1 - - "GET / HTTP/1.1" 200 3944 "-" "curl/7.81.0" "-"
```

---

## 🛡️ 安全改進效果

### 攔截統計（預期）

**之前**:
- ❌ 每分鐘數十條 Vue Router 警告
- ❌ 前端處理惡意請求，浪費資源

**現在**:
- ✅ Nginx 層直接斷開惡意連接
- ✅ 前端日誌乾淨，無警告
- ✅ 攔截記錄可供審計

### 查看攔截日誌

```bash
# 統計被攔截的請求
bash /home/ubuntu/QuantLab/scripts/view-blocked-requests.sh

# 查看 Nginx 攔截日誌
docker compose exec nginx tail -f /var/log/nginx/blocked.log

# 即時監控
docker compose logs nginx -f | grep "444"
```

---

## 📝 使用指南

### 查看各容器日誌

```bash
# Backend（帶時間戳）
docker compose logs backend -f

# Frontend（帶時間戳）
docker compose logs frontend -f

# Celery Beat（帶時間戳）
docker compose logs celery-beat -f

# Celery Worker（帶時間戳）
docker compose logs celery-worker -f

# Nginx（使用便捷腳本，推薦）
bash /home/ubuntu/QuantLab/scripts/view-nginx-logs.sh

# Nginx 訪問日誌（直接查看文件）
docker compose exec nginx tail -f /var/log/nginx/quantlab-access.log

# Nginx 攔截日誌
docker compose exec nginx tail -f /var/log/nginx/blocked.log
```

### 時間換算（UTC → 台北）

日誌顯示 UTC 時間，需要腦內 +8 小時:

| UTC 時間 | 台北時間 | 說明 |
|---------|---------|------|
| 00:00 | 08:00 | 台灣早上 8 點 |
| 01:00 | 09:00 | 開盤時間 |
| 05:30 | 13:30 | 收盤時間 |
| 13:00 | 21:00 | 晚上 9 點（每日同步） |
| 21:00 | 次日 05:00 | 隔天凌晨 5 點 |

---

## 🔍 驗證方法

### 1. 驗證時間戳格式

```bash
# Backend
docker compose logs backend --tail=10 | grep "INFO:"
# 預期: [2025-12-27 13:58:12] INFO: ...

# Frontend
docker compose logs frontend --tail=10
# 預期: [2025-12-27 13:00:00.123] ...

# Celery
docker compose logs celery-beat --tail=10
# 預期: [2025-12-27 13:00:04,303: INFO/MainProcess] ...

# Nginx
docker compose exec nginx tail -5 /var/log/nginx/quantlab-access.log
# 預期: 2025-12-27T14:07:39+00:00 172.18.0.1 - - "GET / HTTP/1.1" 200 ...
```

### 2. 驗證安全規則

```bash
# 測試惡意請求被攔截（應該無響應）
curl -v http://localhost/wp-admin/test.php
# 預期: 連接被關閉，無 HTTP 響應

# 測試正常請求（應該正常）
curl -v http://localhost/
# 預期: 200 OK
```

### 3. 驗證容器時區

```bash
# 檢查所有容器使用 UTC
docker compose exec backend date
docker compose exec celery-worker date
docker compose exec celery-beat date
# 預期: ... UTC 2025
```

---

## 📦 相關文件

**新增/修改的文件**:
1. `backend/logging_config.yaml` - Uvicorn 日誌配置 (時間戳)
2. `backend/uvicorn_filters.py` - 日誌過濾器（嘗試過濾 /health, /metrics）
3. `backend/start.sh` - 添加日誌配置參數
4. `frontend/plugins/logger.ts` - 前端日誌時間戳插件
5. `nginx/nginx.conf` - 新增 `log_format main_with_time`（ISO 8601 時間戳）
6. `nginx/conf.d/quantlab.conf` - 安全規則、時間戳格式
7. `scripts/view-blocked-requests.sh` - 攔截日誌查看工具
8. `scripts/view-nginx-logs.sh` - Nginx 日誌互動式查看工具（新增）
9. `docker-compose.yml` - 統一時區為 UTC
10. `Document/LOGGING_IMPROVEMENTS.md` - 本文檔

**相關文檔**:
- [TIMEZONE_COMPLETE_GUIDE.md](TIMEZONE_COMPLETE_GUIDE.md) - 時區處理完整指南
- [CLAUDE.md](../CLAUDE.md) - 開發指南

---

## ✅ 檢查清單

部署後驗證:

- [ ] Backend 日誌有時間戳 (`[YYYY-MM-DD HH:MM:SS]`)
- [ ] Frontend 日誌有時間戳
- [ ] Celery 日誌有時間戳
- [ ] 所有容器使用 UTC 時區 (`TZ=UTC`)
- [ ] Nginx 攔截惡意請求（返回 444）
- [ ] 正常請求不受影響（200/404）
- [ ] 攔截日誌可查看 (`/var/log/nginx/blocked.log`)
- [ ] 前端無 Vue Router 警告（惡意掃描）

---

**文檔版本**: 1.0
**最後更新**: 2025-12-27
**維護者**: 開發團隊
**涵蓋範圍**: 日誌時間戳、時區統一、Nginx 安全加固
