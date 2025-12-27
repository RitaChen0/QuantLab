# QuantLab 文檔中心

> 📚 **QuantLab** 台股量化交易平台完整文檔索引
>
> 📅 最後更新：2025-12-23

---

## 📖 文檔導覽

### 🚀 快速開始

| 文檔 | 說明 | 適用對象 |
|------|------|---------|
| [../README.md](../README.md) | 專案介紹與快速開始 | 所有人 |
| [../CLAUDE.md](../CLAUDE.md) | **開發指南（核心）** | 開發者、AI 助手 |
| [../DOCUMENTATION_PLAN.md](../DOCUMENTATION_PLAN.md) | **文檔規劃原則** | 文檔維護者 |

---

## 🗂️ 核心文檔（長期維護）

### 📊 資料庫文檔

| 文檔 | 說明 | 重要性 |
|------|------|--------|
| [DATABASE_SCHEMA_REPORT.md](DATABASE_SCHEMA_REPORT.md) | 完整資料庫架構報告（16 個資料表） | ⭐⭐⭐ |
| [DATABASE_ER_DIAGRAM.md](DATABASE_ER_DIAGRAM.md) | ER 圖與關聯關係視覺化 | ⭐⭐⭐ |
| [DATABASE_CHANGE_CHECKLIST.md](DATABASE_CHANGE_CHECKLIST.md) | 資料庫變更檢查清單（56 項） | ⭐⭐⭐ |
| [DATABASE_MAINTENANCE.md](DATABASE_MAINTENANCE.md) | 數據庫維護指南 | ⭐⭐ |
| [DATABASE_INTEGRITY_SYSTEM.md](DATABASE_INTEGRITY_SYSTEM.md) | 資料庫完整性檢查系統 | ⭐⭐ |
| [DATABASE_INTEGRITY_COMPLETE_SUMMARY.md](DATABASE_INTEGRITY_COMPLETE_SUMMARY.md) | 資料庫完整性修復總結 | ⭐⭐ |

**使用場景**：
- 📝 添加/修改資料表前，必讀 `DATABASE_CHANGE_CHECKLIST.md`
- 🔍 查詢資料表結構，參考 `DATABASE_SCHEMA_REPORT.md`
- 🎨 理解資料表關聯，查看 `DATABASE_ER_DIAGRAM.md`

---

### 🧮 因子評估文檔

| 文檔 | 說明 | 重要性 |
|------|------|--------|
| [FACTOR_EVALUATION_GUIDE.md](FACTOR_EVALUATION_GUIDE.md) | 因子評估系統完整指南 | ⭐⭐⭐ |
| [FACTOR_EVALUATION_UI_GUIDE.md](FACTOR_EVALUATION_UI_GUIDE.md) | 因子評估 UI 使用指南 | ⭐⭐ |

**功能說明**：
- 📈 評估量化因子的預測能力（IC、ICIR、Sharpe Ratio）
- 🔬 回測因子策略效果
- 📊 視覺化因子表現

---

### 🔄 系統管理文檔

| 文檔 | 說明 | 重要性 |
|------|------|--------|
| [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) | 完整遷移指南（跨機器/災難恢復） | ⭐⭐⭐ |
| [IMPROVEMENT_ROADMAP.md](IMPROVEMENT_ROADMAP.md) | 專案改進路線圖 | ⭐⭐⭐ |

**適用場景**：
- 遷移到新機器
- 災難恢復
- 環境複製（開發/測試/生產）
- 專案規劃與改進

---

### 🛠️ 系統操作與管理

| 文檔 | 說明 | 重要性 |
|------|------|--------|
| [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md) | 完整操作手冊 | ⭐⭐⭐ |
| [DATA_SYNC_SCHEDULE.md](DATA_SYNC_SCHEDULE.md) | 數據同步排程總覽 | ⭐⭐⭐ |
| [ADMIN_PANEL_GUIDE.md](ADMIN_PANEL_GUIDE.md) | 後台管理面板使用指南 | ⭐⭐ |
| [STRATEGY_MONITORING_GUIDE.md](STRATEGY_MONITORING_GUIDE.md) | 策略實盤監控功能使用指南 | ⭐⭐ |
| [TASK_RETRY_GUIDE.md](TASK_RETRY_GUIDE.md) | 任務重試機制使用指南 | ⭐⭐ |

**功能說明**：
- 📊 數據同步排程與管理
- 🎛️ 後台管理面板操作
- 📡 策略監控與 Telegram 通知
- 🔄 任務重試與故障恢復

---

### 🔌 API 與整合文檔

| 文檔 | 說明 | 重要性 |
|------|------|--------|
| [API_DATETIME_GUIDE.md](API_DATETIME_GUIDE.md) | API 日期時間處理完整指南 | ⭐⭐⭐ |
| [API_QUICK_REFERENCE.md](API_QUICK_REFERENCE.md) | API 端點快速參考 | ⭐⭐ |
| [INSTITUTIONAL_API_GUIDE.md](INSTITUTIONAL_API_GUIDE.md) | 法人買賣超 API 使用指南 | ⭐⭐ |

**功能說明**：
- 🌐 API 日期時間參數解析與序列化規範
- 📚 API 端點快速查詢
- 💼 法人買賣超數據 API

---

### ⏰ Celery 與數據同步

| 文檔 | 說明 | 重要性 |
|------|------|--------|
| [CELERY_TASKS_GUIDE.md](CELERY_TASKS_GUIDE.md) | Celery 任務管理 | ⭐⭐⭐ |
| [QLIB_SYNC_GUIDE.md](QLIB_SYNC_GUIDE.md) | Qlib 同步詳解 | ⭐⭐⭐ |
| [SHIOAJI_SYNC_GUIDE.md](SHIOAJI_SYNC_GUIDE.md) | Shioaji 數據同步指南 | ⭐⭐ |
| [CELERY_REVOKED_TASKS_FIX.md](CELERY_REVOKED_TASKS_FIX.md) | Celery Revoked Tasks 完整解決方案 | ⭐⭐⭐ |
| [TIMEZONE_COMPLETE_GUIDE.md](TIMEZONE_COMPLETE_GUIDE.md) | 時區處理完整指南 | ⭐⭐⭐ |

**功能說明**：
- ⚙️ Celery 定時任務配置與管理
- 📊 Qlib 數據同步與優化
- 📈 Shioaji 期貨/股票數據同步
- 🔧 Celery 任務問題排查與修復
- ⏰ 系統時區統一處理規範

---

### 🛡️ 系統維護與故障恢復

| 文檔 | 說明 | 重要性 |
|------|------|--------|
| [SHUTDOWN_RECOVERY_GUIDE.md](SHUTDOWN_RECOVERY_GUIDE.md) | 系統關機恢復指南 | ⭐⭐⭐ |
| [QLIB_STRATEGY_OPTIMIZATION_GUIDE.md](QLIB_STRATEGY_OPTIMIZATION_GUIDE.md) | Qlib 策略優化指南 | ⭐⭐ |

**功能說明**：
- 🔄 系統異常關機後的恢復流程
- 📈 Qlib 策略優化與調參

---

## 📋 其他參考文檔

| 文檔 | 說明 | 狀態 |
|------|------|------|
| [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) | 開發規範與工作流 | ✅ 保留 |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | 專案結構快速查找 | ✅ 保留 |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | 常見問題快速解決 | ✅ 保留 |

---

## 📚 進階文檔（docs/ 目錄）

| 文檔 | 說明 |
|------|------|
| [../docs/QLIB.md](../docs/QLIB.md) | Qlib 引擎完整指南 |
| [../docs/RDAGENT.md](../docs/RDAGENT.md) | RD-Agent 整合文檔 |
| [../docs/SECURITY.md](../docs/SECURITY.md) | 安全指南 |
| [../docs/EXTERNAL_ACCESS.md](../docs/EXTERNAL_ACCESS.md) | 外部訪問配置 |
| [../docs/GUIDES.md](../docs/GUIDES.md) | 各類使用指南集合 |
| [../docs/DOCUMENTATION_GUIDE.md](../docs/DOCUMENTATION_GUIDE.md) | 文檔撰寫指南 |

---

## 🛠️ 開發工作流

### 新功能開發
```
1. 閱讀 CLAUDE.md（開發指南）
2. 如涉及數據庫變更 → DATABASE_CHANGE_CHECKLIST.md
3. 開發完成後更新相關文檔
```

### 數據庫修改
```
1. 必讀：DATABASE_CHANGE_CHECKLIST.md
2. 參考：DATABASE_SCHEMA_REPORT.md（現有架構）
3. 創建 Alembic 遷移腳本
4. 測試並更新 ER 圖
```

### 系統遷移
```
1. 閱讀：MIGRATION_GUIDE.md
2. 執行：scripts/backup-for-migration.sh
3. 傳輸備份到新機器
4. 執行：scripts/restore-from-backup.sh
5. 驗證測試
```

### 因子研究
```
1. 閱讀：FACTOR_EVALUATION_GUIDE.md
2. 使用 RD-Agent 生成因子（docs/RDAGENT.md）
3. 評估因子表現（FACTOR_EVALUATION_UI_GUIDE.md）
4. 整合到策略
```

---

## 📊 文檔統計

### 核心文檔（長期維護）
| 類別 | 文檔數量 |
|------|---------|
| 資料庫 | 6 |
| 因子評估 | 2 |
| 系統管理 | 2 |
| 系統操作與管理 | 5 |
| API 與整合 | 3 |
| Celery 與數據同步 | 5 |
| 系統維護與故障恢復 | 2 |
| 其他參考 | 3 |
| 索引 | 1 |
| **小計** | **29** |

### 總計
| 類別 | 文檔數量 |
|------|---------|
| Document/ 目錄 | 30 |
| docs/ 目錄 | 6 |
| 根目錄 | 4 |
| **總計** | **40** |

---

## 🎯 常用查詢

### "我想要..."

| 需求 | 參考文檔 |
|------|---------|
| 快速上手開發 | [CLAUDE.md](../CLAUDE.md) |
| 了解資料表結構 | [DATABASE_SCHEMA_REPORT.md](DATABASE_SCHEMA_REPORT.md) |
| 修改數據庫 | [DATABASE_CHANGE_CHECKLIST.md](DATABASE_CHANGE_CHECKLIST.md) |
| 遷移到新機器 | [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) |
| 評估量化因子 | [FACTOR_EVALUATION_GUIDE.md](FACTOR_EVALUATION_GUIDE.md) |
| 配置外部訪問 | [../docs/EXTERNAL_ACCESS.md](../docs/EXTERNAL_ACCESS.md) |
| 使用 Qlib | [../docs/QLIB.md](../docs/QLIB.md) |
| 使用 RD-Agent | [../docs/RDAGENT.md](../docs/RDAGENT.md) |
| 解決 Celery 任務問題 | [CELERY_REVOKED_TASKS_FIX.md](CELERY_REVOKED_TASKS_FIX.md) |
| 處理時區問題 | [TIMEZONE_COMPLETE_GUIDE.md](TIMEZONE_COMPLETE_GUIDE.md) |
| 系統關機恢復 | [SHUTDOWN_RECOVERY_GUIDE.md](SHUTDOWN_RECOVERY_GUIDE.md) |
| 優化 Qlib 策略 | [QLIB_STRATEGY_OPTIMIZATION_GUIDE.md](QLIB_STRATEGY_OPTIMIZATION_GUIDE.md) |
| 查看變更記錄 | [../CHANGELOG.md](../CHANGELOG.md) |

---

## 🔍 文檔搜尋

### 按關鍵字查找

```bash
# 搜尋所有文檔中的關鍵字
grep -r "關鍵字" Document/ ../docs/ ../*.md

# 搜尋特定主題
grep -r "PostgreSQL" Document/
grep -r "Qlib" Document/ ../docs/
grep -r "遷移" Document/
```

---

## 📝 文檔貢獻

### 創建新文檔前

1. **閱讀規劃原則**：[DOCUMENTATION_PLAN.md](../DOCUMENTATION_PLAN.md)
2. **檢查決策流程圖**：確認是否真的需要新文檔
3. **優先更新現有文檔**：而非創建新文檔

### 撰寫新文檔

1. **確定分類**：
   - 資料庫相關 → `Document/DATABASE_*.md`
   - 使用指南 → `docs/GUIDES.md`（集合文檔）
   - 重大功能 → `docs/` 新文檔

2. **遵循格式**：
   - 參考 `docs/DOCUMENTATION_GUIDE.md`
   - 使用 Markdown 格式
   - 包含目錄（TOC）

3. **更新索引**：
   - 在本文件（README.md）中添加連結
   - 更新相關文檔的交叉引用

---

## 🔗 相關資源

### 外部文檔
- [Qlib 官方文檔](https://qlib.readthedocs.io/)
- [Backtrader 官方文檔](https://www.backtrader.com/docu/)
- [FastAPI 官方文檔](https://fastapi.tiangolo.com/)
- [Nuxt.js 官方文檔](https://nuxt.com/)

### 專案資源
- GitHub Repository: [QuantLab](https://github.com/your-repo/quantlab)
- API 文檔: http://localhost:8000/docs
- 前端應用: http://localhost:3000

---

## 📞 支援與反饋

### 遇到問題？

1. **查閱相關文檔**（使用上方查詢表）
2. **檢查日誌**：`docker compose logs -f`
3. **查看 CLAUDE.md 的常見問題排查章節**
4. **提交 GitHub Issue**

### 文檔改進建議

如果發現文檔有誤或需要補充：
- 提交 Pull Request
- 或在 GitHub Issues 反饋

---

**💡 提示**: 建議先閱讀 [CLAUDE.md](../CLAUDE.md) 了解專案整體架構，再根據需求查閱相關文檔。

---

**更新記錄**:
- 2025-12-27 - 文檔整理完成：移除 14 個過程文件，移動 4 個重要文檔到 Document/，更新所有交叉引用
- 2025-12-23 - 文檔整合與清理：移除 47 個過程文件，整合時區相關指南，新增 API 與操作文檔分類
- 2025-12-12 - 重新規劃文檔結構，標示核心文檔與待整合文檔
- 2025-12-09 - 新增改進路線圖與貢獻指南
