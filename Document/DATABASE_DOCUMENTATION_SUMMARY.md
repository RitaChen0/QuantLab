# 資料庫文檔總覽

## 📚 文檔清單

我們為 QuantLab 專案建立了完整的資料庫文檔體系，確保資料庫的完整性和可維護性：

### 1. 📖 [DATABASE_SCHEMA_REPORT.md](DATABASE_SCHEMA_REPORT.md)
**完整資料庫架構報告（113 KB，10 章節）**

**內容**：
- ✅ 16 個資料表的詳細結構說明
- ✅ 所有欄位的資料型別、約束、說明
- ✅ 15 個外鍵關聯與級聯規則
- ✅ 完整的索引策略（主鍵、唯一、複合、GIN 索引）
- ✅ 10 個 Alembic 遷移歷史記錄
- ✅ TimescaleDB hypertable 配置
- ✅ 資料完整性約束與驗證 SQL
- ✅ 效能優化建議
- ✅ 備份與維護策略
- ✅ 新增資料表的完整指南

**使用時機**：
- 🔍 查詢特定資料表的結構
- 🔍 了解外鍵關聯與級聯刪除規則
- 🔍 檢查索引配置是否正確
- 🔍 參考新增資料表的標準流程
- 🔍 執行資料完整性驗證

**統計數據**（2025-12-05）：
```
總資料表數: 16
總資料大小: ~437 MB
股票數量: 2,671 檔
財務指標記錄: 1,880,982 筆
產業分類: 41 個 (TWSE)
股票-產業映射: 1,935 筆 (72.5% 覆蓋率)
```

---

### 2. 📋 [DATABASE_CHANGE_CHECKLIST.md](DATABASE_CHANGE_CHECKLIST.md)
**資料庫變更檢查清單（56 項檢查）**

**內容**：
- ✅ 變更前檢查（設計階段、相容性檢查）
- ✅ 實作階段（Model、Schema、Alembic、Repository、Service、API）
- ✅ 測試階段（單元測試、整合測試、效能測試）
- ✅ 文檔更新（必須/選擇性）
- ✅ 部署流程（部署前檢查、執行遷移、驗證）
- ✅ 部署後驗證（功能、資料完整性、效能）
- ✅ 回滾計畫（4 個步驟）
- ✅ 常見問題與解決方案

**使用時機**：
- ⚠️ **必讀**：任何資料庫 schema 變更前
- ⚠️ 新增資料表前的完整檢查
- ⚠️ 修改欄位或外鍵時的安全驗證
- ⚠️ 執行遷移前的準備工作
- ⚠️ 部署後的驗證確認

**檢查清單項目**：
```
設計階段: 16 項
實作階段: 24 項
測試階段: 8 項
文檔更新: 4 項
部署流程: 8 項
部署後驗證: 6 項
```

---

### 3. 🔗 [DATABASE_ER_DIAGRAM.md](DATABASE_ER_DIAGRAM.md)
**ER 圖與關聯關係視覺化**

**內容**：
- ✅ 文字版 ER 圖（所有關聯流程）
- ✅ 核心業務流程圖（使用者 → 策略 → 回測 → 結果/交易）
- ✅ 產業分類系統圖（TWSE 3 層階層 + FinMind 產業鏈）
- ✅ 外鍵級聯規則總覽（CASCADE vs NO ACTION）
- ✅ 索引設計圖
- ✅ 資料流向圖（回測執行、產業指標計算）
- ✅ 資料表依賴順序（建立/刪除）
- ✅ dbdiagram.io 程式碼（可直接生成視覺化 ER 圖）

**使用時機**：
- 🔍 快速理解資料表之間的關聯
- 🔍 設計新功能時規劃資料流向
- 🔍 Debug 外鍵約束問題
- 🔍 視覺化展示給團隊成員
- 🔍 新成員快速了解資料庫架構

**生成視覺化 ER 圖**：
1. 訪問 https://dbdiagram.io/
2. 複製 DATABASE_ER_DIAGRAM.md 中的 dbdiagram.io 程式碼
3. 貼到線上編輯器
4. 自動生成互動式 ER 圖
5. 可匯出為 PNG/PDF/SQL

---

## 🎯 使用指南

### 新進開發者

**第一步：了解資料庫架構**
1. 閱讀 [DATABASE_ER_DIAGRAM.md](DATABASE_ER_DIAGRAM.md) - 快速了解關聯關係
2. 瀏覽 [DATABASE_SCHEMA_REPORT.md](DATABASE_SCHEMA_REPORT.md) - 深入了解資料表結構

**第二步：執行第一次變更**
3. 詳細閱讀 [DATABASE_CHANGE_CHECKLIST.md](DATABASE_CHANGE_CHECKLIST.md)
4. 按照檢查清單逐項執行

### 經驗開發者

**日常開發**：
- 新增資料表：參考 DATABASE_SCHEMA_REPORT.md 的「新增資料表指南」
- 變更前檢查：使用 DATABASE_CHANGE_CHECKLIST.md
- 查詢關聯：參考 DATABASE_ER_DIAGRAM.md

**資料驗證**：
- 使用 DATABASE_SCHEMA_REPORT.md 的「資料驗證清單」章節
- 執行 SQL 查詢檢查孤兒記錄、唯一約束等

### 資料庫管理員

**維護任務**：
- 定期備份：使用 DATABASE_SCHEMA_REPORT.md 的「備份與維護」章節
- 效能優化：參考「效能優化」章節
- 索引檢查：參考「索引策略」章節

**問題排查**：
- 遷移失敗：查看 DATABASE_SCHEMA_REPORT.md 附錄 B「疑難排解」
- 效能問題：執行「效能檢查」SQL 查詢

---

## 📝 文檔維護規範

### 何時更新文檔？

**必須更新**（每次資料庫變更）：

1. **新增/修改資料表時**：
   - ✅ 更新 DATABASE_SCHEMA_REPORT.md 的「資料表結構詳細說明」
   - ✅ 更新 DATABASE_ER_DIAGRAM.md 的 ER 圖和 dbdiagram.io 程式碼
   - ✅ 更新 DATABASE_SCHEMA_REPORT.md 的「遷移歷史」
   - ✅ 更新統計數據（資料表數、大小）

2. **新增索引時**：
   - ✅ 更新 DATABASE_SCHEMA_REPORT.md 的「索引策略」
   - ✅ 更新 DATABASE_ER_DIAGRAM.md 的「索引設計圖」

3. **修改外鍵關聯時**：
   - ✅ 更新 DATABASE_SCHEMA_REPORT.md 的「關聯關係圖」
   - ✅ 更新 DATABASE_ER_DIAGRAM.md 的「外鍵級聯規則總覽」

4. **發現新問題時**：
   - ✅ 更新 DATABASE_CHANGE_CHECKLIST.md 的「常見問題」章節

**定期審查**（每月）：
- 📅 檢查統計數據是否準確
- 📅 驗證索引使用率
- 📅 更新資料表大小排序
- 📅 檢查文檔是否與實際資料庫一致

### 如何更新？

**步驟 1: 執行變更**
```bash
# 執行 Alembic 遷移
docker compose exec backend alembic upgrade head
```

**步驟 2: 收集資料**
```bash
# 查看資料表
docker compose exec postgres psql -U quantlab quantlab -c "\dt"

# 查看資料表大小
docker compose exec postgres psql -U quantlab quantlab -c "
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

**步驟 3: 更新文檔**
- 編輯 DATABASE_SCHEMA_REPORT.md
- 編輯 DATABASE_ER_DIAGRAM.md
- 更新版本號與日期

**步驟 4: 提交變更**
```bash
git add DATABASE_SCHEMA_REPORT.md DATABASE_ER_DIAGRAM.md
git commit -m "docs: update database documentation for [your change]"
```

---

## 🔒 資料完整性保證

### 三道防線

**第一道：設計階段**
- 使用 DATABASE_CHANGE_CHECKLIST.md 確保設計完整
- 檢查外鍵關聯是否正確
- 確認索引策略

**第二道：實作階段**
- SQLAlchemy Model 定義完整約束
- Alembic 遷移檔案手動審查
- 單元測試覆蓋 CRUD 操作

**第三道：部署後**
- 執行資料完整性驗證 SQL
- 檢查孤兒記錄
- 驗證唯一約束

### 驗證清單

定期執行以下 SQL 檢查資料完整性：

```bash
# 使用 DATABASE_SCHEMA_REPORT.md 的「資料驗證清單」
docker compose exec postgres psql -U quantlab quantlab

# 檢查孤兒記錄
# 檢查產業映射覆蓋率
# 檢查回測結果與交易記錄一致性
# 檢查財務數據季度連續性
```

---

## 🚀 快速參考

### 常見任務速查

| 任務 | 參考文檔 | 章節 |
|------|---------|------|
| 新增資料表 | DATABASE_SCHEMA_REPORT.md | 新增資料表指南 |
| 查詢資料表結構 | DATABASE_SCHEMA_REPORT.md | 資料表結構詳細說明 |
| 了解關聯關係 | DATABASE_ER_DIAGRAM.md | 核心業務流程 |
| 執行遷移 | DATABASE_CHANGE_CHECKLIST.md | 部署流程 |
| 資料驗證 | DATABASE_SCHEMA_REPORT.md | 資料驗證清單 |
| 效能優化 | DATABASE_SCHEMA_REPORT.md | 效能優化 |
| 備份還原 | DATABASE_SCHEMA_REPORT.md | 備份與維護 |
| 疑難排解 | DATABASE_SCHEMA_REPORT.md | 附錄 B |

### 關鍵檔案路徑

```
QuantLab/
├── DATABASE_SCHEMA_REPORT.md      ← 完整架構報告
├── DATABASE_CHANGE_CHECKLIST.md   ← 變更檢查清單
├── DATABASE_ER_DIAGRAM.md         ← ER 圖視覺化
├── DATABASE_MAINTENANCE.md        ← 維護指南（已存在）
├── CLAUDE.md                      ← 專案指南（已更新引用）
└── backend/
    ├── app/
    │   ├── models/                ← SQLAlchemy 模型（16 個）
    │   ├── schemas/               ← Pydantic Schemas
    │   ├── repositories/          ← 資料訪問層
    │   └── db/
    │       └── base.py            ← Base 類別與模型註冊
    └── alembic/
        └── versions/              ← 遷移檔案（10 個）
```

### 聯絡資訊

如遇問題：
1. 📖 先查閱對應文檔的「疑難排解」章節
2. 🔍 檢查日誌：`docker compose logs backend postgres`
3. 💬 團隊討論前準備：
   - 變更描述
   - 錯誤訊息
   - 已嘗試的解決方案
   - 相關遷移版本號

---

## 📊 文檔統計

### 文檔規模

| 文檔 | 大小 | 章節數 | 檢查項目 |
|------|------|--------|---------|
| DATABASE_SCHEMA_REPORT.md | ~113 KB | 10 | - |
| DATABASE_CHANGE_CHECKLIST.md | ~31 KB | 9 | 56 |
| DATABASE_ER_DIAGRAM.md | ~28 KB | 8 | - |
| **總計** | **~172 KB** | **27** | **56** |

### 涵蓋範圍

- ✅ 16 個資料表 100% 文檔化
- ✅ 15 個外鍵關聯 100% 記錄
- ✅ 10 個遷移歷史 100% 追蹤
- ✅ 56 個變更檢查項目
- ✅ 3 種 ER 圖表示（文字、視覺化、dbdiagram.io）

---

## 🎉 總結

這套資料庫文檔體系提供了：

1. **完整性** - 涵蓋所有資料表、關聯、索引、約束
2. **可操作性** - 提供檢查清單、SQL 範例、最佳實踐
3. **可維護性** - 明確的更新規範、版本追蹤
4. **易用性** - 清楚的章節分類、快速參考表、視覺化圖表

**使用建議**：
- 🔖 將此文檔加入書籤，方便快速查閱
- 📚 新進成員必讀 DATABASE_ER_DIAGRAM.md
- ⚠️ 資料庫變更前必讀 DATABASE_CHANGE_CHECKLIST.md
- 🔍 遇到問題先查 DATABASE_SCHEMA_REPORT.md

**文檔維護承諾**：
- 每次資料庫變更後 24 小時內更新文檔
- 每月審查一次文檔準確性
- 持續收集常見問題並更新

---

**文檔版本**: 1.0
**建立日期**: 2025-12-05
**下次審查**: 2026-01-05
**維護者**: Database Team

**變更記錄**:
- 2025-12-05: 建立完整資料庫文檔體系
  - DATABASE_SCHEMA_REPORT.md (113 KB, 10 章節)
  - DATABASE_CHANGE_CHECKLIST.md (31 KB, 56 項檢查)
  - DATABASE_ER_DIAGRAM.md (28 KB, 8 章節)
  - 更新 CLAUDE.md 引用
