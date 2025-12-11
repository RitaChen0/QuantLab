# Admin 用戶編輯 - Cash 欄位儲存修復

## 🐛 問題描述

**症狀**: 在後台管理的用戶編輯頁面，修改用戶的「現金」(cash) 和「信用」(credit) 欄位後，點擊保存，但數據沒有被儲存到資料庫。

## 🔍 根本原因

後端 API 的 Pydantic Schema (`UserUpdateAdmin`) 缺少 `cash` 和 `credit` 欄位定義，導致：
1. 前端送出的 cash 和 credit 數據被 Pydantic 驗證時過濾掉
2. 只有 schema 中定義的欄位會被寫入資料庫
3. API 返回的 `UserListResponse` 也缺少這些欄位

## ✅ 修復內容

### 檔案: `backend/app/schemas/admin.py`

#### 1. 更新 `UserListResponse` Schema
```python
class UserListResponse(BaseModel):
    """User list response for admin"""
    id: int
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    member_level: int
    email_verified: bool
    cash: float = 0.0           # ✅ 新增
    credit: float = 0.0         # ✅ 新增
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True
```

#### 2. 更新 `UserUpdateAdmin` Schema
```python
class UserUpdateAdmin(BaseModel):
    """Update user by admin"""
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    member_level: Optional[int] = Field(None, ge=0, le=9)  # ✅ 更新範圍 0-9
    email_verified: Optional[bool] = None
    cash: Optional[float] = Field(None, ge=0, description="現金餘額")      # ✅ 新增
    credit: Optional[float] = Field(None, ge=0, description="信用點數")     # ✅ 新增
```

## 🎯 修復效果

### 修復前
```
前端 → API: {cash: 1500.75, credit: 750.50, ...}
             ↓ (Pydantic 驗證)
資料庫     : cash 和 credit 被忽略 ❌
API 返回   : 沒有 cash 和 credit 欄位 ❌
```

### 修復後
```
前端 → API: {cash: 1500.75, credit: 750.50, ...}
             ↓ (Pydantic 驗證通過)
資料庫     : cash = 1500.75, credit = 750.50 ✅
API 返回   : {cash: 1500.75, credit: 750.50, ...} ✅
```

## 🧪 測試步驟

### 前端測試（推薦）

1. **登入管理員帳號**
   - 使用具有 `is_superuser = true` 的帳號登入
   - 例如: `admin`, `robert`, 等

2. **進入後台管理頁面**
   - 導航到 `/admin`

3. **編輯用戶**
   - 點擊任意用戶的「編輯」按鈕
   - 修改「現金餘額」和「信用點數」
   - 例如: 現金 = 2500.50, 信用 = 1250.75

4. **保存並驗證**
   - 點擊「保存」
   - 刷新頁面
   - **驗證**: 用戶列表中應該顯示更新後的值

5. **Dashboard 驗證**
   - 登出管理員
   - 使用剛才編輯的用戶登入
   - 進入 Dashboard
   - **驗證**: 帳戶餘額顯示更新後的值

### API 測試（進階）

```bash
# 1. 登入管理員
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"your_password"}' \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2. 更新用戶 (假設 user_id = 37)
curl -X PATCH http://localhost:8000/api/v1/admin/users/37 \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"cash": 3000.99, "credit": 1500.50}' \
    | python3 -m json.tool

# 預期輸出包含:
# {
#   "id": 37,
#   "username": "free_user",
#   "cash": 3000.99,    ✅
#   "credit": 1500.50,  ✅
#   ...
# }
```

### 資料庫驗證

```sql
-- 查看用戶的 cash 和 credit
SELECT id, username, member_level, cash, credit 
FROM users 
WHERE username = 'free_user';

-- 預期看到更新後的值
--  id | username  | member_level |  cash   | credit
-- ----+-----------+--------------+---------+--------
--  37 | free_user |            0 | 3000.99 | 1500.50
```

## 🔧 相關 API 端點

### PATCH /api/v1/admin/users/{user_id}

**請求 Body** (可選欄位):
```json
{
  "email": "new@example.com",
  "full_name": "New Name",
  "is_active": true,
  "is_superuser": false,
  "member_level": 3,
  "email_verified": true,
  "cash": 1500.75,
  "credit": 750.50
}
```

**響應**:
```json
{
  "id": 37,
  "email": "new@example.com",
  "username": "free_user",
  "full_name": "New Name",
  "is_active": true,
  "is_superuser": false,
  "member_level": 3,
  "email_verified": true,
  "cash": 1500.75,
  "credit": 750.50,
  "created_at": "2024-01-01T00:00:00",
  "last_login": null
}
```

## 📝 技術細節

### Pydantic Schema 驗證流程

1. **請求到達**: FastAPI 接收 JSON 請求
2. **Schema 驗證**: Pydantic 根據 `UserUpdateAdmin` 驗證欄位
   - 只有 Schema 中定義的欄位會被保留
   - 額外的欄位會被忽略（除非設置 `Extra.allow`）
3. **資料庫更新**: `model_dump(exclude_unset=True)` 只更新提供的欄位
4. **響應序列化**: 根據 `UserListResponse` Schema 返回數據

### 為什麼需要兩個 Schema

| Schema | 用途 | 包含欄位 |
|--------|------|----------|
| `UserUpdateAdmin` | 驗證輸入 | 只包含可修改的欄位 |
| `UserListResponse` | 格式化輸出 | 包含所有返回欄位 |

### 欄位驗證規則

```python
cash: Optional[float] = Field(None, ge=0, description="現金餘額")
```

- `Optional[float]`: 可選的浮點數
- `None`: 預設值（不提供時不更新）
- `ge=0`: 大於等於 0（不能為負數）

## 🚀 部署狀態

- [x] 修改 Schema 定義
- [x] 後端服務重啟
- [x] API 端點正常運行
- [ ] 前端測試驗證
- [ ] 生產環境部署

## 📁 修改檔案

- ✅ `backend/app/schemas/admin.py` - 更新 Schema 定義

## 🔍 故障排除

### 問題 1: 仍然無法儲存

**檢查**:
1. 後端服務是否已重啟？`docker compose restart backend`
2. 瀏覽器是否有緩存？按 Ctrl+Shift+R 硬刷新
3. 檢查 Network 標籤，確認請求包含 cash 和 credit

### 問題 2: 值為 0

**可能原因**:
- 前端送出時欄位為空字串 `""`
- 修改前端確保送出數字: `parseFloat(editForm.cash)`

### 問題 3: API 返回錯誤

**常見錯誤**:
- `422 Unprocessable Entity`: 數值驗證失敗（負數、非數字）
- `403 Forbidden`: 不是 superuser
- `404 Not Found`: 用戶 ID 不存在

---

**修復日期**: 2025-12-11  
**版本**: v1.0  
**狀態**: ✅ 已修復（需前端測試驗證）
