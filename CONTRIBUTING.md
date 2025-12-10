# 貢獻指南

> 感謝您對 QuantLab 的興趣！我們歡迎所有形式的貢獻。

---

## 📋 目錄

- [行為準則](#行為準則)
- [我能貢獻什麼？](#我能貢獻什麼)
- [開發流程](#開發流程)
- [代碼規範](#代碼規範)
- [提交規範](#提交規範)
- [測試要求](#測試要求)
- [文檔撰寫](#文檔撰寫)
- [問題回報](#問題回報)

---

## 行為準則

### 我們的承諾
我們致力於為所有人提供一個友善、安全和包容的環境。

### 期望行為
- 使用友善和包容的語言
- 尊重不同的觀點和經驗
- 優雅地接受建設性批評
- 關注對社群最有利的事情
- 對其他社群成員表示同理心

### 不可接受的行為
- 使用性化的語言或圖像
- 人身攻擊或政治攻擊
- 公開或私下騷擾
- 未經許可發布他人私人信息
- 其他在專業環境中不當的行為

---

## 我能貢獻什麼？

### 🐛 Bug 修復
發現 bug？歡迎提交修復！

### ✨ 新功能
有好主意？先開 Issue 討論，再提交 PR。

### 📝 文檔改進
文檔永遠不嫌完善！

### 🧪 測試增強
提升測試覆蓋率，讓專案更穩定。

### 🎨 UI/UX 改進
讓介面更友善、更美觀。

### 🌍 翻譯
幫助 QuantLab 支援更多語言。

---

## 開發流程

### 1. Fork 專案

點擊 GitHub 頁面右上角的 "Fork" 按鈕。

### 2. Clone 到本地

```bash
git clone https://github.com/YOUR_USERNAME/quantlab.git
cd quantlab
```

### 3. 添加上游倉庫

```bash
git remote add upstream https://github.com/original/quantlab.git
```

### 4. 創建功能分支

```bash
git checkout -b feature/amazing-feature
```

**分支命名規範**:
- `feature/xxx` - 新功能
- `fix/xxx` - Bug 修復
- `docs/xxx` - 文檔更新
- `test/xxx` - 測試相關
- `refactor/xxx` - 重構
- `perf/xxx` - 性能優化

### 5. 設置開發環境

```bash
# 複製環境變數範例
cp .env.example .env

# 修改 .env（添加必要的 API Keys）
nano .env

# 啟動開發環境
docker compose up -d
```

### 6. 進行開發

遵循 [代碼規範](#代碼規範)。

### 7. 運行測試

```bash
# 後端測試
docker compose exec backend pytest

# 前端測試（待實施）
cd frontend && npm run test

# Linting
docker compose exec backend black --check app/
docker compose exec backend flake8 app/
```

### 8. 提交變更

```bash
git add .
git commit -m "feat(strategies): add momentum strategy template"
```

遵循 [提交規範](#提交規範)。

### 9. 同步上游更新

```bash
git fetch upstream
git rebase upstream/main
```

### 10. 推送分支

```bash
git push origin feature/amazing-feature
```

### 11. 提交 Pull Request

1. 訪問您的 Fork 頁面
2. 點擊 "New Pull Request"
3. 填寫 PR 模板
4. 等待 Code Review

---

## 代碼規範

### Python (後端)

#### 格式化
使用 **Black** (line length: 88):
```bash
black app/
```

#### Linting
使用 **Flake8**:
```bash
flake8 app/ --max-line-length=88 --extend-ignore=E203
```

#### 類型檢查
使用 **mypy**:
```bash
mypy app/ --ignore-missing-imports
```

#### 風格指南
- 遵循 [PEP 8](https://pep8.org/)
- 使用類型提示（Type Hints）
- 函數名使用 `snake_case`
- 類名使用 `PascalCase`
- 常數使用 `UPPER_CASE`

**範例**:
```python
from typing import List, Optional
from fastapi import HTTPException

def get_strategies(
    user_id: int,
    status: Optional[str] = None,
    limit: int = 10
) -> List[Strategy]:
    """
    獲取用戶策略列表

    Args:
        user_id: 用戶 ID
        status: 策略狀態過濾（可選）
        limit: 返回數量限制

    Returns:
        策略列表

    Raises:
        HTTPException: 用戶不存在或無權限
    """
    # 實作邏輯...
    pass
```

#### 文檔字串
使用 **Google Style**:
```python
def function(arg1: str, arg2: int) -> bool:
    """Summary line.

    Extended description of function.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        Description of return value

    Raises:
        ValueError: If arg1 is empty
    """
    pass
```

---

### TypeScript/Vue (前端)

#### 格式化
使用 **ESLint** + **Prettier**:
```bash
npm run lint
npm run lint:fix
```

#### 風格指南
- 遵循 [Vue 3 Style Guide](https://vuejs.org/style-guide/)
- 使用 Composition API
- 優先使用 `<script setup>`
- 組件名使用 PascalCase
- Props 使用 camelCase

**範例**:
```vue
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

// Props
interface Props {
  strategyId?: string
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false
})

// Emits
const emit = defineEmits<{
  save: [strategy: Strategy]
  cancel: []
}>()

// State
const loading = ref(false)
const strategy = ref<Strategy | null>(null)

// Computed
const isValid = computed(() => {
  return strategy.value?.name && strategy.value?.code
})

// Methods
const handleSave = () => {
  if (!isValid.value) return
  emit('save', strategy.value!)
}

// Lifecycle
onMounted(() => {
  loadStrategy()
})
</script>
```

---

## 提交規範

### Commit Message 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type（必填）
- `feat`: 新功能
- `fix`: Bug 修復
- `docs`: 文檔更新
- `style`: 代碼格式（不影響功能）
- `refactor`: 重構
- `test`: 測試相關
- `chore`: 構建/工具配置
- `perf`: 性能優化

### Scope（選填）
- `backend`: 後端
- `frontend`: 前端
- `api`: API 端點
- `db`: 數據庫
- `strategies`: 策略相關
- `backtest`: 回測相關
- `docs`: 文檔
- `ci`: CI/CD

### Subject（必填）
- 簡短描述（不超過 50 字）
- 使用現在式：`add` 而非 `added`
- 不要大寫首字母
- 不要句號結尾

### Body（選填）
- 詳細描述變更內容
- 說明為什麼做這個變更
- 影響範圍

### Footer（選填）
- 關閉 Issue: `Closes #123`
- 破壞性變更: `BREAKING CHANGE: xxx`

### 範例

**簡單提交**:
```
feat(strategies): add MACD strategy template
```

**詳細提交**:
```
feat(api): add factor evaluation endpoint

Implement new API endpoint for evaluating quantitative factors.
Includes calculation of IC, ICIR, and Sharpe Ratio.

Closes #42
```

**破壞性變更**:
```
refactor(db)!: change strategy table schema

Rename 'params' column to 'parameters' for consistency.

BREAKING CHANGE: Existing strategies need migration
Run: alembic upgrade head
```

---

## 測試要求

### 測試覆蓋率
- 新功能必須包含測試
- 目標覆蓋率：70%+
- 關鍵路徑：100%

### 後端測試
使用 **pytest**:
```python
# tests/test_strategies.py
import pytest
from fastapi.testclient import TestClient

def test_create_strategy(client: TestClient, auth_headers):
    """測試策略創建"""
    response = client.post(
        "/api/v1/strategies/",
        json={
            "name": "Test Strategy",
            "code": "# Test code",
            "status": "draft"
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test Strategy"
```

### 前端測試
使用 **Vitest** + **@vue/test-utils**:
```typescript
// components/__tests__/StrategyEditor.spec.ts
import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import StrategyEditor from '../StrategyEditor.vue'

describe('StrategyEditor', () => {
  it('renders properly', () => {
    const wrapper = mount(StrategyEditor)
    expect(wrapper.find('.editor').exists()).toBe(true)
  })

  it('emits save event', async () => {
    const wrapper = mount(StrategyEditor)
    await wrapper.find('button.save').trigger('click')
    expect(wrapper.emitted('save')).toBeTruthy()
  })
})
```

---

## 文檔撰寫

### Markdown 格式
- 使用清晰的標題層級
- 添加目錄（TOC）
- 包含代碼範例
- 添加截圖（如適用）

### 文檔位置
- 數據庫相關: `Document/DATABASE_*.md`
- 使用指南: `Document/*_GUIDE.md`
- 技術文檔: `docs/*.md`
- API 文檔: OpenAPI 規範（自動生成）

### 文檔檢查清單
- [ ] 標題清晰
- [ ] 目錄完整
- [ ] 代碼範例正確
- [ ] 截圖清晰
- [ ] 語法正確
- [ ] 鏈接有效

---

## 問題回報

### Bug Report

**使用 GitHub Issues**，包含：

1. **環境信息**
   - OS: (e.g., Ubuntu 22.04)
   - Docker 版本
   - Python 版本
   - Node.js 版本

2. **重現步驟**
   ```
   1. 訪問 /strategies
   2. 點擊「新增策略」
   3. 填寫表單
   4. 點擊「儲存」
   ```

3. **預期行為**
   策略應該被成功創建

4. **實際行為**
   返回 500 錯誤

5. **錯誤日誌**
   ```
   docker compose logs backend
   ```

6. **截圖**（如適用）

### Feature Request

1. **功能描述**
   簡要描述想要的功能

2. **使用場景**
   為什麼需要這個功能？

3. **建議實作**
   如何實作（可選）

4. **替代方案**
   有其他解決方法嗎？

---

## Code Review 流程

### 提交者
1. 自我檢查 PR Checklist
2. 確保 CI 通過
3. 回應 Review 意見
4. 及時更新 PR

### 審查者
1. 檢查代碼質量
2. 運行測試
3. 提供建設性反饋
4. 及時 Review（24 小時內）

### PR Checklist

**提交前檢查**:
- [ ] 代碼遵循規範
- [ ] 包含測試
- [ ] 測試通過
- [ ] 文檔已更新
- [ ] Commit 訊息規範
- [ ] 無衝突

**合併前檢查**:
- [ ] 至少 1 個 Approve
- [ ] CI 全部通過
- [ ] 無衝突
- [ ] Squash commits（可選）

---

## 社群

### 溝通渠道
- 💬 GitHub Discussions: 一般討論
- 🐛 GitHub Issues: Bug 回報、功能請求
- 📧 Email: security@quantlab.dev（安全問題）

### 響應時間
- Issue: 48 小時內
- PR: 24-48 小時內
- 安全問題: 24 小時內

---

## 授權

提交代碼即表示您同意您的貢獻以專案的開源授權（MIT License）發布。

---

## 感謝

感謝您的貢獻！每個 PR 都讓 QuantLab 變得更好。🎉

---

**有問題？**
- 📖 閱讀 [CLAUDE.md](CLAUDE.md)
- 💬 在 GitHub Discussions 提問
- 📧 聯繫維護者
