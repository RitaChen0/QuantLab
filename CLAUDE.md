# CLAUDE.md

> 專案描述文件，提供 QuantLab 專案的整體概覽與架構說明，專為 AI 助手和開發者設計。

## 📖 文檔導航指南

### 快速導航

| 需求 | 文檔 | 位置 |
|------|------|------|
| 📚 **快速啟動** | [README.md](README.md) | 根目錄 |
| 🤖 **開發架構** | [CLAUDE.md](CLAUDE.md) | 根目錄（本文件） |
| 📋 **文檔規劃** | [DOCUMENTATION_PLAN.md](DOCUMENTATION_PLAN.md) | 根目錄 |
| 📊 **資料庫架構** | [Document/DATABASE_SCHEMA_REPORT.md](Document/DATABASE_SCHEMA_REPORT.md) | Document/ |
| ✅ **資料庫變更** | [Document/DATABASE_CHANGE_CHECKLIST.md](Document/DATABASE_CHANGE_CHECKLIST.md) | Document/ |
| 🔄 **系統遷移** | [Document/MIGRATION_GUIDE.md](Document/MIGRATION_GUIDE.md) | Document/ |
| 📈 **Qlib 引擎** | [docs/QLIB.md](docs/QLIB.md) | docs/ |
| 🧠 **RD-Agent** | [docs/RDAGENT.md](docs/RDAGENT.md) | docs/ |
| 🔒 **安全指南** | [docs/SECURITY.md](docs/SECURITY.md) | docs/ |
| 📚 **使用指南** | [docs/GUIDES.md](docs/GUIDES.md) | docs/ |
| 📁 **文檔索引** | [Document/README.md](Document/README.md) | Document/ |

### 建議閱讀順序

1. **README.md** - 快速上手（5 分鐘）
2. **CLAUDE.md** - 理解架構（15 分鐘）- 本文件
3. **DOCUMENTATION_PLAN.md** - 了解文檔組織（10 分鐘）
4. **需要時查閱專項文檔**（Database、Qlib、RD-Agent 等）

### 📋 文檔組織原則

> ⚠️ **重要**：本章節定義文檔管理規範，完整版請參閱 [DOCUMENTATION_PLAN.md](DOCUMENTATION_PLAN.md)

#### 文檔結構

```
QuantLab/
├── README.md, CLAUDE.md, CHANGELOG.md, CONTRIBUTING.md  # 4 個核心文檔
├── docs/                       # 專題技術文檔（6 個）
│   ├── QLIB.md                 # Qlib 引擎完整指南
│   ├── RDAGENT.md              # RD-Agent 完整指南
│   ├── SECURITY.md             # 安全文檔
│   ├── GUIDES.md               # 使用指南集合
│   ├── EXTERNAL_ACCESS.md      # 外部訪問配置
│   └── DOCUMENTATION_GUIDE.md  # 文檔撰寫指南
└── Document/                   # 資料庫與系統文檔（17 個）
    ├── DATABASE_*.md           # 5 個資料庫文檔（核心）
    ├── FACTOR_EVALUATION_*.md  # 2 個因子評估文檔（核心）
    ├── MIGRATION_GUIDE.md      # 系統遷移指南（核心）
    ├── IMPROVEMENT_ROADMAP.md  # 改進路線圖（核心）
    └── *_GUIDE.md              # 7 個待整合文檔
```

#### ❌ 絕對不應該提交的文檔類型

**1. 開發過程記錄**
- `*_FIX.md`（如 `DASHBOARD_REFRESH_FIX.md`）
- `*_IMPLEMENTATION.md`
- `*_TROUBLESHOOTING.md`（特定問題的排查過程）
- `*_ISSUE_RESOLVED.md`

**原因**：一次性問題解決記錄，對未來沒有參考價值

**替代方案**：
- 重要修復 → 加入 `CHANGELOG.md`
- 通用故障排查 → 加入 `docs/GUIDES.md`
- 架構決策 → 加入 `CLAUDE.md`

**2. 遷移/升級記錄**
- `*_MIGRATION.md`（如 `MEMBER_LEVELS_0_9_MIGRATION.md`）
- `*_UPGRADE.md`

**原因**：遷移完成後就過時了

**替代方案**：
- 遷移步驟 → 加入 `Document/MIGRATION_GUIDE.md`（通用流程）
- 版本變更 → 加入 `CHANGELOG.md`

**3. 臨時性文檔**
- `TODO.md`、`NOTES.md`、`TEST_RESULTS.md`、會議記錄

**原因**：短期資訊，不應進入版本控制

**替代方案**：使用 GitHub Issues 或保留本地

#### 📝 創建新文檔的決策流程

```
需要記錄資訊？
    │
    ├─ 是一次性問題修復？ → ❌ 不創建 .md，加入 CHANGELOG.md
    ├─ 是臨時性資訊？     → ❌ 不提交，使用 Issues
    ├─ 是小型功能說明？   → ✅ 加入 docs/GUIDES.md
    ├─ 是現有文檔的補充？ → ✅ 更新現有文檔（QLIB.md、RDAGENT.md 等）
    ├─ 是資料庫相關？     → ✅ 加入 Document/DATABASE_*.md
    ├─ 是重大新功能？     → ✅ 在 docs/ 創建新文檔（> 1000 行代碼）
    └─ 其他情況          → ⚠️ 再次考慮是否真的需要
```

#### 🔄 文檔更新規則

**創建新文檔前**：
1. 檢查是否可以加入現有文檔
2. 參考 [DOCUMENTATION_PLAN.md](DOCUMENTATION_PLAN.md) 的完整決策流程
3. 優先更新現有文檔，避免文檔碎片化

**日常維護**：
- 每季度審查文檔，刪除過時內容
- 問題修復後，更新相關故障排查章節，不要創建新文檔
- 功能完成後，更新 CHANGELOG.md 和相關技術文檔

## 專案定位

QuantLab 是一個開源的台股量化交易平台，專注於提供完整的量化研究與策略開發環境。

## 技術架構

### 核心技術棧

**前端技術**：
- Nuxt.js 3 (Vue 3 + TypeScript)
- Pinia (狀態管理)
- ECharts (圖表視覺化)

**後端技術**：
- FastAPI (Python 3.11)
- SQLAlchemy 2.0 (ORM)
- Pydantic (數據驗證)

**數據存儲**：
- PostgreSQL 15 (主數據庫)
- TimescaleDB (時序數據)
- Redis 7 (快取與消息隊列)

**任務系統**：
- Celery (異步任務處理)
- Celery Beat (定時任務調度)

**量化引擎**：
- Qlib (Microsoft - ML 量化平台)
- Backtrader (技術指標回測)
- TA-Lib (技術指標計算)
- PyTorch (深度學習)

**數據來源**：
- FinLab API (台股歷史數據、基本面)
- Shioaji (永豐證券 - 1 分鐘 K 線)
- FinMind (產業分類、財務指標)

### 系統架構

**多容器架構**（6 個 Docker 容器）：
1. `postgres` - TimescaleDB 主數據庫 + 時序數據存儲
2. `redis` - 緩存層 + Celery 消息代理
3. `backend` - FastAPI 應用（端口 8000）
4. `frontend` - Nuxt.js 應用（端口 3000）
5. `celery-worker` - 異步任務處理器
6. `celery-beat` - 定時任務調度器

**容器通信**：通過 `quantlab-network` 橋接網絡，服務名稱作為主機名。

## 後端架構設計

### 四層分層架構

```
app/
├── api/v1/          # API 路由層
├── services/        # 業務邏輯層
├── repositories/    # 數據訪問層
├── models/          # ORM 模型
├── schemas/         # Pydantic Schemas
├── core/            # 核心配置
├── db/              # 數據庫會話
├── utils/           # 工具模組
└── tasks/           # Celery 任務
```

### 層級職責

**API 層** (`app/api/v1/`)：
- 處理 HTTP 請求與響應
- 依賴注入（database session, current user）
- 調用 Service 層
- 統一錯誤處理與日誌記錄
- 不包含業務邏輯

**Service 層** (`app/services/`)：
- 實作核心業務邏輯
- 數據驗證與轉換
- 配額檢查與速率限制
- 調用 Repository 層
- 不直接操作資料庫

**Repository 層** (`app/repositories/`)：
- 資料庫 CRUD 操作
- 查詢建構與執行
- 事務管理
- 不包含業務邏輯

### 關鍵設計原則

- **關注點分離**：每層職責明確，互不越界
- **依賴注入**：使用 FastAPI 的 Depends 機制
- **環境變數管理**：使用 Pydantic Settings
- **結構化日誌**：使用 contextvars 追蹤上下文
- **速率限制**：使用 slowapi 套件
- **錯誤處理**：環境感知（開發/生產模式）

## 前端架構設計

### 目錄結構

```
frontend/
├── pages/           # 頁面組件（路由）
│   ├── dashboard/   # 儀表板
│   ├── strategies/  # 策略管理
│   ├── backtest/    # 回測管理
│   ├── data/        # 數據瀏覽
│   ├── industry/    # 產業分析
│   ├── rdagent/     # AI 因子挖掘
│   └── admin/       # 後台管理
├── components/      # 通用組件
├── stores/          # Pinia 狀態管理
├── composables/     # 組合式函數
└── assets/          # 靜態資源
```

### 策略範本系統

**三個核心組件**：
1. `StrategyTemplates.vue` - Backtrader 策略範本（20 個）
2. `QlibStrategyTemplates.vue` - Qlib ML 策略範本（9 個）
3. `FactorStrategyTemplates.vue` - RD-Agent AI 因子範本（跨引擎）

**範本整合模式**：
- 替換策略：完全覆蓋現有代碼
- 插入因子：智慧合併到現有策略（推薦）
- 追加代碼：在末尾追加參考資訊

## 核心功能模組

### 1. 雙引擎量化系統

**Backtrader 引擎**：
- 定位：輕量級技術指標策略框架
- 適用：個人交易者、技術分析策略
- 特點：簡單易用、文檔完整、學習曲線平緩

**Qlib 引擎**：
- 定位：企業級 ML 量化研究平台
- 適用：機構投資者、機器學習策略
- 特點：原生 ML 支援、表達式引擎、高效能

**設計理念**：兩者互補而非競爭，滿足不同需求層次。

### 2. Qlib 數據適配器

**核心機制**：
- 優先使用本地 Qlib 二進制數據（快 3-10 倍）
- Fallback 機制自動降級到 FinLab API
- 智慧同步自動判斷增量/完整/跳過
- 支援 Qlib 表達式計算技術指標

**數據格式**：
- 使用 Qlib v2 官方格式 (`FileFeatureStorage` API)
- 目錄結構：`features/{stock}/{feature}.day.bin`
- 6 個特徵欄位：open, high, low, close, volume, factor

### 3. RD-Agent AI 因子挖掘

**功能定位**：
- Microsoft Research 開源的 AI 驅動量化研究助手
- 使用 LLM 自動生成 Qlib 表達式因子
- 基於回測結果迭代改進策略

**架構設計**：
- API 層：接收用戶請求，創建任務
- Service 層：配置 RD-Agent scenarios
- Task 層：Celery 異步執行因子挖掘
- 數據層：`rdagent_tasks`, `generated_factors` 表

**跨引擎整合**：
- Backtrader：自動轉換為 Backtrader indicators
- Qlib：直接插入 `QLIB_FIELDS` 陣列

### 4. 產業分析系統

**雙資料來源**：
1. TWSE 台證所分類（3 層階層：大類/中類/小類）
   - 資料表：`industries` (41 個產業)
   - 映射表：`stock_industries` (1,935 筆)
   - 來源：FinLab `company_basic_info`

2. FinMind 產業鏈（扁平化分類）
   - 來源：FinMind API `TaiwanStockIndustryChain`
   - 需付費會員權限

**產業指標計算**：
- 7 個聚合指標：ROE、ROA、毛利率、營業利益率、EPS、營收成長率、淨利成長率
- 數據來源：`fundamental_data` 表（使用季度字串如 "2024-Q4"）
- 快取策略：30 天

### 5. Celery 定時任務系統

**已實作任務**：
- `sync_stock_list` - 每天 8:00 AM（股票清單，快取 24 小時）
- `sync_daily_prices` - 每天 9:00 PM（每日價格，快取 10 分鐘）
- `sync_ohlcv_data` - 每天 10:00 PM（OHLCV 數據，快取 10 分鐘）
- `sync_latest_prices` - 交易時段每 15 分鐘（即時價格，快取 5 分鐘）
- `cleanup_old_cache` - 每天 3:00 AM（清理過期快取）

**任務特性**：
- 自動重試機制（3-5 次）
- 詳細日誌記錄（使用 loguru）
- 結構化返回結果
- 錯誤處理與重試延遲

## 資料庫設計

### 核心資料表

**用戶與認證**：
- `users` - 用戶資料表
- `strategies` - 交易策略表（含代碼、參數、引擎類型）
- `backtests` - 回測記錄表
- `backtest_results` - 回測結果表（績效指標）
- `trades` - 交易記錄表

**數據存儲**：
- `stock_prices` - 股票日線數據（TimescaleDB hypertable）
- `stock_minute_prices` - 1 分鐘 K 線數據（Shioaji）
- `fundamental_data` - 基本面資料（季度數據）

**產業分類**：
- `industries` - 產業分類表（TWSE 3 層階層）
- `stock_industries` - 股票-產業映射表
- `industry_metrics_cache` - 產業指標快取表

**AI 研發**：
- `rdagent_tasks` - RD-Agent 任務記錄
- `generated_factors` - AI 生成的因子

### TimescaleDB 優化

- `stock_prices` 使用 hypertable（按 `date` 分區）
- `stock_minute_prices` 使用 hypertable（按 `datetime` 分區）
- 自動壓縮策略（7 天後壓縮）
- 索引優化（複合索引、部分索引）

## 安全機制

### 認證與授權

- **JWT Token 管理**：access token (30 分鐘) + refresh token (7 天)
- **密碼加密**：bcrypt (cost factor 12)
- **權限控制**：基於角色的訪問控制（RBAC）
- **API 保護**：所有端點預設需認證

### 策略代碼安全

- **AST 解析驗證**：白名單模組、黑名單危險函數
- **沙盒執行**：隔離策略代碼執行環境
- **資源限制**：超時控制、內存限制

### 速率限制與配額

**速率限制**（使用 slowapi）：
- 策略建立：10 requests/hour
- 策略更新：30 requests/hour
- 回測建立：10 requests/hour
- RD-Agent 因子挖掘：3 requests/hour

**配額系統**：
- 每用戶最大策略數：50
- 每用戶最大回測數：200
- 每策略最大回測數：50

## 效能優化

### 快取策略

**Redis 快取層**：
- 股票清單：24 小時快取
- 每日價格：10 分鐘快取
- 最新價格：5 分鐘快取
- 使用 pickle 序列化 DataFrame

### Qlib 效能優化

- 本地二進制存儲（讀取速度快 3-10 倍）
- 智慧同步機制（節省 95%+ 時間）
- Fallback 確保可靠性

### Celery 效能配置

- `worker_prefetch_multiplier=1`（避免長任務阻塞）
- 任務時間限制：硬限制 30 分鐘、軟限制 25 分鐘
- 結果過期時間：1 小時

## 數據來源整合

### FinLab API

- 台股歷史數據（2,671 檔股票）
- 基本面資料（季度更新）
- 公司基本資訊
- API Token 管理

### Shioaji 數據

- 1 分鐘 K 線數據
- 資料範圍：2018-12-07 ~ 2025-12-10（約 7 年）
- 資料量：1,692 個 CSV 檔案
- 資料表：`stock_minute_prices`（60-120M 筆記錄）

### FinMind 數據

- 產業鏈分類
- 財務指標
- 需付費會員權限

## 開發規範

### 代碼風格

**Python**：
- Black (自動格式化)
- Flake8 (Linting，行寬 88)
- mypy (類型檢查)

**TypeScript/Vue**：
- ESLint (Linting)
- 組件名稱使用 PascalCase
- 使用 Composition API

### Git 工作流

**分支策略**：
- `master` - 生產環境
- `develop` - 開發環境
- `feature/*` - 功能分支
- `fix/*` - 修復分支

**Commit Message 規範**：
```
<type>(<scope>): <subject>

type: feat, fix, docs, style, refactor, test, chore
```

## 環境變數配置

### 必填變數

- `DATABASE_URL` - PostgreSQL 連接字串
- `REDIS_URL` - Redis 連接字串
- `JWT_SECRET` - JWT 簽名密鑰（至少 32 字元）
- `FINLAB_API_TOKEN` - FinLab API Token
- `CELERY_BROKER_URL` - Celery 消息代理
- `CELERY_RESULT_BACKEND` - Celery 結果後端

### 選填變數

- `OPENAI_API_KEY` - RD-Agent 因子挖掘
- `ANTHROPIC_API_KEY` - Claude API
- `SHIOAJI_API_KEY` - 永豐證券
- `FUGLE_API_KEY` - 富果證券
- `ALLOWED_ORIGINS` - CORS 配置

## 文檔體系

### 主文檔
- **README.md** - 快速開始與核心操作命令
- **CLAUDE.md** - 專案概述與架構說明（本文件）

### 快速索引（Document 目錄）
- **PROJECT_STRUCTURE.md** - 專案結構索引（快速定位關鍵文件與目錄職責）
- **TROUBLESHOOTING.md** - 故障排查快速索引（常見問題與解決方案）
- **API_QUICK_REFERENCE.md** - API 快速參考（所有端點總覽與代碼位置）

### 操作指南（Document 目錄）
- **OPERATIONS_GUIDE.md** - 完整操作手冊（Docker、資料庫、開發工具）
- **QLIB_SYNC_GUIDE.md** - Qlib 數據同步詳解（智慧同步、效能優化）
- **CELERY_TASKS_GUIDE.md** - Celery 任務管理指南（定時任務、監控）
- **DEVELOPMENT_GUIDE.md** - 開發規範與工作流（架構、測試、Git）

### 資料庫文檔（Document 目錄）
- **DATABASE_SCHEMA_REPORT.md** - 16 個資料表詳細說明
- **DATABASE_CHANGE_CHECKLIST.md** - 56 項變更檢查清單
- **DATABASE_ER_DIAGRAM.md** - ER 圖視覺化
- **DATABASE_MAINTENANCE.md** - 備份與維護指南

## API 文檔

- **Swagger UI**: http://localhost:8000/docs（互動測試）
- **ReDoc**: http://localhost:8000/redoc（閱讀優先）
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

## 重要設計決策

### 1. 為何選擇 FastAPI？

- 現代化的 Python Web 框架
- 原生支援異步操作
- 自動生成 OpenAPI 文檔
- Pydantic 數據驗證
- 高效能（與 Node.js 相當）

### 2. 為何使用 TimescaleDB？

- PostgreSQL 的時序數據擴展
- 自動分區管理
- 壓縮策略節省存儲
- 保留 PostgreSQL 生態系統

### 3. 為何支援雙引擎？

- Backtrader：降低學習門檻，適合初學者
- Qlib：提供企業級 ML 能力，滿足進階需求
- 兩者互補，覆蓋更廣泛的用戶群

### 4. 為何使用 Celery？

- 成熟的分散式任務系統
- 支援定時任務調度
- 可靠的重試機制
- 與 Python 生態系統整合良好

### 5. 為何採用四層架構？

- 關注點分離，提高可維護性
- 業務邏輯與數據訪問解耦
- 便於單元測試
- 支援未來擴展（如微服務化）

## 已知限制與未來規劃

### 目前限制

- 僅支援台股市場
- 回測引擎尚未完整實作
- 缺少實盤交易功能
- AI 因子挖掘需 OpenAI API（付費）

### 未來規劃

- 支援美股、港股市場
- 完善回測引擎（滑價、交易成本模擬）
- 整合更多券商 API
- 策略社群分享平台
- 雲端部署方案

## 授權與貢獻

- **授權**：MIT License
- **貢獻**：歡迎提交 Issue 和 Pull Request
- **免責聲明**：本軟體僅供教育與研究用途，不構成投資建議
