<template>
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
        <NuxtLink to="/strategies" class="nav-link">
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
        <!-- 管理者專屬連結 -->
        <NuxtLink v-if="isSuperuser" to="/admin" class="nav-link admin-link">
          <span class="icon">⚙️</span>
          後台管理
        </NuxtLink>
      </nav>

      <div class="user-section">
        <div class="user-info">
          <span class="user-name">{{ userLoading ? '載入中...' : (fullName || username || '用戶') }}</span>
          <span v-if="isSuperuser" class="admin-badge">管理者</span>
        </div>
        <button @click="handleLogout" class="btn-logout">
          <span class="icon">🚪</span>
          登出
        </button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
const { logout } = useAuth()
const { username, fullName, isSuperuser, loading: userLoading } = useUserInfo()

const handleLogout = () => {
  console.log('Logging out...')
  logout()
}
</script>

<style scoped lang="scss">
.dashboard-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 100;
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
  gap: 0.75rem;
}

.logo {
  font-size: 1.5rem;
  font-weight: 700;
  color: white;
  margin: 0;
}

.badge {
  padding: 0.25rem 0.75rem;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 1rem;
  font-size: 0.75rem;
  color: white;
  font-weight: 500;
}

.nav-links {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  overflow-x: auto;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  color: rgba(255, 255, 255, 0.9);
  text-decoration: none;
  border-radius: 0.5rem;
  font-size: 0.9rem;
  font-weight: 500;
  white-space: nowrap;
  transition: all 0.2s;

  .icon {
    font-size: 1.1rem;
  }

  &:hover {
    background: rgba(255, 255, 255, 0.15);
    color: white;
  }

  &.active,
  &.router-link-active {
    background: rgba(255, 255, 255, 0.25);
    color: white;
    font-weight: 600;
  }

  &.admin-link {
    border: 1px solid rgba(255, 255, 255, 0.3);
    background: rgba(255, 255, 255, 0.1);

    &:hover {
      background: rgba(255, 255, 255, 0.2);
      border-color: rgba(255, 255, 255, 0.5);
    }

    &.router-link-active {
      background: rgba(255, 255, 255, 0.3);
      border-color: white;
    }
  }
}

.user-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: white;
}

.user-name {
  font-weight: 500;
  font-size: 0.95rem;
}

.admin-badge {
  padding: 0.2rem 0.6rem;
  background: rgba(255, 215, 0, 0.9);
  color: #333;
  border-radius: 0.75rem;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.btn-logout {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 0.5rem;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  .icon {
    font-size: 1.1rem;
  }

  &:hover {
    background: rgba(255, 255, 255, 0.3);
    border-color: rgba(255, 255, 255, 0.5);
  }
}

@media (max-width: 1200px) {
  .header-content {
    flex-wrap: wrap;
  }

  .nav-links {
    order: 3;
    width: 100%;
  }
}

@media (max-width: 768px) {
  .header-content {
    padding: 1rem;
  }

  .logo {
    font-size: 1.25rem;
  }

  .badge {
    font-size: 0.7rem;
  }

  .nav-link {
    padding: 0.4rem 0.8rem;
    font-size: 0.85rem;

    .icon {
      font-size: 1rem;
    }
  }

  .user-name {
    display: none;
  }

  .btn-logout {
    padding: 0.4rem 0.8rem;
    font-size: 0.85rem;
  }
}
</style>
