# ✅ QuantLab 增強錯誤處理系統

## 🎯 功能特點

### ✨ 主要改進
1. ✅ **開發環境：顯示完整堆棧追蹤** - Docker 內的真實錯誤直接回傳前端
2. ✅ **生產環境：隱藏敏感信息** - 保護系統安全
3. ✅ **統一錯誤格式** - 所有錯誤響應格式一致
4. ✅ **自定義錯誤類型** - 資料庫錯誤、回測錯誤、策略錯誤等
5. ✅ **前端錯誤展示組件** - 可折疊、可複製、可回報

---

## 🔧 後端改進

### 1. 新增全局異常處理器

**檔案**: `backend/app/core/exceptions.py`

**功能**:
- ✅ 捕獲所有未處理異常
- ✅ 根據環境自動切換錯誤詳細程度
- ✅ 統一錯誤響應格式
- ✅ 記錄完整日誌

**錯誤響應格式**:
```json
{
  "success": false,
  "error": {
    "type": "DatabaseError",
    "message": "錯誤訊息",
    "code": "DATABASE_ERROR",
    "details": { ... },
    "traceback": "完整堆棧追蹤（僅開發環境）"
  },
  "request": {
    "method": "POST",
    "url": "http://localhost:8000/api/v1/backtest",
    "client": "127.0.0.1"
  }
}
```

### 2. 自定義異常類型

```python
from app.core.exceptions import BacktestError, StrategyError, DatabaseError

# 範例：回測執行錯誤
raise BacktestError(
    message="回測執行失敗：數據不足",
    details={
        "stock_id": "2330",
        "date_range": "2024-01-01 to 2024-12-31",
        "available_data": 245,
        "required_data": 252
    }
)
```

### 3. 環境控制

**.env 配置**:
```bash
# 開發環境（顯示完整錯誤）
DEBUG=True
ENVIRONMENT=development

# 生產環境（隱藏敏感信息）
DEBUG=False
ENVIRONMENT=production
```

---

## 🎨 前端改進

### 1. ErrorDisplay 組件

**檔案**: `frontend/components/ErrorDisplay.vue`

**功能**:
- ✅ 美觀的錯誤展示
- ✅ 可折疊的詳細信息
- ✅ 複製堆棧追蹤到剪貼簿
- ✅ 複製完整錯誤 JSON
- ✅ 一鍵回報問題

**使用範例**:
```vue
<template>
  <div>
    <ErrorDisplay
      v-if="currentError"
      :error="currentError"
      @close="clearError"
    />
  </div>
</template>

<script setup>
import { useErrorHandler } from '@/composables/useErrorHandler'
import ErrorDisplay from '@/components/ErrorDisplay.vue'

const { currentError, clearError } = useErrorHandler()
</script>
```

### 2. useErrorHandler Composable

**檔案**: `frontend/composables/useErrorHandler.ts`

**功能**:
- ✅ 統一錯誤處理
- ✅ 自動顯示 Toast 通知
- ✅ 可選顯示詳細錯誤對話框
- ✅ 開發環境自動記錄到 Console

**使用範例 1：基本用法**
```vue
<script setup>
import { useErrorHandler } from '@/composables/useErrorHandler'

const { handleError } = useErrorHandler()

const runBacktest = async () => {
  try {
    const response = await $fetch('/api/v1/backtest', {
      method: 'POST',
      body: { ... }
    })
  } catch (error) {
    // 自動顯示 Toast + 記錄到 Console
    handleError(error)
  }
}
</script>
```

**使用範例 2：顯示詳細錯誤對話框**
```vue
<script setup>
import { useErrorHandler } from '@/composables/useErrorHandler'
import ErrorDisplay from '@/components/ErrorDisplay.vue'

const { currentError, showErrorDialog, handleError, clearError } = useErrorHandler()

const runBacktest = async () => {
  try {
    const response = await $fetch('/api/v1/backtest', {
      method: 'POST',
      body: { ... }
    })
  } catch (error) {
    // 顯示 Toast + 彈出詳細錯誤對話框
    handleError(error, { showDialog: true })
  }
}
</script>

<template>
  <div>
    <!-- 其他內容 -->

    <!-- 錯誤對話框 -->
    <div v-if="showErrorDialog" class="error-overlay">
      <ErrorDisplay :error="currentError" @close="clearError" />
    </div>
  </div>
</template>

<style scoped>
.error-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}
</style>
```

**使用範例 3：自動錯誤處理包裝器**
```vue
<script setup>
import { useErrorHandler } from '@/composables/useErrorHandler'

const { withErrorHandling } = useErrorHandler()

const runBacktest = async () => {
  // 自動捕獲錯誤，返回 null 而不是拋出異常
  const result = await withErrorHandling(
    async () => {
      return await $fetch('/api/v1/backtest', {
        method: 'POST',
        body: { ... }
      })
    },
    {
      showToast: true,
      showDialog: true,
      customMessage: '回測執行失敗'
    }
  )

  if (result) {
    console.log('回測成功:', result)
  } else {
    console.log('回測失敗（錯誤已處理）')
  }
}
</script>
```

---

## 🚀 部署步驟

### 1. 重啟 Backend 服務
```bash
docker compose restart backend
```

### 2. 測試錯誤處理

**測試 API**:
```bash
# 測試驗證錯誤
curl -X POST http://localhost:8000/api/v1/backtest \
  -H "Content-Type: application/json" \
  -d '{"invalid": "data"}'

# 預期響應（開發環境）
{
  "success": false,
  "error": {
    "type": "ValidationError",
    "message": "請求參數驗證失敗",
    "code": "VALIDATION_ERROR",
    "details": [
      {
        "type": "missing",
        "loc": ["body", "strategy_id"],
        "msg": "Field required"
      }
    ],
    "traceback": "Traceback (most recent call last):\n..."
  }
}
```

### 3. 驗證環境切換

**開發環境** (DEBUG=True):
- ✅ 顯示完整堆棧追蹤
- ✅ 顯示請求信息
- ✅ 顯示數據庫 SQL 錯誤詳情

**生產環境** (DEBUG=False):
- ✅ 隱藏堆棧追蹤
- ✅ 隱藏敏感信息
- ✅ 顯示用戶友好的錯誤訊息

---

## 📊 錯誤類型對照表

| 錯誤代碼 | 錯誤類型 | 狀態碼 | 說明 |
|---------|---------|--------|------|
| `VALIDATION_ERROR` | 參數驗證錯誤 | 422 | 請求參數格式錯誤 |
| `DATABASE_ERROR` | 資料庫錯誤 | 500 | 資料庫操作失敗 |
| `BACKTEST_ERROR` | 回測錯誤 | 500 | 回測執行失敗 |
| `STRATEGY_ERROR` | 策略錯誤 | 400 | 策略代碼或配置錯誤 |
| `HTTP_404` | 資源不存在 | 404 | 請求的資源不存在 |
| `HTTP_403` | 權限不足 | 403 | 沒有訪問權限 |
| `HTTP_401` | 未授權 | 401 | 需要登入 |
| `NETWORK_ERROR` | 網絡錯誤 | - | 網絡連接失敗 |

---

## 🎯 使用場景範例

### 場景 1：回測執行失敗

**後端拋出錯誤**:
```python
# backend/app/services/backtest_service.py
from app.core.exceptions import BacktestError

if len(stock_data) < 100:
    raise BacktestError(
        message=f"股票 {stock_id} 數據不足，無法執行回測",
        details={
            "stock_id": stock_id,
            "available_days": len(stock_data),
            "required_days": 100,
            "date_range": f"{start_date} to {end_date}"
        }
    )
```

**前端接收並顯示**:
```vue
<script setup>
const { handleError } = useErrorHandler()

const runBacktest = async () => {
  try {
    await $fetch('/api/v1/backtest', { ... })
  } catch (error) {
    handleError(error, { showDialog: true })
  }
}
</script>
```

**用戶看到的錯誤**:
```
❌ 回測執行錯誤

股票 2330 數據不足，無法執行回測

詳細信息：
{
  "stock_id": "2330",
  "available_days": 85,
  "required_days": 100,
  "date_range": "2024-09-01 to 2024-12-31"
}

堆棧追蹤：
Traceback (most recent call last):
  File "/app/app/services/backtest_service.py", line 123, in run_backtest
    raise BacktestError(...)
  ...
```

### 場景 2：資料庫連接失敗

**後端自動捕獲**:
```python
# SQLAlchemy 錯誤會被自動捕獲
db.query(Stock).filter(Stock.id == stock_id).first()
# 如果資料庫連接失敗，會觸發 sqlalchemy_exception_handler
```

**用戶看到的錯誤**（開發環境）:
```
💾 資料庫錯誤

(psycopg2.OperationalError) could not connect to server: Connection refused

堆棧追蹤：
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not connect to server: Connection refused
  Is the server running on host "postgres" (172.18.0.2) and accepting
  TCP/IP connections on port 5432?
  ...
```

**用戶看到的錯誤**（生產環境）:
```
💾 資料庫錯誤

資料庫操作失敗
```

---

## 🛡️ 安全注意事項

### 生產環境必須設置
```bash
# .env
DEBUG=False
ENVIRONMENT=production
```

### 不應暴露的信息
- ❌ 資料庫連接字串
- ❌ API 密鑰
- ❌ 內部文件路徑
- ❌ 資料庫結構詳情
- ❌ 伺服器 IP/端口

### 可以顯示的信息
- ✅ 錯誤類型（VALIDATION_ERROR 等）
- ✅ 用戶友好的錯誤訊息
- ✅ 驗證錯誤的欄位名稱
- ✅ 錯誤代碼

---

## 📝 日誌記錄

所有錯誤都會記錄到日誌，即使在生產環境：

```bash
# 查看錯誤日誌
docker compose logs backend | grep ERROR

# 即時追蹤錯誤
docker compose logs -f backend | grep -E "ERROR|CRITICAL"
```

**日誌格式**:
```
2025-12-31 10:30:45.123 | ERROR | app.core.exceptions:123 - Database Error: (psycopg2.OperationalError) could not connect to server
Traceback (most recent call last):
  File "/app/app/services/backtest_service.py", line 45, in get_stock_data
    ...
```

---

## ✅ 檢查清單

### 後端部署
- [ ] 已新增 `backend/app/core/exceptions.py`
- [ ] 已修改 `backend/app/main.py` 註冊異常處理器
- [ ] 已設置 `.env` 環境變數（DEBUG, ENVIRONMENT）
- [ ] 已重啟 backend 服務
- [ ] 已測試錯誤響應格式

### 前端部署
- [ ] 已新增 `frontend/components/ErrorDisplay.vue`
- [ ] 已新增 `frontend/composables/useErrorHandler.ts`
- [ ] 已在需要的頁面使用錯誤處理
- [ ] 已測試錯誤顯示效果

### 測試
- [ ] 測試驗證錯誤（422）
- [ ] 測試資料庫錯誤（500）
- [ ] 測試回測錯誤
- [ ] 測試網絡錯誤
- [ ] 測試開發/生產環境切換

---

## 🎉 總結

### 改進前
```
❌ 錯誤訊息：Internal Server Error
❌ 無法知道發生什麼問題
❌ 需要查看 Docker logs 才能調試
❌ 用戶體驗差
```

### 改進後
```
✅ 詳細錯誤訊息（開發環境）
✅ 完整堆棧追蹤（開發環境）
✅ 一鍵複製錯誤信息
✅ 可直接回報問題
✅ 生產環境自動隱藏敏感信息
✅ 統一錯誤格式
✅ 優雅的錯誤展示
```

**現在，Docker 內的真實錯誤會直接、清晰地回傳給用戶！** 🚀
