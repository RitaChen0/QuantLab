# QuantLab 開發指南

完整的開發規範、工作流程與最佳實踐。

## 目錄

- [開發環境](#開發環境)
- [架構設計](#架構設計)
- [開發工作流](#開發工作流)
- [代碼規範](#代碼規範)
- [測試指南](#測試指南)
- [Git 工作流](#git-工作流)
- [安全注意事項](#安全注意事項)

## 開發環境

### 系統需求

- Docker & Docker Compose
- Node.js 18+（本地開發）
- Python 3.11+（本地開發）
- Git

### 環境變數配置

```bash
# 複製範例文件
cp .env.example .env

# 必填變數
DATABASE_URL=postgresql://quantlab:quantlab2025@postgres:5432/quantlab
REDIS_URL=redis://redis:6379/0
JWT_SECRET=<使用強隨機字串，至少 32 字元>
FINLAB_API_TOKEN=<從 https://ai.finlab.tw/ 取得>
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# 選填變數（AI 功能）
OPENAI_API_KEY=<RD-Agent 因子挖掘>
ANTHROPIC_API_KEY=<Claude API>
SHIOAJI_API_KEY=<永豐證券>
FUGLE_API_KEY=<富果證券>

# CORS 配置（外部訪問）
ALLOWED_ORIGINS=http://localhost:3000,http://192.168.1.100:3000
```

### 本地開發設置

**後端開發**：
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**前端開發**：
```bash
cd frontend
npm install
npm run dev
```

## 架構設計

### 後端四層架構

```
app/
├── api/v1/          # API 路由層
│   ├── auth.py      # 認證相關 API
│   ├── strategies.py # 策略管理 API
│   ├── backtest.py  # 回測管理 API
│   └── ...
├── services/        # 業務邏輯層
│   ├── strategy_service.py
│   ├── backtest_service.py
│   ├── qlib_data_adapter.py
│   └── ...
├── repositories/    # 數據訪問層
│   ├── strategy.py
│   ├── backtest.py
│   └── ...
├── models/          # ORM 模型
├── schemas/         # Pydantic Schemas
├── core/            # 核心配置
├── db/              # 數據庫會話
├── utils/           # 工具模組
└── tasks/           # Celery 任務
```

### 層級職責

**API 層（`app/api/v1/`）**：
- 處理 HTTP 請求/響應
- 依賴注入（database session, current user）
- 調用 Service 層方法
- 統一錯誤處理
- 結構化日誌記錄
- **不包含業務邏輯**

**Service 層（`app/services/`）**：
- 核心業務邏輯實作
- 數據驗證與轉換
- 配額檢查與限制
- 調用 Repository 層方法
- 拋出 HTTPException 處理錯誤
- **不直接操作 SQLAlchemy 模型**

**Repository 層（`app/repositories/`）**：
- 資料庫 CRUD 操作
- 查詢建構與執行
- 事務管理（commit/rollback）
- 返回 ORM 模型物件
- **不包含業務邏輯**

### 前端組件架構

```
frontend/
├── pages/           # 頁面組件
│   ├── index.vue    # 首頁
│   ├── dashboard/   # 儀表板
│   ├── strategies/  # 策略管理
│   ├── backtest/    # 回測管理
│   └── ...
├── components/      # 通用組件
│   ├── StrategyTemplates.vue        # Backtrader 範本
│   ├── QlibStrategyTemplates.vue    # Qlib 範本
│   ├── FactorStrategyTemplates.vue  # RD-Agent 範本
│   └── ...
├── stores/          # Pinia 狀態管理
├── composables/     # 組合式函數
└── assets/          # 靜態資源
```

## 開發工作流

### 添加新 API 端點

**步驟 1：定義 Schema**
```python
# backend/app/schemas/resource.py
from pydantic import BaseModel

class ResourceCreate(BaseModel):
    name: str
    description: str | None = None

class ResourceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

class ResourceResponse(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime
```

**步驟 2：創建 Repository**
```python
# backend/app/repositories/resource.py
from sqlalchemy.orm import Session
from app.models.resource import Resource
from app.schemas.resource import ResourceCreate

class ResourceRepository:
    def create(self, db: Session, user_id: int, data: ResourceCreate) -> Resource:
        resource = Resource(user_id=user_id, **data.model_dump())
        db.add(resource)
        db.commit()
        db.refresh(resource)
        return resource

    def get_by_id(self, db: Session, resource_id: int) -> Resource | None:
        return db.query(Resource).filter(Resource.id == resource_id).first()
```

**步驟 3：實作 Service**
```python
# backend/app/services/resource_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.repositories.resource import ResourceRepository
from app.schemas.resource import ResourceCreate

class ResourceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ResourceRepository()

    def create_resource(self, user_id: int, data: ResourceCreate):
        # 配額檢查
        count = self.repo.count_by_user(self.db, user_id)
        if count >= 50:
            raise HTTPException(status_code=429, detail="配額已滿")

        # 調用 Repository
        return self.repo.create(self.db, user_id, data)
```

**步驟 4：創建 API 端點**
```python
# backend/app/api/v1/resources.py
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user, get_db
from app.services.resource_service import ResourceService
from app.schemas.resource import ResourceCreate, ResourceResponse
from app.core.rate_limit import limiter, RateLimits
from app.utils.logging import api_log

router = APIRouter(prefix="/resources", tags=["resources"])

@router.post("/", response_model=ResourceResponse)
@limiter.limit(RateLimits.OPERATION_CREATE)
async def create_resource(
    request: Request,
    data: ResourceCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ResourceService(db)
    resource = service.create_resource(current_user.id, data)
    api_log.log_operation("create", "resource", resource.id, current_user.id, success=True)
    return resource
```

**步驟 5：註冊路由**
```python
# backend/app/api/v1/__init__.py
from app.api.v1 import resources

# backend/app/main.py
from app.api.v1 import resources
app.include_router(resources.router, prefix="/api/v1")
```

### 添加新數據庫模型

**步驟 1：創建模型**
```python
# backend/app/models/resource.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime

class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="resources")
```

**步驟 2：在 base.py 導入**
```python
# backend/app/db/base.py
from app.db.base import Base
from app.models.user import User
from app.models.resource import Resource  # 新增
```

**步驟 3：創建遷移**
```bash
docker compose exec backend alembic revision --autogenerate -m "add resources table"
```

**步驟 4：檢查遷移檔案**
```bash
# 檢查生成的遷移檔案
cat backend/alembic/versions/最新版本_add_resources_table.py

# 確認 upgrade() 和 downgrade() 函數正確
```

**步驟 5：執行遷移**
```bash
docker compose exec backend alembic upgrade head
```

### 添加新 Celery 任務

**步驟 1：創建任務**
```python
# backend/app/tasks/my_tasks.py
from celery import Task
from app.core.celery_app import celery_app
from loguru import logger

@celery_app.task(bind=True, name="app.tasks.my_new_task")
def my_new_task(self: Task) -> dict:
    """任務說明"""
    try:
        logger.info("開始執行任務")
        # 業務邏輯
        result = do_something()
        logger.info("任務執行成功")
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"任務失敗: {str(e)}")
        raise self.retry(exc=e, countdown=300, max_retries=3)
```

**步驟 2：導出任務**
```python
# backend/app/tasks/__init__.py
from app.tasks.my_tasks import my_new_task

__all__ = [
    "my_new_task",
    # ... 其他任務
]
```

**步驟 3：添加定時任務（可選）**
```python
# backend/app/core/celery_app.py
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "my-new-task-daily": {
        "task": "app.tasks.my_new_task",
        "schedule": crontab(hour=10, minute=0),
    },
    # ... 其他任務
}
```

**步驟 4：重啟服務**
```bash
# 清除 cache
docker compose exec celery-worker find /app -name __pycache__ -type d -exec rm -rf {} +

# 重啟
docker compose restart celery-worker celery-beat

# 驗證
docker compose exec backend celery -A app.core.celery_app inspect registered | grep my_new_task
```

## 代碼規範

### Python 代碼風格

使用 **Black** 和 **Flake8**：

```bash
# 自動格式化
docker compose exec backend black app/

# 檢查格式
docker compose exec backend black --check app/

# Linting
docker compose exec backend flake8 app/ --max-line-length=88

# 類型檢查
docker compose exec backend mypy app/
```

**代碼規範**：
- 使用 Black 預設配置（88 字元行寬）
- 使用 type hints
- 函數和類添加 docstrings
- 避免使用 `from module import *`
- 使用 pathlib 而非 os.path

### TypeScript/Vue 代碼風格

使用 **ESLint**：

```bash
# Linting
docker compose exec frontend npm run lint

# 自動修復
docker compose exec frontend npm run lint:fix
```

**代碼規範**：
- 使用 TypeScript 嚴格模式（目前已關閉，逐步遷移）
- 組件名稱使用 PascalCase
- 使用 Composition API
- Props 和 Emits 明確定義類型
- 避免使用 `any` 類型

### Vue 模板注意事項

**Python f-string 轉義**：
```vue
<script setup lang="ts">
const code = `
# ❌ 錯誤：Vue 編譯器會解析 ${變數}
print(f'價格 ${order.price:.2f}')

# ✅ 正確：使用單反斜線轉義
print(f'價格 \${order.price:.2f}')
`
</script>
```

**SVG 尺寸設定**：
```vue
<style scoped>
svg.w-4 {
  width: 1rem !important;
  height: 1rem !important;
  flex-shrink: 0;
}
</style>
```

## 測試指南

### 後端測試

**運行測試**：
```bash
# 所有測試
docker compose exec backend pytest

# 特定測試檔案
docker compose exec backend pytest tests/test_auth.py

# 特定測試函數
docker compose exec backend pytest tests/test_auth.py::test_register

# 顯示覆蓋率
docker compose exec backend pytest --cov=app
```

**測試範例**：
```python
# backend/tests/test_resource.py
import pytest
from fastapi.testclient import TestClient

def test_create_resource(client: TestClient, auth_headers: dict):
    response = client.post(
        "/api/v1/resources/",
        json={"name": "Test Resource"},
        headers=auth_headers
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test Resource"
```

### 前端測試

**運行測試**（需配置）：
```bash
# 單元測試
docker compose exec frontend npm run test

# E2E 測試
docker compose exec frontend npm run test:e2e
```

## Git 工作流

### Commit Message 規範

```
<type>(<scope>): <subject>

<body>

<footer>
```

**類型（type）**：
- `feat`: 新功能
- `fix`: Bug 修復
- `docs`: 文檔更新
- `style`: 代碼格式（不影響功能）
- `refactor`: 重構
- `test`: 測試相關
- `chore`: 構建/工具配置

**範例**：
```
feat(api): add resource management endpoints

- Implement CRUD operations for resources
- Add quota checking (max 50 per user)
- Add rate limiting (10 requests/hour)

Closes #123
```

### 分支策略

```
master (main)       # 生產環境
  └── develop       # 開發環境
      ├── feature/user-profile    # 功能分支
      ├── feature/export-csv      # 功能分支
      └── fix/login-error         # 修復分支
```

**工作流程**：
```bash
# 1. 從 develop 創建功能分支
git checkout develop
git pull origin develop
git checkout -b feature/my-feature

# 2. 開發並提交
git add .
git commit -m "feat(module): add new feature"

# 3. 推送到遠端
git push origin feature/my-feature

# 4. 創建 Pull Request 到 develop

# 5. Code Review 通過後合併
```

## 安全注意事項

### 環境變數

```bash
# ✅ 正確：使用環境變數
JWT_SECRET=<強隨機字串>

# ❌ 錯誤：寫死在代碼中
JWT_SECRET = "my-secret-key"  # 不要這樣做！
```

### 密碼處理

```python
# ✅ 正確：使用 bcrypt
from app.core.security import get_password_hash, verify_password

hashed = get_password_hash("password123")
verified = verify_password("password123", hashed)

# ❌ 錯誤：明文存儲
user.password = "password123"  # 不要這樣做！
```

### SQL 注入防護

```python
# ✅ 正確：使用參數化查詢
db.execute(text("SELECT * FROM users WHERE id = :id"), {"id": user_id})

# ❌ 錯誤：字串拼接
db.execute(f"SELECT * FROM users WHERE id = {user_id}")  # 不要這樣做！
```

### 策略代碼驗證

系統已實作 AST 解析驗證，自動檢查：
- 白名單模組（backtrader, pandas, numpy 等）
- 黑名單危險函數（eval, exec, open 等）
- 危險屬性訪問（__globals__, __code__ 等）

### 日誌記錄

```python
# ✅ 正確：不記錄敏感信息
logger.info(f"User {user_id} logged in")

# ❌ 錯誤：記錄密碼或 token
logger.info(f"User logged in with password {password}")  # 不要這樣做！
```

## 效能最佳實踐

### 資料庫查詢

```python
# ✅ 正確：使用 eager loading
strategies = db.query(Strategy).options(
    joinedload(Strategy.user)
).all()

# ❌ 錯誤：N+1 查詢
strategies = db.query(Strategy).all()
for strategy in strategies:
    print(strategy.user.username)  # 每次都查詢資料庫
```

### 快取使用

```python
# 使用 Redis 快取
from app.utils.cache import cached

@cached(ttl=3600, key_prefix="stock_list")
def get_stock_list():
    # 昂貴的 API 調用
    return finlab_client.get_stock_list()
```

### 前端效能

- 使用 `lazy` 載入大型組件
- 避免在 `v-for` 中使用複雜計算
- 使用 `computed` 緩存計算結果
- 圖片使用適當大小和格式

## 相關文檔

- [操作指南](OPERATIONS_GUIDE.md)
- [資料庫架構報告](DATABASE_SCHEMA_REPORT.md)
- [資料庫變更檢查清單](DATABASE_CHANGE_CHECKLIST.md)
