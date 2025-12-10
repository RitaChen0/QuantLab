# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- CI/CD 自動化流程
- 監控與告警系統（Prometheus + Grafana）
- 前端測試框架（Vitest）
- 性能優化（查詢優化、快取策略）
- E2E 測試

## [0.1.0] - 2025-12-09

### Added
- **核心功能**
  - 用戶認證系統（JWT Token）
  - 策略管理（CRUD 操作）
  - 回測功能（Backtrader 引擎）
  - 數據瀏覽（台股歷史數據）
  - 產業分析（TWSE 分類 + FinMind 產業鏈）

- **量化引擎**
  - Qlib 整合（Microsoft 量化平台）
  - Backtrader 整合（技術指標策略）
  - 雙引擎架構（可切換）
  - Qlib v2 數據格式支援

- **AI 整合**
  - RD-Agent 因子挖掘（自動生成量化因子）
  - 因子評估系統（IC, ICIR, Sharpe Ratio）
  - LLM 驅動的策略優化

- **策略範本**
  - 20 個 Backtrader 策略範本（趨勢跟隨、均值回歸、機器學習）
  - 22 個 Qlib 策略範本（因子策略、ML 模型、高級策略）
  - RD-Agent 因子範本（AI 生成）

- **數據管理**
  - 定時同步股票清單（2,671 檔台股）
  - OHLCV 數據同步（Celery 定時任務）
  - 基本面數據同步（財務指標）
  - Qlib 智慧同步（增量更新）

- **前端功能**
  - 儀表板總覽
  - 策略編輯器（Monaco Editor）
  - 回測結果視覺化（ECharts）
  - 因子評估 UI
  - RD-Agent 任務管理

- **文檔**
  - 完整開發指南（CLAUDE.md）
  - 資料庫架構報告（16 個資料表）
  - 遷移指南（跨機器部署）
  - 因子評估指南
  - Qlib 整合文檔
  - RD-Agent 整合文檔

### Infrastructure
- Docker Compose 多服務編排
- PostgreSQL 15 + TimescaleDB（時序數據）
- Redis 7（快取 + 消息隊列）
- Celery（異步任務處理）
- Nginx 配置（可選）

### Security
- JWT 認證機制
- 速率限制（slowapi）
- CORS 配置
- 環境變數隔離
- 代碼驗證（AST 解析）

### Developer Experience
- 統一的用戶信息管理（useUserInfo composable）
- 結構化日誌（contextvars）
- API 自動文檔（Swagger + ReDoc）
- 開發腳本（備份、還原、清理）
- Git 版本控制

## [0.0.1] - 2025-11-XX

### Added
- 初始專案架構
- 基礎 FastAPI 後端
- 基礎 Nuxt.js 前端
- PostgreSQL 數據庫
- Docker 化部署

---

## Version History

| 版本 | 發布日期 | 主要更新 |
|------|---------|---------|
| 0.1.0 | 2025-12-09 | 完整功能發布 |
| 0.0.1 | 2025-11-XX | 初始版本 |

---

## Upgrade Guide

### 從 0.0.1 升級到 0.1.0

**數據庫遷移**:
```bash
docker compose exec backend alembic upgrade head
```

**環境變數更新**:
```bash
# 添加新的環境變數到 .env
QLIB_DATA_PATH=/data/qlib/tw_stock_v2
OPENAI_API_KEY=your_key  # 如使用 RD-Agent
```

**Qlib 數據同步**:
```bash
./scripts/sync-qlib-smart.sh
```

---

## Breaking Changes

### 0.1.0
- 無破壞性變更（新專案）

---

## Known Issues

### 0.1.0
- [ ] 前端測試覆蓋率為 0
- [ ] 缺少 CI/CD 自動化
- [ ] 缺少生產環境監控
- [ ] 部分 Qlib 策略範本需要額外依賴（XGBoost, LSTM）

---

## Contributors

感謝所有貢獻者的付出！

- [@your-username](https://github.com/your-username) - 專案維護者

---

## Support

- 📝 文檔: [Document/README.md](Document/README.md)
- 🐛 Issues: [GitHub Issues](https://github.com/your-repo/quantlab/issues)
- 💬 討論: [GitHub Discussions](https://github.com/your-repo/quantlab/discussions)
