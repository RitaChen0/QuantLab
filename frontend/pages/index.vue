<template>
  <div class="home-page">
    <div class="hero-section">
      <div class="container mx-auto px-4 py-20 text-center">
        <h1 class="text-5xl font-bold mb-6">
          QuantLab
        </h1>
        <p class="text-xl text-gray-600 mb-8">
          開源的台股量化交易平台
        </p>
        <div class="flex justify-center gap-4">
          <NuxtLink to="/login" class="btn btn-primary">
            開始使用
          </NuxtLink>
          <NuxtLink to="/docs" class="btn btn-secondary">
            查看文檔
          </NuxtLink>
        </div>
      </div>
    </div>

    <div class="features-section py-20 bg-gray-50">
      <div class="container mx-auto px-4">
        <h2 class="text-3xl font-bold text-center mb-12">
          核心功能
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          <div class="feature-card">
            <div class="icon">📊</div>
            <h3>完整資料整合</h3>
            <p>支援 FinLab API、FinMind 等多種資料源</p>
          </div>
          <div class="feature-card">
            <div class="icon">🔬</div>
            <h3>專業回測引擎</h3>
            <p>精確模擬交易成本、滑價與市場衝擊</p>
          </div>
          <div class="feature-card">
            <div class="icon">🤖</div>
            <h3>AI 策略生成</h3>
            <p>使用 AI 自動生成交易策略</p>
          </div>
          <div class="feature-card">
            <div class="icon">📈</div>
            <h3>豐富視覺化</h3>
            <p>互動式圖表、績效分析與風險評估</p>
          </div>
          <div class="feature-card">
            <div class="icon">🔌</div>
            <h3>券商整合</h3>
            <p>支援永豐證券、富果等主流券商</p>
          </div>
          <div class="feature-card">
            <div class="icon">🐳</div>
            <h3>容器化部署</h3>
            <p>Docker 一鍵啟動完整環境</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'default'
})
</script>

<style scoped lang="scss">
.hero-section {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.feature-card {
  background: white;
  padding: 2rem;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  .icon {
    font-size: 3rem;
    margin-bottom: 1rem;
  }

  h3 {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
  }

  p {
    color: #6b7280;
  }
}

.btn {
  padding: 0.75rem 2rem;
  border-radius: 0.5rem;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-primary {
  background: #3b82f6;
  color: white;

  &:hover {
    background: #2563eb;
  }
}

.btn-secondary {
  background: white;
  color: #3b82f6;
  border: 2px solid #3b82f6;

  &:hover {
    background: #eff6ff;
  }
}
</style>
