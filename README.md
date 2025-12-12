# QuantLab - 台股量化交易平台

> 開源的台股量化交易平台，整合資料分析、策略回測與 AI 因子挖掘

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Node](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)

## 🚀 快速開始

### 1. 啟動服務

```bash
# 啟動所有服務
docker compose up -d

# 執行資料庫遷移
docker compose exec backend alembic upgrade head

# 訪問應用
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

### 2. 基本操作

```bash
# 查看服務狀態
docker compose ps

# 查看日誌
docker compose logs -f backend
docker compose logs -f frontend

# 重啟服務
docker compose restart backend

# 停止所有服務
docker compose down
```

## 📖 核心操作命令

### 資料庫管理

```bash
# 執行資料庫遷移
docker compose exec backend alembic upgrade head

# 創建新的遷移檔案
docker compose exec backend alembic revision --autogenerate -m "描述"

# 連接到 PostgreSQL
docker compose exec postgres psql -U quantlab -d quantlab
```

### Qlib 數據同步

```bash
# 智慧同步（推薦）
./scripts/sync-qlib-smart.sh

# 測試模式（10 檔）
./scripts/sync-qlib-smart.sh --test

# 同步單一股票
./scripts/sync-qlib-smart.sh --stock 2330
```

### Shioaji 分鐘線匯入

```bash
# 啟動匯入
./scripts/import_all_shioaji.sh

# 增量匯入（斷點續傳）
./scripts/import_all_shioaji.sh --incremental

# 監控進度
./scripts/monitor_shioaji_import.sh
```

### Celery 任務管理

```bash
# 查看 worker 日誌
docker compose logs -f celery-worker

# 手動觸發任務
docker compose exec backend celery -A app.core.celery_app call app.tasks.sync_stock_list

# 檢查任務狀態
docker compose exec backend celery -A app.core.celery_app inspect registered
```

### 開發工具

```bash
# Python 代碼格式化
docker compose exec backend black app/
docker compose exec backend flake8 app/ --max-line-length=88

# Vue/TypeScript 格式化
docker compose exec frontend npm run lint:fix

# 清理前端緩存
./scripts/quick-clean.sh
```

## 🏗️ 技術架構

### 核心技術棧

**前端**：Nuxt.js 3 (Vue 3 + TypeScript) + Pinia
**後端**：FastAPI (Python 3.11) + SQLAlchemy 2.0
**資料庫**：PostgreSQL 15 + TimescaleDB
**快取/任務**：Redis 7 + Celery
**量化引擎**：Qlib (Microsoft) + Backtrader + TA-Lib

### Docker 容器

- `postgres` - TimescaleDB 主數據庫
- `redis` - 緩存層 + Celery 消息代理
- `backend` - FastAPI 應用（端口 8000）
- `frontend` - Nuxt.js 應用（端口 3000）
- `celery-worker` - 異步任務處理器
- `celery-beat` - 定時任務調度器

## 📚 文檔索引

> 📁 **查看完整文檔索引**：[Document/README.md](Document/README.md) - 包含所有文檔分類與導覽

### 快速索引
- [專案結構索引](Document/PROJECT_STRUCTURE.md) - 快速定位關鍵文件與目錄
- [故障排查索引](Document/TROUBLESHOOTING.md) - 常見問題快速解決
- [API 快速參考](Document/API_QUICK_REFERENCE.md) - 所有 API 端點總覽

### 操作指南
- [詳細操作指南](Document/OPERATIONS_GUIDE.md) - 完整操作手冊
- [Qlib 同步指南](Document/QLIB_SYNC_GUIDE.md) - Qlib 數據同步詳解
- [Celery 任務管理](Document/CELERY_TASKS_GUIDE.md) - 定時任務與監控

### 開發文檔
- [開發指南](Document/DEVELOPMENT_GUIDE.md) - 開發規範與工作流
- [資料庫架構報告](Document/DATABASE_SCHEMA_REPORT.md) - 16 個資料表詳細說明
- [資料庫變更檢查清單](Document/DATABASE_CHANGE_CHECKLIST.md) - 56 項檢查
- [資料庫維護指南](Document/DATABASE_MAINTENANCE.md) - 備份與維護

### API 文檔
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🎯 核心功能

### 雙引擎架構

**Backtrader**：輕量級技術指標策略（適合初學者）
**Qlib**：企業級 ML 量化平台（適合進階用戶）

### RD-Agent AI 因子挖掘

- 使用 LLM 自動生成 Qlib 表達式因子
- 支援跨引擎整合（Backtrader / Qlib）
- 三種插入模式：替換策略、插入因子、追加代碼

### 數據來源

- **FinLab API**：台股歷史數據、基本面數據
- **Shioaji**：1 分鐘 K 線數據（2018-2025）
- **FinMind**：產業分類、財務指標

## 🔧 環境變數

```bash
# 必填
DATABASE_URL=postgresql://quantlab:quantlab2025@postgres:5432/quantlab
REDIS_URL=redis://redis:6379/0
JWT_SECRET=<強隨機字串>
FINLAB_API_TOKEN=<從 https://ai.finlab.tw/ 取得>

# 選填（AI 功能）
OPENAI_API_KEY=<RD-Agent 因子挖掘>
```

## 📊 專案結構

```
QuantLab/
├── frontend/           # Nuxt.js 前端
├── backend/            # FastAPI 後端
│   ├── app/
│   │   ├── api/v1/     # API 路由
│   │   ├── services/   # 業務邏輯
│   │   ├── models/     # ORM 模型
│   │   └── tasks/      # Celery 任務
│   └── alembic/        # 資料庫遷移
├── scripts/            # 運維腳本
├── Document/           # 文檔
└── docker-compose.yml  # Docker 編排
```

## 🛡️ 重要提醒

1. **資料庫變更**：參考 [變更檢查清單](Document/DATABASE_CHANGE_CHECKLIST.md)
2. **Qlib 數據**：使用智慧同步節省 95%+ 時間
3. **速率限制**：開發時可用 `./scripts/reset-rate-limit.sh` 重置
4. **前端緩存**：更新後執行 `./scripts/quick-clean.sh`

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## 📄 授權

MIT License - 詳見 [LICENSE](LICENSE)

## ⚠️ 免責聲明

本軟體僅供教育與研究用途，不構成投資建議。使用本軟體進行交易的風險由使用者自行承擔。
