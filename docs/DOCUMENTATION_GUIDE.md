# 文檔管理指南

本指南說明 QuantLab 專案的文檔組織原則和維護規範。

## 📋 目錄

- [文檔結構](#文檔結構)
- [新增文檔規範](#新增文檔規範)
- [維護原則](#維護原則)
- [精簡歷史](#精簡歷史)

---

## 文檔結構

### 當前文檔組織（12 個核心文檔）

```
QuantLab/
├── README.md                    # 📖 專案首頁（面向用戶）
├── CLAUDE.md                    # 🤖 AI 開發指南（面向 AI 助手）
├── docs/
│   ├── GUIDES.md                # 📚 使用指南集合
│   ├── QLIB.md                  # 📊 Qlib 引擎完整指南
│   ├── SECURITY.md              # 🔒 安全文檔
│   ├── RDAGENT.md               # 🧠 RD-Agent 完整指南
│   ├── EXTERNAL_ACCESS.md       # 🌐 外部訪問配置
│   └── DOCUMENTATION_GUIDE.md   # 📝 文檔管理指南（本文件）
└── Document/
    ├── DATABASE_SCHEMA_REPORT.md        # 資料庫架構報告
    ├── DATABASE_CHANGE_CHECKLIST.md    # 變更檢查清單
    ├── DATABASE_ER_DIAGRAM.md           # ER 圖
    ├── DATABASE_MAINTENANCE.md          # 維護指南
    └── DATABASE_DOCUMENTATION_SUMMARY.md # 文檔摘要
```

### 文檔分類

#### 1. **根目錄**（2 個）
- **README.md**：專案首頁，面向終端用戶
  - 專案簡介、快速開始、技術棧
  - 策略範本整合系統說明
  - 量化引擎對比（Backtrader vs Qlib）
  - 前端組件架構

- **CLAUDE.md**：AI 開發指南，面向 AI 助手和開發者
  - 常用開發指令
  - 架構與設計模式
  - 環境變數配置
  - 故障排查
  - 開發工作流建議

#### 2. **docs/ 目錄**（6 個）
專題指南和技術文檔：

- **GUIDES.md**：使用指南集合
  - 批次同步指南
  - 手動同步指南
  - 基本面分析指南
  - 回測監控指南

- **QLIB.md**：Qlib 引擎完整指南
  - Qlib 簡介與定位
  - 數據結構（v2 官方格式）
  - 智慧同步機制
  - 策略開發範例
  - vs PostgreSQL 對比
  - 故障排查

- **SECURITY.md**：安全文檔
  - 安全原則與框架
  - 已修復的安全問題（8 個）
  - 安全最佳實踐
  - 安全監控與日誌
  - 定期安全檢查清單

- **RDAGENT.md**：RD-Agent 完整指南
  - RD-Agent 簡介
  - 環境配置（OpenAI API、Docker）
  - 功能使用（因子挖掘、策略優化）
  - 因子整合（Backtrader & Qlib）
  - Docker 依賴問題解決
  - 故障排查

- **EXTERNAL_ACCESS.md**：外部訪問配置

- **DOCUMENTATION_GUIDE.md**：文檔管理指南（本文件）

#### 3. **Document/ 目錄**（5 個）
資料庫相關文檔：

- 資料庫架構報告
- 變更檢查清單
- ER 圖
- 維護指南
- 文檔摘要

---

## 新增文檔規範

### 決策流程圖

```
需要新增文檔？
    │
    ├─ 是開發過程記錄？
    │   └─ ❌ 不要提交到 Git
    │       建議：保留在本地或 wiki
    │
    ├─ 是使用指南？
    │   └─ ✅ 加入 docs/GUIDES.md
    │       範例：新的數據同步功能、監控工具
    │
    ├─ 是 Qlib 相關？
    │   └─ ✅ 加入 docs/QLIB.md
    │       範例：新的數據格式、同步策略
    │
    ├─ 是安全相關？
    │   └─ ✅ 加入 docs/SECURITY.md
    │       範例：新的安全修復、監控機制
    │
    ├─ 是 RD-Agent 相關？
    │   └─ ✅ 加入 docs/RDAGENT.md
    │       範例：新功能、配置選項
    │
    ├─ 是資料庫相關？
    │   └─ ✅ 加入 Document/ 相應文檔
    │       範例：新資料表、Schema 變更
    │
    ├─ 是重大新功能？
    │   └─ ⚠️ 考慮在 docs/ 新增專門文檔
    │       範例：TRADING.md（實盤交易）、AI.md（AI 策略生成）
    │
    └─ 其他情況？
        └─ ⚠️ 先詢問是否真的需要
            考慮加入現有文檔或 README.md
```

### 新增文檔的標準

**只有在以下情況才新增獨立文檔**：

1. **重大功能模組**
   - 功能複雜度高（> 1000 行代碼）
   - 需要獨立的配置和使用說明
   - 有專門的故障排查需求
   - 範例：TRADING.md（實盤交易模組）

2. **獨立子系統**
   - 可以獨立運作的子系統
   - 有自己的 API 和數據流
   - 範例：AI.md（AI 策略生成系統）

3. **重要的技術決策**
   - 影響整體架構的重大決策
   - 需要長期參考的技術選型
   - 範例：ARCHITECTURE_DECISIONS.md

**不應該新增文檔的情況**：

❌ **開發過程記錄**
- 實作過程筆記
- 問題調試記錄
- 已完成的 issue 修復

❌ **臨時性文檔**
- 一次性的測試結果
- 會議記錄
- TODO 列表

❌ **可整合到現有文檔的內容**
- 功能更新（更新相應專題文檔）
- 小型功能說明（加入 GUIDES.md）
- API 文檔（更新 CLAUDE.md 或 OpenAPI）

---

## 維護原則

### 1. 單一真相來源（Single Source of Truth）

**原則**：每項資訊只在一個地方維護

**✅ 正確做法**：
```markdown
# docs/QLIB.md
## 智慧同步

使用智慧同步腳本：
\`\`\`bash
./scripts/sync-qlib-smart.sh
\`\`\`

詳細參數說明見下方...
```

**❌ 錯誤做法**：
```markdown
# docs/QLIB.md
使用 ./scripts/sync-qlib-smart.sh

# docs/GUIDES.md
使用 ./scripts/sync-qlib-smart.sh

# CLAUDE.md
使用 ./scripts/sync-qlib-smart.sh
```

**交叉引用**（允許）：
```markdown
# CLAUDE.md
Qlib 數據同步詳見：[docs/QLIB.md](docs/QLIB.md)
```

### 2. 定期審查與更新

**每季度檢查**：
- [ ] README.md 是否反映最新功能
- [ ] CLAUDE.md 的開發指令是否準確
- [ ] 專題文檔是否有過時內容
- [ ] 是否有新功能需要文檔化

**版本更新時**：
- [ ] 更新 README.md 的版本號和特色功能
- [ ] 更新 CLAUDE.md 的技術棧和架構說明
- [ ] 檢查所有腳本路徑是否正確

### 3. 保持簡潔

**每次新增內容時問自己**：
1. 這個資訊是否真的需要記錄？
2. 是否可以整合到現有文檔？
3. 一年後還會需要這個資訊嗎？

**文檔瘦身原則**：
- 移除過時的內容
- 合併重複的說明
- 刪除已解決的問題記錄
- 將開發筆記移出 Git

### 4. 面向讀者

**不同文檔面向不同讀者**：

| 文檔 | 讀者 | 風格 | 深度 |
|------|------|------|------|
| README.md | 終端用戶、新手 | 簡潔、吸引人 | 概覽 |
| CLAUDE.md | AI 助手、開發者 | 詳細、技術性 | 深入 |
| docs/GUIDES.md | 使用者 | 步驟式、實用 | 中等 |
| docs/QLIB.md | 量化研究者 | 專業、完整 | 深入 |
| docs/SECURITY.md | 開發者、維運 | 規範、清單式 | 深入 |
| docs/RDAGENT.md | AI/ML 研究者 | 詳細、範例豐富 | 深入 |

---

## 精簡歷史

### 2025-12-07：文檔大整合

**背景**：專案累積了 40 個 .md 檔案，造成維護困難、內容重複、查找不易。

**執行動作**：
1. ✅ 創建 4 個整合文檔（GUIDES.md、QLIB.md、SECURITY.md、RDAGENT.md）
2. ✅ 刪除 33 個過時/重複文檔
3. ✅ 保留 8 個核心文檔（README、CLAUDE、資料庫文檔等）

**成果**：
- 文檔數量：40 → 12（減少 70%）
- 結構清晰：根目錄 2 個、docs/ 6 個、Document/ 5 個
- 易於維護：相關內容集中，避免重複

**刪除的文檔類型**：

1. **開發過程記錄**（6 個）
   - ASYNC_BACKTEST_UPGRADE.md
   - CELERY_SYNC_ISSUE_RESOLVED.md
   - DISTRIBUTED_LOCK_IMPLEMENTATION.md
   - DUAL_CACHE_IMPLEMENTATION.md
   - INDUSTRY_PAGE_TROUBLESHOOTING.md
   - MONITORING_SYSTEM_SUMMARY.md

2. **重複/過時**（3 個）
   - DEVELOPMENT_PLAN.md
   - PROJECT_SUMMARY.md
   - WEBSITE_ANALYSIS.md

3. **已整合到 GUIDES.md**（4 個）
   - BATCH_SYNC_GUIDE.md
   - MANUAL_SYNC_GUIDE.md
   - FUNDAMENTAL_ANALYSIS_GUIDE.md
   - BACKTEST_MONITORING_GUIDE.md

4. **已整合到 QLIB.md**（9 個）
   - QLIB_INTEGRATION_COMPLETE.md
   - QLIB_INTEGRATION_DESIGN.md
   - QLIB_ML_COMPLETE.md
   - QLIB_SMART_SYNC_GUIDE.md
   - QLIB_SYNC_STRATEGIES.md
   - QLIB_EXPORT_GUIDE.md
   - QLIB_DATA_STRUCTURE.md
   - QLIB_VS_POSTGRES.md
   - QLIB_EXPORT_STATUS.md

5. **已整合到 SECURITY.md**（7 個）
   - SECURITY_AUDIT_REPORT.md
   - COMPLETE_SECURITY_FIXES.md
   - SECURITY_FIXES_SUMMARY.md
   - SECURITY_MONITORING.md
   - SECURITY_FIX_CREDENTIALS.md
   - SECURITY_FIX_QLIB_ENGINE.md
   - SECURITY_ISSUES_5-8.md

6. **已整合到 RDAGENT.md**（3 個）
   - RDAGENT_INTEGRATION_GUIDE.md
   - RDAGENT_SETUP.md
   - RDAGENT_FACTOR_EXTRACTION_FIX.md

**經驗教訓**：
- ❌ 不要將開發過程記錄提交到 Git
- ❌ 避免為每個功能創建單獨文檔
- ✅ 相關內容應整合到專題文檔
- ✅ 定期審查並精簡文檔

---

## 文檔撰寫最佳實踐

### 1. 標題結構

使用清晰的層級結構：
```markdown
# 一級標題（文檔標題）
## 二級標題（主要章節）
### 三級標題（子章節）
#### 四級標題（詳細說明）
```

### 2. 目錄

長文檔（> 200 行）應包含目錄：
```markdown
## 目錄

- [章節 1](#章節-1)
- [章節 2](#章節-2)
  - [子章節 2.1](#子章節-21)
```

### 3. 代碼塊

使用語法高亮：
````markdown
```bash
# Bash 腳本
docker compose up -d
```

```python
# Python 代碼
def hello():
    print("Hello, World!")
```
````

### 4. 交叉引用

使用相對路徑：
```markdown
詳見：[CLAUDE.md](../CLAUDE.md)
參考：[docs/QLIB.md](./QLIB.md)
```

### 5. 表格

使用 Markdown 表格：
```markdown
| 欄位 1 | 欄位 2 | 欄位 3 |
|--------|--------|--------|
| 內容 A | 內容 B | 內容 C |
```

### 6. 警告與提示

使用明確的標記：
```markdown
**⚠️ 重要**：這個操作無法復原

**✅ 建議**：使用智慧同步模式

**❌ 錯誤**：不要使用硬編碼憑證
```

---

## 快速參考

### 我應該在哪裡寫？

| 內容類型 | 目標文檔 | 範例 |
|---------|---------|------|
| 功能概述 | README.md | 新增的交易功能 |
| 開發指令 | CLAUDE.md | 新的測試指令 |
| 使用指南 | docs/GUIDES.md | 數據同步步驟 |
| Qlib 相關 | docs/QLIB.md | 新的數據格式 |
| 安全相關 | docs/SECURITY.md | 新的安全修復 |
| RD-Agent | docs/RDAGENT.md | 新的 API 參數 |
| 資料庫 | Document/ | Schema 變更 |

### 文檔更新檢查清單

提交文檔變更前，確認：
- [ ] 內容準確無誤
- [ ] 代碼範例可執行
- [ ] 路徑和連結正確
- [ ] 無拼寫和語法錯誤
- [ ] 格式一致（標題、代碼塊、列表）
- [ ] 交叉引用有效
- [ ] 沒有重複現有內容

---

## 相關文檔

- [README.md](../README.md) - 專案首頁
- [CLAUDE.md](../CLAUDE.md) - AI 開發指南
- [docs/GUIDES.md](./GUIDES.md) - 使用指南集合
- [docs/QLIB.md](./QLIB.md) - Qlib 引擎指南
- [docs/SECURITY.md](./SECURITY.md) - 安全文檔
- [docs/RDAGENT.md](./RDAGENT.md) - RD-Agent 指南
