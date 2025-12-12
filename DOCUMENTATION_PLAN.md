# QuantLab 文檔規劃原則

> 📋 本文檔定義 QuantLab 專案的文檔分類、命名和維護規範

## 📂 文檔分類結構

```
QuantLab/
├── README.md                    # 專案首頁（快速開始、核心功能）
├── CLAUDE.md                    # AI 開發指南（架構、開發指令、設計決策）
├── CHANGELOG.md                 # 版本變更記錄
├── CONTRIBUTING.md              # 貢獻指南
├── docs/                        # 專題技術文檔
│   ├── QLIB.md                  # Qlib 引擎完整指南
│   ├── RDAGENT.md               # RD-Agent 完整指南
│   ├── SECURITY.md              # 安全文檔
│   ├── GUIDES.md                # 使用指南集合
│   ├── EXTERNAL_ACCESS.md       # 外部訪問配置
│   └── DOCUMENTATION_GUIDE.md   # 文檔撰寫指南
├── Document/                    # 資料庫與系統文檔
│   ├── DATABASE_*.md            # 資料庫相關（5 個檔案）
│   ├── FACTOR_EVALUATION_*.md   # 因子評估（2 個檔案）
│   ├── MIGRATION_GUIDE.md       # 系統遷移指南
│   ├── IMPROVEMENT_ROADMAP.md   # 改進路線圖
│   └── README.md                # Document 目錄索引
├── scripts/README.md            # 腳本說明
├── backend/scripts/README_IMPORT.md  # 後端腳本說明
└── monitoring/README.md         # 監控系統說明
```

## 🎯 文檔分類規則

### 1. 根目錄（4 個固定檔案）

| 檔案 | 用途 | 面向對象 |
|------|------|----------|
| **README.md** | 專案介紹、快速開始、核心命令 | 所有用戶 |
| **CLAUDE.md** | 開發指南、架構說明、常用指令 | AI 助手、開發者 |
| **CHANGELOG.md** | 版本變更記錄 | 所有用戶 |
| **CONTRIBUTING.md** | 貢獻規範 | 貢獻者 |

**原則**：
- ✅ 只放置必要的頂層文檔
- ❌ 不放置技術細節（放 docs/）
- ❌ 不放置過程記錄

### 2. docs/ 目錄（專題技術文檔）

**用途**：深入的技術文檔和使用指南

**分類**：
- **引擎文檔**：`QLIB.md`、`RDAGENT.md`（單一主題的完整指南）
- **系統文檔**：`SECURITY.md`、`EXTERNAL_ACCESS.md`
- **集合文檔**：`GUIDES.md`（多個小主題的集合）
- **元文檔**：`DOCUMENTATION_GUIDE.md`（文檔撰寫規範）

**新增規則**：
- ✅ 功能複雜度高（> 1000 行代碼）
- ✅ 需要獨立配置和使用說明
- ✅ 有專門的故障排查需求
- ❌ 小型功能（加入 `GUIDES.md`）
- ❌ 開發過程記錄

### 3. Document/ 目錄（資料庫與系統文檔）

**用途**：結構化的參考文檔

**子分類**：
- **資料庫**：`DATABASE_*.md`（5 個檔案）
  - `DATABASE_SCHEMA_REPORT.md` - 完整架構報告
  - `DATABASE_ER_DIAGRAM.md` - ER 圖
  - `DATABASE_CHANGE_CHECKLIST.md` - 變更檢查清單
  - `DATABASE_MAINTENANCE.md` - 維護指南
  - `DATABASE_DOCUMENTATION_SUMMARY.md` - 文檔摘要

- **因子評估**：`FACTOR_EVALUATION_*.md`（2 個檔案）
  - `FACTOR_EVALUATION_GUIDE.md` - 評估系統指南
  - `FACTOR_EVALUATION_UI_GUIDE.md` - UI 使用指南

- **系統管理**：
  - `MIGRATION_GUIDE.md` - 遷移與部署
  - `IMPROVEMENT_ROADMAP.md` - 改進路線圖
  - `README.md` - 目錄索引

**新增規則**：
- ✅ 資料庫相關變更
- ✅ 系統架構文檔
- ✅ 長期參考文檔
- ❌ 臨時性測試結果
- ❌ 已解決的問題記錄

### 4. 子目錄 README.md

**位置**：`scripts/`、`backend/scripts/`、`monitoring/`

**用途**：說明該目錄的腳本或工具

**內容**：
- 腳本列表與用途
- 使用範例
- 參數說明

## ❌ 絕對不應該提交的文檔類型

### 1. 開發過程記錄
**範例**：
- `*_FIX.md`（如 `DASHBOARD_REFRESH_FIX.md`）
- `*_IMPLEMENTATION.md`
- `*_TROUBLESHOOTING.md`（特定問題的排查過程）
- `*_ISSUE_RESOLVED.md`

**原因**：這些是一次性的問題解決記錄，對未來沒有參考價值

**替代方案**：
- 重要的修復說明 → 加入 `CHANGELOG.md`
- 通用故障排查 → 加入 `docs/GUIDES.md` 或相關技術文檔
- 架構決策 → 加入 `CLAUDE.md`

### 2. 遷移/升級記錄
**範例**：
- `*_MIGRATION.md`（如 `MEMBER_LEVELS_0_9_MIGRATION.md`）
- `*_UPGRADE.md`

**原因**：遷移完成後，這些記錄就過時了

**替代方案**：
- 遷移步驟 → 加入 `Document/MIGRATION_GUIDE.md`（通用遷移流程）
- 版本變更 → 加入 `CHANGELOG.md`

### 3. 臨時性文檔
**範例**：
- `TODO.md`
- `NOTES.md`
- `TEST_RESULTS.md`
- 會議記錄

**原因**：這些是短期資訊，不應該進入版本控制

**替代方案**：
- 使用 GitHub Issues
- 使用專案管理工具（Notion、Trello）
- 保留在本地或團隊 Wiki

## ✅ 文檔決策流程圖

```
需要記錄資訊？
    │
    ├─ 是否為一次性的問題修復？
    │   ├─ 是 → ❌ 不要創建 .md
    │   │       └─ 重要的 → 加入 CHANGELOG.md
    │   └─ 否 → 繼續
    │
    ├─ 是否為臨時性資訊（TODO、測試結果）？
    │   ├─ 是 → ❌ 不要提交到 Git
    │   │       └─ 使用 Issues 或保留本地
    │   └─ 否 → 繼續
    │
    ├─ 是否為小型功能說明？
    │   ├─ 是 → ✅ 加入 docs/GUIDES.md
    │   └─ 否 → 繼續
    │
    ├─ 是否為現有技術文檔的補充？
    │   ├─ 是 → ✅ 更新現有文檔
    │   │       （QLIB.md、RDAGENT.md、SECURITY.md）
    │   └─ 否 → 繼續
    │
    ├─ 是否為資料庫相關？
    │   ├─ 是 → ✅ 加入 Document/DATABASE_*.md
    │   └─ 否 → 繼續
    │
    ├─ 是否為重大新功能（> 1000 行代碼）？
    │   ├─ 是 → ✅ 在 docs/ 創建新文檔
    │   │       └─ 例如：TRADING.md
    │   └─ 否 → ⚠️ 再次考慮是否真的需要
    │
    └─ 其他情況 → 詢問團隊或參考本文檔
```

## 📝 文檔命名規範

### 檔案命名
- 使用 **UPPER_SNAKE_CASE**（全大寫 + 底線）
- 範例：`DATABASE_SCHEMA_REPORT.md`、`QLIB_SYNC_GUIDE.md`
- 例外：`README.md`、`CHANGELOG.md`、`CONTRIBUTING.md`

### 標題層級
```markdown
# 一級標題（文檔標題）- 每個檔案只有一個
## 二級標題（主要章節）
### 三級標題（子章節）
#### 四級標題（詳細說明）- 謹慎使用
```

### 內容結構
1. **標題 + 簡短描述**（2-3 行）
2. **目錄**（超過 200 行的文檔必須有）
3. **主要內容**（使用清晰的章節劃分）
4. **相關文檔連結**（文檔末尾）

## 🔄 文檔維護原則

### 1. 單一真相來源（Single Source of Truth）
- 每項資訊只在一個地方維護
- 其他地方使用交叉引用

**範例**：
```markdown
# docs/QLIB.md
## 智慧同步
詳細說明...

# CLAUDE.md
Qlib 數據同步詳見：[docs/QLIB.md](docs/QLIB.md)
```

### 2. 定期審查（每季度）
- [ ] README.md 是否反映最新功能
- [ ] CLAUDE.md 的開發指令是否準確
- [ ] 專題文檔是否有過時內容
- [ ] 是否有新功能需要文檔化
- [ ] 是否有過程性文檔可以刪除

### 3. 版本更新時
- [ ] 更新 `CHANGELOG.md`
- [ ] 更新 `README.md` 的版本號和特色功能
- [ ] 檢查所有腳本路徑是否正確
- [ ] 刪除過時的文檔

## 📊 當前文檔統計（目標）

| 位置 | 文檔數量 | 類型 |
|------|---------|------|
| 根目錄 | 4 | 核心文檔 |
| docs/ | 6 | 專題技術文檔 |
| Document/ | 10 | 資料庫與系統文檔 |
| 子目錄 | 3 | README 說明 |
| **總計** | **23** | **所有文檔** |

**原則**：保持精簡，避免超過 30 個 .md 檔案

## 🚀 實施此規劃

### 立即執行（一次性清理）
1. ✅ 刪除所有過程性文檔（`*_FIX.md`、`*_MIGRATION.md`）
2. ✅ 將有用資訊整合到對應文檔
3. ✅ 更新 `CLAUDE.md` 記錄此規劃

### 日常開發（持續執行）
- 創建新文檔前，參考本文檔的決策流程圖
- 優先更新現有文檔，而非創建新文檔
- 定期刪除過時文檔

## 📚 相關文檔

- [README.md](README.md) - 專案首頁
- [CLAUDE.md](CLAUDE.md) - 開發指南
- [docs/DOCUMENTATION_GUIDE.md](docs/DOCUMENTATION_GUIDE.md) - 文檔撰寫指南（詳細規範）
- [CHANGELOG.md](CHANGELOG.md) - 版本變更記錄

---

**創建日期**: 2025-12-12
**狀態**: ✅ 執行中
**維護者**: 開發團隊
