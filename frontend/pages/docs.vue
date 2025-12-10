<template>
  <div class="docs-page">
    <!-- 簡化的頂部導航 -->
    <div class="top-bar">
      <div class="container mx-auto px-4">
        <div class="py-4">
          <NuxtLink to="/dashboard" class="back-button">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
            </svg>
            <span>返回儀表板</span>
          </NuxtLink>
        </div>
      </div>
    </div>

    <div class="container mx-auto px-4 py-12 max-w-6xl">
      <!-- 頁面標題 -->
      <div class="text-center mb-12">
        <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
          📚 QuantLab 開發者文檔
        </h1>
        <p class="text-xl text-gray-600">完整的 API 文檔與快速開始指南</p>
      </div>

      <!-- Hero Section - API 文檔 (最突出) -->
      <div class="hero-section mb-12">
        <div class="hero-card">
          <div class="flex items-center gap-3 mb-4">
            <div class="icon-box">
              <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
            </div>
            <div>
              <h2 class="text-3xl font-bold text-gray-800">API 文檔中心</h2>
              <p class="text-gray-600">探索完整的 REST API 端點與互動式測試環境</p>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
            <a :href="apiDocsUrl" target="_blank" class="api-button primary-api">
              <div class="flex items-center gap-3">
                <div class="api-icon">🚀</div>
                <div class="text-left">
                  <div class="font-bold text-lg">Swagger UI</div>
                  <div class="text-sm opacity-90">互動式 API 測試環境</div>
                </div>
              </div>
              <svg class="arrow-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
              </svg>
            </a>

            <a :href="redocUrl" target="_blank" class="api-button secondary-api">
              <div class="flex items-center gap-3">
                <div class="api-icon">📖</div>
                <div class="text-left">
                  <div class="font-bold text-lg">ReDoc</div>
                  <div class="text-sm opacity-90">閱讀優先的文檔介面</div>
                </div>
              </div>
              <svg class="arrow-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
              </svg>
            </a>
          </div>
        </div>
      </div>

      <!-- 快速開始指南 -->
      <div class="mb-12">
        <h2 class="text-2xl font-bold mb-6 flex items-center gap-2">
          <span class="text-3xl">🚀</span>
          快速開始
        </h2>
        <div class="steps-container">
          <div class="step-card">
            <div class="step-number">1</div>
            <div class="step-content">
              <h3 class="font-bold text-lg mb-1">註冊與登入</h3>
              <p class="text-gray-600 text-sm">建立您的 QuantLab 帳號並完成身份驗證</p>
            </div>
          </div>
          <div class="step-card">
            <div class="step-number">2</div>
            <div class="step-content">
              <h3 class="font-bold text-lg mb-1">設定 API Token</h3>
              <p class="text-gray-600 text-sm">連接您的 FinLab API 取得台股資料</p>
            </div>
          </div>
          <div class="step-card">
            <div class="step-number">3</div>
            <div class="step-content">
              <h3 class="font-bold text-lg mb-1">創建交易策略</h3>
              <p class="text-gray-600 text-sm">使用 Python 編寫您的第一個量化策略</p>
            </div>
          </div>
          <div class="step-card">
            <div class="step-number">4</div>
            <div class="step-content">
              <h3 class="font-bold text-lg mb-1">執行回測分析</h3>
              <p class="text-gray-600 text-sm">驗證策略績效並優化參數</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 核心功能 (3欄網格) -->
      <div class="mb-12">
        <h2 class="text-2xl font-bold mb-6 flex items-center gap-2">
          <span class="text-3xl">⚡</span>
          核心功能
        </h2>
        <div class="features-grid">
          <div class="feature-card">
            <div class="feature-icon">💻</div>
            <h3 class="font-bold text-lg mb-2">策略編輯器</h3>
            <p class="text-gray-600 text-sm mb-3">使用 Python 和 Backtrader 編寫專業交易策略</p>
            <ul class="text-sm text-gray-500 space-y-1">
              <li>✓ 支援完整 Python 語法</li>
              <li>✓ 內建程式碼驗證</li>
              <li>✓ 即時語法提示</li>
            </ul>
          </div>

          <div class="feature-card">
            <div class="feature-icon">🔬</div>
            <h3 class="font-bold text-lg mb-2">回測引擎</h3>
            <p class="text-gray-600 text-sm mb-3">精確模擬真實交易環境與成本</p>
            <ul class="text-sm text-gray-500 space-y-1">
              <li>✓ 手續費與證交稅</li>
              <li>✓ 滑價模擬</li>
              <li>✓ 完整績效指標</li>
            </ul>
          </div>

          <div class="feature-card">
            <div class="feature-icon">💹</div>
            <h3 class="font-bold text-lg mb-2">數據整合</h3>
            <p class="text-gray-600 text-sm mb-3">台股完整歷史數據與技術指標</p>
            <ul class="text-sm text-gray-500 space-y-1">
              <li>✓ FinLab 基本面資料</li>
              <li>✓ TA-Lib 100+ 指標</li>
              <li>✓ 即時報價整合</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- 技術支援 -->
      <div class="support-section">
        <div class="flex items-start gap-4">
          <div class="support-icon">💬</div>
          <div class="flex-1">
            <h2 class="text-2xl font-bold mb-3">需要協助？</h2>
            <p class="text-gray-600 mb-4">我們提供多種管道協助您解決問題</p>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
              <a href="https://github.com/your-repo" target="_blank" class="support-link">
                <span class="text-xl">📦</span>
                <span>GitHub</span>
              </a>
              <a href="https://discord.gg/your-invite" target="_blank" class="support-link">
                <span class="text-xl">💭</span>
                <span>Discord</span>
              </a>
              <NuxtLink to="/docs/faq" class="support-link">
                <span class="text-xl">❓</span>
                <span>FAQ</span>
              </NuxtLink>
              <a href="mailto:weiyu58@gmail.com" class="support-link">
                <span class="text-xl">📧</span>
                <span>Email</span>
              </a>
            </div>
          </div>
        </div>
      </div>

      <!-- 快速導航 -->
      <div class="mt-12 quick-nav-section">
        <h3 class="text-lg font-semibold mb-4 text-center text-gray-700">快速前往</h3>
        <div class="flex flex-wrap justify-center gap-3">
          <NuxtLink to="/dashboard" class="quick-nav-btn">
            <span>📊</span> 儀表板
          </NuxtLink>
          <NuxtLink to="/strategies" class="quick-nav-btn">
            <span>📈</span> 策略管理
          </NuxtLink>
          <NuxtLink to="/backtest" class="quick-nav-btn">
            <span>🔬</span> 回測中心
          </NuxtLink>
          <NuxtLink to="/data" class="quick-nav-btn">
            <span>💹</span> 數據瀏覽
          </NuxtLink>
          <NuxtLink to="/industry" class="quick-nav-btn">
            <span>🏭</span> 產業分析
          </NuxtLink>
          <NuxtLink to="/rdagent" class="quick-nav-btn">
            <span>🤖</span> 自動研發
          </NuxtLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const config = useRuntimeConfig()
const apiDocsUrl = `${config.public.apiBase}/docs`
const redocUrl = `${config.public.apiBase}/redoc`
</script>

<style scoped>
.docs-page {
  min-height: 100vh;
  background: linear-gradient(to bottom, #f9fafb 0%, #ffffff 100%);
}

/* 簡化的頂部導航 */
.top-bar {
  background: white;
  border-bottom: 1px solid #e5e7eb;
  position: sticky;
  top: 0;
  z-index: 50;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.back-button {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  color: white;
  border-radius: 0.5rem;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.3s;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
}

.back-button:hover {
  transform: translateX(-4px);
  box-shadow: 0 4px 8px rgba(59, 130, 246, 0.4);
}

/* Hero Section - API 文檔 */
.hero-section {
  animation: fadeInUp 0.6s ease-out;
}

.hero-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 2.5rem;
  border-radius: 1.5rem;
  box-shadow: 0 20px 40px rgba(102, 126, 234, 0.3);
  color: white;
}

.icon-box {
  width: 4rem;
  height: 4rem;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
  border-radius: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.api-button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.5rem;
  border-radius: 1rem;
  text-decoration: none;
  transition: all 0.3s;
  cursor: pointer;
}

.primary-api {
  background: white;
  color: #1f2937;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.primary-api:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
}

.secondary-api {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  color: white;
  border: 2px solid rgba(255, 255, 255, 0.3);
}

.secondary-api:hover {
  background: rgba(255, 255, 255, 0.25);
  transform: translateY(-4px);
}

.api-icon {
  font-size: 2rem;
  width: 3rem;
  height: 3rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(59, 130, 246, 0.1);
  border-radius: 0.75rem;
}

.primary-api .api-icon {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
}

.arrow-icon {
  width: 1.25rem;
  height: 1.25rem;
  flex-shrink: 0;
  opacity: 0.7;
}

/* 快速開始步驟 */
.steps-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.step-card {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  border: 2px solid #e5e7eb;
  display: flex;
  gap: 1rem;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.step-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #3b82f6 0%, #8b5cf6 100%);
  transform: scaleX(0);
  transition: transform 0.3s;
}

.step-card:hover::before {
  transform: scaleX(1);
}

.step-card:hover {
  border-color: #bfdbfe;
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(59, 130, 246, 0.15);
}

.step-number {
  width: 2.5rem;
  height: 2.5rem;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  color: white;
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 1.25rem;
  flex-shrink: 0;
}

.step-content {
  flex: 1;
}

/* 核心功能網格 */
.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 320px));
  gap: 1.5rem;
  justify-content: center;
  max-width: 1200px;
  margin: 0 auto;
}

@media (max-width: 768px) {
  .features-grid {
    grid-template-columns: 1fr;
    max-width: 400px;
  }
}

/* 核心功能卡片 */
.feature-card {
  background: white;
  padding: 2rem;
  border-radius: 1rem;
  border: 2px solid #f3f4f6;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.feature-card::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #3b82f6 0%, #8b5cf6 100%);
  transform: scaleX(0);
  transition: transform 0.3s;
}

.feature-card:hover::after {
  transform: scaleX(1);
}

.feature-card:hover {
  border-color: #e0e7ff;
  transform: translateY(-6px);
  box-shadow: 0 12px 24px rgba(59, 130, 246, 0.12);
}

.feature-icon {
  font-size: 3rem;
  width: 4rem;
  height: 4rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-radius: 1rem;
  margin-bottom: 1rem;
}

/* 技術支援區塊 */
.support-section {
  background: white;
  padding: 2rem;
  border-radius: 1.5rem;
  border: 2px solid #e5e7eb;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.support-icon {
  font-size: 3rem;
  width: 4rem;
  height: 4rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  border-radius: 1rem;
  flex-shrink: 0;
}

.support-link {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 0.75rem;
  text-decoration: none;
  color: #374151;
  font-weight: 600;
  transition: all 0.3s;
  border: 2px solid transparent;
}

.support-link:hover {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-color: #3b82f6;
  color: #2563eb;
  transform: translateY(-3px);
  box-shadow: 0 4px 8px rgba(59, 130, 246, 0.15);
}

/* 快速導航區塊 */
.quick-nav-section {
  padding: 2rem;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border-radius: 1.5rem;
  border: 2px solid #bae6fd;
}

.quick-nav-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: white;
  color: #374151;
  border: 2px solid #e5e7eb;
  border-radius: 0.75rem;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.3s;
}

.quick-nav-btn:hover {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  border-color: #3b82f6;
  color: #1e40af;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
}

.quick-nav-btn span {
  font-size: 1.25rem;
}

/* 動畫 */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
