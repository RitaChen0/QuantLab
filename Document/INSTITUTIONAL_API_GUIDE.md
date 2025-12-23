# 法人買賣超 API 使用指南

## 📋 目錄
- [API 端點總覽](#api-端點總覽)
- [認證方式](#認證方式)
- [API 端點詳細說明](#api-端點詳細說明)
- [使用範例](#使用範例)
- [錯誤處理](#錯誤處理)
- [速率限制](#速率限制)

---

## ✅ API 端點總覽

| 方法 | 端點 | 說明 | 速率限制 |
|------|------|------|----------|
| GET | `/api/v1/institutional/stocks/{stock_id}/data` | 查詢指定股票的法人買賣超數據 | 1000/min |
| GET | `/api/v1/institutional/stocks/{stock_id}/summary` | 查詢指定日期的法人買賣超摘要 | 10000/hour |
| GET | `/api/v1/institutional/stocks/{stock_id}/stats` | 查詢指定期間的法人買賣超統計 | 10000/hour |
| GET | `/api/v1/institutional/rankings/{target_date}` | 查詢指定日期的法人買賣超排行 | 10000/hour |
| POST | `/api/v1/institutional/sync/{stock_id}` | 觸發單一股票的數據同步（異步） | 1000/hour |
| POST | `/api/v1/institutional/sync/batch` | 批量同步多個股票的數據（異步） | 1000/hour |
| GET | `/api/v1/institutional/status/latest-date` | 查詢最新數據日期 | 10000/hour |

---

## 🔐 認證方式

所有 API 端點都需要 JWT Token 認證。

### 1. 獲取 Token

```bash
# 登入獲取 Token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'
```

**響應：**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### 2. 使用 Token

在所有請求的 Header 中加入 Authorization：

```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

---

## 📖 API 端點詳細說明

### 1. 查詢股票法人買賣超數據

**端點：** `GET /api/v1/institutional/stocks/{stock_id}/data`

**參數：**
- `stock_id` (path) - 股票代碼，例如：2330
- `start_date` (query, required) - 開始日期，格式：YYYY-MM-DD
- `end_date` (query, required) - 結束日期，格式：YYYY-MM-DD
- `investor_type` (query, optional) - 法人類型（可選）
  - `Foreign_Investor` - 外資
  - `Investment_Trust` - 投信
  - `Dealer_self` - 自營商-自行買賣
  - `Dealer_Hedging` - 自營商-避險
  - `Foreign_Dealer_Self` - 外資自營商

**請求範例：**
```bash
curl -X GET "http://localhost:8000/api/v1/institutional/stocks/2330/data?start_date=2024-12-01&end_date=2024-12-05&investor_type=Foreign_Investor" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**響應範例：**
```json
[
  {
    "id": 1,
    "date": "2024-12-02",
    "stock_id": "2330",
    "investor_type": "Foreign_Investor",
    "buy_volume": 22853421,
    "sell_volume": 11904333,
    "net_buy_sell": 10949088,
    "created_at": "2024-12-13T10:52:56.000Z",
    "updated_at": "2024-12-13T10:52:56.000Z"
  }
]
```

---

### 2. 查詢單日法人買賣超摘要

**端點：** `GET /api/v1/institutional/stocks/{stock_id}/summary`

**參數：**
- `stock_id` (path) - 股票代碼
- `target_date` (query, required) - 目標日期，格式：YYYY-MM-DD

**請求範例：**
```bash
curl -X GET "http://localhost:8000/api/v1/institutional/stocks/2330/summary?target_date=2024-12-02" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**響應範例：**
```json
{
  "date": "2024-12-02",
  "stock_id": "2330",
  "foreign_net": 10949088,
  "trust_net": 348109,
  "dealer_self_net": 12270,
  "dealer_hedging_net": -133215,
  "total_net": 11176252
}
```

---

### 3. 查詢期間法人買賣超統計

**端點：** `GET /api/v1/institutional/stocks/{stock_id}/stats`

**參數：**
- `stock_id` (path) - 股票代碼
- `investor_type` (query, required) - 法人類型
- `start_date` (query, required) - 開始日期
- `end_date` (query, required) - 結束日期

**請求範例：**
```bash
curl -X GET "http://localhost:8000/api/v1/institutional/stocks/2330/stats?investor_type=Foreign_Investor&start_date=2024-12-01&end_date=2024-12-05" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**響應範例：**
```json
{
  "stock_id": "2330",
  "investor_type": "Foreign_Investor",
  "period_start": "2024-12-01",
  "period_end": "2024-12-05",
  "total_buy": 75607647,
  "total_sell": 64658559,
  "total_net": 10949088,
  "avg_daily_net": 2737272.0,
  "buy_days": 3,
  "sell_days": 1
}
```

---

### 4. 查詢法人買賣超排行榜

**端點：** `GET /api/v1/institutional/rankings/{target_date}`

**參數：**
- `target_date` (path) - 目標日期，格式：YYYY-MM-DD
- `investor_type` (query, required) - 法人類型
- `limit` (query, optional) - 返回數量，預設 50，範圍 1-200
- `order` (query, optional) - 排序方式，`desc`（買超在前）或 `asc`（賣超在前），預設 desc

**請求範例：**
```bash
curl -X GET "http://localhost:8000/api/v1/institutional/rankings/2024-12-02?investor_type=Foreign_Investor&limit=10&order=desc" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**響應範例：**
```json
[
  {
    "id": 1,
    "date": "2024-12-02",
    "stock_id": "2330",
    "investor_type": "Foreign_Investor",
    "buy_volume": 22853421,
    "sell_volume": 11904333,
    "net_buy_sell": 10949088,
    "created_at": "2024-12-13T10:52:56.000Z",
    "updated_at": "2024-12-13T10:52:56.000Z"
  }
]
```

---

### 5. 觸發單一股票數據同步

**端點：** `POST /api/v1/institutional/sync/{stock_id}`

**參數：**
- `stock_id` (path) - 股票代碼
- `start_date` (query, optional) - 開始日期，預設為最新數據日期的下一天
- `end_date` (query, optional) - 結束日期，預設為今天
- `force` (query, optional) - 是否強制覆蓋現有數據，預設 false

**請求範例：**
```bash
curl -X POST "http://localhost:8000/api/v1/institutional/sync/2330?start_date=2024-12-01&end_date=2024-12-05&force=false" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**響應範例：**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending",
  "message": "Sync task started for 2330"
}
```

---

### 6. 批量同步多個股票數據

**端點：** `POST /api/v1/institutional/sync/batch`

**參數：**
- `stock_ids` (query, required) - 股票代碼列表，例如：`?stock_ids=2330&stock_ids=2317`
- `days` (query, optional) - 同步最近 N 天，預設 7，範圍 1-90

**請求範例：**
```bash
curl -X POST "http://localhost:8000/api/v1/institutional/sync/batch?stock_ids=2330&stock_ids=2317&days=7" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**響應範例：**
```json
{
  "task_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "status": "pending",
  "message": "Batch sync task started for 2 stocks"
}
```

---

### 7. 查詢最新數據日期

**端點：** `GET /api/v1/institutional/status/latest-date`

**參數：**
- `stock_id` (query, optional) - 股票代碼，如果不提供則返回全局最新日期

**請求範例：**
```bash
curl -X GET "http://localhost:8000/api/v1/institutional/status/latest-date?stock_id=2330" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**響應範例：**
```json
{
  "stock_id": "2330",
  "latest_date": "2024-12-05"
}
```

---

## 🔍 使用範例

### Python 範例

```python
import requests
from datetime import date, timedelta

# 設定 API URL 和 Token
API_BASE = "http://localhost:8000/api/v1"
TOKEN = "your_access_token_here"
headers = {"Authorization": f"Bearer {TOKEN}"}

# 1. 查詢台積電最近 5 天的外資買賣超
end_date = date.today()
start_date = end_date - timedelta(days=5)

response = requests.get(
    f"{API_BASE}/institutional/stocks/2330/data",
    params={
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "investor_type": "Foreign_Investor"
    },
    headers=headers
)

data = response.json()
for record in data:
    print(f"{record['date']}: 買賣超 {record['net_buy_sell']:,} 股")

# 2. 查詢今日法人買賣超摘要
response = requests.get(
    f"{API_BASE}/institutional/stocks/2330/summary",
    params={"target_date": date.today().isoformat()},
    headers=headers
)

summary = response.json()
print(f"外資: {summary['foreign_net']:,}")
print(f"投信: {summary['trust_net']:,}")
print(f"三大法人合計: {summary['total_net']:,}")

# 3. 觸發數據同步
response = requests.post(
    f"{API_BASE}/institutional/sync/2330",
    params={
        "start_date": "2024-12-01",
        "end_date": "2024-12-05"
    },
    headers=headers
)

task = response.json()
print(f"同步任務已啟動: {task['task_id']}")
```

### JavaScript 範例

```javascript
const API_BASE = 'http://localhost:8000/api/v1';
const TOKEN = 'your_access_token_here';
const headers = {
  'Authorization': `Bearer ${TOKEN}`,
  'Content-Type': 'application/json'
};

// 1. 查詢台積電法人買賣超數據
async function getInstitutionalData(stockId, startDate, endDate) {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
    investor_type: 'Foreign_Investor'
  });

  const response = await fetch(
    `${API_BASE}/institutional/stocks/${stockId}/data?${params}`,
    { headers }
  );

  return await response.json();
}

// 2. 查詢單日摘要
async function getDailySummary(stockId, targetDate) {
  const params = new URLSearchParams({ target_date: targetDate });

  const response = await fetch(
    `${API_BASE}/institutional/stocks/${stockId}/summary?${params}`,
    { headers }
  );

  return await response.json();
}

// 使用範例
getInstitutionalData('2330', '2024-12-01', '2024-12-05')
  .then(data => {
    data.forEach(record => {
      console.log(`${record.date}: 買賣超 ${record.net_buy_sell.toLocaleString()} 股`);
    });
  });
```

### cURL 範例

```bash
# 設定變數
TOKEN="your_access_token_here"
API_BASE="http://localhost:8000/api/v1"

# 1. 查詢法人買賣超數據
curl -X GET "$API_BASE/institutional/stocks/2330/data?start_date=2024-12-01&end_date=2024-12-05&investor_type=Foreign_Investor" \
  -H "Authorization: Bearer $TOKEN" | jq .

# 2. 查詢單日摘要
curl -X GET "$API_BASE/institutional/stocks/2330/summary?target_date=2024-12-02" \
  -H "Authorization: Bearer $TOKEN" | jq .

# 3. 查詢統計數據
curl -X GET "$API_BASE/institutional/stocks/2330/stats?investor_type=Foreign_Investor&start_date=2024-12-01&end_date=2024-12-05" \
  -H "Authorization: Bearer $TOKEN" | jq .

# 4. 查詢排行榜
curl -X GET "$API_BASE/institutional/rankings/2024-12-02?investor_type=Foreign_Investor&limit=10" \
  -H "Authorization: Bearer $TOKEN" | jq .

# 5. 觸發同步
curl -X POST "$API_BASE/institutional/sync/2330?start_date=2024-12-01&end_date=2024-12-05" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

---

## ⚠️ 錯誤處理

### 常見錯誤碼

| 狀態碼 | 說明 | 解決方法 |
|--------|------|----------|
| 401 | 未授權 | 檢查 Token 是否有效 |
| 404 | 資源不存在 | 檢查股票代碼或日期是否正確 |
| 422 | 參數驗證失敗 | 檢查參數格式和範圍 |
| 429 | 超過速率限制 | 降低請求頻率 |
| 500 | 伺服器錯誤 | 檢查日誌或聯絡管理員 |

### 錯誤響應範例

```json
{
  "detail": "Failed to fetch institutional data: Stock not found"
}
```

---

## 🚦 速率限制

### 開發環境（當前）

- **查詢操作**：10,000 requests/hour
- **數據抓取**：1,000 requests/minute
- **同步操作**：1,000 requests/hour
- **批量同步**：3 requests/hour

### 生產環境

- **查詢操作**：1,000 requests/hour
- **數據抓取**：100 requests/minute
- **同步操作**：100 requests/hour
- **批量同步**：3 requests/hour

### 速率限制響應

當超過限制時，API 會返回 429 狀態碼：

```json
{
  "error": "Rate limit exceeded",
  "detail": "Too many requests. Please try again later."
}
```

---

## 📚 相關文檔

- **Swagger UI**：http://localhost:8000/docs
- **ReDoc**：http://localhost:8000/redoc
- **OpenAPI JSON**：http://localhost:8000/api/v1/openapi.json

---

## 🎯 最佳實踐

1. **使用異步同步**：大量數據同步使用 POST 端點，避免阻塞
2. **快取策略**：客戶端應快取常用數據，減少 API 請求
3. **批量查詢**：優先使用日期範圍查詢，而非多次單日查詢
4. **錯誤重試**：實作指數退避重試機制
5. **Token 管理**：定期刷新 Token，避免過期

---

## 📞 支援

如有問題，請：
1. 查看 API 文檔：http://localhost:8000/docs
2. 檢查系統日誌：`docker compose logs backend`
3. 提交 Issue：https://github.com/your-repo/issues

---

**最後更新：** 2024-12-13
**API 版本：** v1
**QuantLab 版本：** 0.1.0
