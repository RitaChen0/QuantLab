<template>
  <div class="dashboard-container">
    <!-- 頂部導航欄 -->
    <header class="dashboard-header">
      <div class="header-content">
        <div class="logo-section">
          <h1 class="logo">QuantLab</h1>
          <span class="badge">量化交易實驗室</span>
        </div>

        <nav class="nav-links">
          <NuxtLink to="/dashboard" class="nav-link">
            <span class="icon">📊</span>
            儀表板
          </NuxtLink>
          <NuxtLink to="/strategies" class="nav-link active">
            <span class="icon">📈</span>
            策略管理
          </NuxtLink>
          <NuxtLink to="/backtest" class="nav-link">
            <span class="icon">🔬</span>
            回測中心
          </NuxtLink>
          <NuxtLink to="/data" class="nav-link">
            <span class="icon">💹</span>
            數據瀏覽
          </NuxtLink>
          <NuxtLink to="/industry" class="nav-link">
            <span class="icon">🏭</span>
            產業分析
          </NuxtLink>
          <NuxtLink to="/rdagent" class="nav-link">
            <span class="icon">🤖</span>
            自動研發
          </NuxtLink>
          <NuxtLink to="/docs" class="nav-link">
            <span class="icon">📚</span>
            API 文檔
          </NuxtLink>
        </nav>

        <div class="user-section">
          <div class="user-info">
            <span class="user-name">{{ userLoading ? '載入中...' : (fullName || username || '用戶') }}</span>
          </div>
          <button @click="handleLogout" class="btn-logout">
            <span class="icon">🚪</span>
            登出
          </button>
        </div>
      </div>
    </header>

    <!-- 主要內容區 -->
    <main class="dashboard-main">
      <div class="page-container">
        <!-- 使用共享的 StrategyEditor 組件 -->
        <StrategyEditor :strategy-id="route.params.id" />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: 'auth'
})

const route = useRoute()
const { logout } = useAuth()
const { username, fullName, loading: userLoading, loadUserInfo } = useUserInfo()

// 登出
const handleLogout = () => {
  logout()
}

// 載入資料
onMounted(() => {
  loadUserInfo()
})
</script>

<style scoped lang="scss">
.dashboard-container {
  min-height: 100vh;
  background: #f5f7fa;
}

.dashboard-header {
  background: white;
  border-bottom: 1px solid #e5e7eb;
  position: sticky;
  top: 0;
  z-index: 50;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 1rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 1rem;

  .logo {
    font-size: 1.5rem;
    font-weight: 700;
    color: #3b82f6;
    margin: 0;
  }

  .badge {
    background: #dbeafe;
    color: #1e40af;
    padding: 0.25rem 0.75rem;
    border-radius: 1rem;
    font-size: 0.75rem;
    font-weight: 500;
  }
}

.nav-links {
  display: flex;
  gap: 0.5rem;
  flex: 1;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  color: #6b7280;
  text-decoration: none;
  font-weight: 500;
  transition: all 0.2s;

  .icon {
    font-size: 1.25rem;
  }

  &:hover {
    background: #f3f4f6;
    color: #111827;
  }

  &.active {
    background: #dbeafe;
    color: #1e40af;
  }
}

.user-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.user-info {
  .user-name {
    font-weight: 500;
    color: #111827;
  }
}

.btn-logout {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: #fee2e2;
  color: #991b1b;
  border: none;
  border-radius: 0.5rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;

  .icon {
    font-size: 1.25rem;
  }

  &:hover {
    background: #fecaca;
  }
}

.dashboard-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
}

.page-container {
  width: 100%;
}

// 響應式
@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    align-items: stretch;
  }

  .nav-links {
    flex-direction: column;
  }
}
</style>
