# 專案結構索引

快速定位專案中的關鍵文件與目錄職責。

## 🎯 快速查找

| 我想... | 查看這個文件/目錄 |
|---------|------------------|
| 添加新的 API 端點 | `backend/app/api/v1/` |
| 修改業務邏輯 | `backend/app/services/` |
| 操作資料庫 | `backend/app/repositories/` |
| 修改資料表結構 | `backend/app/models/` + `backend/alembic/versions/` |
| 添加新頁面 | `frontend/pages/` |
| 創建通用組件 | `frontend/components/` |
| 添加 Celery 任務 | `backend/app/tasks/` |
| 修改環境變數 | `.env` + `backend/app/core/config.py` |
| 查看 API 文檔 | http://localhost:8000/docs |
| 了解資料庫架構 | `Document/DATABASE_SCHEMA_REPORT.md` |

## 📁 目錄結構與職責

```
QuantLab/
├── backend/                    # 後端應用（FastAPI）
│   ├── app/
│   │   ├── api/v1/            # API 路由層
│   │   │   ├── auth.py        # 認證 API（登入、註冊、Token）
│   │   │   ├── users.py       # 用戶管理 API
│   │   │   ├── strategies.py  # 策略管理 API（CRUD、驗證、複製）
│   │   │   ├── backtest.py    # 回測管理 API（執行、結果查詢）
│   │   │   ├── data.py        # 股票數據 API（價格、搜尋）
│   │   │   ├── industry.py    # 產業分析 API（分類、指標）
│   │   │   ├── rdagent.py     # RD-Agent API（因子挖掘、任務管理）
│   │   │   └── admin.py       # 後台管理 API（用戶、系統、日誌）
│   │   ├── services/          # 業務邏輯層
│   │   │   ├── user_service.py           # 用戶業務邏輯
│   │   │   ├── strategy_service.py       # 策略業務邏輯（AST 驗證）
│   │   │   ├── backtest_service.py       # 回測業務邏輯
│   │   │   ├── industry_service.py       # 產業分析邏輯（聚合指標）
│   │   │   ├── rdagent_service.py        # RD-Agent 配置與管理
│   │   │   ├── finlab_client.py          # FinLab API 客戶端
│   │   │   ├── qlib_data_adapter.py      # Qlib 數據適配器（Fallback）
│   │   │   └── qlib_backtest_engine.py   # Qlib 回測引擎
│   │   ├── repositories/      # 數據訪問層
│   │   │   ├── user.py        # 用戶 CRUD
│   │   │   ├── strategy.py    # 策略 CRUD
│   │   │   ├── backtest.py    # 回測 CRUD
│   │   │   └── industry.py    # 產業分類 CRUD
│   │   ├── models/            # ORM 模型（SQLAlchemy）
│   │   │   ├── user.py        # 用戶表模型
│   │   │   ├── strategy.py    # 策略表模型
│   │   │   ├── backtest.py    # 回測、結果、交易表模型
│   │   │   ├── industry.py    # 產業分類表模型
│   │   │   ├── stock_industry.py         # 股票-產業映射表
│   │   │   ├── fundamental_data.py       # 基本面資料表
│   │   │   └── industry_metrics_cache.py # 產業指標快取表
│   │   ├── schemas/           # Pydantic Schemas（數據驗證）
│   │   │   ├── user.py        # 用戶 Schema
│   │   │   ├── strategy.py    # 策略 Schema
│   │   │   ├── backtest.py    # 回測 Schema
│   │   │   └── ...
│   │   ├── core/              # 核心配置
│   │   │   ├── config.py      # 環境變數配置（Pydantic Settings）
│   │   │   ├── security.py    # JWT、密碼加密
│   │   │   ├── rate_limit.py  # 速率限制配置
│   │   │   ├── celery_app.py  # Celery 應用配置
│   │   │   └── qlib_config.py # Qlib 初始化配置
│   │   ├── db/                # 數據庫會話管理
│   │   │   ├── base.py        # Base 模型（**所有模型必須在此導入**）
│   │   │   └── session.py     # 數據庫會話工廠
│   │   ├── utils/             # 工具模組
│   │   │   ├── cache.py       # Redis 快取工具
│   │   │   └── logging.py     # 結構化日誌工具
│   │   ├── tasks/             # Celery 任務
│   │   │   ├── __init__.py    # **任務導出（新任務必須在此導出）**
│   │   │   ├── stock_data.py  # 股票數據同步任務
│   │   │   ├── qlib_tasks.py  # Qlib 相關任務
│   │   │   └── rdagent_tasks.py # RD-Agent 任務
│   │   └── main.py            # FastAPI 應用入口
│   ├── alembic/               # 資料庫遷移
│   │   ├── env.py             # Alembic 環境配置
│   │   └── versions/          # 遷移腳本目錄
│   ├── scripts/               # 後端腳本
│   │   ├── export_to_qlib_v2.py # Qlib 數據同步腳本
│   │   └── test_qlib_engine.py  # Qlib 引擎測試
│   ├── tests/                 # 單元測試
│   ├── alembic.ini            # Alembic 配置檔
│   ├── requirements.txt       # Python 依賴
│   └── start.sh               # 啟動腳本
│
├── frontend/                  # 前端應用（Nuxt.js）
│   ├── pages/                 # 頁面組件（自動路由）
│   │   ├── index.vue          # 首頁（/）
│   │   ├── login.vue          # 登入頁（/login）
│   │   ├── register.vue       # 註冊頁（/register）
│   │   ├── docs.vue           # API 文檔頁（/docs）
│   │   ├── dashboard/
│   │   │   └── index.vue      # 儀表板（/dashboard）
│   │   ├── strategies/
│   │   │   ├── index.vue      # 策略列表（/strategies）
│   │   │   └── [id]/
│   │   │       ├── index.vue  # 策略詳情（/strategies/:id）
│   │   │       └── edit.vue   # 策略編輯（/strategies/:id/edit）
│   │   ├── backtest/
│   │   │   ├── index.vue      # 回測列表（/backtest）
│   │   │   └── [id].vue       # 回測詳情（/backtest/:id）
│   │   ├── data/
│   │   │   └── index.vue      # 股票數據瀏覽（/data）
│   │   ├── industry/
│   │   │   └── index.vue      # 產業分析（/industry）
│   │   ├── rdagent/
│   │   │   └── index.vue      # RD-Agent 因子挖掘（/rdagent）
│   │   └── admin/
│   │       └── index.vue      # 後台管理（/admin）
│   ├── components/            # 通用組件
│   │   ├── StrategyTemplates.vue        # Backtrader 策略範本（20 個）
│   │   ├── QlibStrategyTemplates.vue    # Qlib ML 策略範本（9 個）
│   │   └── FactorStrategyTemplates.vue  # RD-Agent 因子範本
│   ├── stores/                # Pinia 狀態管理
│   │   ├── auth.ts            # 認證狀態（token、用戶資料）
│   │   └── ...
│   ├── composables/           # 組合式函數
│   ├── assets/                # 靜態資源
│   ├── public/                # 公開資源
│   ├── nuxt.config.ts         # Nuxt 配置檔
│   ├── package.json           # Node 依賴
│   └── tsconfig.json          # TypeScript 配置
│
├── scripts/                   # 運維腳本
│   ├── sync-qlib-smart.sh              # Qlib 智慧同步
│   ├── import_all_shioaji.sh           # Shioaji 數據匯入
│   ├── monitor_shioaji_import.sh       # 匯入進度監控
│   ├── backup_database.sh              # 資料庫備份
│   ├── reset-rate-limit.sh             # 速率限制重置
│   ├── quick-clean.sh                  # 前端緩存清理
│   └── monitor_celery.sh               # Celery 監控
│
├── Document/                  # 文檔目錄
│   ├── OPERATIONS_GUIDE.md             # 完整操作手冊
│   ├── QLIB_SYNC_GUIDE.md              # Qlib 同步指南
│   ├── CELERY_TASKS_GUIDE.md           # Celery 任務管理
│   ├── DEVELOPMENT_GUIDE.md            # 開發規範與工作流
│   ├── DATABASE_SCHEMA_REPORT.md       # 資料庫架構報告（16 表）
│   ├── DATABASE_CHANGE_CHECKLIST.md    # 資料庫變更檢查清單（56 項）
│   ├── DATABASE_ER_DIAGRAM.md          # ER 圖視覺化
│   └── DATABASE_MAINTENANCE.md         # 備份與維護指南
│
├── ShioajiData/               # Shioaji 數據存放目錄
│   └── shioaji-stock/         # 1,692 個股票 CSV 檔案
│
├── .env                       # 環境變數配置（**不提交到 Git**）
├── .env.example               # 環境變數範例
├── docker-compose.yml         # Docker 編排配置
├── README.md                  # 快速開始與核心命令
├── CLAUDE.md                  # 專案概述與架構說明
└── PROJECT_STRUCTURE.md       # 專案結構索引（本文件）
```

## 🔑 關鍵文件說明

### 配置文件

| 文件 | 職責 | 何時修改 |
|------|------|---------|
| `.env` | 環境變數配置 | 首次設置、添加新服務 |
| `backend/app/core/config.py` | 環境變數定義 | 添加新的環境變數 |
| `docker-compose.yml` | Docker 服務編排 | 添加新容器、修改資源限制 |
| `backend/requirements.txt` | Python 依賴 | 添加新的 Python 套件 |
| `frontend/package.json` | Node 依賴 | 添加新的 npm 套件 |
| `backend/alembic.ini` | Alembic 配置 | 修改資料庫連接方式 |
| `frontend/nuxt.config.ts` | Nuxt 配置 | 修改路由、模組、插件 |

### 重要文件（必須了解）

| 文件 | 為何重要 |
|------|---------|
| `backend/app/db/base.py` | **所有 ORM 模型必須在此導入**，否則 Alembic 無法檢測 |
| `backend/app/tasks/__init__.py` | **所有 Celery 任務必須在此導出**，否則無法註冊 |
| `backend/app/api/dependencies.py` | 依賴注入定義（如 `get_current_user`） |
| `backend/app/main.py` | FastAPI 應用入口，路由註冊位置 |
| `backend/start.sh` | 後端啟動流程（遷移 → 啟動 Uvicorn） |
| `frontend/nuxt.config.ts` | 前端配置中心（API URL、模組、插件） |

## 📝 文件命名規範

### 後端

- **API 路由**：`backend/app/api/v1/{resource}.py`（單數名詞）
- **Service**：`backend/app/services/{resource}_service.py`
- **Repository**：`backend/app/repositories/{resource}.py`
- **Model**：`backend/app/models/{resource}.py`
- **Schema**：`backend/app/schemas/{resource}.py`
- **Task**：`backend/app/tasks/{domain}_tasks.py`

### 前端

- **頁面**：`frontend/pages/{route}/index.vue`
- **動態路由**：`frontend/pages/{route}/[id].vue`
- **組件**：`frontend/components/{ComponentName}.vue`（PascalCase）
- **Store**：`frontend/stores/{domain}.ts`
- **Composable**：`frontend/composables/use{Feature}.ts`

## 🔍 常見開發場景

### 場景 1：添加新的 API 端點

**修改文件順序**：
1. `backend/app/schemas/{resource}.py` - 定義 Schema
2. `backend/app/repositories/{resource}.py` - 創建 Repository
3. `backend/app/services/{resource}_service.py` - 實作 Service
4. `backend/app/api/v1/{resource}.py` - 創建 API 端點
5. `backend/app/main.py` - 註冊路由

### 場景 2：添加新的資料表

**修改文件順序**：
1. `backend/app/models/{table}.py` - 創建 ORM 模型
2. `backend/app/db/base.py` - **導入新模型**
3. 執行遷移：`alembic revision --autogenerate -m "add {table}"`
4. 檢查遷移檔：`backend/alembic/versions/{hash}_add_{table}.py`
5. 執行遷移：`alembic upgrade head`

### 場景 3：添加新頁面

**修改文件順序**：
1. `frontend/pages/{route}/index.vue` - 創建頁面組件
2. 如需權限保護：在頁面中添加 `definePageMeta({ middleware: 'auth' })`
3. 如需添加到導航：修改對應的導航組件

### 場景 4：添加 Celery 定時任務

**修改文件順序**：
1. `backend/app/tasks/{domain}_tasks.py` - 創建任務函數
2. `backend/app/tasks/__init__.py` - **導出新任務**
3. `backend/app/core/celery_app.py` - 添加到 `beat_schedule`
4. 重啟服務：`docker compose restart celery-worker celery-beat`

## 🗂️ 數據存儲位置

| 數據類型 | 存儲位置 |
|---------|---------|
| PostgreSQL 數據 | Docker volume `postgres_data` |
| Redis 數據 | Docker volume `redis_data` |
| Qlib 二進制數據 | `/data/qlib/tw_stock_v2/` |
| Shioaji CSV 原始數據 | `/home/ubuntu/QuantLab/ShioajiData/shioaji-stock/` |
| 日誌文件 | `/tmp/shioaji_import/`, `/tmp/batch_sync_*.log` |
| 前端緩存 | `frontend/.nuxt`, `frontend/.output` |

## 🔗 依賴關係圖

```
API 層 (api/v1/)
    ↓ 調用
Service 層 (services/)
    ↓ 調用
Repository 層 (repositories/)
    ↓ 操作
Model 層 (models/)
    ↓ 映射
Database (PostgreSQL)
```

```
Frontend Pages
    ↓ 使用
Components + Stores
    ↓ 調用
Backend API
    ↓ 返回
JSON Response
```

## 📌 重要提醒

1. **添加新模型**：必須在 `app/db/base.py` 導入
2. **添加新任務**：必須在 `app/tasks/__init__.py` 導出
3. **修改環境變數**：同時更新 `.env.example`
4. **資料庫變更**：先閱讀 `Document/DATABASE_CHANGE_CHECKLIST.md`
5. **前端更新**：重大修改後執行 `./scripts/quick-clean.sh`
6. **Vue 模板**：Python f-string 的 `$` 必須寫成 `\$`

## 相關文檔

- [README.md](README.md) - 快速開始與核心命令
- [CLAUDE.md](CLAUDE.md) - 專案概述與架構說明
- [Document/DEVELOPMENT_GUIDE.md](Document/DEVELOPMENT_GUIDE.md) - 開發規範與工作流
