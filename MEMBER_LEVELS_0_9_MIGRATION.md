# 會員等級系統重構 - 0 到 9 級

## 📋 變更摘要

從 3 級會員系統（0/3/6 + 倍數系統）重構為 10 級會員系統（0-9 + 固定 Rate Limit）

### 舊系統 (已棄用)
- **等級**: 3 個 (Level 0/3/6)
  - Level 0: 免費用戶
  - Level 3: 付費用戶 (5x)
  - Level 6: VIP 用戶 (10x)
- **Rate Limit**: 使用倍數系統 (1x/5x/10x)

### 新系統 (當前)
- **等級**: 10 個 (Level 0-9)
  - Level 0: 註冊會員
  - Level 1: 普通會員
  - Level 2: 中階會員
  - Level 3: 高階會員
  - Level 4: VIP會員
  - Level 5: 系統推廣會員
  - Level 6: 系統管理員1
  - Level 7: 系統管理員2
  - Level 8: 系統管理員3
  - Level 9: 創造者等級
- **Rate Limit**: 所有限制均為固定值，不使用倍數系統

## 🎯 Rate Limit 配置表

| 等級 | 名稱 | 回測執行 | 策略建立 | 資料查詢 | 因子挖掘 |
|------|------|----------|----------|----------|----------|
| 0 | 註冊會員 | 10/hour | 10/hour | 100/minute | 0/hour ❌ |
| 1 | 普通會員 | 20/hour | 20/hour | 200/minute | 0/hour ❌ |
| 2 | 中階會員 | 30/hour | 30/hour | 300/minute | 0/hour ❌ |
| 3 | 高階會員 | 40/hour | 40/hour | 400/minute | 1/hour |
| 4 | VIP會員 | 50/hour | 50/hour | 500/minute | 2/hour |
| 5 | 系統推廣會員 | 60/hour | 60/hour | 600/minute | 3/hour |
| 6 | 系統管理員1 | 70/hour | 70/hour | 700/minute | 6/hour |
| 7 | 系統管理員2 | 3000/hour | 3000/hour | 3000/minute | 3000/hour |
| 8 | 系統管理員3 | 3000/hour | 3000/hour | 3000/minute | 3000/hour |
| 9 | 創造者等級 | 3000/hour | 3000/hour | 3000/minute | 3000/hour |

### 特殊限制
- **因子挖掘**: Level 0-2 完全不可使用（API 返回 403 Forbidden）
- **管理員等級**: Level 7-9 擁有近乎無限的限制（3000/hour 或 3000/minute）

## ✅ 實作完成項目

### 後端修改

#### 1. 會員限制配置 (`backend/app/core/member_limits.py`)
- ✅ 完全重寫，移除倍數系統
- ✅ 新增 10 級會員定義 (MEMBER_LEVELS 字典)
- ✅ 4 個固定 Rate Limit 字典:
  - `BACKTEST_LIMITS`: 回測執行限制
  - `STRATEGY_CREATE_LIMITS`: 策略建立限制
  - `DATA_QUERY_LIMITS`: 資料查詢限制
  - `FACTOR_MINING_LIMITS`: 因子挖掘限制
- ✅ 新增函數:
  - `get_level_name()`: 獲取等級名稱
  - `get_backtest_limit()`: 獲取回測限制
  - `get_strategy_create_limit()`: 獲取策略建立限制
  - `get_data_query_limit()`: 獲取資料查詢限制
  - `get_factor_mining_limit()`: 獲取因子挖掘限制
  - `get_all_limits()`: 獲取所有限制
  - `is_level_valid()`: 驗證等級有效性
  - `get_level_color()`: 獲取等級顏色（前端用）
- ✅ 移除舊函數:
  - `MemberLevel` enum (改為 MEMBER_LEVELS 字典)
  - `MemberLimitMultiplier` 類別
  - `get_user_rate_limit()` 函數
  - `apply_multiplier()` 函數

#### 2. Rate Limit 配置 (`backend/app/core/rate_limit.py`)
- ✅ 更新 import: 只保留 `get_level_name`
- ✅ 移除對已棄用函數的引用
- ✅ 註解掉 `tiered_rate_limit()` 和 `get_user_limit_info()` (標記為 DEPRECATED)

#### 3. 會員資訊 API (`backend/app/api/v1/membership.py`)
- ✅ 完全重寫，適配新系統
- ✅ 使用新的 import:
  - `MEMBER_LEVELS`, `MIN_LEVEL`, `MAX_LEVEL`
  - `get_level_name`, `get_all_limits`, `is_level_valid`
- ✅ 更新 `MemberLevelUpdate` schema: 支援 0-9 級
- ✅ 簡化 `MemberInfo` schema: 移除 `rate_limit_multiplier`
- ✅ 更新 `get_my_membership_info()`: 使用 `get_all_limits()`
- ✅ 簡化 `get_my_rate_limits()`: 返回格式改為 `{limit, description}`
- ✅ 更新 `update_member_level()`: 支援 0-9 級驗證
- ✅ 更新 `get_all_member_levels()`: 返回所有 10 個等級資訊

#### 4. RD-Agent API (`backend/app/api/v1/rdagent.py`)
- ✅ 更新因子挖掘檢查: `if user_level < 3` (Level 0-2 不可用)
- ✅ 更新錯誤訊息: "因子挖掘功能僅限 Level 3 以上會員使用"
- ✅ 更新文檔字串: 列出所有等級的限制

### 前端修改

#### 1. Admin 頁面 (`frontend/pages/admin/index.vue`)
- ✅ 更新會員等級下拉選單: 10 個選項 (Level 0-9)
- ✅ 更新 CSS `.level-badge`: 10 個等級顏色樣式

#### 2. Dashboard 頁面 (`frontend/pages/dashboard/index.vue`)
- ✅ 移除 `rate_limit_multiplier` 欄位
- ✅ 更新會員等級卡片: 顯示 "Level X" 而非倍數
- ✅ 更新 `getMembershipIcon()`: 10 個等級圖示
- ✅ 更新 `.membership-card` CSS: 10 個等級漸變樣式
- ✅ 簡化 Rate Limit 顯示: 移除 base_limit 和 multiplier
- ✅ 更新 `selectedRateLimits`: 適配新 API 返回格式

### 測試

#### 測試腳本
- ✅ 創建 `test_member_levels_0_9.py`: 完整的 0-9 級測試
- ✅ 測試覆蓋:
  - 會員等級名稱驗證
  - 4 個 Rate Limit 驗證（每個等級）
  - 因子挖掘訪問控制（Level 0-2 拒絕）
  - GET /api/v1/membership/all-levels API

#### 測試結果
```
總測試數: 17
通過: 17 ✅
失敗: 0
```

**測試覆蓋**:
- ✅ Level 0 (註冊會員) - 所有限制正確 + 因子挖掘被拒絕
- ✅ Level 4 (VIP會員) - 所有限制正確
- ✅ GET /api/v1/membership/all-levels - 返回 10 個等級

## 📝 API 響應範例

### GET /api/v1/membership/me

**Level 0 (註冊會員)**:
```json
{
  "user_id": 37,
  "username": "free_user",
  "email": "free@example.com",
  "member_level": 0,
  "level_name": "註冊會員",
  "cash": "1500.75",
  "credit": "750.50",
  "rate_limits": {
    "回測執行": "10/hour",
    "策略建立": "10/hour",
    "資料查詢": "100/minute",
    "因子挖掘": "0/hour"
  }
}
```

**Level 4 (VIP會員)**:
```json
{
  "user_id": 38,
  "username": "paid_user",
  "member_level": 4,
  "level_name": "VIP會員",
  "rate_limits": {
    "回測執行": "50/hour",
    "策略建立": "50/hour",
    "資料查詢": "500/minute",
    "因子挖掘": "2/hour"
  }
}
```

### GET /api/v1/membership/all-levels

```json
[
  {
    "level": 0,
    "name": "註冊會員",
    "limits": {
      "回測執行": "10/hour",
      "策略建立": "10/hour",
      "資料查詢": "100/minute",
      "因子挖掘": "0/hour"
    },
    "description": "Level 0 - 註冊會員"
  },
  ...
  {
    "level": 9,
    "name": "創造者等級",
    "limits": {
      "回測執行": "3000/hour",
      "策略建立": "3000/hour",
      "資料查詢": "3000/minute",
      "因子挖掘": "3000/hour"
    },
    "description": "Level 9 - 創造者等級"
  }
]
```

### POST /api/v1/rdagent/factor-mining (Level 0-2)

**請求**:
```bash
curl -X POST /api/v1/rdagent/factor-mining \
  -H "Authorization: Bearer <level-0-token>" \
  -d '{"research_goal": "測試", ...}'
```

**響應 (HTTP 403)**:
```json
{
  "detail": "因子挖掘功能僅限 Level 3 以上會員使用。請升級會員等級以使用此功能。"
}
```

## 🔧 資料庫遷移

### 更新現有用戶等級

```sql
-- 查看當前用戶等級分佈
SELECT member_level, COUNT(*) FROM users GROUP BY member_level ORDER BY member_level;

-- 更新測試用戶（範例）
UPDATE users SET member_level = 0 WHERE username = 'free_user';
UPDATE users SET member_level = 4 WHERE username = 'paid_user';
UPDATE users SET member_level = 6 WHERE username = 'vip_user';

-- 驗證更新
SELECT id, username, member_level FROM users 
WHERE username IN ('free_user', 'paid_user', 'vip_user') 
ORDER BY member_level;
```

## 📁 修改檔案清單

### 後端
- ✅ `backend/app/core/member_limits.py` - 完全重寫
- ✅ `backend/app/core/rate_limit.py` - 移除舊函數
- ✅ `backend/app/api/v1/membership.py` - 完全重寫
- ✅ `backend/app/api/v1/rdagent.py` - 更新檢查邏輯

### 前端
- ✅ `frontend/pages/admin/index.vue` - 更新下拉選單和CSS
- ✅ `frontend/pages/dashboard/index.vue` - 移除倍數顯示，更新樣式

### 測試
- ✅ `test_member_levels_0_9.py` - 新測試腳本
- 📌 `test_factor_mining_limits.py` - 舊測試（可保留參考）
- 📌 `test_membership_api.sh` - 舊測試（可刪除）

### 文檔
- ✅ `MEMBER_LEVELS_0_9_MIGRATION.md` - 本文檔
- 📌 `FACTOR_MINING_LIMITS.md` - 舊文檔（已過時）

## 🚀 部署檢查清單

- [x] 後端配置更新
- [x] API 端點修改
- [x] 前端顯示更新
- [x] CSS 樣式更新
- [x] 測試腳本創建
- [x] 所有測試通過 (17/17)
- [x] 後端服務重啟
- [x] 文檔撰寫完成
- [ ] 生產環境驗證
- [ ] 用戶通知（等級變更說明）

## ⚠️ 注意事項

### 已知限制
1. **現有用戶**: 需要手動或腳本更新 `member_level` 欄位
2. **舊API客戶端**: 若有外部應用依賴舊 API 格式，需要更新
3. **速率限制**: 使用 Redis 持久化，重啟不會重置

### 向後兼容性
- ❌ **不兼容**: 移除了 `rate_limit_multiplier` 欄位
- ❌ **不兼容**: `/limits` 端點返回格式改變
- ✅ **兼容**: `member_level` 欄位仍存在（數值變更）

### 遷移建議
1. 通知用戶會員等級系統更新
2. 提供等級對照表（舊 Level 3 → 新 Level 4 VIP）
3. 檢查前端應用是否有緩存的會員資訊
4. 監控 API 錯誤率（尤其是因子挖掘 403 錯誤）

## 📚 相關文檔

- [CLAUDE.md](CLAUDE.md#速率限制) - 系統架構說明
- [backend/app/core/member_limits.py](backend/app/core/member_limits.py) - 限制配置源碼
- [backend/app/api/v1/membership.py](backend/app/api/v1/membership.py) - 會員 API 源碼

---

**實作日期**: 2025-12-11  
**版本**: v2.0.0  
**狀態**: ✅ 已完成並通過測試  
**測試覆蓋**: 17/17 通過
