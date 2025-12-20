<template>
  <div class="strategy-detail-container">
    <!-- 載入狀態 -->
    <div v-if="loading" class="loading-container">
      <div class="loading-spinner"></div>
      <p>載入中...</p>
    </div>

    <!-- 錯誤狀態 -->
    <div v-else-if="error" class="error-container">
      <div class="error-icon">⚠️</div>
      <h2>載入失敗</h2>
      <p>{{ error }}</p>
      <button @click="navigateTo('/strategies')" class="btn-back">
        返回策略列表
      </button>
    </div>

    <!-- 策略詳情 -->
    <div v-else-if="strategy" class="strategy-detail">
      <!-- 頂部導航 -->
      <div class="detail-header">
        <button @click="navigateTo('/strategies')" class="btn-back">
          ← 返回列表
        </button>
        <div class="header-actions">
          <button @click="navigateTo(`/strategies/${strategy.id}/edit`)" class="btn-edit">
            ✏️ 編輯
          </button>
          <button @click="handleDelete" class="btn-delete">
            🗑️ 刪除
          </button>
        </div>
      </div>

      <!-- 策略資訊 -->
      <div class="strategy-info-card">
        <div class="info-header">
          <div>
            <h1 class="strategy-name">{{ strategy.name }}</h1>
            <p class="strategy-description">{{ strategy.description || '無描述' }}</p>
          </div>
          <span :class="['status-badge', getStatusClass(strategy.status)]">
            {{ getStatusText(strategy.status) }}
          </span>
        </div>

        <div class="info-meta">
          <div class="meta-item">
            <span class="meta-label">建立時間</span>
            <span class="meta-value">{{ formatDate(strategy.created_at) }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">更新時間</span>
            <span class="meta-value">{{ formatDate(strategy.updated_at) }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">策略 ID</span>
            <span class="meta-value">#{{ strategy.id }}</span>
          </div>
        </div>
      </div>

      <!-- 策略代碼 -->
      <div class="code-section">
        <h2 class="section-title">策略代碼</h2>
        <div class="code-container">
          <pre><code>{{ strategy.code }}</code></pre>
        </div>
      </div>

      <!-- 回測記錄 -->
      <div class="backtest-section">
        <div class="section-header">
          <h2 class="section-title">回測記錄</h2>
          <button @click="navigateTo('/backtest')" class="btn-create">
            + 新增回測
          </button>
        </div>

        <div v-if="backtests.length === 0" class="empty-state">
          <p>尚無回測記錄</p>
        </div>

        <div v-else class="backtest-list">
          <div
            v-for="backtest in backtests"
            :key="backtest.id"
            class="backtest-item"
            @click="navigateTo(`/backtest/${backtest.id}`)"
          >
            <div class="backtest-info">
              <h3 class="backtest-name">{{ backtest.name }}</h3>
              <div class="backtest-meta">
                <span class="meta-tag">{{ backtest.symbol }}</span>
                <span class="meta-tag">{{ backtest.start_date }} ~ {{ backtest.end_date }}</span>
                <span :class="['status-tag', `status-${backtest.status.toLowerCase()}`]">
                  {{ backtest.status }}
                </span>
              </div>
            </div>
            <div v-if="backtest.result" class="backtest-result">
              <span class="result-label">報酬率</span>
              <span :class="['result-value', backtest.result.total_return >= 0 ? 'positive' : 'negative']">
                {{ backtest.result.total_return >= 0 ? '+' : '' }}{{ backtest.result.total_return.toFixed(2) }}%
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: 'auth'
})

const route = useRoute()
const config = useRuntimeConfig()

// 狀態
const strategy = ref(null)
const backtests = ref([])
const loading = ref(true)
const error = ref('')

// 載入策略詳情
const loadStrategyDetail = async () => {
  try {
    loading.value = true
    error.value = ''

    const token = localStorage.getItem('access_token')
    if (!token) {
      error.value = '請先登入'
      return
    }

    const strategyId = route.params.id

    // 載入策略
    const strategyRes = await fetch(
      `${config.public.apiBase}/api/v1/strategies/${strategyId}`,
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    )

    if (!strategyRes.ok) {
      if (strategyRes.status === 404) {
        error.value = '策略不存在'
      } else if (strategyRes.status === 403) {
        error.value = '無權限查看此策略'
      } else {
        error.value = '載入策略失敗'
      }
      return
    }

    strategy.value = await strategyRes.json()

    // 載入回測記錄
    const backtestsRes = await fetch(
      `${config.public.apiBase}/api/v1/backtest/strategy/${strategyId}`,
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    )

    if (backtestsRes.ok) {
      const backtestsData = await backtestsRes.json()
      backtests.value = backtestsData.backtests || []
    }
  } catch (err) {
    console.error('Failed to load strategy:', err)
    error.value = '載入失敗，請稍後再試'
  } finally {
    loading.value = false
  }
}

// 刪除策略
const handleDelete = async () => {
  if (!confirm('確定要刪除此策略嗎？此操作無法復原。')) {
    return
  }

  try {
    const token = localStorage.getItem('access_token')
    const strategyId = route.params.id

    const res = await fetch(
      `${config.public.apiBase}/api/v1/strategies/${strategyId}`,
      {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    )

    if (res.ok) {
      alert('策略已刪除')
      navigateTo('/strategies')
    } else {
      alert('刪除失敗')
    }
  } catch (err) {
    console.error('Failed to delete strategy:', err)
    alert('刪除失敗')
  }
}

// 格式化日期（使用台灣時區）
const { formatToTaiwanTime } = useDateTime()
const formatDate = (dateString: string) => {
  return formatToTaiwanTime(dateString)
}

// 狀態文字
const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    DRAFT: '草稿',
    ACTIVE: '啟用',
    ARCHIVED: '已封存'
  }
  return map[status] || status
}

// 狀態樣式
const getStatusClass = (status: string) => {
  const map: Record<string, string> = {
    DRAFT: 'status-draft',
    ACTIVE: 'status-active',
    ARCHIVED: 'status-archived'
  }
  return map[status] || ''
}

onMounted(() => {
  if (process.client) {
    loadStrategyDetail()
  }
})
</script>

<style scoped lang="scss">
.strategy-detail-container {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 2rem;
}

.loading-container,
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 50vh;
  text-align: center;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.error-container {
  h2 {
    font-size: 1.5rem;
    color: #ef4444;
    margin: 0 0 0.5rem 0;
  }

  p {
    color: #6b7280;
    margin: 0 0 1.5rem 0;
  }
}

.strategy-detail {
  max-width: 1200px;
  margin: 0 auto;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.btn-back {
  background: white;
  border: 1px solid #e5e7eb;
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  color: #374151;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #f9fafb;
    border-color: #3b82f6;
    color: #3b82f6;
  }
}

.header-actions {
  display: flex;
  gap: 1rem;
}

.btn-edit,
.btn-delete {
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-edit {
  background: #3b82f6;
  color: white;

  &:hover {
    background: #2563eb;
  }
}

.btn-delete {
  background: #ef4444;
  color: white;

  &:hover {
    background: #dc2626;
  }
}

.strategy-info-card {
  background: white;
  border-radius: 0.75rem;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.info-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
}

.strategy-name {
  font-size: 2rem;
  font-weight: 700;
  color: #111827;
  margin: 0 0 0.5rem 0;
}

.strategy-description {
  color: #6b7280;
  font-size: 1rem;
  margin: 0;
}

.status-badge {
  padding: 0.5rem 1rem;
  border-radius: 9999px;
  font-size: 0.875rem;
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

.info-meta {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #e5e7eb;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.meta-label {
  font-size: 0.875rem;
  color: #6b7280;
}

.meta-value {
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
}

.code-section,
.backtest-section {
  background: white;
  border-radius: 0.75rem;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 1.5rem 0;
}

.code-container {
  background: #1f2937;
  border-radius: 0.5rem;
  padding: 1.5rem;
  overflow-x: auto;

  pre {
    margin: 0;
    color: #e5e7eb;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.875rem;
    line-height: 1.6;
  }

  code {
    color: #e5e7eb;
  }
}

.btn-create {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: #2563eb;
  }
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: #9ca3af;
}

.backtest-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.backtest-item {
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  padding: 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: #3b82f6;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
  }
}

.backtest-info {
  flex: 1;
}

.backtest-name {
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 0.75rem 0;
}

.backtest-meta {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.meta-tag {
  background: #f3f4f6;
  padding: 0.25rem 0.75rem;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  color: #6b7280;
}

.status-tag {
  padding: 0.25rem 0.75rem;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  font-weight: 600;

  &.status-completed {
    background: #dcfce7;
    color: #16a34a;
  }

  &.status-running {
    background: #dbeafe;
    color: #2563eb;
  }

  &.status-failed {
    background: #fee2e2;
    color: #dc2626;
  }
}

.backtest-result {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.25rem;
}

.result-label {
  font-size: 0.875rem;
  color: #6b7280;
}

.result-value {
  font-size: 1.5rem;
  font-weight: 700;

  &.positive {
    color: #16a34a;
  }

  &.negative {
    color: #dc2626;
  }
}
</style>
