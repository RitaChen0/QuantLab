# Code Reviewer Skill

QuantLab 專用代碼審查技能，自動檢查代碼是否符合團隊標準。

## 📖 簡介

這個技能會在你請求代碼審查時自動啟動，按照 QuantLab 的開發規範執行全面檢查。

## 🚀 使用方法

### 自動觸發

當你說以下任何一句話時，技能會自動啟動：

- "請審查這個 PR"
- "Review this code"
- "檢查這段代碼"
- "這樣寫對嗎"
- "幫我看看這個修改"
- "code review"

### 範例對話

```
你：請審查這個 PR

Claude：我會使用 code-reviewer 技能來審查您的變更。
[自動執行以下步驟]
1. 檢查 git diff 查看變更
2. 執行架構、時區、資料庫等檢查
3. 生成詳細審查報告
```

## ✅ 檢查項目

### 1. 🏗️ 架構規範（Critical）
- 四層架構是否正確（API → Service → Repository → Model）
- 無跨層調用

### 2. ⏰ 時區處理（Critical）
- DateTime 欄位使用 `timezone=True`
- 無 `datetime.utcnow`（已棄用）
- 使用 `timezone_helpers.now_utc()`

### 3. 🗄️ 資料庫變更（Critical）
- 修改 models/ 後有創建 Alembic 遷移
- 已更新 DATABASE_SCHEMA_REPORT.md

### 4. ⚙️ Celery 任務（Warning）
- 定時任務有正確的 `expires` 設置
- crontab 使用 UTC 時間

### 5. 🔒 安全性（Critical）
- 無硬編碼密鑰
- 無 SQL 注入風險
- 輸入驗證完整

### 6. 🧪 測試規範（Warning）
- 測試文件在 `backend/tests/` 下
- 有單元測試覆蓋

### 7. 📝 代碼質量（Info）
- 函數長度合理
- 命名清晰
- 無重複代碼

## 📊 審查報告格式

報告按嚴重性分類：

```markdown
## 代碼審查報告

### 🚨 Critical Issues（必須修復）
1. [檔案:行號] 問題描述
   - 建議修復：具體代碼

### ⚠️ Warnings（強烈建議修復）
1. [檔案:行號] 問題描述

### 💡 Info（最佳實踐建議）
1. [檔案:行號] 建議

### ✅ 正面評價
- 正確使用了...
```

## 📁 文件結構

```
.claude/skills/code-reviewer/
├── SKILL.md                # 主要技能文件（給 Claude 閱讀）
├── QUICK_REFERENCE.md      # 快速參考（檢查清單）
└── README.md              # 此文件（給開發者閱讀）
```

## 🔧 自定義

### 修改檢查規則

編輯 `SKILL.md`，調整各類別的檢查清單。

### 添加新檢查

在 `SKILL.md` 中新增章節，例如：

```markdown
### 🎨 H. 前端規範（Warning）

**檢查清單**：
- [ ] TypeScript strict mode
- [ ] 使用 Composables
- [ ] ...
```

### 調整嚴重性

修改檢查項目前的標籤：
- `Critical` - 阻擋合併
- `Warning` - 強烈建議
- `Info` - 最佳實踐

## 🧪 測試技能

### 驗證技能已註冊

重啟 Claude Code 後，詢問：
```
What Skills are available?
```

應該看到 `code-reviewer` 在列表中。

### 測試審查功能

創建一個測試分支：
```bash
git checkout -b test-review
echo "test" >> test.py
git add test.py
git commit -m "test"
```

然後請求審查：
```
請審查這個變更
```

## 📚 相關文檔

### 項目文檔
- [CLAUDE.md](../../../CLAUDE.md) - QuantLab 開發指南
- [Document/DATABASE_CHANGE_CHECKLIST.md](../../../Document/DATABASE_CHANGE_CHECKLIST.md)
- [Document/TIMEZONE_COMPLETE_GUIDE.md](../../../Document/TIMEZONE_COMPLETE_GUIDE.md)
- [Document/CELERY_REVOKED_TASKS_FIX.md](../../../Document/CELERY_REVOKED_TASKS_FIX.md)

### 技能文檔
- [SKILL.md](SKILL.md) - 完整審查指南
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - 快速參考

## 💡 使用技巧

### 1. 部分審查

如果只想審查特定文件：
```
請審查 backend/app/services/backtest_service.py
```

### 2. 重點檢查

如果只想檢查特定項目：
```
請檢查這段代碼的時區處理是否正確
```

### 3. 快速掃描

如果想要快速掃描：
```
快速檢查這個 PR 有沒有 Critical 問題
```

## 🔄 更新記錄

- **v1.0** (2025-12-27)
  - 初始版本
  - 包含 7 大類審查項目
  - 支援自動觸發

## 📝 待辦事項

- [ ] 添加前端（Nuxt.js）審查規則
- [ ] 添加 SQL 查詢性能檢查
- [ ] 集成 pytest 測試覆蓋率報告
- [ ] 添加自動修復建議腳本

## 🤝 貢獻

如果發現審查規則有誤或需要補充，請：

1. 編輯 `SKILL.md`
2. 更新 `QUICK_REFERENCE.md`
3. 提交 Pull Request

---

**維護者**: QuantLab 開發團隊
**版本**: 1.0
**最後更新**: 2025-12-27
