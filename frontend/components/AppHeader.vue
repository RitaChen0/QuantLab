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
        <div class="user-dropdown" @click="toggleDropdown" v-click-outside="closeDropdown">
          <div class="user-info">
            <span class="icon">👤</span>
            <span class="user-name">{{ userLoading ? '載入中...' : (fullName || username || '用戶') }}</span>
            <span v-if="isSuperuser" class="admin-badge">管理者</span>
            <span class="dropdown-arrow" :class="{ active: isDropdownOpen }">▼</span>
          </div>

          <transition name="dropdown">
            <div v-if="isDropdownOpen" class="dropdown-menu">
              <NuxtLink to="/account/profile" class="dropdown-item" @click="closeDropdown">
                <span class="icon">✏️</span>
                用戶編輯
              </NuxtLink>
              <NuxtLink to="/account/telegram" class="dropdown-item" @click="closeDropdown">
                <span class="icon">📱</span>
                通知設置
              </NuxtLink>
              <div class="dropdown-divider"></div>
              <button @click="handleLogout" class="dropdown-item logout-item">
                <span class="icon">🚪</span>
                登出
              </button>
            </div>
          </transition>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
const { logout } = useAuth()
const { username, fullName, isSuperuser, memberLevel, loading: userLoading } = useUserInfo()

const isDropdownOpen = ref(false)

const toggleDropdown = () => {
  isDropdownOpen.value = !isDropdownOpen.value
}

const closeDropdown = () => {
  isDropdownOpen.value = false
}

const handleLogout = () => {
  console.log('Logging out...')
  closeDropdown()
  logout()
}

// 點擊外部關閉下拉選單的指令
const vClickOutside = {
  mounted(el: any, binding: any) {
    el.clickOutsideEvent = (event: Event) => {
      if (!(el === event.target || el.contains(event.target))) {
        binding.value()
      }
    }
    document.addEventListener('click', el.clickOutsideEvent)
  },
  unmounted(el: any) {
    document.removeEventListener('click', el.clickOutsideEvent)
  }
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
  flex-direction: column;
  align-items: flex-start;
  gap: 0.25rem;
}

.logo {
  font-size: 1.25rem;
  font-weight: 700;
  color: white;
  margin: 0;
  line-height: 1;
}

.badge {
  padding: 0.2rem 0.6rem;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 0.75rem;
  font-size: 0.7rem;
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
  position: relative;
}

.user-dropdown {
  position: relative;
  cursor: pointer;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 0.5rem;
  color: white;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.3);
    border-color: rgba(255, 255, 255, 0.5);
  }

  .icon {
    font-size: 1.1rem;
  }
}

.user-name {
  font-weight: 500;
  font-size: 0.95rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 150px;
}

.admin-badge {
  padding: 0.2rem 0.6rem;
  background: rgba(255, 215, 0, 0.9);
  color: #333;
  border-radius: 0.75rem;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.5px;
  white-space: nowrap;
  flex-shrink: 0;
}

.dropdown-arrow {
  font-size: 0.7rem;
  transition: transform 0.2s;

  &.active {
    transform: rotate(180deg);
  }
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 0.5rem);
  right: 0;
  min-width: 200px;
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  z-index: 1000;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  width: 100%;
  background: none;
  border: none;
  color: #333;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;

  .icon {
    font-size: 1.1rem;
  }

  &:hover {
    background: #f5f5f5;
  }

  &.logout-item {
    color: #e74c3c;

    &:hover {
      background: #fff5f5;
    }
  }
}

.dropdown-divider {
  height: 1px;
  background: #e0e0e0;
  margin: 0.25rem 0;
}

// 下拉選單動畫
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.2s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.dropdown-enter-to,
.dropdown-leave-from {
  opacity: 1;
  transform: translateY(0);
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

  .user-info {
    padding: 0.4rem 0.8rem;

    .user-name {
      display: none;
    }
  }

  .dropdown-menu {
    min-width: 180px;
  }
}
</style>
