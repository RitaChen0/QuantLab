# QuantLab 文檔中心

> 📚 **QuantLab** 台股量化交易平台完整文檔索引
>
> 📅 最後更新：2025-12-09

---

## 📖 文檔導覽

### 🚀 快速開始

| 文檔 | 說明 | 適用對象 |
|------|------|---------|
| [../README.md](../README.md) | 專案介紹與快速開始 | 所有人 |
| [../CLAUDE.md](../CLAUDE.md) | **開發指南（核心）** | 開發者 |
| [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) | 遷移指南 | 運維人員 |

---

## 🗂️ 文檔分類

### 📊 數據庫文檔

| 文檔 | 說明 | 重要性 |
|------|------|--------|
| [DATABASE_SCHEMA_REPORT.md](DATABASE_SCHEMA_REPORT.md) | 完整資料庫架構報告（16 個資料表） | ⭐⭐⭐ |
| [DATABASE_ER_DIAGRAM.md](DATABASE_ER_DIAGRAM.md) | ER 圖與關聯關係視覺化 | ⭐⭐⭐ |
| [DATABASE_CHANGE_CHECKLIST.md](DATABASE_CHANGE_CHECKLIST.md) | 資料庫變更檢查清單（56 項） | ⭐⭐⭐ |
| [DATABASE_MAINTENANCE.md](DATABASE_MAINTENANCE.md) | 數據庫維護指南 | ⭐⭐ |
| [DATABASE_DOCUMENTATION_SUMMARY.md](DATABASE_DOCUMENTATION_SUMMARY.md) | 數據庫文檔總覽 | ⭐⭐ |

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

### 🔄 遷移與部署

| 文檔 | 說明 | 重要性 |
|------|------|--------|
| [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) | 完整遷移指南（跨機器/災難恢復） | ⭐⭐⭐ |

**內容包含**：
- 📦 自動備份腳本（`backup-for-migration.sh`）
- 🚀 快速還原腳本（`restore-from-backup.sh`）
- 🔐 安全檢查清單
- 🧪 驗證測試步驟
- 🔧 常見問題排查

**適用場景**：
- 遷移到新機器
- 災難恢復
- 環境複製（開發/測試/生產）

---

## 📚 進階文檔（docs/ 目錄）

| 文檔 | 說明 |
|------|------|
| [../docs/QLIB.md](../docs/QLIB.md) | Qlib 整合文檔 |
| [../docs/RDAGENT.md](../docs/RDAGENT.md) | RD-Agent 整合文檔 |
| [../docs/SECURITY.md](../docs/SECURITY.md) | 安全指南 |
| [../docs/EXTERNAL_ACCESS.md](../docs/EXTERNAL_ACCESS.md) | 外部訪問配置 |
| [../docs/GUIDES.md](../docs/GUIDES.md) | 各類使用指南 |
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

| 類別 | 文檔數量 | 總頁數（估） |
|------|---------|-------------|
| 數據庫 | 5 | ~50 頁 |
| 因子評估 | 2 | ~20 頁 |
| 遷移部署 | 1 | ~15 頁 |
| 進階指南 | 6 | ~40 頁 |
| **總計** | **14** | **~125 頁** |

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

---

## 🔍 文檔搜尋

### 按關鍵字查找

```bash
# 搜尋所有文檔中的關鍵字
grep -r "關鍵字" Document/ docs/ *.md

# 搜尋特定主題
grep -r "PostgreSQL" Document/
grep -r "Qlib" Document/ docs/
grep -r "遷移" Document/
```

### 按主題分類

**數據相關**：
- PostgreSQL, TimescaleDB, Redis
- → `DATABASE_*.md`

**策略相關**：
- Backtrader, Qlib, 因子評估
- → `FACTOR_EVALUATION_*.md`, `docs/QLIB.md`

**AI 整合**：
- RD-Agent, OpenAI, 因子挖掘
- → `docs/RDAGENT.md`

**運維部署**：
- Docker, 遷移, 備份
- → `MIGRATION_GUIDE.md`

---

## 📝 文檔貢獻

### 撰寫新文檔

1. **確定分類**：
   - 數據庫相關 → `Document/DATABASE_*.md`
   - 使用指南 → `Document/*_GUIDE.md`
   - 技術文檔 → `docs/*.md`

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

## 🚀 新增文檔（2025-12-09）

### 改進與規劃
| 文檔 | 說明 | 重要性 |
|------|------|--------|
| [IMPROVEMENT_ROADMAP.md](IMPROVEMENT_ROADMAP.md) | 專案改進路線圖 | ⭐⭐⭐ |
| [../CHANGELOG.md](../CHANGELOG.md) | 變更日誌 | ⭐⭐⭐ |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | 貢獻指南 | ⭐⭐⭐ |

**IMPROVEMENT_ROADMAP.md 包含**:
- 📊 深度分析（8 個維度）
- 🎯 優先級分類（高/中/低）
- 📅 實施時間表（6 週計劃）
- 🎯 成功指標
- 🛠️ 立即可做的改進

**快速啟動改進**:
```bash
# 查看改進路線圖
cat Document/IMPROVEMENT_ROADMAP.md

# 查看變更日誌
cat CHANGELOG.md

# 查看貢獻指南
cat CONTRIBUTING.md
```

---

**更新記錄**: 2025-12-09 - 新增改進路線圖與貢獻指南
