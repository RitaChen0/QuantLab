<template>
  <div class="dashboard-container">
    <!-- 頂部導航欄 -->
    <AppHeader />

    <!-- 主要內容區 -->
    <main class="dashboard-main">
      <div class="dashboard-page">
        <div class="page-header">
          <h1 class="page-title">儀表板總覽</h1>
          <p class="page-subtitle">歡迎回來！這是您的量化交易控制中心</p>
        </div>

        <!-- 統計卡片 -->
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-icon">📊</div>
            <div class="stat-content">
              <div class="stat-label">策略數量</div>
              <div class="stat-value">{{ stats.strategies }}</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">🔬</div>
            <div class="stat-content">
              <div class="stat-label">回測數量</div>
              <div class="stat-value">{{ stats.backtests }}</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">💰</div>
            <div class="stat-content">
              <div class="stat-label">總報酬率</div>
              <div class="stat-value">{{ stats.totalReturn }}</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">📅</div>
            <div class="stat-content">
              <div class="stat-label">最近活動</div>
              <div class="stat-value">{{ stats.lastActivity }}</div>
            </div>
          </div>
        </div>

        <!-- 快速操作 -->
        <div class="section">
          <h2 class="section-title">快速操作</h2>
          <div class="action-grid">
            <button @click="navigateTo('/strategies')" class="action-card">
              <div class="action-icon">➕</div>
              <div class="action-content">
                <h3>建立新策略</h3>
                <p>開始編寫您的交易策略</p>
              </div>
            </button>

            <button @click="navigateTo('/backtest')" class="action-card">
              <div class="action-icon">🔬</div>
              <div class="action-content">
                <h3>執行回測</h3>
                <p>測試策略的歷史表現</p>
              </div>
            </button>

            <button @click="navigateTo('/data')" class="action-card">
              <div class="action-icon">💹</div>
              <div class="action-content">
                <h3>瀏覽股票數據</h3>
                <p>查看台股即時與歷史數據</p>
              </div>
            </button>

            <button @click="navigateTo('/docs')" class="action-card">
              <div class="action-icon">📚</div>
              <div class="action-content">
                <h3>查看 API 文檔</h3>
                <p>了解 API 使用方式</p>
              </div>
            </button>
          </div>
        </div>

        <!-- 最近策略 -->
        <div class="section">
          <div class="section-header">
            <h2 class="section-title">最近策略</h2>
            <NuxtLink to="/strategies" class="btn-link">查看全部 →</NuxtLink>
          </div>

          <div v-if="loading" class="card">
            <div class="loading-state">載入中...</div>
          </div>

          <div v-else-if="recentStrategies.length === 0" class="card">
            <div class="empty-state">
              <div class="empty-icon">📊</div>
              <h3>尚無策略</h3>
              <p>開始建立您的第一個量化交易策略吧！</p>
              <button @click="navigateTo('/strategies')" class="btn-primary">
                建立策略
              </button>
            </div>
          </div>

          <div v-else class="strategies-list">
            <div
              v-for="strategy in recentStrategies"
              :key="strategy.id"
              class="strategy-item"
              @click="navigateTo(`/strategies/${strategy.id}`)"
            >
              <div class="strategy-info">
                <h3 class="strategy-name">{{ strategy.name }}</h3>
                <p class="strategy-description">
                  {{ strategy.description || '無描述' }}
                </p>
                <div class="strategy-meta">
                  <span :class="['status-badge', getStatusClass(strategy.status)]">
                    {{ getStatusText(strategy.status) }}
                  </span>
                  <span class="meta-item">
                    📅 {{ formatDate(strategy.created_at) }}
                  </span>
                </div>
              </div>
              <div class="strategy-actions">
                <span class="action-icon">→</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: 'auth' // 需要登入
})

const router = useRouter()
const { loadUserInfo } = useUserInfo()
const config = useRuntimeConfig()

// 統計數據
const stats = reactive({
  strategies: 0,
  backtests: 0,
  totalReturn: '-',
  lastActivity: '今天'
})

// 最近策略
const recentStrategies = ref([])
const loading = ref(true)

// 載入儀表板資料
const loadDashboardData = async () => {
  try {
    loading.value = true
    const token = localStorage.getItem('access_token')
    if (!token) return

    // 載入策略列表
    const strategiesRes = await fetch(
      `${config.public.apiBase}/api/v1/strategies/?limit=5`,
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    )

    if (strategiesRes.ok) {
      const strategiesData = await strategiesRes.json()
      recentStrategies.value = strategiesData.strategies || []
      stats.strategies = strategiesData.total || 0
    }

    // 載入回測列表
    const backtestsRes = await fetch(
      `${config.public.apiBase}/api/v1/backtest/?limit=1`,
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    )

    if (backtestsRes.ok) {
      const backtestsData = await backtestsRes.json()
      stats.backtests = backtestsData.total || 0
    }
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  } finally {
    loading.value = false
  }
}

// 載入用戶資訊
onMounted(() => {
  loadUserInfo()
  loadDashboardData()

  console.log('Dashboard mounted')
})

// 格式化日期
const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return '今天'
  if (diffDays === 1) return '昨天'
  if (diffDays < 7) return `${diffDays} 天前`
  return date.toLocaleDateString('zh-TW')
}

// 獲取狀態標籤
const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    DRAFT: '草稿',
    ACTIVE: '啟用',
    ARCHIVED: '已封存'
  }
  return statusMap[status] || status
}

// 獲取狀態樣式
const getStatusClass = (status: string) => {
  const classMap: Record<string, string> = {
    DRAFT: 'status-draft',
    ACTIVE: 'status-active',
    ARCHIVED: 'status-archived'
  }
  return classMap[status] || ''
}
</script>

<style scoped lang="scss">
.dashboard-container {
  min-height: 100vh;
  background: #f5f7fa;
}

.dashboard-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
}

.page-header {
  margin-bottom: 2rem;

  .page-title {
    font-size: 2rem;
    font-weight: 700;
    color: #111827;
    margin: 0 0 0.5rem 0;
  }

  .page-subtitle {
    color: #6b7280;
    font-size: 1rem;
    margin: 0;
  }
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  padding: 1.5rem;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 1rem;
  transition: transform 0.2s, box-shadow 0.2s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }

  .stat-icon {
    font-size: 2.5rem;
  }

  .stat-content {
    flex: 1;
  }

  .stat-label {
    color: #6b7280;
    font-size: 0.875rem;
    margin-bottom: 0.25rem;
  }

  .stat-value {
    font-size: 1.875rem;
    font-weight: 700;
    color: #111827;
  }
}

.section {
  margin-bottom: 2rem;

  .section-title {
    font-size: 1.5rem;
    font-weight: 600;
    color: #111827;
    margin: 0 0 1rem 0;
  }
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.action-card {
  background: white;
  padding: 1.5rem;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 1rem;
  text-align: left;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    border-color: #3b82f6;
  }

  .action-icon {
    font-size: 2.5rem;
  }

  .action-content {
    h3 {
      font-size: 1.125rem;
      font-weight: 600;
      color: #111827;
      margin: 0 0 0.25rem 0;
    }

    p {
      color: #6b7280;
      font-size: 0.875rem;
      margin: 0;
    }
  }
}

.card {
  background: white;
  padding: 2rem;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.empty-state {
  text-align: center;
  padding: 3rem 1rem;

  .empty-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
  }

  h3 {
    font-size: 1.5rem;
    font-weight: 600;
    color: #111827;
    margin: 0 0 0.5rem 0;
  }

  p {
    color: #6b7280;
    margin: 0 0 1.5rem 0;
  }

  .btn-primary {
    padding: 0.75rem 2rem;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 0.5rem;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;

    &:hover {
      background: #2563eb;
    }
  }
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.btn-link {
  color: #3b82f6;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  transition: color 0.2s;

  &:hover {
    color: #2563eb;
  }
}

.loading-state {
  text-align: center;
  padding: 3rem 1rem;
  color: #6b7280;
  font-size: 1rem;
}

.strategies-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.strategy-item {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
  padding: 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: #3b82f6;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
    transform: translateY(-2px);
  }
}

.strategy-info {
  flex: 1;
}

.strategy-name {
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 0.5rem 0;
}

.strategy-description {
  color: #6b7280;
  font-size: 0.875rem;
  margin: 0 0 0.75rem 0;
  line-height: 1.5;
}

.strategy-meta {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;

  &.status-draft {
    background: #f3f4f6;
    color: #6b7280;
  }

  &.status-active {
    background: #dcfce7;
    color: #16a34a;
  }

  &.status-archived {
    background: #fef3c7;
    color: #ca8a04;
  }
}

.meta-item {
  color: #9ca3af;
  font-size: 0.875rem;
}

.strategy-actions {
  .action-icon {
    font-size: 1.5rem;
    color: #d1d5db;
    transition: color 0.2s;
  }

  .strategy-item:hover & .action-icon {
    color: #3b82f6;
  }
}

// 響應式設計
@media (max-width: 768px) {
  .stats-grid,
  .action-grid {
    grid-template-columns: 1fr;
  }
}
</style>
