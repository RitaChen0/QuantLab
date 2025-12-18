<template>
  <div class="dashboard-container">
    <!-- 頂部導航欄 -->
    <AppHeader />

    <!-- 主要內容區 -->
    <main class="dashboard-main">
      <div class="dashboard-page">
        <div class="page-header">
          <h1 class="page-title">儀表板總覽</h1>
          <p class="page-subtitle">
            <template v-if="!initialized">歡迎回來，載入中...！這是您的量化交易控制中心</template>
            <template v-else>歡迎回來，{{ fullName || username || '用戶' }}！這是您的量化交易控制中心</template>
          </p>
        </div>

        <!-- 統計卡片 -->
        <div class="stats-grid">
          <!-- 會員等級卡片 -->
          <div class="stat-card membership-card" :class="`level-${membershipInfo.member_level}`">
            <div class="stat-icon">{{ getMembershipIcon(membershipInfo.member_level) }}</div>
            <div class="stat-content">
              <div class="stat-label">會員等級</div>
              <div class="stat-value">{{ membershipInfo.level_name || '載入中...' }}</div>
              <div class="stat-extra">Level {{ membershipInfo.member_level }}</div>
            </div>
          </div>

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
              <div class="stat-label">帳戶餘額</div>
              <div class="stat-value">${{ membershipInfo.cash || '0.00' }}</div>
              <div class="stat-extra">信用: {{ membershipInfo.credit || '0.00' }}</div>
            </div>
          </div>
        </div>

        <!-- Rate Limit 使用情況 -->
        <div class="section">
          <h2 class="section-title">API 使用情況</h2>
          <div class="rate-limit-grid">
            <div
              v-for="(limit, key) in selectedRateLimits"
              :key="key"
              class="rate-limit-card"
            >
              <div class="limit-header">
                <span class="limit-name">{{ limit.name }}</span>
                <span class="limit-value">{{ limit.limit }}</span>
              </div>
              <div class="limit-bar">
                <div class="limit-bar-fill" :style="{ width: '0%' }"></div>
              </div>
              <div v-if="limit.description" class="limit-description">
                <small>{{ limit.description }}</small>
              </div>
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
const { loadUserInfo, fullName, username, initialized } = useUserInfo()
const config = useRuntimeConfig()

// 統計數據
const stats = reactive({
  strategies: 0,
  backtests: 0,
  totalReturn: '-',
  lastActivity: '今天'
})

// 會員資訊
const membershipInfo = reactive({
  member_level: 0,
  level_name: '載入中...',
  cash: '0.00',
  credit: '0.00',
  rate_limits: {}
})

// Rate Limit 詳情
const rateLimitDetails = ref({})

// 最近策略
const recentStrategies = ref([])
const loading = ref(true)

// 載入會員資訊
const loadMembershipInfo = async () => {
  try {
    const token = localStorage.getItem('access_token')
    if (!token) return

    // 載入會員資訊
    const membershipRes = await fetch(
      `${config.public.apiBase}/api/v1/membership/me`,
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    )

    if (membershipRes.ok) {
      const data = await membershipRes.json()
      Object.assign(membershipInfo, data)
    }

    // 載入 Rate Limit 詳情
    const limitsRes = await fetch(
      `${config.public.apiBase}/api/v1/membership/limits`,
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    )

    if (limitsRes.ok) {
      const data = await limitsRes.json()
      rateLimitDetails.value = data.limits || {}
    }
  } catch (error) {
    console.error('Failed to load membership info:', error)
  }
}

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

// 獲取會員等級圖示
const getMembershipIcon = (level: number) => {
  const iconMap: Record<number, string> = {
    0: '📝',  // 註冊會員
    1: '👤',  // 普通會員
    2: '⭐',  // 中階會員
    3: '💎',  // 高階會員
    4: '👑',  // VIP會員
    5: '🎯',  // 系統推廣會員
    6: '🔧',  // 系統管理員1
    7: '⚙️',  // 系統管理員2
    8: '🛠️',  // 系統管理員3
    9: '🚀'   // 創造者等級
  }
  return iconMap[level] || '📝'
}

// 篩選重要的 Rate Limit 項目
const selectedRateLimits = computed(() => {
  const important = ['回測執行', '策略建立', '資料查詢', '因子挖掘']

  return Object.entries(rateLimitDetails.value)
    .filter(([key]) => important.includes(key))
    .map(([key, value]: [string, any]) => ({
      name: key,
      limit: value.limit || value,
      description: value.description || `${key}限制`
    }))
})

// 載入用戶資訊
onMounted(async () => {
  // 優先載入用戶資訊（確保名稱顯示）
  await loadUserInfo()

  // 並行載入其他數據
  Promise.all([
    loadDashboardData(),
    loadMembershipInfo()
  ])
})

// 當頁面重新激活時刷新數據（例如從其他頁面返回）
onActivated(() => {
  loadMembershipInfo()
  loadDashboardData()
})

// 監聽頁面可見性變化，當頁面重新可見時刷新數據
if (process.client) {
  onMounted(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        loadMembershipInfo()
      }
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)

    // 清理事件監聽器
    onUnmounted(() => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    })
  })
}

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

  .stat-extra {
    color: #9ca3af;
    font-size: 0.875rem;
    margin-top: 0.25rem;
  }
}

// 會員等級卡片樣式
.membership-card {
  border: 2px solid #e5e7eb;

  &.level-0 {
    border-color: #9ca3af;
    background: linear-gradient(135deg, #f9fafb 0%, #ffffff 100%);
  }

  &.level-1 {
    border-color: #60a5fa;
    background: linear-gradient(135deg, #dbeafe 0%, #ffffff 100%);
  }

  &.level-2 {
    border-color: #34d399;
    background: linear-gradient(135deg, #d1fae5 0%, #ffffff 100%);
  }

  &.level-3 {
    border-color: #fbbf24;
    background: linear-gradient(135deg, #fef3c7 0%, #ffffff 100%);
  }

  &.level-4 {
    border-color: #f59e0b;
    background: linear-gradient(135deg, #ffedd5 0%, #ffffff 100%);
  }

  &.level-5 {
    border-color: #ec4899;
    background: linear-gradient(135deg, #fce7f3 0%, #ffffff 100%);
  }

  &.level-6 {
    border-color: #8b5cf6;
    background: linear-gradient(135deg, #ede9fe 0%, #ffffff 100%);
  }

  &.level-7 {
    border-color: #6366f1;
    background: linear-gradient(135deg, #e0e7ff 0%, #ffffff 100%);
  }

  &.level-8 {
    border-color: #3b82f6;
    background: linear-gradient(135deg, #dbeafe 0%, #ffffff 100%);
  }

  &.level-9 {
    border-color: #ef4444;
    background: linear-gradient(135deg, #fee2e2 0%, #ffffff 100%);
  }
}

// Rate Limit 區塊
.rate-limit-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.rate-limit-card {
  background: white;
  padding: 1.25rem;
  border-radius: 0.5rem;
  border: 1px solid #e5e7eb;
  transition: all 0.2s;

  &:hover {
    border-color: #3b82f6;
    box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
  }
}

.limit-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;

  .limit-name {
    font-weight: 600;
    color: #111827;
    font-size: 0.875rem;
  }

  .limit-value {
    font-weight: 700;
    color: #3b82f6;
    font-size: 1rem;
  }
}

.limit-bar {
  width: 100%;
  height: 0.5rem;
  background: #e5e7eb;
  border-radius: 9999px;
  overflow: hidden;
  margin-bottom: 0.5rem;

  .limit-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);
    border-radius: 9999px;
    transition: width 0.3s ease;
  }
}

.limit-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.75rem;

  .limit-base {
    color: #9ca3af;
  }

  .limit-multiplier {
    color: #16a34a;
    font-weight: 600;
  }
}

.limit-description {
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid #e5e7eb;

  small {
    color: #6b7280;
    font-size: 0.75rem;
    font-style: italic;
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
