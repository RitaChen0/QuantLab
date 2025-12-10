# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概述

QuantLab 是一個開源的台股量化交易平台，採用前後端分離架構，使用 Docker Compose 進行服務編排。

**核心技術棧**：
- Frontend: Nuxt.js 3 (Vue 3 + TypeScript) + Pinia
- Backend: FastAPI (Python 3.11) + SQLAlchemy 2.0
- Database: PostgreSQL 15 + TimescaleDB (時序數據)
- Cache/Queue: Redis 7 + Celery
- Quantitative: Qlib (Microsoft) + FinLab API + TA-Lib + Backtrader + PyTorch

**資料庫文檔**：
- 📖 [Document/DATABASE_SCHEMA_REPORT.md](Document/DATABASE_SCHEMA_REPORT.md) - 完整資料庫架構報告（16 個資料表詳細說明）
- 📋 [Document/DATABASE_CHANGE_CHECKLIST.md](Document/DATABASE_CHANGE_CHECKLIST.md) - 資料庫變更檢查清單（56 項檢查）
- 🔗 [Document/DATABASE_ER_DIAGRAM.md](Document/DATABASE_ER_DIAGRAM.md) - ER 圖與關聯關係視覺化

## 常用開發指令

### Docker 環境管理

```bash
# 啟動所有服務
docker compose up -d

# 查看服務狀態
docker compose ps

# 查看日誌（所有服務）
docker compose logs -f

# 查看特定服務日誌
docker compose logs -f backend
docker compose logs -f frontend

# 重啟特定服務
docker compose restart backend

# 停止所有服務
docker compose down

# 停止並刪除所有數據（包括 volumes）
docker compose down -v

# 重新構建並啟動
docker compose up --build -d
```

### 資料庫管理

**⚠️ 重要：任何資料庫變更前，請先閱讀 [Document/DATABASE_CHANGE_CHECKLIST.md](Document/DATABASE_CHANGE_CHECKLIST.md)**

```bash
# 執行資料庫遷移（升級到最新版本）
docker compose exec backend alembic upgrade head

# 創建新的遷移檔案
docker compose exec backend alembic revision --autogenerate -m "描述"

# 回滾到上一個版本
docker compose exec backend alembic downgrade -1

# 查看遷移歷史
docker compose exec backend alembic history

# 直接連接到 PostgreSQL
docker compose exec postgres psql -U quantlab -d quantlab
```

**資料庫架構參考**：
- 詳細資料表結構：[Document/DATABASE_SCHEMA_REPORT.md](Document/DATABASE_SCHEMA_REPORT.md)
- ER 圖視覺化：[Document/DATABASE_ER_DIAGRAM.md](Document/DATABASE_ER_DIAGRAM.md)
- 變更檢查清單：[Document/DATABASE_CHANGE_CHECKLIST.md](Document/DATABASE_CHANGE_CHECKLIST.md)

### 後端開發

```bash
# 進入後端容器
docker compose exec backend bash

# 運行測試
docker compose exec backend pytest

# 運行特定測試檔案
docker compose exec backend pytest tests/test_auth.py

# 檢查代碼風格
docker compose exec backend flake8 app/
docker compose exec backend black --check app/

# 自動格式化代碼
docker compose exec backend black app/

# 類型檢查
docker compose exec backend mypy app/
```

### 前端開發

```bash
# 進入前端容器
docker compose exec frontend sh

# 重新安裝依賴（當 package.json 更新後）
docker compose exec frontend npm install

# 運行 linting
docker compose exec frontend npm run lint

# 自動修復 lint 錯誤
docker compose exec frontend npm run lint:fix
```

### Celery 任務管理

```bash
# 查看 Celery worker 日誌
docker compose logs -f celery-worker

# 查看 Celery beat 日誌
docker compose logs -f celery-beat

# 重啟 Celery worker
docker compose restart celery-worker

# 監控任務執行狀態（使用監控腳本）
./monitor_celery.sh

# 手動觸發任務
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_stock_list

# 檢查任務註冊狀態
docker compose exec backend celery -A app.core.celery_app inspect registered

# 檢查當前活躍任務
docker compose exec backend celery -A app.core.celery_app inspect active

# 查看 worker 統計資訊
docker compose exec backend celery -A app.core.celery_app inspect stats
```

### Qlib 數據引擎同步

**⚠️ 重要變更（2025-12-06）**：系統已遷移至 **Qlib v2 官方格式 + 智慧同步**

**Qlib v2 資料格式轉換**：將資料庫中的股票歷史數據轉換為 Qlib 官方二進制格式，提升回測效能。

```bash
# 🧠 智慧同步（推薦）：自動增量更新，跳過已同步的股票
./scripts/sync-qlib-smart.sh

# 測試模式（僅 10 檔）
./scripts/sync-qlib-smart.sh --test

# 同步單一股票
./scripts/sync-qlib-smart.sh --stock 2330

# 手動執行同步腳本（v2 + 智慧模式）
docker compose exec backend python /app/scripts/export_to_qlib_v2.py \
  --output-dir /data/qlib/tw_stock_v2 \
  --stocks all \
  --smart

# 限制處理數量（測試用）
docker compose exec backend python /app/scripts/export_to_qlib_v2.py \
  --output-dir /data/qlib/tw_stock_v2 \
  --stocks all \
  --smart \
  --limit 100

# 強制完整重新同步（不使用智慧模式）
docker compose exec backend python /app/scripts/export_to_qlib_v2.py \
  --output-dir /data/qlib/tw_stock_v2 \
  --stocks all

# 測試 Qlib 引擎
docker compose exec backend python scripts/test_qlib_engine.py
```

**Qlib v2 數據特性**：
- **官方格式**：使用 `FileFeatureStorage` API，確保完全兼容
- **目錄結構**：`features/{stock}/` 而非舊的 `instruments/`
- **檔案格式**：`{feature}.day.bin`（如 `close.day.bin`）
- **二進制存儲**：讀取速度比 pandas 快 3-10 倍
- **智慧同步**：自動判斷增量/完整/跳過（節省 95%+ 時間）
- **特徵欄位**：6 個（open, high, low, close, volume, factor）
- **Fallback 機制**：本地數據不存在時自動使用 FinLab API

**智慧同步邏輯**：
```
1. 檢查 Qlib 已有數據 → 無數據 → 📦 完整同步
2. Qlib 最後日期 >= 資料庫 → ⏭️  跳過（已是最新）
3. 有新數據 → ➕ 增量同步（只同步新增日期）
```

**效能對比**：
- 首次同步（2,671 檔）：2-4 小時
- 日常增量（10 筆新數據）：2-5 分鐘（節省 ~95%）
- 已是最新：< 30 秒（節省 ~99%）

**重要設定**：
- 環境變數：`QLIB_DATA_PATH=/data/qlib/tw_stock_v2`（已在 `.env` 配置）
- Docker volume 掛載：`/data/qlib:/data/qlib`（持久化儲存）
- Qlib 快取路徑：`/tmp/qlib_cache`（容器內）
- 數據路徑：`/data/qlib/tw_stock_v2/features/`

**腳本版本說明**：
- `export_to_qlib_v2.py`：✅ **推薦使用**（官方格式 + 智慧同步）
- `export_to_qlib.py`：⚠️ 舊版本（自定義格式，保留作參考）

### 財務指標批次同步

```bash
# 手動同步（互動式，推薦）
./scripts/manual-sync.sh

# 批次同步所有股票（2,671 檔，約 6-8 小時）
./scripts/batch-sync.sh

# 測試模式（僅 10 檔）
./scripts/batch-sync.sh --test

# 查看批次同步進度
./scripts/batch-sync.sh --status

# 監控批次同步（圖形化介面）
./scripts/monitor-batch-sync.sh

# 重新開始批次同步（清除進度）
./scripts/batch-sync.sh --reset
```

**批次同步特性**：
- 自動斷點續傳（中斷後可繼續）
- 進度追蹤與預估時間
- 批次處理（每批 100 檔，批次間延遲 60 秒）
- 失敗重試機制
- 詳細日誌記錄於 `/tmp/batch_sync_*.log`
- 進度檔案於 `/tmp/batch_sync_progress.json`

**使用指南**：詳見 `BATCH_SYNC_GUIDE.md` 和 `MANUAL_SYNC_GUIDE.md`

## 架構與設計模式

### 多服務架構

系統由 6 個 Docker 容器組成，通過 `quantlab-network` 橋接網絡通信：

1. **postgres** (TimescaleDB): 主數據庫 + 時序數據存儲
2. **redis**: 緩存層 + Celery 消息代理
3. **backend**: FastAPI 應用（端口 8000）
4. **celery-worker**: 異步任務處理器
5. **celery-beat**: 定時任務調度器
6. **frontend**: Nuxt.js 應用（端口 3000）

### 後端架構模式

**四層分層架構**：
```
app/
├── api/v1/          # API 路由層（處理 HTTP 請求/響應）
├── services/        # 業務邏輯層（核心業務邏輯、驗證、配額檢查）
│   ├── qlib_data_adapter.py       # Qlib 數據適配器（本地數據 + FinLab API）
│   ├── qlib_backtest_engine.py    # Qlib 回測引擎
│   └── finlab_client.py           # FinLab API 客戶端
├── repositories/    # 數據訪問層（數據庫操作抽象）
├── models/          # SQLAlchemy ORM 模型
├── schemas/         # Pydantic Schemas（數據驗證）
├── core/            # 核心配置（config, security, rate_limit, celery_app）
│   └── qlib_config.py             # Qlib 初始化配置
├── db/              # 數據庫會話管理
├── utils/           # 工具模組（cache, logging）
└── tasks/           # Qlib 異步任務
```

**關鍵設計原則**：
1. **API 層責任**：
   - 處理 HTTP 請求/響應
   - 依賴注入（database session, current user）
   - 調用 Service 層方法
   - 統一錯誤處理（使用 `_handle_error()` 輔助函數）
   - 結構化日誌記錄（使用 `api_log`）
   - 不包含業務邏輯

2. **Service 層責任**：
   - 核心業務邏輯實作
   - 數據驗證與轉換
   - 配額檢查與限制
   - 調用 Repository 層方法
   - 拋出 HTTPException 處理錯誤
   - 不直接操作 SQLAlchemy 模型

3. **Repository 層責任**：
   - 資料庫 CRUD 操作
   - 查詢建構與執行
   - 事務管理（commit/rollback）
   - 返回 ORM 模型物件
   - 不包含業務邏輯

4. **關鍵設計決策**：
   - 使用 Pydantic Settings 管理環境變數（`app/core/config.py`）
   - 所有 API 端點前綴為 `/api/v1`
   - 速率限制使用 slowapi（`app/core/rate_limit.py`）
   - 結構化日誌使用 contextvars 追蹤上下文（`app/utils/logging.py`）
   - 自定義 Redoc 頁面使用本地 JavaScript（避免 CDN 依賴）
   - StaticFiles 掛載在 `/static` 用於提供 Redoc 資源

5. **Qlib 數據適配器模式**（`app/services/qlib_data_adapter.py`）：

   **設計原則**：優先使用本地 Qlib 數據，失敗時自動降級到 FinLab API

   ```python
   # 數據讀取流程
   def get_qlib_ohlcv(symbol, start_date, end_date):
       # 1. 檢查 Qlib 本地數據是否存在
       if self.qlib_initialized and self._check_qlib_data_exists(symbol):
           # 使用 Qlib D.features() API 讀取本地 .bin 檔案
           df = D.features(instruments=[symbol], fields=fields, ...)
           if df is not None:
               return df  # ✅ 使用本地數據（快 3-10 倍）

       # 2. Fallback: 從 FinLab API 獲取
       df = self.finlab_client.get_ohlcv(symbol, ...)
       return df  # ⚠️ API 調用（較慢但可靠）
   ```

   **關鍵方法**：
   - `get_qlib_ohlcv()`: 獲取 OHLCV 數據（優先本地，fallback API）
   - `get_qlib_features()`: 使用 Qlib 表達式計算技術指標
   - `_check_qlib_data_exists()`: 檢查本地 `.bin` 檔案是否存在
   - `calculate_technical_factors()`: ⚠️ 已棄用，改用 Qlib 表達式引擎

   **Qlib 表達式範例**：
   ```python
   fields = [
       '$close',                           # 收盤價
       'Mean($close, 5)',                  # 5 日均線
       'Std($close, 20)',                  # 20 日標準差
       '$close / Mean($close, 20)',        # 價格相對均線比率
       '$volume / Mean($volume, 20)',      # 成交量比率
       'Corr($close, $volume, 10)',        # 價量相關性
   ]
   df = adapter.get_qlib_features(symbol, start_date, end_date, fields=fields)
   ```

   **效能對比**：
   - 本地 Qlib 數據：0.1-0.3 秒/檔（讀取 `.bin` 檔案）
   - FinLab API：1-3 秒/檔（HTTP 請求 + 網路延遲）
   - 技術指標計算：Qlib 表達式引擎自動處理，無需手動 pandas 計算

**新增 API 端點的標準流程**：
```python
# 1. API 層 (app/api/v1/module.py)
@router.post("/", response_model=Schema, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.OPERATION_CREATE)
async def create_resource(
    request: Request,
    resource_create: ResourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service = ResourceService(db)
        resource = service.create_resource(current_user.id, resource_create)

        api_log.log_operation("create", "resource", resource.id, current_user.id, success=True)
        return resource
    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error("Create resource", e, "Failed to create resource")

# 2. Service 層 (app/services/resource_service.py)
def create_resource(self, user_id: int, resource_create: ResourceCreate) -> Resource:
    # 檢查配額
    self._check_quota(user_id)

    # 驗證數據
    self._validate_resource_data(resource_create)

    # 調用 Repository
    return self.repo.create(self.db, user_id, resource_create)

# 3. Repository 層 (app/repositories/resource.py)
def create(self, db: Session, user_id: int, resource_create: ResourceCreate) -> Resource:
    resource = Resource(user_id=user_id, **resource_create.model_dump())
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource
```

### 啟動流程

**後端啟動順序**（由 `backend/start.sh` 控制）：
1. 執行 Alembic 資料庫遷移：`alembic upgrade head`
2. 啟動 Uvicorn 服務器：`uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

**健康檢查端點**：
- Backend: `GET /health` 返回 `{"status": "healthy", "version": "0.1.0"}`
- PostgreSQL: `pg_isready -U quantlab`
- Redis: `redis-cli ping`

### 前端架構

**Nuxt.js 配置要點**（`frontend/nuxt.config.ts`）：
- **已禁用模組**：`@nuxtjs/tailwindcss`, `@nuxt/ui`（由於 Tailwind CSS 衝突）
- **TypeScript**：`strict: false`, `typeCheck: false`（避免 vue-tsc 問題）
- **API 配置**：通過 `runtimeConfig.public.apiBase` 設定後端 URL

**路由結構**：
```
pages/
├── index.vue                    # 首頁
├── login.vue                    # 登入頁
├── register.vue                 # 註冊頁
├── docs.vue                     # API 文檔頁
├── admin/
│   └── index.vue                # 後台管理頁（需 superuser 權限）
├── dashboard/
│   └── index.vue                # 儀表板總覽（顯示最近策略、統計數據）
├── strategies/
│   ├── index.vue                # 策略列表頁
│   └── [id]/
│       ├── index.vue            # 策略詳情頁（顯示代碼、回測記錄）
│       └── edit.vue             # 策略編輯頁
├── backtest/
│   ├── index.vue                # 回測列表頁
│   └── [id].vue                 # 回測詳情頁（含 ECharts 圖表）
├── data/
│   └── index.vue                # 股票數據瀏覽頁（支援 10 年歷史數據）
└── industry/
    └── index.vue                # 產業分析頁（TWSE 分類 + FinMind 產業鏈）
```

**前端樣式重要注意事項**：

1. **SVG 圖示大小問題**：
   - Tailwind CSS 的 `w-{n}` 和 `h-{n}` 類別在 `<style scoped>` 中可能失效
   - 必須在 scoped style 中使用 `!important` 明確設定 SVG 尺寸：
   ```scss
   svg.w-4 {
     width: 1rem !important;
     height: 1rem !important;
     flex-shrink: 0;
   }
   ```
   - 參考：`frontend/pages/industry/index.vue:1052-1068`

2. **動態載入 ECharts**：
   - 必須在客戶端載入（檢查 `process.client`）
   - 使用 CDN 動態載入避免 SSR 問題
   - 初始化後調用 `resize()` 確保正確尺寸

**策略範本庫組件**：

1. **StrategyTemplates.vue** - Backtrader 策略範本（20 個）
   - **趨勢跟隨（8 個）**: 雙均線交叉、MACD 趨勢、三均線、ADX 趨勢強度、趨勢線突破、唐奇安通道、多週期確認、停損停利
   - **均值回歸（5 個）**: RSI 反轉、Williams %R、均值回歸通道、KDJ 超買超賣、CCI 商品通道
   - **突破策略（3 個）**: 布林通道突破、成交量突破、波動率收縮突破
   - **機器學習（3 個）**: LightGBM 動量代理、Random Forest 多因子、XGBoost 時序預測
   - **網格交易（1 個）**: 價格網格交易策略

2. **QlibStrategyTemplates.vue** - Qlib 量化策略範本（9 個）
   - **因子策略（5 個）**:
     - 均線交叉策略（Qlib 表達式：`Mean($close, 5)`, `Mean($close, 20)`）
     - 動量因子策略（多周期動量 + 成交量確認 + 波動率調整）
     - 波動率突破策略（布林通道 + ATR）
     - 均值回歸策略（Z-Score + RSI 超買超賣）
     - 價量相關性策略（`Corr($close, $volume, 10)` 趨勢確認）
   - **機器學習（4 個）**:
     - LightGBM 預測模型（18 個技術指標，多因子綜合評分）
     - Alpha158 多因子策略（KBar + Price + Volume + Rolling 四大類）
     - Alpha158 機器學習特徵（完整 158 因子，適合訓練）
     - **Alpha158 真正ML（修復版）** - 完整的 LightGBM 訓練流程（特徵清理 + 訓練/測試分割 + 模型訓練 + 預測）

3. **FactorStrategyTemplates.vue** - RD-Agent 因子範本
   - 自動生成因子的策略框架
   - 支援跨引擎整合（Backtrader / Qlib）
   - 三種插入模式：替換策略、插入因子、追加代碼

**引擎切換功能** (`frontend/pages/strategies/[id]/edit.vue`)：
- **雙引擎架構**: 在策略編輯頁面可選擇 `engine_type`：
  - `backtrader`: 技術指標策略（傳統量化）
  - `qlib`: 機器學習策略（Qlib 表達式引擎）
- **動態範本切換**: 根據引擎類型自動顯示對應範本
- **多種插入模式**:
  - 🔄 **替換策略**: 完全覆蓋現有代碼（需確認）
  - ⭐ **插入因子**: 智慧合併到現有策略（推薦，自動添加分隔線）
  - ➕ **追加代碼**: 追加到代碼末尾

**範本使用流程**：
1. 進入策略編輯頁面（`/strategies/{id}/edit`）
2. 選擇回測引擎（Backtrader / Qlib）
3. 點擊「使用範本」按鈕
4. 選擇範本標籤：
   - 📚 **通用範本**: 根據引擎顯示對應策略（Backtrader 20 個 / Qlib 9 個）
   - 🧬 **RD-Agent 因子範本**: 僅 Qlib 引擎可用（從 AI 生成的因子創建策略）
5. 選擇範本並點擊插入按鈕
6. 確認插入模式（替換/插入因子/追加）
7. 編輯並儲存策略（`engine_type` 會一併儲存）

**重要設計決策**：
- `insertTemplate` 函數支援兩種事件格式：
  - `string`: StrategyTemplates 簡單格式（直接傳代碼字串）
  - `{code, mode, template}`: QlibStrategyTemplates 物件格式（支援多種插入模式）
- 跨引擎警告：Backtrader 引擎選擇 RD-Agent 因子範本時會顯示警告訊息，建議切換引擎或手動轉換語法

### RD-Agent 整合（AI 因子挖掘）

**定位**：Microsoft Research 開源的 AI 驅動量化研究助手

**核心功能**：
- 自動因子挖掘：使用 LLM 生成 Qlib 表達式因子
- 策略優化：基於回測結果迭代改進策略
- 模型提取：從現有策略中萃取可重用因子

**架構**（`app/api/v1/rdagent.py`, `app/services/rdagent_service.py`, `app/tasks/rdagent_tasks.py`）：
- **API 層**：接收用戶請求，創建 RD-Agent 任務
- **Service 層**：配置 RD-Agent scenarios，管理執行流程
- **Task 層**：Celery 異步執行因子挖掘任務
- **數據存儲**：`rdagent_tasks` 表（任務記錄）、`generated_factors` 表（因子結果）

**重要環境變數**：
```bash
OPENAI_API_KEY=your_key         # GPT-4 API（必填）
RDAGENT_ENABLE_DOCKER=false     # 是否啟用 Docker 隔離執行（選填，預設 false）
```

**Docker 依賴問題**：
- RD-Agent 預設需要 Docker 來隔離執行因子代碼
- 如果在 Docker 容器內運行，需要掛載 Docker socket：
  ```yaml
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
  ```
- **安全警告**：掛載 Docker socket 讓容器可完全控制主機，僅在受信任環境使用

**RD-Agent API 端點** (`app/api/v1/rdagent.py`)：
- `POST /api/v1/rdagent/factor-mining` - 創建因子挖掘任務
- `POST /api/v1/rdagent/strategy-optimization` - 創建策略優化任務
- `GET /api/v1/rdagent/tasks` - 獲取任務列表
- `GET /api/v1/rdagent/tasks/{task_id}` - 獲取任務詳情
- `DELETE /api/v1/rdagent/tasks/{task_id}` - 刪除任務
- `GET /api/v1/rdagent/factors` - 獲取生成的因子列表

**前端頁面**（`frontend/pages/rdagent/index.vue`）：
- 創建因子挖掘任務（研究目標、股票池、最大因子數、LLM 模型、迭代次數）
- 查看任務執行進度（pending/running/completed/failed/cancelled）
- 瀏覽生成的因子（名稱、公式、績效指標：IC、ICIR、Sharpe Ratio、年化收益）
- 查看因子代碼（Python 實作，可展開/收合）
- 一鍵插入因子到策略編輯器（支援 Backtrader 和 Qlib 兩種引擎）

**速率限制**：
- 因子挖掘：3 requests/hour
- 策略優化：5 requests/hour
- 每任務最多生成 20 個因子
- 最大迭代次數：10 次

**跨引擎整合**：
- RD-Agent 生成的因子（Qlib 表達式格式）可用於：
  - **Backtrader 策略**：自動轉換為 Backtrader indicators
  - **Qlib ML 策略**：直接插入 QLIB_FIELDS
- 提供三種整合模式：
  - 🔄 **替換策略**：生成完整策略框架
  - ⭐ **插入因子**：智慧合併到現有策略（推薦）
  - ➕ **追加代碼**：在末尾追加因子資訊

**使用流程**：
1. 進入「自動研發」頁面（`/rdagent`）
2. 點擊「新增任務」→「因子挖掘」
3. 設定研究目標（如：「找出台股中的動量因子」）
4. 選擇股票池（如：「台股全市場」）
5. 設定參數（最多 5 個因子、最多 3 次迭代）
6. 提交任務，等待 LLM 生成因子
7. 查看生成的因子清單（包含公式、績效指標）
8. 點擊「插入因子」按鈕，將因子加入策略編輯器

**詳細文檔**：[RDAGENT_INTEGRATION_GUIDE.md](RDAGENT_INTEGRATION_GUIDE.md)

### 產業分析架構

**產業分類系統** (`app/api/v1/industry.py`, `app/services/industry_service.py`)：

支援兩種產業分類資料來源：
1. **TWSE 台證所分類**：3 層階層式分類（大類/中類/小類）
   - 資料來源：`industries` 表（41 個產業類別）
   - 股票映射：`stock_industries` 表（1,935 筆映射）
   - 從 FinLab `company_basic_info` 的「產業類別」欄位匯入

2. **FinMind 產業鏈**：扁平化產業分類
   - 資料來源：FinMind API `TaiwanStockIndustryChain`
   - 需要付費會員才能訪問
   - 提供即時同步功能

**產業 API 端點**：
- `GET /api/v1/industry/` - 獲取產業列表
- `GET /api/v1/industry/statistics/overview` - 產業統計總覽
- `GET /api/v1/industry/{code}/stocks` - 獲取產業內股票
- `GET /api/v1/industry/{code}/metrics` - 計算產業聚合指標
- `GET /api/v1/industry/{code}/metrics/historical` - 歷史指標趨勢
- `POST /api/v1/industry/finmind/sync` - 同步 FinMind 產業鏈

**產業聚合指標計算**（`industry_service.py:122-244`）：

**重要**：`fundamental_data` 表使用**季度字串**（如 "2024-Q4"），不是日期格式。

計算邏輯：
1. 查詢最新可用季度：`SELECT date FROM fundamental_data ORDER BY date DESC LIMIT 1`
2. 使用季度字串精確匹配：`WHERE date = '2024-Q4'`
3. 計算 7 個產業平均指標：
   - ROE稅後、ROA稅後息前、營業毛利率、營業利益率
   - 每股稅後淨利、營收成長率、稅後淨利成長率
4. 快取結果 30 天

**常見錯誤**：
- ❌ 錯誤：使用 `date.today()` 查詢當天日期（如 "2025-12-03"）
- ✅ 正確：查詢最新季度字串並使用該值（如 "2024-Q4"）

## 環境變數配置

**必填變數**（參考 `.env.example`）：
```bash
# 數據庫連接
DATABASE_URL=postgresql://quantlab:quantlab2025@postgres:5432/quantlab

# Redis
REDIS_URL=redis://redis:6379/0

# JWT 認證
JWT_SECRET=<使用強隨機字串>

# FinLab API（需從 https://ai.finlab.tw/ 取得）
FINLAB_API_TOKEN=your_token_here

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

**選填變數**（進階功能）：
```bash
# CORS - 外部訪問配置（逗號分隔多個來源）
ALLOWED_ORIGINS=http://localhost:3000,http://192.168.1.100:3000

# AI 整合
OPENAI_API_KEY=your_openai_key        # OpenAI GPT-4
ANTHROPIC_API_KEY=your_anthropic_key  # Claude API

# 券商 API
SHIOAJI_API_KEY=your_key              # 永豐證券
FUGLE_API_KEY=your_key                # 富果證券

# Email 通知
SMTP_HOST=smtp.gmail.com
SMTP_USER=your_email@gmail.com

# 監控
SENTRY_DSN=your_sentry_dsn            # 錯誤追蹤
```

**容器間通信**：
- 服務名稱（如 `postgres`, `redis`）在容器內作為主機名使用
- 例如：後端通過 `postgresql://quantlab:password@postgres:5432/quantlab` 連接數據庫

**外部訪問配置**：
- 若需從區域網其他設備訪問，修改 `ALLOWED_ORIGINS` 和 `NUXT_PUBLIC_API_BASE`
- 範例：`ALLOWED_ORIGINS=http://192.168.1.100:3000,http://192.168.1.100:8000`

## 數據庫遷移系統

使用 Alembic 進行數據庫版本控制：

**配置檔案**：
- `backend/alembic.ini`: Alembic 配置
- `backend/alembic/env.py`: 遷移環境設定
- `backend/alembic/versions/`: 遷移腳本目錄

**Base 模型導入**：
所有 SQLAlchemy 模型必須在 `app/db/base.py` 中導入，以便 Alembic 自動檢測：
```python
from app.db.base import Base
from app.models.user import User  # noqa: F401
# 新模型在此導入
```

**已有模型**：
- `User` (`app/models/user.py`): 用戶表
- `Strategy` (`app/models/strategy.py`): 交易策略表，包含代碼、參數、狀態
- `Backtest` (`app/models/backtest.py`): 回測記錄表
- `BacktestResult` (`app/models/backtest.py`): 回測結果表（績效指標）
- `Trade` (`app/models/backtest.py`): 交易記錄表
- `Industry` (`app/models/industry.py`): 產業分類表（TWSE 3 層階層）
- `StockIndustry` (`app/models/stock_industry.py`): 股票-產業映射表
- `FundamentalData` (`app/models/fundamental_data.py`): 基本面資料表（季度資料）
- `IndustryMetricsCache` (`app/models/industry_metrics_cache.py`): 產業指標快取表

### 資料庫備份與維護

**自動化備份腳本**：
```bash
# 完整資料庫備份（保留 30 天）
./scripts/backup_database.sh

# 僅備份產業分類資料
./scripts/backup_industries.sh
```

**手動備份**：
```bash
# 完整備份
docker compose exec -T postgres pg_dump -U quantlab quantlab | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# 僅備份特定資料表
docker compose exec -T postgres pg_dump -U quantlab quantlab -t industries -t stock_industries | gzip > industries_backup.sql.gz

# 還原備份
gunzip < backup.sql.gz | docker compose exec -T postgres psql -U quantlab quantlab
```

**資料庫維護清單**（詳見 `DATABASE_MAINTENANCE.md`）：
- 定期檢查資料表大小與成長趨勢
- 監控索引使用情況
- 清理過期快取資料
- 驗證產業映射完整性
- 備份關鍵資料表

## Celery 任務系統

**配置位置**：`app/core/celery_app.py`

**已實作的定時任務**：
```python
celery_app.conf.beat_schedule = {
    "sync-stock-list-daily": {
        "task": "app.tasks.sync_stock_list",
        "schedule": crontab(hour=8, minute=0),  # 每天 8:00 AM
    },
    "sync-daily-prices": {
        "task": "app.tasks.sync_daily_prices",
        "schedule": crontab(hour=21, minute=0),  # 每天 9:00 PM (收盤後)
    },
    "sync-ohlcv-daily": {
        "task": "app.tasks.sync_ohlcv_data",
        "schedule": crontab(hour=22, minute=0),  # 每天 10:00 PM
    },
    "sync-latest-prices-frequent": {
        "task": "app.tasks.sync_latest_prices",
        "schedule": crontab(minute='*/15', hour='9-13', day_of_week='mon,tue,wed,thu,fri'),  # 交易時段每 15 分鐘
    },
    "cleanup-cache-daily": {
        "task": "app.tasks.cleanup_old_cache",
        "schedule": crontab(hour=3, minute=0),  # 每天 3:00 AM
    },
}
```

**已定義任務** (`app/tasks/stock_data.py`)：
- `sync_stock_list`: 同步股票清單 (2,671 檔台股)，快取 24 小時
- `sync_daily_prices`: 同步每日價格 (熱門股票 15 檔，過去 7 天)，快取 10 分鐘
- `sync_ohlcv_data`: 同步 OHLCV 數據 (前 5 大股票，30 天)，快取 10 分鐘
- `sync_latest_prices`: 同步最新價格 (10 檔熱門股)，快取 5 分鐘
- `cleanup_old_cache`: 清理過期快取

**任務特性**：
- 所有任務都有自動重試機制 (3-5 次)
- 詳細的日誌記錄（使用 loguru）
- 結構化的返回結果（status, count, timestamp）
- 錯誤處理與重試延遲 (60-300 秒)

## TA-Lib 安裝注意事項

**重要**：在 ARM64 架構（Apple Silicon）上：
- `requirements.txt` 中不要指定 TA-Lib 版本號
- 只寫 `TA-Lib`，讓 pip 自動選擇兼容的預編譯 wheel（如 `ta_lib-0.6.8-cp311-cp311-manylinux2014_aarch64`）
- 不需要從源碼編譯

## API 文檔訪問

- **Swagger UI（互動測試）**: http://localhost:8000/docs
- **ReDoc（閱讀優先）**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

## 常見問題排查

### 後端容器反覆重啟
檢查日誌：`docker compose logs backend`
常見原因：
1. 資料庫連接失敗（檢查 `DATABASE_URL`）
2. 環境變數缺失（如 `JWT_SECRET`）
3. Python 依賴問題（重新構建：`docker compose build backend`）

### Alembic 遷移失敗
確認：
1. PostgreSQL 容器健康：`docker compose ps postgres`
2. 遷移檔案語法正確
3. 新模型已在 `app/db/base.py` 導入

### 前端白屏或 500 錯誤
檢查：
1. `nuxt.config.ts` 中的模組配置（避免重複的 Tailwind CSS 模組）
2. 容器日誌：`docker compose logs frontend`
3. TypeScript 錯誤（已禁用 typeCheck）

### Celery worker 無法連接
確認：
1. Redis 容器運行：`docker compose ps redis`
2. 環境變數正確：`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
3. 檢查 `app/core/celery_app.py` 配置
4. **重要**：backend 服務也需要 CELERY 環境變數（用於手動觸發任務）

### 任務更新後無法載入
如果更新了 Celery 任務但出現 ImportError：
1. 檢查 `app/tasks/__init__.py` 是否正確導出新任務
2. 清除 Python cache：`docker compose exec celery-worker find /app -name __pycache__ -type d -exec rm -rf {} +`
3. 重啟 worker 和 beat：`docker compose restart celery-worker celery-beat`

### Pydantic RecursionError
如果 schemas 出現遞迴錯誤：
1. 避免使用過於複雜的 Field 描述
2. 簡化 schema 定義，使用基本型別
3. 檢查是否有循環引用

### 文件權限問題
Docker volume 掛載可能導致權限問題：
1. 新增的 Python 檔案：`chmod 644 filename.py`
2. 新增的目錄：`chmod 755 dirname`
3. 或使用：`chmod -R a+r backend/app/ && chmod -R a+X backend/app/`

### 前端緩存問題
Nuxt.js 緩存可能導致組件更新不生效、出現舊組件警告等問題：

**症狀**：
- 組件重命名後仍出現舊組件警告
- 代碼更新後未生效
- 頁面顯示異常

**解決方案 1：使用自動化腳本（推薦）**
```bash
# 完整清理（交互式）
./scripts/clear-frontend-cache.sh

# 快速清理（無交互）
./scripts/quick-clean.sh
```

**解決方案 2：手動清理**
```bash
# 1. 停止前端服務
docker compose stop frontend

# 2. 清理本地緩存
cd frontend
rm -rf .nuxt .output node_modules/.vite node_modules/.cache

# 3. 清理容器內緩存
cd ..
docker compose run --rm frontend sh -c "rm -rf .nuxt .output node_modules/.vite node_modules/.cache"

# 4. 重啟服務
docker compose up -d frontend
```

**解決方案 3：完整重建（最徹底）**
```bash
docker compose down
docker compose build --no-cache frontend
docker compose up -d
```

**預防措施**：
- 重大更新後主動清理緩存
- 開發時定期執行 `quick-clean.sh`
- CI/CD 流程中加入緩存清理步驟

### SVG 圖示顯示異常

**症狀**：
- SVG 圖示（箭頭、圖標）佔據整個螢幕
- Tailwind CSS 的 `w-{n}` 和 `h-{n}` 類別失效

**根本原因**：
- 在 `<style scoped>` 中，Tailwind utility classes 可能被 CSS 特異性覆蓋
- Vue scoped styles 的處理方式導致 class 選擇器優先級問題

**解決方案**：
在 `<style scoped>` 區塊中明確設定 SVG 尺寸：
```scss
svg.w-3 {
  width: 0.75rem !important;  /* 12px */
  height: 0.75rem !important;
  flex-shrink: 0;
}

svg.w-4 {
  width: 1rem !important;  /* 16px */
  height: 1rem !important;
  flex-shrink: 0;
}

svg.w-5 {
  width: 1.25rem !important;  /* 20px */
  height: 1.25rem !important;
  flex-shrink: 0;
}
```

**參考實作**：
- `frontend/pages/docs.vue:320-325`
- `frontend/pages/industry/index.vue:1052-1068`

### Vue 模板中的 Python f-string 語法錯誤

**症狀**：
- 前端編譯錯誤：`[vue/compiler-sfc] Unexpected token, expected "}"`
- 錯誤指向包含 Python f-string 的程式碼行

**根本原因**：
- Vue 單檔案組件中使用 JavaScript 模板字面值（template literals）語法：`` `code` ``
- Python f-string 中的 `${變數}` 會被 Vue 編譯器誤認為 JavaScript 模板插值
- 例如：`print(f'價格 ${order.price:.2f}')` 在模板字面值中會導致語法錯誤

**解決方案**：
在 Vue 組件的 JavaScript 模板字面值中，需要轉義所有 Python f-string 的美元符號：

```javascript
// ❌ 錯誤：Vue 編譯器會嘗試解析 ${order.price} 為 JavaScript
code: `print(f'價格 ${order.price:.2f}')`

// ❌ 也錯誤：雙反斜線會產生字面反斜線字符
code: `print(f'價格 \\${order.price:.2f}')`

// ✅ 正確：使用單反斜線轉義
code: `print(f'價格 \${order.price:.2f}')`
```

**關鍵規則**：
- 在 Vue 的 `` `模板字面值` `` 中，Python f-string 的 `$` 必須寫成 `\$`
- 使用**單反斜線** `\$`，不是雙反斜線 `\\$`
- 這只影響 `.vue` 檔案中的 `code:` 屬性，不影響 `.py` 檔案

**受影響檔案**：
- `frontend/components/StrategyTemplates.vue`
- `frontend/components/QlibStrategyTemplates.vue`

**除錯方法**：
```bash
# 檢查前端編譯錯誤
docker compose logs frontend | grep "Unexpected token"

# 搜尋未轉義的 Python f-string
grep -n 'f.*\${[^}]*}' frontend/components/*.vue
```

### 產業聚合指標計算失敗

**症狀**：
- API 返回 0 個指標
- 日誌顯示 "Calculated industry metrics for M15: 0 indicators"

**根本原因**：
- `fundamental_data` 表的 `date` 欄位使用**季度字串**（如 "2024-Q4"）
- 程式錯誤地使用 `date.today()` 查詢當天日期（如 "2025-12-03"）
- SQL WHERE 條件無法匹配：`date >= '2025-12-03'` 找不到 "2024-Q4"

**解決方案**：
```python
# ❌ 錯誤做法
metric_date = date.today()  # "2025-12-03"
data = query_fundamental_data(start_date=str(metric_date), end_date=str(metric_date))

# ✅ 正確做法
latest_quarter = db.execute(
    text("SELECT date FROM fundamental_data ORDER BY date DESC LIMIT 1")
).fetchone()[0]  # 返回 "2024-Q4"

data = db.execute(
    text("SELECT value FROM fundamental_data WHERE date = :quarter"),
    {"quarter": latest_quarter}
).fetchall()
```

**檢查資料庫季度資料**：
```bash
docker compose exec postgres psql -U quantlab quantlab -c \
  "SELECT DISTINCT date FROM fundamental_data ORDER BY date DESC LIMIT 10;"
```

**參考修復**：`backend/app/services/industry_service.py:142-244`

### 前端導航後需要重新登入

**症狀**：
- 從 API 文檔頁面返回儀表板後需要重新登入
- Authentication token 遺失

**根本原因**：
- 使用 `<a href="/path">` 觸發完整頁面重載（full page reload）
- 頁面重載清除 Vue 應用狀態和記憶體中的認證資訊
- localStorage 中的 token 仍存在，但 Pinia store 已清空

**解決方案**：
將所有內部導航連結改為 `<NuxtLink>`：
```vue
<!-- ❌ 錯誤：觸發完整頁面重載 -->
<a href="/dashboard">返回儀表板</a>

<!-- ✅ 正確：使用 Vue Router，保留應用狀態 -->
<NuxtLink to="/dashboard">返回儀表板</NuxtLink>
```

**注意事項**：
- `<NuxtLink>` 使用 Vue Router 進行客戶端路由
- 不會觸發頁面重載，保留 Pinia store 和全局狀態
- 外部連結（如 API 文檔的 Swagger/ReDoc）仍使用 `<a href>` 配合 `target="_blank"`

## 開發工作流建議

**添加新 API 端點**：
1. 在 `app/api/v1/{module}.py` 添加路由
2. 在 `app/schemas/` 創建 Pydantic Schema
3. 在 `app/services/` 實作業務邏輯
4. 在 `app/repositories/` 添加數據訪問方法
5. 測試：`pytest tests/test_{module}.py`

**添加新數據庫模型**：
1. 在 `app/models/` 創建模型類
2. 在 `app/db/base.py` 導入模型
3. 創建遷移：`docker compose exec backend alembic revision --autogenerate -m "add {table}"`
4. 檢查遷移檔案並執行：`docker compose exec backend alembic upgrade head`

**添加新 Celery 任務**：
1. 在 `app/tasks/` 創建任務函數
2. 使用 `@celery_app.task(bind=True, name="app.tasks.task_name")` 裝飾器
3. 在 `app/tasks/__init__.py` 導出新任務
4. 如需定時執行，在 `app/core/celery_app.py` 的 `beat_schedule` 添加配置
5. 重啟 worker 和 beat：`docker compose restart celery-worker celery-beat`
6. 驗證任務已註冊：`docker compose exec backend celery -A app.core.celery_app inspect registered`

**任務實作模式**：
```python
from celery import Task
from app.core.celery_app import celery_app
from loguru import logger

@celery_app.task(bind=True, name="app.tasks.my_task")
def my_task(self: Task, param1: str) -> dict:
    """任務說明"""
    try:
        logger.info(f"Starting task with {param1}")

        # 業務邏輯
        result = do_something(param1)

        logger.info("Task completed successfully")
        return {
            "status": "success",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        # 重試 3 次，每次延遲 300 秒
        raise self.retry(exc=e, countdown=300, max_retries=3)
```

## FinLab API 整合

**API Token 取得**：
1. 訪問 https://ai.finlab.tw/
2. 使用 `gameic@gmail.com` 登入
3. 複製 API Token 到 `.env` 的 `FINLAB_API_TOKEN`

**FinLab 客戶端** (`app/services/finlab_client.py`)：
```python
from app.services.finlab_client import FinLabClient

# 初始化客戶端
client = FinLabClient()

# 獲取股票清單
stocks_df = client.get_stock_list()  # 返回 2,671 檔台股

# 獲取價格數據
price_df = client.get_price(
    stock_id="2330",
    start_date="2024-01-01",
    end_date="2024-01-10"
)

# 獲取 OHLCV 數據
ohlcv_df = client.get_ohlcv(
    stock_id="2330",
    start_date="2024-01-01",
    end_date="2024-01-10"
)

# 獲取最新價格
latest_price = client.get_latest_price("2330")

# 搜尋股票
results = client.search_stocks("台積電")
```

**已實作的 API 端點**：

**股票數據** (`app/api/v1/data.py`)：
- `GET /api/v1/data/stocks` - 獲取所有股票清單
- `POST /api/v1/data/stocks/search` - 搜尋股票
- `GET /api/v1/data/price/{stock_id}` - 獲取歷史價格
- `GET /api/v1/data/ohlcv/{stock_id}` - 獲取 OHLCV 數據
- `GET /api/v1/data/latest-price/{stock_id}` - 獲取最新價格
- `DELETE /api/v1/data/cache/clear` - 清除快取

**策略管理 API** (`app/api/v1/strategies.py`)：
- `GET /api/v1/strategies/` - 獲取策略列表（支援分頁、狀態過濾）
- `POST /api/v1/strategies/` - 建立新策略（10 requests/hour 速率限制）
- `GET /api/v1/strategies/{id}` - 獲取策略詳情
- `PUT /api/v1/strategies/{id}` - 更新策略（30 requests/hour 速率限制）
- `DELETE /api/v1/strategies/{id}` - 刪除策略
- `POST /api/v1/strategies/{id}/clone` - 複製策略
- `POST /api/v1/strategies/validate` - 驗證策略代碼（20 requests/minute 速率限制）

**回測管理 API** (`app/api/v1/backtest.py`)：
- `GET /api/v1/backtest/` - 獲取回測列表（支援分頁、狀態過濾）
- `POST /api/v1/backtest/` - 建立新回測（10 requests/hour 速率限制）
- `GET /api/v1/backtest/{id}` - 獲取回測詳情
- `PUT /api/v1/backtest/{id}` - 更新回測
- `DELETE /api/v1/backtest/{id}` - 刪除回測
- `GET /api/v1/backtest/strategy/{strategy_id}` - 獲取特定策略的回測列表
- `GET /api/v1/backtest/{id}/result` - 獲取回測結果
- `POST /api/v1/backtest/run` - 執行回測（暫時停用，返回 501）

**後台管理 API** (`app/api/v1/admin.py`)：
- `GET /api/v1/admin/users` - 使用者列表（需 superuser 權限）
- `GET /api/v1/admin/users/{user_id}` - 使用者詳情
- `PATCH /api/v1/admin/users/{user_id}` - 更新使用者
- `DELETE /api/v1/admin/users/{user_id}` - 刪除使用者
- `GET /api/v1/admin/stats` - 系統統計（用戶數、策略數、資料庫大小等）
- `GET /api/v1/admin/health` - 服務健康檢查（PostgreSQL, Redis, Celery）
- `GET /api/v1/admin/sync/tasks` - 列出所有同步任務
- `POST /api/v1/admin/sync/trigger` - 手動觸發同步任務
- `GET /api/v1/admin/sync/workers` - Celery worker 資訊
- `GET /api/v1/admin/sync/active-tasks` - 當前執行中的任務
- `POST /api/v1/admin/logs/query` - 查詢應用日誌

**前端後台頁面** (`frontend/pages/admin/index.vue`)：
- 系統統計：總用戶數、活躍用戶、策略數、回測數、資料庫大小、快取大小
- 服務健康：PostgreSQL、Redis、Celery Worker 狀態監控
- 用戶管理：列表、編輯、刪除（不可刪除自己）
- 數據同步：查看定時任務、手動觸發、Celery worker 資訊
- 日誌查詢：按級別、模組、關鍵字過濾（需從主機執行 docker compose logs）

**待實作 API 模組**：
- `app/api/v1/trading.py` - 交易執行
- `app/api/v1/ai.py` - AI 策略生成

**快取系統** (`app/utils/cache.py`)：
- 使用 Redis 進行快取
- 支援 pickle 和 JSON 序列化
- 提供 `@cached` 裝飾器自動快取函數結果
- 快取效能提升約 3 倍

**速率限制** (`app/core/rate_limit.py`)：
- 使用 slowapi 套件實作速率限制
- 策略建立：10 requests/hour
- 策略更新：30 requests/hour
- 策略驗證：20 requests/minute
- 回測建立：10 requests/hour
- 回測執行：5 requests/hour
- RD-Agent 因子挖掘：3 requests/hour
- RD-Agent 策略優化：5 requests/hour
- 超過限制返回 HTTP 429 錯誤

**速率限制重置工具**（除錯專用）：
```bash
# 互動式重置（推薦）
./scripts/reset-rate-limit.sh
# 選項：
#   1) 刪除所有速率限制 keys
#   2) 僅刪除 RD-Agent 相關的 keys
#   3) 僅刪除因子挖掘 (factor-mining) keys
#   4) 僅刪除策略優化 (strategy-optimization) keys
#   5) 取消操作

# 快速重置 RD-Agent 速率限制（無互動）
./scripts/reset-rate-limit-quick.sh
```

**重要提醒**：
- 速率限制使用 Redis 持久化儲存（重啟不會重置）
- 速率限制計數器會在時間窗口結束後自動重置
- 開發/測試階段可使用重置工具快速清除限制
- 生產環境不建議手動重置速率限制

**結構化日誌** (`app/utils/logging.py`)：
- `StructuredLogger`: 帶上下文資訊的日誌記錄器
- `APILogger`: API 操作專用日誌記錄器
  - `log_operation()`: 記錄業務操作（create, update, delete 等）
  - `log_request()`: 記錄 API 請求
  - `log_response()`: 記錄 API 響應與執行時長
- 使用 `contextvars` 追蹤 request_id 和 user_id
- 所有 API 操作自動記錄上下文資訊

**配額系統** (`app/core/config.py`)：
- `MAX_STRATEGIES_PER_USER`: 50（每用戶最大策略數）
- `MAX_BACKTESTS_PER_USER`: 200（每用戶最大回測數）
- `MAX_BACKTESTS_PER_STRATEGY`: 50（每策略最大回測數）
- 超過配額返回 HTTP 429 錯誤並提供詳細說明

## 監控與日誌

**Celery 任務監控**：
```bash
# 使用監控腳本（推薦）
./monitor_celery.sh

# 實時查看日誌
docker compose logs -f celery-worker celery-beat

# 查看錯誤
docker compose logs celery-worker celery-beat | grep -i error

# 查看任務執行狀態
docker compose logs celery-worker | grep "succeeded\|failed"

# 查看特定任務
docker compose logs celery-worker | grep "sync_stock_list"

# 查看最近 1 小時的日誌
docker compose logs --since 1h celery-worker
```

**日誌級別**：
- **DEBUG**: 詳細執行信息（每筆數據處理）
- **INFO**: 任務開始/結束、統計信息
- **WARNING**: FinLab API 提示、重試警告
- **ERROR**: 任務失敗、連接錯誤

**監控重點**：
- 所有 Celery 任務都有詳細日誌（使用 loguru）
- 每個任務記錄：開始時間、處理數量、成功/失敗數、執行時長
- 錯誤會記錄完整 traceback
- 可通過 `monitor_celery.sh` 腳本快速檢查系統狀態

## 測試數據與範例

**健康檢查測試**：
```bash
curl http://localhost:8000/health
# 預期輸出：{"status":"healthy","version":"0.1.0"}

curl http://localhost:3000/
# 預期：返回 HTML 首頁
```

**API 測試範例**：
```bash
# 1. 使用者註冊
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"password123","full_name":"Test User"}'

# 2. 使用者登入（獲取 JWT token）
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123"}' \
  | jq -r '.access_token')

# 3. 獲取股票清單
curl -X GET http://localhost:8000/api/v1/data/stocks \
  -H "Authorization: Bearer $TOKEN"

# 4. 搜尋股票
curl -X POST http://localhost:8000/api/v1/data/stocks/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"keyword":"2330"}'

# 5. 獲取歷史價格
curl -X GET "http://localhost:8000/api/v1/data/price/2330?start_date=2024-01-01&end_date=2024-01-10" \
  -H "Authorization: Bearer $TOKEN"

# 6. 獲取最新價格
curl -X GET http://localhost:8000/api/v1/data/latest-price/2330 \
  -H "Authorization: Bearer $TOKEN"

# 7. 清除快取
curl -X DELETE "http://localhost:8000/api/v1/data/cache/clear?pattern=price:*" \
  -H "Authorization: Bearer $TOKEN"
```

## 使用者認證系統

**已實作的認證功能** (`app/core/security.py`、`app/api/v1/auth.py`)：
- ✅ JWT Token 管理（access token + refresh token）
- ✅ 密碼加密（bcrypt 4.0.1）
- ✅ 使用者註冊與登入
- ✅ Token 驗證與刷新

**認證 API 端點**：
- `POST /api/v1/auth/register` - 使用者註冊
- `POST /api/v1/auth/login` - 使用者登入（返回 JWT tokens）
- `POST /api/v1/auth/refresh` - 刷新 access token
- `POST /api/v1/auth/logout` - 登出
- `GET /api/v1/auth/me` - 獲取當前使用者資訊

**使用者管理 API** (`app/api/v1/users.py`)：
- `GET /api/v1/users/` - 獲取使用者列表（需管理員權限）
- `GET /api/v1/users/{user_id}` - 獲取特定使用者
- `PUT /api/v1/users/{user_id}` - 更新使用者資訊
- `DELETE /api/v1/users/{user_id}` - 刪除使用者

**架構分層**：
- `app/core/security.py` - JWT 和密碼處理
- `app/api/dependencies.py` - 認證依賴（get_current_user）
- `app/services/user_service.py` - 使用者業務邏輯
- `app/repositories/user.py` - 資料庫訪問層
- `app/schemas/user.py` - Pydantic 驗證 schemas
- `app/models/user.py` - SQLAlchemy ORM 模型

**重要注意事項**：
- bcrypt 版本必須是 4.0.1（5.0.0 有兼容性問題）
- JWT_SECRET 必須在 .env 中設定強隨機字串
- 所有受保護的 API 端點使用 `Depends(get_current_user)`

## 效能與最佳實踐

**快取策略**：
- 股票清單：24 小時快取（很少變動）
- 每日價格：10 分鐘快取（日內不變）
- 最新價格：5 分鐘快取（需頻繁更新）
- OHLCV 數據：10 分鐘快取

**資料同步策略**：
- 股票清單：每天 8:00 AM 同步一次
- 每日價格：收盤後 9:00 PM 同步
- OHLCV 數據：收盤後 10:00 PM 同步
- 即時價格：交易時段每 15 分鐘同步（9:00-13:30，週一至五）

**效能優化**：
- 使用 Redis 快取減少 API 調用（效能提升 3 倍）
- Celery worker 設定：`worker_prefetch_multiplier=1`（避免長任務阻塞）
- 任務時間限制：30 分鐘硬限制，25 分鐘軟限制
- 使用 pickle 序列化 DataFrame（比 JSON 更高效）

**安全注意事項**：
- 所有密碼使用 bcrypt 加密（cost factor 12）
- JWT token 有效期：access token 30 分鐘，refresh token 7 天
- API 端點預設需要認證（除非明確標記為 public）
- 不要在日誌中記錄敏感信息（token, password）
- 策略代碼使用 AST 解析驗證（避免代碼注入攻擊）
  - 白名單允許的模組（backtrader, pandas, numpy 等）
  - 黑名單危險函數（eval, exec, open 等）
  - 阻擋危險屬性訪問（__globals__, __code__ 等）
- 錯誤訊息環境感知（開發模式顯示詳細錯誤，生產模式顯示通用訊息）

## 開發規範

**代碼風格**：
```bash
# Python (使用 Black + Flake8)
docker compose exec backend black app/
docker compose exec backend flake8 app/ --max-line-length=88

# 類型檢查（使用 mypy）
docker compose exec backend mypy app/

# TypeScript/Vue (使用 ESLint)
docker compose exec frontend npm run lint
docker compose exec frontend npm run lint:fix
```

**Git 工作流**：
1. 從 `develop` 分支創建 feature 分支：`git checkout -b feature/your-feature`
2. 完成開發並確保測試通過
3. 提交前運行代碼格式化
4. 創建 Pull Request 到 `develop` 分支
5. Code Review 通過後合併

**Commit Message 規範**：
```
<type>(<scope>): <subject>

<body>

<footer>
```

類型（type）：
- `feat`: 新功能
- `fix`: Bug 修復
- `docs`: 文檔更新
- `style`: 代碼格式（不影響功能）
- `refactor`: 重構
- `test`: 測試相關
- `chore`: 構建/工具配置

範例：
```
feat(api): add stock recommendation endpoint

- Implement collaborative filtering algorithm
- Add caching layer for recommendations
- Create API endpoint at /api/v1/recommendations

Closes #123
```
## 前端圖表視覺化

**ECharts 整合** (`frontend/pages/backtest/[id].vue`)：

回測詳情頁面使用 ECharts 5.4.3 顯示交易記錄視覺化，關鍵實作要點：

1. **動態載入 ECharts**：
   - 使用 CDN 動態載入（避免 SSR 問題）
   - 檢查 `process.client` 確保只在客戶端運行
   - 手動觸發載入（用戶點擊按鈕）而非自動載入

2. **數據格式匹配**：
   ```javascript
   // 價格 API 返回帶時間戳的日期：'2007-05-24 00:00:00'
   // 交易數據只有日期：'2007-05-24'
   // 使用日期標準化函數統一格式
   const normalizeDateStr = (dateStr) => dateStr.split(' ')[0].split('T')[0]
   ```

3. **交易標記定位**：
   ```javascript
   // ⚠️ 重要：標記的 Y 軸使用收盤價，而非交易成交價
   const marker = {
     value: [matchingDate, priceData.data[matchingDate]],  // [日期, 收盤價]
     tradePrice: parseFloat(trade.price),  // 保存成交價用於 tooltip
     itemStyle: { color: trade.action === 'BUY' ? '#22c55e' : '#ef4444' }
   }
   ```

4. **ECharts Scatter 數據格式**：
   - ✅ 正確：`{ value: [x, y], itemStyle: {...} }`
   - ❌ 錯誤：`{ coord: [x, y], value: label }` （這是 markPoint 格式）

5. **圖表尺寸問題**：
   - 初始化和渲染後都需調用 `chartInstance.resize()`
   - 使用 `setTimeout(100ms)` 確保容器尺寸已計算完成
   - 監聽 window resize 事件自動調整

6. **智能縮放範圍**：
   - 初始視圖至少顯示 30% 數據（避免過窄）
   - 自動聚焦到交易日期範圍 ±20%
   - 提供 slider 和 inside 兩種 dataZoom 控制

**常見問題排查**：
- 標記不顯示：檢查數據格式是否使用 `value: [x, y]`
- 圖表寬度太窄：檢查容器尺寸並調用 `resize()`
- 日期匹配失敗：使用 `normalizeDateStr()` 標準化日期格式
- Y 軸位置錯誤：確認使用收盤價而非交易價

### RD-Agent 因子策略生成語法錯誤

**問題 1：Python 類別名稱以數字開頭** (`FactorStrategyTemplates.vue:415-430`)

**症狀**：
- 建立策略時出現 `invalid decimal literal` 語法錯誤
- 錯誤發生在第 3 行（class 定義）

**根本原因**：
- RD-Agent 生成的因子名稱可能以數字開頭（如 "20DaySMA"、"10DayMomentum"）
- `toPascalCase()` 函數直接轉換會產生 `class 20daysmaStrategy`
- Python 類別名稱不能以數字開頭，導致 AST 解析失敗

**解決方案**：
```javascript
// frontend/components/FactorStrategyTemplates.vue
const toPascalCase = (str: string): string => {
  let result = str
    .replace(/[^a-zA-Z0-9]/g, '_')
    .split('_')
    .filter(s => s.length > 0)
    .map(s => s.charAt(0).toUpperCase() + s.slice(1).toLowerCase())
    .join('')

  // 如果結果以數字開頭，添加 "Factor" 前綴
  if (result && /^[0-9]/.test(result)) {
    result = 'Factor' + result  // "20daysma" → "Factor20daysma" ✅
  }

  return result
}
```

**問題 2：多行代碼註解導致未縮排的函數定義** (`FactorStrategyTemplates.vue:359-363`)

**症狀**：
- 建立策略時出現 `expected an indented block after function definition on line 22`
- 錯誤通常發生在使用通用因子範本時

**根本原因**：
- `generateGenericFactorStrategy()` 嘗試將完整的 `factor.code`（多行 Python 代碼）插入到單行註解中
- 只有第一行有 `#` 註解符號，後續行變成實際的 Python 代碼：
  ```python
  def __init__(self):
      # TODO: 在此實作因子計算邏輯
      # import pandas as pd          # ← 只有這行有 #
      import numpy as np             # ← 沒有 #，變成實際代碼！❌

      def calculate_20_day_SMA(df): # ← 在 __init__ 內部定義函數！❌
          ...
  ```

**解決方案**：
移除多行代碼插入，改用簡單提示訊息：
```python
def __init__(self):
    # TODO: 在此實作因子計算邏輯
    # 完整的因子代碼請參考「自動研發」頁面的因子詳情

    self.factor_value = None  # 替換為實際因子計算
```

**參考檔案**：
- `frontend/components/FactorStrategyTemplates.vue:159-381` - 策略代碼生成邏輯
- `backend/app/services/strategy_service.py:293-362` - AST 代碼驗證
