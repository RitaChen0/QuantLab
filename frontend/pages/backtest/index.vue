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
          <NuxtLink to="/strategies" class="nav-link">
            <span class="icon">📈</span>
            策略管理
          </NuxtLink>
          <NuxtLink to="/backtest" class="nav-link active">
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
            <span class="user-name">{{ username || '用戶' }}</span>
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
        <!-- 頁面標題和操作 -->
        <div class="page-header">
          <div>
            <h1 class="page-title">回測中心</h1>
            <p class="page-subtitle">執行策略回測，分析績效表現</p>
          </div>
          <button @click="showCreateModal = true" class="btn-primary">
            <span class="icon">➕</span>
            建立新回測
          </button>
        </div>

        <!-- 搜尋和篩選 -->
        <div class="filters-section">
          <div class="search-box">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="搜尋回測名稱..."
              class="search-input"
            >
          </div>
          <div class="filter-buttons">
            <button
              v-for="status in filterOptions"
              :key="status.value"
              @click="currentFilter = status.value"
              :class="['filter-btn', { active: currentFilter === status.value }]"
            >
              {{ status.label }}
            </button>
          </div>
        </div>

        <!-- 載入中 -->
        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <p>載入回測記錄中...</p>
        </div>

        <!-- 錯誤訊息 -->
        <div v-else-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>

        <!-- 回測列表 -->
        <div v-else-if="filteredBacktests.length > 0" class="backtests-grid">
          <div
            v-for="backtest in filteredBacktests"
            :key="backtest.id"
            class="backtest-card"
          >
            <div class="backtest-header">
              <h3 class="backtest-name">{{ backtest.name }}</h3>
              <span :class="['status-badge', `status-${backtest.status.toLowerCase()}`]">
                {{ getStatusText(backtest.status) }}
              </span>
            </div>

            <p class="backtest-description">{{ backtest.description || '無描述' }}</p>

            <!-- 執行中的進度提示 -->
            <div v-if="backtest.status === 'RUNNING'" class="progress-section">
              <div class="progress-bar-container">
                <div
                  class="progress-bar-filled"
                  :style="{ width: `${getProgressInfo(backtest)?.progress || 0}%` }"
                ></div>
              </div>
              <div class="progress-message">
                <span class="icon">⚙️</span>
                <span class="text">
                  <template v-if="(getProgressInfo(backtest)?.progress || 0) > 90">
                    即將完成 - {{ getProgressInfo(backtest)?.progress || 0 }}% 🎉
                  </template>
                  <template v-else>
                    回測執行中 - {{ getProgressInfo(backtest)?.progress || 0 }}%
                  </template>
                </span>
              </div>
              <p class="progress-hint">
                <span class="highlight">📅 當前處理日期：{{ formatDateSimple(getProgressInfo(backtest)?.currentDate || backtest.start_date) }}</span>
              </p>
              <p class="progress-details">
                已處理 {{ getProgressInfo(backtest)?.daysProcessed || 0 }} / {{ getProgressInfo(backtest)?.totalDays || 0 }} 個交易日
              </p>
              <p class="progress-time">
                股票代碼：{{ backtest.symbol || '載入中' }} | 期間：{{ formatDateSimple(backtest.start_date) }} ~ {{ formatDateSimple(backtest.end_date) }}
              </p>
              <p v-if="(getProgressInfo(backtest)?.progress || 0) > 90" class="progress-waiting">
                ⏳ 正在完成最後計算，即將顯示結果...
              </p>
            </div>

            <!-- 失敗的錯誤訊息 -->
            <div v-if="backtest.status === 'FAILED'" class="error-section">
              <div class="error-header">
                <span class="icon">❌</span>
                <span class="text">回測執行失敗</span>
              </div>
              <div v-if="backtest.error_message" class="error-detail">
                <p class="error-title">失敗原因：</p>
                <p class="error-message-text">{{ backtest.error_message }}</p>
              </div>
              <div v-else class="error-detail">
                <p class="error-message-text">未知錯誤，請查看系統日誌</p>
              </div>
              <div class="error-actions">
                <button @click="deleteBacktest(backtest.id)" class="btn-delete-small">
                  🗑️ 刪除此回測
                </button>
              </div>
            </div>

            <!-- 等待執行的提示 -->
            <div v-if="backtest.status === 'PENDING'" class="pending-section">
              <div class="pending-message">
                <span class="icon">⏳</span>
                <span class="text">等待執行中...</span>
              </div>
              <p class="pending-hint">回測任務已加入隊列，請稍候</p>
            </div>

            <div class="backtest-meta">
              <div class="meta-item">
                <span class="meta-label">策略：</span>
                <span class="meta-value">{{ backtest.strategy?.name || '-' }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">回測引擎：</span>
                <span class="engine-badge" :class="backtest.engine_type || 'backtrader'">
                  {{ (backtest.engine_type || 'backtrader') === 'qlib' ? '🤖 Qlib' : '📊 Backtrader' }}
                </span>
              </div>
              <div class="meta-item">
                <span class="meta-label">股票代碼：</span>
                <span class="meta-value">{{ backtest.symbol || '-' }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">回測期間：</span>
                <span class="meta-value">{{ formatDateRange(backtest.start_date, backtest.end_date) }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">初始資金：</span>
                <span class="meta-value">{{ formatCurrency(backtest.initial_capital) }}</span>
              </div>
              <div v-if="backtest.result" class="meta-item">
                <span class="meta-label">報酬率：</span>
                <span :class="['meta-value', backtest.result.total_return >= 0 ? 'text-success' : 'text-danger']">
                  {{ backtest.result.total_return >= 0 ? '+' : '' }}{{ (backtest.result.total_return * 100).toFixed(2) }}%
                </span>
              </div>
              <div class="meta-item">
                <span class="meta-label">建立時間：</span>
                <span class="meta-value">{{ formatDate(backtest.created_at) }}</span>
              </div>
            </div>

            <div class="backtest-actions">
              <button
                v-if="backtest.status === 'COMPLETED'"
                @click="viewResult(backtest.id)"
                class="btn-action btn-view"
              >
                查看結果
              </button>
              <button
                v-if="backtest.status === 'PENDING'"
                @click="runBacktest(backtest.id)"
                class="btn-action btn-run"
                :disabled="running === backtest.id"
              >
                {{ running === backtest.id ? '執行中...' : '執行回測' }}
              </button>
              <button @click="deleteBacktest(backtest.id)" class="btn-action btn-delete">
                刪除
              </button>
            </div>
          </div>
        </div>

        <!-- 空狀態 -->
        <div v-else class="empty-state">
          <div class="empty-icon">🔬</div>
          <h3>尚無回測記錄</h3>
          <p>開始建立您的第一個回測吧！</p>
          <button @click="showCreateModal = true" class="btn-primary">
            建立新回測
          </button>
        </div>

        <!-- 分頁 -->
        <div v-if="filteredBacktests.length > 0" class="pagination">
          <button
            @click="currentPage--"
            :disabled="currentPage === 1"
            class="btn-page"
          >
            上一頁
          </button>
          <span class="page-info">第 {{ currentPage }} 頁</span>
          <button
            @click="currentPage++"
            :disabled="filteredBacktests.length < pageSize"
            class="btn-page"
          >
            下一頁
          </button>
        </div>
      </div>
    </main>

    <!-- 建立回測 Modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click="showCreateModal = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>建立新回測</h2>
          <button @click="showCreateModal = false" class="btn-close">✕</button>
        </div>

        <div class="modal-body">
          <div v-if="createError" class="error-message">
            {{ createError }}
          </div>

          <form @submit.prevent="handleCreateBacktest">
            <div class="form-group">
              <label for="name">回測名稱 *</label>
              <input
                id="name"
                v-model="newBacktest.name"
                type="text"
                placeholder="例如：台積電均線策略回測"
                required
              >
            </div>

            <div class="form-group">
              <label for="description">描述</label>
              <textarea
                id="description"
                v-model="newBacktest.description"
                placeholder="描述此次回測的目的..."
                rows="2"
              ></textarea>
            </div>

            <div class="form-group">
              <label for="strategy">選擇策略 *</label>
              <select
                id="strategy"
                v-model="newBacktest.strategy_id"
                required
              >
                <option value="">請選擇策略</option>
                <option
                  v-for="strategy in availableStrategies"
                  :key="strategy.id"
                  :value="strategy.id"
                >
                  {{ strategy.name }}
                </option>
              </select>
              <p v-if="availableStrategies.length === 0" class="field-hint warning">
                ⚠️ 目前沒有可用的策略，請先到<NuxtLink to="/strategies" class="link">策略管理</NuxtLink>建立策略
              </p>
              <p v-else class="field-hint">
                已載入 {{ availableStrategies.length }} 個策略
              </p>
            </div>

            <div class="form-group">
              <label for="symbol">股票代碼 *</label>
              <input
                id="symbol"
                v-model="newBacktest.symbol"
                type="text"
                placeholder="例如：2330"
                required
              >
            </div>

            <div class="form-row">
              <div class="form-group">
                <label for="start_date">開始日期 *</label>
                <input
                  id="start_date"
                  v-model="newBacktest.start_date"
                  type="date"
                  required
                >
              </div>

              <div class="form-group">
                <label for="end_date">結束日期 *</label>
                <input
                  id="end_date"
                  v-model="newBacktest.end_date"
                  type="date"
                  required
                >
              </div>
            </div>

            <div class="form-group">
              <label for="initial_capital">初始資金 *</label>
              <input
                id="initial_capital"
                v-model.number="newBacktest.initial_capital"
                type="number"
                min="10000"
                step="10000"
                placeholder="1000000"
                required
              >
            </div>

            <div class="modal-actions">
              <button
                type="button"
                @click="showCreateModal = false"
                class="btn-secondary"
              >
                取消
              </button>
              <button
                type="submit"
                :disabled="creatingBacktest"
                class="btn-primary"
              >
                {{ creatingBacktest ? '建立中...' : '建立回測' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: 'auth'
})

const router = useRouter()
const { logout } = useAuth()
const config = useRuntimeConfig()

// 用戶資訊
const username = ref('')

// 狀態
const backtests = ref<any[]>([])
const availableStrategies = ref<any[]>([])
const loading = ref(false)
const errorMessage = ref('')
const showCreateModal = ref(false)
const creatingBacktest = ref(false)
const createError = ref('')
const running = ref<number | null>(null)
const pollingInterval = ref<NodeJS.Timeout | null>(null)
const taskIds = ref<Record<number, string>>({}) // 存儲每個回測的任務 ID
const progressData = ref<Record<number, {
  startTime: number
  currentProgress: number
  currentDate: string
}>>({})
const progressInterval = ref<NodeJS.Timeout | null>(null)

// 搜尋和篩選
const searchQuery = ref('')
const currentFilter = ref('all')
const currentPage = ref(1)
const pageSize = ref(10)

const filterOptions = [
  { value: 'all', label: '全部' },
  { value: 'PENDING', label: '待執行' },
  { value: 'RUNNING', label: '執行中' },
  { value: 'COMPLETED', label: '已完成' },
  { value: 'FAILED', label: '失敗' }
]

// 新回測表單
const newBacktest = reactive({
  name: '',
  description: '',
  strategy_id: '',
  symbol: '',
  start_date: '',
  end_date: '',
  initial_capital: 1000000,
  parameters: {}
})

// 計算過濾後的回測
const filteredBacktests = computed(() => {
  let result = backtests.value

  // 狀態過濾
  if (currentFilter.value !== 'all') {
    result = result.filter(b => b.status === currentFilter.value)
  }

  // 搜尋過濾
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(b =>
      b.name.toLowerCase().includes(query) ||
      (b.description && b.description.toLowerCase().includes(query))
    )
  }

  return result
})

// 載入回測列表
const loadBacktests = async () => {
  loading.value = true
  errorMessage.value = ''

  try {
    const token = process.client ? localStorage.getItem('access_token') : null
    if (!token) {
      router.push('/login')
      return
    }

    const response = await $fetch<any>(`${config.public.apiBase}/api/v1/backtest/`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      params: {
        page: currentPage.value,
        page_size: pageSize.value,
        status_filter: currentFilter.value !== 'all' ? currentFilter.value : undefined
      }
    })

    backtests.value = response.backtests || response || []
    console.log('Loaded backtests:', backtests.value.length)
  } catch (error: any) {
    console.error('Failed to load backtests:', error)
    errorMessage.value = error.data?.detail || '載入回測失敗'

    if (error.status === 401) {
      router.push('/login')
    }
  } finally {
    loading.value = false
  }
}

// 載入可用策略
const loadStrategies = async () => {
  try {
    const token = process.client ? localStorage.getItem('access_token') : null
    if (!token) return

    console.log('Loading strategies for backtest...')
    const response = await $fetch<any>(`${config.public.apiBase}/api/v1/strategies/`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      params: {
        skip: 0,
        limit: 100,
        status: 'active'  // 只載入已啟用的策略
      },
      cache: 'no-cache'  // 禁用快取，確保獲取最新資料
    })

    console.log('Strategies API response:', response)

    // 處理不同的回應格式（與策略列表頁面相同的邏輯）
    if (Array.isArray(response)) {
      availableStrategies.value = response
    } else if (response && response.items) {
      availableStrategies.value = response.items
    } else if (response && Array.isArray(response.strategies)) {
      availableStrategies.value = response.strategies
    } else {
      console.warn('Unexpected strategies response format:', response)
      availableStrategies.value = []
    }

    console.log('Available strategies loaded:', availableStrategies.value.length)
    console.log('Strategies:', availableStrategies.value)
  } catch (error: any) {
    console.error('Failed to load strategies:', error)
    availableStrategies.value = []
  }
}

// 建立回測
const handleCreateBacktest = async () => {
  createError.value = ''
  creatingBacktest.value = true

  try {
    const token = process.client ? localStorage.getItem('access_token') : null
    if (!token) {
      router.push('/login')
      return
    }

    const response = await $fetch<any>(`${config.public.apiBase}/api/v1/backtest/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: {
        name: newBacktest.name,
        description: newBacktest.description,
        strategy_id: parseInt(newBacktest.strategy_id),
        symbol: newBacktest.symbol,
        start_date: newBacktest.start_date,
        end_date: newBacktest.end_date,
        initial_capital: newBacktest.initial_capital,
        parameters: newBacktest.parameters
      }
    })

    console.log('Backtest created:', response)

    // 重置表單
    newBacktest.name = ''
    newBacktest.description = ''
    newBacktest.strategy_id = ''
    newBacktest.symbol = ''
    newBacktest.start_date = ''
    newBacktest.end_date = ''
    newBacktest.initial_capital = 1000000
    newBacktest.parameters = {}

    // 關閉 modal
    showCreateModal.value = false

    // 重新載入列表
    await loadBacktests()
  } catch (error: any) {
    console.error('Failed to create backtest:', error)

    if (error.data?.detail) {
      if (typeof error.data.detail === 'string') {
        createError.value = error.data.detail
      } else if (Array.isArray(error.data.detail)) {
        createError.value = error.data.detail.map((err: any) => {
          const field = err.loc ? err.loc.join('.') : ''
          const msg = err.msg || err.message || ''
          return field ? `${field}: ${msg}` : msg
        }).join('; ')
      }
    } else {
      createError.value = '建立回測失敗，請稍後再試'
    }
  } finally {
    creatingBacktest.value = false
  }
}

// 計算進度和當前日期
const calculateProgress = (backtest: any) => {
  const startDate = new Date(backtest.start_date).getTime()
  const endDate = new Date(backtest.end_date).getTime()
  const totalDays = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24))

  // 預估執行時間：45秒（可根據實際情況調整）
  const estimatedDuration = 45000

  if (!progressData.value[backtest.id]) {
    progressData.value[backtest.id] = {
      startTime: Date.now(),
      currentProgress: 0,
      currentDate: backtest.start_date
    }
  }

  const elapsed = Date.now() - progressData.value[backtest.id].startTime
  const progress = Math.min((elapsed / estimatedDuration) * 100, 99) // 最多顯示99%，等實際完成才100%

  // 根據進度計算當前處理的日期
  const daysProcessed = Math.floor((totalDays * progress) / 100)
  const currentDateMs = startDate + (daysProcessed * 24 * 60 * 60 * 1000)
  const currentDate = new Date(currentDateMs).toISOString().split('T')[0]

  progressData.value[backtest.id].currentProgress = progress
  progressData.value[backtest.id].currentDate = currentDate

  return {
    progress: Math.round(progress),
    currentDate,
    totalDays,
    daysProcessed
  }
}

// 獲取回測進度信息
const getProgressInfo = (backtest: any) => {
  if (backtest.status !== 'RUNNING') return null
  return calculateProgress(backtest)
}

// 執行回測
// 輪詢任務狀態
const pollTaskStatus = async (backtestId: number, taskId: string) => {
  const token = process.client ? localStorage.getItem('access_token') : null
  if (!token) return

  try {
    const response = await $fetch<any>(
      `${config.public.apiBase}/api/v1/backtest/${backtestId}/task/${taskId}`,
      {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${token}` }
      }
    )

    const state = response.state
    const current = response.current || 0
    const total = response.total || 100
    const status = response.status || ''

    // 更新進度數據
    if (progressData.value[backtestId]) {
      progressData.value[backtestId].currentProgress = current
    }

    console.log(`Task ${taskId} status: ${state} (${current}%)`)

    // 檢查任務是否完成
    if (state === 'SUCCESS') {
      console.log('Task completed successfully!')
      delete progressData.value[backtestId]
      delete taskIds.value[backtestId]
      running.value = null

      alert('✅ 回測執行成功！')
      await loadBacktests()
      return true // 完成
    } else if (state === 'FAILURE') {
      console.error('Task failed:', response.error)
      delete progressData.value[backtestId]
      delete taskIds.value[backtestId]
      running.value = null

      alert(`❌ 回測執行失敗：${response.error || '未知錯誤'}`)
      await loadBacktests()
      return true // 完成（失敗）
    }

    return false // 尚未完成
  } catch (error: any) {
    console.error('Failed to poll task status:', error)
    return false
  }
}

const runBacktest = async (id: number) => {
  if (!confirm('確定要執行此回測嗎？')) return

  running.value = id

  try {
    const token = process.client ? localStorage.getItem('access_token') : null
    if (!token) {
      router.push('/login')
      return
    }

    // 初始化進度追蹤
    const backtest = backtests.value.find(b => b.id === id)
    if (backtest) {
      progressData.value[id] = {
        startTime: Date.now(),
        currentProgress: 0,
        currentDate: backtest.start_date
      }
    }

    // 提交異步任務
    const response = await $fetch<any>(`${config.public.apiBase}/api/v1/backtest/run`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: {
        backtest_id: id
      }
    })

    console.log('Backtest task submitted:', response)

    // 檢查是否為異步響應 (HTTP 202)
    if (response.task_id) {
      // 存儲任務 ID
      taskIds.value[id] = response.task_id

      console.log(`Task ID: ${response.task_id}`)
      alert(`✅ 回測任務已提交！\n任務 ID: ${response.task_id.substring(0, 8)}...\n\n系統將在背景執行，請稍後查看結果。`)

      // 立即載入一次以更新狀態
      await loadBacktests()

      // 開始輪詢任務狀態 (每 2 秒檢查一次，加快狀態更新)
      const pollInterval = setInterval(async () => {
        const completed = await pollTaskStatus(id, response.task_id)
        if (completed) {
          clearInterval(pollInterval)
        }
      }, 2000)

      // 10 分鐘後停止輪詢
      setTimeout(() => {
        clearInterval(pollInterval)
        if (taskIds.value[id]) {
          delete taskIds.value[id]
          delete progressData.value[id]
          running.value = null
          console.log('Polling timeout after 10 minutes')
        }
      }, 600000)

    } else {
      // 同步響應（向後兼容）
      delete progressData.value[id]
      alert('回測執行成功！')
      await loadBacktests()
      running.value = null
    }

  } catch (error: any) {
    console.error('Failed to run backtest:', error)

    // 清理進度數據
    delete progressData.value[id]
    delete taskIds.value[id]

    // 處理速率限制錯誤
    if (error.status === 429) {
      alert('⚠️ 超過執行次數限制\n\n每小時最多執行 30 次回測。\n請稍後再試，或等待限制重置。\n\n提示：速率限制每小時重置一次。')
    } else {
      alert(error.data?.detail || '執行回測失敗')
    }
    running.value = null
  }
}

// 查看結果
const viewResult = (id: number) => {
  router.push(`/backtest/${id}`)
}

// 刪除回測
const deleteBacktest = async (id: number) => {
  if (!confirm('確定要刪除此回測嗎？此操作無法復原。')) return

  try {
    const token = process.client ? localStorage.getItem('access_token') : null
    if (!token) {
      router.push('/login')
      return
    }

    await $fetch(`${config.public.apiBase}/api/v1/backtest/${id}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    alert('回測已刪除')
    await loadBacktests()
  } catch (error: any) {
    console.error('Failed to delete backtest:', error)
    alert(error.data?.detail || '刪除回測失敗')
  }
}

// 格式化日期
const formatDate = (dateString: string) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 格式化日期範圍
const formatDateRange = (start: string, end: string) => {
  if (!start || !end) return '-'
  const startDate = new Date(start).toLocaleDateString('zh-TW')
  const endDate = new Date(end).toLocaleDateString('zh-TW')
  return `${startDate} ~ ${endDate}`
}

// 格式化簡單日期
const formatDateSimple = (dateString: string) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

// 格式化金額
const formatCurrency = (amount: number) => {
  if (!amount) return '-'
  return new Intl.NumberFormat('zh-TW', {
    style: 'currency',
    currency: 'TWD',
    minimumFractionDigits: 0
  }).format(amount)
}

// 狀態文字
const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    PENDING: '待執行',
    RUNNING: '執行中',
    COMPLETED: '已完成',
    FAILED: '失敗'
  }
  return statusMap[status] || status
}

// 登出
const handleLogout = () => {
  logout()
}

// 載入資料
onMounted(() => {
  if (process.client) {
    const token = localStorage.getItem('access_token')
    if (token) {
      username.value = '用戶'
    }
  }

  loadBacktests()
  loadStrategies()
})

// 監聽篩選變化
watch(currentFilter, () => {
  currentPage.value = 1
  loadBacktests()
})

// 監聽 modal 開啟，重新載入策略列表
watch(showCreateModal, (newValue) => {
  if (newValue) {
    console.log('Create modal opened, reloading strategies...')
    loadStrategies()
  }
})

// 檢查是否有執行中的回測
const hasRunningBacktests = computed(() => {
  return backtests.value.some(b => b.status === 'RUNNING')
})

// 監聽執行中的回測，啟動進度更新
watch(hasRunningBacktests, (hasRunning) => {
  if (hasRunning) {
    // 啟動狀態輪詢（每 2 秒檢查一次完成狀態）
    if (!pollingInterval.value) {
      console.log('Starting status polling (every 2s)...')
      pollingInterval.value = setInterval(() => {
        loadBacktests()
      }, 2000)
    }

    // 啟動進度顯示更新（每 500 毫秒更新當前處理日期）
    if (!progressInterval.value) {
      console.log('Starting progress display updates...')
      progressInterval.value = setInterval(() => {
        // 更新進度顯示（計算當前處理的日期）
        backtests.value.forEach(backtest => {
          if (backtest.status === 'RUNNING') {
            calculateProgress(backtest)
          }
        })
      }, 500)
    }
  } else {
    // 停止所有計時器
    if (pollingInterval.value) {
      console.log('Stopping polling')
      clearInterval(pollingInterval.value)
      pollingInterval.value = null
    }

    if (progressInterval.value) {
      console.log('Stopping progress updates')
      clearInterval(progressInterval.value)
      progressInterval.value = null
    }
  }
})

// 組件卸載時清理輪詢
onBeforeUnmount(() => {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value)
    pollingInterval.value = null
  }
  if (progressInterval.value) {
    clearInterval(progressInterval.value)
    progressInterval.value = null
  }
})
</script>

<style scoped lang="scss">
// 複用策略頁面的樣式
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

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;

  .page-title {
    font-size: 2rem;
    font-weight: 700;
    color: #111827;
    margin: 0 0 0.5rem 0;
  }

  .page-subtitle {
    color: #6b7280;
    margin: 0;
  }
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;

  .icon {
    font-size: 1.25rem;
  }

  &:hover:not(:disabled) {
    background: #2563eb;
  }

  &:disabled {
    background: #9ca3af;
    cursor: not-allowed;
  }
}

// 搜尋和篩選
.filters-section {
  background: white;
  padding: 1.5rem;
  border-radius: 0.75rem;
  margin-bottom: 2rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.search-box {
  margin-bottom: 1rem;

  .search-input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #d1d5db;
    border-radius: 0.5rem;
    font-size: 1rem;

    &:focus {
      outline: none;
      border-color: #3b82f6;
    }
  }
}

.filter-buttons {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.filter-btn {
  padding: 0.5rem 1rem;
  background: #f3f4f6;
  color: #6b7280;
  border: 2px solid transparent;
  border-radius: 0.5rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #e5e7eb;
  }

  &.active {
    background: #dbeafe;
    color: #1e40af;
    border-color: #3b82f6;
  }
}

// 載入和錯誤狀態
.loading-state {
  text-align: center;
  padding: 4rem 2rem;

  .spinner {
    width: 3rem;
    height: 3rem;
    border: 4px solid #e5e7eb;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 1rem;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-message {
  padding: 1rem;
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 0.5rem;
  color: #991b1b;
  margin-bottom: 1rem;
}

// 回測卡片
.backtests-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.backtest-card {
  background: white;
  padding: 1.5rem;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }
}

.backtest-header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  margin-bottom: 1rem;
}

.backtest-name {
  font-size: 1.25rem;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 1rem;
  font-size: 0.75rem;
  font-weight: 500;

  &.status-pending {
    background: #f3f4f6;
    color: #6b7280;
  }

  &.status-running {
    background: #fef3c7;
    color: #92400e;
  }

  &.status-completed {
    background: #d1fae5;
    color: #065f46;
  }

  &.status-failed {
    background: #fee2e2;
    color: #991b1b;
  }
}

.backtest-description {
  color: #6b7280;
  margin-bottom: 1rem;
  line-height: 1.5;
}

// 進度提示區
.progress-section {
  margin-bottom: 1rem;
  padding: 1rem;
  background: #f0f9ff;
  border-left: 4px solid #3b82f6;
  border-radius: 0.5rem;
}

.progress-bar-container {
  width: 100%;
  height: 8px;
  background: #dbeafe;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 0.75rem;
  position: relative;
}

.progress-bar-filled {
  height: 100%;
  background: linear-gradient(
    90deg,
    #3b82f6 0%,
    #60a5fa 100%
  );
  transition: width 0.5s ease-out;
  border-radius: 4px;
  position: relative;
  overflow: hidden;

  &::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(
      90deg,
      transparent 0%,
      rgba(255, 255, 255, 0.3) 50%,
      transparent 100%
    );
    animation: shimmer 2s infinite;
  }
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.progress-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #1e40af;

  .icon {
    font-size: 1.25rem;
    animation: rotate 2s linear infinite;
  }

  .text {
    font-size: 0.95rem;
  }
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.progress-hint {
  margin: 0.5rem 0;
  font-size: 0.95rem;
  color: #1e40af;
  line-height: 1.5;
  font-weight: 500;

  .highlight {
    background: linear-gradient(120deg, #dbeafe 0%, #bfdbfe 100%);
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    font-weight: 600;
  }
}

.progress-details {
  margin: 0.5rem 0;
  font-size: 0.875rem;
  color: #1e40af;
  font-weight: 500;
}

.progress-time {
  margin: 0.5rem 0 0 0;
  font-size: 0.8rem;
  color: #6b7280;
}

.progress-waiting {
  margin: 0.75rem 0 0 0;
  padding: 0.5rem;
  background: linear-gradient(120deg, #fef3c7 0%, #fde68a 100%);
  border-left: 3px solid #f59e0b;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  color: #92400e;
  font-weight: 600;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

// 錯誤訊息區
.error-section {
  margin-bottom: 1rem;
  padding: 1rem;
  background: #fef2f2;
  border-left: 4px solid #ef4444;
  border-radius: 0.5rem;
}

.error-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  font-weight: 600;
  color: #991b1b;

  .icon {
    font-size: 1.25rem;
  }

  .text {
    font-size: 1rem;
  }
}

.error-detail {
  margin-bottom: 0.75rem;

  .error-title {
    font-size: 0.875rem;
    font-weight: 600;
    color: #991b1b;
    margin: 0 0 0.5rem 0;
  }

  .error-message-text {
    font-size: 0.875rem;
    color: #7f1d1d;
    line-height: 1.5;
    margin: 0;
    padding: 0.75rem;
    background: white;
    border-radius: 0.375rem;
    border: 1px solid #fecaca;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  }
}

.error-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.btn-delete-small {
  padding: 0.375rem 0.75rem;
  background: #fee2e2;
  border: 1px solid #fecaca;
  color: #991b1b;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #fecaca;
    border-color: #fca5a5;
  }
}

// 等待執行區
.pending-section {
  margin-bottom: 1rem;
  padding: 1rem;
  background: #f9fafb;
  border-left: 4px solid #9ca3af;
  border-radius: 0.5rem;
}

.pending-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #4b5563;

  .icon {
    font-size: 1.25rem;
    animation: spin 2s linear infinite;
  }

  .text {
    font-size: 1rem;
  }
}

.pending-hint {
  font-size: 0.875rem;
  color: #6b7280;
  margin: 0;
  padding-left: 1.75rem;
}

.backtest-meta {
  margin-bottom: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
}

.meta-item {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;

  .meta-label {
    color: #6b7280;
  }

  .meta-value {
    color: #111827;
    font-weight: 500;

    &.text-success {
      color: #059669;
    }

    &.text-danger {
      color: #dc2626;
    }
  }
}

.backtest-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.btn-action {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 0.5rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.875rem;

  &.btn-view {
    background: #dbeafe;
    color: #1e40af;

    &:hover {
      background: #bfdbfe;
    }
  }

  &.btn-run {
    background: #d1fae5;
    color: #065f46;

    &:hover:not(:disabled) {
      background: #a7f3d0;
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }

  &.btn-delete {
    background: #fee2e2;
    color: #991b1b;

    &:hover {
      background: #fecaca;
    }
  }
}

// 空狀態
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  background: white;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);

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
}

// 分頁
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 2rem;
}

.btn-page {
  padding: 0.5rem 1rem;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(:disabled) {
    background: #f3f4f6;
    border-color: #3b82f6;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.page-info {
  color: #6b7280;
}

// Modal
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-content {
  background: white;
  border-radius: 0.75rem;
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;

  h2 {
    font-size: 1.5rem;
    font-weight: 600;
    color: #111827;
    margin: 0;
  }
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6b7280;
  transition: color 0.2s;

  &:hover {
    color: #111827;
  }
}

.modal-body {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1.5rem;

  label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: #374151;
  }

  input,
  textarea,
  select {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #d1d5db;
    border-radius: 0.5rem;
    font-size: 1rem;
    font-family: inherit;

    &:focus {
      outline: none;
      border-color: #3b82f6;
    }
  }

  textarea {
    resize: vertical;
  }

  .field-hint {
    margin-top: 0.5rem;
    font-size: 0.875rem;
    color: #6b7280;

    &.warning {
      color: #92400e;
      background: #fef3c7;
      padding: 0.5rem;
      border-radius: 0.375rem;
      border-left: 3px solid #f59e0b;
    }

    .link {
      color: #3b82f6;
      text-decoration: underline;
      font-weight: 500;

      &:hover {
        color: #2563eb;
      }
    }
  }
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 2rem;
}

.btn-secondary {
  padding: 0.75rem 1.5rem;
  background: #f3f4f6;
  color: #374151;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: #e5e7eb;
  }
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

  .page-header {
    flex-direction: column;
    align-items: stretch;
    gap: 1rem;
  }

  .backtests-grid {
    grid-template-columns: 1fr;
  }

  .modal-content {
    width: 95%;
  }

  .form-row {
    grid-template-columns: 1fr;
  }
}

/* 引擎徽章樣式 */
.engine-badge {
  font-size: 0.875rem;
  padding: 0.375rem 0.875rem;
  border-radius: 16px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.engine-badge.backtrader {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.engine-badge.qlib {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
}
</style>
