# API 快速參考

快速查找 API 端點與代碼位置。

## 📍 API 端點總覽

| 模組 | 端點前綴 | 代碼位置 | 說明 |
|------|---------|---------|------|
| 認證 | `/api/v1/auth` | `backend/app/api/v1/auth.py` | 登入、註冊、Token |
| 用戶 | `/api/v1/users` | `backend/app/api/v1/users.py` | 用戶管理 |
| 策略 | `/api/v1/strategies` | `backend/app/api/v1/strategies.py` | 策略 CRUD |
| 回測 | `/api/v1/backtest` | `backend/app/api/v1/backtest.py` | 回測管理 |
| 數據 | `/api/v1/data` | `backend/app/api/v1/data.py` | 股票數據 |
| 產業 | `/api/v1/industry` | `backend/app/api/v1/industry.py` | 產業分析 |
| RD-Agent | `/api/v1/rdagent` | `backend/app/api/v1/rdagent.py` | AI 因子挖掘 |
| 後台 | `/api/v1/admin` | `backend/app/api/v1/admin.py` | 系統管理 |

## 🔐 認證 API

**基礎 URL**：`/api/v1/auth`
**代碼位置**：`backend/app/api/v1/auth.py`
**Service**：`backend/app/services/user_service.py`

| 端點 | 方法 | 說明 | 速率限制 | 需認證 |
|------|------|------|---------|--------|
| `/register` | POST | 註冊新用戶 | - | ❌ |
| `/login` | POST | 用戶登入 | - | ❌ |
| `/refresh` | POST | 刷新 token | - | ❌ |
| `/logout` | POST | 登出 | - | ✅ |
| `/me` | GET | 獲取當前用戶 | - | ✅ |

**請求範例**：
```bash
# 註冊
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser",
    "password": "password123",
    "full_name": "Test User"
  }'

# 登入
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }'

# 獲取當前用戶
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer {token}"
```

---

## 👤 用戶 API

**基礎 URL**：`/api/v1/users`
**代碼位置**：`backend/app/api/v1/users.py`

| 端點 | 方法 | 說明 | 需權限 |
|------|------|------|--------|
| `/` | GET | 獲取用戶列表 | 管理員 |
| `/{user_id}` | GET | 獲取特定用戶 | - |
| `/{user_id}` | PUT | 更新用戶 | - |
| `/{user_id}` | DELETE | 刪除用戶 | - |

---

## 📊 策略 API

**基礎 URL**：`/api/v1/strategies`
**代碼位置**：`backend/app/api/v1/strategies.py`
**Service**：`backend/app/services/strategy_service.py`

| 端點 | 方法 | 說明 | 速率限制 | 需認證 |
|------|------|------|---------|--------|
| `/` | GET | 獲取策略列表 | - | ✅ |
| `/` | POST | 建立新策略 | 10/hour | ✅ |
| `/{id}` | GET | 獲取策略詳情 | - | ✅ |
| `/{id}` | PUT | 更新策略 | 30/hour | ✅ |
| `/{id}` | DELETE | 刪除策略 | - | ✅ |
| `/{id}/clone` | POST | 複製策略 | - | ✅ |
| `/validate` | POST | 驗證策略代碼 | 20/minute | ✅ |

**查詢參數**（GET `/`）：
- `skip`: 跳過數量（分頁）
- `limit`: 每頁數量（預設 10）
- `status`: 過濾狀態（`active`, `inactive`, `draft`）

**請求範例**：
```bash
# 獲取策略列表
curl -X GET "http://localhost:8000/api/v1/strategies/?skip=0&limit=10" \
  -H "Authorization: Bearer {token}"

# 建立新策略
curl -X POST http://localhost:8000/api/v1/strategies/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "均線策略",
    "description": "雙均線交叉策略",
    "code": "策略代碼...",
    "engine_type": "backtrader",
    "status": "draft"
  }'

# 驗證策略代碼
curl -X POST http://localhost:8000/api/v1/strategies/validate \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"code": "策略代碼..."}'
```

**配額限制**：
- 每用戶最大策略數：50

---

## 🔬 回測 API

**基礎 URL**：`/api/v1/backtest`
**代碼位置**：`backend/app/api/v1/backtest.py`
**Service**：`backend/app/services/backtest_service.py`

| 端點 | 方法 | 說明 | 速率限制 | 需認證 |
|------|------|------|---------|--------|
| `/` | GET | 獲取回測列表 | - | ✅ |
| `/` | POST | 建立新回測 | 10/hour | ✅ |
| `/{id}` | GET | 獲取回測詳情 | - | ✅ |
| `/{id}` | PUT | 更新回測 | - | ✅ |
| `/{id}` | DELETE | 刪除回測 | - | ✅ |
| `/strategy/{strategy_id}` | GET | 獲取策略的回測列表 | - | ✅ |
| `/{id}/result` | GET | 獲取回測結果 | - | ✅ |
| `/run` | POST | 執行回測 | 5/hour | ✅ |

**查詢參數**（GET `/`）：
- `skip`: 跳過數量
- `limit`: 每頁數量
- `status`: 過濾狀態（`pending`, `running`, `completed`, `failed`）

**配額限制**：
- 每用戶最大回測數：200
- 每策略最大回測數：50

---

## 📈 數據 API

**基礎 URL**：`/api/v1/data`
**代碼位置**：`backend/app/api/v1/data.py`
**Service**：`backend/app/services/finlab_client.py`

| 端點 | 方法 | 說明 | 快取時間 | 需認證 |
|------|------|------|---------|--------|
| `/stocks` | GET | 獲取股票清單 | 24 小時 | ✅ |
| `/stocks/search` | POST | 搜尋股票 | - | ✅ |
| `/price/{stock_id}` | GET | 獲取歷史價格 | 10 分鐘 | ✅ |
| `/ohlcv/{stock_id}` | GET | 獲取 OHLCV 數據 | 10 分鐘 | ✅ |
| `/latest-price/{stock_id}` | GET | 獲取最新價格 | 5 分鐘 | ✅ |
| `/cache/clear` | DELETE | 清除快取 | - | ✅ |

**查詢參數**：
- `start_date`: 開始日期（格式：`YYYY-MM-DD`）
- `end_date`: 結束日期
- `pattern`: 快取模式（用於清除快取）

**請求範例**：
```bash
# 獲取股票清單
curl -X GET http://localhost:8000/api/v1/data/stocks \
  -H "Authorization: Bearer {token}"

# 搜尋股票
curl -X POST http://localhost:8000/api/v1/data/stocks/search \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"keyword": "台積電"}'

# 獲取歷史價格
curl -X GET "http://localhost:8000/api/v1/data/price/2330?start_date=2024-01-01&end_date=2024-12-31" \
  -H "Authorization: Bearer {token}"

# 清除快取
curl -X DELETE "http://localhost:8000/api/v1/data/cache/clear?pattern=price:*" \
  -H "Authorization: Bearer {token}"
```

---

## 🏭 產業 API

**基礎 URL**：`/api/v1/industry`
**代碼位置**：`backend/app/api/v1/industry.py`
**Service**：`backend/app/services/industry_service.py`

| 端點 | 方法 | 說明 | 快取時間 | 需認證 |
|------|------|------|---------|--------|
| `/` | GET | 獲取產業列表 | 1 小時 | ✅ |
| `/statistics/overview` | GET | 產業統計總覽 | 1 小時 | ✅ |
| `/{code}/stocks` | GET | 獲取產業內股票 | 1 小時 | ✅ |
| `/{code}/metrics` | GET | 計算產業聚合指標 | 30 天 | ✅ |
| `/{code}/metrics/historical` | GET | 歷史指標趨勢 | 1 天 | ✅ |
| `/finmind/sync` | POST | 同步 FinMind 產業鏈 | - | ✅ |

**產業指標**（7 個）：
- ROE 稅後
- ROA 稅後息前
- 營業毛利率
- 營業利益率
- 每股稅後淨利
- 營收成長率
- 稅後淨利成長率

**請求範例**：
```bash
# 獲取產業列表
curl -X GET http://localhost:8000/api/v1/industry/ \
  -H "Authorization: Bearer {token}"

# 獲取產業指標
curl -X GET http://localhost:8000/api/v1/industry/M15/metrics \
  -H "Authorization: Bearer {token}"
```

**重要提醒**：`fundamental_data` 表使用季度字串（如 "2024-Q4"），計算指標時需使用季度字串匹配。

---

## 🤖 RD-Agent API

**基礎 URL**：`/api/v1/rdagent`
**代碼位置**：`backend/app/api/v1/rdagent.py`
**Service**：`backend/app/services/rdagent_service.py`

| 端點 | 方法 | 說明 | 速率限制 | 需認證 |
|------|------|------|---------|--------|
| `/factor-mining` | POST | 創建因子挖掘任務 | 3/hour | ✅ |
| `/strategy-optimization` | POST | 創建策略優化任務 | 5/hour | ✅ |
| `/tasks` | GET | 獲取任務列表 | - | ✅ |
| `/tasks/{task_id}` | GET | 獲取任務詳情 | - | ✅ |
| `/tasks/{task_id}` | DELETE | 刪除任務 | - | ✅ |
| `/factors` | GET | 獲取生成的因子列表 | - | ✅ |

**請求範例**：
```bash
# 創建因子挖掘任務
curl -X POST http://localhost:8000/api/v1/rdagent/factor-mining \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "research_goal": "找出台股中的動量因子",
    "stock_universe": "台股全市場",
    "max_factors": 5,
    "llm_model": "gpt-4",
    "max_iterations": 3
  }'

# 獲取任務列表
curl -X GET http://localhost:8000/api/v1/rdagent/tasks \
  -H "Authorization: Bearer {token}"

# 獲取生成的因子
curl -X GET http://localhost:8000/api/v1/rdagent/factors \
  -H "Authorization: Bearer {token}"
```

**配額限制**：
- 每任務最多 20 個因子
- 最大迭代次數：10 次

**環境變數**：
- `OPENAI_API_KEY` - 必填（GPT-4 API）

---

## 🔧 後台管理 API

**基礎 URL**：`/api/v1/admin`
**代碼位置**：`backend/app/api/v1/admin.py`

| 端點 | 方法 | 說明 | 需權限 |
|------|------|------|--------|
| `/users` | GET | 使用者列表 | superuser |
| `/users/{user_id}` | GET | 使用者詳情 | superuser |
| `/users/{user_id}` | PATCH | 更新使用者 | superuser |
| `/users/{user_id}` | DELETE | 刪除使用者 | superuser |
| `/stats` | GET | 系統統計 | superuser |
| `/health` | GET | 服務健康檢查 | superuser |
| `/sync/tasks` | GET | 列出同步任務 | superuser |
| `/sync/trigger` | POST | 手動觸發同步 | superuser |
| `/sync/workers` | GET | Celery worker 資訊 | superuser |
| `/sync/active-tasks` | GET | 當前執行中任務 | superuser |
| `/logs/query` | POST | 查詢應用日誌 | superuser |

**系統統計指標**：
- 總用戶數、活躍用戶數
- 策略數、回測數
- 資料庫大小、快取大小

**請求範例**：
```bash
# 獲取系統統計
curl -X GET http://localhost:8000/api/v1/admin/stats \
  -H "Authorization: Bearer {token}"

# 服務健康檢查
curl -X GET http://localhost:8000/api/v1/admin/health \
  -H "Authorization: Bearer {token}"

# 手動觸發任務
curl -X POST http://localhost:8000/api/v1/admin/sync/trigger \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"task_name": "sync_stock_list"}'
```

---

## 📦 響應格式

### 成功響應

```json
{
  "id": 1,
  "name": "策略名稱",
  "created_at": "2024-12-12T10:00:00",
  ...
}
```

### 錯誤響應

```json
{
  "detail": "錯誤訊息"
}
```

### HTTP 狀態碼

| 狀態碼 | 說明 |
|--------|------|
| 200 | 成功 |
| 201 | 創建成功 |
| 400 | 請求錯誤 |
| 401 | 未認證 |
| 403 | 無權限 |
| 404 | 未找到 |
| 429 | 速率限制 / 配額超過 |
| 500 | 服務器錯誤 |

---

## 🔒 認證方式

所有需認證的 API 使用 Bearer Token：

```bash
curl -X GET {endpoint} \
  -H "Authorization: Bearer {your_access_token}"
```

**Token 有效期**：
- Access Token: 30 分鐘
- Refresh Token: 7 天

---

## 📊 速率限制總覽

| 操作 | 限制 |
|------|------|
| 策略建立 | 10 requests/hour |
| 策略更新 | 30 requests/hour |
| 策略驗證 | 20 requests/minute |
| 回測建立 | 10 requests/hour |
| 回測執行 | 5 requests/hour |
| RD-Agent 因子挖掘 | 3 requests/hour |
| RD-Agent 策略優化 | 5 requests/hour |

**重置速率限制**（開發環境）：
```bash
./scripts/reset-rate-limit.sh
```

---

## 📚 互動式文檔

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

---

## 🔗 相關文檔

- [README.md](README.md) - 快速開始
- [CLAUDE.md](CLAUDE.md) - 專案概述
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - 專案結構索引
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - 故障排查
- [Document/DEVELOPMENT_GUIDE.md](Document/DEVELOPMENT_GUIDE.md) - 開發指南
