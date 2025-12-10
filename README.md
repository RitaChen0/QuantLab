# QuantLab - 量化交易實驗室

> 開源的台股量化交易平台，整合資料分析、策略回測與自動交易

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Node](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)

## 特色功能

- 📊 **完整資料整合** - 支援 FinLab API、FinMind 等多種資料源
- 🔬 **專業回測引擎** - 精確模擬交易成本、滑價與市場衝擊
- 🤖 **AI 策略生成** - 使用 OpenAI/Claude 自動生成交易策略
- 📈 **豐富視覺化** - 互動式圖表、績效分析與風險評估
- 🔌 **券商整合** - 支援永豐證券、富果等主流券商 API
- 🐳 **容器化部署** - Docker Compose 一鍵啟動完整環境

## 快速開始

### 前置需求

- Docker & Docker Compose
- Node.js 18+（本地開發）
- Python 3.11+（本地開發）

### 使用 Docker（推薦）

```bash
# 1. Clone 專案
git clone https://github.com/yourusername/quantlab.git
cd quantlab

# 2. 設定環境變數
cp .env.example .env
# 編輯 .env 填入必要的 API Token

# 3. 啟動服務
docker-compose up -d

# 4. 執行資料庫遷移
docker-compose exec backend alembic upgrade head

# 5. 訪問應用
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

### 本地開發

#### 後端開發

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### 前端開發

```bash
cd frontend
npm install
npm run dev
```

## 專案結構

```
quantlab/
├── frontend/          # Nuxt.js 前端應用
├── backend/           # FastAPI 後端服務
├── docs/              # 專案文檔
├── scripts/           # 工具腳本
├── deployment/        # 部署配置
└── docker-compose.yml # Docker 編排文件
```

## 技術棧

### 前端
- **框架**: Nuxt.js 3 (Vue 3 + TypeScript)
- **UI**: Vuetify 3 / Element Plus
- **圖表**: Apache ECharts
- **編輯器**: Monaco Editor
- **狀態管理**: Pinia

### 後端
- **框架**: FastAPI (Python 3.11+)
- **資料庫**: PostgreSQL 15 + TimescaleDB
- **快取**: Redis 7
- **任務佇列**: Celery
- **ORM**: SQLAlchemy 2.0

### 量化核心
- **回測**: Backtrader / Qlib (Microsoft)
- **技術指標**: TA-Lib, pandas-ta
- **機器學習**: scikit-learn, LightGBM, XGBoost
- **AI 研發**: RD-Agent (Microsoft Research)

## 策略範本整合系統

QuantLab 提供三種策略範本整合模式，讓您靈活組合與擴展交易策略：

### 🔄 替換策略（完全覆蓋）
- **用途**：從頭開始創建新策略
- **行為**：完全覆蓋編輯器中的現有代碼
- **安全措施**：會提示確認以防誤操作
- **適用場景**：新手學習範本、快速測試策略想法

### ⭐ 插入因子（智慧合併，推薦）
- **用途**：為現有策略添加新的技術因子或指標
- **Backtrader 模式**：
  - 提取範本中 `__init__` 方法的因子計算邏輯
  - 智慧插入到現有策略的 `__init__` 方法末尾
  - 保留原有策略結構與交易邏輯
- **Qlib 模式**：
  - 提取範本中的 `QLIB_FIELDS` 定義
  - 合併到現有策略的 fields 陣列
  - 自動檢查重複，避免插入相同因子
- **適用場景**：策略優化、多因子組合、漸進式開發

### ➕ 追加代碼（末尾附加）
- **用途**：保留現有代碼，手動整合新邏輯
- **行為**：在代碼末尾追加完整範本（附帶註解說明）
- **適用場景**：參考學習、複雜邏輯手動整合

### 跨引擎整合

RD-Agent 生成的因子（Qlib 表達式格式）可無縫整合到兩種引擎：

- **→ Backtrader 策略**：自動轉換為 Backtrader indicators
- **→ Qlib ML 策略**：直接插入 `QLIB_FIELDS` 陣列

**範例**：RD-Agent 生成的動量因子 `($close / Ref($close, 5) - 1)`
- 在 Backtrader 中變成 `(self.data.close - self.data.close(-5)) / self.data.close(-5)`
- 在 Qlib 中保持原樣 `'($close / Ref($close, 5) - 1)'`

## 量化引擎對比

QuantLab 支援兩種互補的量化引擎，滿足不同需求：

| 維度 | Backtrader | Qlib (Microsoft) |
|------|-----------|------------------|
| **開發者** | 個人開發者 | Microsoft Research |
| **定位** | 技術分析回測框架 | AI/ML 量化研究平台 |
| **適用對象** | 個人交易者、散戶 | 機構投資者、量化團隊 |
| **主要用途** | 技術指標策略 | 機器學習策略、因子挖掘 |
| **學習曲線** | ⭐⭐ 簡單（1-2 週） | ⭐⭐⭐⭐⭐ 複雜（1-3 個月） |
| **因子/指標** | ~100 技術指標 | 158+ 量化因子（Alpha158） |
| **ML 支援** | ⚠️ 需自行整合 | ✅ 原生支援 LightGBM/XGBoost |
| **表達式引擎** | ❌ | ✅ `Mean($close, 20)` |
| **數據處理** | 中小規模 | 大規模 + 分散式 |
| **回測速度** | 快 | 超快（二進制 `.bin` 檔案） |
| **文檔完整度** | ⭐⭐⭐⭐ | ⭐⭐⭐ |

### 如何選擇？

#### ✅ 選擇 Backtrader，如果您：
- 剛開始學習量化交易
- 想快速測試一個技術指標想法
- 策略基於經典指標（MA、RSI、MACD、布林通道等）
- 不需要複雜的機器學習模型

#### ✅ 選擇 Qlib，如果您：
- 有機器學習背景或想學習 ML 策略
- 需要進行因子挖掘、多因子選股
- 處理大量股票數據（全市場回測）
- 想使用 LightGBM/XGBoost 等 ML 模型
- 研究 Alpha 因子、統計套利

### 兩者關係

**不是競爭，而是互補**：
- **Backtrader**：輕量級戰鬥機 ✈️（靈活、快速、易用）
- **Qlib**：重型轟炸機 🚀（強大、複雜、企業級）

**QuantLab 設計理念**：
- 提供兩種選擇，滿足不同需求
- 初學者從 Backtrader 開始建立基礎
- 進階用戶使用 Qlib 進行深度研究
- RD-Agent 因子兼容兩者，實現跨引擎整合

## 前端組件架構

QuantLab 前端採用組件化設計，核心範本系統包含三個主要組件：

### 1. FactorStrategyTemplates.vue - RD-Agent 因子範本

**功能**：
- 從 RD-Agent API 動態載入生成的因子
- 顯示因子卡片（名稱、公式、績效指標、標籤）
- 提供三種整合模式按鈕（替換/插入/追加）
- 自動生成 Backtrader 或 Qlib 策略代碼

**關鍵實作**：
- **因子週期提取**：`extractPeriodFromFormula()`
  - 優先從 Qlib 公式解析（如 `Ref($close, 5)` → 5 天）
  - 回退到名稱匹配（如 `"momentum_10d"` → 10 天）
  - 位置：`frontend/components/FactorStrategyTemplates.vue:132-145`

- **策略生成器**：
  - `generateSMAStrategy()` - 均線策略
  - `generateMomentumStrategy()` - 動量策略
  - `generateVolumeWeightedStrategy()` - 成交量加權策略

- **事件命名**：統一使用 `@select` 事件（而非 `@insert`）

**技術細節**：
```javascript
// Python f-string 轉義（重要！）
// Vue 模板字面值中的 ${變數} 必須寫成 \${變數}
code: `print(f'價格 \${order.price:.2f}')`  // ✅ 正確
code: `print(f'價格 ${order.price:.2f}')`   // ❌ 錯誤（Vue 編譯錯誤）
```

### 2. QlibStrategyTemplates.vue - Qlib ML 範本

**功能**：
- 9 個預設範本（均線、動量、波動率、Alpha158 等）
- 支援 LightGBM 真正 ML 訓練流程
- `QLIB_FIELDS` 智慧合併

**範本類型**：
- 基礎策略：均線交叉、動量因子、波動率突破、均值回歸、價量相關性
- 進階策略：LightGBM 預測模型、Alpha158 多因子、Alpha158 ML 特徵
- 完整 ML：Alpha158 真正 ML（修復版，包含完整訓練流程）

**整合邏輯**：
```javascript
// 模式 2：只插入 Qlib 表達式字段
const qlibFields = extractQlibFields(code)
if (existingCode.includes('QLIB_FIELDS')) {
  // 合併到現有 QLIB_FIELDS
  newStrategy.code = insertQlibFieldsIntoStrategy(existingCode, qlibFields)
} else {
  // 建立新的 QLIB_FIELDS
  newStrategy.code = qlibFields + '\n\n' + existingCode
}
```

### 3. StrategyTemplates.vue - Backtrader 範本

**功能**：
- 6 個經典技術分析策略
- 下拉選單選擇式（不同於卡片式 UI）

**範本列表**：
1. 📈 均線交叉策略 - 雙均線交叉信號
2. 📊 RSI 反轉策略 - 超買超賣反轉
3. 📉 布林通道突破策略 - 波動率突破
4. 🎯 MACD 趨勢策略 - MACD 金叉死叉
5. 🔄 多週期確認策略 - 多時間框架驗證
6. 🛡️ 停損停利策略 - 風險管理範例

### 跨組件通信

**事件流**：
```
FactorStrategyTemplates.vue
  ↓ emit('select', { code, mode, template })
strategies/index.vue
  ↓ applyFactorTemplate() / applyFactorTemplateForQlib()
newStrategy.code (更新)
```

**關鍵函數**（`frontend/pages/strategies/index.vue`）：
- `applyFactorTemplate()` - Backtrader 模式因子插入
- `applyFactorTemplateForQlib()` - Qlib 模式因子插入
- `extractFactorCalculation()` - 提取因子計算邏輯
- `insertFactorIntoStrategy()` - 插入因子到 `__init__` 方法
- `extractQlibFields()` - 提取 `QLIB_FIELDS` 定義
- `insertQlibFieldsIntoStrategy()` - 合併 Qlib 字段

## 文檔

- [安裝指南](docs/deployment/installation.md)
- [開發指南](docs/development/guide.md)
- [API 文檔](http://localhost:8000/docs)
- [架構設計](docs/development/architecture.md)

## 授權

本專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 文件

## 致謝

- 感謝 [FinLab](https://www.finlab.tw/) 提供優質的資料 API
- 靈感來源於多個開源量化交易專案

## 聯絡方式

- 問題回報：[GitHub Issues](https://github.com/yourusername/quantlab/issues)
- Email: your.email@example.com

---

**免責聲明**: 本軟體僅供教育與研究用途，不構成投資建議。使用本軟體進行交易的風險由使用者自行承擔。
