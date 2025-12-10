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
        <div class="features-grid">
          <div class="feature-card card-primary">
            <div class="icon-wrapper">
              <div class="icon">📊</div>
            </div>
            <h3>完整資料整合</h3>
            <p>支援 FinLab API、FinMind 等多種資料源</p>
          </div>
          <div class="feature-card card-blue">
            <div class="icon-wrapper">
              <div class="icon">🔬</div>
            </div>
            <h3>專業回測引擎</h3>
            <p>精確模擬交易成本、滑價與市場衝擊</p>
          </div>
          <div class="feature-card card-purple">
            <div class="icon-wrapper">
              <div class="icon">🤖</div>
            </div>
            <h3>AI 策略生成</h3>
            <p>使用 AI 自動生成交易策略</p>
          </div>
          <div class="feature-card card-green">
            <div class="icon-wrapper">
              <div class="icon">📈</div>
            </div>
            <h3>豐富視覺化</h3>
            <p>互動式圖表、績效分析與風險評估</p>
          </div>
          <div class="feature-card card-orange">
            <div class="icon-wrapper">
              <div class="icon">🔌</div>
            </div>
            <h3>券商整合</h3>
            <p>支援永豐證券、富果等主流券商</p>
          </div>
          <div class="feature-card card-indigo">
            <div class="icon-wrapper">
              <div class="icon">🐳</div>
            </div>
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

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 320px));
  gap: 2rem;
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

.feature-card {
  background: white;
  padding: 2rem;
  border-radius: 1rem;
  border: 2px solid #e5e7eb;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
  transition: all 0.3s ease;
  text-align: center;

  &:hover {
    transform: translateY(-8px);
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
    border-color: transparent;
  }

  .icon-wrapper {
    width: 80px;
    height: 80px;
    margin: 0 auto 1.5rem;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.3s ease;
  }

  &:hover .icon-wrapper {
    transform: scale(1.1) rotate(5deg);
  }

  .icon {
    font-size: 2.5rem;
  }

  h3 {
    font-size: 1.25rem;
    font-weight: 700;
    margin-bottom: 0.75rem;
    color: #111827;
  }

  p {
    color: #6b7280;
    font-size: 0.95rem;
    line-height: 1.6;
  }

  // 卡片顏色主題
  &.card-primary {
    .icon-wrapper {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    &:hover {
      border-color: #667eea;
    }
  }

  &.card-blue {
    .icon-wrapper {
      background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
    }
    &:hover {
      border-color: #3b82f6;
    }
  }

  &.card-purple {
    .icon-wrapper {
      background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
    }
    &:hover {
      border-color: #8b5cf6;
    }
  }

  &.card-green {
    .icon-wrapper {
      background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    }
    &:hover {
      border-color: #10b981;
    }
  }

  &.card-orange {
    .icon-wrapper {
      background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    }
    &:hover {
      border-color: #f59e0b;
    }
  }

  &.card-indigo {
    .icon-wrapper {
      background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
    }
    &:hover {
      border-color: #6366f1;
    }
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
