<template>
  <div class="task-detail-page">
    <!-- 頂部導航欄 -->
    <AppHeader />

    <!-- 頁首麵包屑 -->
    <div class="breadcrumb">
      <NuxtLink to="/rdagent">自動研發</NuxtLink>
      <span class="separator">›</span>
      <NuxtLink to="/rdagent?tab=tasks">任務列表</NuxtLink>
      <span class="separator">›</span>
      <span class="current">任務 #{{ taskId }}</span>
    </div>

    <!-- 載入中 -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>載入任務詳情中...</p>
    </div>

    <!-- 錯誤訊息 -->
    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <NuxtLink to="/rdagent?tab=tasks" class="btn-back">返回任務列表</NuxtLink>
    </div>

    <!-- 任務詳情 -->
    <div v-else-if="task" class="task-content">
      <!-- 任務標題與狀態 -->
      <div class="task-header">
        <div class="header-left">
          <h1>任務 #{{ task.id }}</h1>
          <span :class="['status-badge', task.status]">{{ getStatusLabel(task.status) }}</span>
        </div>
        <div class="header-right">
          <span class="task-type">{{ getTypeLabel(task.task_type) }}</span>
        </div>
      </div>

      <!-- 任務時間資訊 -->
      <div class="time-info">
        <div class="time-item">
          <span class="label">創建時間：</span>
          <span class="value">{{ formatDate(task.created_at) }}</span>
        </div>
        <div class="time-item" v-if="task.started_at">
          <span class="label">開始時間：</span>
          <span class="value">{{ formatDate(task.started_at) }}</span>
        </div>
        <div class="time-item" v-if="task.completed_at">
          <span class="label">完成時間：</span>
          <span class="value">{{ formatDate(task.completed_at) }}</span>
        </div>
        <div class="time-item" v-if="task.started_at && task.completed_at">
          <span class="label">執行時長：</span>
          <span class="value">{{ calculateDuration(task.started_at, task.completed_at) }}</span>
        </div>
      </div>

      <!-- 輸入參數 -->
      <div class="section">
        <h2>📋 輸入參數</h2>
        <div class="params-grid">
          <div class="param-item" v-for="(value, key) in task.input_params" :key="key">
            <span class="param-key">{{ formatParamKey(key) }}</span>
            <span class="param-value">{{ formatParamValue(value) }}</span>
          </div>
        </div>
      </div>

      <!-- 執行結果 -->
      <div class="section" v-if="task.result">
        <h2>📊 執行結果</h2>
        <div class="result-summary">
          <div class="result-card" v-if="task.result.generated_factors_count !== undefined">
            <div class="result-label">生成因子數量</div>
            <div class="result-value">{{ task.result.generated_factors_count }} 個</div>
          </div>
          <div class="result-card" v-if="task.llm_calls">
            <div class="result-label">LLM API 調用</div>
            <div class="result-value">{{ task.llm_calls }} 次</div>
          </div>
          <div class="result-card" v-if="task.llm_cost">
            <div class="result-label">LLM 成本</div>
            <div class="result-value">${{ task.llm_cost.toFixed(4) }}</div>
          </div>
        </div>

        <!-- 策略優化結果 -->
        <div v-if="task.task_type === 'strategy_optimization'">
          <!-- 策略資訊 -->
          <div v-if="task.result.strategy_info" class="strategy-info">
            <h3>📋 策略資訊</h3>
            <div class="info-grid">
              <div class="info-item">
                <span class="label">策略 ID</span>
                <span class="value">{{ task.result.strategy_info.id }}</span>
              </div>
              <div class="info-item">
                <span class="label">策略名稱</span>
                <span class="value">{{ task.result.strategy_info.name }}</span>
              </div>
              <div class="info-item">
                <span class="label">引擎類型</span>
                <span class="value">{{ task.result.strategy_info.engine_type }}</span>
              </div>
              <div class="info-item">
                <span class="label">最近回測 ID</span>
                <span class="value">{{ task.result.strategy_info.latest_backtest_id }}</span>
              </div>
            </div>
          </div>

          <!-- 當前績效 -->
          <div v-if="task.result.current_performance" class="current-performance">
            <h3>📈 當前績效指標</h3>
            <div class="metrics-grid">
              <div class="metric-card">
                <div class="metric-label">Sharpe Ratio</div>
                <div class="metric-value" :class="getMetricClass('sharpe', task.result.current_performance.sharpe_ratio)">
                  {{ formatNumber(task.result.current_performance.sharpe_ratio, 2) }}
                </div>
              </div>
              <div class="metric-card">
                <div class="metric-label">年化報酬率</div>
                <div class="metric-value" :class="getMetricClass('return', task.result.current_performance.annual_return)">
                  {{ formatPercent(task.result.current_performance.annual_return) }}
                </div>
              </div>
              <div class="metric-card">
                <div class="metric-label">最大回撤</div>
                <div class="metric-value" :class="getMetricClass('drawdown', task.result.current_performance.max_drawdown)">
                  {{ formatPercent(task.result.current_performance.max_drawdown) }}
                </div>
              </div>
              <div class="metric-card">
                <div class="metric-label">勝率</div>
                <div class="metric-value" :class="getMetricClass('winrate', task.result.current_performance.win_rate)">
                  {{ formatPercent(task.result.current_performance.win_rate) }}
                </div>
              </div>
              <div class="metric-card">
                <div class="metric-label">總交易次數</div>
                <div class="metric-value">
                  {{ task.result.current_performance.total_trades }}
                </div>
              </div>
              <div class="metric-card">
                <div class="metric-label">盈利因子</div>
                <div class="metric-value" :class="getMetricClass('profit_factor', task.result.current_performance.profit_factor)">
                  {{ formatNumber(task.result.current_performance.profit_factor, 2) }}
                </div>
              </div>
            </div>
          </div>

          <!-- 問題診斷 -->
          <div v-if="task.result.issues_diagnosed && task.result.issues_diagnosed.length > 0" class="issues-diagnosed">
            <h3>🔍 問題診斷</h3>
            <div class="issues-list">
              <div v-for="(issue, index) in task.result.issues_diagnosed" :key="index"
                   class="issue-item" :class="'severity-' + issue.severity">
                <div class="issue-header">
                  <span class="severity-badge" :class="'severity-' + issue.severity">
                    {{ issue.severity.toUpperCase() }}
                  </span>
                  <span class="issue-type">{{ issue.type }}</span>
                </div>
                <div class="issue-body">
                  <p class="issue-description">{{ issue.description }}</p>
                  <div class="issue-metrics">
                    <span class="current-value">當前值: {{ formatMetricValue(issue.current_value) }}</span>
                    <span class="target-value">目標值: {{ formatMetricValue(issue.target_value) }}</span>
                  </div>
                  <p class="issue-recommendation">💡 建議: {{ issue.recommendation }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 優化建議 -->
          <div v-if="task.result.optimization_suggestions && task.result.optimization_suggestions.length > 0" class="optimization-suggestions">
            <h3>💡 優化建議</h3>
            <div class="suggestions-list">
              <div v-for="(suggestion, index) in task.result.optimization_suggestions" :key="index"
                   class="suggestion-card" :class="'priority-' + (suggestion.priority || 'medium')">
                <div class="suggestion-header">
                  <span class="suggestion-number">建議 {{ index + 1 }}</span>
                  <span class="priority-badge" :class="'priority-' + (suggestion.priority || 'medium')">
                    {{ (suggestion.priority || 'medium').toUpperCase() }}
                  </span>
                </div>
                <div class="suggestion-body">
                  <div class="suggestion-field">
                    <strong>類型:</strong> {{ suggestion.type || 'N/A' }}
                  </div>
                  <div class="suggestion-field">
                    <strong>問題:</strong> {{ suggestion.problem || 'N/A' }}
                  </div>
                  <div class="suggestion-field">
                    <strong>解決方案:</strong>
                    <p class="solution-text">{{ suggestion.solution || 'N/A' }}</p>
                  </div>
                  <div class="suggestion-field">
                    <strong>預期效果:</strong> {{ suggestion.expected_improvement || 'N/A' }}
                  </div>
                  <div v-if="suggestion.code_changes" class="suggestion-field">
                    <strong>代碼修改:</strong>
                    <pre class="code-block">{{ suggestion.code_changes }}</pre>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 預期改進 -->
          <div v-if="task.result.estimated_improvements" class="estimated-improvements">
            <h3>📊 預期改進</h3>
            <div class="improvements-grid">
              <div v-for="(value, key) in task.result.estimated_improvements" :key="key" class="improvement-item">
                <span class="improvement-label">{{ formatImprovementLabel(key) }}</span>
                <span class="improvement-value">{{ value }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 因子挖掘結果 -->
        <div v-if="task.task_type === 'factor_mining'">
          <!-- 生成的因子列表 -->
          <div v-if="task.result.factors && task.result.factors.length > 0" class="factors-list">
            <h3>生成的因子</h3>
            <div class="factor-item" v-for="(factor, index) in task.result.factors" :key="index">
              <div class="factor-header">
                <span class="factor-name">{{ factor.name }}</span>
                <span class="factor-category" v-if="factor.category">{{ factor.category }}</span>
              </div>
              <div class="factor-formula">
                <code>{{ factor.formula }}</code>
              </div>
            </div>
          </div>

          <!-- 其他結果訊息 -->
          <div v-if="task.result.message" class="result-message">
            <p>{{ task.result.message }}</p>
          </div>

          <!-- 日誌目錄 -->
          <div v-if="task.result.log_directory" class="log-directory">
            <span class="label">日誌目錄：</span>
            <code>{{ task.result.log_directory }}</code>
          </div>
        </div>
      </div>

      <!-- 錯誤訊息 -->
      <div class="section error-section" v-if="task.error_message">
        <h2>❌ 錯誤訊息</h2>
        <div class="error-box">
          <pre>{{ task.error_message }}</pre>
        </div>
      </div>

      <!-- 操作按鈕 -->
      <div class="actions">
        <NuxtLink to="/rdagent?tab=tasks" class="btn-secondary">返回任務列表</NuxtLink>
        <button
          v-if="task.status === 'failed'"
          @click="retryTask"
          class="btn-primary"
          :disabled="isRetrying"
        >
          {{ isRetrying ? '重試中...' : '🔄 重試任務' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const { loadUserInfo } = useUserInfo()
const config = useRuntimeConfig()

const taskId = ref(route.params.id)
const task = ref<any>(null)
const loading = ref(true)
const error = ref('')
const isRetrying = ref(false)

// 載入任務詳情
const loadTaskDetail = async () => {
  loading.value = true
  error.value = ''

  try {
    const token = localStorage.getItem('access_token')  // ✅ 修正：使用正確的 key
    if (!token) {
      router.push('/login')
      return
    }

    task.value = await $fetch(`${config.public.apiBase}/api/v1/rdagent/tasks/${taskId.value}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
  } catch (err: any) {
    error.value = err.data?.detail || '載入任務詳情失敗'
    console.error('Failed to load task detail:', err)
  } finally {
    loading.value = false
  }
}

// 重試失敗的任務
const retryTask = async () => {
  isRetrying.value = true

  try {
    const token = localStorage.getItem('access_token')  // ✅ 修正：使用正確的 key
    await $fetch(`${config.public.apiBase}/api/v1/rdagent/tasks/${taskId.value}/retry`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    })

    alert('任務已重新提交！')
    loadTaskDetail()
  } catch (err: any) {
    alert('重試失敗：' + (err.data?.detail || err.message))
  } finally {
    isRetrying.value = false
  }
}

// 格式化日期（使用台灣時區）
const { formatToTaiwanTime } = useDateTime()
const formatDate = (dateStr: string) => {
  return formatToTaiwanTime(dateStr, { showSeconds: true })
}

// 計算執行時長
// Note: Using `new Date()` here is acceptable for duration calculation (not display)
// Purpose: Calculate time elapsed between start and end timestamps
// Timezone is irrelevant because:
// 1. .getTime() returns Unix timestamp (ms since 1970), which is timezone-independent
// 2. The difference (diffMs) is always correct regardless of timezone
// 3. Result is formatted as duration string ("X hours Y minutes"), not a timestamp
const calculateDuration = (startStr: string, endStr: string) => {
  const start = new Date(startStr).getTime()  // Acceptable: duration calculation
  const end = new Date(endStr).getTime()      // Acceptable: duration calculation
  const diffMs = end - start

  const hours = Math.floor(diffMs / 3600000)
  const minutes = Math.floor((diffMs % 3600000) / 60000)
  const seconds = Math.floor((diffMs % 60000) / 1000)

  if (hours > 0) {
    return `${hours} 小時 ${minutes} 分鐘`
  } else if (minutes > 0) {
    return `${minutes} 分鐘 ${seconds} 秒`
  } else {
    return `${seconds} 秒`
  }
}

// 格式化參數鍵
const formatParamKey = (key: string) => {
  const keyMap: Record<string, string> = {
    research_goal: '研究目標',
    stock_pool: '股票池',
    max_factors: '最多生成因子',
    llm_model: 'LLM 模型',
    max_iterations: '最大迭代次數'
  }
  return keyMap[key] || key
}

// 格式化參數值
const formatParamValue = (value: any) => {
  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2)
  }
  return String(value)
}

// 狀態標籤
const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    pending: '等待中',
    running: '執行中',
    completed: '已完成',
    failed: '失敗',
    cancelled: '已取消'
  }
  return labels[status] || status
}

// 類型標籤
const getTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    factor_mining: '因子挖掘',
    strategy_optimization: '策略優化',
    model_extraction: '模型提取'
  }
  return labels[type] || type
}

// 格式化數值
const formatNumber = (value: number | null | undefined, decimals: number = 2) => {
  if (value === null || value === undefined) return 'N/A'
  return value.toFixed(decimals)
}

// 格式化百分比
const formatPercent = (value: number | null | undefined) => {
  if (value === null || value === undefined) return 'N/A'
  return (value * 100).toFixed(2) + '%'
}

// 格式化指標值
const formatMetricValue = (value: any) => {
  if (value === null || value === undefined) return 'N/A'
  if (typeof value === 'number') {
    // 假設小於 1 的是百分比
    if (value < 1 && value > -1) {
      return formatPercent(value)
    }
    return formatNumber(value, 2)
  }
  return String(value)
}

// 格式化改進標籤
const formatImprovementLabel = (key: string) => {
  const labels: Record<string, string> = {
    sharpe_ratio: 'Sharpe Ratio',
    annual_return: '年化報酬率',
    max_drawdown: '最大回撤',
    win_rate: '勝率',
    profit_factor: '盈利因子'
  }
  return labels[key] || key
}

// 獲取指標樣式類別
const getMetricClass = (metricType: string, value: number | null | undefined) => {
  if (value === null || value === undefined) return ''

  switch (metricType) {
    case 'sharpe':
      if (value >= 2.0) return 'metric-excellent'
      if (value >= 1.0) return 'metric-good'
      return 'metric-poor'

    case 'return':
      if (value >= 0.20) return 'metric-excellent'
      if (value >= 0.10) return 'metric-good'
      return 'metric-poor'

    case 'drawdown':
      if (value <= -0.30) return 'metric-poor'
      if (value <= -0.20) return 'metric-good'
      return 'metric-excellent'

    case 'winrate':
      if (value >= 0.60) return 'metric-excellent'
      if (value >= 0.40) return 'metric-good'
      return 'metric-poor'

    case 'profit_factor':
      if (value >= 1.5) return 'metric-excellent'
      if (value >= 1.2) return 'metric-good'
      return 'metric-poor'

    default:
      return ''
  }
}

onMounted(() => {
  loadUserInfo()
  loadTaskDetail()
})
</script>

<style scoped lang="scss">
.task-detail-page {
  min-height: 100vh;
  background: #f9fafb;
}

.breadcrumb {
  margin-bottom: 2rem;
  font-size: 0.9rem;
  color: #6b7280;

  a {
    color: #3b82f6;
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }

  .separator {
    margin: 0 0.5rem;
  }

  .current {
    color: #111827;
    font-weight: 500;
  }
}

.loading-state,
.error-state {
  text-align: center;
  padding: 4rem 2rem;

  .spinner {
    width: 50px;
    height: 50px;
    margin: 0 auto 1rem;
    border: 4px solid #f3f4f6;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
}

.error-state {
  color: #dc2626;
}

.btn-back {
  display: inline-block;
  margin-top: 1rem;
  padding: 0.75rem 1.5rem;
  background: #3b82f6;
  color: white;
  text-decoration: none;
  border-radius: 0.375rem;

  &:hover {
    background: #2563eb;
  }
}

.task-content {
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2rem;
  border-bottom: 1px solid #e5e7eb;

  .header-left {
    display: flex;
    align-items: center;
    gap: 1rem;

    h1 {
      font-size: 1.75rem;
      font-weight: 700;
      margin: 0;
    }
  }

  .status-badge {
    padding: 0.375rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.875rem;
    font-weight: 500;

    &.pending {
      background: #fef3c7;
      color: #92400e;
    }

    &.running {
      background: #dbeafe;
      color: #1e40af;
    }

    &.completed {
      background: #d1fae5;
      color: #065f46;
    }

    &.failed {
      background: #fee2e2;
      color: #991b1b;
    }
  }

  .task-type {
    padding: 0.5rem 1rem;
    background: #f3f4f6;
    border-radius: 0.375rem;
    font-size: 0.9rem;
    font-weight: 500;
  }
}

.time-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  padding: 1.5rem 2rem;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;

  .time-item {
    .label {
      display: block;
      font-size: 0.875rem;
      color: #6b7280;
      margin-bottom: 0.25rem;
    }

    .value {
      font-weight: 500;
      color: #111827;
    }
  }
}

.section {
  padding: 2rem;
  border-bottom: 1px solid #e5e7eb;

  &:last-child {
    border-bottom: none;
  }

  h2 {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 1.5rem;
  }

  h3 {
    font-size: 1.1rem;
    font-weight: 600;
    margin: 1.5rem 0 1rem;
  }
}

.params-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;

  .param-item {
    display: flex;
    flex-direction: column;
    padding: 1rem;
    background: #f9fafb;
    border-radius: 0.375rem;

    .param-key {
      font-size: 0.875rem;
      color: #6b7280;
      margin-bottom: 0.5rem;
    }

    .param-value {
      font-weight: 500;
      color: #111827;
      word-wrap: break-word;
    }
  }
}

.result-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;

  .result-card {
    padding: 1.5rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 0.5rem;
    color: white;

    .result-label {
      font-size: 0.875rem;
      opacity: 0.9;
      margin-bottom: 0.5rem;
    }

    .result-value {
      font-size: 1.75rem;
      font-weight: 700;
    }
  }
}

.factors-list {
  .factor-item {
    margin-bottom: 1.5rem;
    padding: 1rem;
    background: #f9fafb;
    border-radius: 0.375rem;
    border-left: 4px solid #3b82f6;

    .factor-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.75rem;

      .factor-name {
        font-weight: 600;
        color: #111827;
      }

      .factor-category {
        padding: 0.25rem 0.75rem;
        background: #dbeafe;
        color: #1e40af;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
      }
    }

    .factor-formula {
      code {
        display: block;
        padding: 0.75rem;
        background: white;
        border-radius: 0.25rem;
        font-family: 'Monaco', 'Courier New', monospace;
        font-size: 0.875rem;
        color: #1f2937;
        overflow-x: auto;
      }
    }
  }
}

.result-message {
  padding: 1rem;
  background: #dbeafe;
  border-radius: 0.375rem;
  margin-bottom: 1rem;

  p {
    margin: 0;
    color: #1e40af;
  }
}

.log-directory {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background: #f3f4f6;
  border-radius: 0.375rem;

  .label {
    font-weight: 500;
    color: #6b7280;
  }

  code {
    flex: 1;
    padding: 0.5rem;
    background: white;
    border-radius: 0.25rem;
    font-family: 'Monaco', 'Courier New', monospace;
    font-size: 0.875rem;
    overflow-x: auto;
  }
}

.error-section {
  .error-box {
    padding: 1rem;
    background: #fee2e2;
    border-radius: 0.375rem;
    border-left: 4px solid #dc2626;

    pre {
      margin: 0;
      color: #991b1b;
      font-family: 'Monaco', 'Courier New', monospace;
      font-size: 0.875rem;
      white-space: pre-wrap;
      word-wrap: break-word;
    }
  }
}

.actions {
  display: flex;
  gap: 1rem;
  padding: 2rem;

  .btn-secondary,
  .btn-primary {
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 0.375rem;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    text-decoration: none;
    display: inline-block;
  }

  .btn-secondary {
    background: #f3f4f6;
    color: #374151;

    &:hover {
      background: #e5e7eb;
    }
  }

  .btn-primary {
    background: #3b82f6;
    color: white;

    &:hover:not(:disabled) {
      background: #2563eb;
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }
}

// 策略優化專用樣式
.strategy-info,
.current-performance,
.issues-diagnosed,
.optimization-suggestions,
.estimated-improvements {
  margin-top: 2rem;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;

  .info-item {
    display: flex;
    flex-direction: column;
    padding: 1rem;
    background: #f9fafb;
    border-radius: 0.375rem;

    .label {
      font-size: 0.875rem;
      color: #6b7280;
      margin-bottom: 0.5rem;
    }

    .value {
      font-weight: 500;
      color: #111827;
    }
  }
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 1rem;

  .metric-card {
    padding: 1.25rem;
    background: #f9fafb;
    border-radius: 0.5rem;
    text-align: center;
    transition: transform 0.2s;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    .metric-label {
      font-size: 0.875rem;
      color: #6b7280;
      margin-bottom: 0.5rem;
    }

    .metric-value {
      font-size: 1.5rem;
      font-weight: 700;

      &.metric-excellent {
        color: #10b981;
      }

      &.metric-good {
        color: #3b82f6;
      }

      &.metric-poor {
        color: #ef4444;
      }
    }
  }
}

.issues-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;

  .issue-item {
    border-left: 4px solid;
    padding: 1rem;
    background: #f9fafb;
    border-radius: 0.375rem;

    &.severity-high {
      border-left-color: #ef4444;
    }

    &.severity-medium {
      border-left-color: #f59e0b;
    }

    &.severity-low {
      border-left-color: #3b82f6;
    }

    .issue-header {
      display: flex;
      gap: 0.75rem;
      align-items: center;
      margin-bottom: 0.75rem;

      .severity-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        color: white;

        &.severity-high {
          background: #ef4444;
        }

        &.severity-medium {
          background: #f59e0b;
        }

        &.severity-low {
          background: #3b82f6;
        }
      }

      .issue-type {
        font-weight: 600;
        color: #111827;
      }
    }

    .issue-body {
      .issue-description {
        color: #374151;
        margin-bottom: 0.75rem;
      }

      .issue-metrics {
        display: flex;
        gap: 1.5rem;
        margin-bottom: 0.75rem;
        font-size: 0.875rem;
        color: #6b7280;
      }

      .issue-recommendation {
        color: #10b981;
        font-style: italic;
        margin: 0;
      }
    }
  }
}

.suggestions-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;

  .suggestion-card {
    border: 2px solid;
    padding: 1.5rem;
    border-radius: 0.5rem;
    background: white;

    &.priority-high {
      border-color: #ef4444;
    }

    &.priority-medium {
      border-color: #f59e0b;
    }

    &.priority-low {
      border-color: #3b82f6;
    }

    .suggestion-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
      padding-bottom: 0.75rem;
      border-bottom: 1px solid #e5e7eb;

      .suggestion-number {
        font-size: 1.125rem;
        font-weight: 700;
        color: #111827;
      }

      .priority-badge {
        padding: 0.375rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        color: white;

        &.priority-high {
          background: #ef4444;
        }

        &.priority-medium {
          background: #f59e0b;
        }

        &.priority-low {
          background: #3b82f6;
        }
      }
    }

    .suggestion-body {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;

      .suggestion-field {
        line-height: 1.6;

        strong {
          color: #111827;
        }

        .solution-text {
          margin: 0.5rem 0 0 0;
          padding: 0.75rem;
          background: #f9fafb;
          border-radius: 0.375rem;
          color: #374151;
          line-height: 1.6;
        }

        .code-block {
          background: #1f2937;
          color: #f3f4f6;
          padding: 1rem;
          border-radius: 0.375rem;
          overflow-x: auto;
          font-family: 'Monaco', 'Courier New', monospace;
          font-size: 0.875rem;
          line-height: 1.5;
          margin: 0.5rem 0 0 0;
        }
      }
    }
  }
}

.improvements-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;

  .improvement-item {
    display: flex;
    flex-direction: column;
    padding: 1rem;
    background: #ecfdf5;
    border-radius: 0.375rem;
    border-left: 4px solid #10b981;

    .improvement-label {
      font-size: 0.875rem;
      color: #059669;
      font-weight: 600;
      margin-bottom: 0.5rem;
    }

    .improvement-value {
      font-size: 1.25rem;
      font-weight: 700;
      color: #111827;
    }
  }
}
</style>
